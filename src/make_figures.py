"""Figures du README : régénérées depuis la base, en anglais, dans docs/figures/.

Pourquoi un script plutôt que des captures des notebooks :
- les notebooks sont en français, le README est en anglais ;
- une figure du README doit pouvoir être refaite à l'identique (même découpage,
  mêmes graines aléatoires) après une nouvelle collecte : une seule commande ;
- le script n'invente rien : il réutilise features.py, models.py et explain.py,
  donc les chiffres sont ceux des notebooks 03 à 05.

Structure :
1. réglages communs (couleurs, noms anglais des variables, enregistrement) ;
2. une fonction par figure, qui reçoit ses données et renvoie le fichier écrit ;
3. main() : construit les données une fois, entraîne les deux modèles sur
   l'entraînement, appelle les quatre fonctions et affiche un résumé.

Utilisation (base PostgreSQL démarrée) :
    python src/make_figures.py
"""

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # pas de fenêtre : on écrit seulement des fichiers PNG
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from explain import linear_contributions, reliability_table, wilson_interval
from features import FEATURES, ROLE_FEATURES, ROOT, TARGET, build_features, time_split
from models import evaluate, fit_predict, make_lgbm, make_logit, time_folds

warnings.filterwarnings("ignore", message="X does not have valid feature names")

OUT_DIR = ROOT / "docs" / "figures"

# ---------------------------------------------------------------------------
# 1. Réglages communs
# ---------------------------------------------------------------------------
# Deux couleurs seulement, toujours la même pour le même modèle d'une figure à
# l'autre (bleu = régression logistique, orange = LightGBM).
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#8a8984"
SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"

BEST_LGBM = {"num_leaves": 4, "n_estimators": 200}  # meilleur réglage de l'étape 13

LABELS = {
    "gold_k": "Gold difference",
    "dragons_diff": "Dragon difference",
    "xp_k": "XP difference",
    "first_dragon": "First dragon",
    "first_tower": "First tower",
    "grubs_diff": "Void grub difference",
    "kills_diff": "Kill difference",
    "towers_diff": "Tower difference",
    "plates_diff": "Plate difference",
    "cs_diff": "CS difference",
    "first_blood": "First blood",
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GREY, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "font.size": 10.5, "lines.linewidth": 2, "lines.markersize": 6,
})


def save(fig, name):
    """Enregistre la figure en PNG (150 dpi : net sur GitHub, fichier léger)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 2. Les figures
# ---------------------------------------------------------------------------
def fig_gold_curve(df):
    """Taux de victoire du bleu par décile d'écart d'or à 15 min (IC 95 %)."""
    groups = pd.qcut(df["gold_k"], 10)
    t = df.groupby(groups, observed=True).agg(
        x=("gold_k", "mean"), n=(TARGET, "size"), wins=(TARGET, "sum"))
    t["p"] = t["wins"] / t["n"]
    t["lo"], t["hi"] = wilson_interval(t["wins"], t["n"])

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axhline(0.5, color=GREY, linestyle="--", linewidth=1)
    ax.errorbar(t["x"], t["p"], yerr=[t["p"] - t["lo"], t["hi"] - t["p"]],
                color=BLUE, marker="o", capsize=3)
    # Étiquettes seulement aux deux extrémités : ce sont les chiffres cités dans le README.
    for i in (0, len(t) - 1):
        ax.annotate(f"{t['p'].iloc[i]:.0%}", (t["x"].iloc[i], t["p"].iloc[i]),
                    textcoords="offset points", xytext=(0, 10), ha="center", color=INK)
    ax.set(xlabel="Blue minus red gold at 15:00 (thousands, decile mean)",
           ylabel="Blue win rate", ylim=(0, 1.05))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_title(f"Gold at 15 minutes and the final result ({len(df):,} matches)")
    return save(fig, "win_rate_by_gold.png")


def fig_learning_curve(train):
    """Log loss de validation selon le nombre de parties d'entraînement (comme le notebook 04)."""
    sorted_train, folds = time_folds(train, n_splits=5)
    pool_idx, valid_idx = folds[-1]
    pool, valid = sorted_train.iloc[pool_idx], sorted_train.iloc[valid_idx]
    models = {
        "Logistic regression": (make_logit, FEATURES, BLUE),
        "LightGBM": (lambda: make_lgbm(**BEST_LGBM), FEATURES + ROLE_FEATURES, ORANGE),
    }
    sizes = [400, 800, 1600, 2400, len(pool)]
    rng = np.random.default_rng(42)
    rows = []
    for n in sizes:
        draws = 1 if n == len(pool) else 5   # 5 tirages pour les petites tailles
        for _ in range(draws):
            sub = pool if n == len(pool) else pool.iloc[np.sort(rng.choice(len(pool), n, replace=False))]
            for name, (make, cols, _) in models.items():
                p, _ = fit_predict(make, cols, sub, valid)
                rows.append({"model": name, "n": n, "log_loss": evaluate(valid[TARGET], p)["log_loss"]})
    lc = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, (_, _, color) in models.items():
        s = lc[lc["model"] == name].groupby("n")["log_loss"].agg(["mean", "std"]).fillna(0)
        ax.errorbar(s.index, s["mean"], yerr=s["std"], color=color, marker="o",
                    capsize=3, label=name)
    ax.set(xlabel="Training matches", ylabel="Validation log loss (lower is better)")
    ax.set_title("Learning curve: more matches barely help the logistic regression")
    ax.legend(frameon=False)
    return save(fig, "learning_curve.png")


def fig_reliability(y_test, p):
    """Courbe de fiabilité de la logistique sur le test + répartition des probabilités."""
    t = reliability_table(y_test, p)
    fig, (ax, ax_h) = plt.subplots(2, 1, figsize=(6.5, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax.plot([0, 1], [0, 1], color=GREY, linestyle="--", linewidth=1, label="Perfect calibration")
    ax.errorbar(t["annoncé"], t["réel"], yerr=[t["réel"] - t["ic_bas"], t["ic_haut"] - t["réel"]],
                color=BLUE, marker="o", capsize=3, label="Test deciles (95% CI)")
    ax.set(ylabel="Observed blue win rate", xlim=(0, 1), ylim=(0, 1))
    ax.set_title(f"Calibration of the logistic regression ({len(y_test)} test matches)")
    ax.legend(frameon=False, loc="upper left")

    ax_h.hist(p, bins=20, range=(0, 1), color=BLUE, edgecolor=SURFACE, linewidth=2)
    ax_h.set(xlabel="Predicted blue win probability", ylabel="Matches")
    for a in (ax, ax_h):
        a.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    fig.tight_layout()
    return save(fig, "calibration.png")


def fig_shap(contrib):
    """Importance moyenne |SHAP| des 11 variables de la logistique, sur le test."""
    imp = contrib.abs().mean().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh([LABELS.get(c, c) for c in imp.index], imp.values, color=BLUE, height=0.6)
    for y, v in enumerate(imp.values):
        ax.text(v + imp.max() * 0.01, y, f"{v:.2f}", va="center", color=INK_2, fontsize=9.5)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, imp.max() * 1.12)  # place pour les étiquettes
    ax.set(xlabel="Mean |SHAP value| on test matches (log-odds)")
    ax.set_title("What drives the 15-minute prediction")
    return save(fig, "shap_importance.png")


# ---------------------------------------------------------------------------
# 3. Programme principal
# ---------------------------------------------------------------------------
def main():
    df = build_features()
    train, test = time_split(df, test_frac=0.2)
    y_test = test[TARGET].to_numpy()
    p_logit, logit = fit_predict(make_logit, FEATURES, train, test)
    contrib, _ = linear_contributions(logit, test[FEATURES])

    print(f"{len(df)} parties : {len(train)} entraînement, {len(test)} test.")
    print(f"Contrôle : log loss de la logistique sur le test = "
          f"{evaluate(y_test, p_logit)['log_loss']:.4f} (attendu : 0.5242)")
    for path in [fig_gold_curve(df), fig_learning_curve(train),
                 fig_reliability(y_test, p_logit), fig_shap(contrib)]:
        print(f"écrit : {path.relative_to(ROOT)} ({path.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
