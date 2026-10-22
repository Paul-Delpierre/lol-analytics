import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
BASE = "https://europe.api.riotgames.com"

MATCH_ID = "EUW1_7995392565"


def get(path, **params):
    r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


timeline = get(f"/lol/match/v5/matches/{MATCH_ID}/timeline")

with open("data/timeline_exemple.json", "w", encoding="utf-8") as f:
    json.dump(timeline, f, indent=2, ensure_ascii=False)

frames = timeline["info"]["frames"]
print("Nombre de frames :", len(frames))
print("Durée approximative :", len(frames) - 1, "minutes")
print("Fichier enregistré : data/timeline_exemple.json")