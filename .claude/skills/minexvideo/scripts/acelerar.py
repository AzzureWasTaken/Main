#!/usr/bin/env python3
"""
Acelera (o ralentiza) la fuente antes de que el resto del pipeline la toque.

    acelerar.py <entrada.mp4> <salida.mp4> <factor>

Un short a 1.25x-1.5x se siente mucho mas agil, y es lo normal en el formato:
recorta los silencios entre frases sin tener que cortar nada a mano, y mete mas
contenido en menos segundos, que es lo que decide si alguien llega al final.

**Se aplica ANTES de transcribir**, y esa es toda la gracia del sitio donde
esta puesto. Si se acelerase despues, cada timestamp de `words.json` y cada
`start_sec` del plan quedarian desplazados y habria que reescalarlos a mano —
justo el tipo de cuenta que se hace mal una vez y descuadra el karaoke entero.
Acelerando primero, todo lo que viene despues mide sobre la linea de tiempo
final y no se entera de nada.

Consecuencia para quien escribe el plan: **los `start_sec` van en segundos del
video YA acelerado**. Con factor 1.5, el segundo 90 del bruto es el 60 del plan.

El tono de la voz NO sube: `atempo` cambia la duracion sin tocar el pitch. Sin
eso, la narracion sonaria a ardilla y el canal perderia su voz.
"""
import subprocess
import sys
from pathlib import Path


def cadena_atempo(factor: float) -> str:
    """`atempo` solo acepta 0.5-2.0 por instancia; fuera de ahi se encadena.

    Para 1.5 basta una. Para 3.0 harian falta dos (1.732 * 1.732). Se resuelve
    en general para que la skill no se rompa si algun dia se pide un 2.5x.
    """
    partes, f = [], factor
    while f > 2.0:
        partes.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        partes.append("atempo=0.5")
        f /= 0.5
    partes.append(f"atempo={f:.6f}")
    return ",".join(partes)


def tiene_audio(path: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return bool(out.stdout.strip())


def main() -> None:
    if len(sys.argv) < 4:
        print("uso: acelerar.py <entrada.mp4> <salida.mp4> <factor>", file=sys.stderr)
        sys.exit(2)

    entrada, salida, factor = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])
    if factor <= 0:
        print(f"[error] invalid factor: {factor}", file=sys.stderr)
        sys.exit(1)

    # fps de origen: se conserva para que el movimiento siga igual de fluido.
    # Sin fijarlo, `setpts` deja timestamps comprimidos y algunos reproductores
    # deducen un framerate raro.
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(entrada)],
        capture_output=True, text=True, check=True,
    )
    fps_raw = out.stdout.strip()
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    except ValueError:
        fps = float(fps_raw or 30)

    filtros = [f"[0:v]setpts=PTS/{factor},fps={fps:.4f}[v]"]
    mapas = ["-map", "[v]"]
    if tiene_audio(entrada):
        filtros.append(f"[0:a]{cadena_atempo(factor)},aresample=48000[a]")
        mapas += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]

    salida.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(entrada),
         "-filter_complex", ";".join(filtros), *mapas,
         # crf 16: esto es un master de trabajo del que despues sale el render
         # final, asi que se comprime poco para no acumular perdidas.
         "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", str(salida)],
        check=True,
    )

    def dur(p: Path) -> float:
        o = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
        return float(o.stdout.strip())

    print(f"[velocidad] x{factor} — {dur(entrada):.2f}s -> {dur(salida):.2f}s "
          f"(el plan mide sobre los {dur(salida):.2f}s)")


if __name__ == "__main__":
    main()
