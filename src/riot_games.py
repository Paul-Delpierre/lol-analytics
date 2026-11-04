"""Les parties d'un joueur, téléchargées à la demande pour l'appli (API Riot + cache disque).

Ce module réutilise le client de l'étape 7 (riot_api.RiotClient : limites de débit,
429, clé expirée) et le format de fichiers de la collecte (JSON compressé, écriture
via un .tmp). Deux différences avec collect.py :
- le cache est À PART (data/app_cache/), pour ne pas mélanger les parties regardées
  dans l'appli avec le jeu de données d'entraînement (data/raw → base → modèle) ;
- le Riot ID et la dernière liste de parties sont gardés aussi, pour que l'appli
  marche encore quand la clé de développement a expiré (elle dure 24 h) : on retrouve
  alors les parties déjà téléchargées, avec un avertissement.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from collect import RANKED_SOLO, load_json_gz, save_json_gz
from riot_api import RiotClient, RiotKeyError  # noqa: F401  (RiotKeyError : pour l'appli)

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "app_cache"


class PlayerNotFound(Exception):
    """Riot ID inconnu (ou mal écrit)."""


def make_client():
    load_dotenv(ROOT / ".env")
    return RiotClient(os.environ.get("RIOT_API_KEY"), os.environ.get("RIOT_REGION", "europe"))


def split_riot_id(riot_id):
    """« Pseudo#TAG » -> (pseudo, tag). Les espaces autour sont retirés."""
    if riot_id.count("#") != 1:
        raise ValueError("Le Riot ID doit avoir la forme Pseudo#TAG (ex. TECHNIQUEMENT#99999).")
    name, tag = (part.strip() for part in riot_id.split("#"))
    if not name or not tag:
        raise ValueError("Le Riot ID doit avoir la forme Pseudo#TAG (ex. TECHNIQUEMENT#99999).")
    return name, tag


def _player_file(name, tag):
    safe = "".join(ch if ch.isalnum() else "_" for ch in f"{name}_{tag}".lower())
    return CACHE / "players" / f"{safe}.json"


def recent_games(client, riot_id, count=10):
    """(puuid, ids des `count` dernières parties classées solo/duo, info).

    info = None si la liste vient de l'API, sinon la date de la liste gardée en cache
    (API injoignable ou clé expirée). Lève PlayerNotFound si le Riot ID n'existe pas.
    """
    name, tag = split_riot_id(riot_id)
    path = _player_file(name, tag)
    try:
        account = client.get(f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}")
        if account is None:
            raise PlayerNotFound(f"Riot ID introuvable : {name}#{tag}")
        ids = client.get(f"/lol/match/v5/matches/by-puuid/{account['puuid']}/ids",
                         queue=RANKED_SOLO, start=0, count=count) or []
    except (RiotKeyError, RuntimeError):
        if not path.exists():
            raise
        saved = json.loads(path.read_text(encoding="utf-8"))
        return saved["puuid"], saved["ids"][:count], saved["saved"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"puuid": account["puuid"], "ids": ids,
                                "saved": datetime.now().isoformat(timespec="minutes")}),
                    encoding="utf-8")
    return account["puuid"], ids, None


def get_game(client, match_id):
    """(match, timeline) d'une partie : depuis le cache si possible, sinon l'API.

    Renvoie None si Riot ne la connaît pas (404) ou si l'API est injoignable et que
    la partie n'a jamais été téléchargée.
    """
    paths = {kind: CACHE / kind / f"{match_id}.json.gz" for kind in ("matches", "timelines")}
    out = {}
    for kind, path in paths.items():
        if path.exists():
            out[kind] = load_json_gz(path)
            continue
        suffix = "/timeline" if kind == "timelines" else ""
        try:
            data = client.get(f"/lol/match/v5/matches/{match_id}{suffix}")
        except (RiotKeyError, RuntimeError):
            return None
        if data is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        save_json_gz(data, path)
        out[kind] = data
    return out["matches"], out["timelines"]
