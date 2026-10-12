#!/usr/bin/env python3
"""
Convierte words.json en un guion de subtítulos karaoke.

Salida: captions_plan.json -> [{start_sec, end_sec, words:[{text,start_sec,end_sec}], emphasis?}]

Los cortes de línea son la mitad del trabajo de un buen subtítulo. Aquí se
agrupa por tres señales, en este orden de prioridad:

  1. **Pausa al hablar** (>0.28 s de silencio entre palabras). Es la señal más
     fiable: si tú respiraste ahí, el corte cae natural.
  2. **Fin de frase** (. ! ?) — corta después.
  3. **Tope duro** de palabras o de duración, para que ninguna línea se quede
     colgada en pantalla.

Los topes son MÁS AGRESIVOS que en un vídeo largo a propósito: en un short
vertical caben 3–4 palabras legibles por línea, no 6, y una línea que dura más
de 1.6 s ya se siente parada. El ritmo del formato es rápido; los subtítulos
tienen que seguirlo.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

# Topes pensados para 9:16. Subirlos hace que el texto encoja para caber y
# deje de leerse de un vistazo en un móvil.
MAX_PALABRAS = 4
MIN_PALABRAS = 1
MAX_DURACION = 1.6      # segundos por línea
PAUSA_CORTE = 0.28      # silencio que fuerza línea nueva
FIN_FRASE = re.compile(r"[.!?]+[\"'»)]?\s*$")

# Contar palabras no basta: cuatro palabras cortas caben en una fila, pero tres
# largas ("en construcción o completamente") las envuelve el navegador en TRES
# filas. El tope inferior de Captions.tsx solo reserva sitio para una
# (`maxTop = ... - fontSize * 1.5`), así que la tercera fila acaba dentro del
# 18% que tapa la interfaz de YouTube y esa palabra no se lee.
#
# CHARS_POR_FILA está calibrado contra render a 1080 de ancho con la fuente de
# subtítulo (9.3% del ancho, en mayúsculas). Medido: "EN CONSTRUCCIÓN" (15
# unidades) entra justo y "LADRILLOS PUEDES" (16) ya no. Se deja en 14 a
# propósito, un punto por debajo del límite real, porque el ancho depende de
# QUÉ letras sean: "O COMPLETAMENTE" también son 15 unidades y NO entra, por
# las dos emes. Pasarse de largo parte una línea de más (inofensivo);
# quedarse corto mete una fila en la zona que tapa YouTube.
CHARS_POR_FILA = 14
MAX_FILAS = 2
# La línea de énfasis se pinta al 12.8% del ancho en vez de al 9.3%, así que
# entran proporcionalmente menos caracteres por fila.
CHARS_ENFASIS_POR_FILA = 11


def filas_necesarias(palabras: list[str]) -> int:
    """Filas que ocupará la línea, simulando el ajuste greedy del navegador.

    Flexbox coloca palabras en la fila hasta que la siguiente no cabe, y
    entonces baja. Se replica aquí para poder cortar ANTES de que una línea
    se vaya a tres filas, en vez de descubrirlo mirando el render.
    """
    filas, actual = 1, 0
    for p in palabras:
        n = len(p)
        if actual == 0:
            actual = n
        elif actual + 1 + n <= CHARS_POR_FILA:
            actual += 1 + n
        else:
            filas += 1
            actual = n
    return filas


def normaliza(s: str) -> str:
    """Normaliza para comparar frases: sin acentos, sin signos, en minúsculas.

    Quitar los acentos importa: el agente que escribe el plan puede pedir
    énfasis en "murio" y la transcripción traer "murió". Sin esta
    normalización el emparejamiento fallaría justo en las palabras españolas
    más comunes.
    """
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]+", " ", s)).strip()


def busca_spans(words: list[dict], frases: list[str]) -> list[tuple[int, int]]:
    """Localiza cada frase de énfasis como un rango de índices de palabra.

    Se compara sobre la transcripción normalizada completa y luego se traduce
    la posición de carácter de vuelta a índices de palabra. Hacerlo sobre el
    texto entero (y no palabra a palabra) permite que la frase pedida no
    coincida exactamente en puntuación o acentos con lo transcrito.
    """
    spans: list[tuple[int, int]] = []
    normalizadas = [normaliza(w["word"]) for w in words]
    # Mapa: posición de carácter en el texto unido -> índice de palabra.
    texto, mapa = "", []
    for i, n in enumerate(normalizadas):
        if not n:
            continue
        if texto:
            texto += " "
            mapa.append(i)
        for _ in n:
            mapa.append(i)
        texto += n

    for f in frases:
        obj = normaliza(f)
        if not obj:
            continue
        pos = texto.find(obj)
        if pos < 0:
            print(f"[warning] emphasis phrase '{f}' does not appear in the transcript")
            continue
        ini, fin = mapa[pos], mapa[min(pos + len(obj) - 1, len(mapa) - 1)]
        if fin - ini + 1 > 6:
            print(f"[warning] '{f}' is {fin - ini + 1} words; at emphasis size it "
                  f"will not fit. Shorten it.")
        # A tamaño de énfasis (12.8% del ancho) entran ~11 caracteres por fila,
        # y una palabra suelta no puede partirse: se sale del encuadre por los
        # dos lados. Se avisa aquí porque en el render solo se ve recortada.
        largas = [w["word"] for w in words[ini:fin + 1]
                  if len(w["word"].strip(" ¿¡")) > CHARS_ENFASIS_POR_FILA]
        if largas:
            print(f"[warning] in '{f}' the word(s) {', '.join(largas)} do not fit "
                  f"at emphasis size and will overflow the frame. Pick another phrase.")
        spans.append((ini, fin))
    return spans


def agrupa(words: list[dict], spans: list[tuple[int, int]]) -> list[dict]:
    """Agrupa palabras en líneas de subtítulo.

    Los rangos de `spans` (frases marcadas para salir EN GRANDE) se emiten como
    una línea propia y completa, saltándose los topes de palabras y duración.
    Si no se tratasen como unidad, una frase de énfasis de 5 palabras se
    partiría en dos líneas por el tope de 4 y nunca se renderizaría entera.
    """
    lineas: list[dict] = []
    actual: list[dict] = []
    inicio_span = {s: e for s, e in spans}

    def cierra(enfasis: bool = False) -> None:
        if not actual:
            return
        ln = {
            "start_sec": round(actual[0]["start"], 3),
            "end_sec": round(actual[-1]["end"], 3),
            "words": [
                {"text": w["word"], "start_sec": round(w["start"], 3),
                 "end_sec": round(w["end"], 3)}
                for w in actual
            ],
        }
        if enfasis:
            ln["emphasis"] = True
        lineas.append(ln)
        actual.clear()

    i = 0
    while i < len(words):
        if i in inicio_span:
            cierra()                       # corta lo que hubiera antes
            fin = inicio_span[i]
            actual.extend(words[i:fin + 1])
            cierra(enfasis=True)           # la frase entera, en una línea
            i = fin + 1
            continue

        w = words[i]
        if actual:
            pausa = w["start"] - actual[-1]["end"]
            dur = w["end"] - actual[0]["start"]
            # Corta también justo antes de que empiece un span, para que no se
            # arrastren palabras sueltas dentro de la línea de énfasis.
            if (pausa >= PAUSA_CORTE
                    or dur >= MAX_DURACION
                    or len(actual) >= MAX_PALABRAS
                    or filas_necesarias([x["word"] for x in actual] + [w["word"]]) > MAX_FILAS
                    or i in inicio_span
                    or FIN_FRASE.search(actual[-1]["word"])):
                cierra()

        actual.append(w)
        i += 1

    cierra()

    # Una línea de una sola palabra corta ("y", "que") se ve como un parpadeo.
    # Se fusiona con la siguiente si el hueco entre ambas es pequeño.
    fusionadas: list[dict] = []
    for ln in lineas:
        if (fusionadas
                and len(fusionadas[-1]["words"]) == 1
                and len(fusionadas[-1]["words"][0]["text"]) <= 3
                and ln["start_sec"] - fusionadas[-1]["end_sec"] < 0.2
                and len(ln["words"]) < MAX_PALABRAS
                and filas_necesarias(
                    [w["text"] for w in fusionadas[-1]["words"]]
                    + [w["text"] for w in ln["words"]]) <= MAX_FILAS):
            prev = fusionadas[-1]
            prev["words"].extend(ln["words"])
            prev["end_sec"] = ln["end_sec"]
        else:
            fusionadas.append(ln)
    return fusionadas


ESTILOS = ("karaoke", "palabra", "bloque")


def marca_estilos(lineas: list[dict], estilo: str, tramos: list[dict]) -> None:
    """Asigna estilo de subtítulo línea a línea.

    Se decide por el CENTRO de la línea, no por su arranque: una línea que
    empieza medio segundo antes de que arranque el tramo pertenece al tramo si
    la mayor parte de ella cae dentro. Cambiar de estilo a media frase se ve
    como un fallo de render, no como una decisión.
    """
    for ln in lineas:
        medio = (ln["start_sec"] + ln["end_sec"]) / 2
        e = estilo
        for tr in tramos:
            if tr["start_sec"] <= medio < tr["end_sec"]:
                e = tr.get("estilo", estilo)
                break
        if e != "karaoke":
            ln["estilo"] = e


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("words_json")
    ap.add_argument("out_json")
    ap.add_argument("--enfasis", default="",
                    help="| separated phrases to render extra large")
    ap.add_argument("--estilo", default="karaoke",
                    help="default style: karaoke | palabra | bloque")
    ap.add_argument("--tramos", default="",
                    help="JSON list of {start_sec,end_sec,estilo} overriding the default")
    a = ap.parse_args()

    estilo = a.estilo or "karaoke"
    if estilo not in ESTILOS:
        print(f"[warning] unknown caption style '{estilo}' - using karaoke")
        estilo = "karaoke"
    tramos = json.loads(a.tramos) if a.tramos.strip() else []
    for tr in tramos:
        if tr.get("estilo", "karaoke") not in ESTILOS:
            print(f"[warning] segment with unknown style '{tr.get('estilo')}' - ignored")
            tr["estilo"] = estilo

    words = json.loads(Path(a.words_json).read_text(encoding="utf-8"))
    words = [w for w in words if w.get("start") is not None and w.get("end") is not None]
    if not words:
        Path(a.out_json).write_text("[]", encoding="utf-8")
        print("[captions] words.json is empty - 0 lines")
        return

    spans = busca_spans(words, [f for f in a.enfasis.split("|") if f.strip()])
    lineas = agrupa(words, spans)
    marca_estilos(lineas, estilo, tramos)
    n_enf = sum(1 for ln in lineas if ln.get("emphasis"))
    otros = {}
    for ln in lineas:
        if ln.get("estilo"):
            otros[ln["estilo"]] = otros.get(ln["estilo"], 0) + 1

    Path(a.out_json).write_text(
        json.dumps(lineas, ensure_ascii=False, indent=2), encoding="utf-8")
    extra = "".join(f", {n} en {k}" for k, n in sorted(otros.items()))
    print(f"[captions] {len(lineas)} lines ({n_enf} with emphasis{extra}) -> {a.out_json}")


if __name__ == "__main__":
    main()
