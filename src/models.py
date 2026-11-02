"""Modèles de victoire à 15 min : briques communes à l'étape 13 et aux suivantes.

Ce module regroupe ce qui sert à COMPARER des modèles sans tricher :
1. les modèles eux-mêmes : make_logit() (régression logistique scikit-learn) et
   make_lgbm() (LightGBM, arbres de décision boostés) ;
2. prepare() : ajoute le score de scaling en l'apprenant sur la partie
   entraînement SEULEMENT (appelé dans chaque pli de validation croisée), et
   oof_scaling() le calcule « hors pli » pour les parties d'entraînement ;
3. evaluate() : les métriques (log loss, Brier, AUC, précision) ;
4. cross_validate() : validation croisée chronologique (TimeSeriesSplit) ;
5. fit_predict() : entraîne sur un jeu, prédit sur un autre (test final) ;
6. paired_bootstrap() : intervalle de confiance d'un ÉCART de score entre deux
   modèles évalués sur les mêmes parties.

Utilisation (notebook 03) :
    from models import make_logit, make_lgbm, cross_validate, fit_predict
"""

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import KFold, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import TARGET, add_scaling, fit_scaling

SEED = 42


# ---------------------------------------------------------------------------
# 1. Les modèles
# ---------------------------------------------------------------------------
def make_baseline():
    """Prédit toujours le taux de victoire du bleu vu à l'entraînement (≈ 48,5 %)."""
    return DummyClassifier(strategy="prior")


def make_logit(C=1.0):
    """Régression logistique avec variables centrées-réduites.

    StandardScaler dans le pipeline : la pénalité L2 (C) traite toutes les variables
    de la même façon seulement si elles sont à la même échelle ; et le scaler est
    réappris dans chaque pli avec le modèle (pas de fuite par la moyenne / l'écart type).
    """
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))


def make_lgbm(n_estimators=300, num_leaves=7, learning_rate=0.03, min_child_samples=50):
    """LightGBM réglé « prudent » : petits arbres, apprentissage lent, sous-échantillonnage.

    Avec ~4 800 parties, un LightGBM aux réglages par défaut (31 feuilles, 100 arbres
    à 0,1) apprend vite le bruit. On limite la taille des arbres (num_leaves), on
    exige 50 parties par feuille, et chaque arbre ne voit que 80 % des parties et
    80 % des variables (subsample, colsample_bytree).
    """
    return LGBMClassifier(
        objective="binary",
        n_estimators=n_estimators,
        num_leaves=num_leaves,
        learning_rate=learning_rate,
        min_child_samples=min_child_samples,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=SEED,
        verbose=-1,
    )


# ---------------------------------------------------------------------------
# 2. Préparation sans fuite
# ---------------------------------------------------------------------------
def oof_scaling(train, n_splits=5):
    """Score de scaling des parties d'ENTRAÎNEMENT, calculé « hors pli ».

    Problème : les notes des champions sont des taux de victoire. Si on les apprend
    sur l'entraînement puis qu'on les applique à ces MÊMES parties, chaque partie a
    contribué à la note de ses propres champions : son score contient un peu de son
    propre résultat. Le modèle croit alors le score plus fiable qu'il n'est, et lui
    donne trop de poids. C'est le piège classique du « target encoding ».

    Solution : on coupe l'entraînement en 5 morceaux ; le score des parties de chaque
    morceau est calculé avec des notes apprises sur les 4 autres. Aucune partie ne
    voit son propre résultat dans son score.
    """
    parts = []
    for fit_idx, score_idx in KFold(n_splits, shuffle=True, random_state=SEED).split(train):
        notes = fit_scaling(train.iloc[fit_idx])
        parts.append(add_scaling(train.iloc[score_idx], notes))
    return pd.concat(parts).loc[train.index]


def prepare(train, other, use_scaling, oof=True):
    """Renvoie (train, other) prêts pour le modèle.

    Si use_scaling : les notes de scaling sont apprises sur `train` uniquement,
    puis appliquées à `other` (validation ou test), qui ne sert jamais à les
    apprendre. Pour les lignes de `train` elles-mêmes, le score est calculé hors
    pli (oof=True, voir oof_scaling) ; oof=False garde la version naïve, pour
    montrer la différence dans le notebook.
    """
    if not use_scaling:
        return train, other
    notes = fit_scaling(train)
    train_scored = oof_scaling(train) if oof else add_scaling(train, notes)
    return train_scored, add_scaling(other, notes)


# ---------------------------------------------------------------------------
# 3. Métriques
# ---------------------------------------------------------------------------
def evaluate(y, p):
    """Scores d'un jeu de probabilités p (victoire du bleu) face aux résultats y."""
    return {
        "log_loss": log_loss(y, p, labels=[0, 1]),  # critère principal : plus bas = mieux
        "brier": brier_score_loss(y, p),            # erreur quadratique des probabilités
        "auc": roc_auc_score(y, p),                 # capacité à classer, 0,5 = hasard
        "accuracy": accuracy_score(y, p >= 0.5),    # % de bons pronostics à 50 %
    }


# ---------------------------------------------------------------------------
# 4 et 5. Entraîner, prédire, valider
# ---------------------------------------------------------------------------
def fit_predict(make_model, columns, train, other, use_scaling=False, oof=True):
    """Entraîne un modèle neuf sur `train`, renvoie les probabilités sur `other`."""
    train, other = prepare(train, other, use_scaling, oof)
    model = make_model()
    model.fit(train[columns], train[TARGET])
    return model.predict_proba(other[columns])[:, 1], model


def time_folds(df, n_splits=5):
    """Plis chronologiques : chaque pli valide sur des parties PLUS RÉCENTES que
    toutes celles de son entraînement (fenêtre d'entraînement qui s'agrandit)."""
    df = df.sort_values("game_creation").reset_index(drop=True)
    return df, list(TimeSeriesSplit(n_splits=n_splits).split(df))


def cross_validate(make_model, columns, df, use_scaling=False, n_splits=5, oof=True):
    """Une ligne de scores par pli. Tout (scaling, scaler, modèle) est réappris dans le pli."""
    df, folds = time_folds(df, n_splits)
    rows = []
    for k, (tr, va) in enumerate(folds, start=1):
        train, valid = df.iloc[tr], df.iloc[va]
        p, _ = fit_predict(make_model, columns, train, valid, use_scaling, oof)
        rows.append({"fold": k, "n_train": len(tr), "n_valid": len(va),
                     **evaluate(valid[TARGET], p)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 6. Comparer deux modèles sur les mêmes parties
# ---------------------------------------------------------------------------
def paired_bootstrap(y, p_a, p_b, metric=log_loss, n_boot=2000, seed=SEED):
    """Écart metric(b) − metric(a) et son intervalle de confiance à 95 %.

    « Apparié » : à chaque tirage, les MÊMES parties (tirées avec remise) servent
    aux deux modèles. On mesure ainsi l'incertitude de l'écart, bien plus petite
    que celle de chaque score pris seul (les deux modèles se trompent souvent
    sur les mêmes parties).
    """
    y, p_a, p_b = np.asarray(y), np.asarray(p_a), np.asarray(p_b)
    rng = np.random.default_rng(seed)
    n = len(y)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        if y[idx].min() == y[idx].max():  # tirage sans victoire ou sans défaite
            diffs[i] = np.nan
            continue
        diffs[i] = metric(y[idx], p_b[idx]) - metric(y[idx], p_a[idx])
    low, high = np.nanpercentile(diffs, [2.5, 97.5])
    return metric(y, p_b) - metric(y, p_a), low, high
