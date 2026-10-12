#!/usr/bin/env bash
# Saca un PNG del punto medio de cada beat y los junta en una hoja de
# contactos. Cuesta ~1 segundo y evita tener que ver el preview entero para
# comprobar que un overlay quedó bien colocado.
#
#   bash scripts/extract_stills.sh <video>
#
# Lee el preview ya renderizado (<video>.preview.mp4) y el plan.
set -euo pipefail
export PYTHONIOENCODING=utf-8

VIDEO="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
BASE="${VIDEO%.*}"
PREVIEW="$BASE.preview.mp4"
PLAN="${PLAN:-$BASE.plan.json}"
OUTDIR="$BASE.stills"

[ -f "$PREVIEW" ] || { echo "[error] no preview found: $PREVIEW - run render.sh first" >&2; exit 1; }
[ -f "$PLAN" ] || { echo "[error] no plan found: $PLAN" >&2; exit 1; }

rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"

# Un PNG por beat, nombrado con su índice y su kind para poder identificarlo
# de un vistazo en el explorador de archivos.
# `tr -d '\r'` NO es opcional: en Windows, Python escribe \r\n y el \r
# sobrevive al pipe, así que `mid` acabaría siendo "1.00\r" y ffmpeg rechaza
# el -ss con "Invalid duration".
python3 -c "
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
for i, b in enumerate(p.get('beats', [])):
    mid = (b['start_sec'] + b['end_sec']) / 2
    print(f\"{i:02d} {b.get('kind','?')} {mid:.2f}\")
" "$PLAN" | tr -d '\r' | while read -r idx kind mid; do
  ffmpeg -y -loglevel error -ss "$mid" -i "$PREVIEW" -frames:v 1 \
    "$OUTDIR/${idx}_${kind}.png"
done

# Hoja de contactos: todos los beats en una sola imagen.
#
# Se construye desde el MP4 con el filtro `select`, no juntando los PNG ya
# extraídos: el globbing de ffmpeg (-pattern_type glob) no está compilado en
# las builds de Windows, así que leer "*.png" falla ahí. Sacar los frames otra
# vez del vídeo cuesta lo mismo y funciona en las tres plataformas.
COUNT="$(ls -1 "$OUTDIR"/*.png 2>/dev/null | wc -l | tr -d ' ')"
if [ "$COUNT" -gt 0 ]; then
  FPS_PREV="$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate \
    -of default=noprint_wrappers=1:nokey=1 "$PREVIEW" | awk -F/ '{print ($2? $1/$2 : $1)}')"
  SELECT="$(python3 -c "
import json, sys
plan, fps = sys.argv[1], float(sys.argv[2])
p = json.load(open(plan, encoding='utf-8'))
frames = [round((b['start_sec'] + b['end_sec']) / 2 * fps) for b in p.get('beats', [])]
print('+'.join(f'eq(n\,{f})' for f in frames))
" "$PLAN" "$FPS_PREV" | tr -d '\r')"
  COLS=$(( COUNT < 5 ? COUNT : 5 ))
  ROWS=$(( (COUNT + COLS - 1) / COLS ))
  ffmpeg -y -loglevel error -i "$PREVIEW" \
    -vf "select='${SELECT}',scale=270:480,tile=${COLS}x${ROWS}" \
    -frames:v 1 "$OUTDIR/_hoja.png" 2>/dev/null || true
fi

echo "==> $COUNT frames in $OUTDIR"
[ -f "$OUTDIR/_hoja.png" ] && echo "==> contact sheet: $OUTDIR/_hoja.png"
