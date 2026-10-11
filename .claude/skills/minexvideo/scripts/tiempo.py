#!/usr/bin/env python3
"""
Traductor entre las líneas de tiempo del pipeline.

    tiempo.py --workdir <wd> 12.4 31.0        # fuente  -> montaje final
    tiempo.py --workdir <wd> --inversa 8.2    # montaje -> fuente
    tiempo.py --workdir <wd> --tabla          # el mapa entero, legible
    tiempo.py --workdir <wd> --words a.json b.json     # reescala la transcripción
    tiempo.py --workdir <wd> --recoloca plan.json      # recoloca un plan ya escrito

El short pasa por hasta tres estiramientos antes de que nadie escriba un beat:

    bruto  --cortar_silencios-->  base  --ritmo-->  rampas  --velocidad-->  final
             (tramos eliminados)          (por tramos)         (lineal)

La **base** es la línea de tiempo que se transcribe (voz a velocidad natural,
que es la única que Whisper entiende bien) y el **final** es sobre el que miden
los `start_sec` del plan, los subtítulos y todo lo que ve Remotion.

Sin este traductor cada uno de esos pasos obligaría a rehacer cuentas a mano, y
las de `ritmo` ni siquiera son lineales: un beat se desplaza según cuántas
rampas tenga POR DELANTE, no según un factor.

Se usa de dos maneras:

  * **Desde `render.sh`**, para reescalar `words.json` de la base al final. Eso
    es lo que hace que los subtítulos caigan clavados aunque el short lleve
    rampas.
  * **A mano**, cuando ya hay un plan escrito y se le añaden rampas después.
    `--recoloca` mueve todos los tiempos del plan del mapa viejo al nuevo.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Mapa:
    """Composición de los tres estiramientos. Monótona y por tanto invertible."""

    def __init__(self, tramos: list[dict] | None, vel: float,
                 silencios: list[list[float]] | None = None):
        self.tramos = tramos or []
        self.vel = vel or 1.0
        self.silencios = silencios or []

    # ── bruto <-> base ────────────────────────────────────────────────────
    def bruto_a_base(self, t: float) -> float:
        quitado = 0.0
        for a, b in self.silencios:
            if b <= t:
                quitado += b - a
            elif a < t:                     # el tiempo cae DENTRO de un hueco
                quitado += t - a            # eliminado: se pega al borde
        return max(0.0, t - quitado)

    def base_a_bruto(self, t: float) -> float:
        for a, b in sorted(self.silencios):
            base_a = self.bruto_a_base(a)
            if base_a <= t:
                t += b - a
        return t

    # ── base <-> rampas ───────────────────────────────────────────────────
    def base_a_rampas(self, t: float) -> float:
        if not self.tramos:
            return t
        for tr in self.tramos:
            if t < tr["src_start"] - 1e-9:
                return tr["out_start"]
            if tr["tipo"] == "congelado":
                continue                    # src_start == src_end: no consume tiempo
            if t <= tr["src_end"] + 1e-9:
                k = (t - tr["src_start"]) / (tr["src_end"] - tr["src_start"])
                return tr["out_start"] + k * (tr["out_end"] - tr["out_start"])
        return self.tramos[-1]["out_end"]

    def rampas_a_base(self, t: float) -> float:
        if not self.tramos:
            return t
        for tr in self.tramos:
            if t <= tr["out_end"] + 1e-9:
                if tr["tipo"] == "congelado" or tr["out_end"] <= tr["out_start"]:
                    return tr["src_start"]
                k = (t - tr["out_start"]) / (tr["out_end"] - tr["out_start"])
                return tr["src_start"] + k * (tr["src_end"] - tr["src_start"])
        return self.tramos[-1]["src_end"]

    # ── extremos ──────────────────────────────────────────────────────────
    def base_a_final(self, t: float) -> float:
        return self.base_a_rampas(t) / self.vel

    def final_a_base(self, t: float) -> float:
        return self.rampas_a_base(t * self.vel)

    def bruto_a_final(self, t: float) -> float:
        return self.base_a_final(self.bruto_a_base(t))

    def final_a_bruto(self, t: float) -> float:
        return self.base_a_bruto(self.final_a_base(t))

    @property
    def trivial(self) -> bool:
        return not self.tramos and not self.silencios and abs(self.vel - 1) < 1e-9


def carga(workdir: Path, sufijo: str = "") -> Mapa:
    """Lee el mapa del workdir. `sufijo='.anterior'` lee el mapa previo, que es
    lo que permite recolocar un plan escrito antes de cambiar las rampas."""
    ritmo_p = workdir / ("ritmo%s.json" % sufijo)
    vel_p = workdir / (".velocidad%s" % sufijo)
    sil_p = workdir / "silencios.json"
    tramos = None
    if ritmo_p.exists():
        tramos = json.loads(ritmo_p.read_text(encoding="utf-8")).get("tramos")
    vel = 1.0
    if vel_p.exists():
        try:
            vel = float(vel_p.read_text(encoding="utf-8").strip() or 1)
        except ValueError:
            vel = 1.0
    silencios = None
    if sil_p.exists():
        try:
            silencios = json.loads(sil_p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            silencios = None
    return Mapa(tramos, vel, silencios)


CLAVES_TIEMPO = ("start_sec", "end_sec", "appear_sec", "en_sec")


def recoloca(obj, viejo: Mapa, nuevo: Mapa, dentro_de_ritmo: bool = False):
    """Recorre un plan y traduce cada tiempo del mapa viejo al nuevo.

    `ritmo` y `cortar_silencios` se saltan a propósito: sus tiempos se declaran
    en la línea de tiempo de ENTRADA de su propia etapa, no en la final, así
    que traducirlos los rompería.
    """
    if isinstance(obj, list):
        return [recoloca(x, viejo, nuevo, dentro_de_ritmo) for x in obj]
    if isinstance(obj, dict):
        salida = {}
        for k, v in obj.items():
            if k == "ritmo":
                salida[k] = v
            elif k in CLAVES_TIEMPO and isinstance(v, (int, float)) and not dentro_de_ritmo:
                salida[k] = round(nuevo.base_a_final(viejo.final_a_base(float(v))), 3)
            else:
                salida[k] = recoloca(v, viejo, nuevo, dentro_de_ritmo)
        return salida
    return obj


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tiempos", nargs="*", type=float)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--inversa", action="store_true",
                    help="los tiempos dados están en el montaje final")
    ap.add_argument("--tabla", action="store_true")
    ap.add_argument("--words", nargs=2, metavar=("ENTRADA", "SALIDA"),
                    help="reescala una transcripción de la base al final")
    ap.add_argument("--recoloca", metavar="PLAN",
                    help="reescribe los tiempos de un plan del mapa anterior al actual")
    ap.add_argument("--salida", help="destino de --recoloca (por defecto, sobrescribe)")
    a = ap.parse_args()

    wd = Path(a.workdir)
    mapa = carga(wd)

    if a.words:
        entrada, salida = Path(a.words[0]), Path(a.words[1])
        words = json.loads(entrada.read_text(encoding="utf-8"))
        if not mapa.trivial:
            for w in words:
                w["start"] = round(mapa.base_a_final(w["start"]), 3)
                w["end"] = round(mapa.base_a_final(w["end"]), 3)
            # Una rampa puede comprimir dos palabras hasta solaparse por
            # redondeo; el karaoke necesita que el orden se mantenga estricto.
            for x, y in zip(words, words[1:]):
                if y["start"] < x["end"]:
                    y["start"] = x["end"]
                if y["end"] <= y["start"]:
                    y["end"] = y["start"] + 0.04
            print("[time] %d words rescaled to the final timeline"
                  % len(words))
        salida.write_text(json.dumps(words, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        return

    if a.recoloca:
        plan_p = Path(a.recoloca)
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        viejo = carga(wd, ".anterior")
        nuevo = mapa
        destino = Path(a.salida) if a.salida else plan_p
        destino.write_text(
            json.dumps(recoloca(plan, viejo, nuevo), ensure_ascii=False, indent=2),
            encoding="utf-8")
        print("[time] plan repositioned -> %s" % destino)
        print("         CHECK IT: beats keep their place in the narration, but a "
              "ramp may have left one shorter than its minimum.")
        return

    if a.tabla or not a.tiempos:
        print("global speed: x%g" % mapa.vel)
        if mapa.silencios:
            print("silences removed: %d segments, -%.2fs"
                  % (len(mapa.silencios), sum(b - a2 for a2, b in mapa.silencios)))
        if not mapa.tramos:
            print("sin rampas de ritmo")
        for tr in mapa.tramos:
            etq = tr["tipo"] if tr["tipo"] != "rampa" else "x%g" % tr["factor"]
            print("  base %8.2f-%8.2f  ->  final %8.2f-%8.2f   %s"
                  % (tr["src_start"], tr["src_end"],
                     tr["out_start"] / mapa.vel, tr["out_end"] / mapa.vel, etq))
        if not a.tiempos:
            return

    for t in a.tiempos:
        if a.inversa:
            print("final %.3f  ->  base %.3f  ->  bruto %.3f"
                  % (t, mapa.final_a_base(t), mapa.final_a_bruto(t)))
        else:
            print("bruto %.3f  ->  base %.3f  ->  final %.3f"
                  % (t, mapa.bruto_a_base(t), mapa.bruto_a_final(t)))


if __name__ == "__main__":
    main()
