"""Collecte de parties classées (match + timeline) en fichiers JSON compressés.

Principe « boule de neige » : on part d'un joueur (Riot ID), on télécharge
ses dernières parties classées, puis on ajoute à la file d'attente les
9 autres joueurs de chaque partie, et ainsi de suite.

Reprise : un fichier déjà téléchargé n'est jamais redemandé, et les joueurs
déjà parcourus sont notés dans data/raw/players_done.txt. Si le script
s'arrête (Ctrl+C, coupure, clé expirée), il suffit de le relancer.

Exemple :
    python src/collect.py --riot-id "TECHNIQUEMENT#99999" --max-matches 20
"""

import argparse
import gzip
import json
import os
import time
from collections import deque
from pathlib import Path

from dotenv import load_dotenv

from riot_api import RiotClient, RiotKeyError

RANKED_SOLO = 420  # queueId des parties classées Solo/Duo

RAW = Path("data/raw")
MATCH_DIR = RAW / "matches"
TIMELINE_DIR = RAW / "timelines"
PLAYERS_DONE = RAW / "players_done.txt"


def save_json_gz(obj, path):
    """Écrit d'abord un fichier .tmp puis le renomme : jamais de fichier à moitié écrit."""
    tmp = path.with_name(path.name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load_json_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def match_path(match_id):
    return MATCH_DIR / f"{match_id}.json.gz"


def timeline_path(match_id):
    return TIMELINE_DIR / f"{match_id}.json.gz"


def is_done(match_id):
    return match_path(match_id).exists() and timeline_path(match_id).exists()


def count_done():
    return sum(1 for p in MATCH_DIR.glob("*.json.gz") if timeline_path(p.name[:-8]).exists())


def load_state(seed_puuid):
    """Reconstruit la file d'attente des joueurs à partir de ce qui est déjà sur le disque."""
    done = set()
    if PLAYERS_DONE.exists():
        done = set(PLAYERS_DONE.read_text(encoding="utf-8").split())

    queue, seen = deque(), set(done)
    for puuid in [seed_puuid] + [
        p for f in sorted(MATCH_DIR.glob("*.json.gz"))
        for p in load_json_gz(f)["metadata"]["participants"]
    ]:
        if puuid not in seen:
            seen.add(puuid)
            queue.append(puuid)
    return queue, seen


def mark_player_done(puuid):
    with open(PLAYERS_DONE, "a", encoding="utf-8") as f:
        f.write(puuid + "\n")


def download_match(client, match_id):
    """Télécharge match + timeline. Renvoie le JSON du match, ou None si introuvable."""
    match = load_json_gz(match_path(match_id)) if match_path(match_id).exists() else None
    if match is None:
        match = client.get(f"/lol/match/v5/matches/{match_id}")
        if match is None:
            return None
        save_json_gz(match, match_path(match_id))
    if not timeline_path(match_id).exists():
        timeline = client.get(f"/lol/match/v5/matches/{match_id}/timeline")
        if timeline is None:
            return None
        save_json_gz(timeline, timeline_path(match_id))
    return match


def main():
    parser = argparse.ArgumentParser(description="Collecte de parties classées LoL")
    parser.add_argument("--riot-id", required=True, help='ex. "TECHNIQUEMENT#99999"')
    parser.add_argument("--max-matches", type=int, default=20,
                        help="nombre total de parties à avoir sur le disque")
    parser.add_argument("--per-player", type=int, default=20,
                        help="nombre de parties récentes demandées par joueur")
    args = parser.parse_args()

    load_dotenv()
    client = RiotClient(os.environ.get("RIOT_API_KEY"), os.environ.get("RIOT_REGION", "europe"))

    MATCH_DIR.mkdir(parents=True, exist_ok=True)
    TIMELINE_DIR.mkdir(parents=True, exist_ok=True)

    name, tag = args.riot_id.split("#")
    try:
        account = client.get(f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}")
    except RiotKeyError as e:
        raise SystemExit(str(e))
    if account is None:
        raise SystemExit(f"Riot ID introuvable : {args.riot_id}")

    queue, seen = load_state(account["puuid"])
    total = count_done()
    print(f"Déjà sur le disque : {total} parties. Joueurs en attente : {len(queue)}")
    start = time.monotonic()
    interrupted = False
    missing = set()  # parties introuvables (404) pendant cette séance

    try:
        while queue and total < args.max_matches:
            puuid = queue.popleft()
            ids = client.get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
                             queue=RANKED_SOLO, start=0, count=args.per_player) or []
            print(f"Joueur {puuid[:8]}… : {len(ids)} parties classées")

            for match_id in ids:
                if total >= args.max_matches:
                    break
                if is_done(match_id):
                    continue
                match = download_match(client, match_id)
                if match is None:
                    print(f"  {match_id} introuvable (404), ignorée")
                    missing.add(match_id)
                    continue
                total += 1
                minutes = (time.monotonic() - start) / 60
                print(f"  [{total}/{args.max_matches}] {match_id} enregistrée ({minutes:.1f} min)")
                for p in match["metadata"]["participants"]:
                    if p not in seen:
                        seen.add(p)
                        queue.append(p)

            # Joueur terminé seulement si toutes ses parties sont sur le disque
            # (sinon on s'est arrêté au milieu : il sera repris la prochaine fois).
            if all(is_done(m) or m in missing for m in ids):
                mark_player_done(puuid)
    except KeyboardInterrupt:
        interrupted = True
        print("\nArrêt demandé (Ctrl+C). Relance la même commande pour reprendre.")
    except RiotKeyError as e:
        interrupted = True
        print(f"\n{e}\nRelance ensuite la même commande : la collecte reprendra où elle s'est arrêtée.")

    if not queue and not interrupted:
        print("Plus aucun joueur à explorer : tout ce qui était accessible a été collecté.")
    print(f"Terminé : {count_done()} parties complètes dans {RAW}")


if __name__ == "__main__":
    main()
