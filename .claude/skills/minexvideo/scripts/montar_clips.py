#!/usr/bin/env python3
"""
Une varios clips en una sola fuente para que el resto del pipeline no cambie.

    montar_clips.py <salida.mp4> <mapa.json> <clip1> <clip2> [...]
                    [--transiciones '<json>']

Todo lo que viene despues (transcripcion, subtitulos, plan, Remotion) trabaja
sobre UN archivo con UNA linea de tiempo. Uniendo aqui, ni el linter ni las
plantillas ni transcribe.py se enteran de que habia varios clips.

`mapa.json` guarda donde empieza cada clip dentro de la fuente montada. Es lo
que permite escribir el plan: los `start_sec` de los beats van en segundos
ABSOLUTOS de la fuente montada, no del clip suelto, y sin el mapa habria que
ir contando a mano.

Tres caminos:

  * **Copia directa** cuando todos los clips comparten codec, resolucion, fps
    y formato de audio, y no hay transiciones. Es instantaneo y sin perdida.
  * **Re-codificacion** cuando los formatos no coinciden. Se normaliza todo al
    formato del primer clip.
  * **Transiciones** (`--transiciones`) cuando se pide que las junturas se
    vean. Recodifica siempre, porque hay que mezclar imagen de dos clips.

NO recorta nada: cada clip entra entero, en el orden dado. Cortar sigue siendo
trabajo previo y a mano, igual que en el resto de la skill.

──────────────────────────────────────────────────────────────────────────────
LAS TRANSICIONES

    --transiciones '[{"tipo":"pixelize","duracion":0.4}, {"tipo":"corte"}]'

Una entrada por juntura (con N clips hay N-1 junturas). Si se pasa una sola,
vale para todas.

El video se cruza con `xfade`. **El audio NO se cruza con `acrossfade`**, que
es la opcion obvia y es la mala: atenua los dos lados del solape, asi que en
una juntura donde se habla hasta el ultimo frame te comes el final de la
palabra. Aqui cada pista se retrasa a su sitio y se SUMAN a ganancia unidad
(`adelay` + `amix=normalize=0`), asi no se pierde ni una silaba. Funciona
porque en la practica al menos uno de los dos lados del solape esta callado —
y si no lo esta, se avisa por consola antes de montar.

Ojo a la duracion total: cada transicion se COME su duracion (los dos clips se
solapan), asi que el montaje dura `suma - suma(duraciones)`. Cambiar el TIPO
de transicion no mueve ningun tiempo; cambiar la DURACION mueve todo lo que
venga detras.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUR_POR_DEFECTO = 0.35
# El umbral con el que se decide si un lado de la juntura "esta hablando".
# Mismo criterio que usa cortar_silencios.py para detectar huecos.
UMBRAL_VOZ_DB = -38.0

# Transiciones de `xfade` que tienen sentido en este formato. La lista existe
# para que no se cuele un nombre invalido (xfade aborta el montaje entero) y
# para que quien escribe el plan elija por SIGNIFICADO, no por catalogo.
TRANSICIONES = {
    "pixelize":   "salto de sitio o de momento — 'nos vamos a otro lado'",
    "smoothleft": "la misma accion continua",
    "smoothright": "la misma accion continua",
    "smoothup":   "la misma accion continua, en vertical",
    "smoothdown": "la misma accion continua, en vertical",
    "wipeleft":   "corte energico",
    "wiperight":  "corte energico",
    "slideup":    "cambio de tema, vertical (encaja con el formato)",
    "slidedown":  "cambio de tema, vertical",
    "circleclose": "se cierra sobre el final de una escena",
    "circleopen": "se abre sobre algo nuevo",
    "fadewhite":  "fogonazo — impacto, explosion, sorpresa",
    "fadeblack":  "paso del tiempo",
    "fade":       "neutro, casi invisible",
    "dissolve":   "granulado, transicion sucia",
    "hlslice":    "glitch horizontal",
    "vuslice":    "glitch vertical",
    "zoomin":     "empuje hacia dentro",
    "distance":   "salto raro, casi psicodelico",
    "squeezev":   "aplastado vertical, comico",
    "hblur":      "desenfoque de velocidad",
}


def probe(path: Path) -> dict:
    """Parametros que tienen que coincidir para poder concatenar sin recodificar."""
    out = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,"
                          "pix_fmt,sample_rate,channels",
         "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), {})
    a = next((s for s in data["streams"] if s.get("codec_type") == "audio"), {})
    return {
        "path": path,
        "dur": float(data["format"]["duration"]),
        "v": (v.get("codec_name"), v.get("width"), v.get("height"),
              v.get("r_frame_rate"), v.get("pix_fmt")),
        "a": (a.get("codec_name"), a.get("sample_rate"), a.get("channels")),
        "codec_v": v.get("codec_name") or "",
        "tiene_audio": bool(a),
        "w": int(v.get("width") or 0),
        "h": int(v.get("height") or 0),
        "fps": v.get("r_frame_rate") or "30/1",
    }


def duracion(path: Path) -> float:
    o = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(o.stdout.strip())


def nivel_medio(path: Path, ini: float, fin: float) -> float:
    """dB medios de un tramo. Sirve para saber si en la juntura se esta hablando."""
    if fin <= ini:
        return -99.0
    o = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", "%.3f" % ini, "-to", "%.3f" % fin,
         "-i", str(path), "-map", "0:a?", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", o.stderr)
    return float(m.group(1)) if m else -99.0


def normaliza_transiciones(crudo, n_junturas: int) -> list[dict]:
    """Una entrada por juntura. Acepta cadena, objeto o lista."""
    if crudo in (None, False, "", []):
        return []
    if isinstance(crudo, str):
        crudo = [{"tipo": crudo}]
    if isinstance(crudo, dict):
        crudo = [crudo]
    if len(crudo) == 1:
        crudo = crudo * n_junturas
    if len(crudo) != n_junturas:
        sys.exit("[error] hay %d junturas y %d transiciones declaradas — pon una "
                 "por juntura, o una sola para todas" % (n_junturas, len(crudo)))

    salida = []
    for i, t in enumerate(crudo):
        if isinstance(t, str):
            t = {"tipo": t}
        tipo = t.get("tipo", "fade")
        if tipo in ("corte", "none", None):
            salida.append({"tipo": "corte", "duracion": 0.0})
            continue
        if tipo not in TRANSICIONES:
            sys.exit("[error] transicion desconocida '%s' en la juntura %d.\n"
                     "        Validas: %s" % (tipo, i + 1, ", ".join(sorted(TRANSICIONES))))
        d = float(t.get("duracion", DUR_POR_DEFECTO))
        if not (0.08 <= d <= 1.2):
            sys.exit("[error] juntura %d: duracion %.2fs fuera de rango (0.08-1.2)"
                     % (i + 1, d))
        salida.append({"tipo": tipo, "duracion": d})
    return salida


def avisa_junturas(clips: list[dict], trans: list[dict]) -> None:
    """Comprueba que el solape cae en un hueco de voz al menos por un lado.

    Sumar a ganancia unidad no pierde nada, pero si los DOS lados hablan
    durante el solape se oyen las dos voces a la vez, que es peor que un corte
    seco. Vale la pena gastar un segundo en mirarlo antes de montar.
    """
    for i, t in enumerate(trans):
        if t["tipo"] == "corte" or not (clips[i]["tiene_audio"] and clips[i + 1]["tiene_audio"]):
            continue
        d = t["duracion"]
        cola = nivel_medio(clips[i]["path"], max(0.0, clips[i]["dur"] - d), clips[i]["dur"])
        cabeza = nivel_medio(clips[i + 1]["path"], 0.0, d)
        if cola > UMBRAL_VOZ_DB and cabeza > UMBRAL_VOZ_DB:
            print("[warning] join %d (%s, %.2fs): both sides have audio "
                  "(%.0f dB / %.0f dB). The two voices will overlap. Shorten the "
                  "transition or trim the tail of the previous clip."
                  % (i + 1, t["tipo"], d, cola, cabeza))


def concat_copia(clips: list[dict], salida: Path) -> None:
    """Concatena sin recodificar, via el demuxer concat."""
    lista = salida.parent / "_concat.txt"
    # El formato del demuxer exige rutas con las comillas simples escapadas.
    lista.write_text(
        "".join("file '%s'\n" % str(c["path"]).replace("'", "'\\''") for c in clips),
        encoding="utf-8",
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lista), "-c", "copy", str(salida)],
        check=True,
    )
    lista.unlink(missing_ok=True)


def normaliza_clip(i: int, c: dict, w: int, h: int, fps: str) -> list[str]:
    """Cadenas de filtro que dejan un clip listo para pegarse con los demas."""
    partes = [
        "[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,"
        "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=%s,format=yuv420p[v%d]"
        % (i, w, h, w, h, fps, i)
    ]
    if c["tiene_audio"]:
        partes.append("[%d:a]aresample=48000,aformat=channel_layouts=stereo[a%d]" % (i, i))
    else:
        # Un clip mudo rompe la concatenacion si los demas traen audio:
        # se le genera silencio de su misma duracion.
        partes.append("anullsrc=channel_layout=stereo:sample_rate=48000,"
                      "atrim=0:%.4f[a%d]" % (c["dur"], i))
    return partes


def concat_recodifica(clips: list[dict], salida: Path) -> None:
    """Normaliza todos los clips al formato del primero y concatena.

    Se escala manteniendo proporcion y se rellena con negro hasta encajar, en
    vez de deformar: un clip grabado en otra resolucion se veria estirado y
    canta mucho mas que unas bandas.
    """
    ref = clips[0]
    w, h, fps = ref["w"], ref["h"], ref["fps"]

    entradas: list[str] = []
    for c in clips:
        entradas += ["-i", str(c["path"])]

    partes, etiquetas = [], []
    for i, c in enumerate(clips):
        partes += normaliza_clip(i, c, w, h, fps)
        etiquetas += ["[v%d]" % i, "[a%d]" % i]
    partes.append("%sconcat=n=%d:v=1:a=1[v][a]" % ("".join(etiquetas), len(clips)))

    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *entradas,
         "-filter_complex", ";".join(partes),
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         str(salida)],
        check=True,
    )


def concat_transiciones(clips: list[dict], trans: list[dict], salida: Path) -> list[float]:
    """Encadena `xfade` en video y suma el audio a ganancia unidad.

    Devuelve el instante de arranque de cada clip dentro del montaje, que ya no
    es la suma de duraciones: cada transicion se come su propio solape.
    """
    ref = clips[0]
    w, h, fps = ref["w"], ref["h"], ref["fps"]

    entradas: list[str] = []
    for c in clips:
        entradas += ["-i", str(c["path"])]

    partes: list[str] = []
    for i, c in enumerate(clips):
        partes += normaliza_clip(i, c, w, h, fps)

    # Offsets. `total` es lo que mide el montaje ya hecho hasta el clip i.
    arranques = [0.0]
    total = clips[0]["dur"]
    etiqueta_v = "[v0]"
    for i, t in enumerate(trans):
        d = t["duracion"]
        arranque = total - d
        arranques.append(arranque)
        nueva = "[x%d]" % i
        if t["tipo"] == "corte":
            partes.append("%s[v%d]concat=n=2:v=1:a=0%s" % (etiqueta_v, i + 1, nueva))
        else:
            partes.append("%s[v%d]xfade=transition=%s:duration=%.4f:offset=%.4f%s"
                          % (etiqueta_v, i + 1, t["tipo"], d, arranque, nueva))
        etiqueta_v = nueva
        total = arranque + clips[i + 1]["dur"]

    # Audio: cada pista a su sitio y sumadas sin normalizar. `normalize=0` es
    # la clave — con la normalizacion por defecto amix divide entre el numero
    # de entradas y la voz se hunde 6 dB en cuanto hay dos pistas vivas.
    for i, arranque in enumerate(arranques):
        ms = int(round(arranque * 1000))
        partes.append("[a%d]adelay=%d:all=1[d%d]" % (i, ms, i))
    partes.append("%samix=inputs=%d:normalize=0:dropout_transition=0[aout]"
                  % ("".join("[d%d]" % i for i in range(len(clips))), len(clips)))

    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *entradas,
         "-filter_complex", ";".join(partes),
         "-map", etiqueta_v, "-map", "[aout]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         str(salida)],
        check=True,
    )
    return arranques


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("mapa")
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--transiciones", default="", help="lista JSON, una por juntura")
    args = ap.parse_args()

    salida = Path(args.salida)
    mapa_p = Path(args.mapa)
    rutas = [Path(p).resolve() for p in args.clips]

    for p in rutas:
        if not p.exists():
            sys.exit("[error] no existe: %s" % p)
    if len(rutas) < 2:
        sys.exit("[error] hacen falta al menos dos clips")

    clips = [probe(p) for p in rutas]
    crudo = json.loads(args.transiciones) if args.transiciones.strip() else None
    trans = normaliza_transiciones(crudo, len(clips) - 1)
    if trans and not any(t["tipo"] != "corte" for t in trans):
        trans = []          # todas "corte" = no hay nada que cruzar

    # AV1: aunque los parametros coincidan, la copia directa le rompe los
    # timestamps y el montaje sale declarando miles de segundos. No da error,
    # solo sale mal — y el sintoma aparece dos etapas mas tarde, en una
    # transcripcion absurdamente corta. Medido el 2026-08-22 con dos clips de
    # 18,85 s + 21,74 s: la fuente montada declaraba 10389 s.
    hay_av1 = any("av1" in c["codec_v"] for c in clips)

    uniforme = (
        len({c["v"] for c in clips}) == 1
        and len({c["a"] for c in clips}) == 1
        and all(c["tiene_audio"] for c in clips)
    )

    salida.parent.mkdir(parents=True, exist_ok=True)
    arranques: list[float] | None = None

    if trans:
        print("[montaje] %d clips con transiciones — recodificando" % len(clips))
        avisa_junturas(clips, trans)
        arranques = concat_transiciones(clips, trans, salida)
    elif hay_av1:
        print("[montaje] %d clips en AV1 — recodificando a H.264 (la copia directa "
              "le rompe los timestamps)" % len(clips))
        concat_recodifica(clips, salida)
    elif uniforme:
        print("[montaje] %d clips con el mismo formato — copia directa" % len(clips))
        try:
            concat_copia(clips, salida)
        except subprocess.CalledProcessError:
            print("[montaje] la copia directa fallo — recodificando")
            concat_recodifica(clips, salida)
    else:
        print("[montaje] %d clips con formatos distintos — recodificando al formato "
              "del primero (%dx%d)" % (len(clips), clips[0]["w"], clips[0]["h"]))
        concat_recodifica(clips, salida)

    if arranques is None:
        arranques, t = [], 0.0
        for c in clips:
            arranques.append(t)
            t += c["dur"]

    mapa = []
    for c, a in zip(clips, arranques):
        mapa.append({
            "clip": c["path"].name,
            "ruta": str(c["path"]),
            "start_sec": round(a, 3),
            "end_sec": round(a + c["dur"], 3),
            "duracion": round(c["dur"], 3),
        })
    mapa_p.write_text(json.dumps(mapa, ensure_ascii=False, indent=2), encoding="utf-8")

    prevista = arranques[-1] + clips[-1]["dur"]
    real = duracion(salida)
    print("[montaje] fuente montada: %.2fs -> %s" % (real, salida))
    print("[montaje] los tiempos del plan van en segundos de ESTA linea de tiempo:")
    for m in mapa:
        print("           %7.2f - %7.2f  %s" % (m["start_sec"], m["end_sec"], m["clip"]))
    if trans:
        print("[montaje] transiciones: %s"
              % ", ".join("%s %.2fs" % (t["tipo"], t["duracion"]) for t in trans))

    # Verificacion dura: si el archivo no mide lo que dice la suma, algo ha
    # roto los timestamps y TODO lo de despues (transcripcion, beats, render)
    # mediria sobre una linea de tiempo inventada. Mejor morir aqui.
    if abs(real - prevista) > 0.5:
        sys.exit("[error] el montaje deberia durar %.2fs y mide %.2fs.\n"
                 "        Los timestamps estan rotos: monta los clips a mano "
                 "recodificando a H.264 y pasa un solo archivo." % (prevista, real))


if __name__ == "__main__":
    main()
