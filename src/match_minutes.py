"""L'état d'une partie minute par minute, calculé de la MÊME façon depuis la base ou le JSON.

Pourquoi ce module ? L'appli Streamlit (étape 18) analyse des parties qui ne sont PAS
dans la base : elle les télécharge à la demande (JSON match + timeline de l'API Riot).
Le modèle, lui, a été entraîné sur des variables calculées depuis la base (étape 17).
Si les deux calculs différaient d'un rien (un event compté une minute trop tôt, un
signe inversé), le modèle recevrait en service des variables qu'il n'a jamais vues
à l'entraînement, sans aucun message d'erreur. Pour l'éviter :
- minute_table() est LE calcul des variables par minute, à partir de deux petits
  tableaux (frames et events). sequences.build_minute_features() (la base) et
  minute_features() (le JSON) l'appellent tous les deux ;
- frames_from_json() et events_from_json() fabriquent depuis le JSON exactement les
  tableaux que FRAMES_SQL et EVENTS_SQL (sequences.py) lisent dans la base, avec les
  mêmes règles que load.py (équipe qui gagne l'event, frame de fin retirée...) ;
- un test compare les deux chemins sur des parties réelles (écart attendu : 0).

Le module ne dépend ni de PyTorch ni de la base : l'appli le charge vite.

Il fournit aussi ce que l'appli affiche autour de la courbe : les events d'une
minute en texte lisible (readable_events) et le résumé d'une partie (game_summary).
"""

import numpy as np
import pandas as pd

from features import FEATURES
from load import EVENT_TYPES, event_team

# ---------------------------------------------------------------------------
# Les colonnes (déplacées depuis sequences.py, qui les réexporte)
# ---------------------------------------------------------------------------
# Les 11 variables de l'étape 12, plus ce qui compte surtout après 15 min.
LATE_FEATURES = [
    "heralds_diff",      # héraut de la faille (apparaît vers 14-16 min)
    "barons_diff",       # baron Nashor (à partir de 20 min)
    "elders_diff",       # dragon ancestral (après 4 dragons d'une équipe) ; pas dans dragons_diff
    "inhibs_diff",       # inhibiteurs détruits
    "kills_1min_diff",   # kills de la DERNIÈRE minute : qui est en surnombre en ce moment
]
SEQ_FEATURES = FEATURES + LATE_FEATURES
TIME = "minute"
MAX_MINUTE = 60          # au-delà, les parties sont coupées (très rares)

EVENT_KINDS = ["kills", "towers", "inhibs", "plates", "dragons", "elders", "grubs",
               "heralds", "barons"]
FIRSTS = {"first_blood": "kills", "first_tower": "towers", "first_dragon": "dragons"}

FRAME_COLUMNS = ["match_id", "minute", "gold_diff", "xp_diff", "cs_diff"]
EVENT_COLUMNS = ["match_id", "timestamp_ms", "sign", "kind"]


# ---------------------------------------------------------------------------
# 1. LE calcul des variables par minute (commun à la base et au JSON)
# ---------------------------------------------------------------------------
def minute_table(frames, events):
    """Une ligne par (partie, minute) : les SEQ_FEATURES en écarts bleu − rouge.

    frames : match_id, minute, gold_diff, xp_diff, cs_diff (écarts de la frame de la
             minute, dernière frame de la partie déjà retirée) ;
    events : match_id, timestamp_ms, sign (+1 bleu, −1 rouge), kind (EVENT_KINDS ou
             None pour un event qui ne compte pas).
    Renvoie match_id, minute et SEQ_FEATURES, trié par partie puis minute.
    """
    frames = frames.copy()
    events = events.copy()
    frames[["gold_diff", "xp_diff", "cs_diff"]] = frames[["gold_diff", "xp_diff",
                                                          "cs_diff"]].astype(float)
    events = events.dropna(subset=["kind"])

    # Un event compte à partir de la minute t si timestamp < t × 60 000 ms,
    # c'est-à-dire t >= « case » = timestamp // 60 000 + 1 (même règle qu'à l'étape 12).
    events["minute"] = events["timestamp_ms"] // 60_000 + 1

    # Écarts PAR minute (somme des +1 / −1 de la minute), puis cumulés depuis le début.
    per_minute = (events.groupby(["match_id", "minute", "kind"])["sign"].sum()
                  .unstack("kind", fill_value=0)
                  .reindex(columns=EVENT_KINDS, fill_value=0)
                  .reset_index())
    df = frames.merge(per_minute, on=["match_id", "minute"], how="left")
    df[EVENT_KINDS] = df[EVENT_KINDS].fillna(0).astype(int)
    df = df.sort_values(["match_id", "minute"])
    df["kills_1min_diff"] = df["kills"]                     # la minute seule, PAS cumulée
    cumulated = df.groupby("match_id")[EVENT_KINDS].cumsum()
    for kind in EVENT_KINDS:
        df[f"{kind}_diff"] = cumulated[kind]

    # Premiers objectifs : +1 / −1 à partir de la minute où ils ont eu lieu, 0 avant.
    first = events.sort_values("timestamp_ms").drop_duplicates(["match_id", "kind"])
    for col, kind in FIRSTS.items():
        f = first[first["kind"] == kind].set_index("match_id")
        when, who = df["match_id"].map(f["minute"]), df["match_id"].map(f["sign"])
        df[col] = np.where(df[TIME] >= when, who, 0).astype(int)  # NaN (jamais) -> 0

    df["gold_k"] = df["gold_diff"] / 1000
    df["xp_k"] = df["xp_diff"] / 1000
    return df[["match_id", TIME] + SEQ_FEATURES].reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Les deux tableaux d'entrée, fabriqués depuis le JSON (comme la base)
# ---------------------------------------------------------------------------
def event_kind(e):
    """Le « genre » d'un event, dans le même ordre que le CASE de EVENTS_SQL."""
    if e["type"] == "CHAMPION_KILL":
        return "kills"
    if e.get("buildingType") == "TOWER_BUILDING":
        return "towers"
    if e.get("buildingType") == "INHIBITOR_BUILDING":
        return "inhibs"
    if e["type"] == "TURRET_PLATE_DESTROYED":
        return "plates"
    if e.get("monsterSubType") == "ELDER_DRAGON":
        return "elders"
    return {"DRAGON": "dragons", "HORDE": "grubs", "RIFTHERALD": "heralds",
            "BARON_NASHOR": "barons"}.get(e.get("monsterType"))


def team_of(match):
    return {p["participantId"]: p["teamId"] for p in match["info"]["participants"]}


def frames_from_json(match, timeline, max_minute=MAX_MINUTE):
    """Comme FRAMES_SQL : écarts d'or, d'XP et de CS à chaque minute 1..max_minute,
    sans la dernière frame (l'instant exact de la fin), seulement si les 10 joueurs
    sont présents. La minute d'une frame = sa position dans la liste (comme load.py)."""
    match_id = match["metadata"]["matchId"]
    teams = team_of(match)
    frames = timeline["info"]["frames"]
    last = len(frames) - 1
    rows = []
    for minute, frame in enumerate(frames):
        if not 1 <= minute <= max_minute or minute >= last:
            continue
        pfs = frame["participantFrames"]
        if len(pfs) != 10:
            continue
        gold = xp = cs = 0
        for pid, pf in pfs.items():
            s = 1 if teams[int(pid)] == 100 else -1
            gold += s * pf["totalGold"]
            xp += s * pf["xp"]
            cs += s * (pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0))
        rows.append((match_id, minute, gold, xp, cs))
    return pd.DataFrame(rows, columns=FRAME_COLUMNS)


def events_from_json(match, timeline):
    """Comme EVENTS_SQL : un event par ligne, avec le signe de l'équipe qui le GAGNE
    (event_team de load.py : bâtiment = l'équipe qui ne le perd pas, exécution =
    l'adversaire de la victime, monstre sans équipe = ignoré)."""
    match_id = match["metadata"]["matchId"]
    teams = team_of(match)
    rows = []
    for frame in timeline["info"]["frames"]:
        for e in frame["events"]:
            if e["type"] not in EVENT_TYPES:
                continue
            team = event_team(e, e.get("killerId") or None, e.get("victimId") or None, teams)
            if team is None:
                continue
            rows.append((match_id, e["timestamp"], 1 if team == 100 else -1, event_kind(e)))
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)


def minute_features(match, timeline, max_minute=MAX_MINUTE):
    """Les variables minute par minute d'UNE partie téléchargée (sans la base)."""
    return minute_table(frames_from_json(match, timeline, max_minute),
                        events_from_json(match, timeline))


# ---------------------------------------------------------------------------
# 3. Ce que l'appli affiche autour de la courbe
# ---------------------------------------------------------------------------
BUILDING_FR = {"TOWER_BUILDING": "une tour", "INHIBITOR_BUILDING": "un inhibiteur"}
LANE_FR = {"TOP_LANE": "top", "MID_LANE": "mid", "BOT_LANE": "bot"}
MONSTER_FR = {"BARON_NASHOR": "le baron Nashor", "RIFTHERALD": "le héraut",
              "HORDE": "une larve du Néant", "ATAKHAN": "Atakhan"}


def readable_events(match, timeline):
    """Les events utiles en phrases courtes, avec la minute où le modèle les « voit ».

    Les joueurs sont désignés par leur CHAMPION et leur équipe, jamais par leur pseudo
    (règle du projet : pseudonymiser les autres joueurs). minute = timestamp // 60 000 + 1,
    la même règle que minute_table : un event de 12:34 apparaît dans l'état de la minute 13.
    """
    info = match["info"]
    champ = {p["participantId"]: p["championName"] for p in info["participants"]}
    teams = team_of(match)
    rows = []
    for frame in timeline["info"]["frames"]:
        for e in frame["events"]:
            if e["type"] not in EVENT_TYPES or e["type"] == "TURRET_PLATE_DESTROYED":
                continue  # les plaques sont trop nombreuses pour être listées une à une
            team = event_team(e, e.get("killerId") or None, e.get("victimId") or None, teams)
            if team is None:
                continue
            if e["type"] == "CHAMPION_KILL":
                killer = champ.get(e.get("killerId"), "une tour ou un sbire")
                text = f"{killer} tue {champ[e['victimId']]}"
            elif e["type"] == "BUILDING_KILL":
                what = BUILDING_FR.get(e.get("buildingType"), "un bâtiment")
                lane = LANE_FR.get(e.get("laneType"), "")
                text = f"détruit {what} {lane}".strip()
            elif e.get("monsterType") == "DRAGON":
                sub = (e.get("monsterSubType") or "").replace("_DRAGON", "").lower()
                text = ("tue le dragon ancestral" if sub == "elder"
                        else f"tue un dragon ({sub})" if sub else "tue un dragon")
            else:
                text = f"tue {MONSTER_FR.get(e.get('monsterType'), e.get('monsterType'))}"
            seconds = e["timestamp"] // 1000
            rows.append({"minute": e["timestamp"] // 60_000 + 1,
                         "time": f"{seconds // 60:02d}:{seconds % 60:02d}",
                         "team": team, "kind": event_kind(e), "text": text})
    return pd.DataFrame(rows, columns=["minute", "time", "team", "kind", "text"])


def find_participant(match, puuid):
    for p in match["info"]["participants"]:
        if p["puuid"] == puuid:
            return p
    return None


def game_summary(match, puuid):
    """Une ligne de résumé de la partie, vue du joueur cherché (None s'il n'y est pas)."""
    info = match["info"]
    me = find_participant(match, puuid)
    if me is None:
        return None
    major, minor = info["gameVersion"].split(".")[:2]
    return {"match_id": match["metadata"]["matchId"],
            "date": pd.to_datetime(info["gameCreation"], unit="ms", utc=True),
            "patch": f"{major}.{minor}",
            "duration_min": info["gameDuration"] / 60,
            "team": me["teamId"], "champion": me["championName"],
            "position": me.get("teamPosition") or "?",
            "win": bool(me["win"]),
            "kda": f"{me['kills']}/{me['deaths']}/{me['assists']}"}


def scoreboard(match, puuid):
    """Tableau de fin de partie : champions et statistiques, le joueur cherché marqué."""
    rows = []
    for p in match["info"]["participants"]:
        rows.append({"équipe": "bleue" if p["teamId"] == 100 else "rouge",
                     "champion": p["championName"] + ("  ← toi" if p["puuid"] == puuid else ""),
                     "poste": p.get("teamPosition") or "?",
                     "K/D/A": f"{p['kills']}/{p['deaths']}/{p['assists']}",
                     "or": p.get("goldEarned"),
                     "CS": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                     "dégâts": p.get("totalDamageDealtToChampions")})
    return pd.DataFrame(rows)
