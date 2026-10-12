#!/usr/bin/env python3
"""
Tapa las palabrotas: pita el audio y enmascara la palabra en los subtítulos.

    censura.py <words.json> <video_in> <video_out> [opciones]

El canal es para niños, así que esto va ENCENDIDO por defecto. Se apaga por
short con `"censura": false` en el plan.

Hace las dos cosas a la vez, y ese es el punto: censurar solo el audio deja la
palabra escrita en el karaoke, y censurar solo el texto la deja sonando. Como
los subtítulos salen de esta misma transcripción, aquí se sabe exactamente qué
palabra es y en qué milisegundo cae.

  * **Audio** — el tramo se silencia y encima se mezcla un pitido de 1 kHz con
    micro-fundidos, para que no chasquee al entrar y al salir.
  * **Texto** — `words.json` se reescribe con la palabra enmascarada
    (`cojones` -> `c******`). Se conserva la primera letra, que es la
    convención que todo el mundo lee como "aquí había un taco", y la
    puntuación de alrededor (`¿`, `?`, comas) para que la frase siga leyéndose.

Se ejecuta ANTES de `captions_plan.py`: cuando las líneas de subtítulo se
construyen, la palabra ya viene enmascarada y no hay que tocarlas después.

IDEMPOTENTE por construcción: `render.sh` regenera `words.json` desde la
transcripción original en cada pasada, así que este script siempre ve el texto
sin enmascarar y encuentra los mismos tramos.

Si no hay ninguna palabrota, NO escribe el vídeo de salida (y borra el de una
pasada anterior). `render.sh` usa esa ausencia para seguir con la fuente
original y no pagar un remux de balde.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# The list. English profanity, tuned for gaming commentary.
#
# These are FULL-WORD patterns (anchored at both ends), not substrings: that
# is why `fuck\w*` does not fire on unrelated words — the pattern has to match
# the whole word — and why prefixes carry `\w*`, to cover inflections without
# listing them one by one.
#
# Deliberately LEFT OUT, because in gaming videos they cause more false
# positives (or are mild enough for YouTube) than they are worth:
#   ass    -> "assassin", and on its own it is mild ("dumbass" IS caught)
#   hell, damn, crap, sucks -> mild, YouTube-safe, bleeping them sounds odd
#   dick   -> mild in most gaming banter; add via `censura.extra` if wanted
# If a specific short needs any of them, add them with `censura.extra`.
# ---------------------------------------------------------------------------
LISTA = [
    r"fuck\w*",                # fuck, fucking, fucked, fucker...
    r"\w*fucker\w*",           # motherfucker, motherfuckers
    r"shit\w*",                # shit, shitty, shitting...
    r"bullshit\w*", r"dogshit\w*", r"horseshit\w*", r"batshit\w*",
    r"bitch\w*",               # bitch, bitches, bitching
    r"asshole\w*", r"arsehole\w*",
    r"dumbass\w*", r"jackass\w*",
    r"cunt\w*",
    r"bastard\w*",
    r"dickhead\w*",
    r"cock(sucker|suckers)",   # "cock" alone is left out (rooster, false positives)
    r"pussy", r"pussies",
    r"twat\w*", r"wanker\w*",
    r"slut\w*", r"whore\w*",
    r"goddamn\w*",
    r"nigg\w*",                # racial slur, always censored
    r"faggot\w*",              # homophobic slur ("fag" alone: British cigarette)
    r"retard(ed|s)?",          # ableist slur as insult
]


def normaliza(palabra: str) -> str:
    """Quita tildes, puntuación y mayúsculas: 'Cojones?' -> 'cojones'.

    Las tildes se van a propósito: así la lista no tiene que llevar 'cabrón' y
    'cabron' por separado.

    La Ñ es la excepción, y no es un detalle: NFD la descompone en n + tilde,
    así que quitar las marcas convierte 'coño' en 'cono' — y entonces la
    palabra 'cono' (la figura geométrica) saldría pitada. Se aparta antes de
    descomponer y se repone después.
    """
    s = palabra.lower().replace("ñ", "\0")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-zñ]", "", s.replace("\0", "ñ"))


def enmascara(palabra: str) -> str:
    """'cojones?' -> 'c******?'  ·  '¿joder!' -> '¿j****!'

    Solo se tocan las letras; los signos de apertura y cierre se quedan donde
    estaban para que el subtítulo siga leyéndose como una frase.
    """
    letras = [i for i, c in enumerate(palabra) if c.isalpha()]
    if not letras:
        return palabra
    out = list(palabra)
    for i in letras[1:]:
        out[i] = "*"
    return "".join(out)


def construye_regex(extra: list[str], excluir: list[str]) -> re.Pattern:
    patrones = list(LISTA) + [re.escape(normaliza(p)) for p in extra if normaliza(p)]
    fuera = {normaliza(p) for p in excluir if normaliza(p)}
    rx = re.compile("|".join(f"(?:{p})" for p in patrones))

    class Filtro:
        def match(self, palabra_norm: str) -> bool:
            if palabra_norm in fuera:
                return False
            m = rx.fullmatch(palabra_norm)
            return m is not None

    return Filtro()


def fusiona(tramos: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Une los tramos que se solapan o se tocan.

    Dos tacos seguidos ('la puta mierda') con el margen aplicado se pisan, y
    dos filtros `volume` encadenados sobre el mismo instante no suman: hay que
    dárselo a ffmpeg como un único tramo o el pitido sale a trozos.
    """
    if not tramos:
        return []
    tramos = sorted(tramos)
    out = [list(tramos[0])]
    for s, e in tramos[1:]:
        if s <= out[-1][1] + 0.02:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(a, b) for a, b in out]


def duracion(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def pita(video_in: Path, video_out: Path, tramos: list[tuple[float, float]],
         pitido_db: float) -> None:
    entradas = ["-i", str(video_in)]
    partes = []

    # La voz: se silencia cada tramo. Encadenar `volume=0:enable=...` es la
    # forma directa; el corte es abrupto, pero el pitido entra en el mismo
    # instante y tapa el chasquido.
    puerta = "".join(
        f"volume=0:enable='between(t,{s:.3f},{e:.3f})'," for s, e in tramos
    )
    partes.append(f"[0:a]{puerta}aformat=channel_layouts=stereo:sample_rates=48000[voz]")

    for i, (s, e) in enumerate(tramos):
        d = e - s
        # Un pitido por tramo, generado a medida y colocado con adelay. Es más
        # largo de escribir que una sola sinusoide recortada con `enable`,
        # pero así cada uno lleva su propio fundido y ninguno chasquea.
        fade = min(0.012, d / 4)
        # `aevalsrc` y no `sine`: el filtro `sine` NO genera a fondo de escala
        # —medido, sale a −18 dBFS— así que `--pitido-db` mentía por 18 dB y el
        # pitido se quedaba en un susurro. Con la expresión explícita la
        # amplitud es 1.0 exacta y el dB pedido es el dB que sale.
        entradas += ["-f", "lavfi", "-t", f"{d:.3f}",
                     "-i", "aevalsrc=sin(2*PI*1000*t):s=48000"]
        partes.append(
            f"[{i + 1}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"afade=t=in:st=0:d={fade:.3f},"
            f"afade=t=out:st={max(0.0, d - fade):.3f}:d={fade:.3f},"
            f"volume={pitido_db}dB,"
            f"adelay={int(round(s * 1000))}|{int(round(s * 1000))}[p{i}]"
        )

    etiquetas = "[voz]" + "".join(f"[p{i}]" for i in range(len(tramos)))
    partes.append(
        f"{etiquetas}amix=inputs={len(tramos) + 1}:normalize=0:duration=first,"
        f"alimiter=limit=0.97[a]"
    )

    # `-c:v copy`: la imagen no se toca, esto es un remux con la pista de audio
    # cambiada. Cuesta un par de segundos y no degrada el vídeo.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *entradas,
         "-filter_complex", ";".join(partes),
         "-map", "0:v", "-c:v", "copy",
         "-map", "[a]", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(video_out)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("video_in")
    ap.add_argument("video_out")
    ap.add_argument("--extra", default="", help="palabras extra, separadas por |")
    ap.add_argument("--excluir", default="", help="palabras a NO censurar, separadas por |")
    ap.add_argument("--pitido-db", type=float, default=-16.0,
                help="pico del pitido en dBFS")
    ap.add_argument("--margen", type=float, default=0.06,
                    help="segundos de colchón a cada lado del tramo")
    args = ap.parse_args()

    words_p = Path(args.words)
    video_in = Path(args.video_in)
    video_out = Path(args.video_out)

    palabras = json.loads(words_p.read_text(encoding="utf-8"))
    filtro = construye_regex(
        [p for p in args.extra.split("|") if p],
        [p for p in args.excluir.split("|") if p],
    )

    tramos, pilladas = [], []
    dur = duracion(video_in)
    for w in palabras:
        if not filtro.match(normaliza(w.get("word", ""))):
            continue
        pilladas.append(w["word"])
        w["word"] = enmascara(w["word"])
        s = max(0.0, float(w["start"]) - args.margen)
        e = min(dur, float(w["end"]) + args.margen)
        if e > s:
            tramos.append((s, e))

    # El texto se reescribe siempre: aunque el remux esté en caché, los
    # subtítulos se generan de este archivo en cada pasada.
    words_p.write_text(json.dumps(palabras, ensure_ascii=False, indent=2), encoding="utf-8")

    if not tramos:
        # Sin tacos no hay nada que pitar. Se borra el vídeo censurado de una
        # pasada anterior para que render.sh no lo reutilice por error.
        video_out.unlink(missing_ok=True)
        Path(str(video_out) + ".firma").unlink(missing_ok=True)
        print("[censor] no profanity found")
        return

    tramos = fusiona(tramos)

    firma_p = Path(str(video_out) + ".firma")
    firma = hashlib.sha1(
        f"{tramos}|{args.pitido_db}|{video_in.stat().st_mtime_ns}".encode()
    ).hexdigest()
    if video_out.exists() and firma_p.exists() and firma_p.read_text() == firma:
        print(f"[censor] {len(tramos)} segment(s) already bleeped (cached): "
              f"{', '.join(pilladas)}")
        return

    pita(video_in, video_out, tramos, args.pitido_db)
    firma_p.write_text(firma)
    detalle = ", ".join(f"{s:.2f}-{e:.2f}s" for s, e in tramos)
    print(f"[censor] {len(tramos)} swear word(s) bleeped and masked "
          f"({', '.join(pilladas)}) -> {detalle}")


if __name__ == "__main__":
    main()
