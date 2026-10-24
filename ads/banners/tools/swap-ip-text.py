"""Rebuild the final panel's IP text as ML.MINEX.GG.

    python3 -I swap-ip-text.py MCL_FRAMES BASE_FRAMES OUT_FRAMES

Frames are the 170 PNGs ffmpeg writes from minex-mcl-source.webm and minex-mss-source.webm
(`ffmpeg -i SOURCE.webm DIR/f%03d.png`).

The existing sets (mss, mcl, mcs) share one pixel font with fixed glyph cells. Every frame of the IP panel
is cut into per-glyph column slabs; the "C" slab of the MCL version is dropped, the remaining ten gaps are
widened evenly so the text keeps its original left and right edges, and the gaps are filled by blending the
neighbouring slab edges. Rows are untouched, so the panel's pop-in and shimmer still play.
"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

SRC_MCL = Path(sys.argv[1]); SRC_BASE = Path(sys.argv[2]); OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
# glyph runs (inclusive) measured on a clean frame: M C L . M I N E X . G G
R = [(299,342),(349,391),(398,440),(448,459),(472,514),(521,564),(571,613),(620,662),(669,712),(719,730),(743,786),(793,835)]
B = [296] + [(R[i-1][1] + R[i][0]) // 2 + 1 for i in range(1, 12)] + [840]
slabs = [(B[i], B[i+1]) for i in range(12)]
KEEP = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]            # M L . M I N E X . G G  (drop the C)
widths = [slabs[i][1] - slabs[i][0] for i in KEEP]
gap = (B[-1] - B[0] - sum(widths)) / (len(KEEP) - 1)
pos = []; x = float(B[0])
for w in widths:
    pos.append(round(x)); x += w + gap
print('slab widths', widths, 'gap', round(gap, 2), 'starts', pos)

def swap(frame):
    out = frame.copy()
    for k, i in enumerate(KEEP):
        s0, s1 = slabs[i]; d0 = pos[k]
        out[:, d0:d0 + (s1 - s0)] = frame[:, s0:s1]
        if k + 1 < len(KEEP):                          # fill the widened gap by blending the two edge columns
            a = d0 + (s1 - s0); b = pos[k + 1]
            if b > a:
                left = frame[:, s1 - 1].astype(np.float32); ns0 = slabs[KEEP[k + 1]][0]; right = frame[:, ns0].astype(np.float32)
                for c in range(a, b):
                    t = (c - a + 1) / (b - a + 1)
                    out[:, c] = np.round(left * (1 - t) + right * t).astype(np.uint8)
    return out

for t in range(1, 171):
    if t >= 133:
        f = np.asarray(Image.open(SRC_MCL / f'f{t:03d}.png').convert('RGB'))
        Image.fromarray(swap(f)).save(OUT / f'f{t:03d}.png')
    else:
        Image.open(SRC_BASE / f'f{t:03d}.png').convert('RGB').save(OUT / f'f{t:03d}.png')
print('done')
