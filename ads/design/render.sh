#!/usr/bin/env bash
#
# Render ad.html to the three Reddit sizes.
#
#   ./render.sh [OUTDIR] [QUERY]
#
#   ./render.sh out
#   ./render.sh out/b3 "head=Nobody has claimed the good land yet.&eyebrow=New map"
#   ./render.sh out "bg=shots/spawn-dawn.png&pos=center 30%"
#
# Chromium's --window-size is the OUTER window, so each frame is rendered
# oversized and cropped down to the exact pixel dimensions.

set -euo pipefail

CHROME=${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/out}
QUERY=${2:-}
mkdir -p "$OUT"

shot () {
  local f=$1 w=$2 h=$3 extra=${4:-}
  local name="minex-$f${extra:+-notext}"
  local url="file://$HERE/ad.html?f=$f${extra:+&notext=1}${QUERY:+&$QUERY}"

  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --virtual-time-budget=6000 \
    --window-size=$((w + 40)),$((h + 160)) \
    --screenshot="$OUT/$name.raw.png" "$url" 2>/dev/null

  convert "$OUT/$name.raw.png" -crop "${w}x${h}+0+0" +repage "$OUT/$name.png"
  rm -f "$OUT/$name.raw.png"
  identify -format '  %f  %wx%h\n' "$OUT/$name.png"
}

for v in "" notext; do
  shot 4x5 1080 1350 "$v"
  shot 1x1 1200 1200 "$v"
  shot 191 1200  628 "$v"
done

echo "wrote $OUT"
