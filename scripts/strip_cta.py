#!/usr/bin/env python3
"""
Remove a burned-in call-to-action banner from a finished Short.

The banner the MineXVideo `tip_banner` template draws is a gold-bordered box.
This finds that box by its border colour, works out which frames it is on
screen for, paints it out with ffmpeg's delogo, and then re-scans the output
to prove it is gone.

Detection is deliberately conservative: it only trusts a candidate that looks
like a RECTANGLE (two long horizontal border runs joined by vertical ones),
which keeps it from locking onto orange gameplay — lava fills most of the
frame in some of these clips and is the obvious false positive.

    python3 strip_cta.py INPUT.mp4 [-o OUTPUT.mp4] [--detect-only]

Exits non-zero if the banner is still detectable in the output, so a batch
loop can stop rather than quietly shipping a video with the ad still in it.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

# The tip_banner border is a saturated gold. Generous bounds: the encode
# shifts it around and the edges are antialiased against whatever is behind.
def is_gold(r, g, b):
    return r > 170 and 100 < g < 215 and b < 110

MIN_RUN_FRAC = 0.35   # the border is one CONTIGUOUS run this wide
MAX_H_FRAC   = 0.22   # ...and the box it encloses is never tall
SEARCH_TOP   = 0.55   # only look in the lower part of the frame
MAX_FILL     = 0.25   # border rows are a small share of the box's height
MAX_EDGE_DEV = 20     # ...and they line up with each other, in pixels


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
               "-show_entries", "format=duration",
               "-of", "json", path]).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"w": int(s["width"]), "h": int(s["height"]),
            "fps": float(num) / float(den),
            "duration": float(d["format"]["duration"])}


def _longest_gold_run(px, w, y):
    """(length, start_x) of the longest CONTIGUOUS gold run on row y.

    Contiguity is what separates the banner from the gameplay. The border is
    a drawn line, so it runs unbroken for most of the frame width; lava is
    textured, so even a frame that is almost entirely orange only manages
    short runs before a darker pixel breaks it.
    """
    best = cur = best_start = start = 0
    for x in range(w):
        if is_gold(*px[x, y]):
            if cur == 0:
                start = x
            cur += 1
            if cur > best:
                best, best_start = cur, start
        else:
            cur = 0
    return best, best_start


def gold_bbox(img, w, h):
    """Bounding box of the banner, found via its border rows, or None.

    Three gates, each one rejecting a way gameplay can look like a banner:

    1. CONTIGUITY - the border is a drawn line, so it runs unbroken across
       most of the frame. Textured orange (lava) breaks into short runs.
    2. FILL - a banner is an outline: two thin border rows with a dark
       interior between them. A lava lake is solid, so every row inside its
       bounds is "hot". Few hot rows relative to the box height means an
       outline; all of them means a filled region.
    3. ALIGNMENT - the two borders belong to one rectangle, so they start
       and end at the same x. Lava drifts from row to row.
    """
    px = img.load()
    need = w * MIN_RUN_FRAC
    rows = []
    for y in range(int(h * SEARCH_TOP), h):
        run_len, run_x = _longest_gold_run(px, w, y)
        if run_len >= need:
            rows.append((y, run_x, run_x + run_len - 1))
    if len(rows) < 2:
        return None

    y0, y1 = rows[0][0], rows[-1][0]
    box_h = y1 - y0 + 1
    if box_h > h * MAX_H_FRAC:
        return None
    if len(rows) / box_h > MAX_FILL:          # filled, not an outline
        return None
    starts = [r[1] for r in rows]
    ends = [r[2] for r in rows]
    if (max(starts) - min(starts) > MAX_EDGE_DEV
            or max(ends) - min(ends) > MAX_EDGE_DEV):
        return None                            # edges do not line up
    return min(starts), y0, max(ends), y1


def detect(path, info, workdir):
    """Return (box, t_first, t_last) or (None, None, None)."""
    from PIL import Image
    frames = os.path.join(workdir, "scan")
    os.makedirs(frames, exist_ok=True)
    # 4 fps is plenty to find a banner that sits on screen for seconds
    run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=4",
         "-f", "image2", os.path.join(frames, "%05d.png"), "-y"])
    hits = []
    box = None
    for name in sorted(os.listdir(frames)):
        idx = int(os.path.splitext(name)[0]) - 1
        t = idx / 4.0
        b = gold_bbox(Image.open(os.path.join(frames, name)).convert("RGB"),
                      info["w"], info["h"])
        if b:
            hits.append(t)
            if box is None:
                box = list(b)
            else:  # union, so a box that animates in is fully covered
                box[0] = min(box[0], b[0]); box[1] = min(box[1], b[1])
                box[2] = max(box[2], b[2]); box[3] = max(box[3], b[3])
    if not hits:
        return None, None, None
    return tuple(box), min(hits), max(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--detect-only", action="store_true")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--pad", type=int, default=8)
    a = ap.parse_args()

    info = probe(a.input)
    work = tempfile.mkdtemp(prefix="strip_cta_")
    try:
        box, t0, t1 = detect(a.input, info, work)
        if not box:
            print(f"[{os.path.basename(a.input)}] no CTA banner found "
                  f"- nothing to do")
            return 0
        x0, y0, x1, y1 = box
        # widen by the scan step plus padding; clamp inside the frame
        p = a.pad + 2
        dx = max(1, x0 - p); dy = max(1, y0 - p)
        dw = min(info["w"] - dx - 1, (x1 - x0 + 1) + 2 * p)
        dh = min(info["h"] - dy - 1, (y1 - y0 + 1) + 2 * p)
        # the 4fps scan can miss the first/last quarter-second; pad the window
        e0 = max(0.0, t0 - 0.30)
        e1 = min(info["duration"], t1 + 0.30)
        print(f"[{os.path.basename(a.input)}] banner x{x0}-{x1} y{y0}-{y1} "
              f"on screen {t0:.2f}s-{t1:.2f}s of {info['duration']:.2f}s")
        if a.detect_only:
            return 0

        out = a.output or (os.path.splitext(a.input)[0] + "-noad.mp4")
        run(["ffmpeg", "-v", "error", "-i", a.input,
             "-vf", f"delogo=x={dx}:y={dy}:w={dw}:h={dh}:"
                    f"enable='between(t,{e0:.2f},{e1:.2f})'",
             "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow",
             "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", out, "-y"])

        # prove it: re-scan the render we just produced
        vbox, _, _ = detect(out, probe(out), work)
        if vbox:
            print(f"  FAILED - banner still detected at {vbox} in {out}")
            return 1
        print(f"  clean -> {out}")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
