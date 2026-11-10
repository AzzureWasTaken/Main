#!/usr/bin/env python3
"""MineX server-list banner, style 4: in the format of the BlossomCraft banner on Minecraft Buzz.

    python3 -I blossom-banner.py sponsor-assets OUT_FRAMES_DIR [IP]

Full bleed, no logo plate. Each panel is one bright colour with a big darker swirl pattern turning slowly
behind everything. Panel 1 is the brand line-up (as BlossomCraft's "1.21 | logo | JAVA + BEDROCK CROSSPLAY"):
the MineX coin on the left, the voxel MineX wordmark in the middle, PREMIUM + CRACKED over the IP on the right.
Panels 2-4 are a thin kicker over a huge bold white word, with the panel's 3D Minecraft item mirrored on each
side. Between panels the giant MineX coin sweeps across the banner and the new panel is revealed behind it;
text zooms in out of a blur and the items pop up from the bottom edge. 170 frames, 1092x140, 25 fps, one loop.
"""
import sys, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

A = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
IP = sys.argv[3] if len(sys.argv) > 3 else 'ML.MINEX.GG'
W, H, N = 1092, 140, 170
STARTS = [0, 43, 85, 128]
SWEEP = 10                                   # frames the coin takes to cross
M9 = str(A / 'fonts' / 'montserrat-900.ttf'); M6 = str(A / 'fonts' / 'montserrat-600.ttf')

PANELS = [  # base colour, swirl-line colour
    dict(kind='brand', base=(248, 142, 52), line=(206, 64, 40), float=('diamond', 'emerald', 'gold_ingot')),
    dict(kind='word', kicker='BUILD, EXPLORE &', word='SURVIVAL', base=(240, 150, 192), line=(120, 44, 96), item='diamond_sword', float=('grass_block', 'nether_star', 'diamond')),
    dict(kind='word', kicker='GRIND FOR REAL', word='PAYOUTS', base=(172, 152, 232), line=(92, 70, 164), item='gold_ingot', float=('emerald', 'diamond', 'gold_block')),
    dict(kind='word', kicker='COMPETE IN', word='EVENTS', base=(92, 204, 232), line=(36, 108, 170), item='firework_rocket', float=('tnt', 'nether_star', 'firework_rocket')),
]

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_back(t):
    t = min(max(t, 0), 1); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

# ------------------------------------------------------------------ type: white, soft shadow, no outline
def text(s, font, size, alpha=255, shadow=True, ss=2):
    f = ImageFont.truetype(font, size * ss)
    l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), s, font=f)
    pad = 14 * ss
    w, h = r - l + 2 * pad, b - t + 2 * pad
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - l, pad - t), s, font=f, fill=255)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = m.filter(ImageFilter.GaussianBlur(5 * ss)).point(lambda v: int(v * .55))
        img.paste((30, 10, 30, 255), (0, int(3 * ss)), sh)
    img.paste((255, 255, 255, alpha), (0, 0), m)
    return img.resize((w // ss, h // ss), Image.LANCZOS)

def fit(s, font, size, max_w, **kw):
    while True:
        t = text(s, font, size, **kw)
        if t.width <= max_w or size < 20: return t
        size -= 2

def prop(name, size, by='height'):
    im = Image.open(A / 'props' / f'{name}.png').convert('RGBA'); im = im.crop(im.getbbox())
    if by == 'height': return im.resize((round(im.width * size / im.height), size), Image.LANCZOS)
    return im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)

def outlined(im, ink=(40, 14, 6), r=5):
    pad = r + 1
    base = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new('L', base.size, 0); a.paste(im.getchannel('A'), (pad, pad))
    base.paste(ink + (255,), (0, 0), a.filter(ImageFilter.MaxFilter(2 * r + 1)).point(lambda v: 255 if v > 90 else int(v * 2.8)))
    base.alpha_composite(im, (pad, pad))
    return base

COIN = outlined(prop('minex_coin', 128))
WORDMARK = outlined(prop('minex_wordmark', 400, by='width'))
SWEEP_COIN = prop('minex_coin', 300)
BRAND_TOP = text('PREMIUM + CRACKED', M9, 25)
BRAND_IP = fit(IP, M9, 46, 330)
KICK = [text(p['kicker'], M6, 24, alpha=235) if p['kind'] == 'word' else None for p in PANELS]
WORD = [fit(p['word'], M9, 96, 620) if p['kind'] == 'word' else None for p in PANELS]

def item_pair(name, height):
    """The panel's 3D item, outlined, as a mirrored pair: the left one faces right, the right one faces left."""
    im = outlined(prop(name, height), ink=(34, 16, 34), r=3)
    return ImageOps.mirror(im), im
ITEMS = [item_pair(p['item'], 136) if p['kind'] == 'word' else None for p in PANELS]

# ------------------------------------------------------------------ background: colour + turning swirl
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
CX, CY = W / 2, H + 30
R = np.hypot((XX - CX) * 0.55, YY - CY) + 1
TH = np.arctan2(YY - CY, (XX - CX) * 0.55)
def background(i, f):
    p = PANELS[i]
    rot = 2 * math.pi * f / N                                      # one full turn of the pattern per loop
    v = np.sin(3 * (TH + rot / 3) + 3.2 * np.log(R / 30))          # 3-armed log spiral, broad sweeping curves
    line = np.clip(1 - (np.abs(v) - 0.26) / 0.09, 0, 1)[..., None]
    base = np.array(p['base'], np.float32); ln = np.array(p['line'], np.float32)
    img = base * (1 - 0.85 * line) + ln * 0.85 * line
    glow = np.clip(1 - np.hypot((XX - CX) / 520, (YY - CY) / 150), 0, 1)[..., None]
    img = img + glow * 26
    edge = np.clip((np.abs(XX - W / 2) / (W / 2) - 0.78) / 0.22, 0, 1)[..., None]
    img = img * (1 - 0.22 * edge)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')

FLOAT_SPOTS = [(48, 34, 52, 0.0), (150, 104, 40, 2.1), (1044, 36, 48, 1.0), (946, 110, 40, 3.3), (250, 22, 30, 4.4), (842, 20, 30, 5.2)]
FLOAT_CACHE = {}
def floaters(img, i, f, t):
    """Small themed items drifting in the outer thirds, behind the main content."""
    names = PANELS[i]['float']
    pop = min(1, max(0, (t - 2) / 8))
    for k, (x, y, size, ph) in enumerate(FLOAT_SPOTS):
        if PANELS[i]['kind'] == 'brand' and x > 200: continue
        name = names[k % len(names)]
        key = (name, size)
        if key not in FLOAT_CACHE: FLOAT_CACHE[key] = outlined(prop(name, size), ink=(34, 16, 34), r=2)
        im = FLOAT_CACHE[key]
        ang = 14 * math.sin(2 * math.pi * f / 85 + ph)
        im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
        if pop < 1:
            im = im.resize((max(1, int(im.width * ease_back(pop))), max(1, int(im.height * ease_back(pop)))), Image.LANCZOS) if pop > 0 else None
        if im is None: continue
        dy = 6 * math.sin(2 * math.pi * f / 56.67 + ph)
        put_center(img, im, x, y + dy)

def zoom_in(layer, u):
    """Text entering: from 1.45x and blurred to sharp and 1x as u goes 0..1."""
    u = min(max(u, 0), 1)
    if u >= 1: return layer
    s = 1 + 0.45 * (1 - ease_out(u))
    out = layer.resize((max(1, round(layer.width * s)), max(1, round(layer.height * s))), Image.LANCZOS)
    out = out.filter(ImageFilter.GaussianBlur(5 * (1 - u)))
    out.putalpha(out.getchannel('A').point(lambda v: int(v * min(1, u * 1.8))))
    return out

def put_center(img, layer, cx, cy):
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

def panel(i, t, f):
    p = PANELS[i]
    img = background(i, f)
    floaters(img, i, f, t)
    u = (t - 4) / 7                                                # entry animation clock
    if p['kind'] == 'brand':
        bob = 3 * math.sin(2 * math.pi * f / 42.5)
        c = zoom_in(COIN, u)
        put_center(img, c, 110, 70 + bob)
        wm = zoom_in(WORDMARK, (t - 5) / 7)
        put_center(img, wm, 480, 70)
        top = zoom_in(BRAND_TOP, (t - 6) / 7); ipl = zoom_in(BRAND_IP, (t - 7) / 7)
        put_center(img, top, 900, 44); put_center(img, ipl, 900, 88)
    else:
        L, Rb = ITEMS[i]
        rise = (1 - ease_back((t - 3) / 9)) * 150 if t < 12 else 0
        gap = WORD[i].width / 2 + 96
        for k, (b, x) in enumerate(((L, W / 2 - gap), (Rb, W / 2 + gap))):
            bob = 3 * math.sin(2 * math.pi * f / 42.5 + k * 2.2)
            ang = 6 * math.sin(2 * math.pi * f / 85 + k)
            bb = b.rotate(ang, resample=Image.BICUBIC, expand=True)
            img.alpha_composite(bb, (int(x - bb.width / 2), int((H - bb.height) / 2 + 4 + rise + bob)))
        put_center(img, zoom_in(KICK[i], (t - 4) / 7), W / 2, 24)
        put_center(img, zoom_in(WORD[i], (t - 5) / 7), W / 2, 84)
    return img

def render(f):
    cur = max(i for i, s in enumerate(STARTS) if s <= f)
    t = f - STARTS[cur]
    img = panel(cur, t, f)
    if t < SWEEP:                                                  # giant coin sweeps across, revealing the new panel
        prev = panel((cur - 1) % 4, 99, f)
        k = ease_out((t + 1) / SWEEP)
        cx = -260 + (W + 520) * k; cy = 190 - 260 * k
        mask = Image.new('L', (W, H), 0)
        ImageDraw.Draw(mask).polygon([(cx + 60, -40), (cx - 60, H + 40), (-10, H + 40), (-10, -40)], fill=255)
        mixed = prev.copy(); mixed.paste(img, (0, 0), mask)
        for j, a in ((3, 50), (2, 90), (1, 140)):                  # motion trail
            g = SWEEP_COIN.rotate(-40 * (k - j * .06) * 9, resample=Image.BICUBIC, expand=True).copy()
            g.putalpha(g.getchannel('A').point(lambda v, a=a: v * a // 255))
            put_center(mixed, g, cx - j * 46, cy + j * 26)
        c = SWEEP_COIN.rotate(-40 * k * 9, resample=Image.BICUBIC, expand=True)
        put_center(mixed, c, cx, cy)
        img = mixed
    return img.convert('RGB')

if __name__ == '__main__':
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    last = int(sys.argv[5]) if len(sys.argv) > 5 else N
    for f in range(first - 1, last):
        render(f).save(OUT / f'f{f + 1:03d}.png')
    print('ok', first, last)
