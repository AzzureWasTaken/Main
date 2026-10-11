#!/usr/bin/env bash
# ============================================================================
#  minexvideo — render pipeline
# ============================================================================
#
#  Uso:
#     bash scripts/render.sh <video>                 # preview (por defecto)
#     bash scripts/render.sh <clip1> <clip2> ...     # varios clips seguidos
#     QUALITY=final bash scripts/render.sh <video>   # entrega
#
#  Variables de entorno:
#     QUALITY=preview|final   preview = 720p rápido. final = resolución nativa.
#     CAPTIONS=1|0            1 por defecto. 0 si el vídeo ya lleva subtítulos.
#     PLAN=<ruta>             plan alternativo. Por defecto <proyecto>.plan.json
#     NOMBRE=<nombre>         nombre del proyecto (plan y salidas). Útil con
#                             varios clips, para no colgarlo del primero.
#     MODELO=large-v3         modelo de Whisper.
#     FORCE_RENDER=1          ignora la caché y re-renderiza.
#
#  VARIOS CLIPS: se unen en una sola fuente ANTES de todo lo demás, así que el
#  plan, el linter y las plantillas siguen viendo una única línea de tiempo.
#  Los `start_sec` del plan van en segundos de esa línea montada; el mapa que
#  imprime el montaje dice dónde empieza cada clip. No recorta nada: cada clip
#  entra entero y en orden.
#
#  MÚSICA: se declara en el plan (campo `musica`) y se mezcla DESPUÉS de
#  transcribir, por debajo de la voz y con ducking. Ver scripts/mezcla_musica.py.
#
#  ORDEN DE LAS ETAPAS, y por qué es ese:
#
#     montaje (+transiciones) -> cortar_silencios -> ritmo -> velocidad
#         -> [aquí se transcribe, sobre la fuente a velocidad NATURAL]
#         -> censura -> efectos_voz -> subtítulos -> música -> render
#
#  Todo lo que estira el tiempo (silencios, ritmo, velocidad) va ANTES de
#  transcribir: así los `start_sec` del plan, los subtítulos y los beats miden
#  todos sobre la línea de tiempo final y no hay ninguna cuenta que rehacer.
#  Pero la transcripción se hace sobre la fuente SIN estirar, porque Whisper con
#  la voz acelerada se inventa palabras; los tiempos se traducen después con
#  scripts/tiempo.py, que compone los tres estiramientos en un solo mapa.
#
#  Lo que toca el audio sin cambiar su duración (censura, efectos de voz) va
#  después, para no descuadrar unos subtítulos ya calculados.
#
#  El pipeline es INCREMENTAL: cada etapa guarda su resultado en el workdir y
#  se salta si sus entradas no han cambiado. Cambiar un beat del plan solo
#  vuelve a lanzar Remotion; la transcripción y el proxy no se tocan. Esto es
#  lo que hace viable iterar 10 veces sobre el mismo short.
# ============================================================================
set -euo pipefail
export PYTHONIOENCODING=utf-8

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTION_DIR="$SKILL_DIR/remotion"
# Biblioteca de imágenes generadas (vive fuera de la skill, con los medios del
# usuario). Debe coincidir con LIB_DIR de generar_imagen.js / biblioteca.js.
LIB_GENERADOS="${MINEX_LIB_DIR:-$SKILL_DIR/assets}"

# En Git Bash (Windows) las rutas POSIX tipo /c/Users/... no las entiende
# Node. cygpath -m las convierte a C:/Users/... que sí funciona en los dos
# mundos. En macOS/Linux cygpath no existe y la ruta se pasa tal cual.
towin() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi
}

if [ $# -lt 1 ]; then
  echo "usage: bash scripts/render.sh <video> [clip2 clip3 ...]" >&2
  exit 2
fi

CLIPS=()
for arg in "$@"; do
  abs="$(cd "$(dirname "$arg")" && pwd)/$(basename "$arg")"
  [ -f "$abs" ] || { echo "[error] file not found: $abs" >&2; exit 1; }
  CLIPS+=("$abs")
done
PRIMERO="${CLIPS[0]}"

QUALITY="${QUALITY:-preview}"
CAPTIONS="${CAPTIONS:-1}"
MODELO="${MODELO:-large-v3}"

# ── Proyecto ───────────────────────────────────────────────────────────────
# El "proyecto" es de dónde cuelgan el plan y las salidas. Con un solo clip es
# el propio vídeo (comportamiento de siempre). Con varios se le añade un
# sufijo, porque llamar al montaje igual que el primer clip hace pensar que la
# edición es solo de ese.
if [ -n "${NOMBRE:-}" ]; then
  case "$NOMBRE" in
    */*) PROYECTO="$NOMBRE" ;;
    *)   PROYECTO="$(dirname "$PRIMERO")/$NOMBRE" ;;
  esac
elif [ ${#CLIPS[@]} -gt 1 ]; then
  PROYECTO="${PRIMERO%.*}-montaje"
else
  PROYECTO="${PRIMERO%.*}"
fi

# ── Workdir ────────────────────────────────────────────────────────────────
# Hash de TODAS las rutas en orden: cambiar el orden de los clips, o añadir
# uno, da un workdir nuevo y no reutiliza por error la transcripción anterior.
# Con un solo clip sale el mismo hash que usa transcribe.py por su cuenta.
HASH="$(python3 -c "
import hashlib, sys, pathlib
rutas = '|'.join(str(pathlib.Path(p).resolve()) for p in sys.argv[1:])
print(hashlib.sha1(rutas.encode()).hexdigest()[:16])" "${CLIPS[@]}")"
WORKDIR="$HOME/.cache/minexvideo/$HASH"
mkdir -p "$WORKDIR"
echo "==> workdir: $WORKDIR"

# ── Plan ───────────────────────────────────────────────────────────────────
# Se lee ANTES del montaje: las transiciones entre clips se declaran en él, y
# el montaje es la primera etapa que las necesita.
PLAN="${PLAN:-$PROYECTO.plan.json}"
if [ ! -f "$PLAN" ]; then
  echo "[error] plan not found: $PLAN" >&2
  echo "        Create that file with the short's beats. See SKILL.md." >&2
  exit 1
fi
echo "==> plan: $PLAN"

# Firma de un archivo, para las cachés de cada etapa.
#
# Comparar mtimes (`-nt`) no basta cuando una etapa puede recibir entradas
# DISTINTAS según el plan: al quitar `ritmo`, por ejemplo, la etapa de velocidad
# pasa de leer `fuente_ritmo.mp4` a leer la fuente base, que es más antigua que
# el acelerado que ya había en caché — y el `-nt` decía "no hay nada que hacer"
# mientras se reutilizaba un archivo derivado de la línea de tiempo anterior.
# Con la firma de la entrada dentro de la marca, cambiar de entrada invalida
# siempre.
firma() { stat -c '%Y:%s' "$1" 2>/dev/null || echo nada; }

# Atajo para sacar un bloque del plan como JSON de una línea, apto para
# meterlo en una variable de shell.
campo_json() {
  python3 -c "
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
v = p.get(sys.argv[2])
print('' if v in (None, False, [], {}) else json.dumps(v, ensure_ascii=False))" "$PLAN" "$1"
}

# ── Fuente (montaje de clips si hay más de uno) ────────────────────────────
# `clips.base.json` guarda el mapa en segundos del MONTAJE CRUDO y no se toca
# nunca más; `clips.json` es ese mismo mapa traducido a la línea de tiempo
# final (con silencios, rampas y velocidad ya aplicados) y se regenera en cada
# pasada. Separarlos evita el error de reescalar dos veces el mismo archivo.
MAPA_CLIPS="$WORKDIR/clips.json"
MAPA_BASE="$WORKDIR/clips.base.json"
if [ ${#CLIPS[@]} -gt 1 ]; then
  VIDEO="$WORKDIR/fuente.mp4"
  TRANSICIONES="$(campo_json transiciones)"
  MARCA_MON="$WORKDIR/.montaje"
  REMONTAR=0
  if [ ! -f "$VIDEO" ] || [ ! -f "$MAPA_BASE" ]; then
    REMONTAR=1
  else
    for c in "${CLIPS[@]}"; do
      if [ "$c" -nt "$VIDEO" ]; then REMONTAR=1; fi
    done
  fi
  # Cambiar la transición (o su duración) cambia la línea de tiempo montada,
  # así que hay que rehacerlo todo desde aquí.
  if [ ! -f "$MARCA_MON" ] || [ "$(cat "$MARCA_MON")" != "$TRANSICIONES" ]; then
    REMONTAR=1
  fi
  if [ "$REMONTAR" = "1" ]; then
    echo "==> joining ${#CLIPS[@]} clips into a single source"
    python3 "$SKILL_DIR/scripts/montar_clips.py" "$VIDEO" "$MAPA_BASE" "${CLIPS[@]}" \
      --transiciones "$TRANSICIONES"
    printf '%s' "$TRANSICIONES" > "$MARCA_MON"
    # La transcripción del montaje anterior ya no vale.
    rm -rf "$WORKDIR/words.json" "$WORKDIR/audio.wav" "$WORKDIR/base"
    rm -f "$WORKDIR"/fuente_*.mp4 "$WORKDIR/proxy_1080.mp4" "$WORKDIR/.velocidad" \
          "$WORKDIR/.ritmo" "$WORKDIR/.silencios"
  else
    echo "==> joined source cached (${#CLIPS[@]} clips)"
  fi
else
  VIDEO="$PRIMERO"
  rm -f "$MAPA_CLIPS" "$MAPA_BASE" "$WORKDIR/.montaje"
fi

# ── Velocidad (opcional, declarada en el plan) ─────────────────────────────
# Va ANTES de sondar y de transcribir: así todo lo que viene después —duración,
# words.json, los start_sec del plan— mide sobre la línea de tiempo final y no
# hay que reescalar nada a mano.
VEL="$(python3 -c "
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
print(p.get('velocidad', 1) or 1)" "$PLAN")"
# ── Cortar silencios (opcional, declarado en el plan) ──────────────────────
# Va antes de acelerar y de transcribir, para que todo lo de después mida sobre
# la línea de tiempo ya recortada. Cortar NO es una escala lineal como
# acelerar: cada beat se desplaza según cuánto silencio quede por delante, así
# que el mapa de tramos eliminados se guarda para poder recolocar un plan ya
# escrito.
CORTAR="$(python3 -c "
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
c = p.get('cortar_silencios')
if c is True: c = {}
if not isinstance(c, dict): print(''); raise SystemExit
print(f\"{c.get('umbral_db',-35)}|{c.get('min_dur',0.35)}|{c.get('dejar',0.12)}\")" "$PLAN")"
MAPA_SIL="$WORKDIR/silencios.json"
if [ -n "$CORTAR" ]; then
  SIN_SIL="$WORKDIR/fuente_sinsilencios.mp4"
  UMB="${CORTAR%%|*}"; RESTO="${CORTAR#*|}"; MIND="${RESTO%%|*}"; DEJ="${RESTO##*|}"
  MARCA_SIL="$WORKDIR/.silencios"
  FIRMA_SIL="$UMB|$MIND|$DEJ|$(firma "$VIDEO")"
  RECORTAR=0
  if [ ! -f "$SIN_SIL" ] || [ ! -f "$MAPA_SIL" ]; then RECORTAR=1; fi
  if [ ! -f "$MARCA_SIL" ] || [ "$(cat "$MARCA_SIL")" != "$FIRMA_SIL" ]; then RECORTAR=1; fi
  if [ "$RECORTAR" = "1" ]; then
    python3 "$SKILL_DIR/scripts/cortar_silencios.py" "$VIDEO" "$SIN_SIL" "$MAPA_SIL"       --umbral-db "$UMB" --min "$MIND" --dejar "$DEJ"
    printf '%s' "$FIRMA_SIL" > "$MARCA_SIL"
    rm -rf "$WORKDIR/base" "$WORKDIR/words.json" "$WORKDIR/fuente_musica.mp4" "$WORKDIR/proxy_1080.mp4"
    rm -f "$WORKDIR"/fuente_x*.mp4 "$WORKDIR/.velocidad"
  else
    echo "==> silences already trimmed (cached)"
  fi
  VIDEO="$SIN_SIL"
else
  rm -f "$MAPA_SIL" "$WORKDIR/.silencios"
fi

VIDEO_BASE="$VIDEO"          # la fuente a velocidad natural: es la que se transcribe

# ── Línea de tiempo: rampas de ritmo + velocidad global ────────────────────
# Las dos estiran el vídeo, así que van juntas y ANTES de transcribir: todo lo
# que viene después (words.json, subtítulos, beats, render) mide sobre la línea
# de tiempo final y no se entera de nada. Ver scripts/ritmo.py.
RITMO="$(campo_json ritmo)"
MAPA_RITMO="$WORKDIR/ritmo.json"
FIRMA_TL="$RITMO|$VEL"
MARCA_TL="$WORKDIR/.linea_tiempo"
CAMBIO_TL=0
if [ -f "$MARCA_TL" ] && [ "$(cat "$MARCA_TL")" != "$FIRMA_TL" ]; then
  # La línea de tiempo va a cambiar. Se guarda el mapa anterior porque es lo
  # único que permite recolocar un plan que ya estaba escrito: sin él, saber
  # dónde cae ahora un beat del segundo 34 es imposible.
  CAMBIO_TL=1
  if [ -f "$MAPA_RITMO" ]; then cp "$MAPA_RITMO" "$WORKDIR/ritmo.anterior.json"
  else rm -f "$WORKDIR/ritmo.anterior.json"; fi
  if [ -f "$WORKDIR/.velocidad" ]; then cp "$WORKDIR/.velocidad" "$WORKDIR/.velocidad.anterior"
  else rm -f "$WORKDIR/.velocidad.anterior"; fi
fi

if [ -n "$RITMO" ]; then
  RIT="$WORKDIR/fuente_ritmo.mp4"
  MARCA_RITMO="$WORKDIR/.ritmo"
  FIRMA_RITMO="$RITMO|$(firma "$VIDEO")"
  REHACER_RITMO=0
  if [ ! -f "$RIT" ] || [ ! -f "$MAPA_RITMO" ]; then REHACER_RITMO=1; fi
  if [ ! -f "$MARCA_RITMO" ] || [ "$(cat "$MARCA_RITMO")" != "$FIRMA_RITMO" ]; then REHACER_RITMO=1; fi
  if [ "$REHACER_RITMO" = "1" ]; then
    python3 "$SKILL_DIR/scripts/ritmo.py" "$VIDEO" "$RIT" "$MAPA_RITMO" --ops "$RITMO"
    printf '%s' "$FIRMA_RITMO" > "$MARCA_RITMO"
    rm -f "$WORKDIR/words.json" "$WORKDIR/fuente_musica.mp4" "$WORKDIR/proxy_1080.mp4"
    rm -f "$WORKDIR"/fuente_x*.mp4 "$WORKDIR/.velocidad"
  else
    echo "==> speed ramps cached"
  fi
  VIDEO="$RIT"
else
  rm -f "$MAPA_RITMO" "$WORKDIR/.ritmo" "$WORKDIR/fuente_ritmo.mp4"
fi

if [ "$(python3 -c "print(abs(float('$VEL')-1) > 0.001)")" = "True" ]; then
  ACEL="$WORKDIR/fuente_x$VEL.mp4"
  # `.velocidad` guarda SOLO el número, porque tiempo.py lo lee como factor;
  # la firma de caché (que incluye la entrada) va en un archivo aparte.
  MARCA="$WORKDIR/.velocidad"
  MARCA_VF="$WORKDIR/.velocidad.firma"
  FIRMA_VEL="$VEL|$(firma "$VIDEO")"
  REACELERAR=0
  if [ ! -f "$ACEL" ]; then REACELERAR=1; fi
  if [ ! -f "$MARCA_VF" ] || [ "$(cat "$MARCA_VF")" != "$FIRMA_VEL" ]; then REACELERAR=1; fi
  if [ "$REACELERAR" = "1" ]; then
    python3 "$SKILL_DIR/scripts/acelerar.py" "$VIDEO" "$ACEL" "$VEL"
    printf '%s' "$VEL" > "$MARCA"
    printf '%s' "$FIRMA_VEL" > "$MARCA_VF"
    # La transcripción y la mezcla anteriores median sobre otra duración.
    rm -f "$WORKDIR/words.json" "$WORKDIR/fuente_musica.mp4" "$WORKDIR/proxy_1080.mp4"
  else
    echo "==> source sped up x$VEL (cached)"
  fi
  VIDEO="$ACEL"
else
  rm -f "$WORKDIR/.velocidad" "$WORKDIR/.velocidad.firma"
fi
printf '%s' "$FIRMA_TL" > "$MARCA_TL"

# El mapa de clips se traduce a la línea de tiempo final. Se deriva SIEMPRE del
# mapa crudo, nunca del traducido: reescalar el mismo archivo en cada pasada lo
# iba dividiendo una vez por ejecución y el mapa acababa mintiendo.
if [ -f "$MAPA_BASE" ]; then
  python3 -c "
import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import tiempo
m = tiempo.carga(pathlib.Path(sys.argv[2]))
clips = json.load(open(sys.argv[3], encoding='utf-8'))
for c in clips:
    c['start_sec'] = round(m.bruto_a_final(c['start_sec']), 3)
    c['end_sec'] = round(m.bruto_a_final(c['end_sec']), 3)
    c['duracion'] = round(c['end_sec'] - c['start_sec'], 3)
json.dump(clips, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('==> plan times are in seconds of this timeline:')
for c in clips:
    print(f\"           {c['start_sec']:7.2f} - {c['end_sec']:7.2f}  {c['clip']}\")
" "$SKILL_DIR/scripts" "$WORKDIR" "$MAPA_BASE" "$MAPA_CLIPS"
fi

if [ "$CAMBIO_TL" = "1" ]; then
  echo "[warning] the timeline changed (ritmo or velocidad)."
  echo "        If the plan already had beats written, move them:"
  echo "        python3 $SKILL_DIR/scripts/tiempo.py --workdir \"$WORKDIR\" --recoloca \"$PLAN\""
fi

# ── Sonda del vídeo ────────────────────────────────────────────────────────
read -r W H DUR FPS <<<"$(ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "$VIDEO" | tr '\n' ' ' | \
  awk '{split($3,a,"/"); fps=(a[2]?a[1]/a[2]:a[1]); print $1, $2, $4, fps}')"
FPS_INT="$(printf '%.0f' "$FPS")"
FRAMES="$(python3 -c "import math,sys; print(max(1, math.ceil(float(sys.argv[1])*float(sys.argv[2]))))" "$DUR" "$FPS_INT")"
echo "==> source: ${W}x${H} @ ${FPS_INT}fps, ${DUR}s (${FRAMES} frames)"

if [ "$W" -gt "$H" ]; then
  echo "[warning] this video is horizontal (${W}x${H}). This skill renders"
  echo "        vertical 9:16 shorts. Overlays will be placed using the"
  echo "        vertical safe zones and will look misplaced."
fi

# ── Transcripción (cacheada) ───────────────────────────────────────────────
WORDS="$WORKDIR/words.json"
BASE_WD="$WORKDIR/base"
CAPS_PLAN="$WORKDIR/captions_plan.json"
if [ "$CAPTIONS" = "1" ]; then
  if [ ! -f "$BASE_WD/words.json" ]; then
    echo "==> transcribing (${LANGUAGE:-en})..."
    # --workdir explícito: con varios clips la fuente vive dentro del propio
    # workdir y transcribe.py derivaría otro distinto de esa ruta.
    # `|| true` a propósito: en Windows con CUDA, torch revienta a veces al
    # CERRAR el intérprete, ya con words.json escrito y completo. Con `set -e`
    # eso abortaba el pipeline DESPUÉS de haber transcrito bien — dos minutos
    # de GPU tirados. Se comprueba el artefacto, que es lo que importa.
    python3 "$SKILL_DIR/scripts/transcribe.py" "$VIDEO_BASE" --modelo "$MODELO" \
      --idioma "${LANGUAGE:-en}" --workdir "$BASE_WD" || true
    if [ ! -s "$BASE_WD/words.json" ]; then
      echo "[error] transcription did not produce $BASE_WD/words.json" >&2
      exit 1
    fi
  else
    echo "==> transcription cached"
  fi
  # Whisper con la voz acelerada se inventa palabras — medido a 1.5x: oía
  # "arrestón" donde el original dice "redstone", y eso acaba escrito en los
  # subtítulos. Por eso se transcribe SIEMPRE la fuente a velocidad natural y
  # después se traducen los tiempos a la línea de tiempo final con el mapa
  # (velocidad global + rampas de ritmo). De paso, cambiar el ritmo ya no
  # obliga a volver a transcribir: se reaprovecha la misma transcripción.
  python3 "$SKILL_DIR/scripts/tiempo.py" --workdir "$WORKDIR" \
    --words "$BASE_WD/words.json" "$WORDS"

  # ── Censura de palabrotas ────────────────────────────────────────────────
  # ENCENDIDA por defecto: el canal es para niños. Va aquí, entre la
  # transcripción y los subtítulos, porque tiene que pitar el audio Y
  # enmascarar la palabra ANTES de que captions_plan.py la escriba en pantalla
  # — censurar solo una de las dos cosas no sirve de nada.
  #
  # `$WORDS` se regenera desde la transcripción original en cada pasada (justo
  # arriba), así que censura.py siempre ve el texto sin enmascarar y encuentra
  # los mismos tramos. Ver scripts/censura.py.
  CENS_CFG="$(python3 -c "
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
c = p.get('censura', True)
if c is False: print('0'); raise SystemExit
if c is True or c is None: c = {}
print('1')
print('|'.join(c.get('extra', [])))
print('|'.join(c.get('excluir', [])))
print(c.get('pitido_db', -16))
print(c.get('margen', 0.06))" "$PLAN")"
  if [ "$(printf '%s' "$CENS_CFG" | sed -n 1p)" = "1" ]; then
    CENS_MP4="$WORKDIR/fuente_censura.mp4"
    python3 "$SKILL_DIR/scripts/censura.py" "$WORDS" "$VIDEO" "$CENS_MP4" \
      --extra "$(printf '%s' "$CENS_CFG" | sed -n 2p)" \
      --excluir "$(printf '%s' "$CENS_CFG" | sed -n 3p)" \
      --pitido-db "$(printf '%s' "$CENS_CFG" | sed -n 4p)" \
      --margen "$(printf '%s' "$CENS_CFG" | sed -n 5p)"
    # Sin palabrotas censura.py no escribe nada y se sigue con la fuente
    # original: no se paga un remux de balde.
    [ -f "$CENS_MP4" ] && VIDEO="$CENS_MP4"
  else
    echo "[censor] disabled in the plan"
    rm -f "$WORKDIR/fuente_censura.mp4" "$WORKDIR/fuente_censura.mp4.firma"
  fi

  # El énfasis y el estilo de subtítulo se declaran en el plan, no por línea de
  # comandos, para que todo el short se describa en un solo archivo.
  ENFASIS="$(python3 -c "
import json,sys
p=json.load(open(sys.argv[1],encoding='utf-8'))
print('|'.join(p.get('enfasis',[])))" "$PLAN")"
  SUB_ESTILO="$(python3 -c "
import json,sys
p=json.load(open(sys.argv[1],encoding='utf-8'))
s=p.get('subtitulos') or {}
if isinstance(s,str): s={'estilo':s}
print(s.get('estilo','karaoke'))" "$PLAN")"
  SUB_TRAMOS="$(python3 -c "
import json,sys
p=json.load(open(sys.argv[1],encoding='utf-8'))
s=p.get('subtitulos') or {}
t=s.get('tramos') if isinstance(s,dict) else None
print('' if not t else json.dumps(t, ensure_ascii=False))" "$PLAN")"
  python3 "$SKILL_DIR/scripts/captions_plan.py" "$WORDS" "$CAPS_PLAN" \
    --enfasis "$ENFASIS" --estilo "$SUB_ESTILO" --tramos "$SUB_TRAMOS"
else
  echo "[]" > "$CAPS_PLAN"
  echo "==> captions disabled (CAPTIONS=0)"
  echo "[warning] without a transcript, profanity cannot be located -"
  echo "        this short is delivered UNCENSORED. Check it by hand."
fi

# ── Efectos de voz (opcional, declarados en el plan) ───────────────────────
# Van DESPUÉS de la censura: el pitido tiene que salir a 1 kHz y no
# transportado. Conservan la duración exacta, así que los subtítulos siguen
# clavados, y no recodifican la imagen. Ver scripts/efectos_voz.py.
VOZ="$(campo_json efectos_voz)"
if [ -n "$VOZ" ]; then
  VOZ_MP4="$WORKDIR/fuente_voz.mp4"
  MARCA_VOZ="$WORKDIR/.voz"
  FIRMA_VOZ="$VOZ|$(firma "$VIDEO")"
  REHACER_VOZ=0
  if [ ! -f "$VOZ_MP4" ]; then REHACER_VOZ=1; fi
  if [ ! -f "$MARCA_VOZ" ] || [ "$(cat "$MARCA_VOZ")" != "$FIRMA_VOZ" ]; then REHACER_VOZ=1; fi
  if [ "$REHACER_VOZ" = "1" ]; then
    python3 "$SKILL_DIR/scripts/efectos_voz.py" "$VIDEO" "$VOZ_MP4" --efectos "$VOZ"
    printf '%s' "$FIRMA_VOZ" > "$MARCA_VOZ"
    rm -f "$WORKDIR/fuente_musica.mp4" "$WORKDIR/proxy_1080.mp4"
  else
    echo "==> voice effects cached"
  fi
  VIDEO="$VOZ_MP4"
else
  rm -f "$WORKDIR/fuente_voz.mp4" "$WORKDIR/.voz"
fi

# ── Validación ─────────────────────────────────────────────────────────────
# Con la transcripción delante el linter puede además comprobar que los
# congelados caen en huecos y que las rampas no atropellan lo que se dice.
if [ -f "$WORDS" ]; then
  python3 "$SKILL_DIR/scripts/lint_plan.py" "$PLAN" "$VIDEO" --words "$WORDS" \
    --workdir "$WORKDIR"
else
  python3 "$SKILL_DIR/scripts/lint_plan.py" "$PLAN" "$VIDEO"
fi

# ── Música (opcional, declarada en el plan) ────────────────────────────────
# Va DESPUÉS de la transcripción a propósito: Whisper con música encima
# inventa palabras y descoloca los tiempos, y el karaoke depende de que esos
# tiempos sean exactos. Se transcribe la voz limpia y se mezcla para el render.
FUENTE_AV="$VIDEO"
# Biblioteca compartida de audio generado con ElevenLabs (sfx/, musica/, voces/).
AUDIO_LIB_DIR="${AUDIO_LIB_DIR:-$SKILL_DIR/assets/audio}"
MUS_CFG="$(python3 -c "
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
m = p.get('musica') or {}
if isinstance(m, str):
    m = {'path': m}
print(m.get('path', ''))
print(m.get('volumen', 0.18))
print(m.get('inicio_sec', 0))
print(m.get('fade_out', 1.2))
print(1 if m.get('ducking', True) else 0)" "$PLAN")"
MUS_PATH="$(printf '%s' "$MUS_CFG" | sed -n 1p)"

if [ -n "$MUS_PATH" ]; then
  MUS_VOL="$(printf '%s' "$MUS_CFG" | sed -n 2p)"
  MUS_INI="$(printf '%s' "$MUS_CFG" | sed -n 3p)"
  MUS_FADE="$(printf '%s' "$MUS_CFG" | sed -n 4p)"
  MUS_DUCK="$(printf '%s' "$MUS_CFG" | sed -n 5p)"

  # Se busca donde los demás assets: junto al primer clip, en
  # <proyecto>.assets/ y en la librería de la skill (assets/musica/).
  MUS_ABS=""
  for d in "$(dirname "$PRIMERO")" "$PROYECTO.assets" "$SKILL_DIR/assets"; do
    [ -d "$d" ] || continue
    if [ -f "$d/$MUS_PATH" ]; then MUS_ABS="$d/$MUS_PATH"; break; fi
    hit="$(find "$d" -name "$(basename "$MUS_PATH")" -type f -print -quit 2>/dev/null || true)"
    if [ -n "$hit" ]; then MUS_ABS="$hit"; break; fi
  done

  if [ -z "$MUS_ABS" ]; then
    echo "[warning] music '$MUS_PATH' not found - rendering without it"
  else
    FUENTE_AV="$WORKDIR/fuente_musica.mp4"
    REMEZCLAR=0
    if [ ! -f "$FUENTE_AV" ]; then REMEZCLAR=1; fi
    if [ -f "$FUENTE_AV" ] && [ "$VIDEO" -nt "$FUENTE_AV" ]; then REMEZCLAR=1; fi
    if [ -f "$FUENTE_AV" ] && [ "$MUS_ABS" -nt "$FUENTE_AV" ]; then REMEZCLAR=1; fi
    if [ -f "$FUENTE_AV" ] && [ "$PLAN" -nt "$FUENTE_AV" ]; then REMEZCLAR=1; fi
    if [ "$REMEZCLAR" = "1" ]; then
      python3 "$SKILL_DIR/scripts/mezcla_musica.py" "$VIDEO" "$FUENTE_AV" "$MUS_ABS" \
        --volumen "$MUS_VOL" --inicio "$MUS_INI" --fade "$MUS_FADE" --ducking "$MUS_DUCK"
    else
      echo "==> music already mixed (cached)"
    fi
  fi
fi

# ── Efectos de sonido puntuales ────────────────────────────────────────────
# Van DESPUÉS de la música (y siempre después de transcribir) para que se
# monten sobre la mezcla ya hecha. Se buscan en la biblioteca compartida de
# ElevenLabs, junto al clip y en los assets de la skill.
TIENE_SFX="$(python3 -c "
import json,sys
p=json.load(open(sys.argv[1],encoding='utf-8'))
print(1 if (p.get('sfx') or []) else 0)" "$PLAN")"

if [ "$TIENE_SFX" = "1" ]; then
  FUENTE_SFX="$WORKDIR/fuente_sfx.mp4"
  REMEZCLAR_SFX=0
  if [ ! -f "$FUENTE_SFX" ]; then REMEZCLAR_SFX=1; fi
  if [ -f "$FUENTE_SFX" ] && [ "$FUENTE_AV" -nt "$FUENTE_SFX" ]; then REMEZCLAR_SFX=1; fi
  if [ -f "$FUENTE_SFX" ] && [ "$PLAN" -nt "$FUENTE_SFX" ]; then REMEZCLAR_SFX=1; fi
  if [ "$REMEZCLAR_SFX" = "1" ]; then
    python3 "$SKILL_DIR/scripts/mezcla_sfx.py" "$FUENTE_AV" "$FUENTE_SFX" "$PLAN" \
      --libs "$AUDIO_LIB_DIR" "$(dirname "$PRIMERO")" "$PROYECTO.assets" "$SKILL_DIR/assets" \
      && FUENTE_AV="$FUENTE_SFX"
  else
    echo "==> effects already mixed (cached)"
    FUENTE_AV="$FUENTE_SFX"
  fi
fi

# ── Preparar assets para Remotion ──────────────────────────────────────────
# Remotion solo puede leer archivos que estén dentro de remotion/public/.
# Se enlazan (hardlink, instantáneo) o se copian si el enlace no es posible.
JOB="job_$HASH"
PUB="$REMOTION_DIR/public/$JOB"
rm -rf "$PUB"; mkdir -p "$PUB"

SRC_FOR_REMOTION="$FUENTE_AV"
if [ "$QUALITY" = "preview" ] && [ "$W" -gt 1080 ]; then
  # Proxy a 1080 de ancho: el coste dominante de un render es decodificar el
  # vídeo fuente frame a frame. Con material 4K el proxy divide el tiempo
  # entre tres o cuatro. Se cachea contra la fecha del original.
  PROXY="$WORKDIR/proxy_1080.mp4"
  if [ ! -f "$PROXY" ] || [ "$FUENTE_AV" -nt "$PROXY" ]; then
    echo "==> generating 1080p proxy (one time only)"
    ffmpeg -y -loglevel error -i "$FUENTE_AV" -vf "scale=1080:-2" \
      -c:v libx264 -preset veryfast -crf 23 -c:a copy "$PROXY"
  fi
  SRC_FOR_REMOTION="$PROXY"
fi

ln "$SRC_FOR_REMOTION" "$PUB/source.mp4" 2>/dev/null || cp "$SRC_FOR_REMOTION" "$PUB/source.mp4"

# Assets referenciados por el plan (iconos de ítems, imágenes, clips).
# Se buscan junto al vídeo, en <video>.assets/, en la librería de la skill
# (assets/items, assets/musica) y en la biblioteca de imágenes generadas.
python3 - "$PLAN" "$PUB" "$(dirname "$PRIMERO")" "$PROYECTO.assets" "$SKILL_DIR/assets" "$LIB_GENERADOS" <<'PY'
import json, shutil, sys
from pathlib import Path

plan_path, pub, *search = sys.argv[1:]
pub = Path(pub)
search_dirs = [Path(s) for s in search if s and Path(s).is_dir()]
plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))

wanted = []
for b in plan.get("beats", []):
    for key in ("image_path",):
        if b.get(key):
            wanted.append(b[key])
    # emoji_burst puede traer reacciones en PNG dentro de items[].
    for it in b.get("items") or []:
        if isinstance(it, dict) and it.get("image_path"):
            wanted.append(it["image_path"])

missing = []
for rel in wanted:
    if rel.startswith(("http://", "https://")):
        continue
    for d in search_dirs:
        # Búsqueda recursiva: así assets/items/diamante.png se referencia
        # simplemente como "diamante.png" desde el plan.
        hits = [d / rel] if (d / rel).exists() else list(d.rglob(Path(rel).name))
        if hits:
            dst = pub / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(hits[0], dst)
            break
    else:
        missing.append(rel)

if missing:
    print(f"[warning] assets not found (those beats render with no image): {', '.join(missing)}")
PY

# ── props.json ─────────────────────────────────────────────────────────────
python3 - "$PLAN" "$CAPS_PLAN" "$JOB" "$W" "$H" "$FPS_INT" "$FRAMES" \
  "$REMOTION_DIR/src/props.json" <<'PY'
import json, sys
from pathlib import Path

plan_p, caps_p, job, w, h, fps, frames, out_p = sys.argv[1:]
plan = json.loads(Path(plan_p).read_text(encoding="utf-8"))
caps = json.loads(Path(caps_p).read_text(encoding="utf-8"))

beats = plan.get("beats", [])

# Los assets del plan se copian a public/<job>/, asi que la ruta que ve
# Remotion tiene que llevar ese prefijo. Sin esto, staticFile("x.png") pide
# /public/x.png, que no existe, y el render se cae con CancelledError.
for _b in beats:
    _ip = _b.get("image_path")
    if _ip and not _ip.startswith(("http://", "https://")):
        _b["image_path"] = f"{job}/{_ip}"
    # Mismo prefijo para las reacciones en PNG de emoji_burst.
    for _it in _b.get("items") or []:
        if isinstance(_it, dict):
            _iip = _it.get("image_path")
            if _iip and not _iip.startswith(("http://", "https://")):
                _it["image_path"] = f"{job}/{_iip}"

# ── Cámara ─────────────────────────────────────────────────────────────────
# Tres fuentes, en este orden:
#
#   1. La lista `zoom` del plan, si la hay. Son movimientos que no cuelgan de
#      ningún beat (un push sobre gameplay limpio, un temblor en una caída).
#   2. El `zoom` que lleve un beat concreto: `false` lo apaga, `true` pone el
#      golpe por defecto y un objeto ajusta tipo, escala, foco, temblor o giro.
#   3. La derivación automática: cada meme_text y cada counter reciben un punch
#      corto al entrar — es el gesto que empareja el texto con el impacto
#      sonoro. Solo se aplica a los beats que no declaran nada.
#
# Cuando dos momentos se solapan, Short.tsx se queda con el de más escala; no
# se suman.
DEFECTO_AUTO = ("meme_text", "counter")


def momento(b):
    z = b.get("zoom")
    if z is False:
        return None
    automatico = False
    if z is None:
        if b.get("kind") not in DEFECTO_AUTO:
            return None
        z, automatico = {}, True
    elif z is True:
        z = {}
    elif not isinstance(z, dict):
        return None

    tipo = z.get("tipo", "punch")
    # Un push o un pull son movimientos LARGOS: si no se dice otra cosa, duran
    # todo el beat. Un punch es un golpe y dura lo que dura un golpe.
    dur = z.get("duracion")
    if dur is None:
        dur = (b["end_sec"] - b["start_sec"]) if tipo in ("push", "pull") else 0.55
    m = {
        "start_sec": b["start_sec"],
        "end_sec": min(b["end_sec"], b["start_sec"] + dur),
        "scale": z.get("scale", 1.22),
        "tipo": tipo,
    }
    for k in ("focus", "shake", "rot"):
        if z.get(k) is not None:
            m[k] = z[k]
    m["_auto"] = automatico
    return m


explicitos = list(plan.get("zoom") or [])
derivados = [m for m in (momento(b) for b in beats) if m]
if explicitos:
    # Con lista explícita en el plan la derivación automática se calla: si
    # alguien se ha puesto a colocar la cámara a mano, no queremos golpes
    # sorpresa encima. Los zooms declarados DENTRO de un beat sí se respetan.
    derivados = [m for m in derivados if not m["_auto"]]
for m in derivados:
    m.pop("_auto", None)
zoom = explicitos + derivados

props = {
    "videoSrc": f"{job}/source.mp4",
    "beats": beats,
    "zoom": zoom,
    "captions": caps,
    "accent": plan.get("accent", "grass"),
    "grade": plan.get("grade", 1),
    "apertura": plan.get("apertura", 1.12),
    "fps": int(fps),
    "width": int(w),
    "height": int(h),
    "durationInFrames": int(frames),
}
Path(out_p).write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[props] {len(beats)} beats, {len(caps)} caption lines, {len(zoom)} zooms")
PY

# ── Render ─────────────────────────────────────────────────────────────────
if [ "$QUALITY" = "final" ]; then
  OUT="$PROYECTO.final.mp4"
  SCALE=1
  CRF=17
else
  OUT="$PROYECTO.preview.mp4"
  # Remotion exige que ancho y alto resultantes sean ENTEROS, y no redondea:
  # un scale de 0.6667 sobre 1920 da 1280.064 y aborta el render. Peor aún,
  # fracciones "limpias" como 2/3 tampoco valen, porque en coma flotante
  # 1920 * (2/3) = 1279.9999999999998.
  #
  # Por eso el scale se elige solo entre fracciones EXACTAS en binario
  # (0.75, 0.5, 0.25): esas multiplican sin error de representación. Se coge
  # la mayor que deje el ancho por debajo de ~820 px y que dé dimensiones
  # pares (h264 las necesita pares).
  SCALE="$(python3 -c '
import sys
w, h = int(sys.argv[1]), int(sys.argv[2])
for s in (0.75, 0.5, 0.25):
    tw, th = w * s, h * s
    if tw <= 820 and tw == int(tw) and th == int(th) and int(tw) % 2 == 0 and int(th) % 2 == 0:
        print(s); break
else:
    print(1)
' "$W" "$H")"
  CRF=23
fi

# Caché: si props.json y las plantillas no han cambiado desde el último
# render correcto, no hay nada que hacer.
FP_FILE="$WORKDIR/.fp.$QUALITY"
FP="$(cat "$REMOTION_DIR/src/props.json"; find "$REMOTION_DIR/src" \( -name '*.tsx' -o -name '*.ts' \) -exec stat -c '%n %Y' {} \; 2>/dev/null | sort; stat -c '%Y' "$SRC_FOR_REMOTION" 2>/dev/null)"
FP_HASH="$(printf '%s' "$FP" | sha1sum | cut -d' ' -f1)"
if [ "${FORCE_RENDER:-0}" != "1" ] && [ -f "$FP_FILE" ] && [ "$(cat "$FP_FILE")" = "$FP_HASH" ] && [ -f "$OUT" ]; then
  echo "==> no changes since the last render - $OUT"
  exit 0
fi

echo "==> rendering ($QUALITY, scale $SCALE) -> $OUT"
(cd "$REMOTION_DIR" && npx --no-install remotion render src/index.ts Short "$(towin "$OUT")" \
  --scale="$SCALE" --crf="$CRF" --log=error)

# La huella se escribe SOLO tras un render correcto: si Remotion peta a medias,
# la próxima ejecución no debe creerse que ya está hecho.
printf '%s' "$FP_HASH" > "$FP_FILE"

echo ""
echo "==> done: $OUT"
if [ "$QUALITY" != "final" ]; then
  echo "    Review it, and when it looks right, render the delivery:"
  echo "    QUALITY=final bash scripts/render.sh$(printf ' \"%s\"' "${CLIPS[@]}")"
fi
