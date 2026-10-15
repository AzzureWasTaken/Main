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

def sprite(d, rows, cx, cy, block):
    w, h = len(rows[0]) * block, len(rows) * block
    x0, y0 = round(cx - w/2), round(cy - h/2)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in COLORS:
                d.rectangle([x0 + i*block, y0 + j*block, x0 + (i+1)*block - 1, y0 + (j+1)*block - 1], COLORS[ch])

MOBS = Path(__file__).with_name('mobs')

def mob(base, name, x, y, scale, anchor='center', rim=False):
    """Paste a mob sprite; whole-number scales stay pixel-crisp, fractional ones are smoothed."""
    im = Image.open(MOBS / f'{name}.png').convert('RGBA')
    size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    whole = abs(scale - round(scale)) < 1e-6
    im = im.resize(size, Image.NEAREST if whole else Image.LANCZOS)
    top = y - im.height if anchor == 'bottom' else y - im.height / 2
    pos = (round(x - im.width / 2), round(top))
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
    halo = Image.new('L', (W, H))
    R = size * 1.9
    ImageDraw.Draw(halo).ellipse([mx - R, my - R, mx + R, my + R], 210)
    halo = ImageChops.multiply(halo.filter(ImageFilter.GaussianBlur(size * .55)), sky.filter(ImageFilter.GaussianBlur(2*f)))
    base = ImageChops.screen(base, Image.composite(Image.new('RGB', (W, H), (235,225,205)), Image.new('RGB', (W, H)), halo))
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
        (230, 184, 2), (262, 184, 2),          # ledge under the left tower's windows
        (295, 244, 2),                         # left wall top
        (370, 275, 2), (436, 275, 2),          # ledge under the left centre tower's windows
        (470, 313, 3),                         # gate wall, centre
        (500, 282, 2), (563, 282, 2),          # ledge under the right centre tower's windows
        (580, 220, 2), (637, 220, 2),          # ledge on the tall right tower
        (772, 300, 2), (812, 300, 2),          # base of the big right tower
        (866, 214, 2),                         # far right wall
    ]
    base = glow(base, [(x, y - 6, .45 * k) for x, y, k in lanterns], f)
    d = ImageDraw.Draw(base)
    for x, y, k in lanterns:
        b = round(k * f)
        sprite(d, PUMPKIN, x*f, y*f - len(PUMPKIN) * b / 2, b)

    # mobs built from Minecraft's own textures (see mobs/README.md), spread across the width:
    # wither skeletons standing on ledges (x, surface y), the ghast in the lava-lit top corner,
    # bats in the bright sky bands (x, y, scale)
    for x, y in ((75, 162), (330, 244), (608, 220), (905, 213)):
        mob(base, 'wither_skeleton', x*f, y*f, f, anchor='bottom', rim=True)
    mob(base, 'ghast', 895*f, 75*f, 1.5*f)
    for x, y, s in ((50,95,.5), (215,18,.75), (400,10,.5), (610,22,.75), (770,12,.5),
                    (945,135,.5), (345,200,.75), (425,232,.5), (535,198,.5), (690,192,.75)):
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

# The Minecraft full moon, 8x8: pale face, grey craters, darker right edge and base.
MOON = ["LLLLLLMM",
        "LDDLLLMM",
        "LDLDLWMM",
        "LDDDLLMD",
        "LLLDLLMM",
        "WLDDLLLM",
        "LLLLLLMM",
        "MMMMDMMD"]
MOON_COLORS = {'L': (224,224,228), 'W': (246,246,250), 'M': (172,172,180), 'D': (124,124,134)}

def render_moon(W, H, mx, my, size):
    """The square Minecraft moon, crisp block pixels, as an RGBA layer."""
    full = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(full)
    b = size / 8
    x0, y0 = mx - size/2, my - size/2
    for j, row in enumerate(MOON):
        for i, ch in enumerate(row):
            d.rectangle([round(x0 + i*b), round(y0 + j*b), round(x0 + (i+1)*b) - 1, round(y0 + (j+1)*b) - 1],
                        MOON_COLORS[ch] + (255,))
    return full
