import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
BASE = "https://europe.api.riotgames.com"

# Même partie que dans explore_timeline.py : les deux fichiers d'exemple
# (match et timeline) doivent toujours décrire la même partie.
MATCH_ID = "EUW1_7995392565"


def get(path, **params):
    r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


# account-v1 : Riot ID (pseudo#tag) -> puuid
acc = get("/riot/account/v1/accounts/by-riot-id/TECHNIQUEMENT/99999")
puuid = acc["puuid"]

# match-v5 : derniers identifiants de parties
ids = get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", start=0, count=5)

# match-v5 : le JSON complet de la partie d'exemple
match = get(f"/lol/match/v5/matches/{MATCH_ID}")
assert match["metadata"]["matchId"] == MATCH_ID

os.makedirs("data", exist_ok=True)
with open("data/match_exemple.json", "w", encoding="utf-8") as f:
    json.dump(match, f, indent=2, ensure_ascii=False)
print(ids)
print("Fichier enregistré : data/match_exemple.json pour", MATCH_ID)
