"""Halloween layer for the Fyre banner: moon, mist, jack-o'-lanterns, mobs, cobwebs.

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

    # moon behind the castle: painted only where the pixel is bright sky, so towers stay in front
    mx, my, mr = 470*f, 222*f, 46*f
    moon = Image.new('RGB', (W, H), (255,238,206))
    md = ImageDraw.Draw(moon)
    for cx, cy, r in ((-14,-10,9), (12,8,7), (-4,18,5), (16,-18,5)):
        md.ellipse([mx+cx*f-r*f, my+cy*f-r*f, mx+cx*f+r*f, my+cy*f+r*f], (226,206,176))
    disk = Image.new('L', (W, H))
    ImageDraw.Draw(disk).ellipse([mx-mr, my-mr, mx+mr, my+mr], 255)
    disk = disk.filter(ImageFilter.GaussianBlur(1.2*f))
    r, g, b = base.split()
    sky = ImageChops.subtract(r, b).point(lambda v: 255 if v > 95 else int(v * 2.6))
    sky = ImageChops.multiply(sky, base.convert('L').point(lambda v: 255 if v > 70 else v * 3))
    sky = sky.filter(ImageFilter.GaussianBlur(.8*f))
    base = glow(base, [(470, 222, 2.6)], f, (255,210,170), 30, .45)
    base = Image.composite(moon, base, ImageChops.multiply(disk, sky))

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

    # jack-o'-lanterns: small ones in the tower windows, larger on battlements, biggest on the gate
    windows = [(388,268), (410,268), (526,272), (548,272), (598,210), (628,210), (218,176), (240,176)]
    walls = [(302,240), (350,244), (642,234), (738,232), (880,208), (812,100)]
    gate = (470,312)
    base = glow(base, [(x, y, .55) for x, y in windows] + [(x, y, .8) for x, y in walls] + [(*gate, 1.4)], f)
    d = ImageDraw.Draw(base)
    for x, y in windows:
        sprite(d, PUMPKIN, x*f, y*f, round(2*f))
    for x, y in walls:
        sprite(d, PUMPKIN, x*f, (y-4)*f, round(3*f))
    sprite(d, PUMPKIN, gate[0]*f, gate[1]*f, round(5*f))

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

def cobwebs(base, box):
    """Cobwebs hanging off the logo's top-left and top-right corners."""
    W = base.size[0]
    f = W / 960
    x0, y0, x1, y1 = box
    layer = Image.new('RGBA', base.size)
    d = ImageDraw.Draw(layer)
    lw = max(1, round(1.2*f))
    col = (240,236,230,190)
    for cx, sx in ((x0 - 6*f, 1), (x1 + 6*f, -1)):
        cy = y0 - 6*f
        R = 70*f
        angles = [math.radians(a) for a in (4, 26, 48, 70, 88)]
        spokes = [(cx + sx*R*math.cos(a), cy + R*math.sin(a)) for a in angles]
        for p in spokes:
            d.line([(cx, cy), p], col, lw)
        for k in range(1, 5):
            t = k / 4.6
            ring = [(cx + (px-cx)*t, cy + (py-cy)*t) for px, py in spokes]
            for a, b in zip(ring, ring[1:]):
                mid = ((a[0]+b[0])/2 + sx*2.5*f*t, (a[1]+b[1])/2 - 2.5*f*t)
                d.line([a, mid, b], col, lw)
        # a spider dropping on a thread
        sx0, sy0 = cx + sx*40*f, cy + 40*f
        d.line([(sx0, sy0), (sx0, sy0 + 30*f)], col, lw)
        sprite_spider(d, sx0, sy0 + 34*f, f)
    base.paste(layer, (0, 0), layer)

def sprite_spider(d, x, y, f):
    b = max(1, round(2*f))
    body = (24,10,16)
    d.rectangle([x - 2*b, y - 2*b, x + 2*b, y + 2*b], body)
    d.rectangle([x - b, y - b, x - b + b//2, y - b + b//2], (220,30,30))
    d.rectangle([x + b//2, y - b, x + b, y - b + b//2], (220,30,30))
    for k in (-1, 0, 1):
        d.line([(x - 2*b, y + k*b), (x - 4*b, y + k*b + b)], body, max(1, b//2))
        d.line([(x + 2*b, y + k*b), (x + 4*b, y + k*b + b)], body, max(1, b//2))
