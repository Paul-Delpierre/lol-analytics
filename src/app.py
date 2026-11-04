"""Appli Streamlit : un Riot ID -> ses parties -> la courbe de probabilité de victoire.

Lancement (depuis la racine du projet, venv activé) :
    streamlit run src/app.py
puis le navigateur s'ouvre sur http://localhost:8501. L'appli tourne SUR CE PC
uniquement : la clé de développement Riot interdit un site public.

Ce que fait l'appli, de haut en bas :
1. Barre de gauche : Riot ID et nombre de parties ; infos sur le modèle.
2. Liste des dernières parties classées solo/duo du joueur (riot_games.py : API Riot
   + cache disque data/app_cache/), une partie choisie dans un menu.
3. Pour cette partie : variables minute par minute depuis le JSON (match_minutes.py,
   même calcul que l'entraînement), probabilité de victoire de SON équipe à chaque
   minute (winprob.py, logistique par minute de l'étape 17), moments clés, et
   l'explication d'une minute choisie (contributions de l'étape 14).

Streamlit relance tout ce script à chaque clic. Les fonctions lentes sont donc mises en
cache : st.cache_resource pour ce qui se partage (modèle, client Riot avec ses limites
de débit), st.cache_data pour les résultats (liste de parties, analyse d'une partie).
"""

import altair as alt
import pandas as pd
import streamlit as st

from match_minutes import TIME, game_summary, minute_features, readable_events, scoreboard
from riot_games import (CACHE, PlayerNotFound, RiotKeyError, get_game, make_client,
                        recent_games)
from winprob import explain_minute, key_moments, load_model, player_report, predict

REMAKE_S = 5 * 60   # comme load.py : une partie de moins de 5 min est un remake
POSITIONS = {"TOP": "top", "JUNGLE": "jungle", "MIDDLE": "mid", "BOTTOM": "ADC",
             "UTILITY": "support"}

st.set_page_config(page_title="LoL Analytics", page_icon="📈", layout="wide")


# ---------------------------------------------------------------------------
# 1. Ressources et données (en cache)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_model():
    return load_model()


@st.cache_resource
def get_client():
    return make_client()


@st.cache_data(ttl=600, show_spinner=False)
def player_games(riot_id, count):
    """Liste des parties (10 min en cache : une nouvelle partie apparaît ensuite)."""
    return recent_games(get_client(), riot_id, count)


@st.cache_data(show_spinner=False, max_entries=200)
def analyse(match_id, puuid):
    """Tout ce que l'appli affiche pour une partie, calculé une seule fois."""
    game = get_game(get_client(), match_id)
    if game is None:
        return None
    match, timeline = game
    summary = game_summary(match, puuid)
    if summary is None or match["info"]["gameDuration"] < REMAKE_S:
        return None
    table = minute_features(match, timeline)
    return {"summary": summary, "table": table, "events": readable_events(match, timeline),
            "scoreboard": scoreboard(match, puuid)}


def pct(p):
    return f"{100 * p:.0f} %"


# ---------------------------------------------------------------------------
# 2. Barre de gauche
# ---------------------------------------------------------------------------
st.sidebar.title("LoL Analytics")
with st.sidebar.form("search"):
    riot_id = st.text_input("Riot ID", placeholder="Pseudo#TAG")
    count = st.slider("Nombre de parties", 5, 50, 20)
    submitted = st.form_submit_button("Chercher", type="primary")
if submitted:
    st.session_state["riot_id"], st.session_state["count"] = riot_id.strip(), count

try:
    model = get_model()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

st.sidebar.caption(
    f"Modèle : une régression logistique par minute, apprise sur {model['n_games']} "
    f"parties classées (patchs {model['patches'][0]} à {model['patches'][-1]}), "
    f"log loss {model['test_log_loss']:.3f} sur les parties de test. "
    "Usage personnel, en local : la clé de développement Riot n'autorise pas de site public.")

st.title("Probabilité de victoire, minute par minute")
if not st.session_state.get("riot_id"):
    st.markdown(
        "Entre un Riot ID à gauche (par exemple `TECHNIQUEMENT#99999`). L'appli télécharge "
        "ses dernières parties classées solo/duo et, pour chacune, montre la probabilité "
        "que **son équipe** gagne à chaque minute, les moments qui l'ont fait basculer et "
        "ce qui pèse dans la balance à la minute de ton choix.")
    st.stop()

# ---------------------------------------------------------------------------
# 3. Les parties du joueur
# ---------------------------------------------------------------------------
rid, count = st.session_state["riot_id"], st.session_state["count"]
try:
    with st.spinner("Recherche du joueur…"):
        puuid, ids, offline_since = player_games(rid, count)
except ValueError as e:                      # Riot ID mal écrit
    st.error(str(e))
    st.stop()
except PlayerNotFound as e:
    st.error(str(e))
    st.stop()
except RiotKeyError as e:
    st.error(f"Clé Riot refusée et aucune partie en cache pour ce joueur.\n\n{e}")
    st.stop()
except RuntimeError as e:
    st.error(f"API Riot injoignable et aucune partie en cache pour ce joueur.\n\n{e}")
    st.stop()
if offline_since:
    st.warning(f"API Riot indisponible (clé expirée ?) : liste de parties enregistrée le "
               f"{offline_since}. Seules les parties déjà téléchargées s'affichent.")

games = {}
progress = st.progress(0.0, text="Téléchargement des parties…")
for i, match_id in enumerate(ids, start=1):
    result = analyse(match_id, puuid)
    if result is not None:
        games[match_id] = result
    progress.progress(i / max(len(ids), 1), text=f"Parties : {i}/{len(ids)}")
progress.empty()
if not games:
    st.info("Aucune partie classée solo/duo exploitable pour ce joueur.")
    st.stop()


def label(match_id):
    s = games[match_id]["summary"]
    return (f"{s['date'].tz_convert('Europe/Paris'):%d/%m %H:%M} · {s['champion']} "
            f"{POSITIONS.get(s['position'], '')} · {'Victoire' if s['win'] else 'Défaite'} · "
            f"{s['kda']} · {s['duration_min']:.0f} min")


wins = sum(g["summary"]["win"] for g in games.values())
st.caption(f"{rid} : {len(games)} parties classées, {wins} victoires.")

# ---------------------------------------------------------------------------
# Bilan : le modèle lit-il ce joueur aussi bien qu'une partie moyenne ?
# ---------------------------------------------------------------------------
report = player_report(model, [(g["table"], 1 if g["summary"]["team"] == 100 else -1,
                                g["summary"]["win"]) for g in games.values()])
report15 = report[report[TIME] == 15]
if len(report15):
    r = report15.iloc[0]
    title = (f"Fiabilité du modèle sur ce joueur : {int(r['bons pronostics'])}/{int(r['parties'])} bons "
             f"pronostics à 15 min (attendus : {r['bons attendus']:.1f})")
    with st.expander(title):
        st.dataframe(pd.DataFrame({
            "minute": report[TIME],
            "parties": report["parties"],
            "bons pronostics (attendus)": [f"{a} ({b:.1f})" for a, b in
                                           zip(report["bons pronostics"], report["bons attendus"])],
            "log loss (attendue)": [f"{a:.3f} ({b:.3f})" for a, b in
                                    zip(report["log loss"], report["log loss attendue"])],
            "écart aussi grand par hasard": [pct(h) for h in report["hasard"]],
            "remontées": report["remontées"],
            "avances perdues": report["avances perdues"]}), hide_index=True, width="stretch")
        verdict = ("le modèle lit **moins bien** ce joueur que la moyenne (moins de 5 % de "
                   "chances que ce soit de la malchance)" if r["hasard"] < 0.05 else
                   "l'écart peut encore venir de la **malchance** : il faut plus de parties "
                   "pour conclure")
        st.markdown(
            f"« Attendu » = ce qu'on observerait en moyenne si les probabilités du modèle "
            f"étaient justes pour ce joueur. « Écart aussi grand par hasard » : on rejoue "
            f"20 000 fois ces {int(r['parties'])} parties en tirant chaque résultat avec la "
            f"probabilité du modèle, et on compte la part des tirages où la log loss est au "
            f"moins aussi mauvaise. À 15 min : {pct(r['hasard'])}, donc {verdict}. "
            "Remontées = victoires alors que le modèle donnait moins de 50 % ; avances "
            "perdues = défaites alors qu'il donnait plus de 50 %.")
match_id = st.selectbox("Partie", list(games), format_func=label)
game = games[match_id]
s, table, events = game["summary"], game["table"], game["events"]
sign = 1 if s["team"] == 100 else -1      # le modèle parle du bleu : on retourne pour le rouge

if s["patch"] not in model["patches"]:
    st.warning(f"Patch {s['patch']} : le modèle a appris sur les patchs "
               f"{model['patches'][0]} à {model['patches'][-1]}. Les probabilités restent "
               "indicatives (champions, objets et objectifs changent d'un patch à l'autre).")

# ---------------------------------------------------------------------------
# 4. La courbe et les moments clés
# ---------------------------------------------------------------------------
p_blue = predict(model, table)
curve = pd.DataFrame({TIME: table[TIME], "p": p_blue if sign == 1 else 1 - p_blue})
moments = key_moments(model, table, sign, n=5)

events = events.assign(side=events["team"].map(
    lambda t: "ton équipe" if t == s["team"] else "adversaire"))


def events_text(minute, limit=4):
    rows = events[events[TIME] == minute]
    texts = [f"{r.text} ({r.side})" for r in rows.itertuples()]
    return " ; ".join(texts[:limit]) + (f" ; +{len(texts) - limit}" if len(texts) > limit else "")


col = st.columns(4)
col[0].metric("Résultat", "Victoire" if s["win"] else "Défaite")
col[1].metric("Champion", f"{s['champion']} ({'bleu' if sign == 1 else 'rouge'})")
col[2].metric("K/D/A", s["kda"])
at15 = curve.loc[curve[TIME] == 15, "p"]
col[3].metric("Probabilité à 15 min", pct(at15.iloc[0]) if len(at15) else "—")

curve["events"] = curve[TIME].map(events_text)
curve["moment"] = curve[TIME].isin(moments[TIME])
base = alt.Chart(curve).encode(
    x=alt.X(f"{TIME}:Q", title="minute"),
    y=alt.Y("p:Q", title="probabilité de victoire de ton équipe",
            scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")))
tooltip = [alt.Tooltip(f"{TIME}:Q", title="minute"),
           alt.Tooltip("p:Q", title="probabilité", format=".0%"),
           alt.Tooltip("events:N", title="events de la minute")]
chart = (alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(strokeDash=[4, 4], color="gray")
         .encode(y="y:Q")
         + base.mark_line(point=True).encode(tooltip=tooltip)
         + base.transform_filter("datum.moment").mark_point(size=180, filled=True,
                                                            color="orange")
         .encode(tooltip=tooltip))
st.altair_chart(chart.properties(height=360), width="stretch")
st.caption("Chaque point = l'état de la partie à cette minute. Points orange = moments clés. "
           "La dernière minute (l'instant de la fin) n'est pas montrée, comme à l'entraînement.")

st.subheader("Moments clés")
if moments.empty:
    st.write("Partie trop courte.")
else:
    shown = pd.DataFrame({
        "minute": moments[TIME],
        "avant → après": [f"{pct(a)} → {pct(b)}" for a, b in zip(moments["avant"],
                                                                 moments["après"])],
        "variation": [f"{100 * v:+.0f} pts" for v in moments["variation"]],
        "dont events": [f"{100 * v:+.0f} pts" for v in moments["part des events"]],
        "ce qui s'est passé": [events_text(m) or "—" for m in moments[TIME]],
        "variables qui ont bougé (log-odds)": moments["variables"]})
    st.dataframe(shown, hide_index=True, width="stretch")
    st.caption("Variation entre la minute précédente et celle-ci. « dont events » = la part "
               "due à ce qui s'est passé dans la partie ; le reste vient du temps qui passe "
               "(le même avantage ne pèse pas autant à 10 et à 30 min).")

# ---------------------------------------------------------------------------
# 5. Expliquer une minute
# ---------------------------------------------------------------------------
st.subheader("Pourquoi cette probabilité ?")
minutes = table[TIME].tolist()
default = int(moments[TIME].iloc[0]) if not moments.empty else minutes[-1]
minute = st.select_slider("Minute", options=minutes, value=default)
explained, p_avg, p_final = explain_minute(model, table, minute, sign)
st.write(f"À la minute {minute}, une partie **moyenne** donne {pct(p_avg)} à ton équipe. "
         f"Avec l'état réel de la partie : **{pct(p_final)}**. Chaque barre montre combien "
         "une variable pousse vers ton équipe (à droite) ou vers l'adversaire (à gauche).")
bars = explained.assign(sens=explained["contribution"].map(
    lambda c: "pour ton équipe" if c >= 0 else "pour l'adversaire"))
st.altair_chart(
    alt.Chart(bars).mark_bar().encode(
        x=alt.X("contribution:Q", title="contribution (log-odds)"),
        y=alt.Y("variable:N", sort=None, title=None,
                axis=alt.Axis(labelLimit=300, labelOverlap=False)),
        color=alt.Color("sens:N", scale=alt.Scale(domain=["pour ton équipe", "pour l'adversaire"],
                                                  range=["#2e7d32", "#c62828"]),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["variable", alt.Tooltip("valeur:Q", format="+.1f"),
                 alt.Tooltip("contribution:Q", format="+.2f"),
                 alt.Tooltip("probabilité après:Q", format=".0%")])
    .properties(height=45 * len(bars)), width="stretch")
st.caption("Valeur = écart ton équipe − adversaire à cette minute (or et XP en milliers). "
           "Log-odds : l'échelle de la régression logistique avant la courbe en S ; "
           "+0,4 fait passer d'environ 50 % à 60 %.")
minute_events = events[events[TIME] == minute]
if len(minute_events):
    st.write("Pendant la minute qui précède : " + " ; ".join(
        f"{r.time} {r.text} ({r.side})" for r in minute_events.itertuples()))

with st.expander("Tableau de fin de partie"):
    st.dataframe(game["scoreboard"], hide_index=True, width="stretch")
    st.caption("Les autres joueurs sont désignés par leur champion (pseudonymisation).")
with st.expander("Comment lire cette page ?"):
    st.markdown(
        f"""
- **Le modèle** : à chaque minute, une régression logistique différente (minute 1, 2, …,
  {model['last']} et plus), apprise sur l'écart entre les deux équipes en or, XP, sbires,
  kills, tours, plaques, dragons, larves, hérauts, barons, inhibiteurs, premiers objectifs
  et kills de la dernière minute. Aucune information sur la fin de la partie n'est utilisée.
- **La probabilité** : à 15 min, le modèle a été vérifié bien calibré (quand il annonce
  70 %, l'équipe gagne environ 70 % du temps sur les parties de test).
- **Les variables** sont calculées à partir de la timeline Riot avec exactement le même code
  que pour l'entraînement (contrôle : écart 0 sur des parties réelles).
- **Limites** : pas de positions, de vision, d'objets ni de compositions d'équipe ; un
  retournement de situation reste possible même à 90 %.
- Parties téléchargées gardées dans `{CACHE.relative_to(CACHE.parent.parent)}`.
""")
