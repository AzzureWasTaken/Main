import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, FONT_MEME, accentOf, outline } from "../theme";
import { popIn, fadeOut } from "./motion";

/**
 * `spotlight` — oscurece todo menos un círculo, y le pone un anillo animado.
 *
 * Resuelve el problema más común de un short de Minecraft: dices "mirad esto"
 * señalando algo diminuto — un bloque concreto, un mob al fondo, un número del
 * HUD — y el espectador no sabe dónde mirar en un frame lleno de cosas. Aquí
 * literalmente se lo apagas todo menos eso.
 *
 * Las coordenadas van en porcentaje del frame (0–100), así que se pueden sacar
 * a ojo de un fotograma extraído con `extract_stills.sh` sin calcular píxeles.
 *
 * Úsalo poco. Es un gesto fuerte: si oscureces la pantalla cinco veces en un
 * short de 40 segundos, deja de significar "esto importa".
 */

export type SpotlightProps = {
  /** Centro del foco, en % del frame. */
  x: number;
  y: number;
  /** Radio en % del ancho. Por defecto 18. */
  radius?: number;
  /** Cuánto se oscurece el resto. 0–1, por defecto 0.72. */
  dim?: number;
  /** Etiqueta opcional junto al foco. */
  label?: string;
  accent?: string;
};

export const Spotlight: React.FC<SpotlightProps & { durFrames: number }> = ({
  x,
  y,
  radius = 18,
  dim = 0.72,
  label,
  accent,
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 10);
  const out = fadeOut(frame, durFrames, 6);
  // El agujero se abre de golpe; el oscurecido entra con él.
  const r = interpolate(p, [0, 1], [radius * 2.2, radius]);
  const dimNow = interpolate(p, [0, 1], [0, dim]) * out;

  // Anillo que late para que el ojo lo encuentre aunque el fondo sea claro.
  const pulse = 1 + Math.sin((frame / 22) * Math.PI * 2) * 0.045;
  const ringR = r * pulse;

  const cx = (x / 100) * width;
  const cy = (y / 100) * height;
  const rPx = (ringR / 100) * width;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* El oscurecido con agujero se hace con un radial-gradient en vez de
          un mask: es una sola capa, no necesita compositing extra y el borde
          sale suave gratis. */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle ${rPx}px at ${cx}px ${cy}px, rgba(0,0,0,0) 0%, rgba(0,0,0,0) 72%, rgba(0,0,0,${dimNow}) 100%)`,
        }}
      />
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", inset: 0 }}
        viewBox={`0 0 ${width} ${height}`}
      >
        <circle
          cx={cx}
          cy={cy}
          r={rPx}
          fill="none"
          stroke={col}
          strokeWidth={width * 0.011}
          opacity={out}
        />
        <circle
          cx={cx}
          cy={cy}
          r={rPx}
          fill="none"
          stroke={C.ink}
          strokeWidth={width * 0.004}
          opacity={out * 0.9}
        />
      </svg>

      {label ? (
        <div
          style={{
            position: "absolute",
            left: cx,
            // La etiqueta va debajo del foco salvo que el foco esté ya abajo,
            // en cuyo caso salta arriba para no salirse del frame.
            top: y > 62 ? cy - rPx - height * 0.075 : cy + rPx + height * 0.018,
            transform: `translateX(-50%) scale(${interpolate(p, [0, 1], [0.6, 1])})`,
            fontFamily: FONT_MEME,
            fontSize: width * 0.062,
            color: C.white,
            textShadow: outline(width * 0.006),
            textTransform: "uppercase",
            whiteSpace: "nowrap",
            opacity: out,
          }}
        >
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
