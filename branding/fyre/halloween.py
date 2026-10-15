"""Halloween layer for the Fyre banner: moon, mist, jack-o'-lanterns, mobs, logo glow.

Every position is in 960x540 space and scaled by f = W/960, so both output
sizes line up. Positions are tied to fyre-background.webp at --bg-top 0.2.
"""
import math, random
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

def sky_mask(base):
    """255 where the background is bright open sky, 0 over stone."""
    r, g, b = base.split()
    sky = ImageChops.subtract(r, b).point(lambda v: 255 if v > 95 else int(v * 2.6))
    return ImageChops.multiply(sky, base.convert('L').point(lambda v: 255 if v > 70 else v * 3))

def mob(base, name, x, y, scale, anchor='center', rim=False, behind=None, shadow=False):
    """Paste a mob sprite; whole-number scales stay pixel-crisp, fractional ones are smoothed."""
    im = Image.open(MOBS / f'{name}.png').convert('RGBA')
    size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    whole = abs(scale - round(scale)) < 1e-6
    im = im.resize(size, Image.NEAREST if whole else Image.LANCZOS)
    top = y - im.height if anchor == 'bottom' else y - im.height / 2
    pos = (round(x - im.width / 2), round(top))
    if behind is not None:
        # standing behind a parapet: below its top line, stone stays in front of the mob
        sky = sky_mask(base).crop((pos[0], pos[1], pos[0] + im.width, pos[1] + im.height))
        keep = Image.new('L', im.size, 255)
        cut = max(0, round(behind - pos[1]))
        keep.paste(sky.crop((0, cut, im.width, im.height)).point(lambda v: 255 if v > 120 else 0), (0, cut))
        im.putalpha(ImageChops.multiply(im.getchannel('A'), keep))
    if shadow:
        # soft contact shadow where the feet meet the ledge
        sh = Image.new('L', base.size)
        w = im.width * .55
        ImageDraw.Draw(sh).ellipse([x - w, y - 2*scale, x + w, y + 2*scale], 170)
        base.paste((8,2,3), (0, 0), sh.filter(ImageFilter.GaussianBlur(1.2*scale)))
    if rim:  # faint orange rim light so dark mobs read against dark stone
        pad = max(2, round(4 * scale))
        a = Image.new('L', (im.width + 2*pad, im.height + 2*pad))
        a.paste(im.getchannel('A'), (pad, pad))
        a = a.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5 * scale))
        base.paste((255,130,40), (pos[0] - pad, pos[1] - pad), a.point(lambda v: int(v * .55)))
    base.paste(im, pos, im)

def glow(base, pts, f, color=(255,140,30), radius=26, strength=.8):
    W, H = base.size
    m = Image.new('L', (W, H))
    d = ImageDraw.Draw(m)
    for x, y, r in pts:
        R = radius * r * f
        d.ellipse([x*f - R, y*f - R, x*f + R, y*f + R], int(255 * strength))
    m = m.filter(ImageFilter.GaussianBlur(radius * f * .6))
    light = Image.new('RGB', (W, H), color)
    return ImageChops.screen(base, Image.composite(light, Image.new('RGB', (W, H)), m))

def scene(base):
    W, H = base.size
    f = W / 960
    rng = random.Random(31)

    # the Minecraft moon behind the castle with a soft round glow; painted only where the
    # pixel is bright sky, so the towers stay in front
    mx, my, size = 470*f, 226*f, 40*f
    r, g, b = base.split()
    sky = ImageChops.subtract(r, b).point(lambda v: 255 if v > 95 else int(v * 2.6))
    sky = ImageChops.multiply(sky, base.convert('L').point(lambda v: 255 if v > 70 else v * 3))
    # deep maroon veil around the moon so the red disc stands out, then a tight red glow at its rim
    veil = Image.new('L', (W, H))
    R = size * 2.4
    ImageDraw.Draw(veil).ellipse([mx - R, my - R, mx + R, my + R], 190)
    veil = ImageChops.multiply(veil.filter(ImageFilter.GaussianBlur(size * .7)), sky.filter(ImageFilter.GaussianBlur(2*f)))
    base = Image.composite(Image.new('RGB', (W, H), (74,8,12)), base, veil)
    rim = Image.new('L', (W, H))
    R = size * .8
    ImageDraw.Draw(rim).ellipse([mx - R, my - R, mx + R, my + R], 255)
    rim = ImageChops.multiply(rim.filter(ImageFilter.GaussianBlur(size * .28)), sky.filter(ImageFilter.GaussianBlur(2*f)))
    base = ImageChops.screen(base, Image.composite(Image.new('RGB', (W, H), (214,40,28)), Image.new('RGB', (W, H)), rim))
    moon = render_moon(W, H, mx, my, size)
    base = Image.composite(moon.convert('RGB'), base, ImageChops.multiply(moon.getchannel('A'), sky))

    # purple and green mist low in the canyon
    W4, H4 = W // 8, H // 8
    noise = Image.new('L', (W4, H4))
    npx = noise.load()
    for y in range(H4):
        for x in range(W4):
            band = max(0, 1 - abs(y/H4 - .74) / .2)
            npx[x, y] = int(255 * band * (.35 + .65 * rng.random()))
    noise = noise.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(14*f))
    purple = Image.new('RGB', (W, H), (150,70,210))
    green = Image.new('RGB', (W, H), (90,220,110))
    base = Image.composite(purple, base, noise.point(lambda v: int(v * .42)))
    gmask = Image.new('L', (W, H))
    gd = ImageDraw.Draw(gmask)
    for x, y, r in ((150,420,70), (520,400,60), (820,430,80)):
        gd.ellipse([(x-r)*f, (y-r*.45)*f, (x+r)*f, (y+r*.45)*f], 70)
    base = Image.composite(green, base, gmask.filter(ImageFilter.GaussianBlur(26*f)))

    # jack-o'-lanterns sitting on real ledges and wall tops: (x, surface y, block size).
    # Surface heights were read off fyre-background.webp at --bg-top 0.2.
    lanterns = [
        (35, 162, 2), (140, 162, 2),           # long ledge on the far-left castle
        (230, 184, 2),                         # ledge under the left tower's windows
        (295, 244, 2),                         # left wall top
        (385, 275, 2),                         # ledge under the left centre tower's windows
        (470, 313, 3),                         # gate wall, centre
        (545, 282, 2),                         # ledge under the right centre tower's windows
        (610, 220, 2),                         # ledge on the tall right tower
        (662, 252, 2), (726, 235, 2),          # right-hand wall top
        (772, 300, 2),                         # base of the big right tower
        (866, 214, 2),                         # far right wall
    ]
    base = glow(base, [(x, y - 6, .45 * k) for x, y, k in lanterns], f)
    d = ImageDraw.Draw(base)
    for x, y, k in lanterns:
        b = round(k * f)
        sprite(d, PUMPKIN, x*f, y*f - len(PUMPKIN) * b / 2, b, outline=max(1, round(b / 2)))

    # mobs built from Minecraft's own textures (see mobs/README.md), spread across the width:
    # wither skeletons standing behind battlements or on a ledge, the ghast in the lava-lit top corner,
    # bats in the bright sky bands (x, y, scale)
    # (x, feet y, parapet top y or None for an open ledge)
    for x, y, wall in ((80, 142, None), (466, 392, None), (702, 233, None), (897, 218, 212)):
        mob(base, 'wither_skeleton', x*f, y*f, .8*f, anchor='bottom', rim=True,
            behind=wall*f if wall else None, shadow=wall is None)
    mob(base, 'ghast', 895*f, 75*f, 1.5*f)
    # two loose rows: the lava-lit strip above the logo and the open sky below it, plus the far edges.
    for x, y, s in ((150,22,.8), (290,10,1.2), (430,26,.8), (570,10,1.2), (705,26,.8), (850,12,1.2),
                    (50,95,.8), (265,198,1.0), (355,214,1.2), (560,190,.8), (690,200,1.2), (940,135,.8)):
        mob(base, 'bat', x*f, y*f, s*f)
    return base

def logo_halo(base, im, pos, pad, W):
    """Pumpkin-orange glow outside a tight dark edge, in place of the plain dark halo."""
    a = Image.new('L', (im.width + 2*pad, im.height + 2*pad))
    a.paste(im.getchannel('A'), (pad, pad))
    wide = a.filter(ImageFilter.MaxFilter(2*(W//160)+1)).filter(ImageFilter.GaussianBlur(W/55))
    base.paste((255,120,20), (pos[0]-pad, pos[1]-pad), wide.point(lambda v: int(v * .75)))
    tight = a.filter(ImageFilter.MaxFilter(2*(W//480)+1)).filter(ImageFilter.GaussianBlur(W/240))
    base.paste((12,2,3), (pos[0]-pad, pos[1]-pad), tight.point(lambda v: int(v * .9)))

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
