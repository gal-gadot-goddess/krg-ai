"""Render an HTML reel to PNG frames using its own deterministic clock.

Every reel exposes window.renderAt(t) and window.DURATION, so each frame
is rendered exactly once at t = i / FPS. No screen recording needed.
"""
import base64
import os

import config


def render_frames(html_path, work_subdir):
    """Returns (frames_dir, duration, fps, frame_count)."""
    from playwright.sync_api import sync_playwright

    frames_dir = os.path.join(config.FRAMES_DIR, work_subdir)
    os.makedirs(frames_dir, exist_ok=True)
    url = "file:///" + html_path.replace("\\", "/") + "?render=1"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": config.WIDTH, "height": config.HEIGHT})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="load")
        page.wait_for_function("() => window.__ready === true")
        duration = float(page.evaluate("() => window.DURATION"))
        total = int(round(duration * config.FPS))
        for i in range(total):
            data_url = page.evaluate(f"() => window.renderAt({i / config.FPS})")
            raw = base64.b64decode(data_url.split(",", 1)[1])
            with open(os.path.join(frames_dir, f"f_{i:04d}.png"), "wb") as fh:
                fh.write(raw)
            if i % 60 == 0 or i == total - 1:
                print(f"RENDER: frame {i + 1}/{total}")
        browser.close()
        if errors:
            raise RuntimeError(f"page errors: {errors[0]}")
    return frames_dir, duration, config.FPS, total


def frames_to_silent_mp4(frames_dir, fps, out_path):
    """Lossless-ish intermediate; audio is muxed later."""
    import subprocess

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(frames_dir, "f_%04d.png"),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", config.CRF,
            "-pix_fmt", "yuv420p",
            "-an",
            out_path,
        ],
        check=True,
    )
    return out_path
