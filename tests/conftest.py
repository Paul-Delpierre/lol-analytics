"""Outils communs aux tests : de fausses parties au format exact de l'API Riot.

Pourquoi des parties fabriquées ? Les vraies parties (data/raw) ne sont pas dans le
dépôt (règle du projet : data/ n'est jamais publié) et GitHub Actions ne les a donc
pas. On fabrique ici, en quelques lignes, un JSON match + timeline qui a la même
forme que celui de Riot (mêmes clés), avec juste ce qu'il faut pour le code testé.

Deux façons de s'en servir :
- make_game(events=[...]) : une partie « calme » (or, XP et CS qui montent
  régulièrement) dans laquelle on place soi-même quelques events. Pour les tests
  où l'on connaît la bonne réponse à l'avance ;
- random_game(seed) : une partie au hasard, avec beaucoup d'events de tous les
  types (dont les cas pièges : exécutions, monstres sans équipe, dragon ancestral).
  Pour le test qui compare le chemin « base » et le chemin « JSON ».
"""

import random

import pytest

# PyTorch en premier, s'il est installé (sur le PC ; pas dans la tâche « unit » de
# GitHub). Sous Windows, importer torch APRÈS LightGBM et scikit-learn, qui chargent
# leur propre bibliothèque OpenMP (calcul en parallèle), peut bloquer le programme
# sans message : c'est arrivé au test base = JSON. conftest.py est lu avant tous les
# fichiers de test, donc torch est chargé avant les autres.
try:
    import torch  # noqa: F401
except ImportError:
    pass

CHAMPIONS = ["Garen", "LeeSin", "Ahri", "Jinx", "Thresh",
             "Darius", "Vi", "Syndra", "Caitlyn", "Lulu"]
POSITIONS = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]


def team_of_pid(pid):
    """Joueurs 1 à 5 : équipe bleue (100) ; 6 à 10 : rouge (200), comme chez Riot."""
    return 100 if pid <= 5 else 200


# ---------------------------------------------------------------------------
# Les events, au format de la timeline Riot
# ---------------------------------------------------------------------------
def kill(ts, killer, victim, assists=()):
    """killer = 0 : exécution (tour, sbire ou monstre)."""
    return {"type": "CHAMPION_KILL", "timestamp": ts, "killerId": killer,
            "victimId": victim, "assistingParticipantIds": list(assists)}


def tower(ts, losing_team, lane="MID_LANE", killer=0):
    """Attention : chez Riot, teamId d'un bâtiment = l'équipe qui le PERD."""
    return {"type": "BUILDING_KILL", "timestamp": ts, "teamId": losing_team,
            "buildingType": "TOWER_BUILDING", "towerType": "OUTER_TURRET",
            "laneType": lane, "killerId": killer}


def inhibitor(ts, losing_team, lane="MID_LANE", killer=0):
    return {"type": "BUILDING_KILL", "timestamp": ts, "teamId": losing_team,
            "buildingType": "INHIBITOR_BUILDING", "laneType": lane, "killerId": killer}


def plate(ts, losing_team, lane="BOT_LANE"):
    return {"type": "TURRET_PLATE_DESTROYED", "timestamp": ts, "teamId": losing_team,
            "laneType": lane, "killerId": 0}


def monster(ts, team, kind, sub=None, killer=0):
    """team = 300 : monstre mort sans équipe (il ne compte pour personne)."""
    e = {"type": "ELITE_MONSTER_KILL", "timestamp": ts, "killerTeamId": team,
         "monsterType": kind, "killerId": killer}
    if sub:
        e["monsterSubType"] = sub
    return e


# ---------------------------------------------------------------------------
# Une partie complète (match + timeline)
# ---------------------------------------------------------------------------
def make_game(events=(), minutes=20, blue_win=True, match_id="EUW1_1000000001",
              patch="16.18", created_ms=1_790_000_000_000, frame_values=None):
    """Une partie de `minutes` minutes pleines, puis la frame de fin (30 s plus tard).

    frame_values(minute, pid) -> (totalGold, xp, minionsKilled, jungleMinionsKilled) ;
    par défaut, tout le monde progresse pareil, sauf le joueur 1 (bleu) qui a
    100 d'or et 10 d'XP d'avance par minute : l'écart bleu − rouge vaut donc
    100 × minute en or et 10 × minute en XP, facile à vérifier.
    """
    if frame_values is None:
        def frame_values(minute, pid):
            bonus = 1 if pid == 1 else 0
            return (500 + 400 * minute + 100 * minute * bonus,
                    450 * minute + 10 * minute * bonus, 6 * minute, minute)

    duration_s = minutes * 60 + 30
    puuids = {pid: f"puuid-{match_id}-{pid}" for pid in range(1, 11)}
    participants = []
    for pid in range(1, 11):
        team = team_of_pid(pid)
        participants.append({
            "participantId": pid, "teamId": team, "puuid": puuids[pid],
            "riotIdGameName": f"Joueur{pid}", "riotIdTagline": "EUW",
            "championId": pid, "championName": CHAMPIONS[pid - 1],
            "teamPosition": POSITIONS[(pid - 1) % 5], "champLevel": 14,
            "kills": 1, "deaths": 1, "assists": 2, "goldEarned": 9000,
            "totalMinionsKilled": 150, "neutralMinionsKilled": 10, "visionScore": 20,
            "totalDamageDealtToChampions": 12000,
            "win": (team == 100) == blue_win, "gameEndedInEarlySurrender": False,
        })
    match = {
        "metadata": {"matchId": match_id, "participants": list(puuids.values())},
        "info": {
            "platformId": "EUW1", "queueId": 420, "gameVersion": f"{patch}.700.1234",
            "gameCreation": created_ms, "gameDuration": duration_s,
            "endOfGameResult": "GameComplete", "participants": participants,
            "teams": [{"teamId": 100, "win": blue_win, "objectives": {}},
                      {"teamId": 200, "win": not blue_win, "objectives": {}}],
        },
    }

    # Frames 0..minutes à chaque minute pile, puis la frame de fin à duration_s.
    # Chaque event est rangé dans la frame qui suit son instant (comme chez Riot).
    frames = []
    for i in range(minutes + 2):
        ts = i * 60_000 if i <= minutes else duration_s * 1000
        minute_for_values = min(i, minutes) + (0.5 if i > minutes else 0)
        pfs = {}
        for pid in range(1, 11):
            gold, xp, cs, jungle = frame_values(minute_for_values, pid)
            pfs[str(pid)] = {"participantId": pid, "totalGold": int(gold), "xp": int(xp),
                             "level": 1 + int(minute_for_values // 2),
                             "minionsKilled": int(cs), "jungleMinionsKilled": int(jungle),
                             "position": {"x": 7000, "y": 7000}}
        frames.append({"timestamp": ts, "participantFrames": pfs, "events": []})
    for e in sorted(events, key=lambda e: e["timestamp"]):
        index = min(e["timestamp"] // 60_000 + 1, len(frames) - 1)
        frames[index]["events"].append(e)

    timeline = {
        "metadata": {"matchId": match_id, "participants": list(puuids.values())},
        "info": {"frameInterval": 60_000, "frames": frames,
                 "participants": [{"participantId": pid, "puuid": puuids[pid]}
                                  for pid in range(1, 11)]},
    }
    return match, timeline


def random_game(seed, minutes=None):
    """Une partie au hasard (reproductible), avec des events de tous les types."""
    rng = random.Random(seed)
    minutes = minutes or rng.randint(18, 38)
    end_ms = minutes * 60_000 + 30_000
    lead = {pid: rng.uniform(-30, 30) for pid in range(1, 11)}

    def frame_values(minute, pid):
        return (500 + (380 + lead[pid]) * minute + rng.randint(0, 40),
                (420 + lead[pid]) * minute + rng.randint(0, 30),
                int(6 * minute + rng.randint(0, 5)), int(minute * rng.random()))

    def ts():
        return rng.randint(60_000, end_ms - 1)

    events = []
    for _ in range(rng.randint(10, 40)):
        victim = rng.randint(1, 10)
        enemies = [p for p in range(1, 11) if team_of_pid(p) != team_of_pid(victim)]
        killer = 0 if rng.random() < 0.1 else rng.choice(enemies)   # 10 % d'exécutions
        events.append(kill(ts(), killer, victim, rng.sample(enemies, rng.randint(0, 2))))
    for _ in range(rng.randint(0, 9)):
        events.append(tower(ts(), rng.choice([100, 200]), rng.choice(["TOP_LANE", "MID_LANE"])))
    for _ in range(rng.randint(0, 2)):
        events.append(inhibitor(ts(), rng.choice([100, 200])))
    for _ in range(rng.randint(0, 8)):
        events.append(plate(rng.randint(60_000, 14 * 60_000), rng.choice([100, 200])))
    for _ in range(rng.randint(0, 4)):
        events.append(monster(ts(), rng.choice([100, 200]), "DRAGON", "FIRE_DRAGON"))
    if minutes >= 22 and rng.random() < 0.5:
        # Le dragon ancestral n'apparaît qu'après 4 dragons d'une équipe, jamais avant
        # 15 min. (L'étape 12 le compte avec les dragons ; sans effet puisqu'il n'y en a
        # aucun à 15 min. Le tableau minute par minute le met à part : elders_diff.)
        events.append(monster(rng.randint(21 * 60_000, end_ms - 1), rng.choice([100, 200]),
                              "DRAGON", "ELDER_DRAGON"))
    for _ in range(rng.randint(0, 3)):
        events.append(monster(rng.randint(5 * 60_000, 9 * 60_000),
                              rng.choice([100, 200]), "HORDE"))
    if rng.random() < 0.5:
        events.append(monster(ts(), rng.choice([100, 200]), "RIFTHERALD"))
    if rng.random() < 0.4:
        events.append(monster(ts(), rng.choice([100, 200]), "BARON_NASHOR"))
    events.append(monster(ts(), 300, "DRAGON", "WATER_DRAGON"))     # sans équipe : ignoré
    return make_game(events, minutes=minutes, blue_win=rng.random() < 0.5,
                     match_id=f"EUW1_{2_000_000_000 + seed}",
                     created_ms=1_790_000_000_000 + seed * 3_600_000,
                     frame_values=frame_values)


@pytest.fixture
def quiet_game():
    """Une partie de 20 minutes sans aucun event."""
    return make_game()
