# Contexte du projet (pour reprendre une conversation)

## Projet
LoL Analytics : analyse de parties League of Legends via l'API Riot, projet perso IA/data publié sur GitHub (pour le CV). Le plan complet est dans PLAN.md. Mon niveau et la façon de travailler sont dans CLAUDE.md (fichier local).

## Environnement
- Windows, VS Code, terminal PowerShell
- Dépôt local : C:\Users\pauld\OneDrive\Bureau\lol-analytics (branche main)
- GitHub : https://github.com/Paul-Delpierre/lol-analytics (public)
- Python 3.14.7, venv .venv (activé automatiquement dans le terminal de VS Code, le prompt commence par (.venv))
- Paquets (requirements.txt) : requests 2.34.2, pandas 3.0.6, numpy 2.5.4, python-dotenv 1.2.4, et leurs dépendances
- Je suis débutant en Git et en terminal : expliquer chaque commande donnée

## État d'avancement (vérifié le 21 oct. 2026 au soir)
- Étapes faites (cochées dans PLAN.md) : dépôt GitHub, venv + paquets, clé Riot + premiers appels (account-v1, match-v5 /ids et /matches/{id}).
- Tout était commité et poussé (main = origin/main). Historique :
  1. Initial project structure
  2. Update plan: mark repo creation as done
  3. Set up Python environment
  4. Etape 3 : premiers appels API Riot
  5. Ajout de CONTEXT.md pour reprendre le contexte
  6. (à faire) Mise à jour de CONTEXT.md + CLAUDE.md ajouté au .gitignore
- En cours : étape 4 « Comprendre le format JSON d'une partie et de sa timeline ». Le JSON d'une partie a été vu (voir plus bas). La timeline n'a pas encore été récupérée : l'étape 3 la mentionne, mais l'appel n'a pas été fait.

## Prochaine étape (détail)
1. Créer src/explore_timeline.py : appeler /lol/match/v5/matches/{matchId}/timeline pour EUW1_7995392565 et enregistrer data/timeline_exemple.json (mêmes conventions que explore.py).
2. Comprendre la structure de la timeline : info.frames (une image par minute), participantFrames (or, XP, niveau, sbires… par joueur), events (kills, objectifs, bâtiments…).
3. Noter les champs utiles au projet (état de la partie à 15 min, objectifs, résultat) : ce sera la base du MCD.
4. Cocher l'étape 4, mettre à jour ce fichier, commit + push.
Ensuite : étape 5 MCD / MLD (Merise) → sql/schema.sql, puis étape 6 PostgreSQL dans Docker.

## Fichiers
- src/explore.py : charge la clé avec load_dotenv(), appelle account-v1 (Riot ID -> puuid), match-v5 /ids (5 dernières parties), puis match-v5 /matches/{id} et enregistre le JSON dans data/match_exemple.json. Affiche la liste des ids.
- src/explore_timeline.py : à créer (voir prochaine étape).
- .env : contient RIOT_API_KEY=... (clé de développement, expire toutes les 24 h). Ignoré par Git.
- .env.example : modèle versionné, sans vraie clé. Contient aussi RIOT_PLATFORM=euw1, RIOT_REGION=europe et DATABASE_URL=postgresql://lol:lol@localhost:5432/lol, pas encore utilisés par le code (BASE est écrit en dur).
- data/match_exemple.json : JSON complet de la partie EUW1_7995392565. Le dossier data/ est ignoré par Git.
- requirements.txt : versions exactes des paquets (pip freeze).
- README.md : présentation en anglais (objectifs, structure, mention légale Riot), à compléter avec les résultats.
- PLAN.md : plan par étapes avec cases à cocher.
- CLAUDE.md : contexte pour Claude Code (local, ignoré par Git).
- sql/, notebooks/, tests/ : vides (un .gitkeep chacun).

## Code existant (conventions)
- HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
- BASE = "https://europe.api.riotgames.com" (région europe pour account-v1 et match-v5)
- Fonction get(path, **params) : requests.get avec HEADERS et timeout=10, puis r.raise_for_status(), renvoie r.json()
- Riot ID utilisé : TECHNIQUEMENT#99999
- Exemple d'id de partie : EUW1_7995392565

## Structure du JSON match (déjà vue)
- metadata : matchId, liste des puuid
- info.participants : 10 joueurs (championName, kills, deaths, assists, win, teamId, puuid...)
- info.teams : 2 équipes (teamId 100 et 200) avec win, bans, objectives

## À corriger (repéré, pas encore fait)
- requirements.txt est encodé en UTF-16 (effet de `pip freeze > requirements.txt` dans PowerShell) : GitHub l'affiche mal. Correction : l'ouvrir dans VS Code, cliquer sur « UTF-16 LE » en bas à droite → « Enregistrer avec l'encodage » → « UTF-8 », puis commit. Les prochaines fois : `pip freeze | Out-File -Encoding utf8 requirements.txt`.
- Plus tard (étape collecte) : sortir get() dans un module commun et lire la région depuis .env au lieu de l'écrire en dur.

## Décision en attente
- Sortir le dossier de OneDrive : OneDrive synchronise .venv et data/ (des milliers de fichiers), ce qui ralentit et peut bloquer des fichiers. À faire au plus tard avant l'étape collecte. Procédure : fermer VS Code, supprimer .venv, déplacer le dossier (ex. C:\Users\pauld\projets\lol-analytics), le rouvrir dans VS Code, recréer le venv (python -m venv .venv), réinstaller (pip install -r requirements.txt), vérifier avec git status. Puis mettre à jour le chemin dans ce fichier.

## Problèmes déjà rencontrés
- KeyError 'RIOT_API_KEY' : .env était vide (fichier non sauvegardé, Ctrl+S)
- 401 Unauthorized : clé expirée, à régénérer sur developer.riotgames.com puis la remettre dans .env
- Warning Git LF/CRLF sur Windows : sans danger
- Ctrl+P ne trouve pas les fichiers de data/ car ils sont ignorés par Git : ouvrir avec "code data/fichier.json" (pareil pour CLAUDE.md)

## Règles
- Ne jamais committer .env, data/ ni CLAUDE.md
- Ne jamais coller la clé Riot dans le chat (afficher .env avec (Get-Content .env) -replace '=.*','=***')
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public
- À la fin de chaque étape : mettre à jour PLAN.md et CONTEXT.md dans le dépôt (commit + push), puis les recopier dans les documents du Project claude.ai
