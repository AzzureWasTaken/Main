# Social graphics

Each graphic is an HTML layout with a rendered PNG next to it. Edit the HTML, then re-render it with headless Chromium at 1x and crop to the exact size. `ads/design/render.sh` shows the pattern.

Fonts come from `ads/design/fonts.css` (Archivo, Silkscreen). Archivo Black and Outfit load from Google Fonts.

## telegram/ (1280×720)
Beta-season card. Everything is vector or CSS, including the pixel coin and diamond, so it has no image dependencies and is sharp at any scale.

## reddit/ (1080×1350)
Halloween LORD offer for `red.minex.gg`. The layout matches the approved version. These parts are still placeholders:
- `bg-placeholder.jpg`, `logo-coin.png` and `badge-lord.png` are cropped from the 600px email screenshot, so they're soft. Replace them with the source art.
- The spider and cobweb decoration, the pumpkin icons (pill and bullets) and the Discord logos aren't drawn yet. The pumpkins are plain orange squares for now.
