#!/usr/bin/env python3
"""
Analyze a LONG raw stream recording (VOD) so Claude can pick the best moments.

    analyze_vod.py <vod.mp4> [--model small] [--language en] [--workdir DIR]
                   [--skip-transcript] [--force]

Produces, inside the workdir (~/.cache/minexvideo/vod-<hash>/):

  info.json        duration, resolution, fps of the VOD
  energy.json      per-second loudness (RMS dBFS) of the audio track
  peaks.txt        the loudest windows (screams, laughter, hype), ranked,
                   each with a timestamp — the fastest map to "something
                   happened here"
  transcript.json  Whisper segments: [{"start":..,"end":..,"text":..}]
  transcript.txt   the same, human readable: "[HH:MM:SS] text" per line

Claude then READS transcript.txt + peaks.txt, picks clip-worthy segments
(funny fails, big wins, rage moments, wholesome bits...) and cuts them with
cut_clip.py. This script only gathers the evidence; the judgement is yours.

Transcription uses a SMALL Whisper model on purpose: a 3-hour VOD with
large-v3 on CPU would take many hours. `small` is accurate enough to know
WHAT is being said and WHEN, which is all clip-picking needs. The final
shorts are re-transcribed clip by clip with large-v3 anyway (render.sh),
so caption quality never depends on this pass.

Word-level alignment is skipped here for the same reason — segment
timestamps are plenty for picking a 40-second window out of 3 hours.

This script relaunches itself inside the skill's venv (whisperx and numpy
live there, not in the global Python).
"""
import hashlib
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

# Windows consoles default to a legacy codepage (cp1252) that cannot encode
# the dashes in this script's help text, nor an accented character in a file
# path or a transcript line. Without this the analysis would succeed and the
# script would then die printing its own progress message.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_DIR = SKILL_DIR / ".venv"

_CANDIDATES = [
    VENV_DIR / "Scripts" / "python.exe",
    VENV_DIR / "bin" / "python3",
    VENV_DIR / "bin" / "python",
]


def _relaunch_in_venv() -> None:
    """Relaunch with the venv interpreter if we are not already inside it.

    subprocess and not os.execv: on Windows, execv does NOT quote arguments,
    so a path with spaces arrives split in two. With subprocess the quoting
    is handled by the library and paths survive.
    """
    try:
        if Path(sys.prefix).resolve() == VENV_DIR.resolve():
            return
    except OSError:
        pass
    for exe in _CANDIDATES:
        if exe.exists():
            sys.exit(subprocess.run(
                [str(exe), os.path.abspath(__file__), *sys.argv[1:]]).returncode)
    print(
        f"[error] venv interpreter not found in {VENV_DIR}\n"
        f"        run: bash {SKILL_DIR / 'scripts' / 'setup.sh'}",
        file=sys.stderr,
    )
    sys.exit(1)


_relaunch_in_venv()

import numpy as np  # noqa: E402  (lives in the venv, pulled in by whisperx)


def hhmmss(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def workdir_for(video: Path) -> Path:
    h = hashlib.sha1(str(video.resolve()).encode("utf-8")).hexdigest()[:16]
    d = Path.home() / ".cache" / "minexvideo" / f"vod-{h}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def probe(video: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(r.stdout)
    st = data["streams"][0]
    num, _, den = st["r_frame_rate"].partition("/")
    fps = float(num) / float(den or 1)
    return {
        "path": str(video),
        "duration_sec": round(float(data["format"]["duration"]), 2),
        "width": st["width"],
        "height": st["height"],
        "fps": round(fps, 2),
    }


def extract_audio(video: Path, out_wav: Path) -> None:
    """Mono 16 kHz — the format Whisper expects, and small enough on disk."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", str(out_wav)],
        check=True,
    )


def energy_per_second(wav_path: Path) -> list[float]:
    """RMS loudness (dBFS) for every second of audio, read in chunks.

    A 5-hour VOD is a ~550 MB wav; reading it whole would eat RAM for no
    reason. One-second chunks at 16 kHz are 32 KB each — trivial.
    """
    out: list[float] = []
    with wave.open(str(wav_path), "rb") as w:
        rate = w.getframerate()
        while True:
            raw = w.readframes(rate)
            if not raw:
                break
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
            if not len(samples):
                break
            rms = float(np.sqrt(np.mean(samples ** 2)))
            db = 20 * np.log10(rms / 32768.0) if rms > 0 else -100.0
            out.append(round(max(db, -100.0), 1))
    return out


def find_peaks(energy: list[float], top_n: int = 40,
               min_gap_sec: int = 45) -> list[dict]:
    """The loudest 4-second windows, at least `min_gap_sec` apart.

    Loudness in a stream correlates with the streamer reacting — screaming,
    laughing, hype. The gap keeps one long loud moment from eating the whole
    ranking. This is a HINT list, not a verdict: quiet moments can be gold
    too (that is what the transcript is for).
    """
    if len(energy) < 8:
        return []
    arr = np.array(energy)
    # 4-second sliding mean: single-sample spikes (a door slam) rank lower
    # than sustained excitement.
    kernel = np.ones(4) / 4
    smooth = np.convolve(arr, kernel, mode="same")
    order = np.argsort(smooth)[::-1]
    peaks: list[dict] = []
    taken: list[int] = []
    for idx in order:
        i = int(idx)
        if any(abs(i - t) < min_gap_sec for t in taken):
            continue
        taken.append(i)
        peaks.append({"sec": i, "time": hhmmss(i), "db": round(float(smooth[i]), 1)})
        if len(peaks) >= top_n:
            break
    peaks.sort(key=lambda p: -p["db"])
    return peaks


def transcribe(wav_path: Path, model_name: str, lang: str) -> list[dict]:
    import torch
    import whisperx

    use_gpu = torch.cuda.is_available()
    device = "cuda" if use_gpu else "cpu"
    compute = "float16" if use_gpu else "int8"
    print(f"[analyze] transcribing: device={device} model={model_name} lang={lang}")
    print("[analyze] a multi-hour VOD takes a while on CPU — this is normal, not a hang")

    model = whisperx.load_model(model_name, device, compute_type=compute, language=lang)
    audio = whisperx.load_audio(str(wav_path))
    result = model.transcribe(audio, batch_size=16 if use_gpu else 4, language=lang)

    segs = []
    for seg in result.get("segments", []):
        txt = (seg.get("text") or "").strip()
        if not txt:
            continue
        segs.append({
            "start": round(float(seg["start"]), 2),
            "end": round(float(seg["end"]), 2),
            "text": txt,
        })
    return segs


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    video = Path(args[0]).resolve()
    if not video.exists():
        print(f"[error] file not found: {video}", file=sys.stderr)
        sys.exit(1)

    opts = args[1:]

    def opt(name: str, default: str) -> str:
        return opts[opts.index(name) + 1] if name in opts else default

    model_name = opt("--model", os.environ.get("VOD_MODEL", "small"))
    lang = opt("--language", os.environ.get("WHISPER_LANG", "en"))
    wd = Path(opt("--workdir", "")).resolve() if "--workdir" in opts else workdir_for(video)
    wd.mkdir(parents=True, exist_ok=True)
    force = "--force" in opts

    # ── Probe ──────────────────────────────────────────────────────────────
    info = probe(video)
    (wd / "info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    dur = info["duration_sec"]
    print(f"[analyze] {video.name}: {hhmmss(dur)} "
          f"({info['width']}x{info['height']} @ {info['fps']}fps)")

    # ── Audio ──────────────────────────────────────────────────────────────
    wav = wd / "audio.wav"
    if not wav.exists() or force:
        print("[analyze] extracting audio track...")
        extract_audio(video, wav)

    # ── Energy ─────────────────────────────────────────────────────────────
    energy_p = wd / "energy.json"
    peaks_p = wd / "peaks.txt"
    if not energy_p.exists() or force:
        print("[analyze] measuring loudness...")
        energy = energy_per_second(wav)
        energy_p.write_text(json.dumps(energy), encoding="utf-8")
    else:
        energy = json.loads(energy_p.read_text(encoding="utf-8"))
    peaks = find_peaks(energy)
    with peaks_p.open("w", encoding="utf-8") as f:
        f.write("Loudest moments of the VOD (sustained 4s loudness, ranked).\n")
        f.write("Loud usually means the streamer is REACTING — check the "
                "transcript around each one.\n\n")
        for p in peaks:
            f.write(f"  {p['time']}  ({p['db']:6.1f} dB)\n")
    print(f"[analyze] {len(peaks)} loudness peaks -> {peaks_p}")

    # ── Transcript ─────────────────────────────────────────────────────────
    tj = wd / "transcript.json"
    tt = wd / "transcript.txt"
    if "--skip-transcript" in opts:
        print("[analyze] transcript skipped (--skip-transcript)")
    elif tj.exists() and not force:
        print(f"[analyze] transcript cached: {tt}")
    else:
        segs = transcribe(wav, model_name, lang)
        tj.write_text(json.dumps(segs, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        with tt.open("w", encoding="utf-8") as f:
            for s in segs:
                f.write(f"[{hhmmss(s['start'])}] {s['text']}\n")
        print(f"[analyze] {len(segs)} segments -> {tt}")

    print(f"[analyze] workdir: {wd}")
    print("[analyze] next: read transcript.txt + peaks.txt, pick moments, "
          "cut them with cut_clip.py")


if __name__ == "__main__":
    main()
