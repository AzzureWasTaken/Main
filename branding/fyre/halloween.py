"""Halloween layer for the Fyre banner: moon, mist, jack-o'-lanterns, mobs, logo glow.

Every position is in 960x540 space and scaled by f = W/960, so both output
sizes line up. Positions are tied to fyre-background.webp at --bg-top 0.2.
"""
import math, random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

PUMPKIN = ["..g..",
           "oOOOo",
           "OYOYO",
           "OOOOO",
           "OYYYO",
           "oOOOo"]
COLORS = {
    'g': (70,120,30), 'O': (232,120,18), 'o': (176,78,10), 'Y': (255,232,96),
}

def sprite(d, rows, cx, cy, block, outline=0, outline_color=(44,4,8)):
    w, h = len(rows[0]) * block, len(rows) * block
    x0, y0 = round(cx - w/2), round(cy - h/2)
    if outline:  # dilate every filled cell by `outline` px in a dark colour, then draw the fills over it
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in COLORS:
                    d.rectangle([x0 + i*block - outline, y0 + j*block - outline,
                                 x0 + (i+1)*block - 1 + outline, y0 + (j+1)*block - 1 + outline], outline_color)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in COLORS:
                d.rectangle([x0 + i*block, y0 + j*block, x0 + (i+1)*block - 1, y0 + (j+1)*block - 1], COLORS[ch])

MOBS = Path(__file__).with_name('mobs')
PLAYERS = Path(__file__).with_name('players')

# ---------------------------------------------------------------------------------------------
# Everything is built as transparent RGBA layers (see build_layers), so the banner generator and
# the interactive board (make-board.py, board/) composite exactly the same pieces.
# ---------------------------------------------------------------------------------------------

def over(layer, src, pos=(0, 0)):
    """Alpha-composite src (RGBA) onto layer (RGBA) with its top-left at pos, clipping at the edges."""
    x0, y0 = pos
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x1, y1 = min(layer.width, x0 + src.width), min(layer.height, y0 + src.height)
    if x1 <= max(x0, 0) or y1 <= max(y0, 0):
        return
    part = src.crop((sx0, sy0, sx0 + (x1 - max(x0, 0)), sy0 + (y1 - max(y0, 0))))
    layer.alpha_composite(part, (max(x0, 0), max(y0, 0)))

def over_color(layer, color, pos, mask):
    """Paint a solid colour through an L mask at pos."""
    src = Image.new('RGBA', mask.size, tuple(color) + (0,))
    src.putalpha(mask)
    over(layer, src, pos)

def place_render(layer, name, x, feet_y, ppu, f, src_ppu=9, ty=26, el=6, tx=0):
    """Paste a 3D player render (players/<name>.png, see players/README.md) so the point under the
    subject's origin lands on (x, feet_y). `ppu` is pixels per Minecraft unit at 960 wide."""
    im = Image.open(PLAYERS / f'{name}.png').convert('RGBA')
    W0, H0 = im.size
    ax = W0 / 2 + (0 - tx) * src_ppu
    ay = H0 / 2 + ty * src_ppu * math.cos(math.radians(el))
    s = ppu * f / src_ppu
    a = np.asarray(im).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:]                                   # premultiply so edges don't darken
    pm = Image.fromarray((a * 255).round().astype(np.uint8), 'RGBA')
    pm = pm.resize((round(W0 * s), round(H0 * s)), Image.LANCZOS)
    b = np.asarray(pm).astype(np.float32) / 255
    b[..., :3] = np.where(b[..., 3:] > 1e-3, b[..., :3] / np.maximum(b[..., 3:], 1e-3), 0)
    out = Image.fromarray((np.clip(b, 0, 1) * 255).round().astype(np.uint8), 'RGBA')
    over(layer, out, (round(x * f - ax * s), round(feet_y * f - ay * s)))

def sky_mask(ref):
    """255 where the background is bright open sky, 0 over stone."""
    r, g, b = ref.split()
    sky = ImageChops.subtract(r, b).point(lambda v: 255 if v > 95 else int(v * 2.6))
    return ImageChops.multiply(sky, ref.convert('L').point(lambda v: 255 if v > 70 else v * 3))

def mob(layer, name, x, y, scale, anchor='center', rim=False, behind=None, shadow=False, sky=None):
    """Paste a mob sprite; whole-number scales stay pixel-crisp, fractional ones are smoothed."""
    im = Image.open(MOBS / f'{name}.png').convert('RGBA')
    size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    whole = abs(scale - round(scale)) < 1e-6
    im = im.resize(size, Image.NEAREST if whole else Image.LANCZOS)
    top = y - im.height if anchor == 'bottom' else y - im.height / 2
    pos = (round(x - im.width / 2), round(top))
    if behind is not None:
        # standing behind a parapet: below its top line, stone stays in front of the mob
        sk = sky.crop((pos[0], pos[1], pos[0] + im.width, pos[1] + im.height))
        keep = Image.new('L', im.size, 255)
        cut = max(0, round(behind - pos[1]))
        keep.paste(sk.crop((0, cut, im.width, im.height)).point(lambda v: 255 if v > 120 else 0), (0, cut))
        im.putalpha(ImageChops.multiply(im.getchannel('A'), keep))
    if shadow:
        # soft contact shadow where the feet meet the ledge
        sh = Image.new('L', layer.size)
        w = im.width * .55
        ImageDraw.Draw(sh).ellipse([x - w, y - 2*scale, x + w, y + 2*scale], 170)
        over_color(layer, (8, 2, 3), (0, 0), sh.filter(ImageFilter.GaussianBlur(1.2*scale)))
    if rim:  # faint orange rim light so dark mobs read against dark stone
        pad = max(2, round(4 * scale))
        a = Image.new('L', (im.width + 2*pad, im.height + 2*pad))
        a.paste(im.getchannel('A'), (pad, pad))
        a = a.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5 * scale))
        over_color(layer, (255, 130, 40), (pos[0] - pad, pos[1] - pad), a.point(lambda v: int(v * .55)))
    over(layer, im, pos)

def blank(size):
    return Image.new('RGBA', size, (0, 0, 0, 0))

# positions are in 960x540 space, read off fyre-background.webp at --bg-top 0.2
PUMPKINS = [  # (x, surface y, block size)
    (35, 162, 2), (140, 162, 2),   # long ledge on the far-left castle
    (230, 184, 2),                 # ledge under the left tower's windows
    (295, 244, 2),                 # left wall top
    (385, 275, 2),                 # ledge under the left centre tower's windows
    (545, 282, 2),                 # ledge under the right centre tower's windows
    (610, 220, 2),                 # ledge on the tall right tower
    (662, 252, 2), (726, 235, 2),  # right-hand wall top
    (866, 214, 2),                 # far right wall
]
PUMPKIN_GATE = (470, 313, 3)       # gate wall, centre (the duel stands there when players are "on the bridge")
PUMPKIN_HILL = (772, 300, 2)       # base of the big right tower (the explorer stands there when players are "on the hill")
SKELETONS = [(80, 142, None), (466, 392, None), (702, 233, None), (897, 218, 212)]  # (x, feet y, parapet top y)
BATS = [(90,32,.8), (335,14,1.2), (560,16,.8), (815,34,1.2), (50,96,.8), (940,150,.8),
        (255,200,1.2), (650,196,1.2), (330,300,1.2), (610,318,.8), (205,360,1.2),
        (740,365,.8), (140,505,1.2), (500,503,.8), (830,505,1.2)]
GHAST = {'default': (915, 290, 874, 304),   # ghast x,y and its fireball x,y
         'hill': (940, 232, 909, 229)}      # moves up-right to give the duel room on the hill
PLAYER_SPOTS = {'hill': {'duel': (852, 312, 1.85), 'explorer': (768, 301, 2.0)},      # x, feet y, px per unit
                'bridge': {'duel': (470, 316, 2.0), 'explorer': (288, 399, 1.85)}}

def build_layers(ref, f):
    """Return {name: (RGBA layer, blend)} for every Halloween element, built against the clean
    background `ref` (RGB). blend is 'normal' or 'screen'. Layers are drawn in dict order."""
    W, H = ref.size
    rng = random.Random(31)
    L = {}
    sky = sky_mask(ref)
    sky_soft = sky.filter(ImageFilter.GaussianBlur(2*f))

    # the Minecraft moon behind the castle; painted only where the pixel is bright sky, so the
    # towers stay in front. A maroon veil makes the red disc stand out, plus a tight red rim glow.
    mx, my, size = 470*f, 226*f, 40*f
    veil = Image.new('L', (W, H))
    R = size * 2.4
    ImageDraw.Draw(veil).ellipse([mx - R, my - R, mx + R, my + R], 190)
    veil = ImageChops.multiply(veil.filter(ImageFilter.GaussianBlur(size * .7)), sky_soft)
    layer = blank((W, H)); over_color(layer, (74, 8, 12), (0, 0), veil); L['moon_veil'] = (layer, 'normal')
    rim = Image.new('L', (W, H))
    R = size * .8
    ImageDraw.Draw(rim).ellipse([mx - R, my - R, mx + R, my + R], 255)
    rim = ImageChops.multiply(rim.filter(ImageFilter.GaussianBlur(size * .28)), sky_soft)
    layer = blank((W, H)); over_color(layer, (214, 40, 28), (0, 0), rim); L['moon_rim'] = (layer, 'screen')
    moon = render_moon(W, H, mx, my, size)
    moon.putalpha(ImageChops.multiply(moon.getchannel('A'), sky))
    L['moon'] = (moon, 'normal')

    # purple and green mist low in the canyon
    W4, H4 = W // 8, H // 8
    noise = Image.new('L', (W4, H4))
    npx = noise.load()
    for y in range(H4):
        for x in range(W4):
            band = max(0, 1 - abs(y/H4 - .74) / .2)
            npx[x, y] = int(255 * band * (.35 + .65 * rng.random()))
    noise = noise.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(14*f))
    layer = blank((W, H)); over_color(layer, (150, 70, 210), (0, 0), noise.point(lambda v: int(v * .42)))
    gmask = Image.new('L', (W, H))
    gd = ImageDraw.Draw(gmask)
    for x, y, r in ((150,420,70), (520,400,60), (820,430,80)):
        gd.ellipse([(x-r)*f, (y-r*.45)*f, (x+r)*f, (y+r*.45)*f], 70)
    over_color(layer, (90, 220, 110), (0, 0), gmask.filter(ImageFilter.GaussianBlur(26*f)))
    L['mist'] = (layer, 'normal')

    # jack-o'-lanterns sitting on ledges and wall tops
    def pumpkins(pts):
        lay = blank((W, H)); d = ImageDraw.Draw(lay)
        for x, y, k in pts:
            b = round(k * f)
            sprite(d, PUMPKIN, x*f, y*f - len(PUMPKIN) * b / 2, b, outline=max(1, round(b / 2)))
        return (lay, 'normal')
    L['pumpkins'] = pumpkins(PUMPKINS)
    L['pumpkin_gate'] = pumpkins([PUMPKIN_GATE])
    L['pumpkin_hill'] = pumpkins([PUMPKIN_HILL])

    # two players sword-fighting and one exploring with a torch, on the hill or on the bridge
    for where, spots in PLAYER_SPOTS.items():
        for who, (x, y, ppu) in spots.items():
            lay = blank((W, H)); place_render(lay, who, x, y, ppu, f); L[f'{who}_{where}'] = (lay, 'normal')

    # wither skeletons standing behind battlements or on a ledge
    lay = blank((W, H))
    for x, y, wall in SKELETONS:
        mob(lay, 'wither_skeleton', x*f, y*f, 1.05*f, anchor='bottom', rim=True,
            behind=wall*f if wall else None, shadow=wall is None, sky=sky)
    L['skeletons'] = (lay, 'normal')

    # the ghast shooting a fireball: open mouth, fireball flying out toward the castle
    for key, (gx, gy, fx, fy) in GHAST.items():
        lay = blank((W, H))
        mob(lay, 'ghast_shooting', gx*f, gy*f, 2.4*f)
        mob(lay, 'fireball', fx*f, fy*f, 2.0*f)
        L[f'ghast_{key}'] = (lay, 'normal')

    # bats spread over the whole canvas
    lay = blank((W, H))
    for x, y, s in BATS:
        mob(lay, 'bat', x*f, y*f, s*f)
    L['bats'] = (lay, 'normal')
    return L

def composite(ref, layers, order):
    """Composite the named layers over `ref` (RGB) in the given order; returns RGB."""
    out = ref.convert('RGBA')
    for name in order:
        lay, blend = layers[name]
        if blend == 'screen':
            rgb = out.convert('RGB')
            solid = Image.new('RGB', rgb.size, SCREEN_COLORS[name])
            light = Image.composite(solid, Image.new('RGB', rgb.size), lay.getchannel('A'))
            out = ImageChops.screen(rgb, light).convert('RGBA')
        else:
            out.alpha_composite(lay)
    return out.convert('RGB')

SCREEN_COLORS = {'moon_rim': (214, 40, 28)}

def scene(base, players=False):
    """Apply the Halloween layers to the clean background `base` (RGB) and return RGB."""
    f = base.width / 960
    L = build_layers(base, f)
    where = 'hill' if players else None
    order = ['moon_veil', 'moon_rim', 'moon', 'mist', 'pumpkins', 'pumpkin_gate']
    if not players: order.append('pumpkin_hill')
    if players: order += ['duel_hill', 'explorer_hill']
    order += ['skeletons', 'ghast_hill' if players else 'ghast_default', 'bats']
    return composite(base, L, order)

def text_layer(path, size, width, top=None, bottom=None, spooky=False):
    """The logo or tagline image with its halo, as an RGBA layer. `spooky` swaps the dark shadow
    halo for a pumpkin-orange glow inside a tight dark edge."""
    W, H = size
    im = Image.open(path).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    y = top if top is not None else bottom - im.height
    pos = ((W - width) // 2, y)
    pad = W // 20
    a = Image.new('L', (im.width + 2*pad, im.height + 2*pad))
    a.paste(im.getchannel('A'), (pad, pad))
    layer = blank(size)
    at = (pos[0] - pad, pos[1] - pad)
    if spooky:
        wide = a.filter(ImageFilter.MaxFilter(2*(W//160)+1)).filter(ImageFilter.GaussianBlur(W/55))
        over_color(layer, (255, 120, 20), at, wide.point(lambda v: int(v * .75)))
        tight = a.filter(ImageFilter.MaxFilter(2*(W//480)+1)).filter(ImageFilter.GaussianBlur(W/240))
        over_color(layer, (12, 2, 3), at, tight.point(lambda v: int(v * .9)))
    else:
        halo = a.filter(ImageFilter.MaxFilter(2*(W//240)+1)).filter(ImageFilter.GaussianBlur(W/80))
        over_color(layer, (12, 2, 3), at, halo.point(lambda v: int(v * .85)))
    over(layer, im, pos)
    return layer

def shade_layer(size):
    """Darkens the bottom strip so the tagline reads over the lava glow."""
    W, H = size
    ys = np.arange(H, dtype=np.float32) / H
    t = np.clip((ys - .62) / .38, 0, None) * 1.4
    alpha = (190 * np.minimum(1, t)).astype(np.uint8)
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = 14, 3, 4
    arr[..., 3] = alpha[:, None]
    return Image.fromarray(arr, 'RGBA')

# The Minecraft full moon as a blood moon, 8x8: deep red face with a shaded right edge.
MOON = ["LLLLLLLM",
        "LWLLLLMM",
        "LLLLLLLM",
        "LLLWLLLM",
        "LLLLLLMM",
        "LWLLLLLM",
        "LLLLLLMM",
        "MLLLLLMM"]
MOON_COLORS = {'L': (228,44,36), 'W': (255,96,70), 'M': (150,24,28), 'D': (110,16,22)}

def render_moon(W, H, mx, my, size):
    """The square Minecraft moon, crisp block pixels, as an RGBA layer."""
    full = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(full)
    b = size / 8
    x0, y0 = mx - size/2, my - size/2
    o = max(2, round(size / 24))  # thin dark outline so the disc separates from the sky
    d.rectangle([round(x0) - o, round(y0) - o, round(x0 + size) - 1 + o, round(y0 + size) - 1 + o], (44,4,8,255))
    for j, row in enumerate(MOON):
        for i, ch in enumerate(row):
            d.rectangle([round(x0 + i*b), round(y0 + j*b), round(x0 + (i+1)*b) - 1, round(y0 + (j+1)*b) - 1],
                        MOON_COLORS[ch] + (255,))
    return full
