#!/usr/bin/env python3
"""Pixel-art textures for the MineX logo, in Minecraft's own gold and diamond palettes, so the logo can be
rendered as 3D voxel items like the banner's other props.

    python3 -I make_logo_textures.py PTEX_DIR      # writes minex_coin.png (16x16) and minex_wordmark.png
"""
import sys, math
from pathlib import Path
import numpy as np
from PIL import Image

D = Path(sys.argv[1])
G = [(255, 253, 224), (253, 245, 95), (250, 214, 74), (233, 177, 21), (220, 150, 19), (178, 100, 17), (117, 40, 2)]  # gold_ingot.png
C = [(213, 255, 246), (161, 251, 232), (74, 237, 217), (32, 197, 181), (17, 114, 122)]                              # diamond.png

# --- coin: 16x16, outlined rim, bevelled face, cyan X
coin = np.zeros((16, 16, 4), np.uint8)
inside = np.array([[math.hypot(i - 7.5, j - 7.5) <= 7.3 for i in range(16)] for j in range(16)])
for j in range(16):
    for i in range(16):
        if not inside[j, i]: continue
        d = math.hypot(i - 7.5, j - 7.5); s = i + j
        edge = any(not (0 <= j + dj < 16 and 0 <= i + di < 16 and inside[j + dj, i + di]) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge: c = G[6]
        elif d > 5.5: c = G[2] if s < 13 else (G[5] if s > 17 else G[4])
        else:
            c = G[1]
            if d > 4.3 and s < 12: c = G[0]
            if d > 4.3 and s > 18: c = G[3]
        coin[j, i] = (*c, 255)
xm = np.zeros((16, 16), bool)                        # bold X: two-texel diagonals
for k in range(6):
    for (i, j) in ((4 + k, 5 + k), (5 + k, 5 + k), (11 - k, 5 + k), (10 - k, 5 + k)):
        xm[j, i] = True
edge = np.zeros_like(xm)
for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)):
    edge |= np.roll(np.roll(xm, dj, 0), di, 1)
edge &= ~xm & (coin[..., 3] > 0) & ~(np.array([[1 if tuple(coin[j, i, :3]) == G[6] else 0 for i in range(16)] for j in range(16)], bool))
coin[edge, :3] = C[4]
for j in range(16):
    for i in range(16):
        if xm[j, i]: coin[j, i, :3] = C[1] if j < 7 else C[2]
Image.fromarray(coin, 'RGBA').save(D / 'minex_coin.png')

# --- wordmark: "MineX" in the game font, gold rows, 1-texel dark outline
font = np.asarray(Image.open(D / 'ascii.png').convert('RGBA'))[..., 3] > 0
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
rows = [G[0], G[1], G[1], G[2], G[3], G[4], G[5], G[5]]
for y in range(h):
    for x in range(w):
        if bm[y, x]: tex[y + 1, x + 1] = (*rows[y], 255)
Image.fromarray(tex, 'RGBA').save(D / 'minex_wordmark.png')
print('coin 16x16, wordmark', tex.shape[1], 'x', tex.shape[0])
