"""Insertion des parties brutes (data/raw) dans PostgreSQL.

Pour chaque partie sur le disque (match + timeline) :
  1. on saute celles qui sont déjà en base (relancer le script ne crée pas de doublons) ;
  2. on vérifie la partie (contrôles qualité) : une partie refusée n'est pas insérée,
     et la raison est affichée ;
  3. on remplit les 7 tables de sql/schema.sql dans UNE transaction :
     soit toute la partie est insérée, soit rien (jamais de partie à moitié en base).

La base doit tourner (Docker Desktop ouvert + docker compose start).

Exemples :
    python src/load.py --limit 5     # seulement 5 parties, pour tester
    python src/load.py               # toutes les parties de data/raw
"""

import argparse
import os
from collections import Counter
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from collect import MATCH_DIR, RANKED_SOLO, load_json_gz, timeline_path

# Les seuls events gardés (même liste que la contrainte CHECK de la table events).
EVENT_TYPES = {"CHAMPION_KILL", "ELITE_MONSTER_KILL", "BUILDING_KILL", "TURRET_PLATE_DESTROYED"}

REMAKE_MAX_S = 5 * 60  # une partie de moins de 5 min est un remake


# ---------------------------------------------------------------------
# Contrôles qualité AVANT insertion
# ---------------------------------------------------------------------
def check_match(match, timeline):
    """Renvoie None si la partie est bonne, sinon la raison du refus (texte)."""
    info = match["info"]
    participants = info.get("participants", [])

    if timeline["metadata"]["matchId"] != match["metadata"]["matchId"]:
        return "la timeline ne correspond pas au match"
    if info.get("queueId") != RANKED_SOLO:
        return f"pas une partie classée solo/duo (queueId {info.get('queueId')})"
    if any(p.get("gameEndedInEarlySurrender") for p in participants) or info["gameDuration"] < REMAKE_MAX_S:
        return f"remake ({info['gameDuration']} s)"
    if [p["participantId"] for p in participants] != list(range(1, 11)):
        return "il n'y a pas exactement 10 joueurs numérotés de 1 à 10"
    if Counter(p["teamId"] for p in participants) != {100: 5, 200: 5}:
        return "les équipes ne font pas 5 joueurs chacune"
    if sorted(t["win"] for t in info["teams"]) != [False, True]:
        return "il n'y a pas exactement une équipe gagnante"

    # Le participantId de la timeline doit désigner le même joueur que dans le match.
    puuid_match = {p["participantId"]: p["puuid"] for p in participants}
    puuid_timeline = {p["participantId"]: p["puuid"] for p in timeline["info"]["participants"]}
    if puuid_match != puuid_timeline:
        return "les participantId de la timeline ne correspondent pas au match"

    # Valeurs obligatoires (NOT NULL dans le schéma) : si l'une manque, on refuse.
    for p in participants:
        for key in ("puuid", "championId", "championName", "kills", "deaths", "assists"):
            if p.get(key) is None:
                return f"valeur manquante : {key} (joueur {p['participantId']})"
    for minute, frame in enumerate(timeline["info"]["frames"]):
        for pid in range(1, 11):
            pf = frame["participantFrames"].get(str(pid))
            if pf is None or any(pf.get(k) is None for k in ("totalGold", "xp", "level")):
                return f"frame incomplète : minute {minute}, joueur {pid}"
    return None


# ---------------------------------------------------------------------
# Insertion d'une partie dans les 7 tables
# ---------------------------------------------------------------------
def insert_match(cur, match, timeline):
    info = match["info"]
    match_id = match["metadata"]["matchId"]
    team_of = {p["participantId"]: p["teamId"] for p in info["participants"]}

    # 1. matches
    cur.execute(
        """INSERT INTO matches (match_id, platform_id, queue_id, game_version,
                                game_creation, game_duration_s, end_of_game_result)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (match_id, info["platformId"], info["queueId"], info["gameVersion"],
         datetime.fromtimestamp(info["gameCreation"] / 1000, tz=timezone.utc),
         info["gameDuration"], info.get("endOfGameResult")),
    )

    # 2. teams
    for t in info["teams"]:
        obj = t.get("objectives", {})

        def first(name):
            return obj.get(name, {}).get("first")

        def kills(name):
            return obj.get(name, {}).get("kills")

        cur.execute(
            """INSERT INTO teams (match_id, team_id, win,
                                 first_blood, first_tower, first_dragon, first_baron,
                                 champion_kills, tower_kills, inhibitor_kills, dragon_kills,
                                 rift_herald_kills, horde_kills, baron_kills)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (match_id, t["teamId"], t["win"],
             first("champion"), first("tower"), first("dragon"), first("baron"),
             kills("champion"), kills("tower"), kills("inhibitor"), kills("dragon"),
             kills("riftHerald"), kills("horde"), kills("baron")),
        )

    # 3. players (un joueur peut déjà être en base grâce à une autre partie)
    cur.executemany(
        "INSERT INTO players (puuid) VALUES (%s) ON CONFLICT DO NOTHING",
        [(p["puuid"],) for p in info["participants"]],
    )

    # 4. participants
    cur.executemany(
        """INSERT INTO participants (match_id, participant_id, team_id, puuid,
                                     champion_id, champion_name, team_position, champ_level,
                                     kills, deaths, assists, gold_earned,
                                     total_minions_killed, neutral_minions_killed,
                                     vision_score, damage_to_champions)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [(match_id, p["participantId"], p["teamId"], p["puuid"],
          p["championId"], p["championName"],
          p.get("teamPosition") or None,  # Riot met "" quand le poste est inconnu
          p.get("champLevel"), p["kills"], p["deaths"], p["assists"],
          p.get("goldEarned"), p.get("totalMinionsKilled"), p.get("neutralMinionsKilled"),
          p.get("visionScore"), p.get("totalDamageDealtToChampions"))
         for p in info["participants"]],
    )

    # 5. participant_frames : 10 lignes par minute
    rows = []
    for minute, frame in enumerate(timeline["info"]["frames"]):
        for pid in range(1, 11):
            pf = frame["participantFrames"][str(pid)]
            pos = pf.get("position", {})
            rows.append((match_id, pid, minute, frame["timestamp"],
                         pf["totalGold"], pf["xp"], pf["level"],
                         pf.get("minionsKilled", 0), pf.get("jungleMinionsKilled", 0),
                         pos.get("x"), pos.get("y")))
    cur.executemany(
        """INSERT INTO participant_frames (match_id, participant_id, minute, timestamp_ms,
                                           total_gold, xp, level, minions_killed,
                                           jungle_minions_killed, position_x, position_y)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        rows,
    )

    # 6. events (+ 7. event_assists)
    for minute, frame in enumerate(timeline["info"]["frames"]):
        for e in frame["events"]:
            if e["type"] not in EVENT_TYPES:
                continue
            killer = e.get("killerId") or None  # 0 = tour, sbire ou monstre -> NULL
            victim = e.get("victimId") or None
            killer_team = event_team(e, killer, victim, team_of)
            pos = e.get("position", {})
            cur.execute(
                """INSERT INTO events (match_id, minute, timestamp_ms, event_type,
                                       killer_id, victim_id, killer_team_id,
                                       monster_type, monster_sub_type, building_type,
                                       tower_type, lane_type, position_x, position_y)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING event_id""",
                (match_id, minute, e["timestamp"], e["type"], killer, victim, killer_team,
                 e.get("monsterType"), e.get("monsterSubType"), e.get("buildingType"),
                 e.get("towerType"), e.get("laneType"), pos.get("x"), pos.get("y")),
            )
            event_id = cur.fetchone()[0]
            assists = sorted(set(e.get("assistingParticipantIds", [])))
            if assists:
                cur.executemany(
                    "INSERT INTO event_assists (event_id, participant_id) VALUES (%s, %s)",
                    [(event_id, pid) for pid in assists],
                )


def event_team(e, killer, victim, team_of):
    """L'équipe qui GAGNE l'event (voir le commentaire de la table events dans schema.sql)."""
    if e["type"] == "CHAMPION_KILL":
        if killer:
            return team_of[killer]
        return 300 - team_of[victim]          # exécution : l'équipe adverse de la victime
    if e["type"] == "ELITE_MONSTER_KILL":
        team = e.get("killerTeamId")
        return team if team in (100, 200) else None  # 300 = monstre mort sans équipe
    return 300 - e["teamId"]                  # bâtiment / plaque : teamId = équipe qui PERD


# ---------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Insère les parties de data/raw dans PostgreSQL")
    parser.add_argument("--limit", type=int, default=None,
                        help="nombre maximum de NOUVELLES parties à insérer (pour tester)")
    args = parser.parse_args()

    load_dotenv()
    try:
        # autocommit : chaque partie est validée dès qu'elle est insérée
        # (un Ctrl+C ne fait perdre que la partie en cours).
        conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
    except psycopg.OperationalError as e:
        raise SystemExit(f"Connexion à la base impossible : Docker Desktop est-il ouvert, "
                         f"et as-tu lancé « docker compose start » ?\n{e}")

    with conn:
        in_db = {row[0] for row in conn.execute("SELECT match_id FROM matches")}
        files = sorted(MATCH_DIR.glob("*.json.gz"))
        print(f"{len(files)} parties sur le disque, {len(in_db)} déjà en base.")

        inserted, already, rejected, errors = 0, 0, Counter(), 0
        for path in files:
            match_id = path.name[:-len(".json.gz")]
            if match_id in in_db:
                already += 1
                continue
            if not timeline_path(match_id).exists():
                rejected["timeline absente"] += 1
                print(f"  {match_id} refusée : timeline absente")
                continue
            if args.limit is not None and inserted >= args.limit:
                break

            match = load_json_gz(path)
            timeline = load_json_gz(timeline_path(match_id))
            reason = check_match(match, timeline)
            if reason:
                rejected[reason.split(" (")[0]] += 1
                print(f"  {match_id} refusée : {reason}")
                continue

            try:
                with conn.transaction():          # tout ou rien pour cette partie
                    with conn.cursor() as cur:
                        insert_match(cur, match, timeline)
            except psycopg.Error as e:
                errors += 1
                print(f"  {match_id} ERREUR, partie non insérée : {e}")
                continue
            inserted += 1
            print(f"  [{inserted}] {match_id} insérée")

    print(f"\nBilan : {inserted} insérées, {already} déjà en base, "
          f"{sum(rejected.values())} refusées, {errors} erreurs.")
    for reason, n in rejected.most_common():
        print(f"  refusées pour « {reason} » : {n}")


if __name__ == "__main__":
    main()
