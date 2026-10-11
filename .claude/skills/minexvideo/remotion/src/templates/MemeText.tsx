import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, FONT_MEME, accentOf, outline, SAFE } from "../theme";
import { popIn, shake, fadeOut } from "./motion";

/**
 * `meme_text` — el bloque de texto grande que remata un chiste.
 *
 * Es la plantilla más usada del formato y la que más fácil se estropea. Dos
 * reglas que la mantienen bien:
 *
 *  1. **Nunca tapa el centro de la acción.** Por defecto va arriba (`top`),
 *     porque en Minecraft lo que importa suele pasar en el centro del frame
 *     — el jugador, el mob, el bloque que explota. Usa `center` solo cuando
 *     el texto ES el momento y el gameplay puede esperar medio segundo.
 *  2. **Pocas palabras.** Tres o cuatro. Si necesitas una frase entera, eso
 *     no es un meme_text, son los subtítulos haciendo su trabajo.
 *
 * Soporta `\n` para forzar salto de línea y `*palabra*` para pintar una sola
 * palabra del color de acento.
 */

export type MemeTextProps = {
  text: string;
  /** grass | diamond | gold | redstone | purple | white */
  accent?: string;
  position?: "top" | "center" | "bottom";
  /** Emoji opcional pegado encima del texto. */
  emoji?: string;
  /** Intensidad del temblor de entrada. 0 = quieto. 1 = por defecto. */
  impact?: number;
};

export const MemeText: React.FC<MemeTextProps & { durFrames: number }> = ({
  text,
  accent,
  position = "top",
  emoji,
  impact = 1,
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 9);
  // Sobrepasa el 1.0 y vuelve: es lo que da la sensación de golpe.
  const scale = interpolate(p, [0, 0.6, 1], [0.25, 1.12, 1]);
  const sh = shake(frame, width * 0.006 * impact, 11, 1);
  const out = fadeOut(frame, durFrames, 5);

  const lines = text.split("\n");
  const longest = Math.max(...lines.map((l) => l.replace(/\*/g, "").length), 1);
  // Auto-ajuste: una línea larga tiene que encoger o se sale del frame.
  // 88% del ancho es el límite; por debajo de 0.42 ya no se lee de un vistazo
  // en un móvil, así que ahí es mejor partir el texto en dos beats.
  const base = width * 0.155;
  const fitted = Math.min(base, (width * 0.88) / (longest * 0.52));
  const fontSize = Math.max(fitted, width * 0.062);

  const top =
    position === "top"
      ? height * (SAFE.top + 0.05)
      : position === "center"
        ? height * 0.40
        : height * (1 - SAFE.bottom) - fontSize * lines.length * 1.3;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: height * 0.006,
          opacity: out,
          transform: `translate(${sh.x}px, ${sh.y}px) scale(${scale}) rotate(${sh.rot * 0.35}deg)`,
          transformOrigin: "center",
        }}
      >
        {emoji ? (
          <div style={{ fontSize: fontSize * 0.95, lineHeight: 1, marginBottom: -fontSize * 0.1 }}>
            {emoji}
          </div>
        ) : null}
        {lines.map((ln, i) => (
          <div
            key={i}
            style={{
              fontFamily: FONT_MEME,
              fontSize,
              lineHeight: 1.02,
              color: C.white,
              textShadow: outline(fontSize * 0.075),
              textAlign: "center",
              textTransform: "uppercase",
              maxWidth: "92%",
            }}
          >
            {/* *palabra* → pintada con el color de acento */}
            {ln.split(/(\*[^*]+\*)/g).map((part, j) =>
              part.startsWith("*") && part.endsWith("*") && part.length > 2 ? (
                <span key={j} style={{ color: col }}>
                  {part.slice(1, -1)}
                </span>
              ) : (
                <span key={j}>{part}</span>
              ),
            )}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
