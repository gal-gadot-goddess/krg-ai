"""kreggsAi engine configuration. Everything comes from the environment.

GitHub repo holds ONLY code. HTML designs and music come from Drive,
credentials come from secrets. No secrets are ever written to disk.
"""
import os

BRAND = "KREGGSAI"
TAGLINE = "A new game every day."

# Drive (IDs or env overrides; HTML folder is created by the owner later)
DRIVE_HTML_FOLDER_ID = os.environ.get("DRIVE_HTML_FOLDER_ID", "")
DRIVE_MUSIC_FOLDER_ID = os.environ.get("DRIVE_MUSIC_FOLDER_ID", "")

# Local work dirs (all git-ignored)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(BASE_DIR, ".work")
HTML_DIR = os.path.join(WORK_DIR, "html")
MUSIC_DIR = os.path.join(WORK_DIR, "music")
FRAMES_DIR = os.path.join(WORK_DIR, "frames")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")

# Render
WIDTH, HEIGHT, FPS = 1080, 1920, 30
CRF = "18"

# YouTube (OAuth refresh-token flow; all from secrets)
YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

# Meta (Graph API)
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_IG_USER_ID = os.environ.get("META_IG_USER_ID", "")
META_FB_PAGE_ID = os.environ.get("META_FB_PAGE_ID", "")
