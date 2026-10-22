import json
from collections import Counter

with open("data/timeline_exemple.json", encoding="utf-8") as f:
    timeline = json.load(f)

frames = timeline["info"]["frames"]

compteur = Counter()
for frame in frames:
    for event in frame["events"]:
        compteur[event["type"]] += 1

print("Types d'events sur toute la partie :")
for type_event, nombre in compteur.most_common():
    print(f"  {type_event:30} {nombre}")

frame_15 = frames[15]
or_bleu = 0
or_rouge = 0
for pid, joueur in frame_15["participantFrames"].items():
    if int(pid) <= 5:
        or_bleu += joueur["totalGold"]
    else:
        or_rouge += joueur["totalGold"]

print()
print("Frame 15, timestamp :", frame_15["timestamp"], "ms")
print("Or équipe bleue (joueurs 1 à 5) :", or_bleu)
print("Or équipe rouge (joueurs 6 à 10) :", or_rouge)
print("Écart (bleu - rouge) :", or_bleu - or_rouge)