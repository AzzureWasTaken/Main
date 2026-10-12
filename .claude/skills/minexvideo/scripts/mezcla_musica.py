#!/usr/bin/env python3
"""
Mete una pista de musica por debajo del audio original del short.

    mezcla_musica.py <video_in> <video_out> <musica> [--volumen 0.18]
                     [--inicio 0] [--fade 1.2] [--ducking 1]

El video NO se recodifica (`-c:v copy`): solo se sustituye la pista de audio.
Es cuestion de segundos aunque el clip sea largo, y no pierde nada de imagen.

**Se mezcla DESPUES de transcribir, nunca antes.** Whisper transcribiendo con
musica encima inventa palabras y descoloca los tiempos, y los subtitulos
karaoke dependen de que esos tiempos sean exactos. render.sh se encarga de
usar la fuente sin musica para transcribir y esta para renderizar.

**Ducking** (activado por defecto): la musica se agacha sola cuando hablas y
vuelve a subir en los silencios, via `sidechaincompress`. Sin esto hay que
elegir entre musica que no se oye o musica que se come la voz — que es el
fallo tipico de los shorts narrados. El audio del short es la voz; la musica
es cama.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def duracion(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def nivel_medio_db(path: Path) -> float | None:
    """mean_volume de la pista de audio, en dBFS. None si no hay audio."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    for linea in out.stderr.splitlines():
        if "mean_volume:" in linea:
            try:
                return float(linea.split("mean_volume:")[1].split("dB")[0].strip())
            except ValueError:
                return None
    return None


def umbral_ducking(path: Path) -> float:
    """Umbral del sidechain, calibrado al nivel real de la grabacion.

    Un umbral fijo no sirve: `sidechaincompress` lo toma en amplitud lineal
    (0-1), asi que el mismo numero significa cosas distintas segun lo fuerte
    que grabe el micro. Con un umbral demasiado bajo el ruido de sala mantiene
    la musica agachada TODO el rato y nunca vuelve a subir en los silencios —
    que es justo lo que hace que suene mal.

    Se ancla al mean_volume del clip mas un margen. Medido sobre material real:
    con el margen a +4 dB la musica cede unos 4-6 dB mientras hablas y vuelve
    a menos de 2 dB de su nivel en los silencios, que es el comportamiento que
    se busca. Los topes evitan que una pista rarisima (casi muda, o saturada)
    de un umbral absurdo.
    """
    mean = nivel_medio_db(path)
    if mean is None:
        return 0.03
    return max(0.01, min(0.20, 10 ** ((mean + 4.0) / 20.0)))


def tiene_audio(path: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return bool(json.loads(out.stdout).get("streams"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_in")
    ap.add_argument("video_out")
    ap.add_argument("musica")
    ap.add_argument("--volumen", type=float, default=0.18,
                    help="0-1. 0.18 deja la musica presente sin competir con la voz.")
    ap.add_argument("--inicio", type=float, default=0.0,
                    help="segundo del archivo de musica por el que empezar")
    ap.add_argument("--fade", type=float, default=1.2,
                    help="segundos de fundido de salida al final del short")
    ap.add_argument("--ducking", type=int, default=1)
    args = ap.parse_args()

    vin, vout, mus = Path(args.video_in), Path(args.video_out), Path(args.musica)
    if not mus.exists():
        print(f"[error] music not found: {mus}", file=sys.stderr)
        sys.exit(1)

    dur = duracion(vin)
    fade = max(0.0, min(args.fade, dur))
    fade_desde = max(0.0, dur - fade)
    con_voz = tiene_audio(vin)

    # -stream_loop -1 repite la musica si es mas corta que el short. El atrim
    # posterior la corta exactamente a la duracion del video, asi que da igual
    # que sobre o falte.
    entradas = ["-i", str(vin),
                "-stream_loop", "-1", "-ss", f"{args.inicio}", "-i", str(mus)]

    musica_base = (
        f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"atrim=0:{dur:.4f},asetpts=PTS-STARTPTS,"
        f"volume={args.volumen}"
    )

    if con_voz:
        partes = [
            # apad + atrim: si la pista de voz es mas corta que el video (pasa
            # cuando el clip acaba en silencio), se rellena para que la mezcla
            # dure exactamente lo que dura la imagen.
            f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad,atrim=0:{dur:.4f},asetpts=PTS-STARTPTS[voz]",
            f"{musica_base}[mus]",
        ]
        if args.ducking:
            # La voz se duplica: una copia va a la mezcla y la otra sirve de
            # cadena lateral para que la musica sepa cuando agacharse.
            # threshold bajo y ratio alto: basta con que empieces a hablar
            # para que ceda. release largo (350 ms) evita que suba y baje en
            # cada silaba, que es lo que suena a barato.
            thr = umbral_ducking(vin)
            partes += [
                "[voz]asplit=2[voz1][cadena]",
                f"[mus][cadena]sidechaincompress="
                f"threshold={thr:.4f}:ratio=15:attack=5:release=400:makeup=1[musduck]",
            ]
            print(f"[musica] ducking con umbral {thr:.4f} "
                  f"(calibrado al nivel de la voz del clip)")
            voz_lbl, cama = "[voz1]", "[musduck]"
        else:
            voz_lbl, cama = "[voz]", "[mus]"

        # El fundido va SOLO sobre la musica, nunca sobre la mezcla ya hecha:
        # aplicado despues del amix se lleva por delante tambien la narracion, y
        # el final del short es justo donde esta el remate. Medido: fundiendo la
        # mezcla, el ultimo segundo perdia 6 dB de voz.
        partes.append(f"{cama}afade=t=out:st={fade_desde:.4f}:d={fade:.4f}[cama]")
        partes.append(
            f"{voz_lbl}[cama]amix=inputs=2:duration=first:normalize=0,"
            f"alimiter=limit=0.95[aout]"
        )
    else:
        print("[music] the video has no audio - music becomes the only track")
        partes = [
            f"{musica_base},afade=t=out:st={fade_desde:.4f}:d={fade:.4f},"
            f"alimiter=limit=0.95[aout]"
        ]

    vout.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *entradas,
         "-filter_complex", ";".join(partes),
         "-map", "0:v", "-c:v", "copy",
         "-map", "[aout]", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(vout)],
        check=True,
    )

    duck = "con ducking" if args.ducking else "sin ducking"
    print(f"[musica] {mus.name} mezclada al {args.volumen:.0%} {duck} -> {vout.name}")


if __name__ == "__main__":
    main()
