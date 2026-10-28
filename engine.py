"""kreggsAi publisher engine. Runs forever on a schedule.

One cycle: fetch new HTML + pick music -> render frames -> silent MP4 ->
music from halfway -> metadata -> publish (YT/IG/FB, each optional) ->
record in history.json so nothing ever posts twice.

Usage: python engine.py [--once] [--limit N] [--dry-run]
  --once     process at most --limit new designs, then exit (CI mode)
  --dry-run  render + mux locally, publish nothing, write no history
"""
import argparse
import json
import os
import sys

import config
import drive_fetch
import metadata
import music_mux
import publish_meta
import publish_youtube
import render_reel


def load_history():
    if os.path.exists(config.HISTORY_PATH):
        with open(config.HISTORY_PATH) as fh:
            return json.load(fh)
    return {"posted": {}, "music_uses": {}}


def save_history(history):
    with open(config.HISTORY_PATH, "w") as fh:
        json.dump(history, fh, indent=2, sort_keys=True)


def process_one(name, html_path, history, dry_run=False):
    slug = os.path.splitext(name)[0]
    print(f"ENGINE: {name}")
    if render_reel.has_contract(html_path):
        frames_dir, duration, fps, total = render_reel.render_frames(html_path, slug)
        silent = os.path.join(config.OUTPUT_DIR, f"{slug}-silent.mp4")
        render_reel.frames_to_silent_mp4(frames_dir, fps, silent)
    else:
        silent, duration, fps = render_reel.render_realtime(html_path, slug)

    import drive_fetch as df

    svc = df._service()
    music_name, mp3_path = df.fetch_music(svc, history, duration)
    final = os.path.join(config.OUTPUT_DIR, f"{slug}-reel.mp4")
    music_mux.mux_from_halfway(silent, mp3_path, final, duration)

    meta = metadata.build(name, music_name, html_path)
    print(f"ENGINE: {meta['title']}")

    published = {}
    if not dry_run:
        published["youtube"] = publish_youtube.publish(final, meta)
        cap = meta["title"] + "\n" + meta["description"] + "\n" + meta["hashtags"]
        public_url = os.environ.get("PUBLIC_VIDEO_URL", "")
        if public_url:
            published["instagram"] = publish_meta.publish_instagram_reel(public_url, cap)
        else:
            # resumable byte upload: local file straight to IG, no URL needed
            published["instagram"] = publish_meta.publish_instagram_reel_file(final, cap)
        published["facebook"] = publish_meta.publish_facebook_video(final, meta)
        import datetime as _dt
        history["posted"][name] = {"video": final, "music": music_name,
                                   "timestamp": _dt.datetime.now(
                                       _dt.timezone.utc).isoformat(),
                                   **published}
        history["music_uses"][music_name] = history.get("music_uses", {}).get(music_name, 0) + 1
        save_history(history)
    else:
        print(f"ENGINE: dry-run, final video at {final}")
    try:
        os.remove(silent)
    except OSError:
        pass
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    missing = [n for n, v in (("DRIVE_HTML_FOLDER_ID", config.DRIVE_HTML_FOLDER_ID),
                              ("DRIVE_MUSIC_FOLDER_ID", config.DRIVE_MUSIC_FOLDER_ID)) if not v]
    if missing:
        print(f"ENGINE: missing required config (set as secrets/env): {', '.join(missing)}")
        return 2
    history = load_history()
    svc = drive_fetch._service()
    new_designs = drive_fetch.fetch_new_html(svc, history)
    if not new_designs and history.get("posted"):
        # recirculation: everything posted at least once, re-run the
        # least-recently posted design so the channel never goes silent
        posted = history["posted"]
        oldest = sorted(posted, key=lambda n: (posted[n].get("timestamp", ""), n))[0]
        dest = os.path.join(config.HTML_DIR, oldest)
        if os.path.exists(dest):
            os.remove(dest)
        for f in drive_fetch.list_children(svc, config.DRIVE_HTML_FOLDER_ID):
            if f["name"] == oldest:
                drive_fetch.download(svc, f["id"], dest)
                new_designs = [(oldest, dest)]
                print(f"ENGINE: recirculating {oldest}")
                break
    if not new_designs:
        print("ENGINE: nothing new to publish")
        return 0
    for name, path in new_designs[: args.limit]:
        process_one(name, path, history, dry_run=args.dry_run)
        if args.once:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
