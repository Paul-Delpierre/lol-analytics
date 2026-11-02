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

## Exploratory analysis

`notebooks/01_exploration.ipynb` reads the database with SQL (aggregations run in PostgreSQL) and plots the main patterns with matplotlib, with 95 % confidence intervals. Findings on 4,907 matches:

- **Gold at 15 min** is the strongest single signal: the blue side wins 7 % of games in the most behind decile and 94 % in the most ahead one (S-shaped curve).
- **Early leads overlap**: gold, XP and kill differences at 15 min are strongly correlated (0.90 to 0.92), so a model must not read them as independent effects.
- **Red side** wins 51.7 % of games (95 % CI: 50.3 % to 53.1 %) in this sample.
- **Champions**: among 160 champions played at least 100 times, the number whose interval excludes 50 % is about what chance alone would produce.

## Statistical tests

`notebooks/02_regression.ipynb` tests three questions with logistic regression (statsmodels): one row per match seen from the blue side, blue-minus-red differences at 15 min, odds ratios with 95 % confidence intervals and likelihood-ratio tests between nested models. Results on 4,762 matches (patches 16.14 to 16.21, at least 15 min):

- **Gold almost sums up the lead.** Each 1,000 gold ahead at 15 min multiplies the odds of winning by 1.44. At equal gold, **dragons still matter** (odds ratio 1.30 per dragon ahead, about the weight of 1,000 gold) and XP adds a little (1.10 per 1,000 XP); kills, towers, plates and CS add nothing beyond the gold they bring.
- **First tower has no effect of its own.** Taking the first tower before 15 min goes with 2.5 times higher odds, but at equal gold the effect disappears (0.94, 95 % CI 0.79 to 1.13): it is a sign of the lead, not an extra cause.
- **The red-side edge is small and goes through dragons.** Blue wins 48.5 % of games (95 % CI 47.0 to 49.9 %); the patch does not change this, and at equal dragon difference the edge is gone (50.9 %, 95 % CI 49.1 to 52.7 %).

These are controlled associations, not causal effects: player skill and team compositions are not measured.

## Features at 15 minutes

`src/features.py` builds the dataset used by the prediction models: one row per match seen from the blue side, with blue-minus-red differences at 15 min, computed by a single SQL query (aggregations in PostgreSQL).

```bash
python src/features.py    # builds the dataset, runs checks, shows the scaling score
```

- **Game state** (`FEATURES`): gold, XP, CS, kills, towers, plates, dragons and void grubs taken before 15 min, plus first blood / first tower / first dragon coded +1 (blue), -1 (red), 0 (none). No Rift Herald is killed before 15 min in this sample, so it is left out.
- **Gold by role** (`ROLE_FEATURES`): the gold difference per position. It adds up to total gold, so it is meant for tree models, not alongside total gold in a logistic regression.
- **No leakage by design**: only events before 15 min are used, and columns known only after the game (duration) are kept apart from the feature lists.
- **Champion scaling score**: each champion gets a score = its win rate in long games minus its win rate in short games (split at the median duration), smoothed towards 50 % so that rarely played champions do not get extreme scores by chance. Team scores are summed, and the model sees the blue-minus-red difference and its interaction with the gold difference. The scores use the match outcome, so they are **learned on training matches only** (`fit_scaling`) and then applied to test matches (`add_scaling`).

Results on 4,762 matches (time-ordered split: 3,809 older matches to learn the scores, 953 most recent to test):

- The highest scores go to known late-game champions (Kayle, Kassadin, Vladimir, Smolder, Orianna) and the lowest to early-game ones (Kled, Kennen, Mordekaiser, Diana), which is a sanity check on the method.
- On test matches, the team with the better scaling score wins 53.6 % of long games and 49.1 % of short ones. If the scores are learned including the test matches (leakage), the gap looks almost four times larger (59.1 % vs 42.4 %).
- With about 950 test matches, a 4.5-point gap is close to the noise level: whether the score improves predictions is tested with cross-validation in the next section.

## Model comparison: logistic regression vs LightGBM

`notebooks/03_models.ipynb` compares models that predict the blue side's win probability at 15 min. Reusable pieces (models, leakage-free preparation, cross-validation, paired bootstrap) live in `src/models.py`.

- **Protocol**: the 953 most recent matches are held out as a test set and used once. Every choice (LightGBM hyperparameters, feature sets) is made on the 3,809 older matches with **time-ordered cross-validation** (`TimeSeriesSplit`, 5 folds: always validate on matches more recent than the training ones). Main metric: **log loss** (quality of the probabilities), plus Brier score, AUC and accuracy.
- **No leakage**: the champion scaling scores, the scaler and the model are refit inside each fold. Training matches get **out-of-fold** scaling scores (`oof_scaling`), so that no match sees its own result in its score (the classic target-encoding trap).

Test-set results (953 matches):

| Model | Features | Log loss | AUC | Accuracy |
|---|---|---|---|---|
| Constant (blue win rate) | none | 0.692 | 0.500 | 52.9 % |
| Logistic regression | gold only | 0.539 | 0.799 | 72.5 % |
| **Logistic regression** | **11 game-state features** | **0.524** | **0.813** | **74.1 %** |
| Logistic regression | + scaling score and gold × scaling | 0.527 | 0.812 | 74.4 % |
| LightGBM (4 leaves, 200 trees) | 11 features + gold by role | 0.528 | 0.809 | 73.0 % |
| LightGBM | + scaling score | 0.530 | 0.808 | 73.4 % |

- **Logistic regression is the best model.** LightGBM is not significantly different (paired bootstrap on log loss: +0.004, 95 % CI −0.003 to +0.011) and is behind on 3 of 5 cross-validation folds. The signal is mostly linear and driven by gold; the best LightGBM is the simplest in the grid, and bigger trees do worse.
- **The 11 features beat gold alone** (−0.015 log loss, 95 % CI −0.026 to −0.005): dragons and XP add information, kills, towers and CS do not.
- **The scaling score does not improve 15-minute predictions** (+0.002 on test, CI −0.003 to +0.008).
- **Leakage, measured**: learning the scaling scores with the validation matches makes the score look useful (0.524 instead of 0.530 in cross-validation); applying them to the matches they were learned on makes the model overweight it and do worse (0.535). Leakage can bias a conclusion in either direction.

Chosen model: logistic regression on the 11 features. Next: calibration (reliability curve) and SHAP explanations.

### Trying to improve the 15-minute model

`notebooks/04_improvements.ipynb` tests whether more data or more features would beat the logistic regression above (same protocol, test set used once):

- **Learning curve**: training the logistic regression on 1,600 then 3,175 matches only moves validation log loss from 0.524 to 0.523 (−0.0008 for the last 775 matches). LightGBM is still improving but starts about 0.01 behind. Collecting many more matches would not change the picture for this model.
- **New features** (`build_extra_features` in `src/features.py`): gold at 10 min and gold trend, level difference, richest-player gold gap, players dead at 15:00, dragons by type. They are 0.80–0.89 correlated with the gold difference. Two groups passed a selection rule fixed in advance (better on at least 4 of 5 folds), but the gain vanished on the test set (+0.003 log loss, 95 % CI −0.002 to +0.007): a small cross-validation gain after trying five groups is mostly luck.
- **Regularization and ensembling** (logistic `C`, average of logistic and LightGBM) do not help either.

At 15 minutes, the game state summarized as team differences gives about 0.52 log loss and 74 % accuracy, and the limit comes from the information available, not from the model. The 11-feature logistic regression is kept.

### Calibration and explanations

`notebooks/05_calibration.ipynb` checks whether the chosen model's probabilities can be trusted, and explains them. Tools live in `src/explain.py`.

- **The logistic regression is well calibrated as is.** On the 953 test matches: Brier score 0.175, expected calibration error 2.8 points, calibration slope 1.04 (95 % CI 0.89 to 1.18) and intercept 0.02 (CI −0.13 to 0.17); all 10 probability deciles have an observed win rate within the confidence interval of the predicted one. Predictions are also spread out (35 % of matches below 20 % or above 80 %). LightGBM is slightly worse calibrated (ECE 4.2 points).
- **No recalibration is kept.** Platt scaling and isotonic regression, learned on out-of-fold predictions of the training period, do not improve test log loss (+0.001 and +0.007). Those out-of-fold predictions come from models trained on fewer matches and are slightly overconfident (slope 0.93), a flaw the final model does not have: recalibrating on them would correct a problem that is not there.
- **SHAP explanations without the `shap` package.** For a linear model the exact SHAP value of a feature is coefficient × (value − training mean), on the log-odds scale; LightGBM computes TreeSHAP itself (`pred_contrib=True`). Both match the `shap` library to 1e-15. Mean absolute contribution (logistic regression): gold difference 0.82, dragons 0.41, XP 0.28, first dragon 0.16, everything else below 0.10. Kills, towers and CS get small negative effects at equal gold: SHAP explains the model, not causes in the game.

The app will show the logistic regression's probability unchanged, with a per-match breakdown (baseline, then the features that moved the prediction most).

## Data & privacy

Match data comes from the [Riot Games API](https://developer.riotgames.com/). Raw data and API keys are not published in this repository; player identifiers are pseudonymized.

*LoL Analytics isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.*
