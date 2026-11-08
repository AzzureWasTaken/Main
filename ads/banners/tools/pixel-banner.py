#!/usr/bin/env python3
"""Pixel-art rebuild of the MineX server-list banner, drawn natively at 468x60.

    python3 -I pixel-banner.py pixel-assets OUT_FRAMES_DIR [IP]

Everything sits on one 2px grid (one Minecraft texel = 2x2 screen pixels): real block tiles for the
panel backgrounds, real item sprites, the real Minecraft font (font/ascii.png) for the words, a hand-built
pixel coin, flat colours and hard 2px outlines. Nothing is smoothed or blurred. 170 frames at 25 fps, one
loop: SURVIVAL, PAYOUTS, EVENTS, then the IP.
"""
import sys, math, random
from pathlib import Path
import numpy as np
from PIL import Image

TEX = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
IP = sys.argv[3] if len(sys.argv) > 3 else 'ML.MINEX.GG'
W, H, N, G = 468, 60, 170, 2
WW, WH = W // G, H // G                      # world size in texels: 234 x 30
PANELS = ['SURVIVAL', 'PAYOUTS', 'EVENTS', IP]
STARTS = [0, 44, 86, 128]                     # first frame of each panel; each opens with an 8-frame wipe
WIPE = 8
INNER = (4, 4, W - 4, H - 4)                  # inside the frame

# ------------------------------------------------------------------ assets
def tex(name):
    return np.asarray(Image.open(TEX / f'{name}.png').convert('RGBA')).copy()

FONT = np.asarray(Image.open(TEX / 'ascii.png').convert('RGBA'))[..., 3] > 0

def glyph(c):
    code = ord(c); r, col = code // 16, code % 16
    cell = FONT[r*8:(r+1)*8, col*8:(col+1)*8]
    cols = np.where(cell.any(axis=0))[0]
    if not len(cols): return np.zeros((8, 3), bool)            # space: 3 wide + 1 gap = 4
    return cell[:, :cols.max() + 1]

def text_bitmap(s):
    parts = []
    for c in s:
        g = glyph(c)
        parts.append(np.concatenate([g, np.zeros((8, 1), bool)], axis=1))
    return np.concatenate(parts, axis=1)[:, :-1]               # drop the trailing gap

def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out

def blit(dst, src_rgb, mask, x, y, clip=INNER):
    """Draw src_rgb (h,w,3) through bool mask at (x,y), clipped to clip=(x0,y0,x1,y1)."""
    h, w = mask.shape
    x0, y0, x1, y1 = clip
    cx0, cy0, cx1, cy1 = max(x, x0), max(y, y0), min(x + w, x1), min(y + h, y1)
    if cx1 <= cx0 or cy1 <= cy0: return
    m = mask[cy0 - y: cy1 - y, cx0 - x: cx1 - x]
    s = src_rgb[cy0 - y: cy1 - y, cx0 - x: cx1 - x] if src_rgb.ndim == 3 else src_rgb
    region = dst[cy0:cy1, cx0:cx1]
    region[m] = s[m] if src_rgb.ndim == 3 else np.array(src_rgb, np.uint8)

GOLD = [(255, 226, 110), (255, 190, 30), (255, 170, 0), (255, 170, 0), (255, 170, 0), (222, 132, 0), (190, 104, 0)]
CREAM = [(255, 255, 255), (255, 250, 232), (250, 238, 208), (250, 238, 208), (250, 238, 208), (226, 208, 168), (206, 186, 146)]

def draw_text(dst, s, x, y, scale, tones, outline=(45, 25, 0), shadow=(14, 8, 0), clip=INNER):
    """Minecraft-font text: hard outline, drop shadow, row-by-row flat tones (light top, dark bottom)."""
    bm = text_bitmap(s)
    mask = np.kron(bm, np.ones((scale, scale), bool))
    pad = 4
    full = np.zeros((mask.shape[0] + 2*pad, mask.shape[1] + 2*pad), bool)
    full[pad:pad + mask.shape[0], pad:pad + mask.shape[1]] = mask
    rim = dilate(full, 2)
    colors = np.zeros(full.shape + (3,), np.uint8)
    for r in range(8):
        rows = slice(pad + r*scale, pad + (r + 1)*scale)
        colors[rows, :] = tones[min(r, len(tones) - 1)]
    sh = np.roll(np.roll(rim, 2, 0), 2, 1)
    blit(dst, np.array(shadow, np.uint8), sh, x - pad, y - pad, clip)
    blit(dst, np.array(outline, np.uint8), rim, x - pad, y - pad, clip)
    blit(dst, colors, full, x - pad, y - pad, clip)
    return bm.shape[1] * scale

def text_width(s, scale):
    return text_bitmap(s).shape[1] * scale

# ------------------------------------------------------------------ world (texel space, 234x30)
def put_tile(world, t, tx, ty):
    h, w = t.shape[:2]
    x0, y0 = max(tx, 0), max(ty, 0); x1, y1 = min(tx + w, WW), min(ty + h, WH)
    if x1 <= x0 or y1 <= y0: return
    src = t[y0 - ty:y1 - ty, x0 - tx:x1 - tx]
    a = src[..., 3:4] > 127
    world[y0:y1, x0:x1] = np.where(a, src[..., :3], world[y0:y1, x0:x1])

def rect(world, x, y, w, h, c):
    world[max(y, 0):min(y + h, WH), max(x, 0):min(x + w, WW)] = c

T = {n: tex(n) for n in ['stone', 'cobblestone', 'coal_ore', 'gold_ore', 'netherrack', 'nether_bricks', 'obsidian',
                           'grass_block_side', 'glowstone', 'iron_sword', 'gold_ingot', 'firework_rocket', 'ender_pearl']}
LAVA = np.asarray(Image.open(TEX / 'lava_still.png').convert('RGB'))
LAVA_FRAMES = list(range(20)) + list(range(18, 0, -1))          # the game's own animation order

def world_survival(f):
    w = np.zeros((WH, WW, 3), np.uint8)
    rect(w, 0, 0, WW, 9, (113, 166, 255)); rect(w, 0, 9, WW, 10, (143, 189, 255))
    for cx, cy, cw in ((84, 3, 14), (130, 8, 12), (196, 2, 16), (52, 9, 10)):             # blocky clouds
        rect(w, cx + 1, cy, cw - 2, 1, (255, 255, 255)); rect(w, cx, cy + 1, cw, 2, (255, 255, 255))
        rect(w, cx + 1, cy + 3, cw - 2, 1, (214, 226, 255))
    for hx, hw, hh in ((0, 18, 3), (18, 10, 2), (28, 22, 4), (58, 14, 2), (96, 20, 3), (130, 16, 4), (160, 24, 2), (200, 34, 3)):
        rect(w, hx, 19 - hh, hw, hh, (66, 124, 36))                                      # far hills
    for tx in range(0, WW, 16):
        put_tile(w, T['grass_block_side'], tx, 19)
    rect(w, 170, 12, 4, 7, (104, 78, 46)); rect(w, 170, 12, 1, 7, (84, 60, 36)); rng = random.Random(3)   # oak tree
    for ly in range(4, 13):
        for lx in range(164, 180):
            if (ly in (4, 12) and lx in (164, 179)) or (ly == 4 and lx in (165, 178)): continue
            w[ly, lx] = rng.choice([(70, 136, 36), (86, 160, 46), (58, 114, 30), (86, 160, 46)])
    return w

def world_payouts(f):
    w = np.zeros((WH, WW, 3), np.uint8)
    ores = {(2, 0): 'coal_ore', (8, 1): 'coal_ore', (12, 0): 'coal_ore', (5, 1): 'gold_ore', (10, 0): 'gold_ore',
            (13, 1): 'gold_ore', (0, 1): 'cobblestone', (6, 0): 'cobblestone', (14, 1): 'cobblestone', (3, 1): 'cobblestone'}
    for ty in range(2):
        for tx in range(15):
            t = T[ores.get((tx, ty), 'stone')]
            put_tile(w, t, tx * 16, ty * 16)
    return w

def world_events(f):
    w = np.zeros((WH, WW, 3), np.uint8)
    for tx in range(15):
        put_tile(w, T['netherrack'], tx * 16, 0)
    put_tile(w, T['glowstone'], 6 * 16, 0); put_tile(w, T['nether_bricks'], 13 * 16, 0)
    for tx in range(15):
        put_tile(w, T['netherrack'], tx * 16, 16)
    k = LAVA_FRAMES[(f // 2) % len(LAVA_FRAMES)]
    lava = np.concatenate([LAVA[k*16:(k + 1)*16], np.full((16, 16, 1), 255, np.uint8).repeat(1, 1)[:, :, :0].reshape(16, 16, 0)], axis=2) if False else LAVA[k*16:(k + 1)*16]
    for tx in range(15):
        w[18:30, tx*16:min(tx*16 + 16, WW)] = lava[:12, :min(16, WW - tx*16)]
    rect(w, 0, 16, WW, 2, (66, 20, 22))
    return w

def world_ip(f):
    w = np.zeros((WH, WW, 3), np.uint8)
    for ty in range(2):
        for tx in range(15):
            put_tile(w, T['obsidian'], tx * 16, ty * 16)
    for i, (sx, sy) in enumerate(((20, 5), (44, 22), (72, 8), (104, 24), (150, 6), (176, 21), (204, 9), (226, 25), (126, 12))):
        if (f // 5 + i) % 4 == 0: rect(w, sx, sy, 1, 1, (190, 150, 255))
        elif (f // 5 + i) % 4 == 1: rect(w, sx, sy, 1, 1, (110, 80, 190))
    return w

WORLDS = [world_survival, world_payouts, world_events, world_ip]
ICONS = [[('iron_sword', 0, 0)], [('gold_ingot', -6, 4), ('gold_ingot', 4, -4)], [('firework_rocket', 0, 0)], [('ender_pearl', 0, 0)]]

# ------------------------------------------------------------------ fixed pieces
def coin_sprite(f):
    """16x16 gold coin with a cyan X, hand-built; a shine sweeps across it twice per loop."""
    px = np.zeros((16, 16, 4), np.uint8)
    shine = None
    p = f % 85
    if p < 19: shine = int((p - 1) * 1.7)
    for j in range(16):
        for i in range(16):
            d = math.hypot(i - 7.5, j - 7.5)
            if d > 7.7: continue
            if d >= 6.5: c = (104, 62, 0)
            elif d >= 5.4: c = (201, 138, 0)
            else: c = (255, 194, 31)
            if 4.6 < d < 6.5 and (i + j) < 11 and d < 6.5 and c != (104, 62, 0): c = (255, 229, 138)
            if 5.0 <= d < 6.5 and (i + j) > 19: c = (176, 112, 0)
            px[j, i] = (*c, 255)
    gx = glyph('X')                                       # the game font's X: 5x7, cyan with a 1-texel shadow
    for (di, dj, col) in ((1, 1, (24, 56, 150)), (0, 0, (92, 230, 255))):
        for j in range(7):
            for i in range(gx.shape[1]):
                if gx[j, i] and px[2 + j + dj, 5 + i + di, 3]: px[2 + j + dj, 5 + i + di, :3] = col
    if shine is not None:
        for j in range(16):
            for i in range(16):
                if px[j, i, 3] and (i + j) in (shine, shine + 1) and math.hypot(i - 7.5, j - 7.5) < 6.5: px[j, i, :3] = (255, 255, 235)
    return px

def blit_sprite(dst, sprite, x, y, scale, clip=INNER):
    big = np.kron(sprite, np.ones((scale, scale, 1), np.uint8))
    blit(dst, big[..., :3], big[..., 3] > 127, x, y, clip)

def outline_sprite(dst, sprite, x, y, scale, color=(20, 12, 0)):
    big = np.kron(sprite[..., 3] > 127, np.ones((scale, scale), bool))
    pad = 2
    full = np.zeros((big.shape[0] + 2*pad, big.shape[1] + 2*pad), bool); full[pad:-pad, pad:-pad] = big
    rim = dilate(full, 2)
    blit(dst, np.array(color, np.uint8), rim & ~full, x - pad, y - pad)

BADGE = text_bitmap('PREMIUM + CRACKED')

def draw_frame(img):
    img[0:2, :] = img[-2:, :] = img[:, 0:2] = img[:, -2:] = (13, 13, 14)
    img[2:4, 2:W - 2] = (112, 112, 120); img[2:H - 2, 2:4] = (112, 112, 120)
    img[H - 4:H - 2, 2:W - 2] = (36, 36, 42); img[2:H - 2, W - 4:W - 2] = (36, 36, 42)

def panel_at(f):
    p = max(i for i, s in enumerate(STARTS) if s <= f)
    return p, f - STARTS[p]

def render(f):
    p, t = panel_at(f)
    q = (p - 1) % 4
    cur = WORLDS[p](f)
    if t < WIPE:                                                     # hard-edged wipe, left to right, in 2-texel steps
        prev = WORLDS[q](f)
        xb = int(WW * (t + 1) / WIPE) // 2 * 2
        mixed = prev.copy(); mixed[:, :xb] = cur[:, :xb]
        world = mixed
    else:
        world = cur
    img = np.kron(world, np.ones((G, G, 1), np.uint8)).astype(np.float32)
    shade = np.ones((H, W, 1), np.float32)
    shade[:, :156] = 0.42; shade[:, 156:416] = 0.68; shade[:, 416:] = 0.98
    img = (img * shade).astype(np.uint8)

    # left block: coin, wordmark, badge
    coin = coin_sprite(f)
    outline_sprite(img, coin, 8, 14, 2); blit_sprite(img, coin, 8, 14, 2)
    draw_text(img, 'MineX', 46, 6, 4, CREAM)
    bw = BADGE.shape[1] + 6
    bx, by = 46, 39
    img[by:by + 11, bx:bx + bw] = (122, 74, 0); img[by + 1:by + 10, bx + 1:bx + bw - 1] = (255, 170, 0)
    img[by + 1, bx + 1:bx + bw - 1] = (255, 214, 74); img[by + 9, bx + 1:bx + bw - 1] = (214, 128, 0)
    blit(img, np.array((60, 34, 0), np.uint8), np.pad(BADGE, ((0, 0), (0, 0))), bx + 3, by + 2)

    # centre words: old slides up and out, new rises into place
    cx0, cx1 = 156, 416
    def put_word(s, dy):
        wpx = text_width(s, 4)
        draw_text(img, s, (cx0 + cx1) // 2 - wpx // 2 + 2, 16 + dy, 4, GOLD)
    put_word(PANELS[p], max(0, WIPE - 1 - t) * 6 if t < WIPE else 0)
    if t < WIPE: put_word(PANELS[q], -(t + 1) * 6)

    # right icon: bobs gently, swaps once the wipe has reached it
    which = p if (t >= WIPE - 1) else q
    bob = int(round(math.sin(2 * math.pi * f / 34))) * 2
    for name, ox, oy in ICONS[which]:
        spr = T[name]
        outline_sprite(img, spr, 424 + ox, 14 + oy + bob, 2); blit_sprite(img, spr, 424 + ox, 14 + oy + bob, 2)
    draw_frame(img)
    return img

if __name__ == '__main__':
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    last = int(sys.argv[5]) if len(sys.argv) > 5 else N
    for f in range(first - 1, last):
        Image.fromarray(render(f)).save(OUT / f'f{f + 1:03d}.png')
    print('ok', first, last)
