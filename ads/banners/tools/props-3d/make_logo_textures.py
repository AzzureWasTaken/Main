#!/usr/bin/env python3
"""Pixel-art textures for the MineX logo, in Minecraft's own gold and diamond palettes, so the logo can be
rendered as 3D voxel items like the banner's other props.

    python3 -I make_logo_textures.py PTEX_DIR      # writes minex_coin.png (48x48) and minex_wordmark.png
"""
import sys, math
from pathlib import Path
import numpy as np
from PIL import Image

D = Path(sys.argv[1])
G = [(255, 253, 224), (253, 245, 95), (250, 214, 74), (233, 177, 21), (220, 150, 19), (178, 100, 17), (117, 40, 2)]  # gold_ingot.png
C = [(213, 255, 246), (161, 251, 232), (74, 237, 217), (32, 197, 181), (17, 114, 122)]                              # diamond.png

# --- coin: 48x48, outlined rim, bevelled face, "MineX" across it in chunky custom pixel letters
font = np.asarray(Image.open(D / 'ascii.png').convert('RGBA'))[..., 3] > 0
LETTERS = {
 'M': ["XX.....XX", "XXX...XXX", "XXXX.XXXX", "XX.XXX.XX", "XX..X..XX", "XX.....XX", "XX.....XX", "XX.....XX", "XX.....XX"],
 'i': ["XX", "XX", "..", "XX", "XX", "XX", "XX", "XX", "XX"],
 'n': ["......", "......", "......", "XXXXX.", "XXXXXX", "XX..XX", "XX..XX", "XX..XX", "XX..XX"],
 'e': ["......", "......", "......", ".XXXX.", "XX..XX", "XXXXXX", "XX....", "XX..XX", ".XXXX."],
 'X': ["XX.....XX", "XXX...XXX", ".XXX.XXX.", "..XXXXX..", "...XXX...", "..XXXXX..", ".XXX.XXX.", "XXX...XXX", "XX.....XX"],
}
N = 48; R = N / 2 - 0.5
coin = np.zeros((N, N, 4), np.uint8)
inside = np.array([[math.hypot(i - R, j - R) <= R - 0.2 for i in range(N)] for j in range(N)])
for j in range(N):
    for i in range(N):
        if not inside[j, i]: continue
        d = math.hypot(i - R, j - R); s = (i + j) / (2 * R)
        edge = any(not (0 <= j + dj < N and 0 <= i + di < N and inside[j + dj, i + di]) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge: c = G[6]
        elif d > R - 4: c = G[2] if s < .8 else (G[5] if s > 1.2 else G[4])          # rim
        elif d > R - 5: c = G[4]                                                      # inner groove
        else:
            c = G[1]
            if s < .55 and d > R - 10: c = G[0]
            if s > 1.4 and d > R - 10: c = G[3]
        coin[j, i] = (*c, 255)
cols = []
for ch in 'MineX':
    g = np.array([[c == 'X' for c in row] for row in LETTERS[ch]])
    cols += [g, np.zeros((9, 1), bool)]
txt = np.concatenate(cols[:-1], axis=1)                                              # 36 x 9
th, tw = txt.shape; x0 = (N - tw) // 2; y0 = (N - th) // 2
m = np.zeros((N, N), bool); m[y0:y0 + th, x0:x0 + tw] = txt
ring = m.copy()
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        ring |= np.roll(np.roll(m, dy, 0), dx, 1)
shadow = np.roll(ring, 2, 0) | np.roll(np.roll(ring, 1, 0), 1, 1)
coin[shadow & ~ring & (coin[..., 3] > 0), :3] = G[6]                                 # drop shadow on the gold
coin[ring & ~m, :3] = (16, 30, 72)                                                   # navy outline
grad = [(196, 255, 250), (120, 246, 240), (74, 237, 217), (52, 214, 226), (46, 186, 236), (52, 150, 236), (72, 116, 230), (92, 88, 214), (100, 70, 196)]
for y in range(th):
    for x in range(tw):
        if txt[y, x]:
            c = grad[y]
            if y < th // 2 and (y == 0 or not txt[y - 1, x]): c = (232, 255, 252)     # top-edge highlight, upper half only
            coin[y0 + y, x0 + x, :3] = c
Image.fromarray(coin, 'RGBA').save(D / 'minex_coin.png')

# --- wordmark: "MineX" in the game font, gold rows, 1-texel dark outline
def glyph(ch):
    r, c = ord(ch) // 16, ord(ch) % 16
    cell = font[r * 8:(r + 1) * 8, c * 8:(c + 1) * 8]
    cols = np.where(cell.any(axis=0))[0]
    return cell[:, :cols.max() + 1]
def bold(g):                                         # the game's bold style: the glyph drawn again one texel right
    out = np.zeros((g.shape[0], g.shape[1] + 1), bool)
    out[:, :-1] |= g; out[:, 1:] |= g
    return out
parts = []
for ch in 'MineX':
    parts += [bold(glyph(ch)), np.zeros((8, 1), bool)]
bm = np.concatenate(parts[:-1], axis=1)
h, w = bm.shape
pad = np.zeros((h + 2, w + 2), bool); pad[1:-1, 1:-1] = bm
ring = pad.copy()
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        ring |= np.roll(np.roll(pad, dy, 0), dx, 1)
tex = np.zeros((h + 2, w + 2, 4), np.uint8)
tex[ring & ~pad] = (*G[6], 255)
rows = [G[0], G[1], G[1], G[2], G[3], G[4], G[5], G[5]]                    # gold, for the X
white_rows = [(255, 255, 255)] * 8                                              # same white as the headline text, for "Mine"
x_start = sum(p.shape[1] for p in parts[:-2])                                        # first column of the final X
for y in range(h):
    for x in range(w):
        if bm[y, x]: tex[y + 1, x + 1] = (*(rows[y] if x >= x_start else white_rows[y]), 255)
Image.fromarray(tex, 'RGBA').save(D / 'minex_wordmark.png')
print('coin 16x16, wordmark', tex.shape[1], 'x', tex.shape[0])
