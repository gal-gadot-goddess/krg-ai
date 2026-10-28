"""Meta publishing: Instagram Reels + Facebook Page video (Graph API).

Needs META_ACCESS_TOKEN plus META_IG_USER_ID (reels) and/or
META_FB_PAGE_ID (page videos). Each channel is independent: a missing
ID skips that channel only. Media must be publicly reachable by URL;
pass --public-base-url in CI (e.g. a release asset or CDN link).
"""
import os
import time

import requests

import config

_API = "https://graph.facebook.com/v21.0"


def can_publish_ig():
    return bool(config.META_ACCESS_TOKEN and config.META_IG_USER_ID)


def can_publish_fb():
    return bool(config.META_ACCESS_TOKEN and config.META_FB_PAGE_ID)


def publish_instagram_reel(public_video_url, caption):
    if not can_publish_ig():
        print("INSTAGRAM: credentials missing, skipped")
        return None
    uid, tok = config.META_IG_USER_ID, config.META_ACCESS_TOKEN
    c = requests.post(
        f"{_API}/{uid}/media",
        data={"media_type": "REELS", "video_url": public_video_url,
              "caption": caption, "access_token": tok},
        timeout=60,
    ).json()
    cid = c.get("id")
    if not cid:
        print(f"INSTAGRAM: container failed: {c}")
        return None
    for _ in range(30):
        st = requests.get(f"{_API}/{cid}",
                          params={"fields": "status_code", "access_token": tok},
                          timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        time.sleep(10)
    p = requests.post(f"{_API}/{uid}/media_publish",
                      data={"creation_id": cid, "access_token": tok},
                      timeout=60).json()
    mid = p.get("id")
    print(f"INSTAGRAM: published reel {mid}" if mid else f"INSTAGRAM: publish failed: {p}")
    return mid


def publish_instagram_reel_file(mp4_path, caption, thumb_offset_ms=None):
    """Instagram Reel from a LOCAL mp4: resumable upload, no public URL needed.

    Same method as dev-gn: init resumable container -> stream bytes to the
    returned rupload URI -> wait FINISHED -> media_publish.
    """
    import subprocess

    if not can_publish_ig():
        print("INSTAGRAM: credentials missing, skipped")
        return None
    uid, tok = config.META_IG_USER_ID, config.META_ACCESS_TOKEN
    size = os.path.getsize(mp4_path)
    if thumb_offset_ms is None:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", mp4_path],
                capture_output=True, text=True, check=True,
            )
            dur = float(r.stdout.strip())
            thumb_offset_ms = int(max(1.0, dur - 1.2) * 1000)
        except Exception:
            thumb_offset_ms = 1000

    init = requests.post(
        f"{_API}/{uid}/media",
        data={"upload_type": "resumable", "media_type": "REELS",
              "caption": caption[:2200], "share_to_feed": "false",
              "thumb_offset": str(thumb_offset_ms),
              "access_token": tok},
        timeout=60,
    )
    if init.status_code != 200:
        print(f"INSTAGRAM: resumable init failed: {init.text[:200]}")
        return None
    body = init.json()
    cid, uri = body.get("id"), body.get("uri")
    if not cid or not uri:
        print(f"INSTAGRAM: bad init response: {str(body)[:200]}")
        return None
    print(f"INSTAGRAM: container {cid}, streaming {size} bytes")

    with open(mp4_path, "rb") as fh:
        up = requests.post(
            uri,
            headers={"Authorization": f"OAuth {tok}", "offset": "0",
                     "file_size": str(size),
                     "Content-Type": "application/octet-stream"},
            data=fh,
            timeout=300,
        )
    if up.status_code not in (200, 201, 204):
        try:
            ok = up.json().get("success", False)
        except Exception:
            ok = False
        if not ok:
            print(f"INSTAGRAM: byte upload failed: {up.text[:200]}")
            return None
    print("INSTAGRAM: bytes streamed, waiting for processing")
    for _ in range(18):
        time.sleep(10)
        try:
            st = requests.get(f"{_API}/{cid}",
                              params={"fields": "status_code",
                                      "access_token": tok},
                              timeout=30).json()
        except Exception as e:
            print(f"INSTAGRAM: status query notice: {e}")
            continue
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            print(f"INSTAGRAM: container error: {st}")
            return None
    else:
        print("INSTAGRAM: processing not finished in time, giving up")
        return None
    p = requests.post(f"{_API}/{uid}/media_publish",
                      data={"creation_id": cid, "access_token": tok},
                      timeout=60).json()
    mid = p.get("id")
    print(f"INSTAGRAM: published reel {mid}" if mid else f"INSTAGRAM: publish failed: {p}")
    return mid


def publish_facebook_video(mp4_path, meta):
    if not can_publish_fb():
        print("FACEBOOK: credentials missing, skipped")
        return None
    with open(mp4_path, "rb") as fh:
        r = requests.post(
            f"{_API}/{config.META_FB_PAGE_ID}/videos",
            data={"description": meta["description"] + "\n" + meta["hashtags"],
                  "access_token": config.META_ACCESS_TOKEN},
            files={"source": fh},
            timeout=300,
        ).json()
    vid = r.get("id")
    print(f"FACEBOOK: published video {vid}" if vid else f"FACEBOOK: failed: {r}")
    return vid
