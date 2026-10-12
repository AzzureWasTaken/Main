#!/usr/bin/env python3
"""
Transcribe un short a timestamps por PALABRA usando WhisperX, en español.

Salida: <workdir>/words.json  ->  [{"word": "...", "start": 1.23, "end": 1.55}, ...]

Por qué por palabra y no por frase: los subtítulos karaoke necesitan saber
cuándo empieza y acaba CADA palabra para resaltarla en el momento exacto. Un
timestamp por frase no da para eso.

Este script se relanza solo dentro del venv de la skill si lo llamas con el
Python del sistema — whisperx y torch viven ahí, no en el Python global.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_DIR = SKILL_DIR / ".venv"

# En Windows el ejecutable del venv está en Scripts/, en Linux/macOS en bin/.
# El instalador de esta skill crea copias en bin/ también, así que probamos
# los dos y usamos el primero que exista.
_CANDIDATES = [
    VENV_DIR / "Scripts" / "python.exe",
    VENV_DIR / "bin" / "python3",
    VENV_DIR / "bin" / "python",
]


def _relaunch_in_venv() -> None:
    """Vuelve a lanzarse con el intérprete del venv si no estamos ya en él.

    El chequeo usa sys.prefix y no una comparación de rutas de ejecutable: en
    algunas instalaciones el python del venv es un enlace al real y las rutas
    resueltas coinciden aunque NO estemos dentro del venv. sys.prefix es lo
    que de verdad determina qué site-packages hay en el import path.
    """
    try:
        if Path(sys.prefix).resolve() == VENV_DIR.resolve():
            return  # ya estamos dentro
    except OSError:
        pass
    for exe in _CANDIDATES:
        if exe.exists():
            # subprocess y no os.execv: en Windows, execv NO entrecomilla los
            # argumentos, así que una ruta con espacios ("SHORT 1/BRUTO/x.mp4")
            # llega partida en dos y el script recibe una ruta truncada. Con
            # subprocess el quoting lo hace la librería y las rutas sobreviven.
            # El coste es un proceso padre esperando, que no molesta a nadie.
            sys.exit(subprocess.run(
                [str(exe), os.path.abspath(__file__), *sys.argv[1:]]).returncode)
    print(
        f"[error] venv interpreter not found in {VENV_DIR}\n"
        f"        run: bash {SKILL_DIR / 'scripts' / 'setup.sh'}",
        file=sys.stderr,
    )
    sys.exit(1)


_relaunch_in_venv()

import torch  # noqa: E402  (import tardío: solo existe dentro del venv)
import whisperx  # noqa: E402


def workdir_for(video: Path) -> Path:
    """Directorio de trabajo en ~/.cache/minexvideo/<hash>/.

    Vive fuera de la carpeta del vídeo a propósito: así los intermedios no
    ensucian la carpeta de grabaciones ni se suben a la nube si el vídeo está
    dentro de OneDrive o Drive.
    """
    h = hashlib.sha1(str(video.resolve()).encode("utf-8")).hexdigest()[:16]
    d = Path.home() / ".cache" / "minexvideo" / h
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract_audio(video: Path, out_wav: Path) -> None:
    """Extrae audio mono a 16 kHz — el formato que espera Whisper."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", str(out_wav)],
        check=True,
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: transcribe.py <video> [--modelo large-v3] [--idioma en] "
              "[--workdir <dir>] [--forzar]",
              file=sys.stderr)
        sys.exit(1)

    video = Path(sys.argv[1]).resolve()
    if not video.exists():
        print(f"[error] file not found: {video}", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[2:]
    model_name = (args[args.index("--modelo") + 1] if "--modelo" in args
                  else os.environ.get("WHISPER_MODEL", "large-v3"))
    lang = (args[args.index("--idioma") + 1] if "--idioma" in args
            else os.environ.get("WHISPER_LANG", "en"))

    # --workdir fuerza el directorio de trabajo. Hace falta cuando la fuente es
    # un montaje de varios clips: ese archivo vive DENTRO del workdir, asi que
    # derivar el workdir de su ruta daria otro directorio distinto y render.sh
    # no encontraria el words.json.
    wd = (Path(args[args.index("--workdir") + 1]).resolve()
          if "--workdir" in args else workdir_for(video))
    wd.mkdir(parents=True, exist_ok=True)
    out_json = wd / "words.json"
    if out_json.exists() and "--forzar" not in args:
        print(f"[transcribe] already done (cached): {out_json}")
        print(f"[transcribe] workdir: {wd}")
        return

    # float16 solo tiene sentido en GPU. En CPU hay que bajar a int8 o
    # ctranslate2 protesta y encima va más lento.
    use_gpu = torch.cuda.is_available()
    device = "cuda" if use_gpu else "cpu"
    compute = "float16" if use_gpu else "int8"
    print(f"[transcribe] device={device} model={model_name} language={lang}")

    wav = wd / "audio.wav"
    if not wav.exists():
        extract_audio(video, wav)

    model = whisperx.load_model(model_name, device, compute_type=compute, language=lang)
    audio = whisperx.load_audio(str(wav))
    result = model.transcribe(audio, batch_size=16 if use_gpu else 4, language=lang)

    # Alineación forzada: el paso que convierte timestamps por frase en
    # timestamps por palabra. Sin esto no hay subtítulos karaoke.
    # La primera vez descarga el modelo de alineación en español
    # (jonatasgrosman/wav2vec2-large-xlsr-53-spanish, ~1.2 GB) desde
    # HuggingFace; después queda en caché local.
    align_model, metadata = whisperx.load_align_model(language_code=lang, device=device)
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, device,
        return_char_alignments=False,
    )

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            txt = (w.get("word") or "").strip()
            # WhisperX deja sin timestamp alguna palabra que no logra alinear
            # (números escritos raro, onomatopeyas, risas). Se descartan: una
            # palabra sin tiempo rompería el resaltado karaoke.
            if not txt or w.get("start") is None or w.get("end") is None:
                continue
            words.append({
                "word": txt,
                "start": round(float(w["start"]), 3),
                "end": round(float(w["end"]), 3),
            })

    out_json.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    dur = words[-1]["end"] if words else 0
    print(f"[transcribe] {len(words)} words, {dur:.1f}s -> {out_json}")
    print(f"[transcribe] workdir: {wd}")


if __name__ == "__main__":
    main()
