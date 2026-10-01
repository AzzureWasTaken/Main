#!/usr/bin/env bash
#
# Compose MineX SMP Reddit ad creative from a screenshot.
#
#   ./build-creative.sh SCREENSHOT [OUTDIR]
#
# Produces the three Reddit sizes, each composed for its own ratio rather
# than cropped from one master. Requires ImageMagick.
#
# Edit the block below, not the body.

HEADLINE=${HEADLINE:-$'Free rank when\nyou join.'}
SUBLINE=${SUBLINE:-"New update live now"}
IP=${IP:-"fun.minex.gg"}
PLATFORM=${PLATFORM:-"JAVA"}

INK_HEAD="white"
INK_SUB="#C9C2E8"
INK_BAR_BG="#1A1424"
INK_BAR_LABEL="#8C8099"
INK_BAR_IP="#FFA32E"
FONT_BOLD="DejaVu-Sans-Bold"   # swap for the MineX brand face
FONT_REG="DejaVu-Sans"

set -euo pipefail

SRC=${1:?usage: build-creative.sh SCREENSHOT [OUTDIR]}
OUT=${2:-./out}
mkdir -p "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

SRC_W=$(identify -format '%w' "$SRC")

# A no-text variant for the native test gets built alongside every size.
compose () {
  local W=$1 H=$2 NAME=$3 HEAD=$4 SUB=$5 BAR=$6 PAD=$7 FOCAL=$8
  local BODY_H=$((H - BAR))

  if [ "$SRC_W" -lt $((W * 2)) ]; then
    printf 'warn: %s is %spx wide; %s wants >=%spx to stay sharp\n' \
      "$(basename "$SRC")" "$SRC_W" "$NAME" "$((W * 2))" >&2
  fi

  # Backdrop: fill the frame from the focal edge, never stretch.
  convert "$SRC" -resize "${W}x${BODY_H}^" \
    -gravity "$FOCAL" -extent "${W}x${BODY_H}" \
    -modulate 90,106,100 "$TMP/bd.png"

  # Bottom-up scrim. Minecraft skies are bright; white type needs this.
  convert -size "${W}x${BODY_H}" gradient:none-black \
    -alpha set -channel A -evaluate multiply 0.86 +channel "$TMP/scrim.png"
  convert "$TMP/bd.png" "$TMP/scrim.png" -composite "$TMP/body.png"

  # IP bar: a footnote for desktop players, not the call to action.
  convert -size "${W}x${BAR}" xc:"$INK_BAR_BG" \
    -font "$FONT_BOLD" -pointsize $((BAR * 36 / 100)) -gravity West \
    -fill "$INK_BAR_LABEL" -annotate "+${PAD}+0" "$PLATFORM" \
    -fill "$INK_BAR_IP" -annotate "+$((PAD + BAR * 130 / 100))+0" "$IP" \
    "$TMP/bar.png"

  # Headline block, bottom-left, above the bar.
  convert "$TMP/body.png" -gravity SouthWest \
    -font "$FONT_BOLD" -fill "$INK_HEAD" -pointsize "$HEAD" \
    -interline-spacing $((HEAD / 10)) \
    -annotate "+${PAD}+$((PAD + SUB * 2))" "$HEADLINE" \
    -font "$FONT_REG" -fill "$INK_SUB" -pointsize "$SUB" \
    -annotate "+${PAD}+${PAD}" "$SUBLINE" \
    "$TMP/text.png"

  convert "$TMP/text.png" "$TMP/bar.png" -append "$OUT/$NAME.png"

  # Native variant: same framing, no overlay at all.
  convert "$SRC" -resize "${W}x${H}^" \
    -gravity "$FOCAL" -extent "${W}x${H}" "$OUT/$NAME-notext.png"

  identify -format '%f  %wx%h\n' "$OUT/$NAME.png"
}

#       W    H     name                 head sub bar pad focal
compose 1080 1350 "minex-4x5"            86  33 100  58 North
compose 1200 1200 "minex-1x1"            88  33  96  60 North
compose 1200  628 "minex-191"            76  30  84  56 Center

printf '\nwrote %s\n' "$OUT"
