#!/usr/bin/env python3
"""
Rampas de velocidad y congelados — el ritmo POR TRAMOS, no del short entero.

    ritmo.py <entrada.mp4> <salida.mp4> <mapa.json> --ops '<json>'

`velocidad` (acelerar.py) mueve el short entero con un solo número. Eso sirve
para meter 90 segundos de bruto en 58, pero no es lo que hace un editor: un
editor acelera lo que no aporta —el camino de vuelta a casa, la excavación, el
crafteo— y frena justo donde está el golpe. La diferencia de ritmo entre un
tramo y el siguiente es lo que se lee como "montaje", y un factor global no la
produce nunca porque comprime también los remates.

Tres operaciones, todas declaradas en segundos de la fuente que entra aquí:

    {"tipo": "rampa",     "start_sec": 12.0, "end_sec": 20.0, "factor": 3.0}
    {"tipo": "rampa",     "start_sec": 31.2, "end_sec": 32.4, "factor": 0.5,
                          "tono": "sigue"}
    {"tipo": "congelado", "en_sec": 24.8, "duracion": 0.7}

`factor` > 1 acelera, < 1 ralentiza. `tono` decide qué le pasa a la voz:

  * `mantiene` (por defecto) — `atempo`: cambia la duración sin tocar el pitch.
    Es lo correcto cuando hay narración dentro del tramo.
  * `sigue` — `asetrate`: el pitch sube o baja con la velocidad, como una cinta.
    Ralentizar con `sigue` es el "vwoooom" grave del cámara lenta dramático; es
    un gesto cómico, no un ajuste de duración. Solo en tramos cortos.

`congelado` clava un frame durante N segundos con el audio en silencio. Es el
gesto de "y aquí es donde la lié": el frame se para, entra el texto, y sigue.
Como mete silencio, tiene que caer en un hueco de la narración — `lint_plan.py`
lo comprueba contra la transcripción.

**Por qué va antes de transcribir**, igual que `acelerar.py`: si se aplicase
después, cada timestamp de `words.json` y cada `start_sec` del plan quedarían
desplazados de forma NO lineal (cada beat se mueve según cuántas rampas tenga
por delante) y recolocarlos a mano es la clase de cuenta que se hace mal.

El mapa que escribe (`mapa.json`) es la traducción entre las dos líneas de
tiempo, y es lo que usa `tiempo.py` para reescalar la transcripción y para
convertir tiempos a mano.

**Los bordes se ajustan a frame.** Un corte a mitad de frame lo redondea ffmpeg
por su cuenta y entonces el mapa analítico y el vídeo real dejan de coincidir.
Se redondea aquí, y lo redondeado es lo que se escribe en el mapa.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SR = 48000


def cadena_atempo(factor: float) -> str:
    """`atempo` solo acepta 0.5-2.0 por instancia; fuera de ahi se encadena."""
    partes, f = [], factor
    while f > 2.0:
        partes.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        partes.append("atempo=0.5")
        f /= 0.5
    partes.append("atempo=%.6f" % f)
    return ",".join(partes)


def sonda(path: Path) -> tuple[float, float, bool]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    lineas = [x for x in out.stdout.split() if x]
    fps_raw, dur = lineas[0], float(lineas[1])
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    except ValueError:
        fps = float(fps_raw or 30)
    a = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return fps, dur, bool(a.stdout.strip())


def normaliza_ops(ops: list[dict], dur: float, fps: float) -> list[dict]:
    """Valida, ordena y ajusta a frame.

    Aborta si algo no cuadra: una rampa mal puesta no se ve rara, descuadra
    TODO lo que viene detrás.
    """
    limpio = []
    for i, op in enumerate(ops):
        tipo = op.get("tipo", "rampa")
        if tipo == "congelado":
            p = float(op["en_sec"])
            d = float(op.get("duracion", 0.6))
            if d <= 0:
                sys.exit("[error] ops[%d]: la `duracion` del congelado tiene que ser > 0" % i)
            p = round(p * fps) / fps
            limpio.append({"tipo": "congelado", "src_start": p, "src_end": p,
                           "dur_salida": d})
        else:
            a = round(float(op["start_sec"]) * fps) / fps
            b = round(float(op["end_sec"]) * fps) / fps
            f = float(op.get("factor", 1.0))
            if b <= a:
                sys.exit("[error] ops[%d]: end_sec (%s) no es mayor que start_sec (%s)" % (i, b, a))
            if not (0.15 <= f <= 8.0):
                sys.exit("[error] ops[%d]: factor %s fuera de rango (0.15-8.0)" % (i, f))
            limpio.append({"tipo": "rampa", "src_start": a, "src_end": b, "factor": f,
                           "tono": op.get("tono", "mantiene"),
                           "silencio": bool(op.get("silencio", False))})

    limpio.sort(key=lambda o: (o["src_start"], o["src_end"]))
    for x, y in zip(limpio, limpio[1:]):
        if y["src_start"] < x["src_end"] - 1e-6:
            sys.exit("[error] dos operaciones de ritmo se solapan en [%.2f, %.2f] "
                     "- sepáralas" % (y["src_start"], x["src_end"]))
    if limpio and limpio[-1]["src_end"] > dur + 0.05:
        sys.exit("[error] una operación acaba en %.2fs pero la fuente dura %.2fs"
                 % (limpio[-1]["src_end"], dur))
    return limpio


def construye_tramos(ops: list[dict], dur: float, fps: float) -> list[dict]:
    """Parte la línea de tiempo en tramos consecutivos, cada uno con su factor.

    Los huecos entre operaciones son tramos normales (factor 1). El resultado
    cubre la fuente entera sin solapes ni agujeros, que es justo lo que hace
    falta para que el mapa sea una función monótona y se pueda invertir.
    """
    tramos: list[dict] = []
    cursor_src, cursor_out = 0.0, 0.0

    def agrega(src_a: float, src_b: float, factor: float, tipo: str,
               dur_salida: float | None = None, **extra) -> None:
        nonlocal cursor_out
        salida = dur_salida if dur_salida is not None else (src_b - src_a) / factor
        if salida <= 1e-6:
            return
        tramos.append({"tipo": tipo, "factor": factor,
                       "src_start": round(src_a, 4), "src_end": round(src_b, 4),
                       "out_start": round(cursor_out, 4),
                       "out_end": round(cursor_out + salida, 4), **extra})
        cursor_out += salida

    for op in ops:
        if op["src_start"] > cursor_src + 1e-6:
            agrega(cursor_src, op["src_start"], 1.0, "normal")
        if op["tipo"] == "congelado":
            agrega(op["src_start"], op["src_start"], 0.0, "congelado",
                   dur_salida=op["dur_salida"])
        else:
            agrega(op["src_start"], op["src_end"], op["factor"], "rampa",
                   tono=op["tono"], silencio=op["silencio"])
        cursor_src = max(cursor_src, op["src_end"])
    if dur > cursor_src + 1e-6:
        agrega(cursor_src, dur, 1.0, "normal")
    return tramos


def filtros(tramos: list[dict], fps: float, con_audio: bool) -> tuple[str, list[str]]:
    """Un par de cadenas (vídeo, audio) por tramo, y un concat al final."""
    partes: list[str] = []
    etiquetas: list[str] = []

    for i, t in enumerate(tramos):
        v, a = "[v%d]" % i, "[a%d]" % i
        if t["tipo"] == "congelado":
            d = t["out_end"] - t["out_start"]
            paso = 1.0 / fps
            # Un solo frame clonado hasta llenar la duración pedida. `tpad`
            # clona el ÚLTIMO frame del trozo, así que se recorta un frame
            # exacto para que el congelado sea el de `en_sec` y no el vecino.
            partes.append(
                "[0:v]trim=start=%.4f:duration=%.6f,setpts=PTS-STARTPTS,"
                "tpad=stop_mode=clone:stop_duration=%.4f,fps=%.4f,setsar=1%s"
                % (t["src_start"], paso, max(d - paso, 0.0), fps, v))
            if con_audio:
                partes.append(
                    "anullsrc=channel_layout=stereo:sample_rate=%d,atrim=0:%.4f,"
                    "asetpts=PTS-STARTPTS%s" % (SR, d, a))
        else:
            f = t["factor"]
            partes.append(
                "[0:v]trim=start=%.4f:end=%.4f,setpts=(PTS-STARTPTS)/%.6f,"
                "fps=%.4f,setsar=1%s" % (t["src_start"], t["src_end"], f, fps, v))
            if con_audio:
                cadena = ["[0:a]atrim=start=%.4f:end=%.4f" % (t["src_start"], t["src_end"]),
                          "asetpts=PTS-STARTPTS"]
                if t.get("silencio"):
                    # El tramo se queda mudo pero conserva su duración: para
                    # acelerones largos donde el audio del juego, comprimido,
                    # se convierte en un zumbido.
                    cadena.append("volume=0")
                    if abs(f - 1) > 1e-6:
                        cadena.append(cadena_atempo(f))
                elif abs(f - 1) < 1e-6:
                    cadena.append("anull")
                elif t.get("tono") == "sigue":
                    # La cinta corriendo más rápido: sube la duración Y el tono.
                    cadena.append("asetrate=%d,aresample=%d" % (int(SR * f), SR))
                else:
                    cadena.append(cadena_atempo(f))
                cadena.append("aresample=%d,aformat=channel_layouts=stereo" % SR)
                partes.append(",".join(cadena) + a)
        etiquetas += [v, a] if con_audio else [v]

    n = len(tramos)
    if con_audio:
        partes.append("%sconcat=n=%d:v=1:a=1[vout][aout]" % ("".join(etiquetas), n))
    else:
        partes.append("%sconcat=n=%d:v=1:a=0[vout]" % ("".join(etiquetas), n))
    mapas = ["-map", "[vout]"]
    if con_audio:
        mapas += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    return ";".join(partes), mapas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("mapa")
    ap.add_argument("--ops", required=True, help="lista JSON de operaciones")
    args = ap.parse_args()

    entrada, salida = Path(args.entrada), Path(args.salida)
    ops = json.loads(args.ops)
    if not isinstance(ops, list) or not ops:
        sys.exit("[error] --ops tiene que ser una lista JSON con al menos una operación")

    fps, dur, con_audio = sonda(entrada)
    ops = normaliza_ops(ops, dur, fps)
    tramos = construye_tramos(ops, dur, fps)
    cadena, mapas = filtros(tramos, fps, con_audio)

    salida.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(entrada),
         "-filter_complex", cadena, *mapas,
         # Máster de trabajo: se comprime poco porque de aquí sale todavía el
         # render final. Mismo criterio que acelerar.py.
         "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", str(salida)],
        check=True,
    )

    prevista = tramos[-1]["out_end"] if tramos else dur
    real = sonda(salida)[1]
    mapa = {
        "duracion_fuente": round(dur, 3),
        "duracion_salida": round(prevista, 3),
        "duracion_real": round(real, 3),
        "fps": fps,
        "tramos": tramos,
    }
    Path(args.mapa).write_text(json.dumps(mapa, ensure_ascii=False, indent=2),
                               encoding="utf-8")

    print("[ritmo] %d operation(s) - %.2fs -> %.2fs" % (len(ops), dur, real))
    for t in tramos:
        if t["tipo"] == "normal":
            continue
        if t["tipo"] == "congelado":
            etiqueta = "freeze"
        else:
            etiqueta = "x%g" % t["factor"]
            if t.get("tono") == "sigue":
                etiqueta += " (pitch follows)"
            if t.get("silencio"):
                etiqueta += " (muted)"
        print("         source %7.2f-%7.2f  ->  edit %7.2f-%7.2f   %s"
              % (t["src_start"], t["src_end"], t["out_start"], t["out_end"], etiqueta))
    if abs(real - prevista) > 0.15:
        print("[warning] the map says %.2fs but the file measures %.2fs - plan "
              "times may be off. Check it." % (prevista, real))


if __name__ == "__main__":
    main()
