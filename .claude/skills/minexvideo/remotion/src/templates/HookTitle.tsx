import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { FONT_MEME, FONT_CAPTION, accentOf, outline, SAFE } from "../theme";
import { popIn, shake } from "./motion";

/**
 * `hook_title` — el primer frame del short. Obligatorio, siempre en 0.0s.
 *
 * En Shorts la decision de seguir viendo se toma antes del primer segundo, y
 * se toma con los ojos: si el frame 0 es gameplay generico, el dedo sigue
 * deslizando. Esto pone la promesa del video escrita en pantalla desde el
 * frame cero.
 *
 * SIN BANDA, a proposito. La version anterior pintaba el titulo sobre un
 * rectangulo solido de color inclinado, que se leia como una miniatura pero
 * se comia casi la mitad del frame justo en el segundo en que el espectador
 * decide si el gameplay le interesa. El dueno del canal lo rechazo por eso:
 * al inicio lo que tiene que verse bonito es el juego.
 *
 * La legibilidad la da ahora el contorno negro grueso, la misma tecnica que
 * usan los subtitulos — que se leen sobre cualquier bioma sin tapar nada. El
 * emoji sube a pieza principal en vez de ir de adorno debajo: comunica el
 * tono de un vistazo y ocupa mucho menos que una linea de texto.
 */

export type HookTitleProps = {
  /** Linea pequena de arriba. Opcional, para contexto ("DIA 100"). */
  kicker?: string;
  /** El gancho. Corto y en mayusculas. \n para partir en dos lineas. */
  title: string;
  accent?: string;
  emoji?: string;
};

export const HookTitle: React.FC<HookTitleProps & { durFrames: number }> = ({
  kicker,
  title,
  accent,
  emoji,
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 8);
  const scale = interpolate(p, [0, 0.55, 1], [0.4, 1.1, 1]);
  const sh = shake(frame, width * 0.008, 14, 3);

  // Salida: se va hacia arriba en los ultimos frames en vez de fundirse.
  const exitY = interpolate(frame, [durFrames - 6, durFrames], [0, -height * 0.12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitOp = interpolate(frame, [durFrames - 5, durFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lines = title.split("\n");
  const longest = Math.max(...lines.map((l) => l.length), 1);

  // Mas pequeno que la version con banda (que llegaba a 0.175 del ancho): sin
  // fondo que rellenar, el titulo no necesita ocupar el frame para leerse, y
  // cuanto menos ocupe mas gameplay se ve. El ajuste por longitud evita que un
  // titulo largo se salga; el minimo evita que se quede en un hook diminuto.
  const fontSize = Math.max(
    Math.min(width * 0.125, (width * 0.84) / (longest * 0.52)),
    width * 0.062,
  );

  // El emoji entra un pelin despues que el texto, para que se lean en dos
  // tiempos y no como un solo bloque.
  const pEmoji = popIn(Math.max(0, frame - 3), fps, 8);
  const emojiScale = interpolate(pEmoji, [0, 0.6, 1], [0, 1.18, 1]);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: exitOp }}>
      <div
        style={{
          position: "absolute",
          top: height * (SAFE.top + 0.05),
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          transform: `translate(${sh.x}px, ${sh.y + exitY}px) rotate(${sh.rot * 0.3}deg)`,
        }}
      >
        {emoji ? (
          <div
            style={{
              fontSize: width * 0.19,
              lineHeight: 1,
              marginBottom: height * 0.004,
              // Sombra caida en vez de contorno: los emojis son a color y un
              // contorno negro alrededor los ensucia.
              filter: `drop-shadow(0 ${height * 0.006}px ${height * 0.012}px rgba(0,0,0,0.75))`,
              transform: `scale(${emojiScale}) rotate(${sh.rot * 1.4}deg)`,
            }}
          >
            {emoji}
          </div>
        ) : null}

        {kicker ? (
          <div
            style={{
              fontFamily: FONT_CAPTION,
              fontWeight: 900,
              fontSize: width * 0.045,
              letterSpacing: "0.12em",
              color: col,
              textShadow: outline(width * 0.0055),
              textTransform: "uppercase",
              marginBottom: height * 0.006,
              transform: `scale(${scale})`,
            }}
          >
            {kicker}
          </div>
        ) : null}

        <div
          style={{
            transform: `scale(${scale})`,
            transformOrigin: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            maxWidth: "92%",
          }}
        >
          {lines.map((ln, i) => (
            <div
              key={i}
              style={{
                fontFamily: FONT_MEME,
                fontSize,
                lineHeight: 1.04,
                color: "#FFFFFF",
                // Contorno mas grueso que cuando habia banda detras: aqui es
                // lo unico que separa el texto del gameplay.
                textShadow: outline(fontSize * 0.095),
                textTransform: "uppercase",
                whiteSpace: "nowrap",
              }}
            >
              {ln}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
