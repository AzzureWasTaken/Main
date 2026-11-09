#!/usr/bin/env python3
"""MineX server-list banner, style 3: a sibling of style 2 (sponsor-banner.py) with its own look.

    python3 -I style3-banner.py sponsor-assets OUT_FRAMES_DIR [IP]

Same bones as style 2 (one mode per panel, matching 3D items either side, the IP as a kicker, the MineX logo
block on the left) but borrowing other Minecraft Buzz banners for the details: each panel's background is a
wall of that mode's real Minecraft block (grass, gold, TNT, diamond) tinted and scrolling, light rays rotate
behind the word, the headline is gold in a rounder bubbly face (Luckiest Guy) and drops in with a bounce, the
items spin in, and panels change with a vertical shutter. 170 frames at 1092x140, 25 fps, one seamless loop.
"""
import sys, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

A = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
IP = sys.argv[3] if len(sys.argv) > 3 else 'ML.MINEX.GG'
W, H, N = 1092, 140, 170
STARTS = [0, 43, 85, 128]
WIPE = 7
BUNGEE = str(A / 'fonts' / 'bungee-400.ttf'); LUCKY = str(A / 'fonts' / 'luckiest-guy-400.ttf')

PANELS = [
    dict(word='SURVIVAL', kicker=IP, top=(92, 222, 92), bottom=(22, 140, 52), ink=(10, 52, 18), tint=(226, 255, 214), block='grass_block_side',
         left=('diamond_sword', 118, -1), right=('diamond_sword', 118, 1)),
    dict(word='PAYOUTS', kicker=IP, top=(255, 200, 40), bottom=(242, 118, 0), ink=(88, 38, 0), tint=(255, 246, 196), block='gold_block',
         left=('gold_ingot', 116, -1), right=('gold_ingot', 116, 1)),
    dict(word='EVENTS', kicker=IP, top=(244, 92, 226), bottom=(128, 40, 214), ink=(58, 8, 74), tint=(255, 222, 252), block='tnt_side',
         left=('firework_rocket', 120, -1), right=('firework_rocket', 120, 1), confetti=True),
    dict(word=IP, kicker='JOIN NOW', top=(64, 196, 255), bottom=(28, 84, 222), ink=(8, 34, 92), tint=(216, 242, 255), block='diamond_block',
         left=('diamond_sword', 112, -1), right=('diamond_sword', 112, 1)),
]
CENTER = (318, W - 8)                       # area to the right of the logo block

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_back(t):
    t = min(max(t, 0), 1); c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

# ------------------------------------------------------------------ text layers (drawn at 2x, scaled per frame)
def text_layer(text, font_path, size, top, bottom, ink, stroke, shadow_dy, ss=2):
    f = ImageFont.truetype(font_path, size * ss)
    tmp = ImageDraw.Draw(Image.new('L', (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke * ss)
    pad = 6 * ss
    w, h = r - l + 2 * pad, b - t + 2 * pad + shadow_dy * ss
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ox, oy = pad - l, pad - t
    # drop shadow: the outlined shape, darker, pushed down
    sh = Image.new('L', (w, h), 0)
    ImageDraw.Draw(sh).text((ox, oy + shadow_dy * ss), text, font=f, fill=255, stroke_width=stroke * ss, stroke_fill=255)
    img.paste(tuple(int(c * .55) for c in ink) + (255,), (0, 0), sh)
    # outline
    ol = Image.new('L', (w, h), 0)
    ImageDraw.Draw(ol).text((ox, oy), text, font=f, fill=255, stroke_width=stroke * ss, stroke_fill=255)
    img.paste(ink + (255,), (0, 0), ol)
    # fill: vertical gradient, light top to tinted bottom, with a bright upper half
    fm = Image.new('L', (w, h), 0)
    ImageDraw.Draw(fm).text((ox, oy), text, font=f, fill=255)
    bb = fm.getbbox()
    grad = Image.new('RGBA', (w, h))
    gp = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        k = 0 if y < bb[1] else min(1, (y - bb[1]) / max(1, bb[3] - bb[1]))
        k = 0 if k < .45 else (k - .45) / .55
        gp[y, :, :3] = [int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)]
        gp[y, :, 3] = 255
    grad = Image.fromarray(gp, 'RGBA')
    img.paste(grad, (0, 0), fm)
    return img.resize((w // ss, h // ss), Image.LANCZOS)

def fit_layer(text, font_path, size, max_w, **kw):
    while True:
        lay = text_layer(text, font_path, size, **kw)
        if lay.width <= max_w or size <= 20: return lay
        size -= 2

# ------------------------------------------------------------------ static assets
PROPS = {p: Image.open(A / 'props' / f'{p}.png').convert('RGBA') for p in
         {pp[k][0] for pp in PANELS for k in ('left', 'right')}}
PROPS = {k: v.crop(v.getbbox()) for k, v in PROPS.items()}
def outlined(name, size, ink=(18, 10, 4), by='height'):
    """A 3D render from props/, scaled, with the same dark outline the props get."""
    im = Image.open(A / 'props' / f'{name}.png').convert('RGBA')
    im = im.crop(im.getbbox())
    if by == 'height': im = im.resize((round(im.width * size / im.height), size), Image.LANCZOS)
    else: im = im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
    pad = 6
    base = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new('L', base.size, 0); a.paste(im.getchannel('A'), (pad, pad))
    ring = a.filter(ImageFilter.MaxFilter(7)).point(lambda v: 255 if v > 90 else int(v * 2.8))
    base.paste(ink + (255,), (0, 0), ring)
    base.alpha_composite(im, (pad, pad))
    return base

# the logo, drawn the same way as the props: a voxel gold coin with a diamond-cyan X, and "MineX" as extruded
# gold voxel letters in the game's font (textures from tools/props-3d/make_logo_textures.py)
COIN = outlined('minex_coin', 106)

HEAD = []
for p in PANELS:
    max_w = 520 if p['word'] != IP else 560
    HEAD.append(fit_layer(p['word'], LUCKY, 74, max_w, top=(255, 250, 206), bottom=(255, 168, 16), ink=p['ink'], stroke=6, shadow_dy=6))
def tag(text, ink):
    t = text_layer(text, BUNGEE, 15, top=(255, 255, 255), bottom=(255, 255, 255), ink=ink, stroke=0, shadow_dy=0)
    w, h = t.width + 14, t.height + 2
    im = Image.new('RGBA', (w + 4, h + 6), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 4, w + 2, h + 4], h // 2, fill=(0, 0, 0, 120))
    d.rounded_rectangle([0, 0, w, h], h // 2, fill=ink + (255,), outline=(255, 255, 255, 230), width=2)
    im.alpha_composite(t, (7, (h - t.height) // 2 + 1))
    return im
KICK = [tag(p['kicker'], p['ink']) for p in PANELS]
WORDMARK = outlined('minex_wordmark', 178, by='width')

def badge():
    t = text_layer('PREMIUM + CRACKED', BUNGEE, 15, top=(70, 36, 0), bottom=(70, 36, 0), ink=(255, 214, 90), stroke=0, shadow_dy=0)
    w, h = t.width + 16, t.height + 4
    im = Image.new('RGBA', (w + 6, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 4, w + 4, h + 6], 7, fill=(40, 20, 4, 255))
    d.rounded_rectangle([2, 2, w + 2, h + 2], 6, fill=(255, 176, 20, 255), outline=(40, 20, 4, 255), width=2)
    d.rounded_rectangle([4, 4, w, h // 2 + 2], 5, fill=(255, 214, 90, 255))
    im.alpha_composite(t, (10, (h - t.height) // 2 + 3))
    return im
BADGE = badge()

# ------------------------------------------------------------------ backgrounds
YY = np.linspace(0, 1, H)[:, None, None]
XX = np.arange(W)[None, :, None]
BLOCKS = {p['block']: np.asarray(Image.open(A / 'blocks' / f"{p['block']}.png").convert('RGB').resize((48, 48), Image.NEAREST), np.float32) / 255 for p in PANELS}
def background(i, f):
    p = PANELS[i]
    top = np.array(p['top'], np.float32); bot = np.array(p['bottom'], np.float32)
    col = top * (1 - YY) + bot * YY
    shift = int(round(48 * 2 * f / N))                       # wall scrolls two blocks per loop, so it wraps
    tile = np.tile(BLOCKS[p["block"]], (H // 48 + 1, W // 48 + 4, 1))[:H, shift:shift + W]
    lum = tile.mean(axis=2, keepdims=True)
    img = col * (0.68 + 0.52 * lum)                          # the block's texture, in the panel colour
    img = img * 0.82 + col * 0.18
    # rotating rays behind the headline: 14 rays, a full 1/14 turn per loop, so they wrap
    cx = (CENTER[0] + CENTER[1]) / 2
    ang = np.arctan2(np.arange(H)[:, None] - 70, XX[..., 0] - cx) + 2 * math.pi / 14 * f / N
    ray = (np.sin(ang * 14) > 0.25).astype(np.float32)[..., None]
    dist = np.sqrt(((XX[..., 0] - cx) / 380.0) ** 2 + ((np.arange(H)[:, None] - 70) / 110.0) ** 2)[..., None]
    img = img + ray * np.clip(1 - dist, 0, 1) * 70
    img = img + np.clip(1 - dist * 1.6, 0, 1) * 40
    edge = np.clip((np.abs(XX[..., 0] - W / 2) / (W / 2) - 0.72) / 0.28, 0, 1)[..., None]
    img = img * (1 - 0.30 * edge)
    return np.clip(img, 0, 255)

SPARKS = [(random.Random(s).uniform(330, W - 20), random.Random(s + 99).uniform(10, H - 10), random.Random(s + 7).randrange(N)) for s in range(16)]
def draw_sparkles(img, f):
    d = ImageDraw.Draw(img)
    for x, y, ph in SPARKS:
        k = ((f + ph) % 34) / 34.0
        s = max(0, math.sin(k * math.pi)) * 7
        if s < 1: continue
        a = int(220 * s / 7)
        d.polygon([(x, y - s), (x + s * .28, y), (x, y + s), (x - s * .28, y)], fill=(255, 255, 255, a))
        d.polygon([(x - s, y), (x, y - s * .28), (x + s, y), (x, y + s * .28)], fill=(255, 255, 255, a))

CONF = [(random.Random(s).uniform(330, W - 10), random.Random(s + 1).uniform(0, H), random.Random(s + 2).choice([(255, 238, 90), (120, 230, 255), (255, 120, 120), (140, 255, 140), (255, 255, 255)]), random.Random(s + 3).uniform(0, 6.28)) for s in range(36)]
def draw_confetti(img, t):
    d = ImageDraw.Draw(img)
    for x, y0, c, ph in CONF:
        y = (y0 + t * 2.4) % (H + 10) - 5
        xx = x + 6 * math.sin(ph + t * .25)
        w = 3 + 2 * abs(math.sin(ph + t * .3))
        d.rectangle([xx, y, xx + w, y + 3], fill=c + (230,))

# ------------------------------------------------------------------ panel and frame
_PROP_CACHE = {}
def prop_image(name, height, flip, angle, ink):
    """Prop scaled to height, with a 3px outline in the panel's ink colour (like the headline)."""
    key = (name, height, flip, ink)
    if key not in _PROP_CACHE:
        im = PROPS[name]
        im = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
        if flip < 0: im = ImageOps.mirror(im)
        pad = 6
        base = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        a = Image.new('L', base.size, 0); a.paste(im.getchannel('A'), (pad, pad))
        ring = a.filter(ImageFilter.MaxFilter(7)).point(lambda v: 255 if v > 90 else int(v * 2.8))
        base.paste(ink + (255,), (0, 0), ring)
        base.alpha_composite(im, (pad, pad))
        _PROP_CACHE[key] = base
    return _PROP_CACHE[key].rotate(angle, resample=Image.BICUBIC, expand=True)

def panel(i, t, f):
    """Render panel i, t frames after it started (t large = settled)."""
    p = PANELS[i]
    img = Image.fromarray(background(i, f).astype(np.uint8)).convert('RGBA')
    draw_sparkles(img, f)
    if p.get('confetti'): draw_confetti(img, f)
    cx = (CENTER[0] + CENTER[1]) // 2
    # props: slide in from outside, then bob and sway
    slide = 0
    grow = ease_back(t / 10) if t < 10 else 1.0
    for side, sgn in (('left', -1), ('right', 1)):
        name, hgt, flip = p[side]
        bob = 5 * math.sin(2 * math.pi * f / 42.5 + (0 if side == 'left' else 2.1))
        ang = 5 * math.sin(2 * math.pi * f / 85 + (1.2 if side == 'left' else 0)) - sgn * 360 * (1 - ease_out(t / 10))
        hgt = max(8, int(hgt * max(0.05, grow)))
        im = prop_image(name, hgt, flip, ang, p['ink'])
        hw = HEAD[i].width // 2
        px = cx + sgn * (hw + 18 + im.width // 2) + sgn * slide - im.width // 2
        px = int(min(max(px, CENTER[0] - 6), W - im.width + 6))
        py = int((H - im.height) / 2 + bob)
        img.alpha_composite(im, (px, py)) if 0 <= px <= W else None
    # kicker
    hd = HEAD[i]
    drop = (1 - ease_back(t / 11)) * -120 if t < 11 else 0
    hy = int(62 - hd.height // 2 + drop)
    img.alpha_composite(hd, (cx - hd.width // 2, hy))
    k = KICK[i]
    ky = H - k.height - 6 + (1 - ease_out((t - 4) / 6)) * 40 if t >= 4 else H + 10
    if ky < H: img.alpha_composite(k, (cx - k.width // 2, int(ky)))
    return img

def logo_block(img, f):
    # dark plate so the logo reads on every colour
    plate = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(plate)
    d.polygon([(0, 0), (300, 0), (276, H), (0, H)], fill=(12, 10, 20, 205))
    d.line([(300, 0), (276, H)], fill=(255, 255, 255, 60), width=3)
    img.alpha_composite(plate)
    coin = COIN
    p = f % 85
    if p < 16:                                   # a shine sweeps across the coin twice a loop
        sh = Image.new('L', coin.size, 0); ds = ImageDraw.Draw(sh)
        x = -40 + p * 10
        ds.polygon([(x, 0), (x + 16, 0), (x - 24, coin.height), (x - 40, coin.height)], fill=150)
        sh = Image.composite(sh, Image.new('L', coin.size, 0), coin.getchannel('A'))
        coin = coin.copy(); coin.alpha_composite(Image.merge('RGBA', (Image.new('L', coin.size, 255),) * 3 + (sh,)))
    img.alpha_composite(coin, (12, (H - coin.height) // 2))
    img.alpha_composite(WORDMARK, (116, 8))
    img.alpha_composite(BADGE, (126, 8 + WORDMARK.height + 1))

def render(f):
    cur = max(i for i, s in enumerate(STARTS) if s <= f)
    t = f - STARTS[cur]
    img = panel(cur, t, f)
    if t < WIPE:                                 # diagonal wipe: the new panel sweeps in from the right
        prev = panel((cur - 1) % 4, 99, f)
        mask = Image.new('L', (W, H), 0); d = ImageDraw.Draw(mask)
        flash = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(flash)
        bars, bw = 10, W / 10
        for k in range(bars):
            p = min(1, max(0, (t + 1) / WIPE * 1.8 - k * 0.08))
            h = H * ease_out(p)
            x0 = k * bw
            d.rectangle([x0, (H - h) / 2, x0 + bw, (H + h) / 2], fill=255)
            if 0 < p < 1: dl.rectangle([x0, (H - h) / 2 - 3, x0 + bw, (H - h) / 2], fill=(255, 255, 255, 220)); dl.rectangle([x0, (H + h) / 2, x0 + bw, (H + h) / 2 + 3], fill=(255, 255, 255, 220))
        mixed = prev.copy(); mixed.paste(img, (0, 0), mask)
        mixed.alpha_composite(flash)
        img = mixed
    logo_block(img, f)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=(10, 8, 16, 255), width=3)
    return img.convert('RGB')

if __name__ == '__main__':
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    last = int(sys.argv[5]) if len(sys.argv) > 5 else N
    for f in range(first - 1, last):
        render(f).save(OUT / f'f{f + 1:03d}.png')
    print('ok', first, last)
