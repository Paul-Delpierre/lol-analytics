"""Collecte de parties classées (match + timeline) en fichiers JSON compressés.

Principe « boule de neige » : on part d'un joueur (Riot ID), on télécharge
ses dernières parties classées, puis on ajoute à la file d'attente les
9 autres joueurs de chaque partie, et ainsi de suite.

Reprise : un fichier déjà téléchargé n'est jamais redemandé, et les joueurs
déjà parcourus sont notés dans data/raw/players_done.txt. Si le script
s'arrête (Ctrl+C, coupure, clé expirée), il suffit de le relancer.

Collecte en fond (plusieurs heures) : tous les messages sont aussi écrits
dans data/logs/collect.log, le PC est empêché de se mettre en veille tant
que le script tourne, et une 2e collecte lancée par erreur est refusée.

Exemple :
    python src/collect.py --riot-id "TECHNIQUEMENT#99999" --max-matches 20
"""

import argparse
import ctypes
import gzip
import json
import logging
import os
import sys
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from riot_api import RiotClient, RiotKeyError

RANKED_SOLO = 420  # queueId des parties classées Solo/Duo

RAW = Path("data/raw")
MATCH_DIR = RAW / "matches"
TIMELINE_DIR = RAW / "timelines"
PLAYERS_DONE = RAW / "players_done.txt"
LOG_FILE = Path("data/logs/collect.log")
LOCK_FILE = RAW / "collect.lock"

REPORT_EVERY = 100  # un bilan (vitesse, heure de fin estimée) toutes les 100 parties

log = logging.getLogger("collect")


# --- Journal et veille : ce qui permet de laisser tourner le script seul ---

def setup_logging():
    """Envoie les messages à l'écran ET dans data/logs/collect.log (avec l'heure)."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    to_file = logging.FileHandler(LOG_FILE, encoding="utf-8")
    to_file.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    to_screen = logging.StreamHandler(sys.stdout)
    to_screen.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[to_file, to_screen])


@contextmanager
def keep_awake():
    """Empêche la mise en veille de Windows pendant la collecte.

    SetThreadExecutionState dit à Windows « ce programme travaille » ; l'écran
    peut s'éteindre, mais pas le PC. L'effet s'arrête tout seul quand le
    script se termine (même s'il plante). Ne fait rien hors de Windows.
    """
    if sys.platform != "win32":
        yield
        return
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    kernel32 = ctypes.windll.kernel32
    kernel32.SetThreadExecutionState.argtypes = [ctypes.c_uint]  # drapeaux sur 32 bits non signés
    kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    log.info("Mise en veille du PC désactivée pendant la collecte (l'écran peut s'éteindre).")
    try:
        yield
    finally:
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)


@contextmanager
def single_instance():
    """Refuse de démarrer si une autre collecte tourne déjà dans ce dossier.

    Deux collectes en même temps écriraient les mêmes fichiers .tmp et
    planteraient. On verrouille data/raw/collect.lock auprès du système :
    le verrou disparaît tout seul quand le script s'arrête, même s'il plante
    (contrairement à un simple fichier « je tourne » qui resterait).
    """
    f = open(LOCK_FILE, "a+")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        log.error("Une collecte tourne déjà dans ce dossier (autre fenêtre ?). "
                  "Arrête-la avec Ctrl+C avant d'en lancer une autre.")
        raise SystemExit(1)
    try:
        yield
    finally:
        f.close()


# --- Fichiers bruts sur le disque ---

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


# --- Suivi de la progression ---

def report(new, total, target, start):
    """Bilan : vitesse réelle de la séance et heure de fin estimée."""
    hours = (time.monotonic() - start) / 3600
    per_hour = new / hours if hours > 0 else 0
    msg = f"Bilan : {total}/{target} parties, {new} cette séance, {per_hour:.0f} parties/h"
    if per_hour > 0 and total < target:
        end = datetime.now() + timedelta(hours=(target - total) / per_hour)
        msg += f", fin estimée vers {end:%H:%M}"
    log.info(msg)


def collect(client, seed_puuid, max_matches, per_player):
    """Parcours en largeur des joueurs. Renvoie (parties ajoutées, raison de l'arrêt)."""
    queue, seen = load_state(seed_puuid)
    total = count_done()
    log.info(f"Déjà sur le disque : {total} parties. Joueurs en attente : {len(queue)}")
    start = time.monotonic()
    new = 0
    missing = set()  # parties introuvables (404) pendant cette séance

    try:
        while queue and total < max_matches:
            puuid = queue.popleft()
            ids = client.get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
                             queue=RANKED_SOLO, start=0, count=per_player) or []
            log.info(f"Joueur {puuid[:8]}… : {len(ids)} parties classées")

            for match_id in ids:
                if total >= max_matches:
                    break
                if is_done(match_id):
                    continue
                match = download_match(client, match_id)
                if match is None:
                    log.info(f"  {match_id} introuvable (404), ignorée")
                    missing.add(match_id)
                    continue
                total += 1
                new += 1
                log.info(f"  [{total}/{max_matches}] {match_id} enregistrée")
                if new % REPORT_EVERY == 0:
                    report(new, total, max_matches, start)
                for p in match["metadata"]["participants"]:
                    if p not in seen:
                        seen.add(p)
                        queue.append(p)

            # Joueur terminé seulement si toutes ses parties sont sur le disque
            # (sinon on s'est arrêté au milieu : il sera repris la prochaine fois).
            if all(is_done(m) or m in missing for m in ids):
                mark_player_done(puuid)
    except KeyboardInterrupt:
        return new, "Arrêt demandé (Ctrl+C). Relance la même commande pour reprendre."
    except RiotKeyError as e:
        return new, f"{e}\nRelance ensuite la même commande : la collecte reprendra où elle s'est arrêtée."
    except RuntimeError as e:
        # Le client a déjà réessayé pendant plusieurs minutes : réseau ou Riot en panne.
        return new, f"{e}\nRéseau ou serveurs Riot indisponibles. Relance la même commande plus tard."
    finally:
        if new % REPORT_EVERY:  # bilan final, sauf s'il vient d'être affiché
            report(new, total, max_matches, start)

    if total >= max_matches:
        return new, "Objectif atteint."
    return new, "Plus aucun joueur à explorer : tout ce qui était accessible a été collecté."


def main():
    parser = argparse.ArgumentParser(description="Collecte de parties classées LoL")
    parser.add_argument("--riot-id", required=True, help='ex. "TECHNIQUEMENT#99999"')
    parser.add_argument("--max-matches", type=int, default=20,
                        help="nombre total de parties à avoir sur le disque")
    parser.add_argument("--per-player", type=int, default=20,
                        help="nombre de parties récentes demandées par joueur")
    args = parser.parse_args()

    setup_logging()
    load_dotenv()
    MATCH_DIR.mkdir(parents=True, exist_ok=True)
    TIMELINE_DIR.mkdir(parents=True, exist_ok=True)

    log.info(f"=== Début de la collecte : objectif {args.max_matches} parties ===")
    try:
        client = RiotClient(os.environ.get("RIOT_API_KEY"), os.environ.get("RIOT_REGION", "europe"))
        name, tag = args.riot_id.split("#")
        account = client.get(f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}")
    except RiotKeyError as e:
        log.error(str(e))
        raise SystemExit(1)
    if account is None:
        log.error(f"Riot ID introuvable : {args.riot_id}")
        raise SystemExit(1)

    with single_instance(), keep_awake():
        new, reason = collect(client, account["puuid"], args.max_matches, args.per_player)

    log.info(reason)
    log.info(f"=== Fin : {new} nouvelles parties, {count_done()} parties complètes dans {RAW} ===")


if __name__ == "__main__":
    main()
