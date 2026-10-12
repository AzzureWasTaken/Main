import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import { Captions, type CaptionLine } from "./templates/Captions";
import { MemeText, type MemeTextProps } from "./templates/MemeText";
import { HookTitle, type HookTitleProps } from "./templates/HookTitle";
import { TipBanner, type TipBannerProps } from "./templates/TipBanner";
import { EmojiBurst, type EmojiItem } from "./templates/EmojiBurst";
import { Spotlight, type SpotlightProps } from "./templates/Spotlight";
import { ItemCard, type ItemCardProps } from "./templates/ItemCard";
import { Counter, type CounterProps } from "./templates/Counter";
import { SpeechBubble, type SpeechBubbleProps } from "./templates/SpeechBubble";
import { ImageOverlay, type ImageOverlayProps } from "./templates/ImageOverlay";
import { C } from "./theme";

const resolveSrc = (s: string): string =>
  /^https?:\/\//i.test(s) ? s : staticFile(s);

/**
 * ═══════════════════════════════════════════════════════════════════════
 *  Short de Minecraft — composición principal
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Tres capas, y el orden NO es negociable:
 *
 *   1. Gameplay (con cámara)   ← el contenido. Nunca se tapa entero.
 *   2. Beats (overlays)        ← reaccionan al gameplay, son parciales.
 *   3. Subtítulos              ← siempre encima, siempre visibles.
 *
 * Esta es la diferencia estructural con la skill de la que viene esto. Allí
 * los overlays eran tomas a pantalla completa que sustituían al presentador,
 * y por eso los subtítulos se apagaban cuando había un overlay activo (dos
 * textos a la vez es ruido). Aquí el gameplay ES el contenido: si lo tapas,
 * el espectador se va. Así que todos los beats son parciales por diseño y los
 * subtítulos corren de principio a fin sin excepción.
 *
 * Corolario práctico: no existe `kind` de "takeover" en esta skill. Si alguna
 * vez añades uno, tendrás que reintroducir la lógica de apagado de
 * subtítulos — y probablemente sea señal de que el beat no encaja aquí.
 */

/**
 * Un movimiento de cámara sobre el gameplay.
 *
 * El bruto es una toma fija: el jugador mueve el ratón, pero el ENCUADRE no se
 * mueve nunca. Esta capa es la que añade la cámara que un short editado sí
 * tiene, y es lo que separa "un clip con texto encima" de "un vídeo montado".
 *
 * `tipo` decide la curva, y cada curva significa una cosa distinta:
 *
 *   · `punch`  — entra en 2 frames y sale en 8. Golpe. Va pegado al remate.
 *                La asimetría es lo que suena a impacto: entrada instantánea,
 *                salida con inercia.
 *   · `snap`   — entra y sale en 1 frame. Más seco todavía; para cortes duros
 *                encadenados donde un punch ya se notaría blando.
 *   · `rampa`  — 6 frames a cada lado, sostenido en medio. Acercamiento
 *                narrativo: "fíjate en esto".
 *   · `push`   — crece de 1 a `scale` a lo largo de TODO el momento. No se
 *                percibe como un zoom sino como tensión que sube; es el gesto
 *                de la cuenta atrás y del "y entonces...".
 *   · `pull`   — al revés: entra ya acercado y se abre. Revelación — el
 *                espectador descubre dónde estaba mirando.
 *
 * `focus` (x/y en % del frame) decide HACIA DÓNDE se acerca. Un zoom siempre
 * centrado sobre una acción que pasa en una esquina acerca el sitio
 * equivocado, y es el error que más delata un zoom automático.
 *
 * `shake` (amplitud en % del ancho) mete temblor de cámara. Para golpes,
 * explosiones y caídas. La escala se sube sola lo justo para que el temblor no
 * saque los bordes del vídeo del encuadre.
 */
export type ZoomMoment = {
  start_sec: number;
  end_sec: number;
  /** 1.0 = sin zoom. En este formato 1.15–1.45 es el rango útil. */
  scale?: number;
  /** Compatibilidad: equivale a `tipo: "punch"`. */
  punch?: boolean;
  tipo?: "punch" | "snap" | "rampa" | "push" | "pull";
  focus?: { x: number; y: number };
  /** Temblor de cámara, en % del ancho. 0.4–1.5 es el rango útil. */
  shake?: number;
  /** Inclinación en grados. ±1.5 ya se nota; más es mareo. */
  rot?: number;
};

export type Beat = { start_sec: number; end_sec: number; reason?: string } & (
  | ({ kind: "hook_title" } & HookTitleProps)
  | ({ kind: "meme_text" } & MemeTextProps)
  | ({ kind: "tip_banner" } & TipBannerProps)
  | ({ kind: "emoji_burst"; items: EmojiItem[] })
  | ({ kind: "spotlight" } & SpotlightProps)
  | ({ kind: "item_card" } & ItemCardProps)
  | ({ kind: "counter" } & CounterProps)
  | ({ kind: "speech_bubble" } & SpeechBubbleProps)
  | ({ kind: "image_overlay" } & ImageOverlayProps)
);

export type ShortProps = {
  videoSrc: string;
  beats: Beat[];
  zoom: ZoomMoment[];
  captions?: CaptionLine[];
  /** Color de acento por defecto de todo el short. */
  accent?: string;
  /** Realce de color del gameplay. 0 = crudo, 1 = por defecto. */
  grade?: number;
  /** Empujón de apertura. `false` lo quita; un número fija la escala inicial. */
  apertura?: number | false;
};

type Camara = {
  scale: number;
  ox: number;      // origen del zoom, % del ancho
  oy: number;      // % del alto
  tx: number;      // temblor, px
  ty: number;
  rot: number;     // grados
};

/**
 * Línea de tiempo de la cámara.
 *
 * Cuando dos momentos se solapan **gana el de más escala, no se suman** —
 * sumar produciría zooms desbocados en cadenas de remates seguidos. El que
 * gana es también el que decide el punto de foco y la inclinación, para que la
 * cámara no esté mirando a un sitio y girando por otro.
 */
const useCamara = (zoom: ZoomMoment[], fps: number, width: number): Camara => {
  const frame = useCurrentFrame();
  const t = frame / fps;
  const cam: Camara = { scale: 1, ox: 50, oy: 50, tx: 0, ty: 0, rot: 0 };
  let shakeAmp = 0;

  zoom.forEach((m, i) => {
    const tipo: NonNullable<ZoomMoment["tipo"]> =
      m.tipo ?? (m.punch ? "punch" : "rampa");
    const objetivo = m.scale ?? 1;
    const inFrames = tipo === "punch" ? 2 : tipo === "snap" ? 1 : tipo === "pull" ? 1 : 6;
    const outFrames = tipo === "punch" ? 8 : tipo === "snap" ? 1 : 6;
    const inT = inFrames / fps;
    const outT = outFrames / fps;
    if (t < m.start_sec - inT || t > m.end_sec + outT) return;

    // `k` = cuánto de este momento está aplicado ahora mismo (0–1). Sirve para
    // la escala, y también para el temblor y la inclinación, que entran y
    // salen con la misma curva para que todo el gesto sea uno solo.
    let k: number;
    if (t < m.start_sec) {
      k = Easing.out(Easing.cubic)((t - (m.start_sec - inT)) / inT);
    } else if (t > m.end_sec) {
      k = Easing.out(Easing.cubic)(1 - (t - m.end_sec) / outT);
    } else {
      k = 1;
    }

    let sc: number;
    const dur = Math.max(1e-6, m.end_sec - m.start_sec);
    const avance = Math.min(1, Math.max(0, (t - m.start_sec) / dur));
    if (tipo === "push") {
      sc = 1 + (objetivo - 1) * Easing.inOut(Easing.quad)(avance) * k;
    } else if (tipo === "pull") {
      sc = 1 + (objetivo - 1) * (1 - Easing.out(Easing.quad)(avance)) * k;
    } else {
      sc = 1 + (objetivo - 1) * k;
    }

    if (m.shake) {
      // El temblor se apaga a lo largo del momento: en uno corto es un golpe
      // seco, en uno largo es una sacudida que se calma. Determinista a
      // propósito — un Math.random() daría un temblor distinto en cada
      // re-render y el vídeo saldría con ruido.
      const amp = ((m.shake / 100) * width) * (1 - avance) * k;
      if (amp > shakeAmp) {
        shakeAmp = amp;
        cam.tx = Math.sin((frame + i * 7) * 1.9) * amp;
        cam.ty = Math.cos((frame + i * 11) * 2.3) * amp * 0.7;
      }
    }

    if (sc > cam.scale) {
      cam.scale = sc;
      cam.ox = m.focus?.x ?? 50;
      cam.oy = m.focus?.y ?? 50;
      cam.rot = (m.rot ?? 0) * k;
    }
  });

  // Un desplazamiento sin escala de sobra saca los bordes negros del vídeo por
  // el lado contrario. Se sube la escala lo justo para taparlo.
  if (shakeAmp > 0) {
    cam.scale = Math.max(cam.scale, 1 + (2.2 * shakeAmp) / width);
  }
  return cam;
};

/**
 * Empujón de apertura: el short abre acercado a 1.12 y se abre a 1.0 en los
 * primeros 0.7 s. Un frame 0 estático lee como "vídeo sin editar" y se
 * desliza; con movimiento desde el primer frame, el ojo se queda.
 */
const useOpenPush = (fps: number, apertura: number | false | undefined): number => {
  const frame = useCurrentFrame();
  const desde = apertura === false ? 1 : apertura ?? 1.12;
  return interpolate(frame, [0, Math.round(0.7 * fps)], [desde, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
};

export const Short: React.FC<ShortProps> = ({
  videoSrc,
  beats,
  zoom,
  captions,
  accent,
  grade = 1,
  apertura,
}) => {
  const { fps, width } = useVideoConfig();
  const cam = useCamara(zoom ?? [], fps, width);
  const openPush = useOpenPush(fps, apertura);
  const scale = cam.scale * openPush;

  // Realce muy contenido. Minecraft ya viene saturado de fábrica, así que
  // esto es un empujón, no un look: si se nota que hay un filtro, está mal.
  const filter =
    grade > 0
      ? `saturate(${1 + 0.08 * grade}) contrast(${1 + 0.05 * grade}) brightness(${1 + 0.012 * grade})`
      : "none";

  return (
    <AbsoluteFill style={{ backgroundColor: C.ink }}>
      {/* ── Capa 1: gameplay ─────────────────────────────────────────── */}
      <AbsoluteFill
        style={{
          transform:
            `translate(${cam.tx.toFixed(2)}px, ${cam.ty.toFixed(2)}px) ` +
            `scale(${scale}) rotate(${cam.rot.toFixed(3)}deg)`,
          transformOrigin: `${cam.ox}% ${cam.oy}%`,
          filter,
        }}
      >
        <OffthreadVideo src={resolveSrc(videoSrc)} />
      </AbsoluteFill>

      {/* ── Capa 2: beats ────────────────────────────────────────────────
          Cada beat vive en su propio <Sequence>, así Remotion no evalúa los
          que no están activos y el coste de un plan con 20 beats es el mismo
          que el de uno con 3 en cualquier frame dado. */}
      {(beats ?? []).map((b, i) => {
        const from = Math.round(b.start_sec * fps);
        const durFrames = Math.max(1, Math.round((b.end_sec - b.start_sec) * fps));
        return (
          <Sequence key={i} from={from} durationInFrames={durFrames} layout="none">
            <BeatRenderer beat={b} durFrames={durFrames} accent={accent} />
          </Sequence>
        );
      })}

      {/* ── Capa 3: subtítulos ───────────────────────────────────────────
          Siempre arriba del todo y sin filtrado por beats. Ver el bloque de
          documentación de arriba. */}
      {captions && captions.length > 0 ? (
        <Captions lines={captions} accent={accent ? undefined : C.gold} />
      ) : null}
    </AbsoluteFill>
  );
};

/** Despacho de beat a plantilla. Un beat de `kind` desconocido no revienta el
 *  render: simplemente no pinta nada. Es deliberado — un plan a medio escribir
 *  debe poder previsualizarse. El linter es quien avisa de los kinds malos. */
const BeatRenderer: React.FC<{
  beat: Beat;
  durFrames: number;
  accent?: string;
}> = ({ beat, durFrames, accent }) => {
  // Acento: el del beat manda; si no lo trae, el global del short.
  const a = (beat as { accent?: string }).accent ?? accent;

  switch (beat.kind) {
    case "hook_title":
      return <HookTitle {...beat} accent={a} durFrames={durFrames} />;
    case "meme_text":
      return <MemeText {...beat} accent={a} durFrames={durFrames} />;
    case "tip_banner":
      return <TipBanner {...beat} accent={a} durFrames={durFrames} />;
    case "emoji_burst":
      return <EmojiBurst items={beat.items} startSec={beat.start_sec} durFrames={durFrames} />;
    case "spotlight":
      return <Spotlight {...beat} accent={a} durFrames={durFrames} />;
    case "item_card":
      return <ItemCard {...beat} accent={a} durFrames={durFrames} />;
    case "counter":
      return <Counter {...beat} accent={a} durFrames={durFrames} />;
    case "speech_bubble":
      return <SpeechBubble {...beat} accent={a} durFrames={durFrames} />;
    case "image_overlay":
      return <ImageOverlay {...beat} accent={a} durFrames={durFrames} />;
    default:
      return null;
  }
};
