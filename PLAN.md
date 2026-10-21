# Plan — LoL Analytics (1 h/jour)

## 26 oct. – 8 nov. : bases
- [x] Créer le dépôt GitHub et faire le premier commit
- [x] Environnement Python (venv) + `requests`, `pandas`, `python-dotenv`
- [X] Clé de dev Riot → `.env` ; premiers appels : account-v1 (Riot ID → PUUID), match-v5 (liste, match, timeline)
- [ ] Comprendre le format JSON d'une partie et de sa timeline
- [ ] MCD / MLD (Merise) → `sql/schema.sql`
- [ ] PostgreSQL dans Docker

## 9 – 22 nov. : collecte
- [ ] Script de collecte : limites (20 req/s, 100 req/2 min), erreurs 429, reprise
- [ ] Insertion en base + contrôles qualité (doublons, parties remake, valeurs manquantes)
- [ ] Lancer la collecte en fond (objectif : plusieurs milliers de parties)

## 23 nov. – 6 déc. : analyse et stats
- [ ] Analyse exploratoire (notebook)
- [ ] 2-3 questions testées : régression logistique avec variables de contrôle, intervalles de confiance

## 7 – 20 déc. : modèle à 15 min → v1 publique
- [ ] Features à 15 min (or, XP, objectifs, kills…)
- [ ] Régression logistique vs LightGBM, validation croisée sans fuite
- [ ] Calibration (Brier, courbe de fiabilité), SHAP
- [ ] README en anglais avec résultats et figures

## Janvier : deep learning
- [ ] Tutoriel PyTorch
- [ ] GRU : probabilité de victoire minute par minute, comparaison avec LightGBM

## Février : produit → v2
- [ ] Appli Streamlit (Riot ID → parties, courbe, moments clés)
- [ ] Docker Compose (appli + base), tests pytest, GitHub Actions
- [ ] GIF de démo dans le README

## Règles
- Ne jamais committer `.env` ni `data/`
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public
