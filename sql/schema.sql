-- =====================================================================
-- LoL Analytics : schéma de la base PostgreSQL
-- Une partie (match-v5 + sa timeline) remplit les 7 tables ci-dessous.
-- Ordre de création : une table est créée après celles qu'elle référence.
-- Le script tourne dans une transaction : tout est créé, ou rien.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. players : un joueur, identifié par son puuid (identifiant Riot stable).
--    Le puuid reste dans la base locale ; il sera pseudonymisé avant
--    toute publication (README, figures, appli).
-- ---------------------------------------------------------------------
CREATE TABLE players (
    puuid TEXT PRIMARY KEY
);

-- ---------------------------------------------------------------------
-- 2. matches : une partie (JSON match, partie "info").
-- ---------------------------------------------------------------------
CREATE TABLE matches (
    match_id           TEXT PRIMARY KEY,               -- ex. EUW1_7995392565
    platform_id        TEXT        NOT NULL,           -- ex. EUW1
    queue_id           INTEGER     NOT NULL,           -- 420 = classée solo/duo
    game_version       TEXT        NOT NULL,           -- ex. 16.19.821.7343
    game_creation      TIMESTAMPTZ NOT NULL,           -- converti depuis gameCreation (ms)
    game_duration_s    INTEGER     NOT NULL CHECK (game_duration_s > 0),
    end_of_game_result TEXT,                           -- ex. GameComplete
    collected_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 3. teams : les 2 équipes d'une partie (info.teams).
--    Clé composée : (match_id, team_id), car team_id vaut 100 ou 200
--    dans toutes les parties et ne suffit pas à identifier une équipe.
-- ---------------------------------------------------------------------
CREATE TABLE teams (
    match_id          TEXT     NOT NULL REFERENCES matches (match_id) ON DELETE CASCADE,
    team_id           SMALLINT NOT NULL CHECK (team_id IN (100, 200)),  -- 100 bleue, 200 rouge
    win               BOOLEAN  NOT NULL,                                -- la cible à prédire
    first_blood       BOOLEAN,
    first_tower       BOOLEAN,
    first_dragon      BOOLEAN,
    first_baron       BOOLEAN,
    champion_kills    SMALLINT,
    tower_kills       SMALLINT,
    inhibitor_kills   SMALLINT,
    dragon_kills      SMALLINT,
    rift_herald_kills SMALLINT,
    horde_kills       SMALLINT,
    baron_kills       SMALLINT,
    PRIMARY KEY (match_id, team_id)
);

-- ---------------------------------------------------------------------
-- 4. participants : un joueur dans une partie (info.participants).
--    participant_id (1 à 10) est le numéro utilisé par la timeline.
--    Pas de colonne win : elle se déduit de l'équipe (teams.win).
-- ---------------------------------------------------------------------
CREATE TABLE participants (
    match_id               TEXT     NOT NULL,
    participant_id         SMALLINT NOT NULL CHECK (participant_id BETWEEN 1 AND 10),
    team_id                SMALLINT NOT NULL,
    puuid                  TEXT     NOT NULL REFERENCES players (puuid),
    champion_id            INTEGER  NOT NULL,
    champion_name          TEXT     NOT NULL,
    team_position          TEXT,                 -- TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
    champ_level            SMALLINT,
    kills                  SMALLINT NOT NULL,
    deaths                 SMALLINT NOT NULL,
    assists                SMALLINT NOT NULL,
    gold_earned            INTEGER,
    total_minions_killed   INTEGER,
    neutral_minions_killed INTEGER,
    vision_score           INTEGER,
    damage_to_champions    INTEGER,              -- totalDamageDealtToChampions
    PRIMARY KEY (match_id, participant_id),
    UNIQUE (match_id, puuid),                    -- un joueur apparaît une seule fois par partie
    FOREIGN KEY (match_id, team_id) REFERENCES teams (match_id, team_id) ON DELETE CASCADE
);

-- Retrouver vite toutes les parties d'un joueur (ex. "mes parties").
CREATE INDEX idx_participants_puuid ON participants (puuid);

-- ---------------------------------------------------------------------
-- 5. participant_frames : l'état d'un joueur à chaque minute
--    (timeline, info.frames[minute].participantFrames).
--    On garde toutes les minutes : le GRU en a besoin, et l'état
--    à 15 min se lit avec WHERE minute = 15.
-- ---------------------------------------------------------------------
CREATE TABLE participant_frames (
    match_id              TEXT     NOT NULL,
    participant_id        SMALLINT NOT NULL,
    minute                SMALLINT NOT NULL CHECK (minute >= 0),   -- indice de la frame
    timestamp_ms          INTEGER  NOT NULL,
    total_gold            INTEGER  NOT NULL,     -- or gagné depuis le début (pas currentGold)
    xp                    INTEGER  NOT NULL,
    level                 SMALLINT NOT NULL,
    minions_killed        SMALLINT NOT NULL,
    jungle_minions_killed SMALLINT NOT NULL,
    position_x            INTEGER,
    position_y            INTEGER,
    PRIMARY KEY (match_id, participant_id, minute),
    FOREIGN KEY (match_id, participant_id)
        REFERENCES participants (match_id, participant_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 6. events : les événements utiles de la timeline.
--    Pas d'identifiant naturel : PostgreSQL numérote les lignes.
--    killer_id / victim_id : participant_id, ou NULL quand Riot met 0
--    (tour, sbire ou monstre, ex. une exécution).
--    killer_team_id : l'équipe qui GAGNE l'objectif. Attention, pour
--    BUILDING_KILL et TURRET_PLATE_DESTROYED, le teamId de Riot est
--    l'équipe qui PERD le bâtiment : on stocke donc l'autre équipe.
-- ---------------------------------------------------------------------
CREATE TABLE events (
    event_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id         TEXT     NOT NULL REFERENCES matches (match_id) ON DELETE CASCADE,
    minute           SMALLINT NOT NULL,          -- frame dans laquelle l'event est rangé
    timestamp_ms     INTEGER  NOT NULL,
    event_type       TEXT     NOT NULL CHECK (event_type IN (
                         'CHAMPION_KILL',
                         'ELITE_MONSTER_KILL',
                         'BUILDING_KILL',
                         'TURRET_PLATE_DESTROYED')),
    killer_id        SMALLINT,
    victim_id        SMALLINT,                   -- seulement pour CHAMPION_KILL
    killer_team_id   SMALLINT CHECK (killer_team_id IN (100, 200)),
    monster_type     TEXT,                       -- DRAGON, BARON_NASHOR, RIFTHERALD, HORDE...
    monster_sub_type TEXT,                       -- ex. AIR_DRAGON
    building_type    TEXT,                       -- TOWER_BUILDING, INHIBITOR_BUILDING
    tower_type       TEXT,                       -- OUTER_TURRET, INNER_TURRET...
    lane_type        TEXT,                       -- TOP_LANE, MID_LANE, BOT_LANE
    position_x       INTEGER,
    position_y       INTEGER,
    FOREIGN KEY (match_id, killer_id) REFERENCES participants (match_id, participant_id),
    FOREIGN KEY (match_id, victim_id) REFERENCES participants (match_id, participant_id)
);

-- Les requêtes filtrent presque toujours par partie puis par type.
CREATE INDEX idx_events_match_type ON events (match_id, event_type);

-- ---------------------------------------------------------------------
-- 7. event_assists : qui a aidé sur un event (assistingParticipantIds).
--    Association plusieurs-à-plusieurs entre events et participants :
--    une ligne par (event, participant qui assiste).
-- ---------------------------------------------------------------------
CREATE TABLE event_assists (
    event_id       BIGINT   NOT NULL REFERENCES events (event_id) ON DELETE CASCADE,
    participant_id SMALLINT NOT NULL CHECK (participant_id BETWEEN 1 AND 10),
    PRIMARY KEY (event_id, participant_id)
);

COMMIT;
