import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, FONT_CAPTION, FONT_MEME, accentOf, outline, shapeOutline, stepped, SAFE } from "../theme";
import { slideIn, fadeOut } from "./motion";

/**
 * `tip_banner` — placa con etiqueta para datos, trucos y avisos.
 *
 * Cuándo usarlo en vez de `meme_text`: cuando lo que dices es INFORMACIÓN que
 * el espectador podría querer apuntar ("la mesa de encantar necesita 15
 * estanterías"), no un chiste. El `meme_text` es para el remate; esto es para
 * el dato. Mezclar los dos registros hace que ninguno destaque.
 *
 * Entra deslizando desde la izquierda, no con rebote: es el gesto de "aquí va
 * un apunte", más tranquilo que el del chiste. Vive en 0.545 de altura, justo
 * ENCIMA del carril de subtítulos (0.66), para que nunca se pisen.
 *
 * DISEÑO (rehecho tras el SHORT 7). La versión anterior era una píldora de
 * esquinas redondeadas con una pastilla de color a la izquierda, y el dueño
 * del canal la llamó "fea fea" al lado de los subtítulos. Tres cosas la
 * delataban y las tres están corregidas aquí:
 *
 *   1. `border-radius`. En Minecraft no hay una sola esquina redondeada: una
 *      píldora sobre gameplay de bloques se lee como la notificación de una
 *      app. Ahora las esquinas van escalonadas (`stepped`), que es el lenguaje
 *      del juego, y el borde negro lo pinta `shapeOutline`, el mismo recurso
 *      que ya hacía legibles los subtítulos.
 *   2. Ocupaba el 90% del ancho pasara lo que pasara, así que un dato corto
 *      dejaba medio rectángulo vacío. Ahora la placa se ajusta a su texto.
 *   3. El texto iba en un peso y un tamaño distintos a los del subtítulo, con
 *      lo que parecía de otro vídeo. Ahora es la MISMA tipografía del karaoke
 *      —Montserrat 900, mayúsculas, contorno negro—, solo que más pequeña.
 */

export type TipBannerProps = {
  /** La etiqueta corta: TRUCO, DATO, OJO, AVISO… */
  label: string;
  text: string;
  accent?: string;
  emoji?: string;
  position?: "top" | "bottom";
};

export const TipBanner: React.FC<TipBannerProps & { durFrames: number }> = ({
  label,
  text,
  accent,
  emoji,
  position = "bottom",
  durFrames,
}) => {
  const { width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const x = slideIn(frame, -width * 0.75, 11);
  const out = fadeOut(frame, durFrames, 6);
  const outX = interpolate(frame, [durFrames - 6, durFrames], [0, -width * 0.25], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const top = position === "top" ? height * (SAFE.top + 0.04) : height * 0.545;
  const step = width * 0.022;          // lado del escalón de las esquinas
  const borde = width * 0.006;         // grosor del contorno negro

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          paddingLeft: width * 0.07,
          paddingRight: width * 0.07,
          transform: `translateX(${x + outX}px)`,
          opacity: out,
        }}
      >
        <div
          style={{
            // El contorno va en el envoltorio y no dentro del panel:
            // `drop-shadow` sigue el alfa YA recortado por el clip-path de
            // dentro, así que el borde negro copia el escalón de las esquinas.
            // Con `box-shadow` no se puede: el clip se lo come.
            filter: shapeOutline(borde),
            maxWidth: "100%",
          }}
        >
          <div style={{ clipPath: stepped(step), overflow: "hidden" }}>
            {/* Cabecera: la etiqueta en el color de acento, texto oscuro. */}
            <div
              style={{
                background: col,
                color: C.ink,
                fontFamily: FONT_MEME,
                fontSize: width * 0.042,
                lineHeight: 1,
                letterSpacing: "0.05em",
                textTransform: "uppercase",
                textAlign: "center",
                padding: `${height * 0.012}px ${width * 0.05}px ${height * 0.010}px`,
                whiteSpace: "nowrap",
              }}
            >
              {emoji ? <span style={{ marginRight: width * 0.014 }}>{emoji}</span> : null}
              {label}
            </div>

            {/* Cuerpo: la tipografía del karaoke, un punto más pequeña. */}
            <div
              style={{
                background: "rgba(9,10,14,0.80)",
                color: C.white,
                fontFamily: FONT_CAPTION,
                fontWeight: 900,
                fontSize: width * 0.049,
                lineHeight: 1.16,
                letterSpacing: "-0.005em",
                textTransform: "uppercase",
                textAlign: "center",
                textShadow: outline(width * 0.004),
                padding: `${height * 0.013}px ${width * 0.045}px ${height * 0.016}px`,
              }}
            >
              {text}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
