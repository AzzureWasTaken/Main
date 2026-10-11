#!/usr/bin/env bash
# Instalación idempotente de la skill. Se puede relanzar sin miedo.
#
#   bash scripts/setup.sh
#
# Comprueba ffmpeg, crea el venv de Python (con los enlaces bin/ que necesitan
# los scripts en Windows), instala WhisperX y las dependencias de Remotion.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTION_DIR="$SKILL_DIR/remotion"
VENV="$SKILL_DIR/.venv"

echo "==> minexvideo — setup ($SKILL_DIR)"

# ── ffmpeg ─────────────────────────────────────────────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[error] ffmpeg is not on the PATH."
  echo "        Windows: winget install --id Gyan.FFmpeg -e"
  echo "        macOS:   brew install ffmpeg"
  exit 1
fi
echo "    ffmpeg: $(ffmpeg -version | head -n1 | cut -c1-60)"

# ── Python ─────────────────────────────────────────────────────────────────
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || { echo "[error] Python 3.10 or newer is required"; exit 1; }
echo "    python: $($PY --version)"

if [ ! -d "$VENV" ]; then
  echo "==> creating venv in $VENV"
  "$PY" -m venv "$VENV"
fi

# En Windows el venv crea Scripts/ en vez de bin/. Los scripts de la skill
# esperan bin/, así que se replican ahí. Son copias del ejecutable, no enlaces:
# el lanzador del venv localiza pyvenv.cfg subiendo un nivel desde su propia
# ubicación, y desde bin/ eso sigue apuntando al venv correcto.
if [ -d "$VENV/Scripts" ] && [ ! -f "$VENV/bin/python3" ]; then
  echo "==> creating bin/ links for Windows"
  mkdir -p "$VENV/bin"
  for n in python python3 python.exe python3.exe; do
    cp "$VENV/Scripts/python.exe" "$VENV/bin/$n"
  done
fi

PIP="$VENV/Scripts/pip.exe"
[ -f "$PIP" ] || PIP="$VENV/bin/pip"
VPY="$VENV/Scripts/python.exe"
[ -f "$VPY" ] || VPY="$VENV/bin/python3"

# ── WhisperX ───────────────────────────────────────────────────────────────
if ! "$VPY" -c "import whisperx" >/dev/null 2>&1; then
  echo "==> installing WhisperX (slow, several GB)"
  "$PIP" install --quiet whisperx
fi
echo "    whisperx: $("$VPY" -c 'import importlib.metadata as m; print(m.version("whisperx"))')"

# ── Torch con CUDA ─────────────────────────────────────────────────────────
# WhisperX arrastra la build de torch para CPU. Si hay GPU NVIDIA merece
# muchísimo la pena sustituirla por la de CUDA: la transcripción pasa de
# minutos a segundos. Hay que fijar la MISMA versión que pide whisperx o pip
# volverá a degradarla en la siguiente instalación.
if command -v nvidia-smi >/dev/null 2>&1; then
  if ! "$VPY" -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    TORCH_V="$("$VPY" -c 'import torch; print(torch.__version__.split("+")[0])' 2>/dev/null || echo "")"
    if [ -n "$TORCH_V" ]; then
      echo "==> NVIDIA GPU found but torch is the CPU build; installing CUDA 12.8"
      "$PIP" install --quiet --force-reinstall \
        "torch==$TORCH_V" "torchaudio==$TORCH_V" \
        --index-url https://download.pytorch.org/whl/cu128 || \
        echo "[warning] could not install the CUDA build; it will keep working on CPU"
    fi
  fi
  echo "    cuda: $("$VPY" -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "not available")')"
fi

# ── Remotion ───────────────────────────────────────────────────────────────
command -v npm >/dev/null 2>&1 || { echo "[error] Node 18+ is required"; exit 1; }
if [ ! -d "$REMOTION_DIR/node_modules" ]; then
  echo "==> npm install in $REMOTION_DIR"
  (cd "$REMOTION_DIR" && npm install --silent)
fi
echo "    remotion: $(cd "$REMOTION_DIR" && node -e 'console.log(require("./node_modules/remotion/package.json").version)')"

mkdir -p "$REMOTION_DIR/public" "$SKILL_DIR/assets/items"

echo "==> setup complete"
