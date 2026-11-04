"""Probabilité de victoire minute par minute (étape 17) : données, modèles, évaluation.

Ce module prolonge features.py (une photo à 15 min) en un FILM : l'état de la partie
à chaque minute. Il sert à trois choses :
1. build_minute_features() lit la base et renvoie un tableau « long » : une ligne par
   (partie, minute), avec les mêmes écarts bleu − rouge qu'à l'étape 12, plus des
   objectifs de fin de partie (barons, inhibiteurs, dragon ancestral, héraut) et les
   kills de la dernière minute. to_padded() range ce tableau en 3 dimensions
   (parties, minutes, variables) pour le GRU.
2. Trois modèles avec la même interface fit(long) / predict(long) :
   - PerMinuteLogit : une régression logistique par minute (l'adversaire simple) ;
   - StackedLGBM : un seul LightGBM pour toutes les minutes, la minute en variable ;
   - SequenceGRU : le GRU de deep.py, qui lit les minutes dans l'ordre.
3. L'évaluation sans fuite : cross_validate_minutes() (plis chronologiques PAR PARTIE),
   scores_by_minute(), et bootstrap_games() (intervalle de confiance d'un écart de
   log loss, en tirant des PARTIES et non des lignes).

Règles anti-fuite, partout dans ce module :
- l'état à la minute t n'utilise que ce qui s'est passé AVANT t (events dont le
  timestamp < t × 60 000 ms, frame de la minute t) ;
- la dernière frame de chaque partie (l'instant exact de la fin) est retirée ;
- toutes les minutes d'une partie sont du même côté d'un découpage (entraînement,
  validation ou test) ;
- tout ce qui s'apprend (scaler, modèles, arrêt précoce) ne voit que l'entraînement.

Utilisation (notebook 07) :
    from sequences import build_minute_features, PerMinuteLogit, StackedLGBM, SequenceGRU
"""

import numpy as np
import pandas as pd
import psycopg
import torch
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from deep import SEED, WinGRU, masked_bce, set_seed, to_tensor, train_model
from features import FEATURES, TARGET, database_url
from match_minutes import (EVENT_COLUMNS, EVENT_KINDS, FIRSTS, FRAME_COLUMNS,  # noqa: F401
                           LATE_FEATURES, MAX_MINUTE, SEQ_FEATURES, TIME, minute_table)
from models import evaluate, make_lgbm, make_logit

# ---------------------------------------------------------------------------
# Les colonnes : SEQ_FEATURES, TIME, MAX_MINUTE... sont définies dans match_minutes.py
# depuis l'étape 18 (l'appli en a besoin sans PyTorch) et réimportées ci-dessus, pour
# que « from sequences import SEQ_FEATURES » marche toujours (notebook 07, live.py).
# ---------------------------------------------------------------------------
# Chaque event utile devient un « genre » ; +1 s'il est pris par le bleu, −1 par le rouge.
EVENTS_SQL = """
SELECT match_id, timestamp_ms,
       CASE WHEN killer_team_id = 100 THEN 1 ELSE -1 END AS sign,
       CASE WHEN event_type = 'CHAMPION_KILL'                THEN 'kills'
            WHEN building_type = 'TOWER_BUILDING'            THEN 'towers'
            WHEN building_type = 'INHIBITOR_BUILDING'        THEN 'inhibs'
            WHEN event_type = 'TURRET_PLATE_DESTROYED'       THEN 'plates'
            WHEN monster_sub_type = 'ELDER_DRAGON'           THEN 'elders'
            WHEN monster_type = 'DRAGON'                     THEN 'dragons'
            WHEN monster_type = 'HORDE'                      THEN 'grubs'
            WHEN monster_type = 'RIFTHERALD'                 THEN 'heralds'
            WHEN monster_type = 'BARON_NASHOR'               THEN 'barons'
       END AS kind
FROM events
WHERE killer_team_id IS NOT NULL
  AND match_id = ANY(%(ids)s)
"""

# Or, XP et CS des 10 joueurs à chaque minute, en écarts bleu − rouge.
# La dernière frame de chaque partie (minute = last_minute) est l'instant exact de la
# fin : on la retire, sinon le modèle « verrait » la partie se terminer.
FRAMES_SQL = """
WITH last AS (
    SELECT match_id, max(minute) AS last_minute
    FROM participant_frames
    WHERE match_id = ANY(%(ids)s)
    GROUP BY match_id
)
SELECT f.match_id, f.minute,
       sum(CASE WHEN p.team_id = 100 THEN 1 ELSE -1 END * f.total_gold) AS gold_diff,
       sum(CASE WHEN p.team_id = 100 THEN 1 ELSE -1 END * f.xp) AS xp_diff,
       sum(CASE WHEN p.team_id = 100 THEN 1 ELSE -1 END
           * (f.minions_killed + f.jungle_minions_killed)) AS cs_diff
FROM participant_frames f
JOIN participants p USING (match_id, participant_id)
JOIN last l USING (match_id)
WHERE f.minute BETWEEN 1 AND %(max_minute)s
  AND f.minute < l.last_minute
GROUP BY f.match_id, f.minute
HAVING count(*) = 10
ORDER BY f.match_id, f.minute
"""


# ---------------------------------------------------------------------------
# 1. Les données minute par minute
# ---------------------------------------------------------------------------
def build_minute_features(games, max_minute=MAX_MINUTE, url=None):
    """Tableau long : une ligne par (partie, minute) pour les parties de `games`.

    games : le DataFrame de features.build_features() (une ligne par partie). On garde
    ainsi exactement les mêmes parties qu'aux étapes 12 à 16, donc le même test.
    Colonnes renvoyées : match_id, game_creation, minute, SEQ_FEATURES, blue_win.
    Lignes triées par date de la partie puis par minute.
    """
    params = {"ids": list(games["match_id"]), "max_minute": max_minute}
    with psycopg.connect(url or database_url()) as conn:
        frames = pd.DataFrame(conn.execute(FRAMES_SQL, params).fetchall(), columns=FRAME_COLUMNS)
        events = pd.DataFrame(conn.execute(EVENTS_SQL, params).fetchall(), columns=EVENT_COLUMNS)
    # Le calcul lui-même est dans match_minutes.minute_table() : l'appli l'applique
    # aux parties téléchargées (JSON), exactement comme ici à la base.
    df = minute_table(frames, events)
    df = df.merge(games[["match_id", "game_creation", TARGET]], on="match_id")
    df = df.sort_values(["game_creation", "minute"]).reset_index(drop=True)
    return df[["match_id", "game_creation", TIME] + SEQ_FEATURES + [TARGET]]


def check_against_15(long, games):
    """Plus grand écart entre le tableau long à la minute 15 et build_features() (doit être 0)."""
    at15 = long[long[TIME] == 15].set_index("match_id")[FEATURES]
    ref = games.set_index("match_id").loc[at15.index, FEATURES]
    return (at15 - ref).abs().max()


def split_games(long, games_train, games_test):
    """Coupe le tableau long selon un découpage de PARTIES (toutes leurs minutes ensemble)."""
    tr = long[long["match_id"].isin(games_train["match_id"])]
    te = long[long["match_id"].isin(games_test["match_id"])]
    return tr.reset_index(drop=True), te.reset_index(drop=True)


def to_padded(long, columns, n_minutes=MAX_MINUTE, values=None):
    """Tableau long -> tableaux 3D pour le GRU.

    Renvoie X (parties, minutes, variables), y (parties, minutes) et les positions
    (partie, minute) de chaque ligne de `long`, pour remettre les prédictions dans
    l'ordre du tableau. La minute 1 va dans la case 0. Les parties courtes sont
    complétées par des 0 (X) et des NaN (y) après leur fin : c'est le « padding ».
    values : les valeurs à ranger (par défaut long[columns]) ; le GRU y passe les
    variables centrées-réduites, la colonne minute de `long` servant toujours d'adresse.
    """
    game_ids, game_idx = np.unique(long["match_id"], return_inverse=True)
    minute_idx = long[TIME].to_numpy() - 1
    X = np.zeros((len(game_ids), n_minutes, len(columns)), dtype=np.float32)
    y = np.full((len(game_ids), n_minutes), np.nan, dtype=np.float32)
    X[game_idx, minute_idx] = long[columns].to_numpy(dtype=np.float32) if values is None else values
    y[game_idx, minute_idx] = long[TARGET].to_numpy(dtype=np.float32)
    return X, y, (game_idx, minute_idx)


# ---------------------------------------------------------------------------
# 2. Les trois modèles (même interface : fit(long) puis predict(long))
# ---------------------------------------------------------------------------
class PerMinuteLogit:
    """Une régression logistique de l'étape 13 PAR minute (1, 2, …, 40 et plus).

    Chaque modèle ne regarde que l'état à sa minute : il apprend par exemple que
    1 000 d'or pèsent beaucoup à 10 min et moins à 35 min. Au-delà de `last` minutes,
    il reste trop peu de parties : un seul modèle pour « `last` minutes et plus ».
    """

    def __init__(self, columns=SEQ_FEATURES, C=1.0, last=40):
        self.columns, self.C, self.last = columns, C, last

    def _bucket(self, long):
        return long[TIME].clip(upper=self.last).to_numpy()

    def fit(self, long):
        buckets = self._bucket(long)
        self.models_ = {}
        for m in np.unique(buckets):
            rows = long[buckets == m]
            if rows[TARGET].nunique() == 2:
                self.models_[m] = make_logit(self.C).fit(rows[self.columns], rows[TARGET])
        return self

    def predict(self, long):
        buckets = self._bucket(long)
        p = np.full(len(long), np.nan)
        for m in np.unique(buckets):
            rows = buckets == m
            # minute jamais vue à l'entraînement : on prend le modèle le plus proche
            key = min(self.models_, key=lambda k: abs(k - m))
            p[rows] = self.models_[key].predict_proba(long.loc[rows, self.columns])[:, 1]
        return p


class StackedLGBM:
    """Un seul LightGBM pour toutes les (partie, minute), la minute étant une variable.

    Les arbres peuvent découper sur la minute : « écart d'or > 2 000 ET minute < 20 ».
    Comme le tableau a ~30 fois plus de lignes qu'à 15 min (mais toujours ~3 800
    parties), on exige plus de lignes par feuille (min_child_samples).
    """

    def __init__(self, columns=SEQ_FEATURES + [TIME], **params):
        self.columns = columns
        self.params = {"n_estimators": 400, "num_leaves": 15, "min_child_samples": 200,
                       **params}

    def fit(self, long):
        self.model_ = make_lgbm(**self.params).fit(long[self.columns], long[TARGET])
        return self

    def predict(self, long):
        return self.model_.predict_proba(long[self.columns])[:, 1]


class SequenceGRU:
    """Le GRU de deep.py avec la même interface que les deux autres modèles.

    fit() reste SANS FUITE, comme TorchClassifier à l'étape 16 :
    - les `valid_frac` parties les plus RÉCENTES de l'entraînement servent à l'arrêt
      précoce (parties entières, jamais des minutes isolées) ;
    - le StandardScaler est appris sur les autres parties d'entraînement seulement.
    """

    def __init__(self, columns=SEQ_FEATURES + [TIME], hidden=32, dropout=0.2,
                 valid_frac=0.15, lr=3e-3, weight_decay=1e-3, batch_size=64,
                 max_epochs=150, patience=10, seed=SEED):
        self.columns, self.hidden, self.dropout = columns, hidden, dropout
        self.valid_frac, self.seed = valid_frac, seed
        self.train_kwargs = dict(lr=lr, weight_decay=weight_decay, batch_size=batch_size,
                                 max_epochs=max_epochs, patience=patience, seed=seed,
                                 loss_fn=masked_bce, clip=1.0)

    def _tensors(self, long):
        scaled = self.scaler_.transform(long[self.columns]).astype(np.float32)
        X, y, positions = to_padded(long, self.columns, values=scaled)
        return to_tensor(X), to_tensor(y), positions

    def fit(self, long, verbose=False):
        # Découpage par PARTIE, dans l'ordre chronologique (le tableau est trié par date).
        order = long.drop_duplicates("match_id")["match_id"].to_numpy()
        cut = int(len(order) * (1 - self.valid_frac))
        fit_rows = long[long["match_id"].isin(order[:cut])]
        valid_rows = long[long["match_id"].isin(order[cut:])]

        self.scaler_ = StandardScaler().fit(fit_rows[self.columns])
        X_fit, y_fit, _ = self._tensors(fit_rows)
        X_val, y_val, _ = self._tensors(valid_rows)

        set_seed(self.seed)
        self.net_ = WinGRU(len(self.columns), hidden=self.hidden, dropout=self.dropout)
        self.history_ = train_model(self.net_, (X_fit, y_fit), (X_val, y_val),
                                    verbose=verbose, **self.train_kwargs)
        return self

    def predict(self, long):
        X, _, (g, m) = self._tensors(long)
        self.net_.eval()
        with torch.no_grad():
            p = torch.sigmoid(self.net_(X)).numpy()
        return p[g, m]  # on remet chaque prédiction en face de sa ligne du tableau long


# ---------------------------------------------------------------------------
# 3. Évaluer sans fuite
# ---------------------------------------------------------------------------
def game_folds(long, n_splits=5):
    """Plis chronologiques sur les PARTIES : chaque pli valide sur des parties plus
    récentes que toutes celles de son entraînement (comme time_folds de models.py)."""
    order = long.drop_duplicates("match_id")["match_id"].to_numpy()  # trié par date
    for tr, va in TimeSeriesSplit(n_splits=n_splits).split(order):
        yield (long[long["match_id"].isin(order[tr])].reset_index(drop=True),
               long[long["match_id"].isin(order[va])].reset_index(drop=True))


def cross_validate_minutes(make_model, long, n_splits=5, verbose=True):
    """Une ligne de scores par pli ; toutes les (partie, minute) du pli de validation comptent."""
    rows = []
    for k, (train, valid) in enumerate(game_folds(long, n_splits), start=1):
        p = make_model().fit(train).predict(valid)
        rows.append({"fold": k, "n_games_train": train["match_id"].nunique(),
                     "n_rows_valid": len(valid), **evaluate(valid[TARGET], p)})
        if verbose:
            print(f"  pli {k} : log loss {rows[-1]['log_loss']:.4f}")
    return pd.DataFrame(rows)


def scores_by_minute(long, preds, minutes=range(1, 41)):
    """Log loss et AUC de chaque modèle, minute par minute (parties encore en cours)."""
    out = []
    for m in minutes:
        rows = (long[TIME] == m).to_numpy()
        y = long.loc[rows, TARGET]
        if rows.sum() < 30 or y.nunique() < 2:
            continue
        line = {"minute": m, "n_games": int(rows.sum())}
        for name, p in preds.items():
            line[f"{name} log loss"] = log_loss(y, p[rows], labels=[0, 1])
            line[f"{name} AUC"] = roc_auc_score(y, p[rows])
        out.append(line)
    return pd.DataFrame(out).set_index("minute")


def bootstrap_games(long, p_a, p_b, n_boot=2000, seed=SEED):
    """Écart de log loss (b − a) et son IC à 95 %, en tirant des PARTIES avec remise.

    Les ~30 lignes d'une même partie ne sont pas indépendantes (même résultat, états
    voisins) : tirer des lignes ferait croire à ~30 fois plus de données et donnerait
    un intervalle beaucoup trop étroit. On additionne donc la perte de chaque partie,
    puis on tire des parties entières (bootstrap « par grappes »).
    """
    y = long[TARGET].to_numpy()
    eps = 1e-15
    def row_loss(p):
        p = np.clip(p, eps, 1 - eps)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))
    per_game = (pd.DataFrame({"g": long["match_id"].to_numpy(),
                              "a": row_loss(p_a), "b": row_loss(p_b), "n": 1})
                .groupby("g").sum())
    a, b, n = per_game["a"].to_numpy(), per_game["b"].to_numpy(), per_game["n"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (n_boot, len(a)))
    diffs = (b[idx].sum(1) - a[idx].sum(1)) / n[idx].sum(1)
    low, high = np.percentile(diffs, [2.5, 97.5])
    return (b.sum() - a.sum()) / n.sum(), low, high
