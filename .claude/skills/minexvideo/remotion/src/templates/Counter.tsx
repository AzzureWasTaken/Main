import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";
import { C, FONT_ACCENT, FONT_CAPTION, accentOf, outline, SAFE } from "../theme";
import { popIn, shake, fadeOut, idlePulse } from "./motion";

/**
 * `counter` — un número enorme que sube contando.
 *
 * Para el momento en que la gracia ES la cifra: "morí 47 veces", "tardé 9
 * horas", "1.200 bloques". Un número escrito no impresiona; un número que
 * SUBE delante del espectador sí, porque ve el recorrido.
 *
 * El conteo usa una curva `out` (rápido al principio, frena al final) en vez
 * de lineal: así el número llega casi al total enseguida y los últimos
 * dígitos se hacen de rogar, que es donde está la tensión.
 */

export type CounterProps = {
  /** Valor final. Es el que se ve casi todo el rato. */
  value: number;
  /** Desde dónde cuenta. Por defecto 0. */
  from?: number;
  /** Texto encima del número: "MURIÓ", "TARDÉ"… */
  label?: string;
  /** Texto debajo: "VECES", "HORAS", "BLOQUES"… */
  unit?: string;
  accent?: string;
  /** Segundos que dura el conteo. Por defecto 1.1. */
  count_duration?: number;
  position?: "top" | "center";
};

/** Separador de miles en formato español: 1.200, no 1,200. */
const formatEs = (n: number): string =>
  Math.round(n).toLocaleString("en-US");

export const Counter: React.FC<CounterProps & { durFrames: number }> = ({
  value,
  from = 0,
  label,
  unit,
  accent,
  count_duration = 1.1,
  position = "center",
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 8);
  const enter = interpolate(p, [0, 0.6, 1], [0.3, 1.12, 1]);
  const out = fadeOut(frame, durFrames, 6);

  const countFrames = Math.max(1, Math.round(count_duration * fps));
  const shown = interpolate(frame, [0, countFrames], [from, value], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Golpe seco justo cuando el conteo termina: subraya la llegada.
  const landed = frame >= countFrames;
  const sh = landed ? shake(frame - countFrames, width * 0.007, 10, 2) : { x: 0, y: 0, rot: 0 };
  const breathe = landed ? idlePulse(frame - countFrames, 0.022, 40) : 1;

  const top = position === "top" ? height * (SAFE.top + 0.06) : height * 0.34;

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
          opacity: out,
          transform: `translate(${sh.x}px, ${sh.y}px) scale(${enter * breathe}) rotate(${sh.rot * 0.25}deg)`,
        }}
      >
        {label ? (
          <div
            style={{
              fontFamily: FONT_CAPTION,
              fontWeight: 900,
              fontSize: width * 0.055,
              letterSpacing: "0.08em",
              color: C.white,
              textShadow: outline(width * 0.0055),
              textTransform: "uppercase",
              marginBottom: -height * 0.008,
            }}
          >
            {label}
          </div>
        ) : null}

        <div
          style={{
            fontFamily: FONT_ACCENT,
            fontSize: width * 0.34,
            lineHeight: 0.95,
            color: col,
            textShadow: outline(width * 0.019),
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {formatEs(shown)}
        </div>

        {unit ? (
          <div
            style={{
              fontFamily: FONT_ACCENT,
              fontSize: width * 0.098,
              color: C.white,
              textShadow: outline(width * 0.008),
              textTransform: "uppercase",
              marginTop: -height * 0.012,
            }}
          >
            {unit}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
