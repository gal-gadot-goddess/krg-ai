"""Render an HTML reel to MP4.

Two paths, picked automatically:
- Deterministic: the reel exposes window.renderAt(t) + window.DURATION,
  so each frame is rendered exactly once at t = i / FPS (highest quality).
- Realtime: plain rAF animation with no contract (dev-gn style). The page
  is screen-recorded at wall-clock speed with GPU acceleration when present.
"""
import base64
import os
import re

import config

GPU_ARGS = ["--use-gl=angle", "--use-angle=default", "--enable-gpu",
            "--ignore-gpu-blocklist", "--enable-zero-copy"]


def detect_duration(html_path, default=15.0):
    """DURATION/DUR constant in source, else the default reel length."""
    try:
        with open(html_path, encoding="utf-8", errors="ignore") as fh:
            head = fh.read(40000)
    except OSError:
        return default
    m = re.search(r"(?:window\.)?(?:DURATION|DUR)\s*=\s*([0-9.]+)", head)
    if m:
        try:
            return max(5.0, float(m.group(1)))
        except ValueError:
            pass
    return default


def _launch(p, use_gpu=True):
    if use_gpu:
        try:
            return p.chromium.launch(headless=True, args=GPU_ARGS)
        except Exception as e:
            print(f"RENDER: GPU launch failed ({e}), falling back to software")
    return p.chromium.launch(headless=True)


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


def has_contract(html_path):
    """True when the reel exposes the deterministic renderAt/DURATION API."""
    try:
        with open(html_path, encoding="utf-8", errors="ignore") as fh:
            head = fh.read(40000)
    except OSError:
        return False
    return "renderAt" in head and "DURATION" in head


def render_realtime(html_path, work_subdir, duration=None, fps=None):
    """Screen-record a contract-less rAF reel at wall-clock speed.

    Returns (silent_mp4_path, duration, fps). GPU when available, software
    fallback otherwise (verified working, just slower to encode).
    """
    import glob

    from playwright.sync_api import sync_playwright

    fps = fps or config.FPS
    duration = duration or detect_duration(html_path)
    rec_dir = os.path.join(config.WORK_DIR, "rec", work_subdir)
    os.makedirs(rec_dir, exist_ok=True)
    for f in glob.glob(os.path.join(rec_dir, "*.webm")):
        os.remove(f)
    url = "file:///" + html_path.replace("\\", "/") + "?render=1"

    with sync_playwright() as p:
        browser = _launch(p)
        ctx = browser.new_context(
            viewport={"width": config.WIDTH, "height": config.HEIGHT},
            record_video_dir=rec_dir,
            record_video_size={"width": config.WIDTH, "height": config.HEIGHT},
        )
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="load")
        page.wait_for_timeout(int(duration * 1000))
        ctx.close()
        browser.close()
        if errors:
            print(f"RENDER: page warning: {errors[0][:200]}")

    vids = sorted(glob.glob(os.path.join(rec_dir, "*.webm")))
    if not vids:
        raise RuntimeError("screen recording produced no video")
    raw = vids[-1]
    print(f"RENDER: recorded {os.path.getsize(raw)} bytes in {duration:.0f}s")
    silent = os.path.join(config.OUTPUT_DIR, f"{work_subdir}-silent.mp4")
    import subprocess

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw,
         "-c:v", "libx264", "-preset", "medium", "-crf", config.CRF,
         "-pix_fmt", "yuv420p", "-an", silent],
        check=True,
    )
    for f in vids:
        try:
            os.remove(f)
        except OSError:
            pass
    return silent, duration, fps


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
