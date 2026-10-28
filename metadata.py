"""Metadata: SEO titles, descriptions, hashtags for game reels.

Reads the game name from the HTML file itself when possible:
  1. <title> tag inside the HTML
  2. <meta name="description"> / og:title hints
  3. First <h1> on the page
  4. window.* hints (window.TITLE, window.GAME_TITLE, ...)
  5. Fallback: prettified file name (01-neon-runner.html -> Neon Runner)

Then guesses the game kind (runner, platformer, puzzle, ...) from the
file name + HTML text. Gaming-first language throughout: no tech-stack
words, written for search and clicks. Output is identical on every platform.
"""
import os
import re

import config


def _brand_tag():
    return "#" + re.sub(r"[^a-z0-9]", "", config.BRAND.lower())


HASHTAGS = ["#browsergames", "#indiegame", "#gameplay",
            "#gaming", "#reels"]

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
    title = f"{name} - The Browser Game You Can't Stop Playing | {config.BRAND}"
    title = title[:100]
    description = (
        f"{name} ({genre}) is the most addictive browser game you have seen today.\n"
        f"Stop scrolling and watch the full gameplay, steal the high-score tricks, "
        f"and come back tomorrow - a brand-new game drops every single day.\n\n"
        f"New game daily. Follow {config.BRAND} so you never miss a drop."
    )
    tags = [
        name.lower(),
        genre.lower(),
        "browser games",
        "indie game",
        "gameplay",
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
