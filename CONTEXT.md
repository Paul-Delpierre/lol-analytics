# Contexte du projet (pour reprendre une conversation)

## Projet
LoL Analytics : analyse de parties League of Legends via l'API Riot, projet perso IA/data publié sur GitHub (pour le CV). Le plan complet est dans PLAN.md.

## Environnement
- Windows, VS Code, terminal PowerShell
- Dépôt local : C:\Users\pauld\projets\lol-analytics (branche main). Sorti de OneDrive le 28 oct. 2026 (ancien chemin : C:\Users\pauld\OneDrive\Bureau\lol-analytics). Garder le nom du dossier lol-analytics : Docker nomme le volume de la base d'après lui (lol-analytics_pgdata).
- GitHub : https://github.com/Paul-Delpierre/lol-analytics (public)
- Python 3.14.7, venv .venv (activé automatiquement dans le terminal de VS Code, le prompt commence par (.venv))
- Paquets (requirements.txt) : requests 2.34.2, pandas 3.0.6, numpy 2.5.4, python-dotenv 1.2.4, psycopg 3.3.6 + psycopg-binary 3.3.6 (ajoutés à l'étape 6), matplotlib 3.11.2 + ipykernel 7.4.0 (ajoutés à l'étape 10), statsmodels 0.15.0 (étape 11), scikit-learn 1.9.1 + lightgbm 4.7.0 (étape 13), torch 2.14.1 en version CPU (étape 16, pas de carte NVIDIA), streamlit 1.66.1 + altair 6.3.0 + pyarrow 26.0.1 (étape 18), pytest (étape 19), et leurs dépendances. Hors requirements.txt : playwright 1.63.0 + son navigateur Chromium (étape 20, outil pour fabriquer le GIF de démo, pas une dépendance du projet). requirements-app.txt (étape 19) : la liste des seuls paquets de l'appli (sans version : les versions viennent de requirements.txt avec -c)
- Notebooks : ouverts dans VS Code (extension Jupyter), noyau « .venv (3.14.7) » choisi avec Select Kernel. Pas de paquet jupyter complet : VS Code n'a besoin que d'ipykernel.
- Docker Desktop (à partir de l'étape 6) : PostgreSQL 16 tourne dans le conteneur lol-postgres ; à partir de l'étape 19, l'appli Streamlit tourne aussi dans le conteneur lol-app (image lol-analytics-app)

## État d'avancement (mis à jour le 4 nov. 2026, fin de l'étape 20 = GIF de démo + Release du modèle ; tout le PLAN est fait)
- Étapes faites (cochées dans PLAN.md) : dépôt GitHub, venv + paquets, clé Riot + premiers appels (account-v1, match-v5 /ids et /matches/{id}), étape 4 « Comprendre le format JSON d'une partie et de sa timeline », étape 5 « MCD / MLD → sql/schema.sql » (schéma écrit et testé le 23 oct.), étape 6 « PostgreSQL dans Docker » (base lancée sur le PC le 26 oct.), étape 7 « Script de collecte » (testée sur le PC le 27 oct. : 80 parties dans data/raw).
- Étape 8 « Insertion en base + contrôles qualité » faite le 27 oct. 2026 (testée sur le PC : 10/10 contrôles OK).
- Étape 9 « Lancer la collecte en fond » faite le 28 oct. 2026 : 5 000 parties sur le disque, 4 907 en base, contrôles 8/10 OK + 2 avertissements expliqués (voir « Étape 9 faite »).
- Étape 10 « Analyse exploratoire (notebook) » faite le 30 oct. 2026 : notebooks/01_exploration.ipynb exécuté sur les 4 907 parties, conclusions écrites (voir « Étape 10 faite »).
- Étape 11 « 2-3 questions testées » faite le 31 oct. 2026 : notebooks/02_regression.ipynb (régression logistique, statsmodels) exécuté sur 4 762 parties, conclusions écrites (voir « Étape 11 faite »).
- Étape 12 « Features à 15 min » + score de scaling faite le 2 nov. 2026 : src/features.py lancé sur la vraie base (voir « Étape 12 faite »).
- Étape 13 « Régression logistique vs LightGBM » faite le 2 nov. 2026 : notebooks/03_models.ipynb exécuté, la logistique gagne, le scaling n'aide pas (voir « Étape 13 faite »).
- Étape 13 bis « Améliorer le modèle » faite le 2 nov. 2026 : notebooks/04_improvements.ipynb, aucun gain sur le test, collecte supplémentaire inutile (voir « Étape 13 bis faite »).
- Étape 14 « Calibration, SHAP » faite le 2 nov. 2026 : notebooks/05_calibration.ipynb, probabilités de la logistique déjà bien calibrées, pas de recalibrage (voir « Étape 14 faite »).
- Étape 15 « README en anglais avec résultats et figures » faite le 2 nov. 2026 : README réécrit (résultats en tête, schéma du pipeline, 4 figures, limites), src/make_figures.py → docs/figures/ (voir « Étape 15 faite »). Fin du bloc « v1 publique ».
- Étape 16 « Tutoriel PyTorch » faite le 2 nov. 2026 : src/deep.py + notebooks/06_pytorch.ipynb, la logistique refaite en PyTorch retrouve 0,5242, le MLP ne fait pas mieux (voir « Étape 16 faite »).
- Étape 17 « GRU minute par minute, comparaison avec LightGBM » faite le 3 nov. 2026 : src/sequences.py + notebooks/07_gru.ipynb, le GRU ne bat pas la logistique par minute, gardée pour l'appli (voir « Étape 17 faite »). Fin du bloc « Janvier : deep learning ».
- Étape bonus « Mini démo en direct » faite le 3 nov. 2026 : src/live.py (voir « Étape bonus faite »).
- Étape 18 « Appli Streamlit (Riot ID → parties, courbe, moments clés) » faite le 4 nov. 2026 : src/app.py + src/match_minutes.py, src/winprob.py, src/riot_games.py ; mêmes variables qu'à l'entraînement (écart 0 sur 200 parties), bilan de fiabilité par joueur (voir « Étape 18 faite »).
- Étape 19 « Docker Compose (appli + base), tests pytest, GitHub Actions » faite le 4 nov. 2026 : Dockerfile + service app dans docker-compose.yml, tests/ (48 tests), .github/workflows/tests.yml (voir « Étape 19 faite »).
- Étape 20 « GIF de démo dans le README » faite le 4 nov. 2026 : src/make_demo.py → docs/demo.gif en tête du README, modèle de l'appli publié dans la Release v2.0 (voir « Étape 20 faite »). Fin du bloc « Février : produit » : tout le PLAN est fait.
- Historique Git :
  1. Initial project structure
  2. Update plan: mark repo creation as done
  3. Set up Python environment
  4. Etape 3 : premiers appels API Riot
  5. Ajout de CONTEXT.md pour reprendre le contexte
  6. 286c1f1 Mise à jour de CONTEXT.md et mise à jour du .gitignore
  7. 9c987d4 Convert requirements to UTF-8, update CONTEXT.md and .gitignore
  8. f747d0e Etape 4 : exploration de la timeline (explore_timeline.py, resume_timeline.py, PLAN.md, CONTEXT.md)
  9. b44816a Fix CONTEXT.md formatting
  10. 00ca27f Etape 5 : schema SQL (MCD/MLD) et fix explore.py
  11. 6c2f5f0 Etape 6 : PostgreSQL dans Docker
  12. 3aa562f Etape 7 : script de collecte (limites de debit, 429, reprise)
  13. Etape 8 : insertion en base et controles qualite (load.py, quality.py, README, PLAN, CONTEXT) — commit + push par Paul le 27 oct.
  14. Etape 9 : collecte en fond (collect.py, riot_api.py, quality.py, README, PLAN, CONTEXT) — commit + push par Paul (2a52292, 46919ab).
  15. Etape 10 : notebook d'analyse exploratoire (notebook, requirements.txt, README, PLAN, CONTEXT) — commit + push par Paul (4da0dc8).
  16. Etape 11 : régression logistique (notebook 02, requirements.txt, README, PLAN, CONTEXT) — commit + push par Paul (588fc58).
  17. 88b51ef Etape 12 : features à 15 min (src/features.py, README, PLAN, CONTEXT) — commit + push par Paul le 2 nov.
  18. 0b41037 Etape 13 : régression logistique vs LightGBM, CV sans fuite (src/models.py, notebooks/03_models.ipynb, README, PLAN, CONTEXT, requirements.txt) — commit + push par Paul le 2 nov.
  19. 19e91d5 Etape 13 bis : tentatives d'amélioration, courbe d'apprentissage et nouvelles variables (src/features.py, notebooks/04_improvements.ipynb, README, PLAN, CONTEXT) — commit + push par Paul le 2 nov.
  20. 419c62b Etape 14 : calibration et explications SHAP (src/explain.py, notebooks/05_calibration.ipynb, README, PLAN, CONTEXT) — commit + push par Paul le 2 nov.
  21. 0bb2be6 Etape 15 : README anglais avec résultats et figures (README, src/make_figures.py, docs/figures/*.png, PLAN, CONTEXT) — commit + push par Paul le 2 nov. Vérifié sur GitHub (fichiers identiques, figures conformes aux chiffres du README : 7 % / 94 %, SHAP or 0,82, dragons 0,41, XP 0,28).
  22. c60f229 Etape 16 : tutoriel PyTorch, logistique et MLP (src/deep.py, notebooks/06_pytorch.ipynb, README, PLAN, CONTEXT, requirements.txt avec torch 2.14.1) — commit + push par Paul le 2 nov. Vérifié sur GitHub (6 fichiers identiques).
  23. bbfae9e Etape 17 : GRU minute par minute vs logistique et LightGBM (src/sequences.py, src/deep.py, notebooks/07_gru.ipynb, README, PLAN, CONTEXT, .gitignore) — commit + push par Paul le 3 nov. Vérifié sur GitHub (fichiers identiques).
  24. 509c2d9 Etape bonus : mini démo en direct, Live Client Data, modèle sans or (src/live.py, README, PLAN, CONTEXT) — commit + push par Paul le 3 nov.
  25. b7c61d6 Etape 18 : appli Streamlit, courbe minute par minute, moments clés, fiabilité par joueur (src/app.py, src/match_minutes.py, src/winprob.py, src/riot_games.py, src/sequences.py, .streamlit/config.toml, requirements.txt, README, PLAN, CONTEXT) — commit + push par Paul le 4 nov.
  26. d293a8f Etape 19 : Docker Compose (appli + base), tests pytest, GitHub Actions (Dockerfile, .dockerignore, docker-compose.yml, requirements.txt avec pytest 9.2.0, requirements-app.txt, pyproject.toml, tests/, .github/workflows/tests.yml, README, PLAN, CONTEXT) — commit + push par Paul le 4 nov.
  27. 589289f CI : installer les dépendances de PyTorch depuis PyPI — commit + push par Paul le 4 nov. Les 3 tâches GitHub Actions vertes (unit 46 passed + 2 skipped, database 2 passed, docker OK).
  28. 799f7dd Etape 19 : PLAN coché et hashes dans CONTEXT (PLAN.md et CONTEXT.md, absents du commit d293a8f) — commit + push par Paul le 4 nov.
- Vérification du 26 oct. 2026 : étapes 1 à 5 complètes. Le dépôt GitHub et le dossier du PC sont identiques (mêmes fichiers, même contenu), aucun secret ni fichier de data/ dans l'historique Git, .gitignore correct.
- Étape 4 en résumé : la timeline de EUW1_7995392565 a été récupérée (34 frames, partie d'environ 33 min) et enregistrée dans data/timeline_exemple.json. Sa structure est décrite plus bas.

## Étape 6 faite : PostgreSQL dans Docker (26 oct. 2026)
- Fichiers créés (testés d'abord avec Docker + PostgreSQL 16.15 : les 7 tables sont créées, les données survivent à docker compose down / up) :
  - docker-compose.yml : service db, image postgres:16, conteneur lol-postgres, utilisateur / mot de passe / base = lol, port 127.0.0.1:5433 côté PC (5432 dans le conteneur), volume nommé pgdata (sur le PC : lol-analytics_pgdata), sql/schema.sql monté dans /docker-entrypoint-initdb.d/ (exécuté seulement quand le volume est vide), healthcheck pg_isready.
  - src/check_db.py : se connecte avec psycopg à DATABASE_URL (lu dans .env) et vérifie que les 7 tables existent.
  - requirements.txt : + psycopg 3.3.6 et psycopg-binary 3.3.6 (roue Windows pour Python 3.14 disponible).
  - README.md : section Setup complétée (venv, pip install -r requirements.txt, .env, docker compose up -d, check_db.py).
- Fait sur le PC de Paul : Docker Desktop installé (il a fallu activer la Virtual Machine Platform avec `wsl --install --no-distribution` en PowerShell administrateur, puis redémarrer), DATABASE_URL ajouté à .env, docker compose up -d, vérification avec psql dans le conteneur et python src/check_db.py.
- Utilisation au quotidien : ouvrir Docker Desktop, puis `docker compose start` (ou `up -d`) avant de travailler avec la base ; à la fin de la séance, `docker compose stop` puis quitter Docker Desktop (il prend 1 à 2 Go de RAM).
- Si schema.sql change plus tard : les tables ne sont recréées que si le volume est vide → docker compose down -v (efface toutes les données) puis docker compose up -d.

- Problème du 26 oct. : docker compose up -d échouait avec « ports are not available: listen tcp4 127.0.0.1:5432: bind: An attempt was made to access a socket in a way forbidden by its access permissions ». 5432 n'est pas dans les plages réservées par Windows (netsh … excludedportrange : 28385, 28390, 50000-50059) et redémarrer winnat n'a rien changé : un autre programme utilise déjà 5432 sur le PC. Solution : port 5433 côté PC (docker-compose.yml, .env, .env.example).

## Étape 7 faite : script de collecte (26-27 oct. 2026)
- Choix : l'étape 7 télécharge le JSON brut sur le disque (zone « raw ») et n'écrit PAS en base. L'insertion PostgreSQL + contrôles qualité = étape 8. Raison : les appels API sont la ressource rare ; on peut refaire l'insertion sans retélécharger.
- src/riot_api.py : RateLimiter (deux fenêtres glissantes 20 req/1 s et 100 req/120 s, une deque par fenêtre, affiche les pauses > 1 s) ; RiotClient(api_key, region) avec requests.Session et l'en-tête X-Riot-Token ; get(path, **params) : 200 -> JSON, 404 -> None, 401/403 -> RiotKeyError (message avec le chemin et la réponse de Riot), 429 -> attend Retry-After, 5xx et erreurs réseau -> backoff 2, 4, 8, 16 s ; 5 essais max.
- src/collect.py : collecte « boule de neige » (parcours en largeur) depuis un Riot ID ; match-v5 /ids avec queue=420 ; pour chaque partie, match + timeline enregistrés dans data/raw/matches/<id>.json.gz et data/raw/timelines/<id>.json.gz (gzip, écriture atomique .tmp puis os.replace) ; les 9 autres joueurs vont dans la file. Reprise : une partie est faite si ses 2 fichiers existent ; joueurs parcourus dans data/raw/players_done.txt ; la file est reconstruite au démarrage à partir des fichiers de match. Options : --riot-id (obligatoire), --max-matches (objectif TOTAL sur le disque, 20 par défaut), --per-player (20 par défaut). Ctrl+C et clé expirée -> arrêt propre avec message.
- Commande : python src/collect.py --riot-id "TECHNIQUEMENT#99999" --max-matches 20
- Testé avec un faux serveur Riot (429, 503, 404, reprise), puis sur le PC le 27 oct. : 20 parties, puis 80 (pause du limiteur de 84 s observée, Ctrl+C à 68, reprise jusqu'à 80). Résultat : 80 matchs + 80 timelines, 6,4 Mo (≈ 80 Ko par partie), toutes en queue 420, aucun .tmp. Environ 24 parties/min au maximum (2 requêtes par partie), soit ≈ 1 400/h.
- Limite à connaître : l'échantillon part de Paul (biais de niveau au début) ; seules les --per-player dernières parties de chaque joueur sont prises.
- README : section « Data collection » ajoutée.

## Étape 8 faite : insertion en base + contrôles qualité (27 oct. 2026)
- src/load.py : lit data/raw/matches/*.json.gz + la timeline de même nom, et remplit les 7 tables avec psycopg (DATABASE_URL de .env, autocommit).
  - Idempotent : les match_id déjà en base sont sautés (SELECT match_id FROM matches au début). Relancer le script après chaque collecte n'insère que les nouvelles parties. players : INSERT ... ON CONFLICT DO NOTHING (un joueur revient dans plusieurs parties).
  - Une transaction par partie (with conn.transaction()) : la partie est insérée entièrement ou pas du tout ; une erreur SQL sur une partie est affichée et le script continue.
  - Contrôles AVANT insertion (check_match, partie refusée avec sa raison) : timeline d'une autre partie, queueId ≠ 420, remake (gameEndedInEarlySurrender ou < 5 min), pas 10 joueurs numérotés 1-10, équipes ≠ 5/5, pas exactement une équipe gagnante, participantId timeline ≠ match, valeur obligatoire manquante, frame incomplète.
  - Valeurs facultatives absentes -> NULL (p.get(...)) ; teamPosition "" -> NULL ; killerId/victimId 0 -> NULL.
  - killer_team_id : CHAMPION_KILL -> équipe du tueur, ou 300 - équipe de la victime si exécution ; ELITE_MONSTER_KILL -> killerTeamId, NULL si 300 (héraut mort sans équipe, 10 cas sur 80 parties) ; BUILDING_KILL et TURRET_PLATE_DESTROYED -> 300 - teamId.
  - Les parties de plus de 5 min mais de moins de 15 min sont gardées (vraies parties, utiles au GRU) : le modèle à 15 min les exclura avec WHERE minute = 15.
  - Option --limit N : n'insère que N nouvelles parties (pour tester).
- src/quality.py : ne fait que lire. Affiche des chiffres (parties, joueurs, durées, parties sans minute 15, % victoires bleues, exécutions, patchs) et 10 contrôles SQL (OK / ATTENTION n cas) : 2 équipes et un seul gagnant par partie, 10 joueurs 5/5, aucune minute manquante, or total jamais en baisse, kills timeline (hors exécutions) = somme des kills du match par équipe, tours et dragons timeline = tower_kills / dragon_kills, aucun poste manquant, aucun remake.
- Découverte : teams.champion_kills de Riot compte parfois les exécutions et parfois non ; le contrôle fiable est « kills avec un tueur dans la timeline = somme de participants.kills ».
- Test (PostgreSQL 16, schema.sql, les 80 parties du PC) : 79 insérées + 1 remake refusé (EUW1_7961274942, 119 s), 2e lancement : 0 insérée, 79 déjà en base. ≈ 0,08 s par partie. Tables : 79 matches, 158 teams, 670 players, 790 participants, 24 290 participant_frames, 11 768 events, 8 461 event_assists. quality.py : 10/10 OK. Or à 15 min de EUW1_7995392565 identique à l'étape 5 (26 387 / 27 591).
- README : section « Loading into PostgreSQL » ajoutée.
- Fait sur le PC de Paul le 27 oct. : load.py --limit 5, load.py, relance (0 insérée, pas de doublon), quality.py : 10/10 contrôles OK.
- Repartir de zéro si besoin (efface les données, garde les tables) : docker exec -it lol-postgres psql -U lol -d lol -c "TRUNCATE matches, players CASCADE;"

## Étape 9 faite : collecte en fond (28 oct. 2026)
- Dossier sorti de OneDrive le 28 oct. : C:\Users\pauld\projets\lol-analytics (même nom de dossier, donc même volume Docker lol-analytics_pgdata ; premier lancement après le déplacement avec docker compose up -d, qui recrée le conteneur avec le nouveau chemin). .venv supprimé puis recréé (py -3.14 -m venv .venv) ; piège rencontré : pip install lancé sans (.venv) dans le prompt installe dans le Python du PC (« Requirement already satisfied … pythoncore-3.14-64 ») → activer avec .venv\Scripts\Activate.ps1 puis relancer pip.
- Code (testé d'abord avec un faux serveur Riot) :
  - src/collect.py : messages via logging, à l'écran ET dans data/logs/collect.log (horodaté) ; keep_awake() = SetThreadExecutionState (ctypes) pour empêcher la veille de Windows pendant la collecte (l'écran peut s'éteindre ; fermer le capot met quand même en veille) ; single_instance() = verrou du système sur data/raw/collect.lock (msvcrt.locking / fcntl.flock), refuse une 2e collecte dans le même dossier, libéré automatiquement même si le script plante ; collect() séparée de main(), renvoie (nouvelles parties, raison de l'arrêt) ; report() = bilan toutes les 100 parties (parties/h, heure de fin estimée) ; RuntimeError (réseau ou Riot en panne trop longtemps) -> arrêt propre.
  - src/riot_api.py : logging au lieu de print (la bibliothèque produit les messages, collect.py décide où ils vont) ; 8 essais, backoff plafonné à 60 s (2, 4, 8, 16, 32, 60, 60, 60) : une coupure d'environ 4 min est absorbée.
  - src/quality.py : la ligne « Patchs » (left(game_version, 5) affichait « 16.1. ») remplacée par « Parties par patch » (split_part, nombre de parties par patch, tri numérique).
  - README : section « Background collection ».
- Lancement : fenêtre PowerShell séparée, .\.venv\Scripts\python.exe src\collect.py --riot-id "TECHNIQUEMENT#99999" --max-matches 5000 ; suivi avec Get-Content data\logs\collect.log -Encoding utf8 -Wait -Tail 20.
- Résultat : collecte d'une traite le 28 oct. de 17 h 30 à 20 h 50, 4 870 nouvelles parties, 1 460 parties/h (proche du maximum théorique de 1 500/h fixé par 100 requêtes / 2 min), 0 arrêt. data/raw = 5 000 parties, 401 Mo.
- load.py : 4 907 parties en base (93 refusées : remakes). quality.py : 41 173 joueurs, 1 540 740 lignes participant_frames, 729 999 events, 532 538 event_assists ; durée 5,0 / 29,9 / 52,3 min ; 58 parties sans minute 15 ; victoires bleues 48,3 % ; 949 exécutions ; 652 monstres épiques sans équipe.
- 2 avertissements, expliqués (pas des bugs de chargement, données gardées telles quelles) :
  - « L'or total ne baisse jamais » : 2 cas sur 1,5 M lignes (EUW1_7993549538 joueur 8 minute 12 : -90 ; EUW1_8013684170 joueur 2 minute 29 : -176). Les deux coïncident avec un event ITEM_UNDO (bouton « annuler » de la boutique) : Riot retire alors un peu de totalGold. Négligeable.
  - « Aucun poste manquant » : 1 cas, EUW1_8028482881 joueur 6 (Fiora), partie de 8 min, individualPosition = "Invalid" : joueur probablement AFK dès le début, Riot n'a pas pu deviner son poste. team_position NULL est la bonne valeur.
- Patchs (à retenir pour l'analyse) : la boule de neige prend les 20 dernières parties classées de chaque joueur, donc certaines sont anciennes (de juillet 2025, patch 15.14, à octobre 2026). 16.21 : 1 450, 16.20 : 1 053, 16.19 : 421, 16.14 à 16.18 : 1 892, avant 16.14 : environ 90. Penser à filtrer ou contrôler par patch à l'étape 10.

## Étape 10 faite : analyse exploratoire (30 oct. 2026)
- notebooks/01_exploration.ipynb (testé d'abord sur 613 parties, exécuté par Paul sur toute la base, résultats enregistrés dans le fichier et commités pour que GitHub affiche les graphiques ; aucun identifiant de joueur dedans).
- Structure : query(sql) (psycopg -> DataFrame, une connexion par requête ; pas pd.read_sql, qui veut SQLAlchemy) et prop_ci(k, n) (proportion + IC 95 % par approximation normale), puis une section par question : vue d'ensemble/patchs, durées, côté bleu, état à 15 min, premiers objectifs, champions, joueurs répétés, conclusions. Le SQL fait les agrégations, Python ne reçoit que des petits résultats.
- État à 15 min = écarts bleu − rouge : or, XP, CS (participant_frames, minute = 15), kills, bâtiments, plaques, dragons (events, timestamp_ms < 900 000). Requête avec deux CTE (frames15, events15), astuce CASE team_id = 100 THEN 1 ELSE -1, FILTER (WHERE event_type = ...). Courbes de victoire par déciles (pd.qcut) avec IC.
- Résultats (4 907 parties) :
  - Patchs 16.14 à 16.21 = 98 % des parties (≈ 90 plus anciennes, depuis le 19 juil. 2025). Durée médiane 30 min ; 58 parties < 15 min ; pic à 15-16 min (109 parties, abandons).
  - Bleu 48,3 % (IC 46,9-49,7) : léger avantage rouge ; le rouge a aussi plus de dragons avant 15 min (écart moyen −0,17).
  - Écart d'or à 15 min : 6,8 % de victoires dans le décile le plus en retard, 94,2 % dans le plus en avance. Corrélation avec la victoire : or 0,52, XP 0,50, kills 0,48, plaques 0,44, CS 0,40, bâtiments 0,40, dragons 0,34. Écarts très liés entre eux (or-XP 0,92, or-kills 0,90, bâtiments-plaques 0,89).
  - Premiers objectifs (victoire de l'équipe qui l'obtient) : sang 56,8 %, dragon 62,0 %, tour 68,5 %, baron 80,5 %.
  - Champions : 160 joués ≥ 100 fois, 10 dont l'IC exclut 50 % ≈ ce que le hasard donne (8 attendus) : rien de concluant.
  - 79 % des places = joueurs vus une seule fois : parties presque indépendantes.
- towers_diff comptait tous les BUILDING_KILL, donc aussi les inhibiteurs : corrigé à l'étape 11 (filtre building_type = 'TOWER_BUILDING').
- Incident pendant l'exécution : une cellule (comptage des 7 tables) est restée bloquée plusieurs minutes alors que la base était inactive (docker stats : 4,8 % CPU) ; Paul a fini par l'exécuter en entier, cause non identifiée. Si ça recommence : Interrupt, lire la fin du KeyboardInterrupt (connect ou execute ?), et pg_stat_activity.

## Étape 11 faite : 3 questions testées par régression logistique (31 oct. 2026)
- notebooks/02_regression.ipynb (testé d'abord sur 3 000 parties synthétiques, exécuté par Paul sur la vraie base, résultats enregistrés dans le fichier). statsmodels 0.15.0 ajouté au venv (+ scipy, patsy, formulaic ; requirements.txt régénéré).
- Pourquoi statsmodels et pas scikit-learn : on veut expliquer (coefficients, IC, p-valeurs) ; scikit-learn vise la prédiction (étape 12).
- Jeu de données : une ligne par partie vue du bleu (la ligne du rouge = même partie retournée, lignes dépendantes), écarts bleu − rouge à 15 min (gold_k et xp_k en milliers, kills, tours = TOWER_BUILDING seulement, plaques, dragons, CS/10), first_tower15 = bleu / rouge / aucune avant 15 min (calculé dans events avec DISTINCT ON ; pas teams.first_tower, qui porte sur toute la partie = fuite d'information), patch. Filtres : patchs 16.14 à 16.21 et minute 15 présente → 4 762 parties sur 4 907. Comme tout est bleu − rouge, la constante du modèle = avantage de côté.
- Outils : fit(formule) (smf.logit), odds_table (odds ratios + IC 95 % + p-valeurs), lr_test (rapport de vraisemblance entre modèles emboîtés), logistic. Codages : C(first_tower15, Treatment('aucune')), C(patch, Sum) (constante = moyenne sur les patchs).
- Résultats :
  - Or seul : odds ratio 1,44 par 1 000 or (IC 1,40-1,47) ; 47,5 % à écart nul, 56,5 % à +1 000, 79,3 % à +4 000. La courbe passe dans les IC des 10 déciles.
  - Q1 : ajouter XP + kills + dragons améliore le modèle (LR 109, 3 ddl, p < 0,001 ; AIC 5 114 → 5 010 ; pseudo-R² 0,225 → 0,242). À or égal : dragons 1,30 par dragon (≈ 1 000 or), XP 1,10 par 1 000 XP, kills 0,99 (rien), tours, plaques, CS : rien. VIF or 9,8, XP 6,6, kills 5,8.
  - Q2 : première tour avant 15 min : 2,53 sans contrôle, 0,94 (IC 0,79-1,13) à or égal → aucun effet propre au-delà de l'or qu'elle rapporte.
  - Q3 : bleu 48,5 % (IC 47,0-49,9, p = 0,03) ; patch sans effet (LR p = 0,45), avec patch 48,6 % (p = 0,10) ; à écart de dragons égal 50,9 % (IC 49,1-52,7) → l'avantage rouge, faible, passe par les dragons.
  - Modèle complet : or 1,33, XP 1,11, dragons 1,30, le reste nul ; pseudo-R² 0,243. Erreurs types robustes HC1 à moins de 3 % des classiques.
- Limites : associations contrôlées, pas des causes (niveau, compositions non mesurés) ; parties pas tout à fait indépendantes ; une quinzaine de tests.

## Étape 12 faite : features à 15 min + score de scaling (31 oct. – 2 nov. 2026)
- src/features.py (testé d'abord sur 3 000 parties synthétiques, lancé par Paul sur la vraie base le 2 nov.). Module importable par l'étape 13 : `from features import build_features, fit_scaling, add_scaling, FEATURES`. Lancé seul (python src/features.py) : construit le jeu, 5 contrôles, résumé, corrélations, démo du score de scaling.
- build_features(minute=15, patch_min=14, patch_max=21) : une requête SQL à 5 CTE (frames : or/XP/CS à la minute 15, total et par poste ; ev : events avant 15 min avec +1/−1 ; counts ; firsts avec DISTINCT ON ; champs : array_agg des 5 champions par équipe), HAVING count(*) = 10, coalesce 0, requête paramétrée. Une ligne par partie vue du bleu, triée par date. Le paramètre minute servira au GRU.
- Listes de colonnes (garde-fou contre la fuite) : FEATURES = 11 écarts (gold_k, xp_k, cs_diff, kills, tours, plaques, dragons, larves, first_blood / first_tower / first_dragon codés +1/−1/0) ; ROLE_FEATURES = or par poste (somme = gold_k, donc pas avec gold_k en logistique, pour LightGBM) ; SCALING_FEATURES = scaling_diff, gold_x_scaling ; INFO_COLUMNS = match_id, game_creation, patch, duration_min (connue en fin de partie : jamais une feature), blue_champs, red_champs.
- Héraut retiré le 2 nov. : heralds_diff valait 0 dans les 4 762 parties (aucun héraut tué avant 15 min sur ces patchs).
- time_split(df, 0.2) : découpage chronologique (les 20 % les plus récentes en test).
- Score de scaling : fit_scaling(train) = note par champion = 100 × (taux de victoire lissé dans les parties longues − dans les courtes), longue = durée ≥ médiane du train, lissage (victoires + 20 × 0,5) / (parties + 20) ; add_scaling(df, notes) = somme par équipe, scaling_diff = bleu − rouge, gold_x_scaling = gold_k × scaling_diff ; champion inconnu = 0. Séparé en fit / apply comme scikit-learn : à l'étape 13, les notes seront réapprises dans chaque pli.
- Résultats sur la vraie base : 4 762 parties, bleu 48,5 %, 5/5 contrôles OK. Corrélations avec la victoire : or 0,52, XP 0,50, kills 0,48, plaques 0,43, CS 0,40, tours 0,40, première tour 0,35, dragons 0,34, or bot 0,32 … top 0,26, support 0,25, premier dragon 0,23, premier sang 0,14, larves 0,13. Écart de dragons entre −2 et +2 avant 15 min.
- Scaling (3 809 parties d'entraînement, 953 de test) : en tête Belveth 20,1, Braum 19,0, Sona 16,9, Ivern, Evelynn, Kayle, Orianna, Kassadin, Vladimir, Smolder ; en bas Kled −14,7, Kennen, Mordekaiser, Diana, KogMaw, Ekko, Blitzcrank, Xayah, Gragas, Lulu (cohérent avec le jeu). Équipe au meilleur score sur le test : 53,6 % des parties longues, 49,1 % des courtes ; avec fuite (notes apprises avec le test) 59,1 % / 42,4 % → l'écart paraît presque 4 fois plus grand. Écart propre de 4,5 points proche du bruit (≈ 950 parties de test) : à juger en validation croisée.
- README : section « Features at 15 minutes ».

## Étape 13 faite : régression logistique vs LightGBM (2 nov. 2026)
- src/models.py et notebooks/03_models.ipynb (testés d'abord sur 4 762 parties synthétiques, exécutés par Paul sur la vraie base, conclusions écrites dans la partie 9). Paquets ajoutés : scikit-learn 1.9.1, lightgbm 4.7.0 (+ joblib, threadpoolctl).
- models.py (importé par les notebooks, servira à l'étape 14 et à Streamlit) : make_baseline (DummyClassifier « prior »), make_logit (StandardScaler + LogisticRegression C=1 dans un pipeline : le scaler est réappris dans chaque pli), make_lgbm (prudent : min_child_samples 50, subsample / colsample_bytree 0,8, learning_rate 0,03, reg_lambda 1), oof_scaling (score de scaling des parties d'entraînement calculé hors pli, KFold 5 interne), prepare(train, other, use_scaling, oof=True), evaluate (log loss = critère principal, Brier, AUC, précision), fit_predict, time_folds / cross_validate (TimeSeriesSplit 5 plis, entraînement qui grandit), paired_bootstrap (IC 95 % d'un écart de log loss, mêmes parties tirées pour les deux modèles).
- Protocole : test = 953 parties les plus récentes (24 au 28 oct.), regardé une seule fois ; choix faits en validation croisée chronologique sur les 3 809 autres (16 juil. au 24 oct.). Pourquoi pas KFold mélangé : on apprendrait le futur (patchs, champions à la mode).
- Grille LightGBM (num_leaves 4/7/15 × n_estimators 100/200/400) : meilleur = 4 feuilles, 200 arbres (le plus simple, au bord de la grille) ; 15 feuilles / 400 arbres = 0,568.
- Résultats CV (log loss) : constante 0,693, Logit or seul 0,536, Logit 11 variables 0,530, Logit + scaling 0,530, LightGBM 0,535, LightGBM + scaling 0,535.
- Résultats test : Logit 0,524 (AUC 0,813, 74,1 %), Logit or seul 0,539, Logit + scaling 0,527, LightGBM 0,528 (AUC 0,809), LightGBM + scaling 0,530. Bootstrap apparié : Logit > or seul (−0,015, IC −0,026 à −0,005) ; LightGBM vs Logit +0,004 (IC −0,003 à +0,011, pas de différence) ; scaling +0,002 (IC −0,003 à +0,008, rien). Probabilités Logit / LightGBM corrélées à 0,985.
- Deux fuites mesurées (Logit + scaling, CV) : fuite 1 (notes apprises avec la validation) 0,524 → ferait croire que le scaling aide ; fuite 2 (notes appliquées aux parties qui les ont apprises = piège du target encoding) 0,535 → le modèle surpondère le score (coefficient réduit 0,31 au lieu de 0,20) et prédit moins bien ; propre (hors pli) 0,530. Découverte au 1er lancement, corrigée par oof_scaling. Une fuite peut biaiser dans les deux sens.
- Décision : modèle retenu = régression logistique sur les 11 variables, sans scaling. LightGBM reste la référence pour le GRU.
- Limites : une saison de patchs, test de 5 jours (±0,005 de log loss), pli 1 entraîné sur 639 parties.
- README : section « Model comparison ».

## Étape 13 bis faite : tentatives d'amélioration du modèle à 15 min (2 nov. 2026)
- Pistes d'amélioration revues. Faites : courbe d'apprentissage, variables déjà en base, réglage de C, moyenne de modèles. Non faites (jugées inutiles après les résultats) : collecte de 20 000 parties, objets / wards depuis data/raw, rang league-v4, classes Data Dragon.
- src/features.py : nouvelle section « 2 bis », build_extra_features(df, minute=15, early=10) → (df, groupes). Requêtes séparées (EXTRA_SQL, DRAGONS_SQL) pour ne pas modifier le jeu de l'étape 12. Groupes : or à 10 min (gold10_k, gold_trend_k), niveaux (level_diff), joueur le plus riche (top_gold_k), joueurs en vie à 15:00 (alive_diff = tués dans les 30 s avant 15:00), dragons par type (drag_<type>_diff). Testé sur une PostgreSQL 16 locale avec le vrai schéma.
- notebooks/04_improvements.ipynb : courbe d'apprentissage sur le pli 5 (400 → 3 175 parties, 5 tirages) ; groupes ajoutés un par un en CV avec une règle fixée avant (écart moyen < 0 ET ≥ 4 plis sur 5) ; C ∈ {0,001 … 10} ; LightGBM avec toutes les variables ; test final avec bootstrap apparié.
- Résultats : courbe presque plate pour la logistique (0,5242 à 1 600 parties → 0,5226 à 3 175), LightGBM descend encore (0,5410 → 0,5325) mais reste ~0,01 derrière → collecte inutile pour ce modèle. Nouvelles variables corrélées à 0,80-0,89 avec l'or ; gardées par la règle : joueur le plus riche (−0,0020) et or à 10 min (−0,0007) ; avec C = 0,1, CV 0,5297 → 0,5258 ; MAIS test 0,5270 contre 0,5242 (+0,003, IC −0,002 à +0,007) → gain = bruit (malédiction du gagnant). Dragons par type pires (+0,006). LightGBM toutes variables 0,5376 en CV, 0,530 en test. Moyenne Logit + LightGBM 0,528.
- Décision : modèle retenu inchangé = logistique de l'étape 13 (11 variables, C = 1). Plafond à 15 min ≈ 0,52 de log loss / 74 % ; le gain sûr viendra de prédire plus tard (GRU en janvier). README : sous-section « Trying to improve the 15-minute model ».

## Étape 14 faite : calibration et explications SHAP (2 nov. 2026)
- src/explain.py et notebooks/05_calibration.ipynb (testés d'abord sur une PostgreSQL 16 locale avec 4 800 parties synthétiques, exécutés par Paul sur la vraie base, conclusions écrites dans la partie 6). Aucun paquet ajouté : statsmodels était déjà là, et le paquet shap n'est PAS utilisé.
- explain.py, partie calibration : reliability_table (10 déciles de probabilité annoncée, taux réel + IC de Wilson), expected_calibration_error (ECE), calibration_fit (pente et ordonnée de calibration avec IC, statsmodels), oof_predictions (prédictions hors pli avec les plis chronologiques de models.py), fit_recalibrator (Platt = LogisticRegression(C=np.inf) sur logit(p), ou isotonique). penalty=None est déprécié depuis scikit-learn 1.8 : utiliser C=np.inf.
- explain.py, partie SHAP : linear_contributions (logistique : coefficient × (valeur − moyenne d'entraînement) / écart type, en log-odds ; c'est la valeur de SHAP exacte d'un modèle linéaire), tree_contributions (LightGBM : booster_.predict(pred_contrib=True) = TreeSHAP), explain_game (6 variables qui pèsent le plus + probabilité après chaque étape). Vérifié : mêmes valeurs que shap.LinearExplainer / TreeExplainer (écart < 1e-15). Base + somme des contributions = prédiction exacte en log-odds (écart 2e-16).
- Résultats calibration (test, 953 parties) : Logit Brier 0,175, ECE 2,8 points, pente 1,04 (IC 0,89 à 1,18), ordonnée 0,02 (IC −0,13 à 0,17), 10 déciles sur 10 dans l'IC ; LightGBM Brier 0,177, ECE 4,2 points, pente 1,06, 9 / 10. 35 % des parties annoncées à < 20 % ou > 80 %.
- Recalibrage : aucun gardé (règle : meilleur au test ET IC bootstrap qui exclut 0). Platt +0,001 (IC −0,001 à +0,003), isotonique +0,007. Piège mesuré : les prédictions hors pli ont une pente de 0,93 (IC 0,86 à 1,00), trop sûres d'elles car venant de modèles entraînés sur moins de parties ; le modèle final n'a pas ce défaut (1,04 au test).
- SHAP (moyenne |contribution|, log-odds, Logit) : or 0,82, dragons 0,41, XP 0,28, premier dragon 0,16, le reste < 0,10. LightGBM : même ordre (or, XP, dragons). Kills, tours, CS ont un petit effet négatif à or égal (l'or les compte déjà) : SHAP explique le modèle, pas une cause. Or et XP corrélés : lire leur contribution comme un bloc.
- Plus grosse surprise du test : bleu annoncé à 96 %, rouge gagnant. Le décile annoncé 91 % perd 5 % du temps : attendu.
- Décision : logistique de l'étape 13 gardée SANS recalibrage ; l'appli affichera sa probabilité telle quelle et l'explication linear_contributions + explain_game.
- README : section « Calibration and explanations ».

## Étape 15 faite : README en anglais avec résultats et figures (2 nov. 2026)
- README.md réécrit pour la v1 publique : question du projet en une phrase, « Results at a glance » (74 %, log loss 0,524, AUC 0,81 ; or puis dragons ; probabilités fiables ; la limite vient de l'information, pas du modèle ; 2 fuites mesurées) avec 2 figures côte à côte, schéma du pipeline en Mermaid (GitHub le dessine), structure du dépôt à jour, « Reproducing the results », sections détaillées regroupées (Data pipeline, Analysis, Predicting the winner at 15 minutes), « Limitations » et « Roadmap ». Pourcentages à l'anglaise (74%, pas 74 %).
- src/make_figures.py (choix : script plutôt que captures des notebooks, car les notebooks sont en français et les figures doivent se refaire à l'identique) : réutilise features.py / models.py / explain.py, même découpage et mêmes graines que les notebooks 03 à 05 ; affiche la log loss du test comme contrôle (attendu 0,5242). 4 PNG à 150 dpi dans docs/figures/ : win_rate_by_gold.png (déciles d'écart d'or, IC de Wilson), learning_curve.png (comme le notebook 04), calibration.png (courbe de fiabilité + histogramme des probabilités), shap_importance.png (moyenne |SHAP| de la logistique). Couleurs fixes : bleu = logistique, orange = LightGBM. matplotlib en mode Agg (pas de fenêtre). Aucun nouveau paquet.
- Testé sur PostgreSQL 16 + 4 800 parties synthétiques (~12 s).

## Étape 16 faite : tutoriel PyTorch (2 nov. 2026)
- Pourquoi : le GRU (prochaine étape) demande PyTorch, où l'on écrit soi-même la boucle d'entraînement. On l'a d'abord validée sur un problème dont la réponse est connue : la logistique de l'étape 13 (log loss test 0,5242).
- src/deep.py : LogisticNet (une couche nn.Linear = la logistique) ; MLP (linéaire → ReLU → dropout → linéaire) ; train_model (AdamW, mini-lots de 128 mélangés, BCEWithLogitsLoss, arrêt précoce patience 20 sur une validation, retour aux poids de la meilleure époque, renvoie l'historique des pertes) ; predict_proba ; TorchClassifier = adaptateur au format scikit-learn (fit / predict_proba) pour réutiliser cross_validate / fit_predict / paired_bootstrap de models.py ; dans fit : StandardScaler appris sur l'entraînement du pli, 15 % de parties les plus récentes pour l'arrêt précoce. Les modèles renvoient des logits (sigmoïde dans la perte : plus stable).
- notebooks/06_pytorch.ipynb (8 parties) : tenseurs ; autograd (exemple 3w = 9) ; données (mêmes que 13-15) ; logistique « à la main » (w, b, 2 000 pas, pénalité L2 de scikit-learn = ‖w‖² / (2 C n)) ; LogisticNet + train_model ; CV de 4 modèles puis test une fois avec bootstrap apparié ; aperçu du GRU (formes (parties, minutes, variables)) ; conclusions.
- Résultats (exécuté par Paul, PyTorch 2.14.1+cpu) : à la main, coefficients = scikit-learn à 0,002 près, log loss test 0,5242 ; LogisticNet 0,5243 (meilleure époque 12 sur 32). CV : Logit PyTorch 0,5285, Logit scikit-learn 0,5297, MLP 16 neurones 0,5363, MLP 64 neurones 0,5401. Test : MLP 16 0,5285 contre 0,5242, écart +0,0044 (IC 95 % −0,0009 à +0,0094) ; précision 75,6 % contre 74,1 % mais log loss moins bonne. Conclusion : comme LightGBM, un modèle plus souple n'apporte rien à 15 min (effet presque linéaire, ~3 800 parties).
- Testé d'abord à part (PostgreSQL 16 + 4 800 parties synthétiques, PyTorch 2.13 CPU, ~30 s). README : section « Neural networks (PyTorch) ».

## Étape 17 faite : GRU minute par minute vs logistique par minute et LightGBM (2-3 nov. 2026)
- But : une probabilité de victoire du bleu à chaque minute (la courbe de l'appli), et savoir si un GRU qui lit l'historique fait mieux que des modèles qui ne voient que l'état du moment.
- src/sequences.py : build_minute_features(games) = une ligne par (partie, minute), à partir des parties de build_features() (même test) ; FRAMES_SQL (or, XP, CS par minute en écarts, dernière frame de chaque partie retirée car prise à l'instant de la fin) + EVENTS_SQL (un « genre » et un signe par event) puis cumul pandas par partie ; un event compte à la minute t si timestamp < t × 60 000 ms (même règle qu'à l'étape 12). 16 variables (SEQ_FEATURES) = les 11 FEATURES + heralds_diff, barons_diff, elders_diff (dragon ancestral, à part de dragons_diff), inhibs_diff, kills_1min_diff (kills de la dernière minute, non cumulé). check_against_15 (comparaison avec build_features à la minute 15), split_games (découpage par partie), to_padded (tableaux 3D (parties, 60 minutes, variables), padding 0 / NaN après la fin).
- Trois modèles avec la même interface fit(tableau long) / predict(tableau long) : PerMinuteLogit (une make_logit par minute, 40 min et plus regroupées), StackedLGBM (un make_lgbm sur toutes les lignes, minute en variable, 400 arbres, 15 feuilles, 200 lignes par feuille), SequenceGRU (WinGRU 32 neurones d'état, dropout 0,2, AdamW lr 3e-3, weight decay 1e-3, lots de 64 parties, patience 10, clip 1 ; 15 % des parties d'entraînement les plus récentes pour l'arrêt précoce ; scaler appris sur le reste). Évaluation : game_folds / cross_validate_minutes (TimeSeriesSplit sur la liste des parties), scores_by_minute, bootstrap_games (IC en tirant des parties entières : les ~30 lignes d'une partie ne sont pas indépendantes ; le bootstrap par lignes donne un intervalle ~3 fois trop étroit).
- src/deep.py : + WinGRU (nn.GRU unidirectionnel → dropout → nn.Linear, un logit par minute), masked_bce (log loss sur les minutes jouées seulement), train_model(loss_fn=None, clip=None) : valeurs par défaut = comportement de l'étape 16.
- notebooks/07_gru.ipynb (7 parties) : données et contrôles, tableaux 3D, premier GRU + test de causalité (modifier la partie après la minute 20 ne change pas les minutes 1-20 : écart 0,0), CV des 3 modèles, test une fois (global, par minute, bootstrap par partie), une partie racontée, conclusions.
- Résultats (exécuté par Paul le 3 nov., 4 762 parties, 141 149 lignes ; lecture de la base ~4 min) : CV log loss Logit par minute 0,5461, GRU 0,5483, LightGBM 0,5541. Test Logit 0,5327 (AUC 0,802, 72,0 %), LightGBM 0,5345, GRU 0,5359. Bootstrap par partie : GRU − LightGBM +0,0015 (IC −0,0036 à +0,0064), GRU − Logit +0,0033 (IC −0,0014 à +0,0080), LightGBM − Logit +0,0018 (IC −0,0021 à +0,0057) → aucune différence. À la minute 15, Logit par minute 0,5241 = étape 13 (0,5242). Log loss par minute : 0,648 (5 min), 0,524 (15), 0,402 (25), puis 0,467 (30) et 0,487 (35) : à 35 min il ne reste que 205 parties de test sur 953, les plus serrées (biais de sélection).
- Deux contrôles non nuls, vérifiés dans data/raw et bénins : écart 2,0 à 15 min sur first_blood (7 parties) et first_tower (1) où les deux équipes font le premier kill / la première tour à la même milliseconde (égalité départagée différemment par les deux codes) ; 17 parties dont la durée tombe pile sur une minute (ex. 1 680 s) et dont la frame de la minute 28 est à 28:00,5, une demi-seconde avant la fin (arrondi de gameDuration, la frame de fin est bien retirée).
- Décision : pour l'appli, la logistique par minute (PerMinuteLogit) : meilleure en CV, aussi bonne au test, entraînée en 2 s (GRU ~80 s en CV), explicable minute par minute avec les contributions de l'étape 14. Raison : variables cumulées → l'état à la minute t contient déjà l'histoire utile. Limites : une seule taille de GRU, ~3 800 parties, pas de positions / vision / objets.
- Testé d'abord à part (PostgreSQL 16 + 4 800 parties synthétiques complètes, ~2 min). README : section « Win probability minute by minute ».

## Étape bonus faite : mini démo en direct (3 nov. 2026)
- But : afficher pendant une partie, sur le PC de Paul, la probabilité de victoire chaque minute. Usage perso et analyse uniquement, jamais en compétition, rien de distribué (règles Riot) ; ne lit que l'API locale « Live Client Data » (https://127.0.0.1:2999, ouverte par le jeu pendant une partie, certificat auto-signé donc verify=False, aucune clé API).
- src/live.py, 4 commandes : train (base nécessaire : compare au test l'étape 17 et les variantes live, puis entraîne sur toutes les parties et enregistre data/live_model.joblib), watch [--minute N] (lit allgamedata toutes les 5 s, une ligne par minute, CSV + état brut de chaque minute dans data/live_captures/watch_<date>/), dump (instantané JSON), replay FICHIER.
- L'API live est plus pauvre que la timeline : pas d'event pour les plaques ni les larves, le niveau au lieu de l'XP, creepScore (par pas de 10), pas l'or des autres joueurs. Variables live définies pareil à l'entraînement : xp_k = XP minimale du niveau (180 (L−1) + 50 L (L−1), LIVE_FRAMES_SQL), CS arrondi à 10 par joueur. Events : kill pour l'équipe adverse de la victime (comme load.py), tours et inhibiteurs lus dans le NOM du bâtiment (format réel Turret_TChaos_L1_P3_… / Turret_TOrder_…, différent de la doc Turret_T1_… : les deux gérés).
- L'or est retiré : la valeur des objets (prix Data Dragon gold.total ; le champ price du jeu n'est que le prix de la dernière combinaison) est un mauvais substitut. Sur 293 timelines, inventaire reconstitué à 15 min : corrélation 0,78 avec le vrai écart d'or, erreur typique 1 465. En partie contre l'IA : +1,6 k affiché pour +9,0 k réel ; dans une 2e partie, un Malphite AFK avait 2 150 d'objets pour 12 377 d'or gagné (or non dépensé). La valeur des objets reste dans le CSV (items_k), pour information.
- Deux modèles (PerMinuteLogit de l'étape 17) : « sans or » (13 variables : xp_k, cs_diff + 11 variables d'events) = modèle principal ; « events » (11 variables). Test (4 762 parties, même test) : étape 17 0,5327 ; or exact + XP/CS live 0,5326 ; sans or 0,5365 (+0,0038, IC −0,0010 à +0,0085, non significatif) ; events 0,5483 (+0,0156, IC +0,0085 à +0,0224). À 15 min : 0,5241 / 0,5270 / 0,5345 / 0,5465. Raison : l'or vient surtout des kills, CS, tours et XP, déjà dans le modèle.
- Contrôles : test bout en bout à part (parties de la base → faux JSON de l'API → mêmes variables qu'à l'entraînement, écart 0 sur 4 520 (partie, minute)) ; capture réelle en outil d'entraînement (équipes ORDER/CHAOS, KillerName = riotIdGameName) ; 2 parties contre l'IA comparées au tableau de fin (kills +13 à 20:00 puis 46-32 à la fin ; niveaux, CS et objets adverses à jour chaque minute : pas d'effet du brouillard de guerre). L'ordre de allPlayers change d'un instantané à l'autre (sans effet sur les sommes par équipe).
- Vérifié à cette occasion : les étapes 1 à 17 n'utilisent jamais les objets ; l'or de la base (totalGold de la dernière frame) = goldEarned de fin de partie pour les 2 910 joueurs de 300 parties de data/raw (rapport 1,000).
- README : section « Live demo (personal use only) ».

## Étape 18 faite : appli Streamlit (4 nov. 2026)
- But : taper un Riot ID et voir, pour chacune de ses dernières parties classées solo/duo, la probabilité de victoire de SON équipe à chaque minute, les moments clés et ce qui pèse sur la probabilité à la minute choisie. Usage local uniquement (`streamlit run src/app.py`, http://localhost:8501) : la clé de développement interdit un site public.
- Streamlit : un script Python relancé de haut en bas à chaque clic ; st.cache_resource pour ce qui se partage (modèle, client Riot avec ses limites de débit), st.cache_data pour les résultats (liste de parties, ttl 10 min ; analyse d'une partie). Graphiques Altair. .streamlit/config.toml : headless, localhost seulement, pas de statistiques d'usage.
- src/match_minutes.py (nouveau) : minute_table(frames, events) = LE calcul des 16 SEQ_FEATURES, déplacé de sequences.py. Deux chemins l'appellent : l'entraînement (base, FRAMES_SQL / EVENTS_SQL de sequences.py) et l'appli (JSON de l'API : frames_from_json / events_from_json fabriquent les deux mêmes tableaux, avec event_team de load.py pour savoir à qui compte un bâtiment, dernière frame retirée). Raison : éviter le « training-serving skew » (variables calculées autrement en service qu'à l'entraînement). Aussi : readable_events (champions seulement, aucun pseudo), game_summary, scoreboard. sequences.py réexporte les constantes (SEQ_FEATURES, MAX_MINUTE…) : notebook 07 et live.py inchangés, sortie identique.
- src/winprob.py : train (étape 17 refaite : PerMinuteLogit 16 variables, or exact ; contrôle du test puis entraînement sur les 4 762 parties → data/app_model.joblib = dictionnaire des 40 logistiques scikit-learn, sans torch, l'appli n'a besoin ni de la base ni de PyTorch) ; check --n 200 (JSON de data/raw vs base) ; predict, contributions (valeurs de SHAP exactes de l'étape 14, avec le modèle de chaque minute), key_moments, explain_minute, player_report.
- Moments clés : entre deux minutes, l'état de la partie ET le modèle changent (une régression par minute : 1 000 d'or comptent plus à 10 min qu'à 30). Δp = [f_t(x_t) − f_t(x_{t−1})] (part des events) + [f_t(x_{t−1}) − f_{t−1}(x_{t−1})] (part du temps), décomposition exacte ; on garde les 5 minutes où la part des events est la plus forte, avec les events de la minute.
- Bilan « fiabilité du modèle sur ce joueur » (ajouté après les 4/10 de Paul) : à 10, 15 et 20 min, bons pronostics vs attendus (Σ max(p, 1−p)), log loss vs attendue (entropie moyenne), « hasard » = test de Monte-Carlo (20 000 tirages des résultats selon les probabilités du modèle : part des tirages où la log loss est au moins aussi mauvaise que l'observée ; sous 5 % = le modèle lit vraiment moins bien ce joueur), remontées et avances perdues. Vérifié : sous l'hypothèse « le modèle est juste », le hasard est uniforme (6 % des cas sous 5 %).
- src/riot_games.py : client RiotClient de l'étape 7 (limites de débit, 429, clé refusée) ; cache data/app_cache/ (matches/, timelines/, players/), à part de data/raw pour ne pas mélanger avec les données d'entraînement ; si la clé a expiré, l'appli reprend la dernière liste de parties gardée, avec un avertissement.
- Résultats (exécuté par Paul le 4 nov.) : train 4 762 parties, 141 149 lignes, lecture de la base 279 s ; test log loss 0,5327, AUC 0,802 (= étape 17) ; modèle de 40 logistiques, patchs 16.14 à 16.21. check : 200 parties, 6 042 (partie, minute) comparées, plus grand écart base / JSON = 0,0.
- Fiabilité sur 3 joueurs (dont Paul, TECHNIQUEMENT#99999), 50 parties chacun, à 15 min : Paul 37 bons pronostics pour 37,4 attendus (hasard 44 %), joueur 2 28 pour 33,4 (25 %), joueur 3 31 pour 35,2 (33 %). Ensemble, 141 parties : 94 pour 102 attendus, log loss 0,553 pour 0,539 attendue, hasard 35 %, pente de calibration 1,00 ; les patchs hors entraînement (16.6 à 16.13) ne font pas pire. Conclusion : compatible avec le hasard (légère tendance, les trois minutes 10/15/20 ne sont pas des tests indépendants). Les 4/10 du début : 6,9 attendus, P(≤ 4) ≈ 5 %, 10 parties c'est peu.
- Testé d'abord à part (PostgreSQL 16 : 4 800 parties synthétiques + 25 vraies parties du PC, écart 0 ; appli dans un navigateur sans écran avec un faux client Riot : Riot ID mal écrit, inconnu, clé expirée). README : sections « Running the app » et « Streamlit app ».

## Étape 19 faite : Docker Compose, tests pytest, GitHub Actions (4 nov. 2026)
- But : lancer la base ET l'appli avec une seule commande (docker compose up -d), des tests automatiques, et les faire tourner sur GitHub à chaque push.
- Dockerfile (image lol-analytics-app) : python:3.14.7-slim (même Python que le PC) + libgomp1 (OpenMP, pour LightGBM) ; paquets AVANT le code (cache de Docker : seule la copie du code est refaite après une modification) ; pip install -r requirements-app.txt -c requirements.txt (requirements-app.txt dit QUELS paquets, requirements.txt quelles VERSIONS) ; utilisateur appuser (pas root) ; STREAMLIT_SERVER_ADDRESS=0.0.0.0 (dans un conteneur, écouter « localhost » rendrait l'appli injoignable ; c'est le port 127.0.0.1:8501 de docker-compose.yml qui limite l'accès au PC). Sans PyTorch : 276 Mo compressés au lieu de plusieurs Go.
- .dockerignore : .env, data/, .venv/, .git/, notebooks/, tests/... jamais copiés dans l'image. Les secrets et les données arrivent au lancement : env_file .env (required: false : l'appli démarre sans) et volume ./data:/app/data (modèle app_model.joblib et cache app_cache/ partagés avec le PC).
- docker-compose.yml : service db inchangé (étape 6) + service app (container_name lol-app). DATABASE_URL de l'appli = postgresql://lol:lol@db:5432/lol : entre conteneurs, la base s'appelle « db » (nom du service) sur le port 5432 ; localhost:5433 n'existe que vu du PC. Pas de depends_on : l'appli ne lit pas la base (seulement le modèle). Healthcheck de l'appli : http://localhost:8501/_stcore/health (python, pas de curl dans l'image).
- pyproject.toml : réglages de pytest (pythonpath = src, testpaths = tests, marqueur db).
- tests/conftest.py : fausses parties au format exact de l'API Riot (data/ n'est pas dans le dépôt) : make_game(events) = partie calme où l'on place les events (réponse connue), random_game(seed) = partie au hasard avec tous les types d'events et les pièges (exécutions, bâtiment compté pour l'équipe qui NE le perd PAS, monstre sans équipe, dragon ancestral après 21 min).
- tests/test_match_minutes.py (25 tests) : règle de la minute (event à 2:59.999 → minute 3, à 3:00.000 → minute 4), cumuls et kills_1min_diff, premiers objectifs, frame de fin et minute 0 retirées, frame incomplète ignorée, signe et genre de chaque type d'event, event_team de load.py, bout en bout, readable_events sans pseudo, game_summary vu du joueur. tests/test_riot_id.py (10) : split_riot_id, nom de fichier du cache sans « ../ ». tests/test_winprob.py (11) : petit modèle de même forme entraîné dans le test ; base + contributions = logit de predict, variation = part des events + part du temps, rouge = miroir du bleu, explain_minute retombe sur la prédiction, player_report, message clair si le modèle manque.
- tests/test_db_vs_json.py (2, marqueur db) : version automatique de winprob.py check. Base VIDE (TEST_DATABASE_URL, nom obligatoirement en _test car le test efface tout), schema.sql, 12 parties au hasard insérées avec load.insert_match, puis variables minute par minute par la base (SQL de sequences.py) et par le JSON : écart 0 exigé ; et minute 15 = build_features. Sauté si TEST_DATABASE_URL n'est pas défini. A trouvé en l'écrivant : build_features (étape 12) compte le dragon ancestral avec les dragons, minute_table le met à part (elders_diff) ; sans effet réel, aucun ancestral avant 15 min.
- Vérifié que les tests attrapent de vraies erreurs : règle de la minute changée → 4 tests rouges ; signe des bâtiments inversé → 5 ; frame de fin gardée dans FRAMES_SQL → le test base vs JSON rouge.
- .github/workflows/tests.yml, à chaque push sur main et chaque pull request, 3 tâches sur une machine Linux neuve : unit (pytest), database (service PostgreSQL 16, base lol_test, PyTorch CPU, pytest -m db), docker (construit l'image, la lance, attend la réponse de /_stcore/health). Aucune clé Riot ni donnée. Badge en tête du README.
- Testé d'abord à part : 48 tests verts (Python 3.13, PostgreSQL 16) ; image construite (Python 3.14.7) ; docker compose up : les deux conteneurs « healthy », l'appli charge le modèle depuis le volume, check_db.py lancé DANS le conteneur de l'appli trouve les 7 tables via db:5432.
- Résultats sur le PC de Paul (4 nov.) : 46 passed + 2 skipped ; avec la base de test lol_test (docker compose exec db createdb -U lol lol_test, TEST_DATABASE_URL=...localhost:5433/lol_test) : 48 passed après correction. Problème rencontré : sous Windows, le test base = JSON restait bloqué sans message à l'import de PyTorch, fait APRÈS LightGBM / scikit-learn (conflit entre leurs bibliothèques OpenMP). Correction : tests/conftest.py importe torch en premier s'il est installé.
- GitHub Actions : 1er passage (d293a8f), tâche database rouge : le dépôt de paquets de PyTorch n'a pas filelock 4.2.6 (ResolutionImpossible). Correction (589289f) : dépendances de torch installées depuis PyPI avec -c requirements.txt, puis torch --no-deps depuis l'index CPU. 2e passage : 3 tâches vertes.
- README : badge, structure, « Running the app » (Docker), « Running the tests », section « Tests, Docker and CI ».

## Étape 20 faite : GIF de démo dans le README + Release du modèle (4 nov. 2026)
- But : montrer l'appli en 30 secondes en tête du README (un recruteur ne lance pas le code), et permettre à un inconnu de l'essayer sans collecter 5 000 parties.
- src/make_demo.py : un navigateur sans écran (Playwright, Chromium) joue un scénario fixe sur l'appli déjà lancée (http://localhost:8501) : taper le Riot ID lettre par lettre, Chercher, attendre les parties, survoler la courbe (infobulle), descendre aux moments clés, bouger le curseur « Minute ». Une capture après chaque action, avec sa durée d'affichage ; les captures sont assemblées en GIF avec Pillow.
- Pourquoi un script et pas un enregistreur d'écran (ScreenToGif, OBS) : rejouable à l'identique après chaque changement de l'appli, rien d'autre que la page n'est filmé (ni barre des tâches ni notifications), taille du fichier maîtrisée. Playwright plutôt qu'une vidéo convertie : pas besoin de ffmpeg, et chaque capture est prise au bon moment.
- Trois détails : (1) attendre Streamlit : après un cran de curseur, il relance le script environ 0,5 s plus tard ; on attend que l'icône « Running » APPARAISSE puis disparaisse (sinon on photographie l'ancienne page : curseur sur 17, texte encore sur 16). (2) Une seule palette de 256 couleurs pour tout le GIF, apprise (octree) sur une mosaïque de captures prises tout au long de la démo : avec la palette d'une seule image, les barres vertes devenaient grises et les points orange saumon. (3) Deux captures identiques à la suite = une seule, affichée plus longtemps (fichier léger). Menu et icône « Running » de Streamlit masqués par CSS. Arrêt avec un message clair si l'appli affiche une erreur Python.
- Options : --riot-id (obligatoire), --game (0 = partie la plus récente), --count, --width (960), --colors (256), --url, --out (docs/demo.gif).
- Vie privée : le GIF montre le Riot ID de Paul (le sien, déjà public) ; les autres joueurs n'y sont désignés que par leur champion (readable_events, scoreboard). Ne jamais filmer le Riot ID d'un ami.
- Release v2.0 sur GitHub : data/app_model.joblib (63 Ko : les coefficients des 40 logistiques, aucune donnée de joueur) en fichier joint, avec son empreinte SHA-256. Lien stable : releases/latest/download/app_model.joblib. README, « Trying the app without collecting data » : télécharger le modèle dans data/, mettre sa clé Riot dans .env, docker compose up -d --build app (l'appli seule, sans base). Un .joblib est un pickle Python (il peut exécuter du code au chargement) : d'où l'empreinte à vérifier ; modèle enregistré avec scikit-learn 1.9.1 (même version dans l'image Docker).
- Testé d'abord à part sur les parties en cache de Paul (faux client Riot) : 68 images, 28 s, 1,1 Mo ; couleurs et curseur vérifiés image par image.
- README : statut v2, GIF + légende en tête, make_demo.py et docs/demo.gif dans la structure, sections « Trying the app without collecting data » et « Recording the demo GIF », Roadmap (tout le plan prévu est fait).

## Prochaine étape
Tout le PLAN est fait. Idées : une clé de production Riot (site public), un modèle par rang.

## Étape 5 faite : décisions de conception (23 oct. 2026)
- sql/schema.sql = 7 tables : players(puuid), matches, teams (clé match_id + team_id), participants (clé match_id + participant_id, FK vers teams et players), participant_frames (match_id, participant_id, minute : toutes les frames gardées pour le GRU), events (event_id auto ; types CHAMPION_KILL, ELITE_MONSTER_KILL, BUILDING_KILL, TURRET_PLATE_DESTROYED), event_assists (table n,n entre events et participants).
- Choix : pas de win dans participants (déduit de teams) ; totalGold et pas currentGold ; killerId 0 de Riot -> NULL ; events.killer_team_id = équipe qui GAGNE l'objectif (pour BUILDING_KILL et TURRET_PLATE_DESTROYED, le teamId de Riot est l'équipe qui perd le bâtiment, donc on stocke 300 - teamId) ; puuid uniquement dans players (un seul endroit à pseudonymiser).
- Testé sur PostgreSQL 16 : le script s'exécute sans erreur et la partie EUW1_7995392565 se charge entièrement. Or à la minute 15 : équipe 100 = 26 387, équipe 200 = 27 591 (écart bleu - rouge = -1 204).
- Points à gérer à la collecte (étape 7) : convertir gameCreation (ms) en date ; killerId 0 -> NULL ; ignorer les events non listés ; parties de moins de 15 min (pas de frame 15) ; CHAMPION_KILL avec killerId 0 = exécution (tueur NULL, killer_team_id à déduire de la victime).
- Guide détaillé : guide-etape-5-mcd-mld.md (hors dépôt).

## Fichiers
- src/explore.py : charge la clé avec load_dotenv(), appelle account-v1 (Riot ID -> puuid), match-v5 /ids (5 dernières parties), puis match-v5 /matches/{MATCH_ID} (MATCH_ID = EUW1_7995392565, fixé en dur, comme explore_timeline.py) et enregistre le JSON dans data/match_exemple.json (encoding utf-8). Vérifie par un assert que le matchId correspond. Affiche la liste des ids.
- src/explore_timeline.py : appelle /lol/match/v5/matches/{matchId}/timeline pour EUW1_7995392565, enregistre data/timeline_exemple.json, affiche le nombre de frames.
- src/resume_timeline.py : relit data/timeline_exemple.json (aucun appel API), compte les types d'events et calcule l'écart d'or entre les équipes à 15 min.
- .env : contient RIOT_API_KEY=... (clé de développement, expire toutes les 24 h) et, à partir de l'étape 6, DATABASE_URL=postgresql://lol:lol@localhost:5433/lol. Ignoré par Git.
- .env.example : modèle versionné, sans vraie clé. Contient aussi RIOT_PLATFORM=euw1, RIOT_REGION=europe (pas encore utilisés par le code : BASE est écrit en dur) et DATABASE_URL (utilisé par src/check_db.py).
- docker-compose.yml : la base PostgreSQL 16 dans Docker (voir « Étape 6 ») et, depuis l'étape 19, l'appli (voir « Étape 19 faite »).
- src/riot_api.py et src/collect.py : client API et script de collecte (voir « Étape 7 faite » et « Étape 9 faite »).
- data/raw/ : parties brutes compressées (matches/, timelines/, players_done.txt, collect.lock). 5 000 parties, 401 Mo au 28 oct. Ignoré par Git.
- data/logs/collect.log : journal horodaté de la collecte (ajouté à chaque lancement). Ignoré par Git.
- src/check_db.py : test de connexion Python → PostgreSQL et présence des 7 tables.
- src/load.py et src/quality.py : insertion en base et contrôles qualité (voir « Étape 8 faite »).
- src/features.py : features à 15 min et score de scaling, importé par les modèles (voir « Étape 12 faite ») ; variables candidates build_extra_features (voir « Étape 13 bis faite »).
- src/models.py : modèles, préparation sans fuite, validation croisée, bootstrap (voir « Étape 13 faite »).
- src/explain.py : calibration (courbe de fiabilité, recalibrage) et valeurs de SHAP (voir « Étape 14 faite »).
- src/deep.py : modèles PyTorch (LogisticNet, MLP, WinGRU), boucle d'entraînement, adaptateur scikit-learn (voir « Étape 16 faite » et « Étape 17 faite »).
- src/sequences.py : données minute par minute, 3 modèles par minute, évaluation par partie (voir « Étape 17 faite »).
- src/live.py : démo en direct, API locale du jeu → probabilité chaque minute (voir « Étape bonus faite »). Fichiers créés dans data/ (ignorés par Git) : live_model.joblib, ddragon_items.json (prix des objets), live_captures/.
- src/match_minutes.py : calcul unique des variables minute par minute (base et JSON), résumé et événements lisibles d'une partie (voir « Étape 18 faite »). src/sequences.py l'importe depuis l'étape 18.
- src/winprob.py : modèle de l'appli (train, check), prédiction, contributions, moments clés, bilan de fiabilité (voir « Étape 18 faite »).
- src/riot_games.py : parties d'un joueur pour l'appli, API Riot + cache disque (voir « Étape 18 faite »).
- src/app.py : l'appli Streamlit (voir « Étape 18 faite »). .streamlit/config.toml : réglages de Streamlit (localhost, pas de statistiques).
- data/app_model.joblib (modèle de l'appli) et data/app_cache/ (parties téléchargées par l'appli) : créés par winprob.py train et par l'appli. Ignorés par Git.
- data/match_exemple.json : JSON complet de la partie EUW1_7995392565. Ignoré par Git.
- data/timeline_exemple.json : timeline de la même partie (34 frames). Ignoré par Git.
- requirements.txt : versions exactes des paquets (pip freeze), en UTF-8. Pour le régénérer : `pip freeze | Out-File -Encoding utf8 requirements.txt` (sinon PowerShell l'écrit en UTF-16 et GitHub l'affiche mal).
- README.md : présentation en anglais de la v1 (résultats, figures, pipeline, installation, limites, mention légale Riot).
- src/make_figures.py et docs/figures/ : figures du README (voir « Étape 15 faite »).
- PLAN.md : plan par étapes avec cases à cocher.
- sql/schema.sql : schéma PostgreSQL (7 tables, voir « Étape 5 faite »).
- notebooks/01_exploration.ipynb : analyse exploratoire (voir « Étape 10 faite »).
- notebooks/02_regression.ipynb : tests par régression logistique (voir « Étape 11 faite »).
- notebooks/03_models.ipynb : logistique vs LightGBM (voir « Étape 13 faite »).
- notebooks/04_improvements.ipynb : courbe d'apprentissage et nouvelles variables (voir « Étape 13 bis faite »).
- notebooks/05_calibration.ipynb : calibration et explications SHAP (voir « Étape 14 faite »).
- notebooks/06_pytorch.ipynb : tutoriel PyTorch, logistique et MLP (voir « Étape 16 faite »).
- notebooks/07_gru.ipynb : GRU vs logistique par minute vs LightGBM (voir « Étape 17 faite »).
- Dockerfile, .dockerignore, requirements-app.txt : image de l'appli (voir « Étape 19 faite »). docker-compose.yml : base + appli.
- pyproject.toml : réglages de pytest. tests/ : conftest.py (fausses parties), test_match_minutes.py, test_riot_id.py, test_winprob.py, test_db_vs_json.py (voir « Étape 19 faite »). Lancer : python -m pytest.
- .github/workflows/tests.yml : GitHub Actions (voir « Étape 19 faite »). Résultats : onglet Actions du dépôt.

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
- Rien pour l'instant. (Fait à l'étape 7 : get() sorti dans src/riot_api.py, région lue dans .env via RIOT_REGION. Les scripts d'exploration gardent leur propre get(), ce sont des scripts historiques.)

## Décision en attente
- Rien pour l'instant. (Fait le 28 oct. 2026 : dossier sorti de OneDrive vers C:\Users\pauld\projets\lol-analytics ; .venv supprimé puis recréé avec py -3.14 -m venv .venv, car un venv contient des chemins absolus. OneDrive demande alors de confirmer la suppression d'environ 6 380 éléments : c'est le .venv, répondre « Supprimer tous les éléments ».)

## Problèmes déjà rencontrés
- KeyError 'RIOT_API_KEY' : .env était vide (fichier non sauvegardé, Ctrl+S)
- 401 Unauthorized : clé expirée, à régénérer sur developer.riotgames.com puis la remettre dans .env
- 27 oct. : 401 juste après avoir régénéré la clé (account-v1 passait, match-v5 refusait) ; relancé une minute plus tard, tout marchait. Une nouvelle clé met parfois une minute à être active partout : attendre et relancer.
- Warning Git LF/CRLF sur Windows : sans danger
- Ctrl+P ne trouve pas les fichiers de data/ car ils sont ignorés par Git : ouvrir avec "code data/fichier.json"
- 22 oct. : une capture d'écran du terminal montrait le début de la clé Riot. Recadrer les captures avant de les envoyer.
- 3 nov. : ReadTimeout sur 127.0.0.1:2999 à la fin d'une partie (le jeu se ferme, l'API ne répond plus quelques secondes) : corrigé, watch s'arrête proprement.
- 4 nov. : « clé refusée » (401) dans l'appli Streamlit : clé expirée. La régénérer, enregistrer .env, puis Ctrl+C dans le terminal et relancer streamlit run src/app.py (la clé n'est lue qu'au démarrage).
- 2 nov. : TypeError « unexpected keyword argument 'oof' » après une mise à jour de src/models.py : le noyau du notebook gardait l'ancienne version en mémoire (Python n'importe un module qu'une fois). Après avoir modifié un .py importé : Restart du noyau, puis Run All.

## Règles
- Docker : au début de chaque séance qui utilise la base, ouvrir Docker Desktop puis `docker compose start` ; à la fin, `docker compose stop` puis fermer Docker Desktop.
- Ne jamais committer .env ni data/
- Ne jamais coller la clé Riot dans le chat (afficher .env avec (Get-Content .env) -replace '=.*','=***')
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public
- À la fin de chaque étape : mettre à jour CONTEXT.md, cocher PLAN.md, commit + push.
