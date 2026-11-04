"""Tests du calcul des variables minute par minute (src/match_minutes.py).

C'est le cœur de l'appli : si une variable est fausse (un event compté une minute
trop tôt, un signe inversé), le modèle donne une probabilité fausse SANS aucun
message d'erreur. Chaque test fixe une règle du projet et vérifie qu'elle tient.
"""

import pandas as pd
import pytest

from conftest import inhibitor, kill, make_game, monster, plate, tower
from load import event_team
from match_minutes import (EVENT_COLUMNS, FRAME_COLUMNS, SEQ_FEATURES, event_kind,
                           events_from_json, frames_from_json, game_summary,
                           minute_features, minute_table, readable_events)


def at(table, minute):
    """La ligne d'une minute, sous forme de dictionnaire."""
    return table[table["minute"] == minute].iloc[0].to_dict()


# ---------------------------------------------------------------------------
# 1. minute_table : le calcul commun à la base et au JSON
# ---------------------------------------------------------------------------
def tiny_tables(events):
    """5 minutes sans écart d'or, et les events donnés (timestamp_ms, sign, kind)."""
    frames = pd.DataFrame([("M", m, 0, 0, 0) for m in range(1, 6)], columns=FRAME_COLUMNS)
    events = pd.DataFrame([("M", *e) for e in events], columns=EVENT_COLUMNS)
    return frames, events


def test_un_event_compte_a_partir_de_la_minute_suivante():
    # Un kill à 2:59.999 est dans l'état « minute 3 » ; à 3:00.000, dans « minute 4 ».
    frames, events = tiny_tables([(179_999, 1, "kills"), (180_000, -1, "kills")])
    t = minute_table(frames, events)
    assert t["kills_diff"].tolist() == [0, 0, 1, 0, 0]


def test_les_ecarts_sont_cumules_mais_pas_kills_1min():
    frames, events = tiny_tables([(30_000, 1, "kills"), (90_000, 1, "kills"),
                                  (100_000, 1, "kills")])
    t = minute_table(frames, events)
    assert t["kills_diff"].tolist() == [1, 3, 3, 3, 3]          # cumulé
    assert t["kills_1min_diff"].tolist() == [1, 2, 0, 0, 0]     # la minute seule


def test_premiers_objectifs():
    # Premier sang rouge à 1:30 (puis un kill bleu : ne change pas le premier sang).
    frames, events = tiny_tables([(90_000, -1, "kills"), (150_000, 1, "kills"),
                                  (200_000, 1, "towers")])
    t = minute_table(frames, events)
    assert t["first_blood"].tolist() == [0, -1, -1, -1, -1]
    assert t["first_tower"].tolist() == [0, 0, 0, 1, 1]
    assert t["first_dragon"].tolist() == [0, 0, 0, 0, 0]        # jamais pris -> 0


def test_events_sans_genre_ignores():
    frames, events = tiny_tables([(30_000, 1, None)])
    t = minute_table(frames, events)
    assert (t[SEQ_FEATURES] == 0).all().all()


def test_colonnes_et_ordre():
    frames, events = tiny_tables([])
    t = minute_table(frames.sample(frac=1, random_state=0), events)
    assert list(t.columns) == ["match_id", "minute"] + SEQ_FEATURES
    assert t["minute"].tolist() == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# 2. Du JSON de Riot aux deux tableaux d'entrée
# ---------------------------------------------------------------------------
def test_frames_sans_minute_0_ni_frame_de_fin(quiet_game):
    match, timeline = quiet_game                   # 20 minutes + frame de fin
    frames = frames_from_json(match, timeline)
    assert frames["minute"].tolist() == list(range(1, 21))
    # Seul le joueur 1 (bleu) a de l'avance : 100 d'or et 10 d'XP par minute.
    assert frames["gold_diff"].tolist() == [100 * m for m in range(1, 21)]
    assert frames["xp_diff"].tolist() == [10 * m for m in range(1, 21)]
    assert (frames["cs_diff"] == 0).all()


def test_frame_incomplete_ignoree(quiet_game):
    match, timeline = quiet_game
    del timeline["info"]["frames"][5]["participantFrames"]["7"]
    frames = frames_from_json(match, timeline)
    assert 5 not in frames["minute"].tolist() and len(frames) == 19


def test_max_minute(quiet_game):
    match, timeline = quiet_game
    assert frames_from_json(match, timeline, max_minute=10)["minute"].max() == 10


@pytest.mark.parametrize("event, sign, kind", [
    (kill(65_000, 3, 8), 1, "kills"),                  # le bleu 3 tue le rouge 8
    (kill(65_000, 0, 8), 1, "kills"),                  # exécution du rouge 8 -> pour le bleu
    (kill(65_000, 0, 2), -1, "kills"),                 # exécution du bleu 2 -> pour le rouge
    (tower(65_000, 200), 1, "towers"),                 # le rouge PERD la tour -> bleu
    (inhibitor(65_000, 100), -1, "inhibs"),
    (plate(65_000, 200), 1, "plates"),
    (monster(65_000, 100, "DRAGON", "FIRE_DRAGON"), 1, "dragons"),
    (monster(65_000, 200, "DRAGON", "ELDER_DRAGON"), -1, "elders"),  # pas dans dragons
    (monster(65_000, 100, "HORDE"), 1, "grubs"),
    (monster(65_000, 200, "RIFTHERALD"), -1, "heralds"),
    (monster(65_000, 100, "BARON_NASHOR"), 1, "barons"),
])
def test_signe_et_genre_de_chaque_event(event, sign, kind):
    match, timeline = make_game([event])
    events = events_from_json(match, timeline)
    assert events[["sign", "kind"]].values.tolist() == [[sign, kind]]


def test_monstre_sans_equipe_et_autres_events_ignores():
    ward = {"type": "WARD_PLACED", "timestamp": 70_000}
    match, timeline = make_game([monster(65_000, 300, "DRAGON", "FIRE_DRAGON"), ward])
    assert events_from_json(match, timeline).empty


def test_event_team_de_load():
    """La même fonction sert à l'insertion en base (load.py) et au JSON."""
    teams = {pid: 100 if pid <= 5 else 200 for pid in range(1, 11)}
    assert event_team(kill(0, 6, 1), 6, 1, teams) == 200
    assert event_team(kill(0, 0, 1), None, 1, teams) == 200
    assert event_team(tower(0, 100), None, None, teams) == 200
    assert event_team(monster(0, 300, "DRAGON"), None, None, teams) is None


def test_event_kind_dragon_ancestral_avant_dragon():
    assert event_kind(monster(0, 100, "DRAGON", "ELDER_DRAGON")) == "elders"
    assert event_kind(monster(0, 100, "DRAGON", "AIR_DRAGON")) == "dragons"
    assert event_kind(monster(0, 100, "ATAKHAN")) is None


# ---------------------------------------------------------------------------
# 3. Bout en bout : une partie dont on connaît la réponse
# ---------------------------------------------------------------------------
def test_minute_features_bout_en_bout():
    events = [kill(90_000, 2, 7), tower(600_000, 200), monster(420_000, 200, "HORDE"),
              monster(720_000, 100, "DRAGON", "EARTH_DRAGON"), plate(300_000, 100)]
    match, timeline = make_game(events)
    t = minute_features(match, timeline)
    m15 = at(t, 15)
    assert m15["gold_k"] == pytest.approx(1.5) and m15["xp_k"] == pytest.approx(0.15)
    assert (m15["kills_diff"], m15["towers_diff"], m15["dragons_diff"],
            m15["grubs_diff"], m15["plates_diff"]) == (1, 1, 1, -1, -1)
    assert (m15["first_blood"], m15["first_tower"], m15["first_dragon"]) == (1, 1, 1)
    assert at(t, 2)["kills_1min_diff"] == 1 and at(t, 3)["kills_1min_diff"] == 0
    assert at(t, 10)["towers_diff"] == 0 and at(t, 11)["towers_diff"] == 1  # tour à 10:00


# ---------------------------------------------------------------------------
# 4. Ce que l'appli affiche
# ---------------------------------------------------------------------------
def test_readable_events_sans_pseudo():
    """Règle du projet : les autres joueurs sont désignés par leur champion."""
    match, timeline = make_game([kill(90_000, 2, 7), kill(95_000, 0, 3),
                                 plate(100_000, 100), monster(120_000, 100, "BARON_NASHOR")])
    ev = readable_events(match, timeline)
    assert ev["text"].tolist() == ["LeeSin tue Vi", "une tour ou un sbire tue Ahri",
                                   "tue le baron Nashor"]          # plaques non listées
    assert ev["time"].tolist() == ["01:30", "01:35", "02:00"]
    assert ev["minute"].tolist() == [2, 2, 3]
    text = " ".join(ev["text"])
    assert "Joueur" not in text and "puuid" not in text


def test_game_summary_vu_du_joueur():
    match, _ = make_game(blue_win=False)
    red = match["info"]["participants"][7]
    s = game_summary(match, red["puuid"])
    assert (s["team"], s["champion"], s["win"], s["patch"]) == (200, "Syndra", True, "16.18")
    assert s["duration_min"] == pytest.approx(20.5)
    assert game_summary(match, "inconnu") is None
