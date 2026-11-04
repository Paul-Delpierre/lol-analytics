"""Tests des fonctions de l'appli dans src/winprob.py (prédiction et explications).

Le vrai modèle (data/app_model.joblib) n'est pas dans le dépôt : on entraîne ici, en
une fraction de seconde, un petit modèle de même forme (une logistique par minute,
mêmes colonnes) sur des données inventées. On ne teste pas la QUALITÉ du modèle
(c'est le rôle des notebooks), mais des propriétés qui doivent être vraies pour
n'importe quel modèle : les explications retombent exactement sur la prédiction,
la vue de l'équipe rouge est le miroir de celle du bleu, etc.
"""

import numpy as np
import pandas as pd
import pytest
from scipy.special import logit

from conftest import random_game
from match_minutes import SEQ_FEATURES, minute_features
from models import make_logit
from winprob import (_model_keys, contributions, explain_minute, key_moments, load_model,
                     player_report, predict)

LAST = 4   # le petit modèle a une logistique pour les minutes 1, 2, 3 et « 4 et plus »


def fake_rows(n, rng, minute):
    X = pd.DataFrame(rng.normal(0, 1, (n, len(SEQ_FEATURES))), columns=SEQ_FEATURES)
    X["minute"] = minute
    return X


@pytest.fixture(scope="module")
def model():
    rng = np.random.default_rng(0)
    models = {}
    for m in range(1, LAST + 1):
        X = fake_rows(400, rng, m)
        y = (X["gold_k"] * m + X["kills_diff"] + rng.normal(0, 1, len(X)) > 0).astype(int)
        models[m] = make_logit().fit(X[SEQ_FEATURES], y)
    return {"models": models, "columns": SEQ_FEATURES, "last": LAST}


@pytest.fixture
def table():
    """10 minutes d'une partie inventée (une ligne par minute)."""
    t = fake_rows(10, np.random.default_rng(1), 0)
    t["minute"] = range(1, 11)
    return t


def test_predict_donne_des_probabilites(model, table):
    p = predict(model, table)
    assert p.shape == (10,) and ((p > 0) & (p < 1)).all()


def test_apres_last_on_garde_le_dernier_modele(model, table):
    late = table.copy()
    late["minute"] = LAST
    assert np.allclose(predict(model, table)[LAST - 1:], predict(model, late)[LAST - 1:])
    assert _model_keys(model, [1, 3, 4, 25]).tolist() == [1, 3, 4, 4]


def test_contributions_exactes(model, table):
    """Base + somme des contributions = log-odds prédit (valeurs de SHAP exactes)."""
    contrib, base = contributions(model, table)
    assert np.allclose(base + contrib.sum(axis=1), logit(predict(model, table)))


def test_moments_cles_decomposition_exacte(model, table):
    """Variation = part des events + part du temps, pour chaque minute gardée."""
    km = key_moments(model, table, sign=1, n=5)
    assert len(km) == 5 and km["minute"].is_monotonic_increasing
    assert np.allclose(km["variation"], km["part des events"] + km["part du temps"])
    assert np.allclose(km["variation"], km["après"] - km["avant"])


def test_moments_cles_vus_du_rouge_sont_le_miroir(model, table):
    blue = key_moments(model, table, sign=1, n=9).set_index("minute")
    red = key_moments(model, table, sign=-1, n=9).set_index("minute")
    assert np.allclose(red.loc[blue.index, "variation"], -blue["variation"])


def test_moments_cles_partie_trop_courte(model, table):
    assert key_moments(model, table.head(1)).empty


@pytest.mark.parametrize("sign", [1, -1])
def test_explain_minute_retombe_sur_la_prediction(model, table, sign):
    out, start, end = explain_minute(model, table, minute=6, sign=sign)
    p_blue = predict(model, table[table["minute"] == 6])[0]
    assert end == pytest.approx(p_blue if sign == 1 else 1 - p_blue)
    assert out["probabilité après"].iloc[-1] == pytest.approx(end)
    assert len(out) == 7                         # 6 variables + « autres variables »


def test_bilan_joueur(model):
    rng = np.random.default_rng(2)
    games = []
    for _ in range(30):
        t = fake_rows(20, rng, 0)
        t["minute"] = range(1, 21)
        games.append((t, int(rng.choice([1, -1])), bool(rng.random() < 0.5)))
    report = player_report(model, games, n_sim=2_000)
    assert report["minute"].tolist() == [10, 15, 20]
    assert (report["parties"] == 30).all()
    assert report["hasard"].between(0, 1).all()
    assert (report["bons attendus"] >= 15).all()       # Σ max(p, 1 − p) ≥ n / 2
    assert (report["remontées"] + report["avances perdues"] + report["bons pronostics"]
            <= 30).all()


def test_vraie_partie_json_vers_probabilites(model):
    """Le chemin complet de l'appli, sans réseau : JSON -> variables -> probabilités."""
    match, timeline = random_game(seed=3)
    t = minute_features(match, timeline)
    p = predict(model, t)
    assert len(p) == len(t) > 15 and not np.isnan(p).any()


def test_modele_absent_message_clair(tmp_path):
    with pytest.raises(FileNotFoundError, match="winprob.py train"):
        load_model(tmp_path / "absent.joblib")
