"""Variables (features) de l'état d'une partie à 15 min, pour les modèles de victoire.

Ce module sert à deux choses :
1. build_features() lit la base PostgreSQL et renvoie un DataFrame avec UNE LIGNE
   PAR PARTIE, vue du côté bleu : écarts bleu − rouge à la minute 15 (or, XP, CS,
   kills, tours, plaques, dragons, hérauts, larves, premiers objectifs, or par poste),
   la cible blue_win et quelques colonnes d'information (patch, durée, champions).
2. fit_scaling() / add_scaling() ajoutent le score de « scaling » des compositions :
   une note par champion (gagne-t-il plus souvent dans les parties longues que dans
   les courtes ?), apprise UNIQUEMENT sur les parties d'entraînement, puis sommée
   par équipe.

Les notebooks et l'étape 13 (régression logistique vs LightGBM) importent ce module :
    from features import build_features, fit_scaling, add_scaling, FEATURES

Lancé seul, il construit le jeu de données, fait des contrôles et montre le score
de scaling sur un découpage chronologique 80 % / 20 % :
    python src/features.py
"""

import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Les listes de colonnes : qui a le droit d'entrer dans un modèle ?
# ---------------------------------------------------------------------------
TARGET = "blue_win"

# État de la partie à la minute 15, toujours en écart bleu − rouge.
FEATURES = [
    "gold_k",        # écart d'or total, en milliers
    "xp_k",          # écart d'XP, en milliers
    "cs_diff",       # écart de sbires + monstres de la jungle
    "kills_diff",
    "towers_diff",   # tours seulement (pas les inhibiteurs)
    "plates_diff",
    "dragons_diff",
    # Pas de héraut : aucun n'est tué avant 15 min dans les 4 762 parties
    # (colonne toujours à 0 au premier lancement, 2 nov. 2026), donc inutile.
    "grubs_diff",    # larves du Néant (HORDE)
    "first_blood",   # +1 bleu, -1 rouge, 0 personne (avant la minute 15)
    "first_tower",
    "first_dragon",
]

# Écart d'or par poste (TOP, JUNGLE...). Leur somme ≈ gold_k : à ne pas mettre
# avec gold_k dans une régression logistique (colinéarité), utile pour LightGBM.
ROLE_FEATURES = ["gold_top_k", "gold_jungle_k", "gold_mid_k", "gold_bot_k", "gold_support_k"]

# Ajoutées par add_scaling(), jamais par build_features().
SCALING_FEATURES = ["scaling_diff", "gold_x_scaling"]

# Colonnes d'information, PAS des variables du modèle :
# - duration_min est connue seulement à la fin de la partie (fuite d'information) ;
#   elle ne sert qu'à apprendre le score de scaling sur les parties d'entraînement ;
# - game_creation sert au découpage chronologique, patch aux contrôles ;
# - blue_champs / red_champs servent au score de scaling.
INFO_COLUMNS = ["match_id", "game_creation", "patch", "duration_min", "blue_champs", "red_champs"]

SCALING_PRIOR = 20  # force du lissage : « 20 parties imaginaires à 50 % » par champion


# ---------------------------------------------------------------------------
# 1. Lecture de la base
# ---------------------------------------------------------------------------
FEATURES_SQL = """
WITH frames AS (
    -- État des 10 joueurs à la minute choisie, en écarts bleu − rouge.
    SELECT f.match_id,
           sum(s.sign * f.total_gold) AS gold_diff,
           sum(s.sign * f.xp) AS xp_diff,
           sum(s.sign * (f.minions_killed + f.jungle_minions_killed)) AS cs_diff,
           sum(s.sign * f.total_gold) FILTER (WHERE p.team_position = 'TOP')     AS gold_top,
           sum(s.sign * f.total_gold) FILTER (WHERE p.team_position = 'JUNGLE')  AS gold_jungle,
           sum(s.sign * f.total_gold) FILTER (WHERE p.team_position = 'MIDDLE')  AS gold_mid,
           sum(s.sign * f.total_gold) FILTER (WHERE p.team_position = 'BOTTOM')  AS gold_bot,
           sum(s.sign * f.total_gold) FILTER (WHERE p.team_position = 'UTILITY') AS gold_support
    FROM participant_frames f
    JOIN participants p USING (match_id, participant_id)
    CROSS JOIN LATERAL (SELECT CASE WHEN p.team_id = 100 THEN 1 ELSE -1 END AS sign) s
    WHERE f.minute = %(minute)s
    GROUP BY f.match_id
    HAVING count(*) = 10
),
ev AS (
    -- Objectifs pris AVANT la minute choisie, avec +1 pour le bleu et -1 pour le rouge.
    SELECT match_id, event_type, monster_type, building_type, timestamp_ms,
           CASE WHEN killer_team_id = 100 THEN 1 ELSE -1 END AS sign,
           CASE WHEN event_type = 'CHAMPION_KILL' THEN 'blood'
                WHEN building_type = 'TOWER_BUILDING' THEN 'tower'
                WHEN monster_type = 'DRAGON' THEN 'dragon' END AS first_kind
    FROM events
    WHERE timestamp_ms < %(cutoff_ms)s
      AND killer_team_id IS NOT NULL
),
counts AS (
    SELECT match_id,
           sum(sign) FILTER (WHERE event_type = 'CHAMPION_KILL')          AS kills_diff,
           sum(sign) FILTER (WHERE building_type = 'TOWER_BUILDING')      AS towers_diff,
           sum(sign) FILTER (WHERE event_type = 'TURRET_PLATE_DESTROYED') AS plates_diff,
           sum(sign) FILTER (WHERE monster_type = 'DRAGON')               AS dragons_diff,
           sum(sign) FILTER (WHERE monster_type = 'HORDE')                AS grubs_diff
    FROM ev
    GROUP BY match_id
),
firsts AS (
    -- DISTINCT ON garde la 1re ligne de chaque (partie, type) : l'event le plus tôt.
    SELECT match_id,
           max(sign) FILTER (WHERE first_kind = 'blood')  AS first_blood,
           max(sign) FILTER (WHERE first_kind = 'tower')  AS first_tower,
           max(sign) FILTER (WHERE first_kind = 'dragon') AS first_dragon
    FROM (SELECT DISTINCT ON (match_id, first_kind) match_id, first_kind, sign
          FROM ev
          WHERE first_kind IS NOT NULL
          ORDER BY match_id, first_kind, timestamp_ms) x
    GROUP BY match_id
),
champs AS (
    SELECT match_id,
           array_agg(champion_name ORDER BY participant_id) FILTER (WHERE team_id = 100) AS blue_champs,
           array_agg(champion_name ORDER BY participant_id) FILTER (WHERE team_id = 200) AS red_champs
    FROM participants
    GROUP BY match_id
)
SELECT m.match_id,
       m.game_creation,
       split_part(m.game_version, '.', 1) || '.' || split_part(m.game_version, '.', 2) AS patch,
       m.game_duration_s / 60.0 AS duration_min,
       c.blue_champs, c.red_champs,
       f.gold_diff, f.xp_diff, f.cs_diff,
       f.gold_top, f.gold_jungle, f.gold_mid, f.gold_bot, f.gold_support,
       coalesce(n.kills_diff, 0)   AS kills_diff,
       coalesce(n.towers_diff, 0)  AS towers_diff,
       coalesce(n.plates_diff, 0)  AS plates_diff,
       coalesce(n.dragons_diff, 0) AS dragons_diff,
       coalesce(n.grubs_diff, 0)   AS grubs_diff,
       coalesce(fi.first_blood, 0)  AS first_blood,
       coalesce(fi.first_tower, 0)  AS first_tower,
       coalesce(fi.first_dragon, 0) AS first_dragon,
       t.win::int AS blue_win
FROM frames f
JOIN matches m USING (match_id)
JOIN teams t ON t.match_id = f.match_id AND t.team_id = 100
JOIN champs c ON c.match_id = f.match_id
LEFT JOIN counts n ON n.match_id = f.match_id
LEFT JOIN firsts fi ON fi.match_id = f.match_id
WHERE split_part(m.game_version, '.', 1) = '16'
  AND split_part(m.game_version, '.', 2)::int BETWEEN %(patch_min)s AND %(patch_max)s
ORDER BY m.game_creation
"""


def database_url():
    """Lit DATABASE_URL dans le fichier .env à la racine du projet."""
    load_dotenv(ROOT / ".env")
    return os.environ["DATABASE_URL"]


def build_features(minute=15, patch_min=14, patch_max=21, url=None):
    """Une ligne par partie (vue du bleu) : état à `minute`, cible et colonnes d'information.

    Seules les parties qui ont une frame à `minute` et un patch 16.<patch_min> à
    16.<patch_max> sont gardées. Les lignes sont triées par date de la partie.
    """
    params = {"minute": minute, "cutoff_ms": minute * 60_000,
              "patch_min": patch_min, "patch_max": patch_max}
    with psycopg.connect(url or database_url()) as conn:
        cur = conn.execute(FEATURES_SQL, params)
        columns = [col.name for col in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)

    # PostgreSQL renvoie des sommes en Decimal : on repasse en nombres ordinaires.
    raw = ["gold_diff", "xp_diff", "gold_top", "gold_jungle", "gold_mid", "gold_bot",
           "gold_support"]
    counts = ["cs_diff", "kills_diff", "towers_diff", "plates_diff", "dragons_diff",
              "grubs_diff", "first_blood", "first_tower", "first_dragon",
              "blue_win"]
    df[raw] = df[raw].astype(float)
    df[counts] = df[counts].astype(int)
    df["duration_min"] = df["duration_min"].astype(float)

    # Or et XP en milliers : un coefficient « pour 1 000 or » se lit directement.
    df["gold_k"] = df["gold_diff"] / 1000
    df["xp_k"] = df["xp_diff"] / 1000
    for role in ["top", "jungle", "mid", "bot", "support"]:
        # Poste inconnu (joueur AFK) -> écart 0 pour ce poste.
        df[f"gold_{role}_k"] = df[f"gold_{role}"].fillna(0) / 1000

    return df[INFO_COLUMNS + FEATURES + ROLE_FEATURES + [TARGET]].reset_index(drop=True)


def time_split(df, test_frac=0.2):
    """Découpage chronologique : les parties les plus récentes vont dans le test."""
    df = df.sort_values("game_creation").reset_index(drop=True)
    cut = int(len(df) * (1 - test_frac))
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


# ---------------------------------------------------------------------------
# 2. Score de scaling des compositions
# ---------------------------------------------------------------------------
def champion_rows(df):
    """Format long : une ligne par (partie, champion), avec la victoire de SON équipe."""
    blue = df[["blue_champs", "duration_min", "blue_win"]].explode("blue_champs")
    blue.columns = ["champion", "duration_min", "win"]
    red = df[["red_champs", "duration_min", "blue_win"]].explode("red_champs")
    red.columns = ["champion", "duration_min", "win"]
    red["win"] = 1 - red["win"]
    return pd.concat([blue, red], ignore_index=True)


def fit_scaling(train, prior=SCALING_PRIOR):
    """Apprend une note de scaling par champion, sur les parties d'ENTRAÎNEMENT seulement.

    Note = taux de victoire dans les parties longues − taux dans les parties courtes,
    en points de pourcentage. « Longue » = durée >= médiane des parties d'entraînement.
    Chaque taux est lissé vers 50 % (comme si chaque champion avait `prior` parties
    de plus, moitié gagnées) : un champion joué 15 fois ne reçoit pas une note extrême
    par hasard.

    Renvoie une Series : index = nom du champion, valeur = note (ex. +4.2).
    """
    rows = champion_rows(train)
    rows["late"] = rows["duration_min"] >= train["duration_min"].median()
    stats = rows.groupby(["champion", "late"])["win"].agg(["sum", "count"])
    stats = stats.unstack("late", fill_value=0)

    def smoothed_rate(late):
        wins, games = stats[("sum", late)], stats[("count", late)]
        return (wins + prior * 0.5) / (games + prior)

    score = 100 * (smoothed_rate(True) - smoothed_rate(False))
    return score.rename("scaling").sort_values(ascending=False)


def add_scaling(df, scores):
    """Ajoute les colonnes de scaling à un jeu de parties, avec des notes déjà apprises.

    Un champion absent de l'entraînement reçoit 0 (« ni scaling ni early »).
    """
    def team_score(champs):
        return sum(scores.get(c, 0.0) for c in champs)

    out = df.copy()
    out["blue_scaling"] = out["blue_champs"].map(team_score)
    out["red_scaling"] = out["red_champs"].map(team_score)
    out["scaling_diff"] = out["blue_scaling"] - out["red_scaling"]
    # Interaction : l'effet de l'or dépend-il de l'écart de scaling ?
    out["gold_x_scaling"] = out["gold_k"] * out["scaling_diff"]
    return out


# ---------------------------------------------------------------------------
# 3. Lancement direct : contrôles et démonstration
# ---------------------------------------------------------------------------
def check(label, ok, detail=""):
    print(f"  [{'OK' if ok else 'ATTENTION'}] {label}{' : ' + detail if detail else ''}")
    return ok


def run_checks(df):
    print("\nContrôles :")
    check("Une ligne par partie", df["match_id"].is_unique)
    missing = int(df[FEATURES + ROLE_FEATURES + [TARGET]].isna().sum().sum())
    check("Aucune valeur manquante dans les variables", missing == 0,
          f"{missing} manquantes" if missing else "")
    five = df["blue_champs"].map(len).eq(5).all() and df["red_champs"].map(len).eq(5).all()
    check("5 champions par équipe", bool(five))
    roles_sum = df[ROLE_FEATURES].sum(axis=1)
    gap = (roles_sum - df["gold_k"]).abs()
    n_gap = int((gap > 1e-9).sum())
    check("Somme de l'or par poste = or total", n_gap <= 5,
          f"{n_gap} parties avec un poste inconnu" if n_gap else "")
    check("Variables first_* dans {-1, 0, 1}",
          bool(df[["first_blood", "first_tower", "first_dragon"]].isin([-1, 0, 1]).all().all()))


def win_rate_of_higher_scaling(df):
    """% de parties gagnées par l'équipe qui a le meilleur score de scaling."""
    decided = df[df["scaling_diff"] != 0]
    blue_higher = decided["scaling_diff"] > 0
    return (blue_higher == decided["blue_win"].astype(bool)).mean()


def scaling_demo(df):
    train, test = time_split(df)
    print(f"\nScore de scaling (découpage chronologique) : {len(train)} parties "
          f"d'entraînement, {len(test)} de test (les plus récentes).")
    scores = fit_scaling(train)
    print("\n10 champions qui scalent le plus (points de victoire, longues − courtes) :")
    print(scores.head(10).round(1).to_string())
    print("\n10 champions les plus « early » :")
    print(scores.tail(10).round(1).to_string())

    test_champs = set(champion_rows(test)["champion"])
    unseen = test_champs - set(scores.index)
    print(f"\nChampions du test absents de l'entraînement : {len(unseen)} (note 0).")

    # Même mesure avec des notes apprises proprement (sans le test) et avec fuite
    # (notes apprises sur TOUTES les parties, test compris).
    long_game = test["duration_min"] >= train["duration_min"].median()
    table = {}
    for label, notes in [("entraînement seul", scores), ("avec le test (FUITE)", fit_scaling(df))]:
        scored = add_scaling(test, notes)
        table[label] = {
            "parties longues": win_rate_of_higher_scaling(scored[long_game]),
            "parties courtes": win_rate_of_higher_scaling(scored[~long_game]),
        }
    print("\nVictoires de l'équipe à la compo la plus « scaling », sur le test,")
    print("selon les parties qui ont servi à apprendre les notes :")
    print(pd.DataFrame(table).T.map("{:.1%}".format).to_string())
    print("Avec fuite, l'écart entre parties longues et courtes paraît plus grand :")
    print("les notes ont « vu » les résultats qu'on prétend prédire.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--minute", type=int, default=15, help="minute de l'état (15 par défaut)")
    args = parser.parse_args()

    df = build_features(minute=args.minute)
    print(f"{len(df)} parties (patchs 16.14 à 16.21, avec une minute {args.minute}).")
    print(f"Victoires du bleu : {df[TARGET].mean():.1%}")
    run_checks(df)

    print("\nVariables (moyenne, écart type, min, max) :")
    summary = df[FEATURES + ROLE_FEATURES].describe().T[["mean", "std", "min", "max"]]
    print(summary.round(2).to_string())

    print("\nCorrélation avec la victoire du bleu :")
    corr = df[FEATURES + ROLE_FEATURES].corrwith(df[TARGET]).sort_values(ascending=False)
    print(corr.round(2).to_string())

    scaling_demo(df)


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    main()
