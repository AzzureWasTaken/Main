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
    python3 strip_cta.py "C:/path/to/folder" --outdir cleaned

Given a folder it processes every video inside, writes the cleaned copies to
--outdir (default: a "no-ad" folder alongside), and prints a summary. Files
already done are skipped, so an interrupted run can simply be restarted.

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
SCAN_FPS     = 10     # detection sampling rate
EDGE_PAD     = 0.60   # seconds of slack each side of the detected window


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


def _border_present(px, w, box, tol=0.75):
    """Is the banner's gold outline drawn at this exact box, in this frame?

    Once the box is known, presence is a question about four specific lines
    of pixels, not about the frame as a whole. That matters because the
    shape gates in gold_bbox() reject a banner drawn over lava: the lava
    merges with the border and the result no longer looks like an outline.
    Testing the four border lines where they are known to be sidesteps that
    entirely - lava may be the same colour, but it is not gold along all
    four edges of one rectangle at once.
    """
    x0, y0, x1, y1 = box
    checks = []
    for y in (y0, y1):                       # top and bottom edges
        if 0 <= y < len(range(0, 1)) + y:    # guard below
            pass
        pts = [px[x, y] for x in range(x0, x1 + 1, 3)]
        checks.append(sum(1 for p in pts if is_gold(*p)) / max(1, len(pts)))
    for x in (x0, x1):                       # left and right edges
        pts = [px[x, y] for y in range(y0, y1 + 1)]
        checks.append(sum(1 for p in pts if is_gold(*p)) / max(1, len(pts)))
    return all(c >= tol for c in checks)


def detect(path, info, workdir):
    """Return (box, t_first, t_last) or (None, None, None).

    Two passes. The first finds WHERE the banner is, using the shape gates,
    which need a frame whose background does not confuse them. The second
    fixes that box and asks WHEN it is on screen by checking its border
    directly - catching the frames the first pass cannot judge.
    """
    from PIL import Image
    frames = os.path.join(workdir, "scan")
    os.makedirs(frames, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={SCAN_FPS}",
         "-f", "image2", os.path.join(frames, "%05d.png"), "-y"])
    names = sorted(os.listdir(frames))

    # pass 1 - where. The most frequently seen box wins, so one odd frame
    # cannot shift it.
    seen = {}
    for name in names:
        img = Image.open(os.path.join(frames, name)).convert("RGB")
        b = gold_bbox(img, info["w"], info["h"])
        if b:
            seen[b] = seen.get(b, 0) + 1
    if not seen:
        return None, None, None
    box = max(seen.items(), key=lambda kv: kv[1])[0]

    # pass 2 - when.
    hits = []
    for name in names:
        idx = int(os.path.splitext(name)[0]) - 1
        img = Image.open(os.path.join(frames, name)).convert("RGB")
        if _border_present(img.load(), info["w"], box):
            hits.append(idx / SCAN_FPS)
    if not hits:
        return None, None, None
    return box, min(hits), max(hits)


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def process(path, out, args):
    """Returns (status, detail). Status: cleaned | no-banner | failed."""
    info = probe(path)
    work = tempfile.mkdtemp(prefix="strip_cta_")
    try:
        box, t0, t1 = detect(path, info, work)
        name = os.path.basename(path)
        if not box:
            print(f"  {name}: no banner found")
            return "no-banner", ""
        x0, y0, x1, y1 = box
        p = args.pad + 2
        dx = max(1, x0 - p); dy = max(1, y0 - p)
        dw = min(info["w"] - dx - 1, (x1 - x0 + 1) + 2 * p)
        dh = min(info["h"] - dy - 1, (y1 - y0 + 1) + 2 * p)
        e0 = max(0.0, t0 - EDGE_PAD)
        e1 = min(info["duration"], t1 + EDGE_PAD)
        detail = f"x{x0}-{x1} y{y0}-{y1} @ {t0:.2f}-{t1:.2f}s"
        print(f"  {name}: banner {detail}")
        if args.detect_only:
            return "no-banner" if not box else "detected", detail

        run(["ffmpeg", "-v", "error", "-i", path,
             "-vf", f"delogo=x={dx}:y={dy}:w={dw}:h={dh}:"
                    f"enable='between(t,{e0:.2f},{e1:.2f})'",
             "-c:v", "libx264", "-crf", str(args.crf), "-preset", "slow",
             "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", out, "-y"])

        if detect(out, probe(out), work)[0]:
            print(f"    FAILED - banner still present in {out}")
            return "failed", detail
        print(f"    clean -> {out}")
        return "cleaned", detail
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="a video file, or a folder of them")
    ap.add_argument("-o", "--output", help="output file (single input only)")
    ap.add_argument("--outdir", help="output folder (folder input)")
    ap.add_argument("--detect-only", action="store_true")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--pad", type=int, default=8)
    a = ap.parse_args()

    if os.path.isfile(a.input):
        out = a.output or (os.path.splitext(a.input)[0] + "-noad.mp4")
        status, _ = process(a.input, out, a)
        return 1 if status == "failed" else 0

    if not os.path.isdir(a.input):
        print(f"not found: {a.input}", file=sys.stderr)
        return 2

    vids = sorted(f for f in os.listdir(a.input)
                  if os.path.splitext(f)[1].lower() in VIDEO_EXTS
                  and not f.endswith("-noad.mp4"))
    if not vids:
        print(f"no videos in {a.input}")
        return 0
    outdir = a.outdir or os.path.join(a.input, "no-ad")
    if not a.detect_only:
        os.makedirs(outdir, exist_ok=True)
    print(f"{len(vids)} video(s) in {a.input}")

    results = []
    for i, f in enumerate(vids, 1):
        src = os.path.join(a.input, f)
        out = os.path.join(outdir, os.path.splitext(f)[0] + "-noad.mp4")
        print(f"[{i}/{len(vids)}] {f}")
        if not a.detect_only and os.path.exists(out):
            print("  already done, skipping")
            results.append((f, "skipped", ""))
            continue
        try:
            status, detail = process(src, out, a)
        except subprocess.CalledProcessError as e:
            print(f"  ffmpeg failed: {e.stderr.strip().splitlines()[-1:]}")
            status, detail = "failed", "ffmpeg error"
        results.append((f, status, detail))

    print("\n==== summary ====")
    for f, status, detail in results:
        print(f"  {status:9s}  {f}  {detail}")
    bad = [r for r in results if r[1] == "failed"]
    none = [r for r in results if r[1] == "no-banner"]
    if none:
        print(f"\n{len(none)} file(s) had no banner found - check these by eye,"
              f" the banner may differ in colour or position.")
    if bad:
        print(f"\n{len(bad)} FAILED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
