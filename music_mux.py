"""Music mux: the track always starts from its halfway point.

Rationale: intros build slowly; the second half is where the energy is.
Tail must cover the video; the picker in drive_fetch guarantees that,
and -stream_loop covers any rounding edge. A short fade-out avoids a
hard cut at the end of the reel.
"""
import shutil
import subprocess


def probe_duration(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found on PATH")
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def mux_from_halfway(silent_mp4, mp3_path, out_path, video_seconds):
    """Start the MP3 at duration/2, lay under video, AAC out."""
    duration = probe_duration(mp3_path)
    start = duration / 2
    tail = duration - start
    if tail < video_seconds:
        raise RuntimeError(f"music tail {tail:.1f}s shorter than video {video_seconds}s")

    cmd = ["ffmpeg", "-y", "-i", silent_mp4]
    if tail >= video_seconds + 1:
        cmd += ["-ss", f"{start:.2f}", "-i", mp3_path]
    else:  # loop the tail so it always covers the reel
        cmd += ["-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", mp3_path]
    cmd += [
        "-t", f"{video_seconds:.2f}",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-af", f"afade=t=out:st={video_seconds - 1:.2f}:d=1",
        "-movflags", "+faststart",
        "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    print(f"MUX: music starts at {start:.1f}s of {duration:.1f}s")
    return out_path
