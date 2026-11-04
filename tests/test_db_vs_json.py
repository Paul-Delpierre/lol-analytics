"""Test d'intégration : le chemin « base » (entraînement) = le chemin « JSON » (appli).

C'est la version automatique de « python src/winprob.py check » (étape 18), mais sur
des parties fabriquées, pour tourner partout (sur GitHub, sans data/raw) :
1. on remplit une base PostgreSQL VIDE avec sql/schema.sql ;
2. on y insère 12 parties au hasard avec load.insert_match (le vrai code d'insertion) ;
3. on calcule les variables par minute des deux façons :
   - entraînement : features.build_features + sequences.build_minute_features (SQL) ;
   - appli : match_minutes.minute_features sur le JSON ;
4. les deux tableaux doivent être identiques (écart 0).

Il lui faut une base de TEST (variable TEST_DATABASE_URL) : sans elle, le test est
sauté. Par sécurité, il refuse toute base dont le nom ne finit pas par « _test » :
il efface tout ce qu'elle contient avant de commencer. Jamais la vraie base « lol ».
"""

import os
from pathlib import Path

import numpy as np
import pytest

from conftest import random_game

pytestmark = pytest.mark.db
URL = os.environ.get("TEST_DATABASE_URL")
SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
N_GAMES = 12


@pytest.fixture(scope="module")
def test_db():
    if not URL:
        pytest.skip("TEST_DATABASE_URL non défini : test avec base sauté")
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(URL, autocommit=True) as conn:
        name = conn.execute("SELECT current_database()").fetchone()[0]
        if not name.endswith("_test"):
            pytest.fail(f"Refus : la base « {name} » ne finit pas par _test "
                        "(ce test efface toutes ses tables).")
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
    return URL


@pytest.fixture(scope="module")
def games(test_db):
    import psycopg
    from load import check_match, insert_match

    out = {}
    with psycopg.connect(test_db) as conn, conn.cursor() as cur:
        for seed in range(N_GAMES):
            match, timeline = random_game(seed)
            assert check_match(match, timeline) is None   # les contrôles qualité passent
            insert_match(cur, match, timeline)
            out[match["metadata"]["matchId"]] = (match, timeline)
    return out


def test_base_et_json_donnent_les_memes_variables(test_db, games):
    pytest.importorskip("torch")            # sequences.py importe PyTorch (étape 17)
    from features import build_features
    from match_minutes import SEQ_FEATURES, TIME, minute_features
    from sequences import build_minute_features

    table = build_features(url=test_db)
    assert set(table["match_id"]) == set(games)   # toutes les parties gardées
    from_db = build_minute_features(table, url=test_db)

    rows = 0
    for match_id, (match, timeline) in games.items():
        a = from_db[from_db["match_id"] == match_id].sort_values(TIME)
        b = minute_features(match, timeline)
        assert a[TIME].tolist() == b[TIME].tolist(), match_id
        diff = np.abs(a[SEQ_FEATURES].to_numpy(float) - b[SEQ_FEATURES].to_numpy(float))
        assert diff.max() == 0, f"{match_id} : écart {diff.max()}"
        rows += len(a)
    assert rows > N_GAMES * 15


def test_minute_15_egale_build_features(test_db, games):
    """Le tableau minute par minute, à 15 min, = les variables de l'étape 12."""
    from features import FEATURES, build_features
    from match_minutes import minute_features

    table = build_features(url=test_db).set_index("match_id")
    for match_id, (match, timeline) in games.items():
        t = minute_features(match, timeline)
        m15 = t[t["minute"] == 15][FEATURES].iloc[0]
        assert np.allclose(m15.to_numpy(float), table.loc[match_id, FEATURES].to_numpy(float))
