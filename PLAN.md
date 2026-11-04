# Plan — LoL Analytics (1 h/jour)

## 26 oct. – 8 nov. : bases
- [x] Créer le dépôt GitHub et faire le premier commit
- [x] Environnement Python (venv) + `requests`, `pandas`, `python-dotenv`
- [x] Clé de dev Riot → `.env` ; premiers appels : account-v1 (Riot ID → PUUID), match-v5 (liste, match, timeline)
- [x] Comprendre le format JSON d'une partie et de sa timeline
- [x] MCD / MLD (Merise) → `sql/schema.sql`
- [x] PostgreSQL dans Docker

## 9 – 22 nov. : collecte
- [x] Script de collecte : limites (20 req/s, 100 req/2 min), erreurs 429, reprise
- [x] Insertion en base + contrôles qualité (doublons, parties remake, valeurs manquantes)
- [x] Lancer la collecte en fond (objectif : plusieurs milliers de parties)

## 23 nov. – 6 déc. : analyse et stats
- [x] Analyse exploratoire (notebook)
- [x] 2-3 questions testées : régression logistique avec variables de contrôle, intervalles de confiance

## 7 – 20 déc. : modèle à 15 min → v1 publique
- [x] Features à 15 min (or, XP, objectifs, kills…)
- [x] Score de scaling des compositions (calculé sur les parties d'entraînement) + interaction avec l'écart d'or
- [x] Régression logistique vs LightGBM, validation croisée sans fuite
- [x] Améliorer le modèle : courbe d'apprentissage, nouvelles variables (or 10→15 min, dragons…) — aucun gain sur le test, la logistique de l'étape 13 est gardée
- [x] Calibration (Brier, courbe de fiabilité), SHAP — probabilités déjà bien calibrées, pas de recalibrage
- [x] README en anglais avec résultats et figures (src/make_figures.py → docs/figures/) — v1 publique

## Janvier : deep learning
- [x] Tutoriel PyTorch (logistique refaite en PyTorch, MLP : aucun gain)
- [x] GRU : probabilité de victoire minute par minute, comparaison avec LightGBM — aucun gain sur la logistique par minute, gardée pour l'appli
- [x] Bonus : mini démo en direct (src/live.py : API locale « Live Client Data » → probabilité chaque minute) — or retiré (valeur des objets = mauvais substitut), logistique par minute « sans or » 0,5365 vs 0,5327 ; usage perso et analyse uniquement, jamais en compétition (règles Riot)

## Février : produit → v2
- [x] Appli Streamlit (Riot ID → parties, courbe, moments clés) — src/app.py, mêmes variables qu'à l'entraînement (écart 0 sur 200 parties), bilan de fiabilité par joueur
- [ ] Docker Compose (appli + base), tests pytest, GitHub Actions
- [ ] GIF de démo dans le README

## Règles
- Ne jamais committer `.env` ni `data/`
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public
