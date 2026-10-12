import { interpolate, spring, Easing } from "remotion";

/**
 * Helpers de movimiento compartidos.
 *
 * Regla de oro del formato: NADA entra con un fundido suave. En un short de
 * comedia el fundido lee como lentitud. Todo entra de golpe, con rebote, y se
 * va rápido. Estos helpers existen para que ninguna plantilla se invente su
 * propia curva y el conjunto tenga una sola sensación.
 */

/** Entrada con rebote: 0 → pasa de largo → asienta en 1. El gesto por defecto. */
export const popIn = (frame: number, fps: number, durationInFrames = 9): number =>
  spring({
    frame,
    fps,
    durationInFrames,
    config: { damping: 11, stiffness: 200, mass: 0.6 },
  });

/**
 * Temblor decreciente. `seed` desacopla elementos distintos para que dos
 * cosas en pantalla no tiemblen sincronizadas (se notaría como un glitch).
 * Determinista a propósito: Remotion puede re-renderizar cualquier frame de
 * forma aislada, así que un Math.random() daría un temblor distinto en cada
 * pasada y el vídeo saldría con ruido.
 */
export const shake = (
  frame: number,
  amplitude: number,
  decayFrames = 12,
  seed = 0,
): { x: number; y: number; rot: number } => {
  const decay = interpolate(frame, [0, decayFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const a = amplitude * decay;
  return {
    x: Math.sin((frame + seed * 7) * 1.9) * a,
    y: Math.cos((frame + seed * 11) * 2.3) * a * 0.7,
    rot: Math.sin((frame + seed * 5) * 1.55) * decay * 2.2,
  };
};

/** Salida rápida: se encoge y desaparece en los últimos `n` frames. */
export const popOut = (frame: number, durFrames: number, n = 5): number =>
  interpolate(frame, [durFrames - n, durFrames], [1, 0.8], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Opacidad de salida, emparejada con popOut. */
export const fadeOut = (frame: number, durFrames: number, n = 5): number =>
  interpolate(frame, [durFrames - n, durFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Deslizamiento con freno, para banners que entran por un lado. */
export const slideIn = (frame: number, distance: number, frames = 10): number =>
  interpolate(frame, [0, frames], [distance, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

/** Latido sutil e infinito. Para cosas que se quedan en pantalla (contadores). */
export const idlePulse = (frame: number, amount = 0.03, period = 34): number =>
  1 + Math.sin((frame / period) * Math.PI * 2) * amount;

/** Reparto determinista en rejilla dispersa, para ráfagas de emojis/ítems.
 *  Devuelve porcentajes 0–100 dentro de la zona segura vertical. */
export const scatterSlot = (i: number): { left: number; top: number } => {
  const slots = [
    { left: 22, top: 30 }, { left: 76, top: 24 }, { left: 32, top: 55 },
    { left: 68, top: 48 }, { left: 18, top: 44 }, { left: 82, top: 38 },
    { left: 50, top: 22 }, { left: 44, top: 60 },
  ];
  return slots[i % slots.length];
};
