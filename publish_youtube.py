"""YouTube upload (Data API v3, refresh-token flow).

Needs YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN.
Missing credentials -> skip with a clear message, never a crash.
"""
import config


def can_publish():
    return bool(config.YT_CLIENT_ID and config.YT_CLIENT_SECRET and config.YT_REFRESH_TOKEN)


def publish(mp4_path, meta):
    if not can_publish():
        print("YOUTUBE: credentials missing, skipped")
        return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None,
        refresh_token=config.YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.YT_CLIENT_ID,
        client_secret=config.YT_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"] + "\n" + meta["hashtags"],
            "tags": meta["tags"],
            "categoryId": "28",  # Science & Technology (coding)
        },
        "status": {"privacyStatus": "public", "madeForKids": False},
    }
    req = yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(mp4_path, mimetype="video/mp4", resumable=True),
    )
    resp = req.execute()
    vid = resp.get("id")
    print(f"YOUTUBE: uploaded https://youtu.be/{vid}")
    return vid
