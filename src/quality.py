"""Contrôles qualité APRÈS insertion : la base est-elle cohérente ?

Chaque contrôle est une requête SQL qui compte les lignes « anormales ».
0 -> OK ; plus de 0 -> ATTENTION, avec le nombre de cas à examiner.
Le script ne modifie rien dans la base : il ne fait que lire.

Exemple :
    python src/quality.py
"""

import os

import psycopg
from dotenv import load_dotenv

# (description, requête qui compte les problèmes)
CHECKS = [
    ("Chaque partie a exactement 2 équipes",
     """SELECT count(*) FROM matches m
        WHERE (SELECT count(*) FROM teams t WHERE t.match_id = m.match_id) <> 2"""),

    ("Chaque partie a exactement une équipe gagnante",
     """SELECT count(*) FROM (
            SELECT match_id FROM teams GROUP BY match_id
            HAVING count(*) FILTER (WHERE win) <> 1) x"""),

    ("Chaque partie a 10 joueurs, 5 par équipe",
     """SELECT count(*) FROM (
            SELECT match_id FROM participants GROUP BY match_id
            HAVING count(*) <> 10
                OR count(*) FILTER (WHERE team_id = 100) <> 5) x"""),

    ("Chaque minute a une frame pour les 10 joueurs (aucune minute manquante)",
     """SELECT count(*) FROM (
            SELECT match_id FROM participant_frames GROUP BY match_id
            HAVING count(*) <> 10 * (max(minute) + 1)) x"""),

    ("L'or total d'un joueur ne baisse jamais d'une minute à l'autre",
     """SELECT count(*) FROM (
            SELECT total_gold < lag(total_gold) OVER (
                       PARTITION BY match_id, participant_id ORDER BY minute) AS baisse
            FROM participant_frames) x
        WHERE baisse"""),

    ("Kills de la timeline = kills du match (par équipe, hors exécutions)",
     """WITH timeline AS (
            SELECT match_id, killer_team_id AS team_id, count(*) AS n
            FROM events
            WHERE event_type = 'CHAMPION_KILL' AND killer_id IS NOT NULL
            GROUP BY 1, 2),
        match AS (
            SELECT match_id, team_id, sum(kills) AS n
            FROM participants GROUP BY 1, 2)
        SELECT count(*) FROM match
        LEFT JOIN timeline USING (match_id, team_id)
        WHERE match.n <> coalesce(timeline.n, 0)"""),

    ("Tours détruites (timeline) = tower_kills (match)",
     """WITH timeline AS (
            SELECT match_id, killer_team_id AS team_id, count(*) AS n
            FROM events
            WHERE event_type = 'BUILDING_KILL' AND building_type = 'TOWER_BUILDING'
            GROUP BY 1, 2)
        SELECT count(*) FROM teams
        LEFT JOIN timeline USING (match_id, team_id)
        WHERE teams.tower_kills <> coalesce(timeline.n, 0)"""),

    ("Dragons (timeline) = dragon_kills (match)",
     """WITH timeline AS (
            SELECT match_id, killer_team_id AS team_id, count(*) AS n
            FROM events
            WHERE event_type = 'ELITE_MONSTER_KILL' AND monster_type = 'DRAGON'
            GROUP BY 1, 2)
        SELECT count(*) FROM teams
        LEFT JOIN timeline USING (match_id, team_id)
        WHERE teams.dragon_kills <> coalesce(timeline.n, 0)"""),

    ("Aucun poste (team_position) manquant",
     "SELECT count(*) FROM participants WHERE team_position IS NULL"),

    ("Aucune partie de moins de 5 min (remake)",
     "SELECT count(*) FROM matches WHERE game_duration_s < 300"),
]

# Chiffres à connaître, pas des erreurs.
INFOS = [
    ("Parties", "SELECT count(*) FROM matches"),
    ("Joueurs différents", "SELECT count(*) FROM players"),
    ("Lignes participant_frames", "SELECT count(*) FROM participant_frames"),
    ("Lignes events", "SELECT count(*) FROM events"),
    ("Lignes event_assists", "SELECT count(*) FROM event_assists"),
    ("Durée min / moyenne / max (min)",
     """SELECT round(min(game_duration_s) / 60.0, 1) || ' / '
            || round(avg(game_duration_s) / 60.0, 1) || ' / '
            || round(max(game_duration_s) / 60.0, 1) FROM matches"""),
    ("Parties sans minute 15 (exclues du modèle à 15 min)",
     """SELECT count(*) FROM matches m WHERE NOT EXISTS (
            SELECT 1 FROM participant_frames f
            WHERE f.match_id = m.match_id AND f.minute = 15)"""),
    ("Victoires de l'équipe bleue (100)",
     """SELECT round(100.0 * avg(win::int), 1) || ' %' FROM teams WHERE team_id = 100"""),
    ("Exécutions (kill sans tueur)",
     "SELECT count(*) FROM events WHERE event_type = 'CHAMPION_KILL' AND killer_id IS NULL"),
    ("Monstres épiques sans équipe (killerTeamId 300)",
     "SELECT count(*) FROM events WHERE event_type = 'ELITE_MONSTER_KILL' AND killer_team_id IS NULL"),
    ("Patchs", "SELECT string_agg(DISTINCT left(game_version, 5), ', ') FROM matches"),
]


def main():
    load_dotenv()
    try:
        conn = psycopg.connect(os.environ["DATABASE_URL"])
    except psycopg.OperationalError as e:
        raise SystemExit(f"Connexion à la base impossible : Docker Desktop est-il ouvert, "
                         f"et as-tu lancé « docker compose start » ?\n{e}")

    with conn:
        print("=== Chiffres ===")
        for label, sql in INFOS:
            print(f"  {label} : {conn.execute(sql).fetchone()[0]}")

        print("\n=== Contrôles ===")
        problems = 0
        for label, sql in CHECKS:
            n = conn.execute(sql).fetchone()[0]
            status = "OK" if n == 0 else f"ATTENTION : {n} cas"
            print(f"  [{status}] {label}")
            problems += n > 0

    print(f"\n{len(CHECKS) - problems}/{len(CHECKS)} contrôles OK.")


if __name__ == "__main__":
    main()
