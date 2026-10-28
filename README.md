# LoL Analytics

> Work in progress — personal project.

End-to-end data project on League of Legends ranked matches: data collection through the Riot API, a PostgreSQL database, statistical analysis, win-prediction models and a small web app.

## Goals

- **Data pipeline**: collect ranked matches and timelines via the Riot API (rate limits, retries), store them in PostgreSQL.
- **Statistics**: test simple game hypotheses properly (e.g. effect of the first dragon at equal gold difference).
- **Machine learning**: predict the winner at 15 minutes (logistic regression vs LightGBM), with leakage-free validation and calibration.
- **Deep learning**: minute-by-minute win-probability curve with a GRU (PyTorch).
- **App**: Streamlit dashboard, Dockerized.

## Project structure

```
lol-analytics/
├── src/         # Python code (collection, processing, models)
├── sql/         # Database schema
├── notebooks/   # Exploration and analysis
├── tests/       # Unit tests
├── data/        # Local data (not versioned)
└── docker-compose.yml  # PostgreSQL database
```

## Setup

Requirements: Python 3.14 and Docker Desktop.

```bash
# 1. Python environment
python -m venv .venv
.venv\Scripts\activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env               # then add your Riot API key

# 3. Database (PostgreSQL 16 in Docker; tables are created from sql/schema.sql on first start)
docker compose up -d
python src/check_db.py             # should list the 7 tables
```

## Data collection

`src/collect.py` downloads ranked Solo/Duo matches and their timelines (match-v5) as compressed JSON files in `data/raw/`. It starts from one player and snowballs through the other players of each match.

```bash
python src/collect.py --riot-id "GameName#TAG" --max-matches 20
```

- **Rate limits**: `src/riot_api.py` keeps the development-key limits (20 requests/s and 100 requests/2 min) with two sliding windows, and waits for `Retry-After` on HTTP 429.
- **Retries**: network errors and 5xx responses are retried with exponential backoff.
- **Resume**: files are written atomically and never downloaded twice; run the same command again to continue after a stop.

### Background collection

For a long run (several thousand matches, a few hours), start the collection in its own PowerShell window, outside the editor, and follow it from anywhere with the log file:

```powershell
.\.venv\Scripts\python.exe src\collect.py --riot-id "GameName#TAG" --max-matches 5000
Get-Content data\logs\collect.log -Encoding utf8 -Wait -Tail 20   # follow progress from another window
```

- **Log file**: every message is also written with a timestamp to `data/logs/collect.log`, with a progress report (matches per hour, estimated end time) every 100 matches.
- **No sleep**: the script asks Windows not to go to sleep while it runs (`SetThreadExecutionState`); the screen can still turn off.
- **One run at a time**: a lock on `data/raw/collect.lock` refuses a second collection in the same folder. The OS releases it when the script stops, even after a crash.
- **Long outages**: network errors and Riot 5xx are retried for about 4 minutes; after that, or when the 24 h development key expires, the script stops cleanly and the same command resumes it.
- Then load the new matches with `python src/load.py` and check them with `python src/quality.py`.

## Loading into PostgreSQL

`src/load.py` reads the raw files and fills the 7 tables of `sql/schema.sql`. `src/quality.py` then runs consistency checks on the database.

```bash
python src/load.py        # insert every new match from data/raw
python src/quality.py     # read-only checks, prints OK / ATTENTION
```

- **Idempotent**: matches already in the database are skipped, so the script can be run again after each collection.
- **One transaction per match**: a match is inserted completely or not at all.
- **Checks before insertion**: remakes, wrong queue, incomplete teams, missing values or a timeline that does not match the game are rejected with a reason.
- **Checks after insertion**: 2 teams and one winner per match, 10 players, no missing minute, total gold never decreasing, and timeline events matching the match summary (kills, towers, dragons).

## Data & privacy

Match data comes from the [Riot Games API](https://developer.riotgames.com/). Raw data and API keys are not published in this repository; player identifiers are pseudonymized.

*LoL Analytics isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.*
