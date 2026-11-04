# LoL Analytics

[![tests](https://github.com/Paul-Delpierre/lol-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/Paul-Delpierre/lol-analytics/actions/workflows/tests.yml)

**Can you tell who will win a League of Legends match at 15 minutes, and how much should you trust that guess?**

End-to-end data project on ranked Solo/Duo matches (EUW): collection through the Riot API, a PostgreSQL database, statistical tests, a win-prediction model with leakage-free validation, calibration checks and SHAP explanations.

> **Status: v1.** Data pipeline, 15-minute win model, minute-by-minute win probability, a live demo and a local Streamlit app are done; the app and the database start with one Docker Compose command, and tests run on every push (GitHub Actions). Next: a demo GIF.

## Results at a glance

On 4,762 ranked matches (patches 16.14 to 16.21), with the 953 most recent matches held out as a test set and used once:

- **74% accuracy at 15 minutes** (log loss 0.524, AUC 0.81) with a **logistic regression on 11 game-state features**. LightGBM does not beat it (0.528, difference not significant).
- **Gold is most of the story.** The team ahead in gold wins far more often; at equal gold, **dragons** still matter (about as much as 1,000 gold each) and XP adds a little. Kills, towers and CS add nothing beyond the gold they bring.
- **The probabilities can be trusted as they are**: a match announced at 70% is won about 70% of the time (calibration error 2.8 points, all 10 deciles within their confidence interval). No recalibration needed.
- **The limit is the information, not the model.** More matches, more features, tuning and ensembling all failed to improve the test score.
- **Minute by minute, a GRU does not beat a logistic regression per minute** (test log loss 0.536 vs 0.533, difference not significant): the cumulative game state already carries the history (see [Win probability minute by minute](#win-probability-minute-by-minute)).
- **A local Streamlit app** turns any Riot ID into win-probability curves, key moments and per-minute explanations, with features computed by the same code as in training (checked: zero difference on 200 matches; see [Streamlit app](#streamlit-app)).
- **Two data leaks were found and measured**, not just avoided (see [Model comparison](#model-comparison-logistic-regression-vs-lightgbm)).

| Gold at 15 minutes vs the final result | Calibration on the test set |
|---|---|
| ![Blue win rate by gold-difference decile](docs/figures/win_rate_by_gold.png) | ![Reliability curve of the logistic regression](docs/figures/calibration.png) |

## How it works

```mermaid
flowchart LR
    A[Riot API<br/>match-v5] -->|collect.py<br/>rate limits, retries| B[(data/raw<br/>gzipped JSON)]
    B -->|load.py<br/>checks, 1 transaction per match| C[(PostgreSQL<br/>7 tables)]
    C -->|quality.py| C
    C -->|features.py<br/>one SQL query| D[Features<br/>at 15 min]
    D -->|models.py<br/>time-ordered CV| E[Logistic regression<br/>vs LightGBM]
    E -->|explain.py| F[Calibration<br/>+ SHAP]
```

Raw API responses are kept on disk before anything is inserted: API calls are the scarce resource (development key: 100 requests per 2 minutes), so the database can be rebuilt at any time without downloading again.

## Project structure

```
lol-analytics/
├── src/
│   ├── riot_api.py       # API client: rate limiter, retries, errors
│   ├── collect.py        # background collection of matches and timelines
│   ├── load.py           # raw JSON -> PostgreSQL (idempotent)
│   ├── quality.py        # consistency checks on the database
│   ├── features.py       # 15-minute features (SQL) and champion scaling score
│   ├── models.py         # models, leakage-free preparation, CV, paired bootstrap
│   ├── explain.py        # calibration tools and SHAP values
│   ├── deep.py           # PyTorch models (MLP, GRU) and training loop
│   ├── sequences.py      # minute-by-minute data, per-minute models, game-level evaluation
│   ├── match_minutes.py  # minute-by-minute features, shared by training (database) and the app (JSON)
│   ├── winprob.py        # the app's model: training, predictions, key moments, explanations
│   ├── riot_games.py     # the app's Riot API access with an on-disk cache
│   ├── app.py            # Streamlit app (local)
│   ├── live.py           # live demo: local game API -> win probability each minute (personal use)
│   └── make_figures.py   # rebuilds the README figures
├── notebooks/
│   ├── 01_exploration.ipynb   # exploratory analysis
│   ├── 02_regression.ipynb    # hypothesis tests (statsmodels)
│   ├── 03_models.ipynb        # logistic regression vs LightGBM
│   ├── 04_improvements.ipynb  # learning curve, new features
│   ├── 05_calibration.ipynb   # calibration and SHAP
│   ├── 06_pytorch.ipynb       # PyTorch: logistic regression and MLP
│   └── 07_gru.ipynb           # minute by minute: GRU vs per-minute logit vs LightGBM
├── tests/                # pytest: features, Riot ID, model functions, database vs JSON
├── sql/schema.sql        # database schema (7 tables)
├── .streamlit/config.toml # app settings (local only, no usage stats)
├── .github/workflows/tests.yml # CI: unit tests, database test, Docker build
├── docs/figures/         # README figures
├── data/                 # local data (not versioned)
├── Dockerfile            # image of the Streamlit app (no PyTorch, no secrets, non-root)
├── docker-compose.yml    # PostgreSQL 16 + the app
├── requirements.txt      # exact versions of every package
├── requirements-app.txt  # the app's packages only (image and CI)
└── pyproject.toml        # pytest settings
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

### Reproducing the results

```bash
python src/collect.py --riot-id "GameName#TAG" --max-matches 5000   # a few hours
python src/load.py                 # insert the new matches
python src/quality.py              # checks, prints OK / ATTENTION
# then run notebooks/01 to 07 in order
python src/make_figures.py         # regenerate docs/figures/
```

### Running the app

```bash
python src/winprob.py train        # once: trains the app's model (needs the database), ~5 min
python src/winprob.py check        # optional: app features vs database features, should print 0.0
streamlit run src/app.py           # then open http://localhost:8501
```

Or with Docker, once the model is trained (it is read from `data/`, the Riot key from `.env`):

```bash
docker compose up -d --build       # database + app, then open http://localhost:8501
docker compose stop                # stop both (data kept)
```

### Running the tests

```bash
python -m pytest                   # ~50 tests in a few seconds, no API key, no data needed
```

The database test is skipped unless `TEST_DATABASE_URL` points to an empty database whose name ends in `_test` (it wipes it). With the Docker database: `docker compose exec db createdb -U lol lol_test`, then set `TEST_DATABASE_URL=postgresql://lol:lol@localhost:5433/lol_test`.

Your numbers will differ slightly: the sample depends on the starting player and on the patches you collect.

## Data pipeline

### Collection

`src/collect.py` downloads ranked Solo/Duo matches and their timelines (match-v5) as compressed JSON files in `data/raw/`. It starts from one player and snowballs through the other players of each match.

- **Rate limits**: `src/riot_api.py` keeps the development-key limits (20 requests/s and 100 requests/2 min) with two sliding windows, and waits for `Retry-After` on HTTP 429.
- **Retries**: network errors and 5xx responses are retried with exponential backoff (about 4 minutes in total); after that, or when the 24 h development key expires, the script stops cleanly.
- **Resume**: files are written atomically and never downloaded twice; running the same command again continues after a stop.
- **Long runs**: a timestamped log in `data/logs/collect.log` (with matches per hour and estimated end time), Windows sleep prevention while it runs, and a lock file so two collections never write to the same folder.

```powershell
.\.venv\Scripts\python.exe src\collect.py --riot-id "GameName#TAG" --max-matches 5000
Get-Content data\logs\collect.log -Encoding utf8 -Wait -Tail 20   # follow progress from another window
```

### Loading and quality checks

`src/load.py` reads the raw files and fills the 7 tables of `sql/schema.sql`; `src/quality.py` then runs consistency checks.

- **Idempotent**: matches already in the database are skipped, so the script can run after each collection.
- **One transaction per match**: a match is inserted completely or not at all.
- **Checks before insertion**: remakes, wrong queue, incomplete teams, missing values or a timeline that does not match the game are rejected with a reason.
- **Checks after insertion**: 2 teams and one winner per match, 10 players, no missing minute, total gold never decreasing, and timeline events matching the match summary (kills, towers, dragons).

5,000 matches were collected; 4,907 passed the checks.

## Analysis

### Exploratory analysis

`notebooks/01_exploration.ipynb` reads the database with SQL (aggregations run in PostgreSQL) and plots the main patterns with 95% confidence intervals.

- **Gold at 15 min** is the strongest single signal: the blue side wins 7% of games in the most behind decile and 94% in the most ahead one.
- **Early leads overlap**: gold, XP and kill differences at 15 min are 0.90 to 0.92 correlated, so a model must not read them as independent effects.
- **Red side** wins 51.7% of games (95% CI 50.3% to 53.1%) in this sample.
- **Champions**: among 160 champions played at least 100 times, the number whose win-rate interval excludes 50% is about what chance alone would produce.

### Hypothesis tests

`notebooks/02_regression.ipynb` tests three questions with logistic regression (statsmodels): one row per match seen from the blue side, blue-minus-red differences at 15 min, odds ratios with 95% confidence intervals and likelihood-ratio tests between nested models.

- **Gold almost sums up the lead.** Each 1,000 gold ahead at 15 min multiplies the odds of winning by 1.44. At equal gold, **dragons still matter** (odds ratio 1.30 per dragon ahead, about the weight of 1,000 gold) and XP adds a little (1.10 per 1,000 XP); kills, towers, plates and CS add nothing beyond their gold.
- **First tower has no effect of its own.** It goes with 2.5 times higher odds, but at equal gold the effect disappears (0.94, 95% CI 0.79 to 1.13): it is a sign of the lead, not an extra cause.
- **The red-side edge is small and goes through dragons.** Blue wins 48.5% of games (95% CI 47.0% to 49.9%); at equal dragon difference the edge is gone (50.9%, 95% CI 49.1% to 52.7%).

These are controlled associations, not causal effects: player skill and team compositions are not measured.

## Predicting the winner at 15 minutes

### Features

`src/features.py` builds one row per match seen from the blue side, with blue-minus-red differences at 15 min, in a single SQL query.

- **Game state** (11 features): gold, XP, CS, kills, towers, plates, dragons and void grubs taken before 15 min, plus first blood / first tower / first dragon coded +1 (blue), −1 (red), 0 (none).
- **Gold by role**: the gold difference per position, for tree models only (it adds up to total gold, so it would be collinear in a logistic regression).
- **No leakage by design**: only events before 15 min; columns known only after the game (duration) are kept apart from the feature lists.
- **Champion scaling score**: each champion's win rate in long games minus its win rate in short games, smoothed towards 50% so that rare champions do not get extreme scores by chance. It uses the match outcome, so it is **learned on training matches only** and then applied to test matches. Sanity check: the top scores go to known late-game champions (Kayle, Kassadin, Vladimir) and the lowest to early-game ones (Kled, Kennen, Mordekaiser).

### Model comparison: logistic regression vs LightGBM

`notebooks/03_models.ipynb`, with reusable pieces in `src/models.py`.

- **Protocol**: the 953 most recent matches are the test set, used once. Every choice (LightGBM hyperparameters, feature sets) is made on the 3,809 older matches with **time-ordered cross-validation** (5 folds, always validating on matches more recent than the training ones). Main metric: **log loss**, which rates the probabilities and not only the predicted winner.
- **No leakage**: the scaling scores, the scaler and the model are refit inside each fold, and training matches get **out-of-fold** scaling scores, so that no match sees its own result in its score (the classic target-encoding trap).

Test-set results (953 matches):

| Model | Features | Log loss | AUC | Accuracy |
|---|---|---|---|---|
| Constant (blue win rate) | none | 0.692 | 0.500 | 52.9% |
| Logistic regression | gold only | 0.539 | 0.799 | 72.5% |
| **Logistic regression** | **11 game-state features** | **0.524** | **0.813** | **74.1%** |
| Logistic regression | + scaling score and gold × scaling | 0.527 | 0.812 | 74.4% |
| LightGBM (4 leaves, 200 trees) | 11 features + gold by role | 0.528 | 0.809 | 73.0% |
| LightGBM | + scaling score | 0.530 | 0.808 | 73.4% |

- **Logistic regression is the chosen model.** LightGBM is not significantly different (paired bootstrap on log loss: +0.004, 95% CI −0.003 to +0.011) and is behind on 3 of 5 folds; the best LightGBM is the simplest in the grid. The signal is mostly linear and driven by gold.
- **The 11 features beat gold alone** (−0.015 log loss, 95% CI −0.026 to −0.005).
- **The scaling score does not help at 15 minutes** (+0.002, CI −0.003 to +0.008).
- **Leakage, measured**: learning the scaling scores with the validation matches makes the score look useful (0.524 instead of 0.530 in cross-validation); applying them to the matches they were learned on makes the model overweight it and do worse (0.535). Leakage can bias a conclusion in either direction.

### Trying to improve the model

`notebooks/04_improvements.ipynb` tests whether more data or more features would help (same protocol, test set used once).

![Learning curve of both models](docs/figures/learning_curve.png)

- **Learning curve**: going from 1,600 to 3,175 training matches moves the logistic regression's validation log loss from 0.524 to 0.523. LightGBM is still improving but starts about 0.01 behind. Collecting many more matches would not change the picture.
- **New features** (gold at 10 min and gold trend, level difference, richest-player gap, players dead at 15:00, dragons by type) are 0.80 to 0.89 correlated with gold. Two groups passed a selection rule fixed in advance, but the gain vanished on the test set (+0.003, 95% CI −0.002 to +0.007): a small cross-validation gain after trying five groups is mostly luck.
- **Regularization and ensembling** do not help either.

### Calibration and explanations

`notebooks/05_calibration.ipynb`, with tools in `src/explain.py`.

- **Well calibrated as is.** On the test set: Brier score 0.175, expected calibration error 2.8 points, calibration slope 1.04 (95% CI 0.89 to 1.18), and all 10 probability deciles within the confidence interval of the predicted rate. The model also commits: 35% of matches get a probability below 20% or above 80%. LightGBM is slightly worse (error 4.2 points).
- **No recalibration kept.** Platt scaling and isotonic regression, learned on out-of-fold predictions, make the test log loss slightly worse (+0.001 and +0.007). Those out-of-fold predictions come from models trained on fewer matches and are overconfident (slope 0.93), a flaw the final model does not have: recalibrating on them would fix a problem that is not there.
- **SHAP without the `shap` package.** For a linear model the exact SHAP value of a feature is coefficient × (value − training mean), on the log-odds scale; LightGBM computes TreeSHAP itself (`pred_contrib=True`). Both match the `shap` library to 1e-15.

![Mean absolute SHAP value per feature](docs/figures/shap_importance.png)

Gold difference dominates (0.82), then dragons (0.41) and XP (0.28). Kills, towers and CS get small negative weights at equal gold: SHAP explains the model, not causes in the game, and gold and XP should be read together since they move together.

### Neural networks (PyTorch)

`notebooks/06_pytorch.ipynb`, with models and the training loop in `src/deep.py`. This is the groundwork for the minute-by-minute model.

- **Same logistic regression, rebuilt in PyTorch.** Written by hand (weights, gradient descent and the same L2 penalty as scikit-learn), it recovers scikit-learn's coefficients to 0.002 and the same test log loss, 0.5242. With standard PyTorch blocks (`nn.Linear`, AdamW, mini-batches, early stopping on the most recent training matches) it reaches 0.5243. This checks the training loop on a problem with a known answer.
- **Same evaluation as the other models.** A small adapter gives the network scikit-learn's `fit` / `predict_proba` interface, so it goes through the same time-ordered cross-validation; the scaler and early stopping are fitted inside each fold.
- **A multilayer perceptron does not help.** Cross-validated log loss: 0.5285 for the PyTorch logistic regression, 0.5363 with 16 hidden units, 0.5401 with 64. On the test set the 16-unit network scores 0.5285 vs 0.5242 (difference +0.004, 95% CI −0.001 to +0.009). As with LightGBM, the 15-minute signal is close to linear and ~3,800 training matches leave little for a more flexible model to find.

## Win probability minute by minute

`notebooks/07_gru.ipynb`, with data, models and evaluation in `src/sequences.py` and the GRU in `src/deep.py`. Same matches and same test set as above; every minute of every match becomes one prediction (141,149 match-minutes).

- **Data.** The 11 features of the 15-minute model are rebuilt at every minute, plus Baron, Elder dragon, Rift Herald, inhibitors and kills in the last minute. An event counts at minute *t* only if it happened before *t*, and the final frame (the exact moment the game ends) is dropped. At minute 15 this table matches the 15-minute features exactly, except 8 matches where both teams got first blood in the same millisecond.
- **Three models.** A logistic regression per minute (one model for each minute, 40+ pooled), one LightGBM over all match-minutes with the minute as a feature, and a GRU (32 hidden units) that reads the match minute by minute and outputs a probability at each minute. The GRU is unidirectional, and a test checks it: changing a match after minute 20 leaves its predictions for minutes 1-20 exactly unchanged.
- **Leakage-free evaluation.** Splits are always by match, never by row (all minutes of a match stay on the same side), in time order. Confidence intervals come from a bootstrap over matches: a row-level bootstrap treats the ~30 minutes of a match as independent and gives an interval about three times too narrow.

| Log loss, all match-minutes | Cross-validation | Test |
|---|---|---|
| Logistic regression per minute | **0.546** | **0.533** |
| GRU | 0.548 | 0.536 |
| LightGBM | 0.554 | 0.535 |

On the test set the GRU is +0.003 behind the per-minute logistic regression (95% CI −0.001 to +0.008) and +0.002 behind LightGBM (CI −0.004 to +0.006): no detectable difference. Gold, towers and objectives are cumulative, so the state at minute *t* already summarises the match; recent momentum, the one thing only the GRU sees, adds nothing measurable with ~3,800 training matches. At minute 15 the per-minute model scores 0.5241, the same as the 15-minute model (0.5242). Log loss falls from 0.65 at 5 minutes to 0.40 at 25 minutes, then rises again (0.49 at 35 minutes): matches still running that late are the close ones. The app will use the per-minute logistic regression.

## Streamlit app

`src/app.py`, run locally with `streamlit run src/app.py`. Enter a Riot ID: the app downloads the player's latest ranked Solo/Duo matches and, for each one, shows the probability that **the player's team** wins at every minute, the key moments, and what drives the probability at any chosen minute. It runs on the developer's own machine only: a Riot development key does not allow a public site.

- **Model.** The per-minute logistic regression of the previous section (16 features, exact gold from the timeline), retrained on all 4,762 matches. Before saving, `python src/winprob.py train` re-checks the test score (log loss 0.5327, AUC 0.802, as above). The app only loads the saved model: it needs neither the database nor PyTorch.
- **Same features in training and in the app.** Training reads the database; the app reads the JSON of the Riot API. Both now call one function (`minute_table` in `src/match_minutes.py`), and the JSON is turned into the same two inputs as the SQL queries, with the same rules as the loader (who gets credit for a building, final frame dropped). `python src/winprob.py check` compares both paths on 200 collected matches: **6,042 match-minutes, largest difference 0.0**.
- **Key moments.** Between two minutes, both the game state and the model change (each minute has its own regression: 1,000 gold matter more at 10 minutes than at 30). The change is split exactly into the part due to what happened in the game, f<sub>t</sub>(x<sub>t</sub>) − f<sub>t</sub>(x<sub>t−1</sub>), and the part due to time, f<sub>t</sub>(x<sub>t−1</sub>) − f<sub>t−1</sub>(x<sub>t−1</sub>). The five minutes with the largest game-driven change are shown with the events of that minute (champions only: other players are never named).
- **Explanations.** Exact SHAP values of the logistic regression (coefficient × distance to the average), with the model of the chosen minute, as in [Calibration and explanations](#calibration-and-explanations).
- **Is the model reliable for this player?** For 10, 15 and 20 minutes the app compares correct calls and log loss with what the model's own probabilities predict, and runs a Monte Carlo test (20,000 simulated outcomes) to tell bad luck from a real gap. On 141 matches of three players at 15 minutes: 94 correct calls for 102 expected, log loss 0.553 for 0.539 expected; a gap at least this large happens by chance 35% of the time, and the calibration slope is 1.00. No sign that the model reads these players worse.
- **Robust to the API.** The Riot client of the collection step handles rate limits and retries; downloaded matches are cached in `data/app_cache/` (kept apart from the training data), and when the 24-hour development key has expired the app falls back to the matches already downloaded.

## Live demo (personal use only)

`src/live.py` reads the game's local [Live Client Data API](https://developer.riotgames.com/docs/lol) (`https://127.0.0.1:2999`, served by the game on the player's own PC during a match) and prints the win probability once per minute. Personal use and analysis only: never in competitive play, not distributed, and it only reads what the in-game scoreboard already shows.

- **Less data than the timeline.** There are no events for turret plates or Void Grubs, only levels instead of XP, CS in steps of 10, and no gold for the other nine players. The live model is the per-minute logistic regression retrained on what the API provides, with XP (minimum XP of the current level) and CS (rounded down to 10) computed the same way in training, so the model sees the same definitions in training and in a game.
- **Gold is left out.** The item value of the ten players looks like a substitute, but rebuilt from 293 match timelines it correlates only 0.78 with the real gold gap at 15 minutes (typical error 1,500 gold). In a real game it was fooled by unspent gold: an AFK player held about 10,000 gold with 2,150 gold of items.
- **What it costs**, on the same test set (log loss, all match-minutes):

| Model | Test log loss | vs per-minute model (95% CI, bootstrap over matches) |
|---|---|---|
| Per-minute logistic regression (16 features, timeline data) | 0.5327 | |
| Live, no gold (13 features) | **0.5365** | +0.004 (−0.001 to +0.009) |
| Live, events only (11 features) | 0.5483 | +0.016 (+0.009 to +0.022) |

  Gold mostly comes from kills, CS, towers and XP, which the no-gold model already sees, so dropping it costs little. At minute 15 the no-gold model scores 0.5345 (0.5241 with the timeline data).
- **Checked end to end.** Matches from the database turned into fake API payloads give exactly the training features (4,520 match-minutes compared). Two games against bots were checked against the end-of-game scoreboard. Tower names in the real game (`Turret_TChaos_L1_P3_...`) differ from the documented format (`Turret_T2_L_03_A`); both are handled.

```bash
python src/live.py train                # retrains the live models (needs the database)
python src/live.py watch                # during a match: one line per minute
python src/live.py watch --minute 15    # a single line at 15 minutes
python src/live.py dump                 # saves the raw game state (JSON) for debugging
```

## Tests, Docker and CI

- **Tests** (`tests/`, pytest). Real matches are not in the repository, so the tests build fake ones in the exact Riot JSON format (`tests/conftest.py`): a quiet game with hand-placed events when the right answer is known, or a random game with every event type, including the tricky ones (executions, buildings credited to the team that did *not* lose them, monsters killed by no team, the elder dragon). They pin down the rules the model depends on: an event at 12:34 is first seen at minute 13, cumulative vs last-minute counts, first objectives, the final frame dropped, signs from the blue side; the app's explanations add up exactly to its predictions and the red side mirrors the blue side; other players are never named.
- **Training-serving skew test.** `tests/test_db_vs_json.py` is the automatic version of `winprob.py check`: it creates the schema in an empty PostgreSQL database, inserts 12 random games with the real loader, then computes the minute-by-minute features both ways (SQL for training, JSON for the app). They must be identical. It caught a real subtlety while it was written: the 15-minute features count the elder dragon among dragons, the minute-by-minute ones keep it apart; both are right because no elder dragon can spawn before 15 minutes.
- **Docker.** `docker compose up -d` starts the database and the app. The app image holds the code and the packages it needs (no PyTorch, about 280 MB compressed), runs as a non-root user, and contains no secret and no data: `.env` is read at start-up and `data/` (model, cache) is mounted from the host. Inside Docker's network the app reaches the database as `db:5432`; from the host it stays `localhost:5433`. Both ports are bound to `127.0.0.1` only.
- **CI** (`.github/workflows/tests.yml`), on every push to `main` and every pull request, on a fresh Linux machine: the unit tests; the database test against a PostgreSQL 16 service; and a build of the Docker image, started and checked through Streamlit's health endpoint. No API key and no data are needed.

## Limitations

- **Sample**: about 5,000 EUW Solo/Duo matches from a snowball that starts at one player, over eight patches. It is not a random sample of the ladder, and rank is not used.
- **Game state only**: the models see gold, XP, kills and objectives, not positions, vision or items, which is where a sequence model could find more.
- **Associations, not causes**: team compositions, player skill and in-game decisions are not measured.

## Roadmap

- **App**: a demo GIF in this README.

## Data & privacy

Match data comes from the [Riot Games API](https://developer.riotgames.com/). Raw data and API keys are not published in this repository; player identifiers are pseudonymized.

*LoL Analytics isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.*
