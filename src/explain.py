"""Vérifier et expliquer les probabilités des modèles de victoire (étape 14).

Deux questions, deux parties :
1. Calibration : quand le modèle annonce 70 %, le bleu gagne-t-il vraiment 70 % du
   temps ? reliability_table(), expected_calibration_error(), calibration_fit(),
   oof_predictions() et fit_recalibrator().
2. Explications (valeurs de SHAP) : pour UNE partie, combien chaque variable a-t-elle
   poussé la probabilité vers le bleu ou vers le rouge ? linear_contributions()
   (régression logistique) et tree_contributions() (LightGBM).

Pas de dépendance au paquet `shap` : pour ces deux modèles, les valeurs de SHAP se
calculent exactement avec ce qu'on a déjà (voir les deux fonctions), ce qui évite un
paquet lourd de plus et montre qu'on sait d'où viennent les chiffres. Vérifié le
2 nov. 2026 : mêmes valeurs que shap.LinearExplainer et shap.TreeExplainer (écart < 1e-15).

Utilisation (notebook 05) :
    from explain import reliability_table, linear_contributions, tree_contributions
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from features import TARGET
from models import fit_predict, time_folds


# ---------------------------------------------------------------------------
# 1. Calibration
# ---------------------------------------------------------------------------
def wilson_interval(wins, n, z=1.96):
    """Intervalle de confiance à 95 % d'une proportion (Wilson : correct même près de 0 ou 1)."""
    p = wins / n
    center = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return center - half, center + half


def reliability_table(y, p, n_bins=10):
    """Parties regroupées par probabilité annoncée (déciles), avec le taux de victoire réel.

    Déciles plutôt que tranches fixes (0-10 %, 10-20 %…) : chaque groupe a le même
    nombre de parties, donc des taux réels aussi précis les uns que les autres.
    """
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["groupe"] = pd.qcut(d["p"].rank(method="first"), n_bins, labels=False) + 1
    t = d.groupby("groupe").agg(parties=("y", "size"), annoncé=("p", "mean"), réel=("y", "mean"),
                                victoires=("y", "sum"))
    t["ic_bas"], t["ic_haut"] = wilson_interval(t["victoires"], t["parties"])
    t["dans_ic"] = (t["annoncé"] >= t["ic_bas"]) & (t["annoncé"] <= t["ic_haut"])
    return t.drop(columns="victoires")


def expected_calibration_error(y, p, n_bins=10):
    """Écart moyen |annoncé − réel| sur les déciles, pondéré par le nombre de parties."""
    t = reliability_table(y, p, n_bins)
    return float(np.average((t["annoncé"] - t["réel"]).abs(), weights=t["parties"]))


def calibration_fit(y, p):
    """Pente et ordonnée de calibration (avec IC 95 %) : régression logistique de y sur logit(p).

    Pente = 1 et ordonnée = 0 : probabilités parfaitement calibrées.
    Pente < 1 : modèle trop sûr de lui (ses 90 % devraient être plus proches de 50 %) ;
    pente > 1 : trop timide. Ordonnée < 0 : il surestime le bleu en général, > 0 : il le sous-estime.
    statsmodels plutôt que scikit-learn : il donne les intervalles de confiance directement.
    """
    x = sm.add_constant(logit(np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)))
    fit = sm.Logit(np.asarray(y, dtype=float), x).fit(disp=0)
    (b0, b1), ci = fit.params, fit.conf_int(0.05)
    return {"pente": b1, "pente IC": f"{ci[1, 0]:.2f} à {ci[1, 1]:.2f}",
            "ordonnée": b0, "ordonnée IC": f"{ci[0, 0]:.2f} à {ci[0, 1]:.2f}"}


def oof_predictions(make_model, columns, df, n_splits=5):
    """Probabilités « hors pli » sur l'entraînement : chaque partie est prédite par un modèle
    qui ne l'a pas vue (plis chronologiques de l'étape 13). Sert à apprendre un recalibrage
    sans toucher au test. Les parties du 1er bloc (jamais en validation) n'ont pas de prédiction.
    """
    df, folds = time_folds(df, n_splits)
    parts = []
    for tr, va in folds:
        p, _ = fit_predict(make_model, columns, df.iloc[tr], df.iloc[va])
        parts.append(pd.DataFrame({"y": df.iloc[va][TARGET].to_numpy(), "p": p}))
    return pd.concat(parts, ignore_index=True)


def fit_recalibrator(y, p, method="platt"):
    """Apprend une correction des probabilités ; renvoie une fonction p -> p corrigée.

    - platt : une petite régression logistique sur logit(p) (corrige pente et ordonnée,
      2 paramètres, peu de risque de surapprentissage) ;
    - isotonic : une fonction en escalier croissante (plus souple, demande plus de données).
    """
    y, p = np.asarray(y), np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    if method == "platt":
        m = LogisticRegression(C=np.inf).fit(logit(p).reshape(-1, 1), y)
        return lambda q: m.predict_proba(logit(np.clip(q, 1e-6, 1 - 1e-6)).reshape(-1, 1))[:, 1]
    if method == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-3, y_max=1 - 1e-3).fit(p, y)
        return iso.predict
    raise ValueError(method)


# ---------------------------------------------------------------------------
# 2. Explications (valeurs de SHAP)
# ---------------------------------------------------------------------------
def linear_contributions(pipeline, X):
    """Valeurs de SHAP exactes d'une régression logistique (pipeline StandardScaler + logit).

    Pour un modèle linéaire, la contribution d'une variable à une partie est
    coefficient × (valeur − valeur moyenne), en log-odds (l'échelle « avant la courbe
    en S »). La moyenne vient de l'entraînement (le StandardScaler la garde), et
    comme les variables sont centrées, la « base » est la constante du modèle :
    la prédiction pour une partie moyenne. Base + somme des contributions = log-odds
    prédit, exactement.

    Renvoie (contributions : DataFrame parties × variables, base : float).
    """
    scaler, model = pipeline[0], pipeline[-1]
    z = (np.asarray(X, dtype=float) - scaler.mean_) / scaler.scale_
    contrib = pd.DataFrame(z * model.coef_[0], columns=list(X.columns), index=X.index)
    return contrib, float(model.intercept_[0])


def tree_contributions(lgbm, X):
    """Valeurs de SHAP de LightGBM, calculées par LightGBM lui-même (TreeSHAP, exact).

    predict(..., pred_contrib=True) renvoie une colonne par variable + une dernière
    colonne = la base (prédiction moyenne), le tout en log-odds.
    """
    raw = lgbm.booster_.predict(np.asarray(X, dtype=float), pred_contrib=True)
    contrib = pd.DataFrame(raw[:, :-1], columns=list(X.columns), index=X.index)
    return contrib, float(raw[0, -1])


def explain_game(contrib_row, base, top=6):
    """Les variables qui ont le plus pesé sur UNE partie, et le chemin de la probabilité.

    Les autres variables sont regroupées en une ligne « autres ».
    """
    order = contrib_row.abs().sort_values(ascending=False).index
    main = contrib_row[order[:top]]
    rest = contrib_row[order[top:]].sum()
    steps = pd.concat([main, pd.Series({"autres variables": rest})])
    table = pd.DataFrame({"contribution (log-odds)": steps})
    table["probabilité après"] = expit(base + steps.cumsum())
    return table, float(expit(base)), float(expit(base + contrib_row.sum()))
