#!/usr/bin/env python3
"""Fyre still banner: a lava PvP scene in Minecraft pixel art.

Draws on a 240x135 grid and scales it up (nearest) to 960x540 and 1920x1080,
the Discord server-banner sizes. Text stays in the centre, which Discord
never crops. With --bg, the pixel text goes over a 16:9 crop of that image
instead of the drawn scene.

    python3 make-fyre-banner.py [--bg fyre-background.webp] [--logo fyre-logo.png] [--tagline fyre-tagline.png] [--sub "PVP TOURNAMENTS" --sub2 "AND MORE"]
"""
import argparse, math, random
from PIL import Image, ImageFilter

FONT = {  # 5x7 pixel glyphs
 'A':["01110","10001","10001","11111","10001","10001","10001"],
 'B':["11110","10001","10001","11110","10001","10001","11110"],
 'C':["01111","10000","10000","10000","10000","10000","01111"],
 'D':["11110","10001","10001","10001","10001","10001","11110"],
 'E':["11111","10000","10000","11110","10000","10000","11111"],
 'F':["11111","10000","10000","11110","10000","10000","10000"],
 'G':["01111","10000","10000","10011","10001","10001","01111"],
 'H':["10001","10001","10001","11111","10001","10001","10001"],
 'I':["11111","00100","00100","00100","00100","00100","11111"],
 'J':["00111","00010","00010","00010","00010","10010","01100"],
 'K':["10001","10010","10100","11000","10100","10010","10001"],
 'L':["10000","10000","10000","10000","10000","10000","11111"],
 'M':["10001","11011","10101","10101","10001","10001","10001"],
 'N':["10001","11001","10101","10011","10001","10001","10001"],
 'O':["01110","10001","10001","10001","10001","10001","01110"],
 'P':["11110","10001","10001","11110","10000","10000","10000"],
 'Q':["01110","10001","10001","10001","10101","10010","01101"],
 'R':["11110","10001","10001","11110","10100","10010","10001"],
 'S':["01111","10000","10000","01110","00001","00001","11110"],
 'T':["11111","00100","00100","00100","00100","00100","00100"],
 'U':["10001","10001","10001","10001","10001","10001","01110"],
 'V':["10001","10001","10001","10001","10001","01010","00100"],
 'W':["10001","10001","10001","10101","10101","10101","01010"],
 'X':["10001","10001","01010","00100","01010","10001","10001"],
 'Y':["10001","10001","01010","00100","00100","00100","00100"],
 'Z':["11111","00001","00010","00100","01000","10000","11111"],
 '0':["01110","10011","10101","10101","11001","10001","01110"],
 '1':["00100","01100","00100","00100","00100","00100","01110"],
 '2':["01110","10001","00001","00110","01000","10000","11111"],
 '3':["11110","00001","00001","01110","00001","00001","11110"],
 '4':["00010","00110","01010","10010","11111","00010","00010"],
 '5':["11111","10000","11110","00001","00001","10001","01110"],
 '6':["01110","10000","10000","11110","10001","10001","01110"],
 '7':["11111","00001","00010","00100","01000","01000","01000"],
 '8':["01110","10001","10001","01110","10001","10001","01110"],
 '9':["01110","10001","10001","01111","00001","00001","01110"],
 '.':["00000","00000","00000","00000","00000","00000","00100"],
 '-':["00000","00000","00000","01110","00000","00000","00000"],
 '!':["00100","00100","00100","00100","00100","00000","00100"],
 ':':["00000","00100","00000","00000","00000","00100","00000"],
 ' ':["00000"]*7,
}

def text_cells(text, s, gap=1):
    """Return list of (x,y) filled cells and total width for text at scale s."""
    cells, x = [], 0
    for ch in text.upper():
        g = FONT.get(ch, FONT[' '])
        w = 3 if ch == ' ' else len(g[0])
        for gy, row in enumerate(g):
            for gx, b in enumerate(row[:w]):
                if b == '1':
                    for dy in range(s):
                        for dx in range(s):
                            cells.append((x + gx*s + dx, gy*s + dy))
        x += (w + gap) * s
    return cells, x - gap*s

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

GW, GH = 240, 135
LAVA_Y = 112

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sub', default='PVP TOURNAMENTS')
    ap.add_argument('--sub2', default='AND MORE')
    ap.add_argument('--out', default='fyre-banner')
    ap.add_argument('--bg', help='background image; omit to draw the pixel scene')
    ap.add_argument('--logo', help='logo image to use in place of the pixel FYRE title')
    ap.add_argument('--tagline', help='tagline image to use in place of the --sub pixel line')
    ap.add_argument('--bg-top', type=float, default=.2, help='where the 16:9 crop starts, as a fraction of the image height')
    args = ap.parse_args()
    rng = random.Random(11)
    img = Image.new('RGBA' if args.bg else 'RGB', (GW, GH), (0,0,0,0))
    px = img.load()

    if not args.bg:
        # Nether air: dark at the top, glowing orange toward the lava
        for y in range(GH):
            t = y / LAVA_Y
            for x in range(GW):
                c = lerp((28,6,10), (150,42,16), t**1.6)
                px[x, y] = lerp(c, (0,0,0), rng.random()*.06)

        NR = [(97,37,37),(111,44,42),(83,30,32),(128,52,48),(70,24,27)]
        def rack(x, y, shade):
            c = NR[(x*7 + y*13 + (x//4)*(y//4)) % 5]
            c = lerp(c, NR[rng.randrange(5)], .5)
            if x % 4 == 0 or y % 4 == 0:
                c = lerp(c, (40,10,14), .3)
            return lerp(c, (20,5,8), shade)

        # far cliffs (hazy), then near cliffs at the edges, block-stepped like Minecraft
        def ridge(base, amp, freq, seed):
            r = random.Random(seed)
            ph = [r.random()*6.28 for _ in range(3)]
            return [int(base + amp*(math.sin(x*freq+ph[0]) + .5*math.sin(x*freq*2.3+ph[1]) + .3*math.sin(x*freq*5+ph[2])))//2*2
                    for x in range(GW)]
        far = ridge(78, 9, .045, 1)
        for x in range(GW):
            for y in range(far[x], LAVA_Y):
                px[x, y] = lerp(rack(x, y, .2), (150,50,24), .55)
        for x in range(GW):
            edge = min(x, GW-1-x)
            top = 40 + edge*0.9 + 6*math.sin(x*.21) if edge < 60 else GH
            top = int(top)//2*2
            for y in range(max(top, 0), LAVA_Y):
                px[x, y] = rack(x, y, .15 + .25*(1 - (y-top)/max(LAVA_Y-top, 1)) * .0)
        # lavafalls pouring off both cliffs
        for fx in (10, 21, GW-13, GW-24):
            edge = min(fx, GW-1-fx)
            top = int(40 + edge*0.9 + 6*math.sin(fx*.21))//2*2
            for y in range(top, LAVA_Y):
                for dx in range(3):
                    v = .5 + .5*math.sin(y*.5 + dx*1.7 + fx)
                    px[fx+dx, y] = lerp((215,70,10), (255,200,60), v)

        # ceiling of netherrack with glowstone clusters
        ceil = ridge(6, 4, .08, 3)
        for x in range(GW):
            for y in range(0, max(ceil[x], 0)):
                px[x, y] = rack(x, y, .35)
        for gx in (14, 70, 168, 222):
            for dx in range(-3, 4):
                for dy in range(0, 4 - abs(dx)//2):
                    y = ceil[gx] + dy
                    if 0 <= gx+dx < GW and (dx + dy) % 3 != 2:
                        px[gx+dx, y] = (255,226,140) if (dx*dy) % 2 == 0 else (214,160,70)

        # lava lake with waves and bright crests
        for y in range(LAVA_Y, GH):
            for x in range(GW):
                v = .5 + .5*math.sin(x/5 + y*1.1) * math.cos(x/11 - y*.4)
                v = .6*v + .4*rng.random()
                px[x, y] = lerp((185,48,8), (255,210,60), v)
        for x in range(GW):  # glowing shoreline
            px[x, LAVA_Y] = lerp(px[x, LAVA_Y], (255,240,150), .6)

        # obsidian arena platform in the middle of the lake
        PX0, PX1, PY = 62, 178, 106
        for y in range(PY, PY+8):
            for x in range(PX0 + (y-PY)//2, PX1 - (y-PY)//2):
                c = (24,14,38) if (x//4 + y//4) % 2 else (34,20,52)
                if (x*5 + y*3) % 11 == 0:
                    c = (78,46,120)
                if y == PY:
                    c = lerp(c, (120,80,160), .4)
                px[x, y] = c

        # embers
        for _ in range(160):
            x, y = rng.randrange(GW), rng.randrange(10, LAVA_Y-2)
            if 76 <= y <= 106 and 25 <= x <= GW-25:
                continue  # keep the subtitle clean
            px[x, y] = rng.choice([(255,230,120), (255,160,40), (255,110,30)])

        # haze glow behind the title so it pops
        cx, cy = GW//2, 46
        for y in range(GH):
            for x in range(GW):
                d = ((x-cx)/90)**2 + ((y-cy)/34)**2
                if d < 1:
                    px[x, y] = lerp(px[x, y], (30,6,8), .55*(1-d))

    def draw_text(text, s, top, fill_top, fill_bot, outline, shadow=2, glint=False):
        cells, w = text_cells(text, s)
        h = 7*s
        x0 = (GW - w)//2
        cs = set(cells)
        for x, y in cells:
            for k in range(1, shadow+1):
                px[x0+x+k, top+y+k] = (18,4,6)
        for x, y in cells:
            for ox, oy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
                if (x+ox, y+oy) not in cs:
                    px[x0+x+ox, top+y+oy] = outline
        for x, y in cells:
            c = lerp(fill_top, fill_bot, y/h)
            if (x, y-1) not in cs:
                c = lerp(c, (255,255,220), .6)
            if (x, y+1) not in cs:
                c = lerp(c, (120,20,5), .4)
            if glint and 0 <= (x - y*.6) - w*.62 < 3:
                c = lerp(c, (255,255,235), .75)
            px[x0+x, top+y] = c
        return x0, w

    # title in the sky gap; with a photo, tagline drops to the bottom strip
    title_s, title_y, sub_y = (6, 10, 101) if args.bg else (7, 22, 79)
    if not args.logo:
        draw_text('FYRE', title_s, title_y, (255,242,130), (232,60,8), (40,8,8), shadow=3, glint=False)
    if not args.tagline:
        draw_text(args.sub, 2, sub_y, (255,255,255), (255,196,90), (30,6,8))
    sx, sw = draw_text(args.sub2, 1, sub_y+18, (255,226,150), (255,170,60), (30,6,8), shadow=1)

    # crossed diamond swords either side of the subtitle
    def sword(ox, oy, flip, k=2):
        pts = []
        for i in range(11):
            pts += [(i, 10-i, (150,245,235) if i > 3 else (90,200,190)), (i+1, 10-i, (30,110,110))]
        for i in range(-2, 3):
            pts.append((3+i, 7+i, (245,196,70) if abs(i) < 2 else (190,130,40)))
        pts += [(0, 11, (150,100,55)), (1, 10, (170,115,60)), (-1, 12, (245,196,70))]
        for x, y, c in pts:
            X = ox + k*(12 - x if flip else x)
            for dx in range(k):
                for dy in range(k):
                    px[X+dx, oy+k*y+dy] = c
    for base in (sx - 20, sx + sw + 6):
        sword(base, sub_y+14, False, 1)
        sword(base, sub_y+14, True, 1)

    for scale in (4, 8):
        W, H = GW*scale, GH*scale
        out = f'{args.out}-{W}x{H}.png'
        text = img.resize((W, H), Image.NEAREST)
        if args.bg:
            photo = Image.open(args.bg).convert('RGB')
            pw, ph = photo.size
            ch = round(pw * GH / GW)
            top = min(round(ph * args.bg_top), ph - ch)
            base = photo.crop((0, top, pw, top + ch)).resize((W, H), Image.LANCZOS)
            # darken the bottom strip so the tagline reads over the lava glow
            shade = Image.new('L', (W, H))
            sp = shade.load()
            for y in range(H):
                t = max(0, (y/H - .62) / .38)
                for x in range(W):
                    sp[x, y] = int(190 * min(1, t*1.4))
            base = Image.composite(Image.new('RGB', (W, H), (14,3,4)), base, shade)
            base.paste(text, (0, 0), text)
            def overlay(path, width, top=None, bottom=None):
                im = Image.open(path).convert('RGBA')
                im = im.crop(im.getchannel('A').getbbox())
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
                y = top if top is not None else bottom - im.height
                pos = ((W - width)//2, y)
                # soft dark halo so the gold separates from the orange background
                pad = W // 20
                halo = Image.new('L', (im.width + 2*pad, im.height + 2*pad))
                halo.paste(im.getchannel('A'), (pad, pad))
                halo = halo.filter(ImageFilter.MaxFilter(2*(W//240)+1)).filter(ImageFilter.GaussianBlur(W/80))
                halo = halo.point(lambda v: int(v * .85))
                base.paste((12,2,3), (pos[0]-pad, pos[1]-pad), halo)
                base.paste(im, pos, im)
            if args.logo:
                overlay(args.logo, round(W * .66), top=round(H * .06))
            if args.tagline:
                overlay(args.tagline, round(W * .8), bottom=(sub_y + 16) * scale)
            base.save(out, optimize=True)
        else:
            text.save(out, optimize=True)
        print(out)

if __name__ == '__main__':
    main()
