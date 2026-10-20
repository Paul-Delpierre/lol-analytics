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
└── data/        # Local data (not versioned)
```

## Setup

```bash
cp .env.example .env   # then add your Riot API key
```

## Data & privacy

Match data comes from the [Riot Games API](https://developer.riotgames.com/). Raw data and API keys are not published in this repository; player identifiers are pseudonymized.

*LoL Analytics isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.*
