#!/usr/bin/env python3
"""MineX server-list banner, style 3: the "everything at once" board, after ManaCube and MysticMC on
Minecraft Buzz.

    python3 -I board-banner.py sponsor-assets OUT_FRAMES_DIR [IP]

Dark navy board with a gold frame and a faint deepslate texture. Left to right: the MineX coin and voxel
wordmark, a PREMIUM / + / CRACKED stat column, the three game modes stacked in their own colours with item
icons, and an IP plate. 170 frames at 1092x140, 25 fps, one seamless loop. Nothing changes panel; instead a
spotlight runs across the modes in turn (each one bounces, its icon wiggles and a shine sweeps the word),
then lands on the IP plate, which pulses.
"""
import sys, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

A = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
IP = sys.argv[3] if len(sys.argv) > 3 else 'ML.MINEX.GG'
W, H, N = 1092, 140, 170
BUNGEE = str(A / 'fonts' / 'bungee-400.ttf')
BEATS = [(0, 40), (42, 82), (84, 124), (126, 170)]        # spotlight: survival, payouts, events, IP

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3

def text_layer(text, size, top, bottom, ink, stroke, shadow_dy, ss=2):
    f = ImageFont.truetype(BUNGEE, size * ss)
    l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f, stroke_width=stroke * ss)
    pad = 6 * ss
    w, h = r - l + 2 * pad, b - t + 2 * pad + shadow_dy * ss
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ox, oy = pad - l, pad - t
    if shadow_dy:
        sh = Image.new('L', (w, h), 0)
        ImageDraw.Draw(sh).text((ox, oy + shadow_dy * ss), text, font=f, fill=255, stroke_width=stroke * ss, stroke_fill=255)
        img.paste((6, 6, 16, 255), (0, 0), sh)
    if stroke:
        ol = Image.new('L', (w, h), 0)
        ImageDraw.Draw(ol).text((ox, oy), text, font=f, fill=255, stroke_width=stroke * ss, stroke_fill=255)
        img.paste(ink + (255,), (0, 0), ol)
    fm = Image.new('L', (w, h), 0); ImageDraw.Draw(fm).text((ox, oy), text, font=f, fill=255)
    bb = fm.getbbox(); gp = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        k = min(1, max(0, (y - bb[1]) / max(1, bb[3] - bb[1])))
        gp[y, :, :3] = [int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)]; gp[y, :, 3] = 255
    img.paste(Image.fromarray(gp, 'RGBA'), (0, 0), fm)
    out = img.resize((w // ss, h // ss), Image.LANCZOS)
    out.info['fill'] = fm.resize((w // ss, h // ss), Image.LANCZOS)          # fill-only mask, for shines
    return out

def outlined(name, size, ink=(10, 8, 20), by='height'):
    im = Image.open(A / 'props' / f'{name}.png').convert('RGBA'); im = im.crop(im.getbbox())
    if by == 'height': im = im.resize((round(im.width * size / im.height), size), Image.LANCZOS)
    else: im = im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
    pad = 5
    base = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new('L', base.size, 0); a.paste(im.getchannel('A'), (pad, pad))
    base.paste(ink + (255,), (0, 0), a.filter(ImageFilter.MaxFilter(5)).point(lambda v: 255 if v > 90 else int(v * 2.8)))
    base.alpha_composite(im, (pad, pad))
    return base

# ------------------------------------------------------------------ pieces
COIN = outlined('minex_coin', 104)
WORDMARK = outlined('minex_wordmark', 170, by='width')
GOLD = ((255, 246, 190), (255, 186, 40))
STAT = [text_layer('PREMIUM', 22, (255, 255, 255), (214, 222, 255), (10, 12, 30), 4, 3),
        text_layer('+', 22, *GOLD, (40, 22, 4), 4, 3),
        text_layer('CRACKED', 22, (255, 255, 255), (214, 222, 255), (10, 12, 30), 4, 3)]
MODES = [  # word, gradient top/bottom, outline ink, icon
    ('SURVIVAL', (190, 255, 160), (52, 196, 70), (8, 44, 14), 'diamond_sword'),
    ('PAYOUTS', (255, 246, 150), (255, 160, 20), (60, 28, 0), 'gold_ingot'),
    ('EVENTS', (255, 196, 250), (226, 72, 214), (54, 6, 60), 'firework_rocket'),
]
MODE_TXT = [text_layer(w, 34, top, bot, ink, 5, 3) for w, top, bot, ink, _ in MODES]
MODE_ICON = [outlined(icon, 34) for *_, icon in MODES]
KICK = text_layer('PLAY NOW', 16, (255, 250, 170), (255, 196, 40), (40, 22, 4), 3, 2)
def fit_ip(size=46):
    while True:
        t = text_layer(IP, size, (255, 255, 255), (150, 232, 255), (8, 22, 60), 5, 4)
        if t.width <= 300 or size < 20: return t
        size -= 2
IPT = fit_ip()

# ------------------------------------------------------------------ background
def make_background():
    yy = np.linspace(0, 1, H)[:, None, None]
    img = np.array((30, 40, 92), np.float32) * (1 - yy) + np.array((12, 14, 40), np.float32) * yy
    img = np.broadcast_to(img, (H, W, 3)).copy()
    ds = Image.open(A / 'deepslate.png').convert('L').resize((64, 64), Image.NEAREST)
    tile = np.tile(np.asarray(ds, np.float32) / 255, (H // 64 + 1, W // 64 + 1))[:H, :W, None]
    img = img * (0.78 + 0.42 * tile)
    return img
BG = make_background()
XX = np.arange(W)[None, :]; YY = np.arange(H)[:, None]

def background(f):
    img = BG.copy()
    period = 64.0                                         # faint stripes drifting right, wrapping per loop
    u = (XX + YY * 0.6 - 3 * period * f / N) % period
    img += (u < period / 2)[..., None] * 6
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')

def frame_and_dividers(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=(8, 6, 14, 255), width=3)
    d.rectangle([3, 3, W - 4, H - 4], outline=(255, 190, 50, 255), width=2)
    d.rectangle([5, 5, W - 6, H - 6], outline=(120, 70, 10, 255), width=1)
    for x in (300, 432):
        d.line([(x, 18), (x, H - 18)], fill=(255, 190, 50, 140), width=2)
        d.line([(x + 2, 18), (x + 2, H - 18)], fill=(0, 0, 0, 120), width=1)

SPARKS = [(random.Random(s).uniform(20, W - 20), random.Random(s + 99).uniform(12, H - 12), random.Random(s + 7).randrange(N)) for s in range(18)]
def sparkles(img, f):
    d = ImageDraw.Draw(img)
    for x, y, ph in SPARKS:
        k = ((f + ph) % 34) / 34.0; s = max(0, math.sin(k * math.pi)) * 6
        if s < 1: continue
        a = int(200 * s / 6)
        d.polygon([(x, y - s), (x + s * .28, y), (x, y + s), (x - s * .28, y)], fill=(255, 255, 255, a))
        d.polygon([(x - s, y), (x, y - s * .28), (x + s, y), (x, y + s * .28)], fill=(255, 255, 255, a))

def shine(layer, p, width=14):
    """Sweep a diagonal white band across a text layer's fill; p goes 0..1."""
    m = layer.info.get('fill') or layer.getchannel('A')
    band = Image.new('L', layer.size, 0)
    x = -40 + p * (layer.width + 80)
    ImageDraw.Draw(band).polygon([(x, 0), (x + width, 0), (x + width - 30, layer.height), (x - 30, layer.height)], fill=170)
    band = Image.composite(band, Image.new('L', layer.size, 0), m)
    out = layer.copy(); out.alpha_composite(Image.merge('RGBA', (Image.new('L', layer.size, 255),) * 3 + (band,)))
    return out

def scaled(layer, s):
    if abs(s - 1) < 1e-3: return layer
    size = (max(1, round(layer.width * s)), max(1, round(layer.height * s)))
    out = layer.resize(size, Image.LANCZOS)
    if 'fill' in layer.info: out.info['fill'] = layer.info['fill'].resize(size, Image.LANCZOS)
    return out

# ------------------------------------------------------------------ frame
def render(f):
    img = background(f)
    sparkles(img, f)
    beat = next(i for i, (a, b) in enumerate(BEATS) if a <= f < b + (1 if i == 3 else 2)) if f < N else 3
    a0, a1 = BEATS[beat]; t = (f - a0) / (a1 - a0)

    # logo block
    coin = COIN
    p = f % 85
    if p < 16: coin = shine(COIN, p / 15, 14)
    img.alpha_composite(coin, (12, (H - coin.height) // 2))
    img.alpha_composite(WORDMARK, (114, (H - WORDMARK.height) // 2))

    # stat column
    ys = [16, 52, 86]
    for lay, y in zip(STAT, ys):
        img.alpha_composite(lay, (366 - lay.width // 2, y))

    # modes
    x0 = 452
    for i, (lay, icon) in enumerate(zip(MODE_TXT, MODE_ICON)):
        y = 6 + i * 42
        s, ang, dx = 1.0, 0, 0
        L = lay
        if beat == i:
            bump = math.sin(math.pi * min(1, t * 2.2))            # quick pop, then settle
            s = 1 + 0.10 * bump
            ang = 18 * math.sin(t * math.pi * 4) * (1 - t)
            dx = 6 * bump
            L = shine(lay, min(1, t * 1.4))
        else:
            dim = L.copy(); dim.putalpha(dim.getchannel('A').point(lambda v: int(v * .93))); L = dim
        ic = icon.rotate(ang, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(ic, (x0 - ic.width // 2 + 18, y + 22 - ic.height // 2))
        L = scaled(L, s)
        img.alpha_composite(L, (x0 + 42 + int(dx), y + (lay.height - L.height) // 2))

    # IP plate
    px0, px1, py0, py1 = 790, W - 16, 18, H - 16
    glow = 0.0
    if beat == 3: glow = math.sin(math.pi * min(1, t * 1.6))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([px0 + 3, py0 + 5, px1 + 3, py1 + 5], 14, fill=(4, 4, 12, 200))
    base = (24, 34, 84); hi = (40, 70, 160)
    fill = tuple(int(base[k] + (hi[k] - base[k]) * glow) for k in range(3))
    d.rounded_rectangle([px0, py0, px1, py1], 14, fill=fill + (255,), outline=(255, 190, 50, 255), width=3)
    sheen = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sheen).rounded_rectangle([px0 + 6, py0 + 5, px1 - 6, (py0 + py1) // 2 - 6], 10, fill=(255, 255, 255, 26))
    img.alpha_composite(sheen)
    cx = (px0 + px1) // 2
    img.alpha_composite(KICK, (cx - KICK.width // 2, py0 - 8))
    ipl = IPT
    if beat == 3: ipl = shine(scaled(IPT, 1 + 0.05 * glow), min(1, t * 1.3))
    img.alpha_composite(ipl, (cx - ipl.width // 2, (py0 + py1) // 2 - ipl.height // 2 + 8))

    frame_and_dividers(img)
    return img.convert('RGB')

if __name__ == '__main__':
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    last = int(sys.argv[5]) if len(sys.argv) > 5 else N
    for f in range(first - 1, last):
        render(f).save(OUT / f'f{f + 1:03d}.png')
    print('ok', first, last)
