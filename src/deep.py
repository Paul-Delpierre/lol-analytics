"""Réseaux de neurones PyTorch : victoire à 15 min (étape 16) et minute par minute (étape 17).

Ce module regroupe les briques des notebooks 06 et 07 :
1. les modèles : LogisticNet (une seule couche linéaire = la régression logistique)
   et MLP (une couche cachée : le plus petit « vrai » réseau de neurones) ;
2. train_model() : LA boucle d'entraînement (mini-lots, optimiseur, arrêt précoce sur
   un jeu de validation). C'est elle qu'on réutilisera telle quelle pour le GRU ;
3. predict_proba() : probabilités de victoire du bleu, en numpy ;
4. TorchClassifier : enveloppe un réseau dans l'interface de scikit-learn (fit /
   predict_proba). Grâce à elle, les fonctions de src/models.py (cross_validate,
   fit_predict, paired_bootstrap) évaluent un réseau EXACTEMENT comme la logistique
   et LightGBM : mêmes plis chronologiques, mêmes métriques, aucune fuite ;
5. (étape 17) WinGRU : le réseau récurrent qui lit une partie minute par minute et
   donne une probabilité à chaque minute, et masked_bce(), sa fonction de perte qui
   ignore les minutes « vides » (après la fin de la partie).

Utilisation :
    from deep import LogisticNet, MLP, train_model, predict_proba, TorchClassifier  # notebook 06
    from deep import WinGRU, masked_bce                                             # notebook 07
"""

import copy

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

SEED = 42


def set_seed(seed=SEED):
    """Rend les résultats reproductibles : poids de départ et ordre des mini-lots."""
    torch.manual_seed(seed)
    np.random.seed(seed)


def to_tensor(a):
    """DataFrame / Series / tableau numpy -> tenseur float32 (le type par défaut de PyTorch)."""
    return torch.as_tensor(np.asarray(a, dtype=np.float32))


# ---------------------------------------------------------------------------
# 1. Les modèles
# ---------------------------------------------------------------------------
class LogisticNet(nn.Module):
    """Régression logistique écrite comme un réseau : logit = x · w + b.

    Le modèle renvoie le LOGIT (un nombre de −∞ à +∞), pas la probabilité.
    La sigmoïde est appliquée par la fonction de perte (BCEWithLogitsLoss) à
    l'entraînement et par predict_proba() ensuite : c'est plus stable
    numériquement que de calculer log(sigmoïde(x)) en deux temps.
    """

    def __init__(self, n_features):
        super().__init__()
        self.linear = nn.Linear(n_features, 1)

    def forward(self, x):
        return self.linear(x).squeeze(-1)  # (lot, 1) -> (lot,)


class MLP(nn.Module):
    """Perceptron multicouche : linéaire -> ReLU -> dropout -> linéaire.

    La couche cachée (hidden neurones) permet des effets NON linéaires et des
    interactions entre variables, ce que la logistique ne sait pas faire seule.
    Le dropout éteint au hasard une part des neurones à chaque mini-lot pendant
    l'entraînement : le réseau ne peut pas compter sur un neurone précis, il
    apprend moins le bruit (régularisation).
    """

    def __init__(self, n_features, hidden=16, dropout=0.2):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.layers(x).squeeze(-1)


# ---------------------------------------------------------------------------
# 2. La boucle d'entraînement
# ---------------------------------------------------------------------------
def mean_loss(model, X, y, loss_fn):
    """Perte moyenne sur un jeu entier, sans dropout et sans calcul de gradient."""
    model.eval()
    with torch.no_grad():
        return loss_fn(model(X), y).item()


def train_model(model, train, valid, lr=1e-2, weight_decay=0.0, batch_size=128,
                max_epochs=300, patience=20, seed=SEED, verbose=False,
                loss_fn=None, clip=None):
    """Entraîne `model` sur train = (X, y) ; arrêt précoce sur valid = (X, y).

    Une « époque » = un passage sur toutes les parties d'entraînement, par mini-lots
    de batch_size parties mélangées. Après chaque époque on mesure la perte sur la
    validation ; on garde les poids de la MEILLEURE époque et on s'arrête quand la
    validation ne s'améliore plus depuis `patience` époques (le réseau commence à
    apprendre le bruit de l'entraînement : surapprentissage).

    weight_decay : pénalité L2 sur les poids (AdamW), comme le C de la logistique.
    loss_fn : fonction de perte ; par défaut la log loss d'une probabilité par ligne
    (BCEWithLogitsLoss). Le GRU passe masked_bce (une probabilité par minute).
    clip : si donné, limite la norme des gradients (utile pour les réseaux récurrents,
    dont les gradients peuvent « exploser » en remontant le temps). Les valeurs par
    défaut (None) gardent exactement le comportement de l'étape 16.

    Renvoie un DataFrame : une ligne par époque (train_loss, valid_loss).
    Le modèle est modifié sur place et revient à sa meilleure époque.
    """
    set_seed(seed)
    loader = DataLoader(TensorDataset(*train), batch_size=batch_size, shuffle=True)
    loss_fn = loss_fn or nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_loss, best_state, best_epoch, history = np.inf, None, 0, []
    for epoch in range(1, max_epochs + 1):
        model.train()  # active le dropout
        for xb, yb in loader:
            optimizer.zero_grad()          # 1. effacer les gradients du lot précédent
            loss = loss_fn(model(xb), yb)  # 2. prédire et mesurer l'erreur
            loss.backward()                # 3. calculer les gradients (autograd)
            if clip:
                nn.utils.clip_grad_norm_(model.parameters(), clip)
            optimizer.step()               # 4. corriger les poids
        row = {"epoch": epoch,
               "train_loss": mean_loss(model, *train, loss_fn),
               "valid_loss": mean_loss(model, *valid, loss_fn)}
        history.append(row)
        if verbose and epoch % 10 == 0:
            print(f"époque {epoch:3d}  train {row['train_loss']:.4f}  valid {row['valid_loss']:.4f}")

        if row["valid_loss"] < best_loss - 1e-5:
            best_loss, best_epoch = row["valid_loss"], epoch
            best_state = copy.deepcopy(model.state_dict())
        elif epoch - best_epoch >= patience:
            break

    model.load_state_dict(best_state)
    history = pd.DataFrame(history)
    history.attrs["best_epoch"] = best_epoch
    return history


def predict_proba(model, X):
    """Probabilités de victoire du bleu (numpy), modèle en mode évaluation."""
    model.eval()
    with torch.no_grad():
        return torch.sigmoid(model(X)).numpy()


# ---------------------------------------------------------------------------
# 3. L'enveloppe scikit-learn
# ---------------------------------------------------------------------------
class TorchClassifier:
    """Un réseau PyTorch avec l'interface de scikit-learn : fit(X, y), predict_proba(X).

    fit() fait tout ce qu'il faut pour rester SANS FUITE quand cross_validate()
    l'appelle dans chaque pli :
    - le StandardScaler est appris sur les parties d'entraînement du pli seulement ;
    - les `valid_frac` parties les plus RÉCENTES de cet entraînement (les lignes
      arrivent triées par date) servent à l'arrêt précoce ; la validation du pli,
      elle, n'est jamais vue.

    make_net : fonction n_features -> réseau neuf (ex. lambda n: MLP(n, hidden=16)).
    Les autres arguments vont à train_model().
    """

    def __init__(self, make_net, valid_frac=0.15, **train_kwargs):
        self.make_net = make_net
        self.valid_frac = valid_frac
        self.train_kwargs = train_kwargs

    def fit(self, X, y):
        X, y = np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32)
        cut = int(len(X) * (1 - self.valid_frac))
        self.scaler_ = StandardScaler().fit(X[:cut])
        Xs = to_tensor(self.scaler_.transform(X))
        y = to_tensor(y)

        set_seed(self.train_kwargs.get("seed", SEED))  # mêmes poids de départ à chaque fit
        self.net_ = self.make_net(X.shape[1])
        self.history_ = train_model(self.net_, (Xs[:cut], y[:cut]), (Xs[cut:], y[cut:]),
                                    **self.train_kwargs)
        return self

    def predict_proba(self, X):
        Xs = to_tensor(self.scaler_.transform(np.asarray(X, dtype=np.float32)))
        p = predict_proba(self.net_, Xs)
        return np.column_stack([1 - p, p])  # même format que scikit-learn


# ---------------------------------------------------------------------------
# 4. Le GRU minute par minute (étape 17)
# ---------------------------------------------------------------------------
class WinGRU(nn.Module):
    """Lit une partie minute par minute et donne un logit de victoire du bleu à CHAQUE minute.

    Entrée : (lot, minutes, variables). Le GRU tient à jour un état caché de `hidden`
    nombres, un résumé de la partie « jusqu'ici » ; une couche linéaire (la même pour
    toutes les minutes) transforme chaque résumé en logit. Sortie : (lot, minutes).

    Le GRU est UNIDIRECTIONNEL : l'état de la minute t ne dépend que des minutes 1 à t.
    C'est ce qui garantit l'absence de fuite temporelle (un GRU bidirectionnel lirait
    aussi la fin de la partie). Pour la même raison, les minutes vides ajoutées APRÈS
    la fin des parties courtes (le « padding ») ne changent rien aux minutes réelles.
    """

    def __init__(self, n_features, hidden=32, layers=1, dropout=0.2):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, num_layers=layers, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        states, _ = self.gru(x)                              # (lot, minutes, hidden)
        return self.head(self.dropout(states)).squeeze(-1)   # (lot, minutes)


def masked_bce(logits, y):
    """Log loss moyenne sur les minutes RÉELLES seulement.

    y a la forme (lot, minutes) : le résultat de la partie (0 ou 1) répété à chaque
    minute jouée, et NaN après la fin de la partie. Le masque écarte ces NaN : chaque
    (partie, minute) jouée pèse pareil, comme une ligne du tableau de LightGBM.
    """
    mask = ~torch.isnan(y)
    return nn.functional.binary_cross_entropy_with_logits(logits[mask], y[mask])
