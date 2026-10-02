#!/usr/bin/env bash
#
# Convert the animated banner to GIF for server-list sites.
#
#   ./webm-to-gif.sh SOURCE.webm [OUTDIR]
#
# Server lists require GIF and almost all use 468x60. Produces a size
# ladder so you can pick the largest that fits the site's upload cap.

set -euo pipefail
SRC=${1:?usage: webm-to-gif.sh SOURCE.webm [OUTDIR]}
OUT=${2:-.}
BASE=$(basename "${SRC%.*}")
W=${W:-468}
H=${H:-60}

# fps and palette size are the only levers that matter here. Frame
# differencing (-layers Optimize) saves nothing on this clip because the
# background animates behind the text, so almost no pixels are static.
mk () {
  local name=$1 fps=$2 colors=$3 dither=$4
  ffmpeg -hide_banner -v error -i "$SRC" \
    -vf "fps=$fps,scale=$W:$H:flags=lanczos,split[a][b];\
[a]palettegen=max_colors=$colors:stats_mode=diff[p];\
[b][p]paletteuse=dither=$dither:diff_mode=rectangle" \
    -loop 0 -y "$OUT/$BASE-${W}x${H}-$name.gif"
  printf '  %-30s %6.0f KB\n' "$BASE-${W}x${H}-$name.gif" \
    "$(stat -c%s "$OUT/$BASE-${W}x${H}-$name.gif")e-3" 2>/dev/null ||
  ls -la "$OUT/$BASE-${W}x${H}-$name.gif"
}

mk hi   15 256 bayer:bayer_scale=3
mk mid  12 160 bayer:bayer_scale=4
mk lo   10 96  bayer:bayer_scale=5
mk tiny  8 64  bayer:bayer_scale=5
