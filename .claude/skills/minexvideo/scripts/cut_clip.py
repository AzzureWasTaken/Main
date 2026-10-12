#!/usr/bin/env python3
"""
Cut a segment out of a long VOD and turn it into a vertical 9:16 clip,
ready for the render pipeline.

    cut_clip.py <vod.mp4> <start> <end> <out.mp4> [options]

  <start>/<end>   seconds (83.5) or timestamps (01:23.5, 1:02:03)

Options:
  --mode crop|blur     crop (default): fill the frame with the center of the
                       gameplay — the standard look for Minecraft shorts.
                       blur: whole frame visible, blurred copy fills the
                       bars — use when the edges matter (HUD, chat, a build).
  --focus-x <0-100>    horizontal center of the crop, % of source width
                       (default 50). Use when the action is off-center:
                       35 looks left of center, 65 looks right.
  --keep-aspect        no vertical conversion, just cut.
  --width <px>         output width (default 1080 → 1080x1920).

Cutting RE-ENCODES on purpose: stream-copy cuts snap to keyframes, which on
a typical VOD means the clip starts up to several seconds off — unusable
when the punchline lives at second 3. Re-encoding costs a bit of CPU per
clip and is frame-exact.

Audio is kept as-is (re-encoded AAC). The output is a normal standalone
clip: you can render it, re-cut it, or throw it away without touching the
VOD.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Windows consoles default to a legacy codepage (cp1252) that cannot encode
# the dashes in this script's help text, nor an accented character in a file
# path. Without this the cut would succeed and the script would then die
# printing its own success message.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def parse_time(t: str) -> float:
    """'83.5' -> 83.5 · '01:23' -> 83 · '1:02:03.5' -> 3723.5"""
    t = t.strip()
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    parts = t.split(":")
    if not 2 <= len(parts) <= 3 or not all(p.strip() for p in parts):
        raise ValueError(f"cannot parse time: {t!r}")
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return sec


def probe_dims(video: Path) -> tuple[int, int, float]:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True, check=True,
    )
    w, h, dur = r.stdout.split()
    return int(w), int(h), float(dur)


def vertical_filter(w: int, h: int, mode: str, focus_x: float,
                    out_w: int) -> str:
    """Build the ffmpeg -vf chain that produces a 9:16 frame."""
    out_h = out_w * 16 // 9
    src_ratio = w / h
    if src_ratio <= 9 / 16 + 0.01:
        # Already vertical (or square-ish): just normalize the size.
        return f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase," \
               f"crop={out_w}:{out_h}"

    if mode == "blur":
        # Blurred, darkened copy of the frame fills the vertical canvas; the
        # full original sits centered on top.
        return (
            f"split[bg][fg];"
            f"[bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},gblur=sigma=30,eq=brightness=-0.15[bgb];"
            f"[fg]scale={out_w}:-2[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2"
        )

    # crop: take a 9:16 window out of the source, centered on focus_x.
    crop_w = int(h * 9 / 16)
    crop_w -= crop_w % 2
    center = w * focus_x / 100.0
    x = int(round(center - crop_w / 2))
    x = max(0, min(x, w - crop_w))
    return f"crop={crop_w}:{h}:{x}:0,scale={out_w}:{out_h}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vod")
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("out")
    ap.add_argument("--mode", choices=["crop", "blur"], default="crop")
    ap.add_argument("--focus-x", type=float, default=50.0)
    ap.add_argument("--keep-aspect", action="store_true")
    ap.add_argument("--width", type=int, default=1080)
    args = ap.parse_args()

    vod = Path(args.vod).resolve()
    if not vod.exists():
        print(f"[error] file not found: {vod}", file=sys.stderr)
        return 1

    start = parse_time(args.start)
    end = parse_time(args.end)
    if end <= start:
        print(f"[error] end ({end}s) must be after start ({start}s)",
              file=sys.stderr)
        return 1
    dur = end - start

    w, h, vod_dur = probe_dims(vod)
    if start >= vod_dur:
        print(f"[error] start {start:.1f}s is past the end of the VOD "
              f"({vod_dur:.1f}s)", file=sys.stderr)
        return 1
    if end > vod_dur:
        end = vod_dur
        dur = end - start
        print(f"[cut] end clamped to the end of the VOD ({end:.1f}s)")
    if dur > 90:
        print(f"[cut][warning] {dur:.0f}s is long for a short — the final "
              f"edit should stay under 60s (music licensing; see SKILL.md)")

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-ss", f"{start:.3f}", "-i", str(vod), "-t", f"{dur:.3f}"]
    if args.keep_aspect:
        cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]
    else:
        cmd += ["-vf", vertical_filter(w, h, args.mode, args.focus_x, args.width)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)

    shape = "kept as-is" if args.keep_aspect else \
        f"vertical 9:16 ({args.mode}, focus-x {args.focus_x:g}%)"
    print(f"[cut] {start:.1f}s to {end:.1f}s ({dur:.1f}s), {shape} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
