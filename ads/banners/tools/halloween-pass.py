"""Halloween pass for the 962x124 MineX server-list banner.

    python3 -I hbanner.py FRAMES_IN FRAMES_OUT [first last]

Dusk colour grade, Minecraft jack-o'-lanterns along the bottom edge, two bats crossing the top margin and a
slow mist. Everything is periodic over the 170-frame loop, so the GIF loops seamlessly.
"""
import sys, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

IN, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
T0 = int(sys.argv[3]) if len(sys.argv) > 3 else 1
T1 = int(sys.argv[4]) if len(sys.argv) > 4 else 170
W, H, N = 962, 124, 170
BAT = Image.open(Path(__file__).resolve().parents[3] / 'branding' / 'fyre' / 'mobs' / 'bat.png').convert('RGBA')  # Minecraft bat texture, see branding/fyre/mobs/README.md

PUMPKIN = ["..g..", "oOOOo", "OYOYO", "OOOOO", "OYYYO", "oOOOo"]
PCOL = {'g': (70,120,30), 'O': (232,120,18), 'o': (176,78,10), 'Y': (255,232,96)}

def pumpkin_layer(spots):
    """spots: (center x, bottom y, block px). Returns an RGBA layer with 1px dark outlines."""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for cx, by, b in spots:
        x0 = round(cx - len(PUMPKIN[0]) * b / 2); y0 = by - len(PUMPKIN) * b
        for j, row in enumerate(PUMPKIN):
            for i, ch in enumerate(row):
                if ch in PCOL: d.rectangle([x0+i*b-1, y0+j*b-1, x0+(i+1)*b, y0+(j+1)*b], (44, 4, 8))
        for j, row in enumerate(PUMPKIN):
            for i, ch in enumerate(row):
                if ch in PCOL: d.rectangle([x0+i*b, y0+j*b, x0+(i+1)*b-1, y0+(j+1)*b-1], PCOL[ch])
    return np.asarray(lay).astype(np.float32) / 255

PUMPKINS = pumpkin_layer([(122, 114, 4), (180, 114, 3), (900, 114, 3)])

def bat_frame(flap, scale):
    """Spread-wing bat; flap in [-1, 1] raises or lowers the wing tips."""
    w, h = BAT.size
    im = BAT.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    # lighten the dark-brown texture so it reads on a dark panel, and give it a 1px dark outline
    rgb = np.clip(np.asarray(im.convert('RGB')).astype(np.float32) * 1.9 + 18, 0, 255).astype(np.uint8)
    alpha = im.getchannel('A')
    ring = alpha.filter(ImageFilter.MaxFilter(3))
    base = Image.new('RGBA', im.size, (24, 8, 30, 0)); base.putalpha(ring)
    base.alpha_composite(Image.merge('RGBA', (*Image.fromarray(rgb).split(), alpha)))
    im = base
    a = np.asarray(im); out = np.zeros((im.height + 8, im.width, 4), np.uint8)
    cx = im.width / 2
    for x in range(im.width):
        dy = int(round(flap * 4 * abs(x - cx) / cx))      # wing tips rise (negative) or drop (positive)
        out[4 + dy: 4 + dy + im.height, x] = a[:, x]
    return out

FLAP = [-1, -.3, .6, -.3]
BAT_FRAMES = [bat_frame(f, 1.0) for f in FLAP]
BATS = [dict(x0=-40, dirn=1, y=12, amp=3, phase=0, off=0), dict(x0=W + 40, dirn=-1, y=109, amp=3, phase=2, off=85)]

def bat_layer(t):
    lay = np.zeros((H, W, 4), np.float32)
    for b in BATS:
        tt = (t + b['off']) % N
        x = b['x0'] + b['dirn'] * (W + 80) * tt / N
        y = b['y'] + b['amp'] * math.sin(2 * math.pi * tt / N * 3 + b['phase'])
        fr = BAT_FRAMES[(t // 2 + b['phase']) % 4].astype(np.float32) / 255
        if b['dirn'] < 0: fr = fr[:, ::-1]
        h, w = fr.shape[:2]; x0, y0 = int(x - w / 2), int(y - h / 2)
        sx0, sy0 = max(0, -x0), max(0, -y0); ex, ey = min(W, x0 + w), min(H, y0 + h)
        if ex > max(x0, 0) and ey > max(y0, 0):
            part = fr[sy0: sy0 + ey - max(y0, 0), sx0: sx0 + ex - max(x0, 0)]
            region = lay[max(y0, 0): ey, max(x0, 0): ex]
            a = part[..., 3:]; region[:] = part * a + region * (1 - a)
    return lay

# mist: a tile that scrolls 3 px/frame, so it wraps exactly over the 170-frame loop
rng = np.random.default_rng(5)
TILE = 3 * N
noise = Image.fromarray((rng.random((8, TILE // 24)) * 255).astype(np.uint8)).resize((TILE, 36), Image.BICUBIC).filter(ImageFilter.GaussianBlur(5))
MIST = np.asarray(noise).astype(np.float32) / 255
MIST = np.tile(MIST, (1, 3))[:, : TILE + W]
fade = np.clip((np.arange(36) / 36.0) ** 1.4, 0, 1)[:, None]

def grade(f, t):
    """f: float RGB in [0,1], shape (H, W, 3)."""
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    lum = f.mean(axis=2)
    # blue-dominant background (sky) -> dusk gradient purple/orange; keep the coin (left) untouched
    blue = np.clip((b - np.maximum(r, g) * 1.0) * 4.0, 0, 1)
    blue[:, :100] = 0
    yy = np.linspace(0, 1, H)[:, None]
    sky = (np.array([95, 55, 150]) / 255.0)[None, None, :] * (1 - yy)[..., None] + (np.array([255, 140, 60]) / 255.0)[None, None, :] * yy[..., None]
    sky = sky * (0.55 + 0.6 * lum[..., None])
    f = f * (1 - blue[..., None]) + sky * blue[..., None]
    # green-dominant (grass, leaves) -> autumn orange / olive
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    green = np.clip((g - np.maximum(r, b) * 1.05) * 5.0, 0, 1)
    green[:, :100] = 0
    autumn = np.stack([g * 1.15 + .05, g * 0.62, g * 0.22], axis=2)
    f = f * (1 - green[..., None]) + autumn * green[..., None]
    # shadows pick up a purple tint, highlights stay as they are
    lum = f.mean(axis=2)
    shade = np.clip(1 - lum * 2.2, 0, 1)[..., None]
    f = f + shade * np.array([0.10, 0.02, 0.17])[None, None, :] * 0.9
    # purple vignette toward the left and right ends
    xx = np.linspace(-1, 1, W)[None, :, None]
    vig = np.clip(np.abs(xx) - 0.72, 0, 1) * 1.6
    f = f * (1 - vig * 0.35) + vig * 0.35 * np.array([0.22, 0.05, 0.30])[None, None, :]
    return np.clip(f, 0, 1)

def over(f, lay):
    a = lay[..., 3:]; return f * (1 - a) + lay[..., :3] * a

for t in range(T0, T1 + 1):
    f = np.asarray(Image.open(IN / f'f{t:03d}.png').convert('RGB')).astype(np.float32) / 255
    f = grade(f, t)
    # mist along the bottom of the panel
    sh = (3 * t) % TILE
    m = MIST[:, sh: sh + W] * fade * 0.30
    mist = np.zeros((H, W, 4), np.float32)
    mist[84:120, :, 0], mist[84:120, :, 1], mist[84:120, :, 2], mist[84:120, :, 3] = 0.62, 0.40, 0.85, m
    f = over(f, mist)
    f = over(f, PUMPKINS)
    f = over(f, bat_layer(t))
    Image.fromarray((f * 255 + .5).astype(np.uint8)).save(OUT / f'f{t:03d}.png')
print('ok', T0, T1)
