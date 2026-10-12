#!/usr/bin/env python3
"""
Valida un plan.json antes de renderizar.

Existe porque un render de Remotion tarda entre 20 y 60 segundos, y descubrir
en el minuto 1 que a un beat le faltaba un campo es tirar ese minuto. Esto
falla en 50 ms.

Errores  -> abortan el render (exit 1).
Avisos   -> se imprimen y el render continúa.

La regla dura del formato está aquí: NINGÚN beat puede tapar el gameplay entero
y los beats que ocupan el mismo sitio de la pantalla no pueden solaparse en el
tiempo. Ver `knowledge/hard_rules.md`.
"""
import argparse
import json
import re
import unicodedata
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from montar_clips import TRANSICIONES
except Exception:                                    # pragma: no cover
    TRANSICIONES = {}
try:
    import tiempo as _tiempo
except Exception:                                    # pragma: no cover
    _tiempo = None

# Campos obligatorios por tipo de beat. Si añades una plantilla nueva a
# Short.tsx, añádela también aquí o el linter la dejará pasar sin validar.
REQUERIDOS = {
    "hook_title": ["title"],
    "meme_text": ["text"],
    "tip_banner": ["label", "text"],
    "emoji_burst": ["items"],
    "spotlight": ["x", "y"],
    "item_card": ["name"],
    "counter": ["value"],
    "speech_bubble": ["text", "x", "y"],
    "image_overlay": ["image_path"],
}

# Beats que ocupan el MISMO carril visual. Dos del mismo carril solapados en el
# tiempo se pisan literalmente en pantalla.
#
# `spotlight` y `emoji_burst` no tienen carril: el foco oscurece toda la
# pantalla pero no dibuja nada encima, y los emojis se reparten en huecos. Los
# dos conviven con cualquier otro beat.
CARRILES = {
    "hook_title": "centro-arriba",
    "meme_text": "centro-arriba",
    "counter": "centro-arriba",
    "tip_banner": "banda-baja",
    "speech_bubble": "banda-baja",
    "image_overlay": "centro",
}


def carril(b: dict) -> str | None:
    """Carril visual de un beat.

    `item_card` es el caso especial: su carril depende del ancla. Anclada
    arriba invade la banda del `meme_text` (que ocupa todo el ancho de la
    zona superior), así que cuenta como 'centro-arriba'. Anclada abajo cae en
    la banda del `tip_banner`. Verificado en render: una ficha en top-right
    con un meme_text simultáneo se comen mutuamente el texto.
    """
    kind = b.get("kind")
    if kind == "item_card":
        anchor = b.get("anchor", "top-right")
        return "centro-arriba" if anchor.startswith("top") else "banda-baja"
    return CARRILES.get(kind)

# Duraciones sanas, en segundos. Fuera de rango es aviso, no error: a veces un
# beat largo está justificado.
DURACION = {
    "hook_title": (1.0, 3.0),
    "meme_text": (0.8, 3.5),
    "tip_banner": (2.0, 6.0),
    "emoji_burst": (0.8, 5.0),
    "spotlight": (1.0, 4.0),
    "item_card": (1.2, 5.0),
    "counter": (1.5, 4.5),
    "speech_bubble": (1.2, 5.0),
    "image_overlay": (1.0, 6.0),
}


def duracion_video(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════
#  Los recursos "de editor": ritmo, voz, estilo de subtítulo, cámara,
#  transiciones.
#
#  Todos son opcionales y todos se estropean igual: usándolos porque están.
#  Estas comprobaciones existen para que el coste de pasarse se pague en 50 ms
#  y no en un short que el dueño del canal ve raro sin saber por qué.
# ═══════════════════════════════════════════════════════════════════════════

TIPOS_VOZ = ("agudo", "grave", "megafono", "eco", "robot")
ESTILOS_SUB = ("karaoke", "palabra", "bloque")
TIPOS_ZOOM = ("punch", "snap", "rampa", "push", "pull")


def _solapa(a0, a1, b0, b1) -> bool:
    return a0 < b1 and b0 < a1


def valida_ritmo(plan, dur, words_base, errores, avisos) -> None:
    ops = plan.get("ritmo")
    if ops is None:
        return
    if not isinstance(ops, list) or not ops:
        errores.append("`ritmo` must be a list of operations")
        return

    rangos = []
    for i, op in enumerate(ops):
        et = f"ritmo[{i}]"
        tipo = op.get("tipo", "rampa")
        if tipo not in ("rampa", "congelado"):
            errores.append(f"{et}: unknown tipo '{tipo}' (rampa | congelado)")
            continue

        if tipo == "congelado":
            p = op.get("en_sec")
            d = op.get("duracion", 0.6)
            if p is None:
                errores.append(f"{et}: missing `en_sec`")
                continue
            if not (0.2 <= d <= 2.0):
                avisos.append(f"{et}: a congelado of {d}s is outside the comfortable "
                              f"range (0.2-2.0). More than two seconds frozen and it "
                              f"looks like the video has hung.")
            rangos.append((p, p, et))
            # El congelado mete SILENCIO. Si cae dentro de una palabra, la corta
            # a mitad de sílaba y suena a fallo de reproducción, no a gag.
            for w in words_base:
                if w["start"] + 0.05 < p < w["end"] - 0.05:
                    avisos.append(
                        f"{et}: the congelado at {p}s falls inside the word "
                        f"'{w['word'].strip()}' ({w['start']:.2f}-{w['end']:.2f}). "
                        f"Move it to a gap between phrases.")
                    break
            continue

        s, e = op.get("start_sec"), op.get("end_sec")
        f = op.get("factor", 1.0)
        if s is None or e is None:
            errores.append(f"{et}: missing `start_sec` / `end_sec`")
            continue
        if e <= s:
            errores.append(f"{et}: end_sec ({e}) is not greater than start_sec ({s})")
            continue
        if not isinstance(f, (int, float)) or not (0.15 <= f <= 8.0):
            errores.append(f"{et}: factor {f} out of range (0.15-8.0)")
            continue
        if op.get("tono") not in (None, "mantiene", "sigue"):
            errores.append(f"{et}: `tono` only accepts 'mantiene' or 'sigue'")
        rangos.append((s, e, et))

        dentro = [w for w in words_base if _solapa(s, e, w["start"], w["end"])]
        if op.get("silencio"):
            if dentro:
                avisos.append(
                    f"{et}: the segment runs MUTE and {len(dentro)} word(s) are said there "
                    f"('{' '.join(w['word'].strip() for w in dentro[:4])}...'). "
                    f"That narration is lost.")
        elif dentro and f >= 2.0:
            avisos.append(
                f"{et}: x{f} over a stretch where someone is talking ({len(dentro)} words). "
                f"Above 2x the narration stops being understandable - either lower the "
                f"factor, or set `\"silencio\": true` and let the captions "
                f"carry it.")
        elif dentro and f <= 0.6 and op.get("tono") != "sigue":
            avisos.append(
                f"{et}: x{f} with `tono` held over narration sounds like a dragging "
                f"voice. For comic slow motion use `\"tono\": \"sigue\"`.")
        elif not dentro and 0.85 <= f <= 1.15:
            avisos.append(f"{et}: x{f} changes nothing perceptible. Drop it or raise it.")

    for i in range(len(rangos)):
        for j in range(i + 1, len(rangos)):
            a0, a1, ea = rangos[i]
            b0, b1, eb = rangos[j]
            if _solapa(a0, max(a1, a0 + 1e-6), b0, max(b1, b0 + 1e-6)):
                errores.append(f"{ea} and {eb} overlap in time - separate them")

    if dur:
        for s, e, et in rangos:
            if e > dur + 0.05:
                errores.append(f"{et}: ends at {e}s but the source is {dur:.2f}s long")
    if len(ops) > 4:
        avisos.append(
            f"{len(ops)} `ritmo` operations. Past four the short stops having a "
            f"rhythm and starts having a stutter: keep the ones that "
            f"cover a dead gap or underline a punchline.")


def valida_voz(plan, dur, words, errores, avisos) -> None:
    fx = plan.get("efectos_voz")
    if fx is None:
        return
    if not isinstance(fx, list) or not fx:
        errores.append("`efectos_voz` must be a list")
        return

    rangos = []
    for i, e in enumerate(fx):
        et = f"efectos_voz[{i}]"
        tipo = e.get("tipo", "agudo")
        if tipo not in TIPOS_VOZ:
            errores.append(f"{et}: unknown tipo '{tipo}' - valid: {', '.join(TIPOS_VOZ)}")
        s, f = e.get("start_sec"), e.get("end_sec")
        if s is None or f is None:
            errores.append(f"{et}: missing `start_sec` / `end_sec`")
            continue
        if f <= s:
            errores.append(f"{et}: end_sec ({f}) is not greater than start_sec ({s})")
            continue
        if dur and f > dur + 0.05:
            errores.append(f"{et}: ends at {f}s but the video is {dur:.2f}s long")
        d = f - s
        if d < 0.3:
            avisos.append(f"{et}: {d:.2f}s is far too short - there is no time to read "
                          f"the voice change as intentional.")
        elif d > 6.0:
            avisos.append(f"{et}: {d:.2f}s of processed voice gets tiring. It is a joke, "
                          f"not a sound setting: apply it to the sentence, not the paragraph.")
        inten = e.get("intensidad", 1.0)
        if not isinstance(inten, (int, float)) or not (0.2 <= inten <= 2.0):
            errores.append(f"{et}: `intensidad`={inten} out of range (0.2-2.0)")
        if words and not any(_solapa(s, f, w["start"], w["end"]) for w in words):
            avisos.append(f"{et}: nothing is said in [{s}, {f}] - the effect will not "
                          f"be heard. Check the timing against words.json.")
        rangos.append((s, f, et))

    for i in range(len(rangos)):
        for j in range(i + 1, len(rangos)):
            if _solapa(rangos[i][0], rangos[i][1], rangos[j][0], rangos[j][1]):
                errores.append(f"{rangos[i][2]} and {rangos[j][2]} overlap - "
                               f"there can only be one voice effect at a time")
    if len(fx) > 3:
        avisos.append(
            f"{len(fx)} voice effects. From the third one on the viewer stops "
            f"hearing them as characters and starts hearing them as a filter laid "
            f"on top. Keep the two that are funniest.")


def valida_subtitulos(plan, dur, errores, avisos) -> None:
    sub = plan.get("subtitulos")
    if sub is None:
        return
    if isinstance(sub, str):
        sub = {"estilo": sub}
    if not isinstance(sub, dict):
        errores.append("`subtitulos` must be an object or an `estilo` name")
        return

    estilo = sub.get("estilo", "karaoke")
    if estilo not in ESTILOS_SUB:
        errores.append(f"`subtitulos.estilo`='{estilo}' unknown - "
                       f"valid: {', '.join(ESTILOS_SUB)}")
    elif estilo != "karaoke":
        avisos.append(
            f"`subtitulos.estilo`='{estilo}' changes the captions of the WHOLE short. "
            f"Karaoke is the piece the channel owner singled out as his favourite: "
            f"change it per `tramos`, not all at once.")

    tramos = sub.get("tramos") or []
    cubierto = 0.0
    for i, t in enumerate(tramos):
        et = f"subtitulos.tramos[{i}]"
        s, e = t.get("start_sec"), t.get("end_sec")
        if s is None or e is None:
            errores.append(f"{et}: missing `start_sec` / `end_sec`")
            continue
        if e <= s:
            errores.append(f"{et}: end_sec ({e}) is not greater than start_sec ({s})")
            continue
        if t.get("estilo", "karaoke") not in ESTILOS_SUB:
            errores.append(f"{et}: unknown estilo '{t.get('estilo')}'")
        if dur and e > dur + 0.05:
            errores.append(f"{et}: ends at {e}s but the video is {dur:.2f}s long")
        if t.get("estilo", "karaoke") != "karaoke":
            cubierto += e - s
        if e - s < 1.5:
            avisos.append(f"{et}: {e - s:.2f}s of a different `estilo` reads as a "
                          f"blink. Cover a whole sentence or do not change it.")
    for i in range(len(tramos)):
        for j in range(i + 1, len(tramos)):
            a, b = tramos[i], tramos[j]
            if None in (a.get("start_sec"), a.get("end_sec"),
                        b.get("start_sec"), b.get("end_sec")):
                continue
            if _solapa(a["start_sec"], a["end_sec"], b["start_sec"], b["end_sec"]):
                errores.append(f"subtitulos.tramos[{i}] and [{j}] overlap")

    if dur and cubierto > 0.45 * dur:
        avisos.append(
            f"{cubierto:.0f}s out of the short's {dur:.0f}s carry a caption `estilo` "
            f"other than karaoke. It stops being a device and becomes the look of "
            f"the video: get it under half.")


def valida_camara(plan, beats, errores, avisos) -> None:
    momentos = []
    for i, z in enumerate(plan.get("zoom") or []):
        momentos.append((f"zoom[{i}]", z))
    for i, b in enumerate(beats):
        z = b.get("zoom")
        if isinstance(z, dict):
            momentos.append((f"beat[{i}].zoom", z))

    fuertes = 0
    temblores = 0
    for et, z in momentos:
        if not isinstance(z, dict):
            errores.append(f"{et}: must be an object")
            continue
        tipo = z.get("tipo", "punch" if z.get("punch") else "rampa")
        if tipo not in TIPOS_ZOOM:
            errores.append(f"{et}: unknown tipo '{tipo}' - "
                           f"valid: {', '.join(TIPOS_ZOOM)}")
        sc = z.get("scale", 1.22)
        if not isinstance(sc, (int, float)) or sc <= 0:
            errores.append(f"{et}: `scale`={sc} must be a number > 0")
        elif sc > 1.6:
            errores.append(f"{et}: `scale`={sc} - above 1.5 the source video's "
                           f"pixels show. Drop to 1.3-1.45.")
        elif sc > 1.5:
            avisos.append(f"{et}: `scale`={sc} is at the limit; at 1.45 the lack of "
                          f"resolution already shows on footage that is not 4K.")
        if sc >= 1.3:
            fuertes += 1
        foco = z.get("focus")
        if foco is not None:
            if not isinstance(foco, dict) or foco.get("x") is None or foco.get("y") is None:
                errores.append(f"{et}: `focus` needs `x` and `y` in % of the frame")
            else:
                for c in ("x", "y"):
                    if not (0 <= foco[c] <= 100):
                        errores.append(f"{et}: `focus.{c}`={foco[c]} out of range (0-100)")
        sh = z.get("shake")
        if sh is not None:
            if not isinstance(sh, (int, float)) or not (0 <= sh <= 3):
                errores.append(f"{et}: `shake`={sh} out of range (0-3, in % of the width)")
            else:
                temblores += 1
                if sh > 1.5:
                    avisos.append(f"{et}: `shake`={sh} is a lot - above 1.5 the shake "
                                  f"forces the scale up so much that you lose the "
                                  f"framing.")
        rot = z.get("rot")
        if rot is not None and (not isinstance(rot, (int, float)) or abs(rot) > 5):
            errores.append(f"{et}: `rot`={rot} out of range (-5 to 5 degrees)")

    if fuertes > 2:
        avisos.append(
            f"{fuertes} zooms of 1.3 or more. The big zoom is the short's punchline: "
            f"if there are four, none of them lands (style.md).")
    if temblores > 3:
        avisos.append(f"{temblores} camera shakes. It is an impact gesture: spread "
                      f"around it loses the impact and reads as a badly held camera.")

    ap = plan.get("apertura")
    if ap is not None and ap is not False:
        if not isinstance(ap, (int, float)) or not (1.0 <= ap <= 1.4):
            errores.append(f"`apertura`={ap} must be `false` or a number 1.0-1.4")


def valida_transiciones(plan, workdir, errores, avisos) -> None:
    tr = plan.get("transiciones")
    if tr in (None, False, [], {}):
        return
    if isinstance(tr, str):
        tr = [{"tipo": tr}]
    elif isinstance(tr, dict):
        tr = [tr]
    if not isinstance(tr, list):
        errores.append("`transiciones` must be a name, an object or a list")
        return

    n_clips = 0
    if workdir:
        base = Path(workdir) / "clips.base.json"
        if base.exists():
            try:
                n_clips = len(json.loads(base.read_text(encoding="utf-8")))
            except Exception:
                n_clips = 0
    if n_clips == 1:
        avisos.append("`transiciones` declared but the short is a single clip: "
                      "there is no seam to put them on.")
    elif n_clips > 1 and len(tr) not in (1, n_clips - 1):
        errores.append(f"there are {n_clips - 1} seam(s) and {len(tr)} transition(s) "
                       f"declared - put one per seam, or a single one for all")

    tipos = set()
    for i, t in enumerate(tr):
        if isinstance(t, str):
            t = {"tipo": t}
        tipo = t.get("tipo", "fade")
        if tipo not in ("corte", "none") and TRANSICIONES and tipo not in TRANSICIONES:
            errores.append(f"transiciones[{i}]: '{tipo}' does not exist - "
                           f"valid: {', '.join(sorted(TRANSICIONES))}")
        tipos.add(tipo)
        d = t.get("duracion", 0.35)
        if not isinstance(d, (int, float)) or not (0.08 <= d <= 1.2):
            if tipo not in ("corte", "none"):
                errores.append(f"transiciones[{i}]: duration {d}s out of range (0.08-1.2)")
        elif d > 0.6:
            avisos.append(f"transiciones[{i}]: {d}s is long for a short. Above half a "
                          f"second the transition is looking at itself.")

    if len(tipos - {"corte", "none"}) > 2:
        avisos.append(
            "more than two different transition types in the same short. Each type "
            "means something (pixelize = we are going somewhere else, smoothleft = the "
            "same action continues); with four languages they mean nothing.")


def valida_dosis(plan, beats, dur, avisos) -> None:
    """El freno de mano: cuántos recursos especiales lleva el short en total.

    Cada uno por separado puede estar justificado y el conjunto ser un circo.
    Un short editado no es el que usa más juguetes, es el que usa el que toca.
    """
    ritmo = plan.get("ritmo") or []
    voz = plan.get("efectos_voz") or []
    sub = plan.get("subtitulos") or {}
    tramos = (sub.get("tramos") or []) if isinstance(sub, dict) else []
    tr = plan.get("transiciones")
    n_tr = 0
    if isinstance(tr, list):
        n_tr = sum(1 for t in tr if (t if isinstance(t, str) else t.get("tipo")) not in
                   ("corte", "none"))
    elif tr:
        n_tr = 1
    especiales = []
    for i, b in enumerate(beats):
        z = b.get("zoom")
        if isinstance(z, dict) and (z.get("shake") or z.get("tipo") in ("push", "pull")):
            especiales.append(i)
    for z in plan.get("zoom") or []:
        if isinstance(z, dict) and (z.get("shake") or z.get("tipo") in ("push", "pull")):
            especiales.append(-1)

    total = len(ritmo) + len(voz) + len(tramos) + n_tr + len(especiales)
    dur = dur or 45.0                      # sin vídeo delante, se supone un short medio
    tope = max(4, int(dur / 8))
    if total > tope:
        avisos.append(
            f"{total} special editing devices (ritmo {len(ritmo)}, voice "
            f"{len(voz)}, subtitulos {len(tramos)}, transiciones {n_tr}, camera "
            f"{len(especiales)}) for {dur:.0f}s of short. This material fits about "
            f"{tope}. Cut the ones nobody would miss if you deleted them - "
            f"those are the spare ones.")


def main() -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("plan")
    ap.add_argument("video", nargs="?", default=None)
    ap.add_argument("--words", default=None,
                    help="words.json of the final timeline (enables the checks "
                         "against the narration)")
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    beats = plan.get("beats", plan if isinstance(plan, list) else [])
    dur = duracion_video(args.video) if args.video else 0.0

    # La transcripción, en las dos líneas de tiempo que hacen falta: la final
    # (para los efectos de voz y los beats) y la base, sin rampas (para el
    # `ritmo`, que se declara sobre la fuente que entra en esa etapa).
    words: list[dict] = []
    words_base: list[dict] = []
    if args.words and Path(args.words).exists():
        try:
            words = json.loads(Path(args.words).read_text(encoding="utf-8"))
        except Exception:
            words = []
        words_base = words
        if args.workdir and _tiempo is not None:
            try:
                mapa = _tiempo.carga(Path(args.workdir))
                if not mapa.trivial:
                    words_base = [{"word": w.get("word", ""),
                                   "start": mapa.final_a_base(w["start"]),
                                   "end": mapa.final_a_base(w["end"])} for w in words]
            except Exception:
                words_base = words

    errores: list[str] = []
    avisos: list[str] = []

    if not beats:
        avisos.append("the plan has no beats - the short will render with captions only")

    tiene_hook = False
    for i, b in enumerate(beats):
        et = f"beat[{i}]"
        kind = b.get("kind")

        if not kind:
            errores.append(f"{et}: missing `kind`")
            continue
        if kind not in REQUERIDOS:
            errores.append(f"{et}: unknown kind '{kind}' - valid: {', '.join(sorted(REQUERIDOS))}")
            continue

        for campo in REQUERIDOS[kind]:
            if b.get(campo) in (None, "", []):
                errores.append(f"{et} ({kind}): missing required field `{campo}`")

        s, e = b.get("start_sec"), b.get("end_sec")
        if s is None or e is None:
            errores.append(f"{et}: missing `start_sec` / `end_sec`")
            continue
        if e <= s:
            errores.append(f"{et}: end_sec ({e}) is not greater than start_sec ({s})")
            continue
        if dur and e > dur + 0.05:
            errores.append(f"{et}: ends at {e}s but the video is {dur:.2f}s long")

        # `reason` obligatorio: obliga a justificar cada overlay. Sin esto los
        # planes se llenan de adornos que no aportan nada.
        if not b.get("reason"):
            errores.append(f"{et} ({kind}): missing `reason` - say in one line what this beat adds")

        lo, hi = DURACION.get(kind, (0, 99))
        d = e - s
        if d < lo:
            avisos.append(f"{et} ({kind}): lasts {d:.2f}s, too short (comfortable minimum {lo}s)")
        elif d > hi:
            avisos.append(f"{et} ({kind}): lasts {d:.2f}s, runs long (comfortable maximum {hi}s)")

        # Un `tip_banner` abajo se pisa con el karaoke. Medido en render: el
        # panel arranca al 54,5% de la altura y el bloque de subtitulos crece
        # hacia arriba desde abajo, asi que en cuanto una linea de karaoke
        # ocupa dos filas llega al 57% y se solapan. Como los subtitulos no se
        # apagan nunca, no hay forma de garantizarlo desde el plan: arriba.
        # No es un choque de carril, y por eso el resto del linter no lo ve.
        if kind == "tip_banner" and b.get("position", "bottom") == "bottom":
            avisos.append(
                f"{et}: a tip_banner at the bottom clashes with the karaoke when the "
                f"caption takes two lines. Put it in `position: \"top\"` unless "
                f"it falls in a gap with no narration.")

        if kind == "hook_title":
            tiene_hook = True
            if s > 0.15:
                errores.append(f"{et}: the hook_title must start at 0.0s, not at {s}s")

        if kind == "spotlight":
            for c in ("x", "y"):
                v = b.get(c)
                if v is not None and not (0 <= v <= 100):
                    errores.append(f"{et}: `{c}`={v} out of range (0-100, they are percentages)")

        if kind == "emoji_burst":
            for j, it in enumerate(b.get("items", [])):
                # Un item es un emoji del sistema o una reacción propia en PNG.
                if not it.get("emoji") and not it.get("image_path"):
                    errores.append(
                        f"{et}.items[{j}]: needs `emoji` or `image_path`")
                if it.get("appear_sec") is None:
                    errores.append(f"{et}.items[{j}]: missing `appear_sec`")
                elif not (s - 0.01 <= it["appear_sec"] <= e):
                    errores.append(
                        f"{et}.items[{j}]: appear_sec {it['appear_sec']} falls outside "
                        f"the beat [{s}, {e}]")

    if not tiene_hook:
        errores.append("missing a `hook_title` beat at 0.0s - it is mandatory (hard_rules 3)")

    # Una frase de énfasis sube el subtítulo al centro EN GRANDE. Si además
    # existe un meme_text que dice lo mismo, el espectador lee la misma frase
    # dos veces, en dos tamaños, a la vez. Detectado en render: es justo el
    # ruido que `knowledge/style.md` manda evitar.
    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFD", str(s).lower())
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]+", " ", s)).strip()

    enfasis_norm = [_norm(f) for f in plan.get("enfasis", []) if str(f).strip()]
    for i, b in enumerate(beats):
        if b.get("kind") not in ("meme_text", "hook_title"):
            continue
        txt = _norm(b.get("text") or b.get("title") or "")
        for f in enfasis_norm:
            if txt and f and (txt in f or f in txt):
                avisos.append(
                    f"beat[{i}] ({b['kind']}) says the same as the `enfasis` phrase "
                    f"'{f}' - it will read duplicated. Change one of the two.")

    # `velocidad`: fuera de 0.5-2.0 la voz deja de entenderse, y por debajo de
    # 0.5 `atempo` ya no puede en una pasada.
    vel = plan.get("velocidad")
    if vel is not None:
        if not isinstance(vel, (int, float)) or vel <= 0:
            errores.append(f"`velocidad`={vel} must be a number greater than 0")
        elif not (0.5 <= vel <= 2.0):
            errores.append(f"`velocidad`={vel} outside the usable range (0.5-2.0)")
        elif vel > 1.6:
            avisos.append(f"`velocidad`={vel} is a lot: above 1.6x the narration "
                          f"trips over itself and stops being understandable.")

    # Bloque `musica`: se valida aquí para que un volumen absurdo o una ruta
    # olvidada salgan en 50 ms y no después de mezclar y renderizar.
    mus = plan.get("musica")
    if mus is not None:
        if isinstance(mus, str):
            mus = {"path": mus}
        if not isinstance(mus, dict):
            errores.append("`musica` must be an object or a path")
        else:
            if not mus.get("path"):
                errores.append("`musica` has no `path` - say which file plays")
            vol = mus.get("volumen", 0.18)
            if not isinstance(vol, (int, float)) or not (0 <= vol <= 1):
                errores.append(f"`musica.volumen`={vol} out of range (0-1)")
            elif vol > 0.35:
                avisos.append(
                    f"`musica.volumen`={vol} is high for a music bed; "
                    f"above 0.3 it starts competing with the narration.")
            for campo in ("inicio_sec", "fade_out"):
                v = mus.get(campo)
                if v is not None and (not isinstance(v, (int, float)) or v < 0):
                    errores.append(f"`musica.{campo}`={v} must be a number >= 0")

    # Bloque `sfx`: efectos puntuales de ElevenLabs. Mismo criterio que el
    # resto — mejor fallar en 50 ms que después de mezclar y renderizar.
    sfx = plan.get("sfx")
    if sfx is not None:
        if not isinstance(sfx, list):
            errores.append("`sfx` must be a list")
        else:
            if len(sfx) > 8:
                avisos.append(
                    f"`sfx`: {len(sfx)} effects in one short. More than 6-8 and the "
                    f"edit sounds like a toy box; let the voice breathe.")
            for i, s in enumerate(sfx):
                et = f"sfx[{i}]"
                if not isinstance(s, dict):
                    errores.append(f"{et}: must be an object")
                    continue
                if not s.get("path"):
                    errores.append(f"{et}: no `path` - say which effect plays")
                at = s.get("at_sec")
                if at is None:
                    errores.append(f"{et}: missing `at_sec` (when it plays)")
                elif not isinstance(at, (int, float)) or at < 0:
                    errores.append(f"{et}: `at_sec`={at} must be a number >= 0")
                elif dur and at > dur:
                    errores.append(
                        f"{et}: `at_sec`={at} falls outside the short ({dur:.1f}s)")
                vol = s.get("volumen", 0.85)
                if not isinstance(vol, (int, float)) or not (0 <= vol <= 1.5):
                    errores.append(f"{et}: `volumen`={vol} out of range (0-1.5)")
            # Dos efectos casi pegados se emborronan entre sí.
            ordenados = sorted(
                [s for s in sfx if isinstance(s, dict)
                 and isinstance(s.get("at_sec"), (int, float))],
                key=lambda s: s["at_sec"])
            for a, b in zip(ordenados, ordenados[1:]):
                if b["at_sec"] - a["at_sec"] < 0.25:
                    avisos.append(
                        f"`sfx`: two effects at {a['at_sec']}s and {b['at_sec']}s "
                        f"clash; separate them by at least 0.25 s or keep one.")

    # Solapes dentro del mismo carril visual.
    for i in range(len(beats)):
        for j in range(i + 1, len(beats)):
            a, b2 = beats[i], beats[j]
            ka, kb = a.get("kind"), b2.get("kind")
            ca, cb = carril(a), carril(b2)
            if ca is None or cb is None or ca != cb:
                continue
            sa, ea = a.get("start_sec"), a.get("end_sec")
            sb, eb = b2.get("start_sec"), b2.get("end_sec")
            if None in (sa, ea, sb, eb):
                continue
            if sa < eb and sb < ea:
                errores.append(
                    f"beat[{i}] ({ka}) and beat[{j}] ({kb}) overlap in lane "
                    f"'{ca}' - they will clash on screen. Separate them in time, or "
                    f"change the card's `anchor` to bottom-left/bottom-right.")

    # Los recursos de editor. Ver el bloque de arriba y knowledge/editing_choices.md.
    #
    # `ritmo` se mide contra la duración de la fuente que ENTRA en esa etapa
    # (la base), no contra la del vídeo final: si el short lleva rampas, esas
    # dos duraciones no son la misma y compararlas daría errores fantasma.
    dur_base = 0.0
    if args.workdir and (Path(args.workdir) / "ritmo.json").exists():
        try:
            dur_base = json.loads(
                (Path(args.workdir) / "ritmo.json").read_text(encoding="utf-8")
            ).get("duracion_fuente", 0.0)
        except Exception:
            dur_base = 0.0
    valida_ritmo(plan, dur_base, words_base, errores, avisos)
    valida_voz(plan, dur, words, errores, avisos)
    valida_subtitulos(plan, dur, errores, avisos)
    valida_camara(plan, beats, errores, avisos)
    valida_transiciones(plan, args.workdir, errores, avisos)
    valida_dosis(plan, beats, dur, avisos)

    for w in avisos:
        print(f"[warning] {w}")
    for e in errores:
        print(f"[ERROR] {e}")

    if errores:
        print(f"\n{len(errores)} error(s). Fix the plan before rendering.")
        sys.exit(1)
    print(f"[lint] plan OK - {len(beats)} beats, {len(avisos)} warning(s)")


if __name__ == "__main__":
    main()
