import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

# Les 7 tables créées par sql/schema.sql (étape 5).
TABLES_ATTENDUES = {
    "players",
    "matches",
    "teams",
    "participants",
    "participant_frames",
    "events",
    "event_assists",
}

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    version = conn.execute("SHOW server_version").fetchone()[0]
    lignes = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    ).fetchall()

tables = {ligne[0] for ligne in lignes}
print("Connexion OK, PostgreSQL", version)
print("Tables trouvées :", ", ".join(sorted(tables)))

manquantes = TABLES_ATTENDUES - tables
if manquantes:
    print("Tables manquantes :", ", ".join(sorted(manquantes)))
else:
    print("Les 7 tables sont là : la base est prête.")
