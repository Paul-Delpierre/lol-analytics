# Contexte du projet (pour reprendre une conversation)

## Projet
LoL Analytics : analyse de parties League of Legends via l'API Riot, projet perso IA/data publié sur GitHub (pour le CV). Le plan complet est dans PLAN.md. Mon niveau et la façon de travailler sont dans CLAUDE.md (fichier local).

## Façon de travailler (règles fixées les 21 et 22 oct. 2026)
- Claude écrit tout le code ; Paul n'en écrit pas, mais chaque morceau est expliqué en détail (pourquoi + comment, ligne par ligne).
- Chaque étape du plan = un guide détaillé, pas à pas : commandes expliquées, ce qu'on doit voir, erreurs possibles, points de contrôle.
- CONTEXT.md est rempli et mis à jour uniquement par Claude, jamais par Paul. Si Claude n'a pas accès au dossier local, il fournit le fichier complet et Paul le colle tel quel.
- Paul est débutant en Git et en terminal : expliquer chaque commande donnée.

## Environnement
- Windows, VS Code, terminal PowerShell
- Dépôt local : C:\Users\pauld\OneDrive\Bureau\lol-analytics (branche main)
- GitHub : https://github.com/Paul-Delpierre/lol-analytics (public)
- Python 3.14.7, venv .venv (activé automatiquement dans le terminal de VS Code, le prompt commence par (.venv))
- Paquets (requirements.txt) : requests 2.34.2, pandas 3.0.6, numpy 2.5.4, python-dotenv 1.2.4, et leurs dépendances

## État d'avancement (mis à jour le 23 oct. 2026)
- Étapes faites (cochées dans PLAN.md) : dépôt GitHub, venv + paquets, clé Riot + premiers appels (account-v1, match-v5 /ids et /matches/{id}), étape 4 « Comprendre le format JSON d'une partie et de sa timeline », étape 5 « MCD / MLD → sql/schema.sql » (schéma écrit et testé le 23 oct.).
- Historique Git :
  1. Initial project structure
  2. Update plan: mark repo creation as done
  3. Set up Python environment
  4. Etape 3 : premiers appels API Riot
  5. Ajout de CONTEXT.md pour reprendre le contexte
  6. 9c987d4 Convert requirements to UTF-8, update CONTEXT.md and .gitignore
  7. Etape 4 : exploration de la timeline (explore_timeline.py, resume_timeline.py, PLAN.md, CONTEXT.md)
- Étape 4 en résumé : la timeline de EUW1_7995392565 a été récupérée (34 frames, partie d'environ 33 min) et enregistrée dans data/timeline_exemple.json. Sa structure est décrite plus bas.

## Prochaine étape : étape 6, PostgreSQL dans Docker
But : faire tourner PostgreSQL dans un conteneur Docker (docker-compose.yml), avec les identifiants de DATABASE_URL de .env.example (lol / lol / lol, port 5432), et créer les tables avec sql/schema.sql. Paul n'a encore jamais utilisé Docker : tout expliquer (image, conteneur, volume, port, docker compose up -d, psql dans le conteneur). Vérifier que Docker Desktop est installé et démarré.

## Étape 5 faite : décisions de conception (23 oct. 2026)
- sql/schema.sql = 7 tables : players(puuid), matches, teams (clé match_id + team_id), participants (clé match_id + participant_id, FK vers teams et players), participant_frames (match_id, participant_id, minute : toutes les frames gardées pour le GRU), events (event_id auto ; types CHAMPION_KILL, ELITE_MONSTER_KILL, BUILDING_KILL, TURRET_PLATE_DESTROYED), event_assists (table n,n entre events et participants).
- Choix : pas de win dans participants (déduit de teams) ; totalGold et pas currentGold ; killerId 0 de Riot -> NULL ; events.killer_team_id = équipe qui GAGNE l'objectif (pour BUILDING_KILL et TURRET_PLATE_DESTROYED, le teamId de Riot est l'équipe qui perd le bâtiment, donc on stocke 300 - teamId) ; puuid uniquement dans players (un seul endroit à pseudonymiser).
- Testé sur PostgreSQL 16 : le script s'exécute sans erreur et la partie EUW1_7995392565 se charge entièrement. Or à la minute 15 : équipe 100 = 26 387, équipe 200 = 27 591 (écart bleu - rouge = -1 204).
- Points à gérer à la collecte (étape 7) : convertir gameCreation (ms) en date ; killerId 0 -> NULL ; ignorer les events non listés ; parties de moins de 15 min (pas de frame 15) ; CHAMPION_KILL avec killerId 0 = exécution (tueur NULL, killer_team_id à déduire de la victime).
- Guide détaillé : guide-etape-5-mcd-mld.md (dans les fichiers du projet claude, pas dans le dépôt).

## Fichiers
- src/explore.py : charge la clé avec load_dotenv(), appelle account-v1 (Riot ID -> puuid), match-v5 /ids (5 dernières parties), puis match-v5 /matches/{MATCH_ID} (MATCH_ID = EUW1_7995392565, fixé en dur, comme explore_timeline.py) et enregistre le JSON dans data/match_exemple.json (encoding utf-8). Vérifie par un assert que le matchId correspond. Affiche la liste des ids.
- src/explore_timeline.py : appelle /lol/match/v5/matches/{matchId}/timeline pour EUW1_7995392565, enregistre data/timeline_exemple.json, affiche le nombre de frames.
- src/resume_timeline.py : relit data/timeline_exemple.json (aucun appel API), compte les types d'events et calcule l'écart d'or entre les équipes à 15 min.
- .env : contient RIOT_API_KEY=... (clé de développement, expire toutes les 24 h). Ignoré par Git.
- .env.example : modèle versionné, sans vraie clé. Contient aussi RIOT_PLATFORM=euw1, RIOT_REGION=europe et DATABASE_URL=postgresql://lol:lol@localhost:5432/lol, pas encore utilisés par le code (BASE est écrit en dur).
- data/match_exemple.json : JSON complet de la partie EUW1_7995392565. Ignoré par Git.
- data/timeline_exemple.json : timeline de la même partie (34 frames). Ignoré par Git.
- requirements.txt : versions exactes des paquets (pip freeze), en UTF-8. Pour le régénérer : `pip freeze | Out-File -Encoding utf8 requirements.txt` (sinon PowerShell l'écrit en UTF-16 et GitHub l'affiche mal).
- README.md : présentation en anglais (objectifs, structure, mention légale Riot), à compléter avec les résultats.
- PLAN.md : plan par étapes avec cases à cocher.
- CLAUDE.md : contexte pour Claude Code (local, ignoré par Git).
- sql/schema.sql : schéma PostgreSQL (7 tables, voir « Étape 5 faite »).
- notebooks/, tests/ : vides (un .gitkeep chacun).

## Code existant (conventions)
- HEADERS = {"X-Riot-Token": os.environ["RIOT_API_KEY"]}
- BASE = "https://europe.api.riotgames.com" (région europe pour account-v1 et match-v5)
- Fonction get(path, **params) : requests.get(BASE + path, headers=HEADERS, params=params, timeout=10), puis r.raise_for_status(), renvoie r.json()
- Enregistrement JSON : open(..., "w", encoding="utf-8") + json.dump(..., indent=2, ensure_ascii=False)
- Riot ID utilisé : TECHNIQUEMENT#99999
- Exemple d'id de partie : EUW1_7995392565

## Structure du JSON match
- metadata : matchId, liste des puuid
- info.participants : 10 joueurs (championName, kills, deaths, assists, win, teamId, puuid...)
- info.teams : 2 équipes (teamId 100 = bleue, 200 = rouge) avec win, bans, objectives

## Structure de la timeline
- metadata : matchId, liste des puuid.
- info.frameInterval = 60000 : une frame toutes les 60 000 ms (1 min).
- info.participants : lien participantId (1 à 10) ↔ puuid. Dans la timeline, les joueurs sont désignés par participantId, pas par puuid. En général 1-5 = équipe 100 (bleue), 6-10 = équipe 200 (rouge) : à vérifier avec teamId du JSON match.
- info.frames : liste des frames. frames[0] = minute 0, donc frames[15] = minute 15 (timestamp ≈ 900 000 ms). La dernière frame correspond à la fin exacte de la partie. Si la partie dure moins de 15 min (remake, abandon), frames[15] n'existe pas : à gérer à la collecte.
- Chaque frame contient :
  - timestamp (ms)
  - participantFrames : dictionnaire "1" à "10" (clés en texte), état de chaque joueur à cet instant : totalGold (or gagné depuis le début, à utiliser), currentGold (or en poche, à ne pas utiliser), xp, level, minionsKilled, jungleMinionsKilled (CS = la somme des deux), position {x, y}, championStats, damageStats.
  - events : ce qui s'est passé entre la frame précédente et celle-ci.
- Types d'events utiles :
  - CHAMPION_KILL : killerId, victimId, assistingParticipantIds
  - ELITE_MONSTER_KILL : monsterType (DRAGON, RIFTHERALD, HORDE = larves du Néant, BARON_NASHOR…), killerTeamId
  - BUILDING_KILL : tour ou inhibiteur ; teamId = l'équipe qui possède le bâtiment, donc celle qui l'a perdu
  - TURRET_PLATE_DESTROYED : plaques de tour (avant 14 min)
  - GAME_END : dans la dernière frame, avec winningTeam
  - Autres types (ITEM_PURCHASED, WARD_PLACED, SKILL_LEVEL_UP…) ignorés pour l'instant.

## Champs utiles pour l'état à 15 min (base du MCD)
Par équipe :
- Or total : somme des totalGold dans frames[15]
- XP totale, niveau moyen : xp, level dans frames[15]
- CS : minionsKilled + jungleMinionsKilled
- Kills : events CHAMPION_KILL des frames 1 à 15
- Dragons, larves, héraut : events ELITE_MONSTER_KILL
- Tours, plaques : BUILDING_KILL, TURRET_PLATE_DESTROYED
- Premier sang, première tour : premier event de ce type
- Résultat (la cible à prédire) : win dans le JSON match, ou GAME_END dans la timeline

## À corriger (repéré, pas encore fait)
- README.md : la section Setup ne dit pas de créer le venv ni de faire pip install -r requirements.txt. À compléter (en anglais) avant la v1 publique.
- Plus tard (étape collecte) : sortir get() dans un module commun et lire la région depuis .env au lieu de l'écrire en dur.

## Décision en attente
- Sortir le dossier de OneDrive : OneDrive synchronise .venv et data/ (des milliers de fichiers), ce qui ralentit et peut bloquer des fichiers. À faire au plus tard avant l'étape collecte. Procédure : fermer VS Code, supprimer .venv, déplacer le dossier (ex. C:\Users\pauld\projets\lol-analytics), le rouvrir dans VS Code, recréer le venv (python -m venv .venv), réinstaller (pip install -r requirements.txt), vérifier avec git status. Puis mettre à jour le chemin dans ce fichier.

## Problèmes déjà rencontrés
- KeyError 'RIOT_API_KEY' : .env était vide (fichier non sauvegardé, Ctrl+S)
- 401 Unauthorized : clé expirée, à régénérer sur developer.riotgames.com puis la remettre dans .env
- Warning Git LF/CRLF sur Windows : sans danger
- Ctrl+P ne trouve pas les fichiers de data/ car ils sont ignorés par Git : ouvrir avec "code data/fichier.json" (pareil pour CLAUDE.md)
- 22 oct. : une capture d'écran du terminal montrait le début de la clé Riot. Recadrer les captures avant de les envoyer.

## Règles
- Ne jamais committer .env, data/ ni CLAUDE.md
- Ne jamais coller la clé Riot dans le chat (afficher .env avec (Get-Content .env) -replace '=.*','=***')
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public
- À la fin de chaque étape : Claude met à jour CONTEXT.md, PLAN.md est coché, commit + push, puis PLAN.md et CONTEXT.md sont recopiés dans les documents du Project claude.ai
