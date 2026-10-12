import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { C, FONT_CAPTION, accentOf, outline, SAFE } from "../theme";
import { popIn, shake, fadeOut } from "./motion";

/**
 * `image_overlay` — imagen o clip como tarjeta flotante sobre el gameplay.
 *
 * Para memes, capturas de chat, reacciones o un clip de otro momento. La regla
 * que la hace funcionar: **nunca a pantalla completa**. En un short de
 * gameplay, tapar el juego entero para enseñar un meme mata el ritmo — el
 * espectador vino a ver Minecraft. La tarjeta ocupa como mucho media pantalla
 * y el juego sigue corriendo detrás.
 *
 * Acepta imágenes (png/jpg/gif) y vídeo (mp4). El vídeo va siempre mudo:
 * dos audios a la vez es ruido, y el audio del short ya lo lleva tu voz.
 */

export type ImageOverlayProps = {
  /** Ruta relativa dentro del job, o URL. */
  image_path: string;
  /** Pie opcional debajo de la tarjeta. */
  caption?: string;
  accent?: string;
  /** Fracción del ancho del frame. 0.3–0.9, por defecto 0.56. */
  size?: number;
  anchor?: "center" | "top" | "top-left" | "top-right" | "bottom-left" | "bottom-right";
  /** Inclinación en grados. Por defecto un ligero -3 (pegatina). */
  tilt?: number;
};

const resolveSrc = (s: string): string =>
  /^https?:\/\//i.test(s) ? s : staticFile(s);

const isVideo = (s: string): boolean => /\.(mp4|mov|webm|m4v)$/i.test(s);

export const ImageOverlay: React.FC<ImageOverlayProps & { durFrames: number }> = ({
  image_path,
  caption,
  accent,
  size = 0.56,
  anchor = "center",
  tilt = -3,
  durFrames,
}) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const col = accentOf(accent);

  const p = popIn(frame, fps, 9);
  const scale = interpolate(p, [0, 0.6, 1], [0.35, 1.09, 1]);
  const sh = shake(frame, width * 0.004, 9, 4);
  const out = fadeOut(frame, durFrames, 6);

  const w = width * Math.max(0.3, Math.min(0.9, size));

  // Posición según el ancla, siempre dentro de la zona segura.
  const pos: React.CSSProperties = (() => {
    const top = height * (SAFE.top + 0.04);
    const bottom = height * (SAFE.bottom + 0.06);
    const side = width * 0.05;
    switch (anchor) {
      case "top":
        return { top, left: "50%", transform: "translateX(-50%)" };
      case "top-left":
        return { top, left: side };
      case "top-right":
        return { top, right: side };
      case "bottom-left":
        return { bottom, left: side };
      case "bottom-right":
        return { bottom, right: side };
      default:
        // Centrado pero subido un poco: deja libre el carril de subtítulos.
        return { top: height * 0.30, left: "50%", transform: "translateX(-50%)" };
    }
  })();

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          ...pos,
          opacity: out,
        }}
      >
        <div
          style={{
            width: w,
            transform: `${(pos.transform as string) ?? ""} scale(${scale}) rotate(${tilt + sh.rot * 0.3}deg) translate(${sh.x}px, ${sh.y}px)`,
            transformOrigin: "center",
            borderRadius: width * 0.03,
            overflow: "hidden",
            background: C.ink,
            border: `${width * 0.008}px solid ${col}`,
            boxShadow: `0 0 0 ${width * 0.004}px ${C.ink}, 0 ${height * 0.014}px ${height * 0.035}px rgba(0,0,0,0.6)`,
          }}
        >
          {isVideo(image_path) ? (
            <OffthreadVideo
              src={resolveSrc(image_path)}
              // Mudo siempre: el audio del short es tu voz, no la del clip.
              volume={0}
              style={{ width: "100%", display: "block", objectFit: "cover" }}
            />
          ) : (
            <Img
              src={resolveSrc(image_path)}
              style={{ width: "100%", display: "block", objectFit: "cover" }}
            />
          )}

          {caption ? (
            <div
              style={{
                background: col,
                color: C.ink,
                fontFamily: FONT_CAPTION,
                fontWeight: 900,
                fontSize: width * 0.034,
                textTransform: "uppercase",
                letterSpacing: "0.03em",
                textAlign: "center",
                padding: `${height * 0.008}px ${width * 0.02}px`,
              }}
            >
              {caption}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
