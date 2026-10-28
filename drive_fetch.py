"""Drive access layer: HTML designs in, music in. Read-only.

Auth order: GOOGLE_APPLICATION_CREDENTIALS file first, then the raw JSON
in GOOGLE_SERVICE_ACCOUNT_KEY. Only file names/sizes are ever printed.
"""
import io
import json
import os

import config

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _credentials():
    from google.oauth2 import service_account

    fp = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if fp and os.path.exists(fp):
        return service_account.Credentials.from_service_account_file(fp, scopes=_SCOPES)
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON", ""
    )
    if raw:
        return service_account.Credentials.from_service_account_info(
            json.loads(raw), scopes=_SCOPES
        )
    raise RuntimeError("no service-account credential found in environment")


def _service():
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


def list_children(svc, folder_id, mime_contains=None):
    """All direct children of a folder (Shared-Drive aware)."""
    q = f"'{folder_id}' in parents and trashed = false"
    if mime_contains:
        q += f" and mimeType contains '{mime_contains}'"
    out, page, files = [], None, None
    while True:
        resp = (
            svc.files()
            .list(
                q=q,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                pageSize=200,
                pageToken=page,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        out.extend(resp.get("files", []))
        page = resp.get("nextPageToken")
        if not page:
            return out


def download(svc, file_id, dest_path):
    """Download one Drive file. Returns bytes written."""
    from googleapiclient.http import MediaIoBaseDownload

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path):
        return os.path.getsize(dest_path)
    req = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
    with open(dest_path, "wb") as fh:
        dl = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
    return os.path.getsize(dest_path)


def fetch_new_html(svc, history):
    """Download HTML designs not yet posted. Returns [(name, local_path)]."""
    if not config.DRIVE_HTML_FOLDER_ID:
        print("FETCH: DRIVE_HTML_FOLDER_ID not set, skipping HTML fetch")
        return []
    os.makedirs(config.HTML_DIR, exist_ok=True)
    posted = set(history.get("posted", {}))
    new = []
    for f in list_children(svc, config.DRIVE_HTML_FOLDER_ID):
        if not f["name"].lower().endswith(".html"):
            continue
        if f["name"] in posted:
            continue
        dest = os.path.join(config.HTML_DIR, f["name"])
        download(svc, f["id"], dest)
        print(f"FETCH: new design {f['name']}")
        new.append((f["name"], dest))
    return new


def fetch_music(svc, history, video_seconds):
    """Pick least-recently-used MP3 with a tail long enough for the video.

    Returns (name, local_path). The tail (second half) must cover the video.
    """
    os.makedirs(config.MUSIC_DIR, exist_ok=True)
    tracks = [
        f for f in list_children(svc, config.DRIVE_MUSIC_FOLDER_ID, "audio")
        if f["name"].lower().endswith(".mp3")
    ]
    if not tracks:
        raise RuntimeError("no MP3 tracks in music folder")
    uses = history.get("music_uses", {})
    tracks.sort(key=lambda f: (uses.get(f["name"], 0), f["name"]))
    for t in tracks:
        dest = os.path.join(config.MUSIC_DIR, t["name"])
        download(svc, t["id"], dest)
        from music_mux import probe_duration

        dur = probe_duration(dest)
        if dur / 2 >= video_seconds + 1:
            print(f"FETCH: music {t['name']} ({dur:.0f}s, tail fits)")
            return t["name"], dest
        print(f"FETCH: music {t['name']} too short, trying next")
    raise RuntimeError("no track with a long-enough second half")
