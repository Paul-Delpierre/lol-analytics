import os, json, requests
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
BASE = "https://europe.api.riotgames.com"

def get(path, **params):
    r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# account-v1 : Riot ID (pseudo#tag) -> puuid
acc = get("/riot/account/v1/accounts/by-riot-id/TECHNIQUEMENT/99999")
puuid = acc["puuid"]

# match-v5 : derniers identifiants de parties
ids = get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", start=0, count=5)

# match-v5 : le JSON complet d'une partie
match = get(f"/lol/match/v5/matches/{ids[0]}")
os.makedirs("data", exist_ok=True)
with open("data/match_exemple.json", "w") as f:
    json.dump(match, f, indent=2)
print(ids)