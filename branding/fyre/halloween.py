"""Halloween layer for the Fyre banner: moon, mist, jack-o'-lanterns, mobs, logo glow.

Every position is in 960x540 space and scaled by f = W/960, so both output
sizes line up. Positions are tied to fyre-background.webp at --bg-top 0.2.
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageChops

PUMPKIN = ["..g..",
           "oOOOo",
           "OYOYO",
           "OOOOO",
           "OYYYO",
           "oOOOo"]
BAT = ["X.......X",
       "XX..X..XX",
       ".XXXXXXX.",
       "..XX.XX..",
       "...X.X..."]
GHAST = [".WWWWWWW.",
         "WWWWWWWWW",
         "WEEWWWEEW",
         "WWWWWWWWW",
         "WWWMMMWWW",
         "WWWWWWWWW",
         ".WWWWWWW.",
         ".T.T.T.T.",
         ".T.T...T.",
         "...T....."]
WITHER = [".HHHH..",
          ".HeHe..",
          ".HHHH..",
          "..BB..S",
          ".ABBA.S",
          "A.BB.AS",
          "..BB...",
          ".L..L..",
          ".L..L..",
          ".L..L.."]
COLORS = {
    'g': (70,120,30), 'O': (232,120,18), 'o': (176,78,10), 'Y': (255,232,96),
    'X': (16,6,14),
    'W': (236,236,236), 'E': (40,40,40), 'M': (90,90,90), 'T': (205,205,205),
    'H': (58,58,62), 'e': (10,10,10), 'B': (38,38,42), 'A': (48,48,52),
    'L': (44,44,48), 'S': (140,140,150),
}

def sprite(d, rows, cx, cy, block):
    w, h = len(rows[0]) * block, len(rows) * block
    x0, y0 = round(cx - w/2), round(cy - h/2)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in COLORS:
                d.rectangle([x0 + i*block, y0 + j*block, x0 + (i+1)*block - 1, y0 + (j+1)*block - 1], COLORS[ch])

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

    # blood moon behind the castle, veiled by smoke; painted only where the pixel is bright sky,
    # so the towers stay in front
    mx, my, mr = 470*f, 226*f, 48*f
    moon = render_moon(W, H, mx, my, mr)
    r, g, b = base.split()
    sky = ImageChops.subtract(r, b).point(lambda v: 255 if v > 95 else int(v * 2.6))
    sky = ImageChops.multiply(sky, base.convert('L').point(lambda v: 255 if v > 70 else v * 3))
    sky = sky.filter(ImageFilter.GaussianBlur(.8*f))
    smoke = Image.new('L', (24, 14))
    smoke.putdata([rng.randrange(256) for _ in range(24*14)])
    smoke = smoke.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(10*f))
    veil = smoke.point(lambda v: int(255 - .5 * max(0, v - 90)))
    mask = ImageChops.multiply(ImageChops.multiply(moon.getchannel('A'), sky), veil)
    halo = Image.new('L', (W, H))
    ImageDraw.Draw(halo).ellipse([mx - 1.7*mr, my - 1.7*mr, mx + 1.7*mr, my + 1.7*mr], 110)
    halo = ImageChops.multiply(halo.filter(ImageFilter.GaussianBlur(28*f)), sky)
    base = ImageChops.screen(base, Image.composite(Image.new('RGB', (W, H), (190,70,30)), Image.new('RGB', (W, H)), halo))
    base = Image.composite(moon.convert('RGB'), base, mask)

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
        (370, 275, 2), (436, 275, 2),          # ledge under the left centre tower's windows
        (500, 282, 2), (563, 282, 2),          # ledge under the right centre tower's windows
        (580, 220, 2), (637, 220, 2),          # ledge on the tall right tower
        (230, 184, 2), (262, 184, 2),          # ledge under the left tower's windows
        (300, 244, 2), (340, 244, 2),          # left wall top
        (900, 212, 2),                         # far right wall
        (470, 313, 3),                         # gate wall, centre
    ]
    base = glow(base, [(x, y - 6, .45 * k) for x, y, k in lanterns], f)
    d = ImageDraw.Draw(base)
    for x, y, k in lanterns:
        b = round(k * f)
        sprite(d, PUMPKIN, x*f, y*f - len(PUMPKIN) * b / 2, b)

    # wither skeletons on the battlements, a ghast in the haze, bats across the sky
    for x, y in ((326,226), (690,220)):
        sprite(d, WITHER, x*f, y*f, round(3*f))
    sprite(d, GHAST, 664*f, 196*f, round(3*f))
    for x, y, s in ((300,190,3), (352,206,2), (448,204,3), (500,236,2), (580,176,2),
                    (430,14,2), (560,10,3), (700,22,2), (905,140,2), (250,212,2)):
        sprite(d, BAT, x*f, y*f, round(s*f))
    return base

def logo_halo(base, im, pos, pad, W):
    """Pumpkin-orange glow outside a tight dark edge, in place of the plain dark halo."""
    a = Image.new('L', (im.width + 2*pad, im.height + 2*pad))
    a.paste(im.getchannel('A'), (pad, pad))
    wide = a.filter(ImageFilter.MaxFilter(2*(W//160)+1)).filter(ImageFilter.GaussianBlur(W/55))
    base.paste((255,120,20), (pos[0]-pad, pos[1]-pad), wide.point(lambda v: int(v * .75)))
    tight = a.filter(ImageFilter.MaxFilter(2*(W//480)+1)).filter(ImageFilter.GaussianBlur(W/240))
    base.paste((12,2,3), (pos[0]-pad, pos[1]-pad), tight.point(lambda v: int(v * .9)))

def render_moon(W, H, mx, my, mr):
    """A hazy blood moon: warm limb-darkened disk, faint low-contrast seas, no outlines."""
    S = int(mr * 2) + 2
    r = random.Random(5)
    small = Image.new('L', (12, 12))
    small.putdata([r.randrange(256) for _ in range(144)])
    tex = small.resize((S, S), Image.BICUBIC).filter(ImageFilter.GaussianBlur(S * .03)).load()
    maria = Image.new('L', (S, S))
    md = ImageDraw.Draw(maria)
    for cx, cy, rx, ry in ((.36,.34,.18,.14), (.56,.30,.13,.12), (.62,.50,.15,.11),
                           (.40,.60,.10,.08), (.28,.48,.08,.07)):
        md.ellipse([(cx-rx)*S, (cy-ry)*S, (cx+rx)*S, (cy+ry)*S], 255)
    maria = maria.filter(ImageFilter.GaussianBlur(S * .06)).load()
    img = Image.new('RGBA', (S, S))
    px = img.load()
    c = S / 2
    for y in range(S):
        for x in range(S):
            dx, dy = (x - c) / mr, (y - c) / mr
            d = math.sqrt(dx*dx + dy*dy)
            if d > 1:
                continue
            z = math.sqrt(1 - d*d)
            t = .5 + .5 * z ** .7
            col = lerp3((196,64,36), (255,168,104), t)                 # deep red rim to amber centre
            k = (1 - .16 * maria[x, y] / 255) * (.95 + .1 * (tex[x, y] / 255 - .5))
            alpha = int(255 * min(1, (1 - d) * 18))                    # soft anti-aliased edge
            px[x, y] = tuple(min(255, int(ch * k)) for ch in col) + (alpha,)
    full = Image.new('RGBA', (W, H))
    full.paste(img, (int(mx - c), int(my - c)))
    return full

def lerp3(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
