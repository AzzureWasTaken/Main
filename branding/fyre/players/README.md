# Player renders

`duel.png` (two armoured players sword-fighting) and `explorer.png` (one player walking with a torch)
are transparent 3D renders of Minecraft's own skins, armour and item textures, made with three.js in
headless Chromium. `halloween.py` composites them into the banner with `--players`.

Remake them:

```bash
cd scene3d && npm i
python3 -m http.server 8765 --bind 127.0.0.1 &
node render.mjs ../duel.png     "?only=duel&ppu=9&w=1400&h=800&tx=0&ty=26&el=6"
node render.mjs ../explorer.png "?only=explorer&ppu=9&w=700&h=800&tx=0&ty=24&el=6"
```

`render.mjs` expects Chromium at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; change the path
for your machine. Skins and textures in `scene3d/tex/` come from the same Mojang asset mirror as `../mobs/`.
