import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, FONT_CAPTION, accentOf, shapeOutline, stepped, steppedWithTail } from "../theme";
import { popIn, fadeOut } from "./motion";

/**
 * `speech_bubble` — bocadillo para roleplay y doblaje de mobs.
 *
 * El recurso central del humor de roleplay: le pones voz a un aldeano, a un
 * creeper o al amigo que la está liando, y el bocadillo sale de donde está el
 * personaje en pantalla. Sin bocadillo el espectador no sabe QUIÉN habla y el
 * chiste se cae.
 *
 * La cola apunta a `x`/`y` (en % del frame), que es donde está el personaje.
 * El cuerpo se coloca solo por encima o por debajo según haya sitio, para no
 * salirse nunca del frame.
 *
 * DISEÑO (rehecho tras el SHORT 7). El anterior era una caja blanca de
 * esquinas muy redondeadas, con una pastilla de color para el nombre y una
 * cola de triángulo CSS a la que había que simularle el borde con tres
 * `drop-shadow` cruzados. Quedaba a medio camino entre cómic y interfaz web, y
 * el dueño del canal lo llamó "feo feo". Qué cambia:
 *
 *   - Cuerpo y cola son UNA sola forma (`steppedWithTail`), así que la cola ya
 *     no es una pieza pegada: sale del bocadillo. Y el contorno negro lo pinta
 *     `shapeOutline` sobre la forma entera, con lo que tiene el mismo grosor
 *     en todo el perímetro, cola incluida.
 *   - Esquinas escalonadas en vez de redondeadas: es el lenguaje de Minecraft.
 *     Un `border-radius` grande sobre un mundo de cubos canta muchísimo.
 *   - El texto pasa a la tipografía del karaoke (Montserrat 900, mayúsculas),
 *     que es lo que el dueño del canal sí encuentra bonito. En cómic el
 *     rotulado va en mayúsculas de todas formas.
 */

export type SpeechBubbleProps = {
  text: string;
  /** Punto al que apunta la cola — dónde está el personaje, en % del frame. */
  x: number;
  y: number;
  accent?: string;
  /** Nombre de quien habla, en una pestañita pegada al bocadillo. */
  speaker?: string;
};

export const SpeechBubble: React.FC<SpeechBubbleProps & { durFrames: number }> = ({
  text,
  x,
  y,
  accent,
  speaker,
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 8);
  const scale = interpolate(p, [0, 0.6, 1], [0.2, 1.08, 1]);
  const out = fadeOut(frame, durFrames, 5);

  // Si el personaje está en la mitad de abajo, el bocadillo va encima (y la
  // cola apunta hacia abajo). Si está arriba, al revés. Así nunca se sale.
  const above = y > 45;
  const bubbleW = width * 0.6;
  const cx = (x / 100) * width;
  const cy = (y / 100) * height;

  // El bocadillo se centra sobre el personaje pero se frena en los bordes
  // para que no asome por fuera del frame.
  const half = bubbleW / 2;
  const margin = width * 0.04;
  const left = Math.max(margin + half, Math.min(width - margin - half, cx)) - half;

  const step = width * 0.024;          // escalón de las esquinas
  const borde = width * 0.0075;        // contorno negro
  const tailH = height * 0.028;        // cuánto sobresale la cola
  const tailW = width * 0.075;         // ancho de su base

  // La cola nace lo más cerca posible de la vertical del personaje, pero sin
  // salirse del tramo recto del borde: si se monta en una esquina escalonada,
  // el clip-path se cruza consigo mismo y la forma se rompe.
  const minX = step * 2 + tailW / 2;
  const maxX = bubbleW - step * 2 - tailW / 2;
  const tip = Math.max(minX, Math.min(maxX, cx - left));
  const a = tip - tailW / 2;
  const b = tip + tailW / 2;

  const gap = height * 0.028;

  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: out }}>
      <div
        style={{
          position: "absolute",
          left,
          width: bubbleW,
          ...(above ? { bottom: height - cy + gap } : { top: cy + gap }),
          transform: `scale(${scale})`,
          transformOrigin: above ? "center bottom" : "center top",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
        }}
      >
        {speaker ? (
          <div
            style={{
              // La pestaña se solapa medio escalón con el bocadillo para que
              // se lean como una sola pieza y no como dos cosas apiladas.
              marginLeft: width * 0.035,
              marginBottom: -borde * 1.5,
              ...(above ? {} : { order: 2, marginBottom: 0, marginTop: -borde * 1.5 }),
              filter: shapeOutline(borde * 0.85),
              position: "relative",
              zIndex: 2,
            }}
          >
            <div
              style={{
                clipPath: stepped(step * 0.5),
                background: col,
                color: C.ink,
                fontFamily: FONT_CAPTION,
                fontWeight: 900,
                fontSize: width * 0.031,
                lineHeight: 1,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                padding: `${height * 0.0075}px ${width * 0.026}px ${height * 0.0065}px`,
              }}
            >
              {speaker}
            </div>
          </div>
        ) : null}

        <div style={{ width: "100%", filter: shapeOutline(borde), order: 1 }}>
          <div
            style={{
              clipPath: steppedWithTail(step, tailH, a, b, tip, above ? "bottom" : "top"),
              background: C.white,
              color: C.ink,
              fontFamily: FONT_CAPTION,
              fontWeight: 900,
              fontSize: width * 0.045,
              lineHeight: 1.18,
              letterSpacing: "-0.005em",
              textTransform: "uppercase",
              textAlign: "center",
              padding: `${height * 0.017}px ${width * 0.04}px`,
              // El hueco de la cola se reserva con padding: si no, el texto se
              // mete dentro de la punta y se corta.
              ...(above
                ? { paddingBottom: tailH + height * 0.015 }
                : { paddingTop: tailH + height * 0.015 }),
            }}
          >
            {text}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
