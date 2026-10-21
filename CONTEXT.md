# Contexte du projet (pour reprendre une conversation)

## Projet
LoL Analytics : analyse de parties League of Legends via l'API Riot, projet perso IA/data publié sur GitHub (pour le CV). Le plan complet est dans PLAN.md.

## Environnement
- Windows, VS Code, terminal PowerShell
- Dépôt : ~/OneDrive/Bureau/lol-analytics (branche main)
- Venv : .venv (activé automatiquement dans le terminal de VS Code, le prompt commence par (.venv))
- Paquets : requests, pandas, python-dotenv
- Je suis débutant en Git et en terminal : expliquer chaque commande donnée

## État d'avancement
- Étapes faites (cochées dans PLAN.md) : dépôt GitHub, venv + paquets, clé Riot + premiers appels (account-v1, match-v5 /ids et /matches/{id})
- En cours : "Comprendre le format JSON d'une partie et de sa timeline"
- À faire ensuite : MCD/MLD (Merise) -> sql/schema.sql, puis PostgreSQL dans Docker

## Fichiers
- src/explore.py : charge la clé avec load_dotenv(), appelle account-v1 (Riot ID -> puuid), match-v5 /ids (5 dernières parties), puis match-v5 /matches/{id} et enregistre le JSON dans data/match_exemple.json. Affiche la liste des ids.
- src/explore_timeline.py : à créer. Appelle match-v5 /matches/{id}/timeline et enregistre data/timeline_exemple.json.
- .env : contient RIOT_API_KEY=... (clé de développement, expire toutes les 24 h). Ignoré par Git.
- .env.example : modèle versionné, sans vraie clé.
- data/ : JSON d'exemple, ignoré par Git.
- PLAN.md : plan par étapes avec cases à cocher.

## Code existant (conventions)
- HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
- BASE = "https://europe.api.riotgames.com" (région europe pour account-v1 et match-v5)
- Fonction get(path, **params) : requests.get avec HEADERS, puis r.raise_for_status(), renvoie r.json()
- Riot ID utilisé : TECHNIQUEMENT#99999
- Exemple d'id de partie : EUW1_7995392565

## Structure du JSON match (déjà vue)
- metadata : matchId, liste des puuid
- info.participants : 10 joueurs (championName, kills, deaths, assists, win, teamId, puuid...)
- info.teams : 2 équipes (teamId 100 et 200) avec win, bans, objectives

## Problèmes déjà rencontrés
- KeyError 'RIOT_API_KEY' : .env était vide (fichier non sauvegardé, Ctrl+S)
- 401 Unauthorized : clé expirée, à régénérer sur developer.riotgames.com puis la remettre dans .env
- Warning Git LF/CRLF sur Windows : sans danger
- Ctrl+P ne trouve pas les fichiers de data/ car ils sont ignorés par Git : ouvrir avec "code data/fichier.json"

## Règles
- Ne jamais committer .env ni data/
- Ne jamais coller la clé Riot dans le chat (afficher .env avec (Get-Content .env) -replace '=.*','=***')
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public