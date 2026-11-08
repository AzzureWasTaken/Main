# 3D props

Renders Minecraft blocks and items as transparent 600x600 PNGs with three.js in headless Chromium.
Textures in `ptex/` are the game's own (Mojang), from the InventivetalentDev/minecraft-assets mirror.

```bash
npm i
python3 -m http.server 8765 --bind 127.0.0.1 &
node render_props.mjs OUTDIR
```

Add a prop by adding a line to `PROPS` in `render_props.mjs` (`kind=block&side=…` or `kind=item&tex=…`).
`render_props.mjs` expects Chromium at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
