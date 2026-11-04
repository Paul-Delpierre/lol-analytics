# =====================================================================
# LoL Analytics : image Docker de l'appli Streamlit (étape 19)
# Construite et lancée par docker compose (service « app »), ou à la main :
#   docker build -t lol-analytics-app .
# L'image contient le code et les paquets, JAMAIS les secrets ni les données :
# .env et data/ sont exclus (.dockerignore) et fournis au lancement.
# =====================================================================

# Même version de Python que sur le PC (3.14.7), en variante « slim » (Debian allégée).
FROM python:3.14.7-slim

# LightGBM (importé par src/models.py) a besoin de la bibliothèque OpenMP.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Les paquets AVANT le code : Docker garde chaque étape en cache, et cette étape
#    (la plus longue) n'est refaite que si un fichier requirements change.
#    -c requirements.txt : mêmes versions exactes que sur le PC.
COPY requirements.txt requirements-app.txt ./
RUN pip install --no-cache-dir -r requirements-app.txt -c requirements.txt

# 2. Le code (change souvent : seule cette étape est refaite après une modification).
COPY src/ src/
COPY .streamlit/ .streamlit/

# Un utilisateur sans droits d'administration : si l'appli avait une faille,
# l'attaquant ne serait pas « root » dans le conteneur.
RUN useradd --create-home appuser && mkdir -p data && chown appuser data
USER appuser

# Dans le conteneur, Streamlit doit écouter toutes les interfaces (0.0.0.0) pour que
# Docker puisse lui passer les connexions ; c'est docker-compose.yml qui limite
# l'accès à ce PC (127.0.0.1:8501). Cette variable remplace « address » de config.toml.
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    PYTHONUNBUFFERED=1
EXPOSE 8501

CMD ["streamlit", "run", "src/app.py"]
