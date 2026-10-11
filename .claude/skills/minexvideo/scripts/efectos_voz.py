#!/usr/bin/env python3
"""
Efectos puntuales sobre la voz — el gesto de doblarse a uno mismo.

    efectos_voz.py <entrada.mp4> <salida.mp4> --efectos '<json>'

    [{"start_sec": 12.4, "end_sec": 14.0, "tipo": "agudo"},
     {"start_sec": 31.0, "end_sec": 33.2, "tipo": "grave", "intensidad": 1.4}]

En los shorts de gameplay la voz no es solo narración: es el personaje. Subirle
el tono cuando pone voz de aldeano, bajárselo cuando hace de villano o meterla
por un megáfono cuando "habla el servidor" hace el mismo trabajo que un
bocadillo, pero sin tapar un solo píxel de gameplay. Por eso está aquí y no en
las plantillas.

Cinco tipos:

  | tipo       | qué suena                              | para qué |
  |------------|----------------------------------------|----------|
  | `agudo`    | pitch arriba, duración intacta         | aldeanos, niños, pánico |
  | `grave`    | pitch abajo                            | villano, "modo serio", amenaza |
  | `megafono` | banda estrecha + compresión            | megafonía, radio, "habla el server" |
  | `eco`      | repeticiones que se apagan             | revelación, eco de cueva |
  | `robot`    | fase aplanada                          | golem, comando, IA |

**La duración se conserva exactamente.** No es un detalle: los subtítulos
karaoke ya están calculados sobre estos mismos segundos, y un efecto que
estirase el audio los descuadraría todos a partir de ahí. `rubberband` cambia
el tono sin tocar la duración; si no está compilado, se cae al apaño clásico
(`asetrate` + `atempo` compensando), que suena algo peor pero mide igual.

**La imagen no se recodifica** (`-c:v copy`), así que esto no cuesta calidad ni
tiempo de render.

Va DESPUÉS de la censura a propósito: el pitido de 1 kHz tiene que salir a 1 kHz
y no transportado, y la transcripción ya está hecha sobre la voz limpia.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SR = 48000
FUNDIDO = 0.012          # 12 ms en cada juntura: no se oye, pero mata el clic
TIPOS = ("agudo", "grave", "megafono", "eco", "robot")


def hay_rubberband() -> bool:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                         capture_output=True, text=True)
    return " rubberband " in out.stdout


def duracion(path: Path) -> float:
    o = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(o.stdout.strip())


def tiene_audio(path: Path) -> bool:
    o = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    return bool(o.stdout.strip())


def cadena_pitch(k: float, rb: bool) -> str:
    """Cambia el tono SIN cambiar la duración."""
    if rb:
        return "rubberband=pitch=%.4f:pitchq=quality" % k
    # Apaño sin rubberband: acelerar la cinta sube tono y velocidad, y `atempo`
    # devuelve la velocidad dejando el tono arriba. Encadenado porque `atempo`
    # solo acepta 0.5-2.0.
    inv, partes = 1.0 / k, []
    f = inv
    while f > 2.0:
        partes.append("atempo=2.0"); f /= 2.0
    while f < 0.5:
        partes.append("atempo=0.5"); f /= 0.5
    partes.append("atempo=%.6f" % f)
    return "asetrate=%d,aresample=%d,%s" % (int(SR * k), SR, ",".join(partes))


def cadena_efecto(tipo: str, intensidad: float, rb: bool) -> str:
    i = max(0.2, min(2.0, intensidad))
    if tipo == "agudo":
        # 1.25 con intensidad 1: se nota que es otro personaje y todavía se
        # entiende cada palabra. Por encima de 1.5 empieza a ser ininteligible.
        return cadena_pitch(min(1.6, 1 + 0.25 * i), rb)
    if tipo == "grave":
        # Bajar tiene menos margen que subir: por debajo de 0.7 la voz se
        # convierte en un gruñido y se pierde la letra.
        return cadena_pitch(max(0.68, 1 - 0.18 * i), rb)
    if tipo == "megafono":
        return ("highpass=f=%d,lowpass=f=%d,acompressor=threshold=0.05:ratio=6:attack=5:release=90,"
                "volume=%.2f" % (int(600 + 200 * i), int(3400 - 400 * i), 1 + 0.25 * i))
    if tipo == "eco":
        return "aecho=0.8:0.88:%d|%d:%.2f|%.2f" % (
            int(140 * i), int(280 * i), 0.35 * i, 0.22 * i)
    if tipo == "robot":
        return ("afftfilt=real='hypot(re,im)*cos(0)':imag='hypot(re,im)*sin(0)':"
                "win_size=512:overlap=0.75")
    raise SystemExit("[error] tipo de efecto desconocido: %s (válidos: %s)"
                     % (tipo, ", ".join(TIPOS)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--efectos", required=True)
    a = ap.parse_args()

    entrada, salida = Path(a.entrada), Path(a.salida)
    efectos = json.loads(a.efectos)
    if not isinstance(efectos, list) or not efectos:
        sys.exit("[error] --efectos tiene que ser una lista JSON no vacía")
    if not tiene_audio(entrada):
        sys.exit("[error] la fuente no tiene pista de audio")

    dur = duracion(entrada)
    rb = hay_rubberband()

    limpio = []
    for i, e in enumerate(efectos):
        s = max(0.0, float(e["start_sec"]))
        t = min(dur, float(e["end_sec"]))
        if t - s < 0.08:
            print("[warning] effect[%d] lasts %.2fs - too short to be heard, skipped"
                  % (i, t - s))
            continue
        limpio.append({"start": s, "end": t, "tipo": e.get("tipo", "agudo"),
                       "intensidad": float(e.get("intensidad", 1.0))})
    limpio.sort(key=lambda x: x["start"])
    for x, y in zip(limpio, limpio[1:]):
        if y["start"] < x["end"]:
            sys.exit("[error] dos efectos de voz se solapan en [%.2f, %.2f]"
                     % (y["start"], x["end"]))
    if not limpio:
        sys.exit("[error] no queda ningún efecto aplicable")

    # La pista se parte en trozos CONSECUTIVOS y se vuelve a pegar. Es la forma
    # de garantizar que la suma mide exactamente lo mismo que el original: cada
    # trozo se fuerza a su duración con `apad` + `atrim`, así que ni rubberband
    # ni aecho pueden arrastrar unos milisegundos y descuadrar el karaoke.
    partes, etiquetas, n = [], [], 0
    cursor = 0.0

    def trozo(ini: float, fin: float, fx: str | None) -> None:
        nonlocal n
        d = fin - ini
        if d <= 1e-4:
            return
        cad = ["[0:a]atrim=start=%.4f:end=%.4f" % (ini, fin), "asetpts=PTS-STARTPTS"]
        if fx:
            cad.append(fx)
            cad.append("afade=t=in:st=0:d=%.3f" % FUNDIDO)
            cad.append("afade=t=out:st=%.4f:d=%.3f" % (max(0.0, d - FUNDIDO), FUNDIDO))
        cad.append("apad=whole_dur=%.4f" % d)
        cad.append("atrim=0:%.4f" % d)
        cad.append("aresample=%d,aformat=channel_layouts=stereo" % SR)
        partes.append(",".join(cad) + "[p%d]" % n)
        etiquetas.append("[p%d]" % n)
        n += 1

    for e in limpio:
        trozo(cursor, e["start"], None)
        trozo(e["start"], e["end"], cadena_efecto(e["tipo"], e["intensidad"], rb))
        cursor = e["end"]
    trozo(cursor, dur, None)

    partes.append("%sconcat=n=%d:v=0:a=1[aout]" % ("".join(etiquetas), len(etiquetas)))

    salida.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(entrada),
         "-filter_complex", ";".join(partes),
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         str(salida)],
        check=True,
    )

    real = duracion(salida)
    print("[voice] %d effect(s)%s" % (len(limpio), "" if rb else " (no rubberband: atempo fallback)"))
    for e in limpio:
        print("      %6.2f-%6.2f  %s%s" % (
            e["start"], e["end"], e["tipo"],
            "" if abs(e["intensidad"] - 1) < 1e-6 else " x%.2g" % e["intensidad"]))
    if abs(real - dur) > 0.08:
        print("[warning] duration changed (%.2fs -> %.2fs). Captions from that "
              "point on will be out of sync." % (dur, real))


if __name__ == "__main__":
    main()
