"""Mini démo en direct : probabilité de victoire pendant une partie, sur ce PC.

Usage personnel et analyse uniquement : jamais en compétition ni en tournoi, rien de
publié ou de distribué (règles des développeurs Riot). Le script ne fait que LIRE
l'API locale « Live Client Data » que le jeu ouvre sur https://127.0.0.1:2999 ;
il n'utilise que ce que le tableau des scores montre déjà.

Le module a quatre parties :
1. Les variables « live » : celles qu'on peut calculer AUSSI pendant une partie.
   L'API live est moins riche que la timeline de match-v5 :
   - or : seul le joueur actif voit son or. La valeur des objets des 10 joueurs est un
     mauvais substitut (testé sur les timelines : corrélation 0,78 avec le vrai écart
     d'or à 15 min, erreur typique 1 500 d'or ; en partie, les objets et niveaux adverses
     semblent ne se mettre à jour qu'à vue). L'or est donc RETIRÉ des modèles live ;
     la valeur des objets (items_k) n'est gardée que pour information, dans le CSV ;
   - XP : seul le niveau est donné ; on le convertit en XP minimale de ce niveau ;
   - CS : creepScore, arrondi à la dizaine inférieure (des deux côtés) ;
   - pas d'event pour les plaques de tour ni pour les larves du Néant : ces deux
     variables sont retirées du modèle.
2. L'entraînement (python src/live.py train) : la logistique par minute de l'étape 17
   réentraînée sur deux jeux de variables live (VARIANTS) :
   - « sans or » : XP (par le niveau), CS (arrondis à 10) et les events ;
   - « events » : seulement les events (kills, tours, objectifs), les plus fiables.
   L'XP et les CS sont calculés EXACTEMENT comme en live. On mesure sur le test ce que
   coûte chaque variante, puis on réentraîne sur toutes les parties et on enregistre
   les deux dans data/live_model.joblib.
3. La lecture de l'API et le calcul des variables à une minute donnée.
4. Les commandes : dump (sauver un instantané JSON), replay (rejouer un fichier JSON),
   watch (suivre la partie en cours, une ligne par minute).

    python src/live.py train                 # base PostgreSQL nécessaire (Docker)
    python src/live.py watch                 # pendant une partie, pas besoin de la base
    python src/live.py watch --minute 15     # une seule ligne, à 15 min
    python src/live.py dump                  # instantané brut -> data/live_captures/
    python src/live.py replay data/live_captures/xxx.json
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
import requests
import urllib3

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MODEL_PATH = DATA / "live_model.joblib"
ITEMS_PATH = DATA / "ddragon_items.json"
CAPTURES = DATA / "live_captures"
API = "https://127.0.0.1:2999/liveclientdata"

# ---------------------------------------------------------------------------
# 1. Les variables live
# ---------------------------------------------------------------------------
# Variables tirées des events (datés, exacts en live comme dans la timeline).
EVENT_FEATURES = [
    "kills_diff", "towers_diff", "dragons_diff", "first_blood", "first_tower",
    "first_dragon", "heralds_diff", "barons_diff", "elders_diff", "inhibs_diff",
    "kills_1min_diff",
]
# Les deux modèles live. Ni or, ni plaques, ni larves (rien de fiable en live).
VARIANTS = {
    "sans_or": ["xp_k", "cs_diff"] + EVENT_FEATURES,
    "events": EVENT_FEATURES,
}
# Tout ce que live_features() calcule ; items_k (valeur des objets) = information seulement.
LIVE_FEATURES = ["items_k", "xp_k", "cs_diff"] + EVENT_FEATURES
TEAM_SIGN = {"ORDER": 1, "CHAOS": -1}      # ORDER = bleu (100), CHAOS = rouge (200)


def xp_from_level(level):
    """XP minimale pour atteindre `level` : 280 pour le niveau 2, puis +100 à chaque palier
    (280, 380, 480...). Somme des paliers = 180 (L-1) + 50 L (L-1)."""
    return 180 * (level - 1) + 50 * level * (level - 1)


def cs_floor(cs):
    """CS arrondi à la dizaine inférieure, joueur par joueur (comme le tableau des scores)."""
    return (cs // 10) * 10


# Même découpage que FRAMES_SQL (sequences.py) : minutes 1 à max, dernière frame retirée,
# 10 joueurs présents ; mais XP et CS calculés comme en live, joueur par joueur.
LIVE_FRAMES_SQL = """
WITH last AS (
    SELECT match_id, max(minute) AS last_minute
    FROM participant_frames
    WHERE match_id = ANY(%(ids)s)
    GROUP BY match_id
)
SELECT f.match_id, f.minute,
       sum(CASE WHEN p.team_id = 100 THEN 1 ELSE -1 END
           * (180 * (f.level - 1) + 50 * f.level * (f.level - 1))) AS xp_level_diff,
       sum(CASE WHEN p.team_id = 100 THEN 1 ELSE -1 END
           * (((f.minions_killed + f.jungle_minions_killed) / 10) * 10)) AS cs10_diff
FROM participant_frames f
JOIN participants p USING (match_id, participant_id)
JOIN last l USING (match_id)
WHERE f.minute BETWEEN 1 AND %(max_minute)s
  AND f.minute < l.last_minute
GROUP BY f.match_id, f.minute
HAVING count(*) = 10
"""


# ---------------------------------------------------------------------------
# 2. L'entraînement (la base est nécessaire ; imports lourds faits ici seulement)
# ---------------------------------------------------------------------------
def build_live_table(games):
    """Tableau long de l'étape 17, avec xp_k et cs_diff remplacés par leur version live."""
    import psycopg
    from features import database_url
    from sequences import MAX_MINUTE, build_minute_features

    long = build_minute_features(games)
    params = {"ids": list(games["match_id"]), "max_minute": MAX_MINUTE}
    with psycopg.connect(database_url()) as conn:
        live = pd.DataFrame(conn.execute(LIVE_FRAMES_SQL, params).fetchall(),
                            columns=["match_id", "minute", "xp_level_diff", "cs10_diff"])
    out = long.merge(live, on=["match_id", "minute"], how="inner", validate="1:1")
    assert len(out) == len(long), "les minutes des deux requêtes ne correspondent pas"
    out["xp_k"] = out["xp_level_diff"].astype(float) / 1000
    out["cs_diff"] = out["cs10_diff"].astype(float)
    return long, out.drop(columns=["xp_level_diff", "cs10_diff"])


def train():
    """Mesure le coût de la version live sur le test, puis entraîne le modèle final."""
    from features import TARGET, build_features, time_split
    from models import evaluate
    from sequences import (SEQ_FEATURES, PerMinuteLogit, bootstrap_games,
                           scores_by_minute, split_games)

    t0 = time.time()
    games = build_features()
    games_train, games_test = time_split(games, 0.2)
    full, live = build_live_table(games)
    print(f"{len(games)} parties, {len(live)} lignes (partie, minute), lues en "
          f"{time.time() - t0:.0f} s")

    # a) Même découpage et même test que les étapes 13 à 17.
    full_tr, full_te = split_games(full, games_train, games_test)
    live_tr, live_te = split_games(live, games_train, games_test)
    assert (full_te["match_id"].to_numpy() == live_te["match_id"].to_numpy()).all()
    preds = {"étape 17 (16 variables)": PerMinuteLogit(SEQ_FEATURES).fit(full_tr).predict(full_te),
             # référence seulement : l'or EXACT n'existe pas en live
             "or exact + XP/CS live (14)": PerMinuteLogit(["gold_k"] + VARIANTS["sans_or"])
                                           .fit(live_tr).predict(live_te)}
    for name, cols in VARIANTS.items():
        preds[f"{name} ({len(cols)} variables)"] = (PerMinuteLogit(cols).fit(live_tr)
                                                    .predict(live_te))

    y = live_te[TARGET]
    scores = pd.DataFrame({name: evaluate(y, p) for name, p in preds.items()}).T
    print("\nTest (les 20 % de parties les plus récentes), toutes les minutes :")
    print(scores.round(4).to_string())
    ref = preds["étape 17 (16 variables)"]
    print("\nÉcart de log loss avec l'étape 17 (IC 95 % par parties) :")
    for name, p in list(preds.items())[1:]:
        diff, low, high = bootstrap_games(live_te, ref, p)
        print(f"  {name:30s} {diff:+.4f}  ({low:+.4f} à {high:+.4f})")
    short = {name.split(" (")[0]: p for name, p in preds.items()}
    by_minute = scores_by_minute(live_te, short, minutes=[5, 10, 15, 20, 25, 30, 35])
    print("\nLog loss par minute :")
    print(by_minute[[c for c in by_minute.columns if "log loss" in c]].round(4).to_string())

    # b) Modèles finaux : toutes les parties (plus de données = coefficients plus stables).
    variants = {}
    for name, cols in VARIANTS.items():
        final = PerMinuteLogit(cols).fit(live)
        variants[name] = {"models": final.models_, "columns": cols,
                          "test_log_loss": float(scores.loc[f"{name} ({len(cols)} variables)",
                                                            "log_loss"])}
    DATA.mkdir(exist_ok=True)
    joblib.dump({"variants": variants, "last": final.last,
                 "n_games": int(games["match_id"].nunique()),
                 "created": dt.datetime.now().isoformat(timespec="seconds")},
                MODEL_PATH)
    print(f"\nModèles enregistrés : {MODEL_PATH.relative_to(ROOT)} "
          f"({', '.join(variants)} ; {len(final.models_)} logistiques chacun)")


def load_model(path=MODEL_PATH):
    if not path.exists():
        sys.exit(f"Modèle introuvable ({path.relative_to(ROOT)}). Lance d'abord : "
                 "python src/live.py train (Docker Desktop ouvert + docker compose start).")
    model = joblib.load(path)
    if "variants" not in model:
        sys.exit("Modèle d'une ancienne version (avec l'or). Relance : python src/live.py train")
    return model


def predict(model, features, minute, variant):
    """P(victoire du bleu) avec la logistique de la minute (la plus proche si absente)."""
    v = model["variants"][variant]
    bucket = min(minute, model["last"])
    key = min(v["models"], key=lambda k: abs(k - bucket))
    row = pd.DataFrame([features])[v["columns"]]
    return float(v["models"][key].predict_proba(row)[0, 1])


# ---------------------------------------------------------------------------
# 3. L'API live et les variables à une minute donnée
# ---------------------------------------------------------------------------
class GameNotRunning(Exception):
    """Pas de partie en cours (le jeu n'ouvre l'API que pendant une partie)."""


# Le jeu sert l'API en HTTPS avec un certificat auto-signé : on désactive la vérification.
# Sans risque ici : on ne parle qu'à 127.0.0.1 (ce PC) et on n'envoie aucun secret.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_game():
    """Tout l'état de la partie en cours (endpoint allgamedata), en dictionnaire Python."""
    try:
        r = requests.get(f"{API}/allgamedata", verify=False, timeout=3)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        # API fermée (pas de partie) ou qui ne répond plus (fin de partie : le jeu se
        # ferme et l'API reste muette quelques secondes, vu le 3 nov. 2026).
        raise GameNotRunning from e
    if r.status_code in (404, 503):     # jeu lancé mais partie pas encore chargée
        raise GameNotRunning
    r.raise_for_status()
    return r.json()


def load_item_costs():
    """Coût total de chaque objet (Data Dragon de Riot), mis en cache dans data/.

    Pourquoi pas le champ « price » de l'API live ? Ce n'est PAS le prix total : dans une
    capture réelle, Hubris (environ 3 000 d'or au total) a price = 750 : le prix de la dernière combinaison.
    Data Dragon donne gold.total. « price » ne sert que pour un objet absent de Data Dragon.
    """
    if ITEMS_PATH.exists():
        return {int(k): v for k, v in json.loads(ITEMS_PATH.read_text()).items()}
    try:
        version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json",
                               timeout=10).json()[0]
        items = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{version}"
                             "/data/fr_FR/item.json", timeout=20).json()["data"]
    except requests.exceptions.RequestException:
        print("Data Dragon injoignable : prix des objets lus dans l'API live (champ price).")
        return {}
    costs = {int(k): v["gold"]["total"] for k, v in items.items()}
    DATA.mkdir(exist_ok=True)
    ITEMS_PATH.write_text(json.dumps(costs))
    print(f"Prix de {len(costs)} objets téléchargés (patch {version}) -> "
          f"{ITEMS_PATH.relative_to(ROOT)}")
    return costs


def player_names(p):
    """Tous les noms sous lesquels un joueur peut apparaître dans les events."""
    keys = ["riotId", "riotIdGameName", "summonerName", "championName"]
    return {p[k] for k in keys if p.get(k)}


def items_value(p, costs):
    return sum(costs.get(it["itemID"], it.get("price", 0)) * it.get("count", 1)
               for it in p.get("items", []))


def structure_sign(name):
    """Signe de l'équipe qui DÉTRUIT une tour / un inhibiteur, d'après son nom.

    Le jeu nomme le bâtiment d'après l'équipe qui le POSSÈDE. Deux formats existent :
    - celui du jeu actuel (vu dans une capture réelle, nov. 2026) : Turret_TOrder_L2_P3_...,
      Turret_TChaos_L1_P3_... ;
    - celui de la documentation Riot : Turret_T1_L_03_A, Barracks_T2_R1 (T1 = Order).
    Bâtiment d'Order (bleu) -> détruit par le rouge (−1) ; de Chaos -> par le bleu (+1).
    On lit le nom du bâtiment plutôt que KillerName, qui est souvent un sbire.
    """
    m = re.search(r"_T(1|2|Order|Chaos)_", name or "", flags=re.IGNORECASE)
    if m is None:
        return None
    return -1 if m.group(1).lower() in ("1", "order") else 1


def live_features(game, minute, costs):
    """Variables LIVE_FEATURES à la minute `minute`, vues du bleu (comme à l'entraînement).

    Events : ceux d'AVANT minute × 60 s (même règle que l'étape 12). Or, XP et CS :
    l'instantané reçu, pris juste après le passage de la minute par `watch`.
    Renvoie (variables, avertissements).
    """
    players = game["allPlayers"]
    sign_of, warnings = {}, []
    for p in players:
        for n in player_names(p):
            sign_of[n] = TEAM_SIGN[p["team"]]

    s = lambda p: TEAM_SIGN[p["team"]]
    f = {
        "items_k": sum(s(p) * items_value(p, costs) for p in players) / 1000,  # info
        "xp_k": sum(s(p) * xp_from_level(p["level"]) for p in players) / 1000,
        "cs_diff": float(sum(s(p) * cs_floor(p["scores"]["creepScore"]) for p in players)),
    }
    counts = {k: 0 for k in ["kills", "towers", "dragons", "elders", "heralds", "barons",
                             "inhibs", "kills_1min"]}
    firsts = {"first_blood": 0, "first_tower": 0, "first_dragon": 0}
    cutoff = minute * 60
    unknown = set()
    for e in sorted(game["events"]["Events"], key=lambda e: e["EventTime"]):
        if e["EventTime"] >= cutoff:
            continue
        name = e["EventName"]
        if name == "ChampionKill":
            # Comme load.py : le kill va à l'équipe ADVERSE de la victime (exécutions comprises).
            victim = sign_of.get(e.get("VictimName"))
            sign = -victim if victim else sign_of.get(e.get("KillerName"))
            kind = "kills"
            if sign and e["EventTime"] >= cutoff - 60:
                counts["kills_1min"] += sign
        elif name in ("TurretKilled", "InhibKilled"):
            sign = structure_sign(e.get(name))
            kind = "towers" if name == "TurretKilled" else "inhibs"
        elif name == "DragonKill":
            sign = sign_of.get(e.get("KillerName"))
            kind = "elders" if e.get("DragonType") == "Elder" else "dragons"
        elif name in ("HeraldKill", "BaronKill"):
            sign = sign_of.get(e.get("KillerName"))
            kind = "heralds" if name == "HeraldKill" else "barons"
        else:
            if name not in KNOWN_OTHER_EVENTS:
                unknown.add(name)
            continue
        if sign is None:
            warnings.append(f"event {name} à {e['EventTime']:.0f} s : équipe inconnue, ignoré")
            continue
        counts[kind] += sign
        first = {"kills": "first_blood", "towers": "first_tower", "dragons": "first_dragon"}
        if kind in first and firsts[first[kind]] == 0:
            firsts[first[kind]] = sign
    for k in ["kills", "towers", "dragons", "elders", "heralds", "barons", "inhibs",
              "kills_1min"]:
        f[f"{k}_diff"] = counts[k]
    f.update(firsts)
    if unknown:
        warnings.append("events non utilisés : " + ", ".join(sorted(unknown)))
    return f, warnings


# Events connus mais sans variable dans le modèle.
KNOWN_OTHER_EVENTS = {"GameStart", "MinionsSpawning", "FirstBrick", "FirstBlood",
                      "Multikill", "Ace", "InhibRespawningSoon", "InhibRespawned", "GameEnd"}


def my_sign(game):
    """+1 si le joueur actif est bleu, −1 s'il est rouge, None en spectateur."""
    me = game.get("activePlayer", {})
    names = {me.get(k) for k in ["riotId", "riotIdGameName", "summonerName"]} - {None}
    for p in game["allPlayers"]:
        if names & player_names(p):
            return TEAM_SIGN[p["team"]]
    return None


# ---------------------------------------------------------------------------
# 4. Affichage et commandes
# ---------------------------------------------------------------------------
_shown = set()   # chaque avertissement n'est affiché qu'une fois par lancement


def report(game, minute, model, costs, log=None, late=False):
    f, warnings = live_features(game, minute, costs)
    p = {v: predict(model, f, minute, v) for v in model["variants"]}
    me = my_sign(game)
    line = (f"min {minute:2d} | XP {f['xp_k']:+5.1f} k | CS {f['cs_diff']:+4.0f} | "
            f"kills {f['kills_diff']:+3d} | tours {f['towers_diff']:+2d} | "
            f"dragons {f['dragons_diff']:+2d} | bleu : sans or {p['sans_or']:5.1%}, "
            f"events {p['events']:5.1%}")
    if me is not None:
        mine = {v: (q if me == 1 else 1 - q) for v, q in p.items()}
        line += (f" | ton équipe ({'bleue' if me == 1 else 'rouge'}) : "
                 f"{mine['sans_or']:5.1%} / {mine['events']:5.1%}")
    print(line + ("   (lancé en retard : XP/CS de maintenant)" if late else ""))
    for w in warnings:
        if w not in _shown:
            print("   !", w)
            _shown.add(w)
    if log is not None:
        log.writerow({"minute": minute, "p_sans_or": round(p["sans_or"], 4),
                      "p_events": round(p["events"], 4),
                      "my_team": {1: "bleu", -1: "rouge"}.get(me, ""), **f})
    return p


def cmd_watch(minute=None, interval=5):
    model, costs = load_model(), load_item_costs()
    print(f"Modèle : {model['n_games']} parties, entraîné le {model['created']}. "
          "Ctrl+C pour arrêter.")
    print("Probabilités vues du bleu (en écart bleu − rouge). En attente d'une partie...")
    CAPTURES.mkdir(parents=True, exist_ok=True)
    stamp = f"{dt.datetime.now():%Y%m%d_%H%M%S}"
    path = CAPTURES / f"watch_{stamp}.csv"
    # L'état brut de chaque minute est gardé aussi : pour vérifier après coup ce que le
    # jeu envoie vraiment (données locales, data/ n'est jamais publié).
    raw_dir = CAPTURES / f"watch_{stamp}"
    save = lambda game, name: (raw_dir / f"{name}.json").write_text(
        json.dumps(game, ensure_ascii=False), encoding="utf-8")
    done, first_poll, log_file, log, last_game = set(), True, None, None, None
    try:
        while True:
            try:
                game = fetch_game()
            except GameNotRunning:
                if log is not None:      # on suivait une partie : elle vient de se fermer
                    save(last_game, "fin")
                    print("Partie terminée (le jeu ne répond plus).")
                    break
                time.sleep(10)
                continue
            last_game = game
            if log is None:
                log_file = open(path, "w", newline="", encoding="utf-8")
                log = csv.DictWriter(log_file, ["minute", "p_sans_or", "p_events", "my_team"]
                                     + LIVE_FEATURES)
                log.writeheader()
                raw_dir.mkdir(exist_ok=True)
            now = int(game["gameData"]["gameTime"] // 60)
            if any(e["EventName"] == "GameEnd" for e in game["events"]["Events"]):
                save(game, "fin")
                print("Partie terminée.")
                break
            wanted = now >= 1 and now not in done and (minute is None or now == minute
                                                       or (first_poll and now > minute))
            if wanted:
                report(game, now if minute is None or now == minute else minute, model,
                       costs, log, late=first_poll and now > 1)
                log_file.flush()
                save(game, f"min_{now:02d}")
                done.add(now)
                if minute is not None:
                    break
            first_poll = False
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
    finally:
        if log_file:
            log_file.close()
            print(f"Lignes enregistrées dans {path.relative_to(ROOT)} "
                  f"(états bruts dans {raw_dir.relative_to(ROOT)})")


def cmd_dump():
    try:
        game = fetch_game()
    except GameNotRunning:
        sys.exit("Aucune partie en cours : lance une partie (ou l'outil d'entraînement).")
    CAPTURES.mkdir(parents=True, exist_ok=True)
    path = CAPTURES / f"capture_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(game, indent=2, ensure_ascii=False), encoding="utf-8")
    t = game["gameData"]["gameTime"]
    print(f"Instantané à {int(t // 60)} min {int(t % 60):02d} s -> {path.relative_to(ROOT)}")
    print(f"{len(game['allPlayers'])} joueurs, {len(game['events']['Events'])} events")


def cmd_replay(path, minute=None):
    game = json.loads(Path(path).read_text(encoding="utf-8"))
    now = int(game["gameData"]["gameTime"] // 60)
    report(game, minute or now, load_model(), load_item_costs(),
           late=minute is not None and minute < now)


def main():
    parser = argparse.ArgumentParser(description="Probabilité de victoire en direct (usage perso)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("train", help="entraîner le modèle live (base PostgreSQL nécessaire)")
    w = sub.add_parser("watch", help="suivre la partie en cours, une ligne par minute")
    w.add_argument("--minute", type=int, help="une seule ligne, à cette minute")
    w.add_argument("--interval", type=float, default=5, help="secondes entre deux lectures")
    sub.add_parser("dump", help="sauver l'état brut de la partie en cours (JSON)")
    r = sub.add_parser("replay", help="calculer la probabilité sur un fichier JSON sauvé")
    r.add_argument("file")
    r.add_argument("--minute", type=int)
    args = parser.parse_args()
    if args.cmd == "train":
        train()
    elif args.cmd == "watch":
        cmd_watch(args.minute, args.interval)
    elif args.cmd == "dump":
        cmd_dump()
    else:
        cmd_replay(args.file, args.minute)


if __name__ == "__main__":
    main()
