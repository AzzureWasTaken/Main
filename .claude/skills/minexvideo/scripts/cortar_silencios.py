#!/usr/bin/env python3
"""
Quita los silencios largos de la fuente para bajar la duracion del short.

    cortar_silencios.py <entrada.mp4> <salida.mp4> <mapa.json>
                        [--umbral-db -35] [--min 0.35] [--dejar 0.12]

Existe por una razon muy concreta: **la licencia de musica del catalogo de
Shorts solo cubre hasta 60 segundos**. A partir de ahi Content ID trata la
cancion como copyright sin licencia, y un Short de entre 1 y 3 minutos con una
reclamacion activa se bloquea globalmente. Recortar los huecos muertos es la
forma menos invasiva de entrar en los 60 s: no acelera la narracion ni toca
lo que se dice.

**No corta a lo bruto.** De cada silencio deja `--dejar` segundos, para que la
narracion siga respirando entre frase y frase. Un corte a cero suena atropellado
y delata el montaje.

Nunca toca el primer medio segundo: ahi vive el `hook_title`, y arrancar el
short a media accion se carga el gancho.

`mapa.json` guarda los tramos eliminados. Es lo que permite recolocar los beats
de un plan ya escrito: cortar NO es una escala lineal como acelerar, cada beat
se desplaza segun cuanto silencio haya por delante de el.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

NO_TOCAR_INICIO = 0.5


def duracion(path: Path) -> float:
    o = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(o.stdout.strip())


def detecta_silencios(path: Path, umbral_db: float, min_dur: float) -> list[tuple[float, float]]:
    o = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path),
         "-af", f"silencedetect=noise={umbral_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True)
    silencios, ini = [], None
    for linea in o.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", linea)
        if m:
            ini = float(m.group(1))
            continue
        m = re.search(r"silence_end: ([\d.]+)", linea)
        if m and ini is not None:
            silencios.append((max(0.0, ini), float(m.group(1))))
            ini = None
    return silencios


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("mapa")
    ap.add_argument("--umbral-db", type=float, default=-35.0)
    ap.add_argument("--min", dest="min_dur", type=float, default=0.35)
    ap.add_argument("--dejar", type=float, default=0.12,
                    help="segundos de silencio que se conservan en cada hueco")
    args = ap.parse_args()

    entrada, salida, mapa_p = Path(args.entrada), Path(args.salida), Path(args.mapa)
    dur = duracion(entrada)

    # Tramos a ELIMINAR: el silencio menos el margen que se deja respirar.
    quitar = []
    for s, e in detecta_silencios(entrada, args.umbral_db, args.min_dur):
        s2 = max(s + args.dejar, NO_TOCAR_INICIO)
        if e - s2 > 0.05:                      # por debajo de 50 ms no compensa
            quitar.append((round(s2, 3), round(e, 3)))

    if not quitar:
        print("[silences] no gaps worth removing")
        mapa_p.write_text("[]", encoding="utf-8")
        return

    # Tramos a CONSERVAR = el complemento de los anteriores.
    conservar, t = [], 0.0
    for s, e in quitar:
        if s > t:
            conservar.append((t, s))
        t = e
    if t < dur:
        conservar.append((t, dur))

    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in conservar)
    # `select` + `setpts` reconstruye una linea de tiempo continua a partir de
    # los trozos que sobreviven. Hay que recodificar: no existe forma de cortar
    # en puntos arbitrarios copiando el flujo tal cual.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(entrada),
         "-filter_complex",
         f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB[v];"
         f"[0:a]aselect='{expr}',asetpts=N/SR/TB[a]",
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         str(salida)],
        check=True,
    )

    mapa_p.write_text(json.dumps(quitar, indent=2), encoding="utf-8")
    quitado = sum(b - a for a, b in quitar)
    print(f"[silencios] {len(quitar)} huecos, -{quitado:.2f}s "
          f"({dur:.2f}s -> {duracion(salida):.2f}s), dejando {args.dejar}s en cada uno")


if __name__ == "__main__":
    main()
