"""Le modèle de l'appli : probabilité de victoire minute par minute et ses explications.

Trois parties :
1. train (python src/winprob.py train, base nécessaire) : la logistique par minute de
   l'étape 17 (PerMinuteLogit, 16 variables, or exact de la timeline). On vérifie
   d'abord sur le test des étapes 13 à 17 qu'on retrouve sa log loss (0,5327), puis on
   la réentraîne sur TOUTES les parties et on l'enregistre dans data/app_model.joblib.
   L'appli ne fait que charger ce fichier : elle n'a besoin ni de la base, ni de PyTorch.
2. check (python src/winprob.py check, base nécessaire) : sur des parties de data/raw,
   compare les variables calculées depuis le JSON (match_minutes.minute_features, le
   chemin de l'appli) à celles de la base (le chemin de l'entraînement). Écart attendu : 0.
3. Les fonctions de l'appli : predict(), contributions() (valeurs de SHAP exactes de
   la logistique, comme à l'étape 14, minute par minute) et key_moments() (les minutes
   où la probabilité bouge le plus, avec la part due aux events et celle due au temps).

Pourquoi la version « or exact » et pas le modèle « sans or » de la démo en direct ?
Après la partie, la timeline de Riot donne l'or exact des 10 joueurs à chaque minute :
inutile de se priver de la meilleure variable (0,5327 contre 0,5365 au test).
"""

import argparse
import datetime as dt
import gzip
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.special import expit

from explain import linear_contributions
from match_minutes import SEQ_FEATURES, TIME, minute_features

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "app_model.joblib"

# Noms lisibles des variables, pour l'appli (la valeur affichée est l'écart bleu − rouge,
# ou ton équipe − l'adversaire une fois retournée).
LABELS = {
    "gold_k": "Écart d'or (milliers)",
    "xp_k": "Écart d'XP (milliers)",
    "cs_diff": "Écart de sbires et monstres",
    "kills_diff": "Écart de kills",
    "towers_diff": "Écart de tours",
    "plates_diff": "Écart de plaques",
    "dragons_diff": "Écart de dragons",
    "grubs_diff": "Écart de larves du Néant",
    "first_blood": "Premier sang",
    "first_tower": "Première tour",
    "first_dragon": "Premier dragon",
    "heralds_diff": "Écart de hérauts",
    "barons_diff": "Écart de barons",
    "elders_diff": "Écart de dragons ancestraux",
    "inhibs_diff": "Écart d'inhibiteurs",
    "kills_1min_diff": "Kills de la dernière minute",
}


# ---------------------------------------------------------------------------
# 1. Entraînement (imports lourds ici seulement : PyTorch vient avec sequences.py)
# ---------------------------------------------------------------------------
def train():
    from features import TARGET, build_features, time_split
    from models import evaluate
    from sequences import PerMinuteLogit, build_minute_features, split_games

    t0 = time.time()
    games = build_features()
    long = build_minute_features(games)
    print(f"{len(games)} parties, {len(long)} lignes (partie, minute), lues en "
          f"{time.time() - t0:.0f} s")

    # a) Contrôle : même découpage et même test qu'aux étapes 13 à 17.
    games_train, games_test = time_split(games, 0.2)
    train_rows, test_rows = split_games(long, games_train, games_test)
    p = PerMinuteLogit(SEQ_FEATURES).fit(train_rows).predict(test_rows)
    scores = evaluate(test_rows[TARGET], p)
    print(f"Test (20 % de parties les plus récentes) : log loss {scores['log_loss']:.4f}, "
          f"AUC {scores['auc']:.3f}  (étape 17 : 0,5327 et 0,802)")

    # b) Modèle final : toutes les parties.
    final = PerMinuteLogit(SEQ_FEATURES).fit(long)
    patches = sorted(games["patch"].unique(), key=lambda v: tuple(map(int, v.split("."))))
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"models": final.models_, "columns": SEQ_FEATURES, "last": final.last,
                 "n_games": int(len(games)), "patches": patches,
                 "test_log_loss": float(scores["log_loss"]),
                 "created": dt.datetime.now().isoformat(timespec="seconds")}, MODEL_PATH)
    print(f"Modèle enregistré : {MODEL_PATH.relative_to(ROOT)} ({len(final.models_)} "
          f"logistiques, minutes 1 à {final.last} et plus ; patchs {patches[0]} à {patches[-1]})")


def check(n=200):
    """Le chemin JSON de l'appli donne-t-il les mêmes variables que la base ?"""
    from features import build_features
    from sequences import build_minute_features

    games = build_features()
    raw = ROOT / "data" / "raw"
    ids = [m for m in games["match_id"] if (raw / "timelines" / f"{m}.json.gz").exists()]
    ids = ids[:: max(1, len(ids) // n)][:n]       # parties réparties sur toute la période
    db = build_minute_features(games[games["match_id"].isin(ids)])
    worst, rows = 0.0, 0
    for match_id, from_db in db.groupby("match_id"):
        def read(kind):
            with gzip.open(raw / kind / f"{match_id}.json.gz", "rt", encoding="utf-8") as f:
                return json.load(f)
        from_json = minute_features(read("matches"), read("timelines"))
        a = from_db.sort_values(TIME)[[TIME] + SEQ_FEATURES].to_numpy(dtype=float)
        b = from_json[[TIME] + SEQ_FEATURES].to_numpy(dtype=float)
        if a.shape != b.shape:
            print(f"  {match_id} : {len(a)} minutes en base, {len(b)} depuis le JSON")
            worst = np.inf
            continue
        worst, rows = max(worst, float(np.abs(a - b).max())), rows + len(a)
    print(f"{db['match_id'].nunique()} parties, {rows} (partie, minute) comparées : "
          f"plus grand écart base / JSON = {worst}")
    print("OK : l'appli calcule exactement les variables de l'entraînement." if worst == 0
          else "ÉCART : ne pas utiliser l'appli avant d'avoir trouvé la cause.")


# ---------------------------------------------------------------------------
# 2. Les fonctions de l'appli
# ---------------------------------------------------------------------------
def load_model(path=MODEL_PATH):
    if not path.exists():
        raise FileNotFoundError(
            f"Modèle introuvable ({path.name}). Lance d'abord : python src/winprob.py train "
            "(Docker Desktop ouvert + docker compose start).")
    return joblib.load(path)


def _model_keys(model, minutes):
    """Pour chaque minute, la clé de sa logistique : min(minute, last), ou la plus proche."""
    keys = np.array(sorted(model["models"]))
    buckets = np.minimum(np.asarray(minutes), model["last"])
    return keys[np.abs(keys[None, :] - buckets[:, None]).argmin(axis=1)]


def predict(model, table):
    """P(victoire du bleu) à chaque ligne (minute) de `table`."""
    keys = _model_keys(model, table[TIME])
    p = np.empty(len(table))
    for k in np.unique(keys):
        rows = keys == k
        p[rows] = model["models"][k].predict_proba(table.loc[rows, model["columns"]])[:, 1]
    return p


def contributions(model, table):
    """Contributions de chaque variable (log-odds, vers le bleu), minute par minute.

    Chaque minute a sa propre logistique : on applique linear_contributions() de
    l'étape 14 avec le modèle de la minute. base = constante du modèle de la minute.
    base + somme des contributions = logit de predict(), exactement.
    """
    keys = _model_keys(model, table[TIME])
    contrib = pd.DataFrame(index=table.index, columns=model["columns"], dtype=float)
    base = pd.Series(index=table.index, dtype=float)
    for k in np.unique(keys):
        rows = table.index[keys == k]
        c, b = linear_contributions(model["models"][k], table.loc[rows, model["columns"]])
        contrib.loc[rows] = c.to_numpy()
        base.loc[rows] = b
    return contrib, base


def key_moments(model, table, sign=1, n=5):
    """Les n minutes où la probabilité (vue de l'équipe `sign`) bouge le plus.

    Entre t−1 et t, deux choses changent : l'état de la partie (les events) ET le
    modèle (chaque minute a sa logistique : 1 000 d'or ne pèsent pas pareil à 10 et à
    30 min). On sépare les deux, avec f_t = le modèle de la minute t :
        variation totale = f_t(x_t) − f_{t−1}(x_{t−1})
                         = [f_t(x_t) − f_t(x_{t−1})]       part des events
                         + [f_t(x_{t−1}) − f_{t−1}(x_{t−1})] part du temps
    Les moments clés sont classés par la part des events (ce que les joueurs ont fait).
    Les variables qui expliquent ce changement : contributions de x_t moins celles de
    x_{t−1}, toutes deux avec le modèle de la minute t (en log-odds, exactes).
    """
    t = table.reset_index(drop=True)
    if len(t) < 2:
        return pd.DataFrame()
    now, before = t.iloc[1:].reset_index(drop=True), t.iloc[:-1].reset_index(drop=True)
    before_now_model = before.assign(**{TIME: now[TIME].to_numpy()})  # x_{t−1}, modèle f_t

    def side(p):
        return p if sign == 1 else 1 - p
    p_now, p_before = side(predict(model, now)), side(predict(model, before))
    p_mixed = side(predict(model, before_now_model))
    c_now, _ = contributions(model, now)
    c_before, _ = contributions(model, before_now_model)
    change = (c_now - c_before) * sign

    rows = []
    for i in range(len(now)):
        top = change.iloc[i].abs().sort_values(ascending=False)
        top = [f"{LABELS[v]} ({change.iloc[i][v]:+.2f})" for v in top.index[:3]
               if abs(change.iloc[i][v]) > 0.01]
        rows.append({"minute": int(now[TIME][i]), "avant": p_before[i], "après": p_now[i],
                     "variation": p_now[i] - p_before[i],
                     "part des events": p_now[i] - p_mixed[i],
                     "part du temps": p_mixed[i] - p_before[i],
                     "variables": ", ".join(top)})
    out = pd.DataFrame(rows)
    order = out["part des events"].abs().sort_values(ascending=False).index[:n]
    return out.loc[order].sort_values("minute").reset_index(drop=True)


def player_report(model, games, minutes=(10, 15, 20), n_sim=20_000, seed=0):
    """Le modèle se trompe-t-il plus sur CE joueur que sur une partie moyenne ?

    games : liste de (tableau minute par minute, sign, victoire) pour les parties du
    joueur ; sign = +1 s'il était bleu, −1 s'il était rouge.

    Pour chaque minute de contrôle, on compare ce qu'on observe à ce qu'on ATTENDRAIT
    si les probabilités du modèle étaient justes pour ce joueur :
    - bons pronostics (probabilité > 50 % du bon côté) : attendus = somme de max(p, 1 − p) ;
    - log loss : attendue = moyenne de l'entropie −p log p − (1 − p) log(1 − p) ;
    - « hasard » : on simule n_sim fois les résultats de ces mêmes parties en tirant
      chaque victoire avec la probabilité p du modèle, et on compte la part des
      simulations où la log loss est au moins aussi mauvaise que l'observée. Petite
      (< 5 %) = le modèle lit vraiment moins bien ce joueur ; grande = malchance possible.
    Pas besoin de réentraîner ni de connaître le test : la référence vient des
    probabilités elles-mêmes (c'est un test de calibration sur un seul joueur).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for m in minutes:
        p, y = [], []
        for table, sign, win in games:
            at = table[table[TIME] == m]
            if len(at):
                pb = predict(model, at)[0]
                p.append(pb if sign == 1 else 1 - pb)
                y.append(int(win))
        if len(p) < 3:
            continue
        p, y = np.clip(np.array(p), 1e-6, 1 - 1e-6), np.array(y)

        def loss(outcomes):
            return -(outcomes * np.log(p) + (1 - outcomes) * np.log(1 - p)).mean(axis=-1)

        observed = float(loss(y))
        simulated = loss((rng.random((n_sim, len(p))) < p).astype(int))
        rows.append({"minute": m, "parties": len(p),
                     "bons pronostics": int(((p > 0.5) == (y == 1)).sum()),
                     "bons attendus": float(np.maximum(p, 1 - p).sum()),
                     "log loss": observed,
                     "log loss attendue": float(loss(p)),
                     "hasard": float((simulated >= observed).mean()),
                     "remontées": int(((p < 0.5) & (y == 1)).sum()),
                     "avances perdues": int(((p > 0.5) & (y == 0)).sum())})
    return pd.DataFrame(rows)


def explain_minute(model, table, minute, sign=1, top=6):
    """Pourquoi la probabilité vaut ce qu'elle vaut à `minute` : base, puis chaque variable.

    Même présentation que explain_game() à l'étape 14 (les plus grosses contributions,
    les autres regroupées), mais vue de l'équipe `sign` et avec la valeur de la variable.
    """
    row = table[table[TIME] == minute]
    contrib, base = contributions(model, row)
    c, b = contrib.iloc[0] * sign, float(base.iloc[0]) * sign
    order = c.abs().sort_values(ascending=False).index
    main, rest = c[order[:top]], c[order[top:]].sum()
    out = pd.DataFrame({"variable": [LABELS[v] for v in main.index] + ["autres variables"],
                        "valeur": list(row[main.index].iloc[0] * sign) + [np.nan],
                        "contribution": list(main) + [rest]})
    out["probabilité après"] = expit(b + out["contribution"].cumsum())
    return out, float(expit(b)), float(expit(b + c.sum()))


def main():
    parser = argparse.ArgumentParser(description="Modèle de l'appli (logistique par minute)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("train", help="entraîne et enregistre data/app_model.joblib (base nécessaire)")
    c = sub.add_parser("check", help="compare les variables JSON / base sur data/raw")
    c.add_argument("--n", type=int, default=200, help="nombre de parties comparées")
    args = parser.parse_args()
    if args.command == "train":
        train()
    else:
        check(args.n)


if __name__ == "__main__":
    main()
