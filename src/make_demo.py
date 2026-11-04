"""Fabrique docs/demo.gif : un navigateur piloté par un script joue la démo de l'appli.

Lancement (l'appli doit déjà tourner : docker compose up -d, ou streamlit run src/app.py) :
    python src/make_demo.py --riot-id "Pseudo#TAG"
Il faut Playwright (outil de documentation, pas une dépendance de l'appli) :
    pip install playwright==1.63.0
    python -m playwright install chromium

Pourquoi un script plutôt qu'un enregistreur d'écran : la démo est rejouable à
l'identique quand l'appli change (même scénario, même taille, mêmes pauses), rien
d'autre que la page n'est filmé (ni barre des tâches, ni notifications), et la
taille du GIF est maîtrisée.

Le principe : on ne filme pas une vidéo, on prend une capture de la page après chaque
action (une lettre tapée, un cran de défilement, un cran du curseur) et on garde la
durée d'affichage de chaque capture. Les captures sont ensuite assemblées en GIF avec
Pillow (déjà installé avec matplotlib). Deux captures identiques à la suite n'en font
qu'une, affichée plus longtemps : c'est ce qui garde le fichier léger.

Le scénario (fonction play) :
1. taper le Riot ID et cliquer sur « Chercher » ;
2. attendre le téléchargement des parties (la barre de progression est filmée) ;
3. survoler la courbe de gauche à droite (l'infobulle donne la probabilité et les events) ;
4. descendre jusqu'aux moments clés ;
5. bouger le curseur « Minute » et regarder les barres d'explication changer.
"""

import argparse
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import TimeoutError as PlaywrightTimeout, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIEWPORT = {"width": 1280, "height": 800}   # taille de la fenêtre filmée (pixels)

# Cache ce qui n'est pas l'appli : menu et indicateur « Running » de Streamlit.
HIDE_CHROME = """
[data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"],
[data-testid="stHeader"], [data-testid="stElementToolbar"] { visibility: hidden !important; }
"""


# ---------------------------------------------------------------------------
# 1. Les captures
# ---------------------------------------------------------------------------
class Recorder:
    """Garde la liste des captures [image, durée en ms]."""

    def __init__(self, page, width):
        self.page, self.width, self.frames = page, width, []
        self._last = None

    def snap(self, ms):
        """Capture la page et l'affiche `ms` millisecondes dans le GIF."""
        png = self.page.screenshot()
        if png == self._last:              # rien n'a changé : on allonge la capture précédente
            self.frames[-1][1] += ms
            return
        self._last = png
        img = Image.open(io.BytesIO(png)).convert("RGB")
        height = round(img.height * self.width / img.width)
        self.frames.append([img.resize((self.width, height), Image.LANCZOS), ms])

    def hold(self, ms):
        """Pause sur l'écran actuel (aucune nouvelle capture)."""
        self.frames[-1][1] += ms

    def save(self, path, colors):
        """Assemble les captures en GIF qui tourne en boucle."""
        # Une seule palette pour tout le GIF, apprise sur une mosaïque de captures prises
        # tout au long de la démo : sans elle, chaque image choisit ses couleurs, le fond
        # « clignote » et une couleur rare (les barres vertes, les points orange) peut
        # disparaître.
        sample = [f[0] for f in self.frames[:: max(1, len(self.frames) // 12)]]
        mosaic = Image.new("RGB", (self.width * len(sample), max(im.height for im in sample)))
        for i, im in enumerate(sample):
            mosaic.paste(im, (i * self.width, 0))
        palette = mosaic.quantize(colors, method=Image.Quantize.FASTOCTREE)
        images = [f[0].quantize(palette=palette, dither=Image.Dither.NONE) for f in self.frames]
        path.parent.mkdir(parents=True, exist_ok=True)
        images[0].save(path, save_all=True, append_images=images[1:], loop=0,
                       duration=[f[1] for f in self.frames], optimize=True, disposal=1)


# ---------------------------------------------------------------------------
# 2. Petites actions sur la page
# ---------------------------------------------------------------------------
def check_no_error(page):
    """Arrête tout si l'appli affiche une erreur Python (inutile de filmer une erreur)."""
    error = page.locator('[data-testid="stException"]')
    if error.count():
        raise RuntimeError("L'appli affiche une erreur :\n" + error.first.inner_text()[:500])


RUNNING = '[data-testid="stStatusWidgetRunningIcon"]'   # icône « Running... » de Streamlit


def wait_for_app(page, timeout_s=60):
    """Attend que Streamlit ait fini de recalculer la page après une action.

    Streamlit ne relance pas le script tout de suite (environ 0,5 s après un cran de
    curseur) : on attend d'abord que l'icône « Running » APPARAISSE, puis qu'elle
    disparaisse. Sans la première attente, on photographierait l'ancienne page.
    """
    try:
        page.wait_for_selector(RUNNING, state="attached", timeout=1500)
    except PlaywrightTimeout:               # action qui ne relance rien, ou déjà fini
        pass
    page.wait_for_selector(RUNNING, state="detached", timeout=timeout_s * 1000)
    check_no_error(page)
    page.wait_for_timeout(500)             # le temps que les graphiques se dessinent


def scroll_to(page, rec, text, steps=8, ms=60):
    """Descend en douceur jusqu'au titre `text` (plusieurs crans de molette filmés)."""
    target = page.get_by_text(text, exact=True).first
    page.mouse.move(VIEWPORT["width"] * 0.65, VIEWPORT["height"] * 0.5)
    distance = target.bounding_box()["y"] - 80
    for _ in range(steps):
        page.mouse.wheel(0, distance / steps)
        page.wait_for_timeout(ms)
        rec.snap(ms)


# ---------------------------------------------------------------------------
# 3. Le scénario
# ---------------------------------------------------------------------------
def play(page, rec, url, riot_id, count, game):
    page.goto(url)
    page.add_style_tag(content=HIDE_CHROME)
    page.wait_for_selector('[data-testid="stSidebar"], [data-testid="stException"]', timeout=60_000)
    check_no_error(page)
    page.get_by_label("Riot ID").wait_for(timeout=30_000)
    wait_for_app(page)
    rec.snap(1200)

    # 1. Taper le Riot ID lettre par lettre, régler le nombre de parties, chercher.
    box = page.get_by_label("Riot ID")
    box.click()
    for ch in riot_id:
        box.press_sequentially(ch)
        rec.snap(70)
    if count != 20:
        page.get_by_role("slider", name="Nombre de parties").focus()
    for _ in range(abs(count - 20)):        # 20 = valeur de départ du curseur dans app.py
        page.keyboard.press("ArrowRight" if count > 20 else "ArrowLeft")
    rec.snap(500)
    page.get_by_role("button", name="Chercher").click()

    # 2. Le téléchargement des parties (barre de progression), jusqu'à la courbe.
    for _ in range(600):
        if page.get_by_text("Moments clés", exact=True).count():
            break
        rec.snap(150)
        page.wait_for_timeout(150)
    wait_for_app(page)
    if game:                                # une autre partie que la plus récente
        page.locator('[data-testid="stSelectbox"]').click()
        page.locator('[role="option"]').nth(game).click()
        wait_for_app(page)
    rec.snap(2500)

    # 3. Survoler la courbe de gauche à droite : l'infobulle suit la souris.
    chart = page.locator('[data-testid="stVegaLiteChart"]').first.bounding_box()
    y = chart["y"] + chart["height"] * 0.45
    for i in range(1, 15):
        x = chart["x"] + chart["width"] * (0.08 + 0.85 * i / 14)
        # Une infobulle Vega n'apparaît que près d'un point : on longe la courbe en
        # cherchant le point le plus proche de cette verticale.
        page.mouse.move(x, y)
        point = page.evaluate(
            """([x]) => { let best = null;
                 for (const p of document.querySelectorAll('[data-testid="stVegaLiteChart"] path.mark-symbol path, [data-testid="stVegaLiteChart"] .mark-symbol path')) {
                   const r = p.getBoundingClientRect(); const d = Math.abs(r.x + r.width / 2 - x);
                   if (r.width && (!best || d < best.d)) best = {d, x: r.x + r.width / 2, y: r.y + r.height / 2}; }
                 return best; }""", [x])
        if point:
            page.mouse.move(point["x"], point["y"])
        page.wait_for_timeout(120)
        rec.snap(350)
    page.mouse.move(5, VIEWPORT["height"] - 5)   # l'infobulle disparaît
    rec.snap(300)

    # 4. Les moments clés.
    scroll_to(page, rec, "Moments clés")
    rec.hold(3500)

    # 5. Le curseur « Minute » : les barres d'explication changent à chaque cran.
    scroll_to(page, rec, "Pourquoi cette probabilité ?")
    rec.hold(1500)
    minute = page.get_by_role("slider", name="Minute")
    for key in ["ArrowLeft"] * 4 + ["ArrowRight"] * 8:
        minute.focus()
        page.keyboard.press(key)
        wait_for_app(page)
        rec.snap(700)
    rec.hold(2500)


def main():
    parser = argparse.ArgumentParser(description="Fabrique le GIF de démo de l'appli.")
    parser.add_argument("--riot-id", required=True, help="Riot ID filmé, ex. TECHNIQUEMENT#99999")
    parser.add_argument("--url", default="http://localhost:8501", help="adresse de l'appli")
    parser.add_argument("--count", type=int, default=20, help="nombre de parties (5 à 50)")
    parser.add_argument("--game", type=int, default=0,
                        help="partie filmée : 0 = la plus récente, 1 = la suivante...")
    parser.add_argument("--width", type=int, default=960, help="largeur du GIF en pixels")
    parser.add_argument("--colors", type=int, default=256, help="couleurs du GIF (2 à 256)")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "demo.gif")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, locale="fr-FR", timezone_id="Europe/Paris")
        rec = Recorder(page, args.width)
        try:
            play(page, rec, args.url, args.riot_id, args.count, args.game)
        finally:
            browser.close()
    rec.save(args.out, args.colors)
    seconds = sum(f[1] for f in rec.frames) / 1000
    size = args.out.stat().st_size / 1e6
    print(f"{args.out} : {len(rec.frames)} images, {seconds:.0f} s, {size:.1f} Mo")
    if size > 8:
        print("Plus de 8 Mo : relancer avec --width 800 ou --colors 64.")


if __name__ == "__main__":
    main()
