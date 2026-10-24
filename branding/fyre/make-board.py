#!/usr/bin/env python3
"""Cut every banner element into its own 1920x1080 transparent layer for board.html.

    python3 make-board.py            # writes board/layers/*.png and base.webp

board.html stacks these in the same order halloween.scene() and make-fyre-banner.py use, so the
board's download matches the generated banners.
"""
from pathlib import Path
from PIL import Image
import halloween

HERE = Path(__file__).parent
OUT = HERE / 'board' / 'layers'
W, H = 1920, 1080
GW, GH = 240, 135

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    photo = Image.open(HERE / 'fyre-background.webp').convert('RGB')
    pw, ph = photo.size
    ch = round(pw * GH / GW)
    top = min(round(ph * .2), ph - ch)
    ref = photo.crop((0, top, pw, top + ch)).resize((W, H), Image.LANCZOS)
    ref.save(OUT / 'base.webp', quality=95, method=6)

    for name, (layer, blend) in halloween.build_layers(ref, W / 960).items():
        layer.save(OUT / f'{name}.png', optimize=True)
    halloween.shade_layer((W, H)).save(OUT / 'shade.png', optimize=True)
    scale = W // GW
    halloween.text_layer(HERE / 'fyre-logo.png', (W, H), round(W * .66), top=round(H * .06)).save(OUT / 'logo_classic.png', optimize=True)
    halloween.text_layer(HERE / 'fyre-logo.png', (W, H), round(W * .66), top=round(H * .06), spooky=True).save(OUT / 'logo_halloween.png', optimize=True)
    halloween.text_layer(HERE / 'fyre-tagline.png', (W, H), round(W * .94), bottom=(GH - 12) * scale).save(OUT / 'tagline.png', optimize=True)
    total = 0
    for p in sorted(OUT.iterdir()):
        total += p.stat().st_size
        print(f'{p.name:28s}{p.stat().st_size/1024:8.0f} KB')
    print(f'total {total/1024/1024:.1f} MB')

if __name__ == '__main__':
    main()
