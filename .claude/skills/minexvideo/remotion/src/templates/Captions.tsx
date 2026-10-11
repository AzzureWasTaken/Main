import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { C, FONT_CAPTION, outline, shapeOutline, stepped, SAFE } from "../theme";

/**
 * Subtítulos para shorts verticales en español. Tres estilos, un solo idioma
 * visual.
 *
 * El estilo por defecto —y el que hay que usar salvo motivo— es el KARAOKE:
 * una frase corta (2–4 palabras) en pantalla a la vez, en mayúsculas, y la
 * palabra que se está diciendo AHORA se agranda y se pinta del color de
 * acento. Es la pieza que el dueño del canal señaló como "increíbles", así que
 * no se toca.
 *
 * Los otros dos existen para lo mismo que un editor cambia de plano: para que
 * un tramo concreto SUENE distinto sin que parezca otro vídeo.
 *
 *   · `palabra` — una sola palabra enorme por vez. Es el estilo de los tramos
 *     rápidos: enumeraciones, cuentas atrás, frases cortadas a hachazos. Como
 *     solo hay una palabra en pantalla, se puede pintar al doble de tamaño sin
 *     tapar más, y el ritmo de lectura se acopla al de la voz.
 *   · `bloque` — la frase entera con la palabra activa dentro de un bloque de
 *     color. Es el más "gritón" de los tres: destaca sobre biomas claros
 *     (nieve, desierto, el End) donde el contorno negro solo se defiende.
 *
 * Las tres comparten fuente (Montserrat 900), mayúsculas, contorno negro y
 * carril. Cambiar de estilo cambia el ÉNFASIS, nunca la identidad — que es
 * justo lo que separa un montaje con criterio de uno que usa todos los juguetes
 * a la vez.
 *
 * Diferencia crítica con la skill original de la que viene esto: allí los
 * subtítulos se APAGABAN cuando había un overlay en pantalla, porque los
 * overlays eran tomas completas con su propio texto. Aquí no. El gameplay de
 * Minecraft nunca se tapa y los overlays son parciales, así que los subtítulos
 * corren SIEMPRE, de principio a fin. Ver `knowledge/hard_rules.md` rule 2.
 */

export type CaptionWord = {
  text: string;
  start_sec: number;
  end_sec: number;
  accent?: boolean;
};

export type CaptionStyle = "karaoke" | "palabra" | "bloque";

export type CaptionLine = {
  start_sec: number;
  end_sec: number;
  words: CaptionWord[];
  /** Remate: sube al centro y se hace enorme. Úsalo 1–2 veces por short. */
  emphasis?: boolean;
  /** Color de la palabra activa. Por defecto oro. */
  accent?: string;
  /** Estilo de esta línea. Por defecto karaoke. */
  estilo?: CaptionStyle;
};

/** Altura del carril normal, en fracción del alto del frame.
 *  0.66 = por debajo del centro (no tapa la acción) y por encima del 18%
 *  inferior que YouTube ocupa con el título y los botones. */
const LANE_Y = 0.66;

/** Relación empírica entre el tamaño de fuente y el ancho de un carácter en
 *  mayúsculas con esta tipografía. Calibrada contra render a 1080 de ancho:
 *  14 caracteres llenan el 88% útil a un cuerpo del 9.3% del ancho. Sirve para
 *  encoger una palabra suelta muy larga en vez de dejar que se salga. */
const ANCHO_CHAR = 0.676;

export const Captions: React.FC<{ lines: CaptionLine[]; accent?: string }> = ({
  lines,
  accent,
}) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {lines.map((line, i) => {
        const from = Math.round(line.start_sec * fps);
        const dur = Math.max(1, Math.round((line.end_sec - line.start_sec) * fps));
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <CaptionPhrase line={line} accent={line.accent ?? accent ?? C.gold} />
          </Sequence>
        );
      })}
    </>
  );
};

/** Reparto por estilo. El énfasis manda sobre el estilo del tramo: una frase
 *  marcada como remate se pinta siempre en grande y centrada, porque para eso
 *  se marcó. */
const CaptionPhrase: React.FC<{ line: CaptionLine; accent: string }> = ({ line, accent }) => {
  if (!line.emphasis && line.estilo === "palabra") {
    return <PalabraSuelta line={line} accent={accent} />;
  }
  if (!line.emphasis && line.estilo === "bloque") {
    return <Karaoke line={line} accent={accent} bloque />;
  }
  return <Karaoke line={line} accent={accent} />;
};

/**
 * Karaoke (y su variante `bloque`, que es el mismo reparto con la palabra
 * activa metida en una caja de color en vez de solo teñida).
 *
 * La caja se recorta con `stepped()` y se contornea con `shapeOutline()`, no
 * con `border-radius`: en Minecraft no hay una sola esquina redondeada y una
 * píldora sobre un mundo de cubos se lee como la notificación de una app.
 * Misma regla que los paneles — ver `knowledge/estetica-de-los-paneles`.
 */
const Karaoke: React.FC<{ line: CaptionLine; accent: string; bloque?: boolean }> = ({
  line,
  accent,
  bloque = false,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  // Tiempo ABSOLUTO del vídeo fuente. Dentro de un <Sequence> el frame se
  // reinicia a 0, así que hay que volver a sumarle el arranque de la frase
  // para poder comparar contra los start_sec/end_sec de cada palabra, que
  // vienen en segundos absolutos desde words.json.
  const t = frame / fps + line.start_sec;

  const emph = !!line.emphasis;

  // Entrada con muelle: golpe seco, sin fundido. En este formato un fade
  // lee como lento — el corte tiene que ser instantáneo.
  const pop = spring({
    frame,
    fps,
    durationInFrames: 7,
    config: { damping: 12, stiffness: 220, mass: 0.5 },
  });
  const enterScale = interpolate(pop, [0, 1], [0.72, 1]);

  // Salida: se encoge un pelo en los últimos 3 frames para que el cambio
  // entre frases no sea un salto duro.
  const durFrames = Math.max(1, Math.round((line.end_sec - line.start_sec) * fps));
  const exit = interpolate(frame, [durFrames - 3, durFrames], [1, 0.94], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const fontSize = emph ? width * 0.128 : width * 0.093;
  const strokePx = emph ? width * 0.011 : width * 0.0085;
  const top = emph ? height * 0.46 : height * LANE_Y;

  // Tope inferior duro: pase lo que pase, el bloque de texto no invade el
  // 18% que tapa la interfaz de YouTube.
  //
  // El bloque se ancla por ABAJO, no por arriba. Anclado por arriba, una línea
  // que el navegador envuelve en varias filas crece hacia abajo y se mete en
  // la zona que tapa YouTube: reservar sitio para una fila (`- fontSize * 1.5`)
  // no basta y no hay forma fiable de predecir cuántas filas saldrán, porque
  // depende del ancho real de cada letra ("EN CONSTRUCCIÓN" y "CONSTRUCCIÓN O"
  // tienen los mismos caracteres y no ocupan lo mismo). Anclado por abajo, la
  // primera fila queda donde siempre y las que sobren crecen hacia arriba,
  // hacia el gameplay, que es espacio visible.
  const filaAlto = fontSize * 1.08;                      // = lineHeight del span
  const bottomY = Math.min(top + filaAlto, height * (1 - SAFE.bottom));

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "center",
        paddingLeft: width * 0.06,
        paddingRight: width * 0.06,
      }}
    >
      <div
        style={{
          position: "absolute",
          bottom: height - bottomY,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "baseline",
          gap: `${width * 0.034}px`,
          transform: `scale(${enterScale * exit})`,
          transformOrigin: "center",
          maxWidth: "88%",
        }}
      >
        {line.words.map((w, i) => {
          // La palabra activa es la que se está pronunciando en este frame.
          const active = t >= w.start_sec && t < w.end_sec;
          // Un pequeño adelanto (60 ms) hace que el resalte se sienta a
          // tiempo en vez de a remolque: el ojo tarda en llegar a la palabra.
          const almost = t >= w.start_sec - 0.06 && t < w.start_sec;
          const lit = active || almost || w.accent;
          const scale = active ? 1.10 : 1;
          const caja = bloque && lit;
          return (
            <span
              key={i}
              style={{
                fontFamily: FONT_CAPTION,
                fontWeight: 900,
                fontSize,
                lineHeight: 1.08,
                letterSpacing: "-0.01em",
                textTransform: "uppercase",
                color: caja ? C.ink : lit ? accent : C.white,
                textShadow: caja ? "none" : outline(strokePx),
                transform: `scale(${scale})`,
                transformOrigin: "center bottom",
                display: "inline-block",
                ...(caja
                  ? {
                      background: accent,
                      padding: `${fontSize * 0.08}px ${fontSize * 0.16}px`,
                      margin: `${-fontSize * 0.08}px ${-fontSize * 0.16}px`,
                      clipPath: stepped(Math.max(3, fontSize * 0.09)),
                      filter: shapeOutline(strokePx * 0.55),
                    }
                  : {}),
                // Sin transición CSS a propósito: Remotion renderiza frame a
                // frame de forma independiente, así que una transición CSS no
                // se interpolaría — cada frame se pintaría en su estado final.
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/**
 * Una palabra por vez, al doble de cuerpo.
 *
 * Como solo hay una palabra en pantalla, se puede pintar mucho más grande sin
 * ocupar más sitio del que ya ocupaba la frase entera — y el ojo no tiene que
 * buscar cuál es la activa, que es lo que hace que este estilo aguante ritmos
 * a los que el karaoke llega tarde.
 *
 * El cuerpo se encoge para las palabras largas: una palabra no se puede
 * partir, así que sin este ajuste "COMPLETAMENTE" se sale del frame por los
 * dos lados. Se calcula con la misma relación carácter/cuerpo que usa
 * `captions_plan.py` para decidir los cortes de línea.
 */
const PalabraSuelta: React.FC<{ line: CaptionLine; accent: string }> = ({ line, accent }) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const t = frame / fps + line.start_sec;

  // La palabra vigente es la última que ya ha empezado. En los huecos entre
  // palabras se queda la anterior: apagar el subtítulo en cada respiración
  // produce un parpadeo constante.
  let idx = 0;
  for (let i = 0; i < line.words.length; i++) {
    if (t >= line.words[i].start_sec - 0.06) idx = i;
  }
  const w = line.words[idx];

  // Muelle por PALABRA, no por frase: cada una entra con su propio golpe, y
  // eso es lo que da la sensación de que el texto va al ritmo de la voz.
  const desde = Math.round((w.start_sec - line.start_sec) * fps);
  const local = frame - desde;
  const pop = spring({
    frame: Math.max(0, local),
    fps,
    durationInFrames: 8,
    config: { damping: 11, stiffness: 240, mass: 0.5 },
  });
  const escala = interpolate(pop, [0, 1], [0.6, 1]);

  // Cuerpo máximo 15.5% del ancho, y por debajo de eso lo que quepa: una
  // palabra de n caracteres ocupa n · ANCHO_CHAR · cuerpo, y tiene que caber
  // en el 88% útil del frame.
  const largo = Math.max(3, w.text.replace(/[¿¡.,!?]/g, "").length);
  const fontSize = Math.min(width * 0.155, (width * 0.88) / (largo * ANCHO_CHAR));
  const strokePx = fontSize * 0.105;
  const top = height * LANE_Y;
  const bottomY = Math.min(top + fontSize * 1.08, height * (1 - SAFE.bottom));

  return (
    <AbsoluteFill style={{ alignItems: "center" }}>
      <div
        style={{
          position: "absolute",
          bottom: height - bottomY,
          fontFamily: FONT_CAPTION,
          fontWeight: 900,
          fontSize,
          lineHeight: 1.08,
          letterSpacing: "-0.015em",
          textTransform: "uppercase",
          color: w.accent ? accent : C.white,
          textShadow: outline(strokePx),
          transform: `scale(${escala})`,
          transformOrigin: "center bottom",
          whiteSpace: "nowrap",
        }}
      >
        {w.text}
      </div>
    </AbsoluteFill>
  );
};
