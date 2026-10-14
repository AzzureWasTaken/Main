#!/usr/bin/env python3
"""Fyre server-list banner: animated Nether/lava pixel-art scene.

Renders on a 481x62 pixel grid, scaled 2x (nearest) to 962x124, and
downsampled to 468x60. Every motion is a whole number of cycles per loop,
so the GIF loops seamlessly.

    python3 make-fyre-banner.py [--lines "LAVA PVP SERVER" "FIGHT ON THE LAVA"] [--ip play.fyre.gg]
"""
import argparse, math, random
from PIL import Image, ImageDraw

GW, GH, SCALE = 481, 62, 2
FRAMES, FRAME_MS = 48, 80

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lines', nargs='+', default=['LAVA PVP SERVER', 'FIGHT ON THE LAVA'])
    ap.add_argument('--ip', default='')
    ap.add_argument('--out', default='fyre')
    args = ap.parse_args()

    rng = random.Random(7)
    # Netherrack texture, 8x8-cell blocks
    NR = [(97,37,37),(111,44,42),(83,30,32),(128,52,48),(70,24,27)]
    rack = [[rng.choice(NR) for _ in range(GW)] for _ in range(GH)]
    for y in range(GH):
        for x in range(GW):
            if x % 8 == 0 or y % 8 == 0:
                rack[y][x] = lerp(rack[y][x], (40,10,14), .35)

    LAVA_TOP = 50
    lava_noise = [[rng.random() for _ in range(64)] for _ in range(GH)]
    embers = [(rng.uniform(0, GW), rng.uniform(0, GH), rng.choice([1, 2]),
               rng.uniform(0, 2*math.pi)) for _ in range(70)]
    flame_seed = [rng.random()*6.28 for _ in range(GW)]

    title, tw = text_cells('FYRE', 5, gap=1)       # 35px tall
    tx, ty = 18, (LAVA_TOP - 35)//2 + 1
    right = args.lines + [args.ip.upper() if args.ip else 'JOIN THE BLAZE!']

    frames = []
    for f in range(FRAMES):
        p = f / FRAMES
        img = Image.new('RGB', (GW, GH))
        px = img.load()
        # background with heat glow toward the lava
        for y in range(GH):
            heat = max(0, (y - 18) / (LAVA_TOP - 18))
            for x in range(GW):
                c = lerp(rack[y][x], (25,6,10), .45)          # darken for contrast
                px[x, y] = lerp(c, (200,70,20), heat*.35)
        # flame fringe licking above the lava
        for x in range(GW):
            h = 3 + 3*math.sin(flame_seed[x] + 2*math.pi*p*2) + 2*math.sin(x*.37 + 2*math.pi*p)
            for k in range(int(max(0, h))):
                t = k / max(h, 1)
                px[x, LAVA_TOP-1-k] = lerp((255,190,40), (200,40,10), t)
        # scrolling lava
        for y in range(LAVA_TOP, GH):
            for x in range(GW):
                n = lava_noise[y][(x + int(p*64)) % 64]
                w = .5 + .5*math.sin((x + p*96)/6 + y*.9)
                v = .55*n + .45*w
                px[x, y] = lerp((190,50,8), (255,215,60), v)
        # embers rise (each makes a whole number of trips per loop)
        for ex, ey, sp, ph in embers:
            y = (ey - p*GH*sp) % GH
            x = (ex + 2*math.sin(ph + 2*math.pi*p*sp)) % GW
            if y < LAVA_TOP - 2:
                c = (255,230,120) if (f + int(ph*10)) % 4 else (255,140,30)
                px[int(x), int(y)] = c
        # title: shadow, outline, gradient fill
        d = ImageDraw.Draw(img)
        for x, y in title:
            d.point((tx+x+2, ty+y+2), (20,4,6))
        ts = set(title)
        for x, y in title:
            for ox, oy in ((-1,0),(1,0),(0,-1),(0,1)):
                if (x+ox, y+oy) not in ts:
                    px[tx+x+ox, ty+y+oy] = (35,8,8)
        shimmer = (math.sin(2*math.pi*p) + 1) / 2
        for x, y in title:
            t = y / 35
            c = lerp((255,240,120), (235,70,10), t)
            band = ((x - y*.6) - (p*(tw+60) - 30)) % (tw+60)  # sweeping glint
            if band < 4:
                c = lerp(c, (255,255,230), .7)
            if (x, y-1) not in ts:
                c = lerp(c, (255,255,210), .6)               # top highlight
            px[tx+x, ty+y] = c
        # right-hand text, alternating every half loop
        line = right[f * len(right) // FRAMES]
        cells, w = text_cells(line, 2)
        rx, ry = GW - w - 16, (LAVA_TOP - 14)//2
        cs = set(cells)
        for x, y in cells:
            for ox, oy in ((-1,0),(1,0),(0,-1),(0,1),(1,1)):
                if (x+ox, y+oy) not in cs:
                    px[rx+x+ox, ry+y+oy] = (25,6,8)
        for x, y in cells:
            px[rx+x, ry+y] = lerp((255,255,255), (255,200,90), y/14)
        frames.append(img.resize((GW*SCALE, GH*SCALE), Image.NEAREST).crop((0,0,962,124)))

    def save(frs, path, colors=256, ms=FRAME_MS):
        q = [fr.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE) for fr in frs]
        q[0].save(path, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True)
        print(path)

    save(frames, f'{args.out}-962x124.gif')
    small = [fr.resize((468, 60), Image.LANCZOS) for fr in frames]
    save(small, f'{args.out}-468x60.gif', 96)
    save(small[::2], f'{args.out}-468x60-lite.gif', 64, FRAME_MS*2)  # for ~500 KB upload caps

if __name__ == '__main__':
    main()
