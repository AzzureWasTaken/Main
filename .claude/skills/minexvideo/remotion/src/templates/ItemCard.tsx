import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, FONT_MEME, FONT_CAPTION, accentOf, outline, SAFE } from "../theme";
import { popIn, fadeOut } from "./motion";

/**
 * `item_card` — ficha de un ítem o bloque de Minecraft.
 *
 * Cuando nombras algo del juego ("necesitas una pica de netherita"), el
 * espectador que no juega desde hace años no sabe de qué hablas y el que sí
 * juega agradece la confirmación visual. Esto lo enseña sin cortar el
 * gameplay: ficha pequeña en una esquina, el juego sigue corriendo.
 *
 * El icono es opcional. Si no le pasas `image_path`, la ficha se dibuja igual
 * con solo el nombre y un cuadro de color — no bloquea el render por no tener
 * el PNG. Los iconos van en `assets/items/` y se referencian por nombre de
 * archivo, sin ruta ("netherite_pickaxe.png").
 *
 * `renderizado por píxel`: los iconos de Minecraft son de 16x16 px. Se fuerza
 * `imageRendering: pixelated` para que al escalarlos se vean como bloques
 * nítidos y no como una mancha borrosa interpolada.
 */

export type ItemCardProps = {
  /** Nombre visible. En español y en mayúsculas: "PICA DE NETHERITA". */
  name: string;
  image_path?: string;
  /** Línea pequeña debajo: cantidad, rareza, coste… */
  sub?: string;
  accent?: string;
  /** Esquina donde vive. Por defecto arriba a la derecha. */
  anchor?: "top-left" | "top-right" | "bottom-left" | "bottom-right";
};

const resolveSrc = (s: string): string =>
  /^https?:\/\//i.test(s) ? s : staticFile(s);

export const ItemCard: React.FC<ItemCardProps & { durFrames: number }> = ({
  name,
  image_path,
  sub,
  accent,
  anchor = "top-right",
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 9);
  const scale = interpolate(p, [0, 0.6, 1], [0.3, 1.1, 1]);
  const out = fadeOut(frame, durFrames, 6);

  const right = anchor.endsWith("right");
  const bottom = anchor.startsWith("bottom");
  // Se ancla dentro de la zona segura: arriba por debajo del 8% del estado
  // del móvil, abajo por encima del 18% de la interfaz de YouTube.
  const pos: React.CSSProperties = {
    [right ? "right" : "left"]: width * 0.05,
    [bottom ? "bottom" : "top"]: bottom
      ? height * (SAFE.bottom + 0.04)
      : height * (SAFE.top + 0.03),
  };

  const box = width * 0.20;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          ...pos,
          opacity: out,
          transform: `scale(${scale}) rotate(${right ? 2 : -2}deg)`,
          transformOrigin: right ? "top right" : "top left",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: height * 0.005,
          padding: `${height * 0.012}px ${width * 0.022}px`,
          borderRadius: width * 0.028,
          background: "rgba(11,12,16,0.86)",
          border: `${width * 0.007}px solid ${col}`,
          boxShadow: `0 0 0 ${width * 0.004}px ${C.ink}, 0 ${height * 0.01}px ${height * 0.028}px rgba(0,0,0,0.6)`,
        }}
      >
        <div
          style={{
            width: box,
            height: box,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: `${col}22`,
            borderRadius: width * 0.014,
            border: `${width * 0.003}px solid ${col}66`,
          }}
        >
          {image_path ? (
            <Img
              src={resolveSrc(image_path)}
              style={{
                width: "86%",
                height: "86%",
                objectFit: "contain",
                imageRendering: "pixelated",
                filter: "drop-shadow(0 4px 10px rgba(0,0,0,0.5))",
              }}
            />
          ) : (
            // Sin icono: un cuadro del color de acento hace de marcador. La
            // ficha sigue comunicando; no se rompe el render por un PNG que
            // falta.
            <div
              style={{
                width: "60%",
                height: "60%",
                background: col,
                borderRadius: width * 0.006,
                boxShadow: `inset 0 0 0 ${width * 0.006}px rgba(0,0,0,0.25)`,
              }}
            />
          )}
        </div>

        <div
          style={{
            fontFamily: FONT_MEME,
            fontSize: width * 0.042,
            color: C.white,
            textShadow: outline(width * 0.0035),
            textTransform: "uppercase",
            textAlign: "center",
            maxWidth: box * 1.6,
            lineHeight: 1.05,
          }}
        >
          {name}
        </div>

        {sub ? (
          <div
            style={{
              fontFamily: FONT_CAPTION,
              fontWeight: 800,
              fontSize: width * 0.028,
              color: col,
              textShadow: outline(width * 0.002),
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {sub}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
