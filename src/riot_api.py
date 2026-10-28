"""Client pour l'API Riot : respecte les limites de débit et gère les erreurs.

Utilisé par collect.py. Remplace la petite fonction get() des scripts
d'exploration (explore.py, explore_timeline.py).

Les messages passent par le module logging (et non print) : collect.py
choisit où ils vont (écran + fichier de log pour la collecte en fond).
"""

import logging
import time
from collections import deque

import requests

# Limites d'une clé de développement Riot : (nombre de requêtes, fenêtre en s).
DEV_KEY_LIMITS = [(20, 1), (100, 120)]

# Pause maximale entre deux essais : avec 8 essais, une coupure réseau ou une
# panne de Riot de 4 minutes environ est absorbée sans arrêter la collecte.
MAX_BACKOFF = 60

log = logging.getLogger(__name__)


class RiotKeyError(Exception):
    """Clé absente, expirée (401) ou refusée (403) : inutile de réessayer."""


class RateLimiter:
    """Attend juste ce qu'il faut pour ne jamais dépasser les limites.

    Pour chaque limite (n requêtes par fenêtre de w secondes), on garde
    l'heure des n dernières requêtes. Si la plus ancienne date de moins
    de w secondes, une nouvelle requête ferait n+1 dans la fenêtre :
    on dort jusqu'à ce qu'elle sorte de la fenêtre.
    """

    def __init__(self, limits=DEV_KEY_LIMITS):
        self.windows = [(n, w, deque(maxlen=n)) for n, w in limits]

    def wait(self):
        for n, w, times in self.windows:
            if len(times) == n:
                pause = times[0] + w - time.monotonic()
                if pause > 1:
                    log.info(f"  Limite de {n} requêtes / {w} s atteinte : pause de {pause:.0f} s")
                if pause > 0:
                    time.sleep(pause + 0.05)
        now = time.monotonic()
        for _, _, times in self.windows:
            times.append(now)


class RiotClient:
    def __init__(self, api_key, region="europe", limiter=None, session=None,
                 max_retries=8):
        if not api_key:
            raise RiotKeyError("RIOT_API_KEY est vide : vérifie le fichier .env")
        self.base = f"https://{region}.api.riotgames.com"
        self.limiter = limiter or RateLimiter()
        self.session = session or requests.Session()
        self.session.headers["X-Riot-Token"] = api_key
        self.max_retries = max_retries

    def get(self, path, **params):
        """Renvoie le JSON de la réponse, ou None si Riot répond 404."""
        for attempt in range(1, self.max_retries + 1):
            self.limiter.wait()
            try:
                r = self.session.get(self.base + path, params=params, timeout=10)
            except (requests.ConnectionError, requests.Timeout) as e:
                pause = min(2 ** attempt, MAX_BACKOFF)
                log.warning(f"  Réseau indisponible ({type(e).__name__}), "
                            f"nouvel essai dans {pause} s")
                time.sleep(pause)
                continue

            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code in (401, 403):
                raise RiotKeyError(
                    f"Erreur {r.status_code} sur {path}\n"
                    f"Réponse de Riot : {r.text[:200]}\n"
                    "Clé Riot expirée ou invalide ? "
                    "Régénère-la sur developer.riotgames.com et mets-la dans .env"
                )
            if r.status_code == 429:
                pause = int(r.headers.get("Retry-After", 10))
                log.warning(f"  429 Too Many Requests : pause de {pause} s")
                time.sleep(pause)
                continue
            if r.status_code >= 500:
                pause = min(2 ** attempt, MAX_BACKOFF)
                log.warning(f"  Erreur serveur {r.status_code}, nouvel essai dans {pause} s")
                time.sleep(pause)
                continue
            r.raise_for_status()  # autre code (400...) : erreur dans notre requête

        raise RuntimeError(f"Échec après {self.max_retries} essais : {path}")
