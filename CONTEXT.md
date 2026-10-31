# Contexte du projet (pour reprendre une conversation)

## Projet
LoL Analytics : analyse de parties League of Legends via l'API Riot, projet perso IA/data publié sur GitHub (pour le CV). Le plan complet est dans PLAN.md. Mon niveau et la façon de travailler sont dans CLAUDE.md (fichier local).

## Façon de travailler (règles fixées les 21 et 22 oct. 2026)
- Claude écrit tout le code ; Paul n'en écrit pas, mais chaque morceau est expliqué en détail (pourquoi + comment, ligne par ligne).
- Explication du code (règle actuelle, 27 oct. 2026 au soir) : expliquer le code par parties : ce que fait chaque partie, POURQUOI (choix de conception, alternatives écartées) et la structure d'ensemble. Le « comment » rapidement, pas ligne par ligne. Objectif : que Paul sache répondre à des questions de structure en entretien ; il pose ses questions de détail sur le coup.
- Chaque étape du plan = un guide détaillé, pas à pas : commandes expliquées, ce qu'on doit voir, erreurs possibles, points de contrôle.
- CONTEXT.md est rempli et mis à jour uniquement par Claude, jamais par Paul. Si Claude n'a pas accès au dossier local, il fournit le fichier complet et Paul le colle tel quel.
- Paul est débutant en Git et en terminal : expliquer chaque commande donnée.

## Environnement
- Windows, VS Code, terminal PowerShell
- Dépôt local : C:\Users\pauld\projets\lol-analytics (branche main). Sorti de OneDrive le 28 oct. 2026 (ancien chemin : C:\Users\pauld\OneDrive\Bureau\lol-analytics). Garder le nom du dossier lol-analytics : Docker nomme le volume de la base d'après lui (lol-analytics_pgdata).
- GitHub : https://github.com/Paul-Delpierre/lol-analytics (public)
- Python 3.14.7, venv .venv (activé automatiquement dans le terminal de VS Code, le prompt commence par (.venv))
- Paquets (requirements.txt) : requests 2.34.2, pandas 3.0.6, numpy 2.5.4, python-dotenv 1.2.4, psycopg 3.3.6 + psycopg-binary 3.3.6 (ajoutés à l'étape 6), matplotlib 3.11.2 + ipykernel 7.4.0 (ajoutés à l'étape 10), et leurs dépendances
- Notebooks : ouverts dans VS Code (extension Jupyter), noyau « .venv (3.14.7) » choisi avec Select Kernel. Pas de paquet jupyter complet : VS Code n'a besoin que d'ipykernel.
- Docker Desktop (à partir de l'étape 6) : PostgreSQL 16 tourne dans le conteneur lol-postgres

## État d'avancement (mis à jour le 31 oct. 2026, fin de l'étape 11)
- Étapes faites (cochées dans PLAN.md) : dépôt GitHub, venv + paquets, clé Riot + premiers appels (account-v1, match-v5 /ids et /matches/{id}), étape 4 « Comprendre le format JSON d'une partie et de sa timeline », étape 5 « MCD / MLD → sql/schema.sql » (schéma écrit et testé le 23 oct.), étape 6 « PostgreSQL dans Docker » (base lancée sur le PC le 26 oct.), étape 7 « Script de collecte » (testée sur le PC le 27 oct. : 80 parties dans data/raw).
- Étape 8 « Insertion en base + contrôles qualité » faite le 27 oct. 2026 (testée sur le PC : 10/10 contrôles OK).
- Étape 9 « Lancer la collecte en fond » faite le 28 oct. 2026 : 5 000 parties sur le disque, 4 907 en base, contrôles 8/10 OK + 2 avertissements expliqués (voir « Étape 9 faite »).
- Étape 10 « Analyse exploratoire (notebook) » faite le 30 oct. 2026 : notebooks/01_exploration.ipynb exécuté sur les 4 907 parties, conclusions écrites (voir « Étape 10 faite »).
- Étape 11 « 2-3 questions testées » faite le 31 oct. 2026 : notebooks/02_regression.ipynb (régression logistique, statsmodels) exécuté sur 4 762 parties, conclusions écrites (voir « Étape 11 faite »).
- Historique Git :
  1. Initial project structure
  2. Update plan: mark repo creation as done
  3. Set up Python environment
  4. Etape 3 : premiers appels API Riot
  5. Ajout de CONTEXT.md pour reprendre le contexte
  6. 286c1f1 Mise à jour de CONTEXT.md et ajout de CLAUDE.md au .gitignore
  7. 9c987d4 Convert requirements to UTF-8, update CONTEXT.md and .gitignore
  8. f747d0e Etape 4 : exploration de la timeline (explore_timeline.py, resume_timeline.py, PLAN.md, CONTEXT.md)
  9. b44816a Fix CONTEXT.md formatting
  10. 00ca27f Etape 5 : schema SQL (MCD/MLD) et fix explore.py
  11. 6c2f5f0 Etape 6 : PostgreSQL dans Docker
  12. 3aa562f Etape 7 : script de collecte (limites de debit, 429, reprise)
  13. Etape 8 : insertion en base et controles qualite (load.py, quality.py, README, PLAN, CONTEXT) — commit + push par Paul le 27 oct.
  14. Etape 9 : collecte en fond (collect.py, riot_api.py, quality.py, README, PLAN, CONTEXT) — commit + push par Paul (2a52292, 46919ab).
  15. Etape 10 : notebook d'analyse exploratoire (notebook, requirements.txt, README, PLAN, CONTEXT) — commit + push par Paul (4da0dc8).
  16. Etape 11 : régression logistique (notebook 02, requirements.txt, README, PLAN, CONTEXT) — commit + push par Paul.
- Vérification du 26 oct. 2026 : étapes 1 à 5 complètes. Le dépôt GitHub et le dossier du PC sont identiques (mêmes fichiers, même contenu), aucun secret ni fichier de data/ dans l'historique Git, .gitignore correct. Seul écart corrigé : CLAUDE.md (local) n'avait pas la règle « Claude écrit tout le code » ; il a été remis à jour.
- Étape 4 en résumé : la timeline de EUW1_7995392565 a été récupérée (34 frames, partie d'environ 33 min) et enregistrée dans data/timeline_exemple.json. Sa structure est décrite plus bas.

## Étape 6 faite : PostgreSQL dans Docker (26 oct. 2026)
- Fichiers écrits par Claude sur le PC (testés dans le cloud avec Docker + PostgreSQL 16.15 : les 7 tables sont créées, les données survivent à docker compose down / up) :
  - docker-compose.yml : service db, image postgres:16, conteneur lol-postgres, utilisateur / mot de passe / base = lol, port 127.0.0.1:5433 côté PC (5432 dans le conteneur), volume nommé pgdata (sur le PC : lol-analytics_pgdata), sql/schema.sql monté dans /docker-entrypoint-initdb.d/ (exécuté seulement quand le volume est vide), healthcheck pg_isready.
  - src/check_db.py : se connecte avec psycopg à DATABASE_URL (lu dans .env) et vérifie que les 7 tables existent.
  - requirements.txt : + psycopg 3.3.6 et psycopg-binary 3.3.6 (roue Windows pour Python 3.14 disponible).
  - README.md : section Setup complétée (venv, pip install -r requirements.txt, .env, docker compose up -d, check_db.py).
- Fait sur le PC de Paul : Docker Desktop installé (il a fallu activer la Virtual Machine Platform avec `wsl --install --no-distribution` en PowerShell administrateur, puis redémarrer), DATABASE_URL ajouté à .env, docker compose up -d, vérification avec psql dans le conteneur et python src/check_db.py. Guide : Claude Doc « Étape 6 — PostgreSQL dans Docker ».
- Utilisation au quotidien : ouvrir Docker Desktop, puis `docker compose start` (ou `up -d`) avant de travailler avec la base ; à la fin de la séance, `docker compose stop` puis quitter Docker Desktop (il prend 1 à 2 Go de RAM).
- Si schema.sql change plus tard : les tables ne sont recréées que si le volume est vide → docker compose down -v (efface toutes les données) puis docker compose up -d.

- Problème du 26 oct. : docker compose up -d échouait avec « ports are not available: listen tcp4 127.0.0.1:5432: bind: An attempt was made to access a socket in a way forbidden by its access permissions ». 5432 n'est pas dans les plages réservées par Windows (netsh … excludedportrange : 28385, 28390, 50000-50059) et redémarrer winnat n'a rien changé : un autre programme utilise déjà 5432 sur le PC. Solution : port 5433 côté PC (docker-compose.yml, .env, .env.example).

## Étape 7 faite : script de collecte (26-27 oct. 2026)
- Choix : l'étape 7 télécharge le JSON brut sur le disque (zone « raw ») et n'écrit PAS en base. L'insertion PostgreSQL + contrôles qualité = étape 8. Raison : les appels API sont la ressource rare ; on peut refaire l'insertion sans retélécharger.
- src/riot_api.py : RateLimiter (deux fenêtres glissantes 20 req/1 s et 100 req/120 s, une deque par fenêtre, affiche les pauses > 1 s) ; RiotClient(api_key, region) avec requests.Session et l'en-tête X-Riot-Token ; get(path, **params) : 200 -> JSON, 404 -> None, 401/403 -> RiotKeyError (message avec le chemin et la réponse de Riot), 429 -> attend Retry-After, 5xx et erreurs réseau -> backoff 2, 4, 8, 16 s ; 5 essais max.
- src/collect.py : collecte « boule de neige » (parcours en largeur) depuis un Riot ID ; match-v5 /ids avec queue=420 ; pour chaque partie, match + timeline enregistrés dans data/raw/matches/<id>.json.gz et data/raw/timelines/<id>.json.gz (gzip, écriture atomique .tmp puis os.replace) ; les 9 autres joueurs vont dans la file. Reprise : une partie est faite si ses 2 fichiers existent ; joueurs parcourus dans data/raw/players_done.txt ; la file est reconstruite au démarrage à partir des fichiers de match. Options : --riot-id (obligatoire), --max-matches (objectif TOTAL sur le disque, 20 par défaut), --per-player (20 par défaut). Ctrl+C et clé expirée -> arrêt propre avec message.
- Commande : python src/collect.py --riot-id "TECHNIQUEMENT#99999" --max-matches 20
- Testé dans le cloud avec un faux serveur Riot (429, 503, 404, reprise), puis sur le PC le 27 oct. : 20 parties, puis 80 (pause du limiteur de 84 s observée, Ctrl+C à 68, reprise jusqu'à 80). Résultat : 80 matchs + 80 timelines, 6,4 Mo (≈ 80 Ko par partie), toutes en queue 420, aucun .tmp. Environ 24 parties/min au maximum (2 requêtes par partie), soit ≈ 1 400/h.
- Limite à connaître : l'échantillon part de Paul (biais de niveau au début) ; seules les --per-player dernières parties de chaque joueur sont prises.
- README : section « Data collection » ajoutée. Guide : Claude Doc « Étape 7 — Script de collecte » (https://claude.ai/artifact/MMmDJrCtXXLbWbszmnJy5c).

## Étape 8 faite : insertion en base + contrôles qualité (27 oct. 2026)
- src/load.py (écrit par Claude) : lit data/raw/matches/*.json.gz + la timeline de même nom, et remplit les 7 tables avec psycopg (DATABASE_URL de .env, autocommit).
  - Idempotent : les match_id déjà en base sont sautés (SELECT match_id FROM matches au début). Relancer le script après chaque collecte n'insère que les nouvelles parties. players : INSERT ... ON CONFLICT DO NOTHING (un joueur revient dans plusieurs parties).
  - Une transaction par partie (with conn.transaction()) : la partie est insérée entièrement ou pas du tout ; une erreur SQL sur une partie est affichée et le script continue.
  - Contrôles AVANT insertion (check_match, partie refusée avec sa raison) : timeline d'une autre partie, queueId ≠ 420, remake (gameEndedInEarlySurrender ou < 5 min), pas 10 joueurs numérotés 1-10, équipes ≠ 5/5, pas exactement une équipe gagnante, participantId timeline ≠ match, valeur obligatoire manquante, frame incomplète.
  - Valeurs facultatives absentes -> NULL (p.get(...)) ; teamPosition "" -> NULL ; killerId/victimId 0 -> NULL.
  - killer_team_id : CHAMPION_KILL -> équipe du tueur, ou 300 - équipe de la victime si exécution ; ELITE_MONSTER_KILL -> killerTeamId, NULL si 300 (héraut mort sans équipe, 10 cas sur 80 parties) ; BUILDING_KILL et TURRET_PLATE_DESTROYED -> 300 - teamId.
  - Les parties de plus de 5 min mais de moins de 15 min sont gardées (vraies parties, utiles au GRU) : le modèle à 15 min les exclura avec WHERE minute = 15.
  - Option --limit N : n'insère que N nouvelles parties (pour tester).
- src/quality.py (écrit par Claude) : ne fait que lire. Affiche des chiffres (parties, joueurs, durées, parties sans minute 15, % victoires bleues, exécutions, patchs) et 10 contrôles SQL (OK / ATTENTION n cas) : 2 équipes et un seul gagnant par partie, 10 joueurs 5/5, aucune minute manquante, or total jamais en baisse, kills timeline (hors exécutions) = somme des kills du match par équipe, tours et dragons timeline = tower_kills / dragon_kills, aucun poste manquant, aucun remake.
- Découverte : teams.champion_kills de Riot compte parfois les exécutions et parfois non ; le contrôle fiable est « kills avec un tueur dans la timeline = somme de participants.kills ».
- Test dans le cloud (PostgreSQL 16, schema.sql, les 80 parties du PC) : 79 insérées + 1 remake refusé (EUW1_7961274942, 119 s), 2e lancement : 0 insérée, 79 déjà en base. ≈ 0,08 s par partie. Tables : 79 matches, 158 teams, 670 players, 790 participants, 24 290 participant_frames, 11 768 events, 8 461 event_assists. quality.py : 10/10 OK. Or à 15 min de EUW1_7995392565 identique à l'étape 5 (26 387 / 27 591).
- README : section « Loading into PostgreSQL » ajoutée.
- Fait sur le PC de Paul le 27 oct. : load.py --limit 5, load.py, relance (0 insérée, pas de doublon), quality.py : 10/10 contrôles OK. Guide : Claude Doc « Étape 8 — Insertion en base + contrôles qualité » (https://claude.ai/artifact/156x2HZrwLsmciAWfmkvMM).
- Repartir de zéro si besoin (efface les données, garde les tables) : docker exec -it lol-postgres psql -U lol -d lol -c "TRUNCATE matches, players CASCADE;"

## Étape 9 faite : collecte en fond (28 oct. 2026)
- Dossier sorti de OneDrive le 28 oct. : C:\Users\pauld\projets\lol-analytics (même nom de dossier, donc même volume Docker lol-analytics_pgdata ; premier lancement après le déplacement avec docker compose up -d, qui recrée le conteneur avec le nouveau chemin). .venv supprimé puis recréé (py -3.14 -m venv .venv) ; piège rencontré : pip install lancé sans (.venv) dans le prompt installe dans le Python du PC (« Requirement already satisfied … pythoncore-3.14-64 ») → activer avec .venv\Scripts\Activate.ps1 puis relancer pip.
- Code (écrit par Claude, testé dans le cloud avec un faux serveur Riot) :
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
- Guide : Claude Doc « Étape 9 — Collecte en fond » (https://claude.ai/artifact/K1DSMirV5KudR2PawJMjHY).

## Étape 10 faite : analyse exploratoire (30 oct. 2026)
- notebooks/01_exploration.ipynb (écrit par Claude, testé dans le cloud sur 613 parties, exécuté par Paul sur toute la base, résultats enregistrés dans le fichier et commités pour que GitHub affiche les graphiques ; aucun identifiant de joueur dedans).
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
- Guide : Claude Doc « Étape 10 — Analyse exploratoire » (https://claude.ai/artifact/GYeByCahxvkotSmdMNn5M5).

## Étape 11 faite : 3 questions testées par régression logistique (31 oct. 2026)
- notebooks/02_regression.ipynb (écrit par Claude, testé dans le cloud sur 3 000 parties synthétiques, exécuté par Paul sur la vraie base, résultats enregistrés dans le fichier). statsmodels 0.15.0 ajouté au venv (+ scipy, patsy, formulaic ; requirements.txt régénéré).
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
- Générateur du notebook (pour Claude) : /mnt/project-files/lol-analytics/etape11/build_nb.py. Guide : Claude Doc « Étape 11 — Régression logistique » (https://claude.ai/artifact/2etVcQzSA2VfDTLtY9JD5j).

## Prochaine étape : étape 12, features à 15 min
Premier point de la période « modèle à 15 min → v1 publique » : construire le jeu de features à 15 min (or, XP, objectifs, kills…) dans un module Python réutilisable (src/), pour la régression logistique vs LightGBM qui suit. D'après l'étape 11 : or, XP et dragons portent l'information en logistique ; garder aussi kills, tours, plaques, CS pour LightGBM (effets non linéaires possibles). Côté et patch en contrôles, effet attendu proche de zéro.

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
- .env : contient RIOT_API_KEY=... (clé de développement, expire toutes les 24 h) et, à partir de l'étape 6, DATABASE_URL=postgresql://lol:lol@localhost:5433/lol. Ignoré par Git.
- .env.example : modèle versionné, sans vraie clé. Contient aussi RIOT_PLATFORM=euw1, RIOT_REGION=europe (pas encore utilisés par le code : BASE est écrit en dur) et DATABASE_URL (utilisé par src/check_db.py).
- docker-compose.yml : la base PostgreSQL 16 dans Docker (voir « Étape 6 »).
- src/riot_api.py et src/collect.py : client API et script de collecte (voir « Étape 7 faite » et « Étape 9 faite »).
- data/raw/ : parties brutes compressées (matches/, timelines/, players_done.txt, collect.lock). 5 000 parties, 401 Mo au 28 oct. Ignoré par Git.
- data/logs/collect.log : journal horodaté de la collecte (ajouté à chaque lancement). Ignoré par Git.
- src/check_db.py : test de connexion Python → PostgreSQL et présence des 7 tables.
- src/load.py et src/quality.py : insertion en base et contrôles qualité (voir « Étape 8 faite »).
- data/match_exemple.json : JSON complet de la partie EUW1_7995392565. Ignoré par Git.
- data/timeline_exemple.json : timeline de la même partie (34 frames). Ignoré par Git.
- requirements.txt : versions exactes des paquets (pip freeze), en UTF-8. Pour le régénérer : `pip freeze | Out-File -Encoding utf8 requirements.txt` (sinon PowerShell l'écrit en UTF-16 et GitHub l'affiche mal).
- README.md : présentation en anglais (objectifs, structure, installation complète, mention légale Riot), à compléter avec les résultats.
- PLAN.md : plan par étapes avec cases à cocher.
- CLAUDE.md : contexte pour Claude Code (local, ignoré par Git).
- sql/schema.sql : schéma PostgreSQL (7 tables, voir « Étape 5 faite »).
- notebooks/01_exploration.ipynb : analyse exploratoire (voir « Étape 10 faite »).
- notebooks/02_regression.ipynb : tests par régression logistique (voir « Étape 11 faite »). tests/ : vide (un .gitkeep).

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
- Ctrl+P ne trouve pas les fichiers de data/ car ils sont ignorés par Git : ouvrir avec "code data/fichier.json" (pareil pour CLAUDE.md)
- 22 oct. : une capture d'écran du terminal montrait le début de la clé Riot. Recadrer les captures avant de les envoyer.

## Règles
- Docker : Claude rappelle à Paul, au début de chaque séance qui utilise la base, d'ouvrir Docker Desktop puis de faire `docker compose start`, et à la fin, de faire `docker compose stop` puis de fermer Docker Desktop (demande de Paul du 26 oct. 2026).
- Ne jamais committer .env, data/ ni CLAUDE.md
- Ne jamais coller la clé Riot dans le chat (afficher .env avec (Get-Content .env) -replace '=.*','=***')
- Pseudonymiser les identifiants des autres joueurs
- Clé de dev = usage perso uniquement, pas de site public
- À la fin de chaque étape : Claude met à jour CONTEXT.md, PLAN.md est coché, commit + push, puis Claude recopie lui-même PLAN.md et CONTEXT.md dans les fichiers du projet claude.ai (knowledge/claude/)
