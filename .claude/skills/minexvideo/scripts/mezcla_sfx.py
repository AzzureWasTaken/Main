#!/usr/bin/env python3
"""
Superpone efectos de sonido puntuales sobre el audio del short.

    mezcla_sfx.py <video_in> <video_out> <plan.json> [--libs DIR ...]

Lee la lista `sfx` del plan:

    "sfx": [
      { "path": "whoosh.mp3", "at_sec": 3.2, "volumen": 0.8 },
      { "path": "impacto.mp3", "at_sec": 7.0 }
    ]

El video NO se recodifica (`-c:v copy`): solo se rehace la pista de audio, asi
que es cuestion de segundos.

**Se mezcla DESPUES de transcribir**, igual que la musica: Whisper con efectos
encima inventa palabras y descoloca el karaoke.

Los efectos se SUMAN al audio original a ganancia unidad (`normalize=0`), que
es como suena natural — un whoosh no debe agachar la voz, debe montarse encima.
Al final pasa por un limitador para que la suma no sature.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def tiene_audio(path: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return bool(out.stdout.strip())


def localizar(nombre: str, libs: list[Path]) -> Path | None:
    p = Path(nombre)
    if p.is_absolute() and p.exists():
        return p
    for d in libs:
        if not d.is_dir():
            continue
        directo = d / nombre
        if directo.exists():
            return directo
        hits = list(d.rglob(p.name))
        if hits:
            return hits[0]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_in")
    ap.add_argument("video_out")
    ap.add_argument("plan")
    ap.add_argument("--libs", nargs="*", default=[])
    args = ap.parse_args()

    video_in = Path(args.video_in)
    video_out = Path(args.video_out)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    libs = [Path(x) for x in args.libs]

    sfx = plan.get("sfx") or []
    if not sfx:
        print("[sfx] the plan has no effects - nothing to mix")
        return 0

    entradas, filtros, etiquetas = [], [], []
    faltan = []
    for i, s in enumerate(sfx):
        nombre = s.get("path")
        if not nombre:
            continue
        ruta = localizar(nombre, libs)
        if ruta is None:
            faltan.append(nombre)
            continue
        at_ms = int(round(float(s.get("at_sec", 0)) * 1000))
        vol = float(s.get("volumen", 0.85))
        # `entradas` crece de dos en dos ("-i" + ruta); el indice de ffmpeg es
        # el numero de entradas reales, y el 0 lo ocupa el video.
        idx = len(entradas) // 2 + 1
        entradas += ["-i", str(ruta)]
        et = f"s{idx}"
        # adelay necesita un retardo por canal; `all=1` lo aplica a todos.
        filtros.append(f"[{idx}:a]volume={vol},adelay={at_ms}:all=1[{et}]")
        etiquetas.append(f"[{et}]")

    if faltan:
        print(f"[sfx][warning] not found: {', '.join(faltan)}")
    if not etiquetas:
        print("[sfx] no effect located - copying the video as-is")
        subprocess.run(["ffmpeg", "-y", "-i", str(video_in), "-c", "copy",
                        str(video_out), "-loglevel", "error"], check=True)
        return 0

    if tiene_audio(video_in):
        fuentes = "[0:a]" + "".join(etiquetas)
        n = len(etiquetas) + 1
    else:
        fuentes = "".join(etiquetas)
        n = len(etiquetas)

    # normalize=0 suma sin bajar el volumen de cada fuente; alimiter evita que
    # la suma sature en los picos donde coinciden voz y efecto.
    filtros.append(f"{fuentes}amix=inputs={n}:duration=first:normalize=0[mix]")
    filtros.append("[mix]alimiter=limit=0.95[a]")

    cmd = ["ffmpeg", "-y", "-i", str(video_in), *entradas,
           "-filter_complex", ";".join(filtros),
           "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           str(video_out), "-loglevel", "error"]
    subprocess.run(cmd, check=True)
    print(f"[sfx] {len(etiquetas)} effect(s) mixed -> {video_out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
