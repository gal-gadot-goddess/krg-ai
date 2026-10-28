"""Metadata: viral SEO titles, descriptions, hashtags (krg-ai voice: HYPE).

Reads the game name from the HTML file itself when possible:
  1. <title> tag inside the HTML
  2. <meta name="description"> / og:title hints
  3. First <h1> on the page
  4. window.* hints (window.TITLE, window.GAME_TITLE, ...)
  5. Fallback: prettified file name (01-neon-runner.html -> Neon Runner)

Genre is guessed from filename + HTML text; one or two real techniques
used by the game are detected from its code so every description teaches
something. Gaming-first language, written for search and clicks.
"""
import os
import re

import config


def _brand_tag():
    return "#" + re.sub(r"[^a-z0-9]", "", config.BRAND.lower())


HASHTAGS = ["#browsergames", "#gameplay", "#satisfying",
            "#indiegame", "#gaming", "#reels"]

# (keyword, label) pairs checked against filename + html text
GENRE_HINTS = [
    ("adventure", "Adventure"),
    ("runner", "Runner"),
    ("run", "Runner"),
    ("platformer", "Platformer"),
    ("platform", "Platformer"),
    ("puzzle", "Puzzle"),
    ("snake", "Snake"),
    ("breakout", "Breakout"),
    ("brick", "Breakout"),
    ("shooter", "Shooter"),
    ("shoot", "Shooter"),
    ("racer", "Racer"),
    ("racing", "Racer"),
    ("drift", "Racer"),
    ("hop", "Platformer"),
    ("jump", "Platformer"),
    ("tower", "Tower Defense"),
    ("defense", "Tower Defense"),
    ("maze", "Maze"),
    ("pong", "Pong"),
    ("tetris", "Tetris"),
    ("flappy", "Flappy"),
    ("asteroid", "Shooter"),
    ("space", "Space Shooter"),
    ("ninja", "Ninja Platformer"),
    ("survivor", "Survivor"),
    ("rogue", "Roguelike"),
    ("dungeon", "Dungeon Crawler"),
    ("card", "Card Game"),
    ("memory", "Memory Game"),
    ("match", "Match-3"),
    ("tunnel", "Tunnel"),
    ("vortex", "Vortex"),
    ("neon", "Neon Arcade"),
    ("retro", "Retro Arcade"),
]

# (keyword, human phrase) - real techniques detected in the game's code
TECHNIQUE_HINTS = [
    ("particle", "a particle system with hundreds of glowing sprites"),
    ("parallax", "layered parallax backgrounds for real depth"),
    ("gravity", "gravity and jump physics that just feel right"),
    ("grappl", "a grappling-hook swing mechanic"),
    ("hook", "a grappling-hook swing mechanic"),
    ("trail", "motion trails that follow every single move"),
    ("shadowblur", "neon glow rendered live on every frame"),
    ("procedural", "procedural generation, so no two runs ever match"),
    ("scroll", "a live code view that types itself out while you play"),
    ("highscore", "a score-chase loop built for one-more-try"),
    ("high score", "a score-chase loop built for one-more-try"),
    ("island", "floating-island level design with hidden paths"),
    ("tilemap", "tile-based levels packed with secrets"),
    ("boss", "a boss-style showdown waiting at the end"),
    ("combo", "a combo system that rewards risky play"),
]

HOOKS = [
    "Stop scrolling. This one is different.",
    "POV: you said 'just one run' an hour ago.",
    "Nobody expected a browser game to go this hard.",
    "This is your sign to take a five-minute game break.",
]


def prettify_stem(filename):
    """01-neon-runner.html -> Neon Runner."""
    stem = filename.lower().rsplit(".html", 1)[0]
    stem = re.sub(r"^[0-9]+[-_]+", "", stem)  # strip leading 01-, 02_ ...
    stem = re.sub(r"[-_]+", " ", stem).strip()
    stem = re.sub(r"\s+", " ", stem)
    return stem.title() if stem else filename


def _read_html(html_path):
    if not html_path or not os.path.exists(html_path):
        return ""
    try:
        with open(html_path, encoding="utf-8", errors="ignore") as fh:
            return fh.read(60000)  # head is enough: title/h1/meta live there
    except OSError:
        return ""


def extract_inner_title(html_text):
    """Best-effort game name from inside the HTML. Returns '' if none."""
    if not html_text:
        return ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    if m:
        t = re.sub(r"\s+", " ", m.group(1)).strip()
        t = re.sub(r"\s*[|\-_\u2013\u2014:]\s*(reel|short|shorts|video|gameplay)\s*$", "", t, flags=re.I)
        t = re.sub(r"\s*[|\-_\u2013\u2014:]\s*reel.*$", "", t, flags=re.I)
        if t:
            return t
    m = re.search(
        r'<meta[^>]+(?:property|name)=["\'](?:og:title|title)["\'][^>]+content=["\'](.*?)["\']',
        html_text, re.I | re.S,
    )
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.I | re.S)
    if m:
        t = re.sub(r"<[^>]+>", "", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        if t and len(t) <= 80:
            return t
    m = re.search(
        r"window\.(?:TITLE|GAME_TITLE|GAME_NAME|TITLE_TEXT)\s*=\s*['\"](.*?)['\"]",
        html_text,
    )
    if m and m.group(1).strip():
        return m.group(1).strip()
    return ""


def guess_genre(filename, html_text):
    hay = (filename + " " + (html_text[:20000] if html_text else "")).lower()
    for keyword, label in GENRE_HINTS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", hay):
            return label
    return "Arcade Game"


def detect_techniques(html_text, limit=2):
    """Human-readable techniques found in the game's code, in order."""
    hay = (html_text[:40000] if html_text else "").lower()
    found = []
    for keyword, phrase in TECHNIQUE_HINTS:
        if keyword in hay and phrase not in found:
            found.append(phrase)
        if len(found) >= limit:
            break
    if not found:
        found = ["tight game-feel tuned frame by frame"]
    return found


GENRE_WORDS = {kw for kw, _ in GENRE_HINTS} | {
    lbl.lower() for _, lbl in GENRE_HINTS
} | {"game"}


def game_name(filename, html_path=None):
    """Final display name: inner HTML title wins, filename is fallback."""
    inner = extract_inner_title(_read_html(html_path))
    if inner:
        inner = re.sub(r"\s+", " ", inner).strip()
        # drop a trailing " - Reel"-style suffix the reel templates add
        inner = re.sub(r"\s+reel\s*$", "", inner, flags=re.I).strip()
        # "Skyhook - Adventure" -> the game is Skyhook, Adventure is the genre
        m = re.match(r"^(.*?)\s+[|\-_\u2013\u2014:/]\s*(\w[\w ]*?)\s*$", inner)
        if m and m.group(2).strip().lower() in GENRE_WORDS:
            inner = m.group(1).strip()
        if inner:
            return inner[:70]
    return prettify_stem(filename)[:70]


def build(filename, music_name, html_path=None):
    html_text = _read_html(html_path)
    name = game_name(filename, html_path)
    genre = guess_genre(filename, html_text)
    techs = detect_techniques(html_text)
    hook = HOOKS[sum(bytearray(name.encode())) % len(HOOKS)]
    tech_line = techs[0] + (f" plus {techs[1]}" if len(techs) > 1 else "")
    title = f"{name} Gameplay Is Insanely Satisfying - Wait for It | {config.BRAND}"
    title = title[:100]
    description = (
        f"{hook}\n\n"
        f"{name} ({genre}) is the most addictive browser game on your feed today. "
        f"One run turns into ten - don't say I didn't warn you.\n\n"
        f"Here is the cool part: everything on screen is drawn live while the game runs, "
        f"including {tech_line}. Watch closely and you'll spot how it works.\n\n"
        f"A brand-new game drops here every single day. "
        f"Follow {config.BRAND} so tomorrow's drop finds you."
    )
    tags = [
        name.lower(),
        genre.lower(),
        "browser games",
        "satisfying gameplay",
        "indie game",
        config.BRAND.lower(),
    ]
    return {
        "title": title,
        "description": description,
        "tags": tags,
        "hashtags": " ".join(HASHTAGS + [_brand_tag()]),
        "game": name,
        "genre": genre,
    }
