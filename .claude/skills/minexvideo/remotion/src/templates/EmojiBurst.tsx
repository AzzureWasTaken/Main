import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { popIn, scatterSlot } from "./motion";

const resolveSrc = (s: string): string =>
  /^https?:\/\//i.test(s) ? s : staticFile(s);

/**
 * `emoji_burst` — reacciones que aparecen sobre el gameplay.
 *
 * Es el sustituto de la cara del youtuber: en un short sin facecam, esto es lo
 * que le dice al espectador cómo debe sentirse el momento (💀 esto salió mal,
 * 😱 no me lo esperaba, 🤑 esto vale mucho). Por eso van SOBRE el gameplay y
 * nunca en un panel: reaccionan a lo que se ve, no lo explican.
 *
 * Cada item tiene su propio `appear_sec`, así que acumulan en cascada en vez
 * de aparecer todos a la vez. Uno bien puesto vale más que seis; si pones
 * seis, el frame se convierte en sopa.
 *
 * Un item puede ser un `emoji` del sistema o una `image_path` — un PNG con
 * fondo transparente, normalmente la CARA DEL CANAL reaccionando. La versión
 * con cara propia es más personal y es lo que hace Mikecrack; el emoji del
 * sistema sigue siendo lo correcto para reacciones genéricas (💀, 🤑) o
 * cuando no hay una cara que encaje.
 */

export type EmojiItem = {
  /** Emoji del sistema. Obligatorio salvo que uses `image_path`. */
  emoji?: string;
  /**
   * Reacción propia en PNG con fondo transparente, en vez de emoji del
   * sistema. Se resuelve como el resto de assets: basta el nombre del fichero
   * si vive en la biblioteca generada (`fotos/minecraft-short/`) o junto al
   * vídeo.
   */
  image_path?: string;
  /** Segundos ABSOLUTOS del vídeo, igual que el resto de beats. */
  appear_sec: number;
  /** 0.5–2.0. Por defecto 1. */
  size?: number;
  /** Posición manual 0–100. Si se omite, se reparte en una rejilla dispersa. */
  left?: number;
  top?: number;
};

export const EmojiBurst: React.FC<{
  items: EmojiItem[];
  startSec: number;
  durFrames: number;
}> = ({ items, startSec, durFrames }) => {
  const { fps, width } = useVideoConfig();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {items.map((it, i) => {
        // appear_sec viene en tiempo absoluto; dentro del Sequence el frame
        // arranca en 0, así que hay que restarle el inicio del beat.
        const localAppear = Math.round((it.appear_sec - startSec) * fps);
        const f = frame - localAppear;
        if (f < 0) return null;

        const p = popIn(f, fps, 8);
        // Sobrepasa y vuelve: mismo gesto de golpe que el resto de la skill.
        const scale = interpolate(p, [0, 0.6, 1], [0, 1.35, 1]) * (it.size ?? 1);
        // Flotan hacia arriba mientras viven — les da peso, no quedan pegados.
        const drift = interpolate(f, [0, durFrames], [0, -width * 0.08], {
          extrapolateRight: "clamp",
        });
        // Se van solos en los últimos 8 frames del beat.
        const out = interpolate(frame, [durFrames - 8, durFrames], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const wobble = Math.sin((f / 20) * Math.PI * 2) * 4;

        const slot = scatterSlot(i);
        const left = it.left ?? slot.left;
        const top = it.top ?? slot.top;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${left}%`,
              top: `${top}%`,
              fontSize: width * 0.17,
              lineHeight: 1,
              opacity: out,
              transform: `translate(-50%, -50%) translateY(${drift}px) scale(${scale}) rotate(${wobble}deg)`,
              filter: "drop-shadow(0 8px 18px rgba(0,0,0,0.55))",
            }}
          >
            {it.image_path ? (
              // Mismo tamaño óptico que el emoji del sistema (0.17 del ancho),
              // así una cara propia y un 💀 pesan igual en el frame.
              <Img
                src={resolveSrc(it.image_path)}
                style={{ width: width * 0.19, height: "auto", display: "block" }}
              />
            ) : (
              it.emoji
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
