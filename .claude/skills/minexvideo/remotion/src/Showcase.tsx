import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT_CAPTION } from "./theme";
import { MemeText } from "./templates/MemeText";
import { HookTitle } from "./templates/HookTitle";
import { TipBanner } from "./templates/TipBanner";
import { EmojiBurst } from "./templates/EmojiBurst";
import { Spotlight } from "./templates/Spotlight";
import { ItemCard } from "./templates/ItemCard";
import { Counter } from "./templates/Counter";
import { SpeechBubble } from "./templates/SpeechBubble";
import { Captions } from "./templates/Captions";

/**
 * Catálogo de plantillas.
 *
 * El fondo NO es liso a propósito: imita el ruido visual de una partida de
 * Minecraft (verdes, marrones, cielo, bloques). Una plantilla que se lee
 * perfecta sobre gris plano y se pierde sobre un bioma no sirve, y con un
 * fondo neutro nunca lo detectarías. Si algo aquí no se lee, no se leerá en
 * un short.
 */

const FakeGameplay: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const cell = width * 0.11;
  const cols = Math.ceil(width / cell) + 1;
  const rows = Math.ceil(height / cell) + 1;
  // Deriva lenta: simula el movimiento de la cámara del juego.
  const off = (frame * 0.6) % cell;

  const palette = ["#6BA13A", "#7BB944", "#8B6239", "#5E8F2E", "#A0724A", "#4F7A28"];

  return (
    <AbsoluteFill style={{ background: "linear-gradient(#7EC0EE 0%, #7EC0EE 32%, #6BA13A 32%)" }}>
      {Array.from({ length: rows }).map((_, r) =>
        Array.from({ length: cols }).map((_, c) => {
          if (r * cell < height * 0.32) return null;
          // Determinista: mismo bloque en el mismo sitio en cada re-render.
          const idx = (r * 7 + c * 13) % palette.length;
          return (
            <div
              key={`${r}-${c}`}
              style={{
                position: "absolute",
                left: c * cell - off,
                top: r * cell,
                width: cell,
                height: cell,
                background: palette[idx],
                boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.10)",
              }}
            />
          );
        }),
      )}
    </AbsoluteFill>
  );
};

const Label: React.FC<{ text: string }> = ({ text }) => {
  const { width, height } = useVideoConfig();
  return (
    <div
      style={{
        position: "absolute",
        bottom: height * 0.035,
        left: 0,
        right: 0,
        textAlign: "center",
        fontFamily: FONT_CAPTION,
        fontWeight: 900,
        fontSize: width * 0.032,
        letterSpacing: "0.14em",
        color: C.white,
        textTransform: "uppercase",
        textShadow: "0 2px 8px rgba(0,0,0,0.9)",
      }}
    >
      {text}
    </div>
  );
};

const S = 30 * 4; // 4 segundos por plantilla

/** Un slot del catálogo: fondo + plantilla + etiqueta con su `kind`. */
const Slot: React.FC<{ index: number; kind: string; children: React.ReactNode }> = ({
  index,
  kind,
  children,
}) => (
  <Sequence from={index * S} durationInFrames={S} layout="none">
    {children}
    <Label text={kind} />
  </Sequence>
);

export const Showcase: React.FC = () => {
  return (
    <AbsoluteFill>
      <FakeGameplay />

      <Slot index={0} kind="hook_title">
        <HookTitle
          kicker="DAY 100"
          title={"ALMOST\nDIED"}
          accent="redstone"
          emoji="💀"
          durFrames={S}
        />
      </Slot>

      <Slot index={1} kind="meme_text">
        <MemeText text={"THAT WAS\nNOT *THE PLAN*"} accent="gold" emoji="😰" durFrames={S} />
      </Slot>

      <Slot index={2} kind="tip_banner">
        <TipBanner
          label="TRICK"
          text="An enchanting table needs 15 bookshelves around it."
          accent="purple"
          emoji="📚"
          durFrames={S}
        />
      </Slot>

      <Slot index={3} kind="emoji_burst">
        <EmojiBurst
          items={[
            { emoji: "💀", appear_sec: 0.0 },
            { emoji: "😂", appear_sec: 0.5 },
            { emoji: "🔥", appear_sec: 1.0 },
            { emoji: "😱", appear_sec: 1.5 },
          ]}
          startSec={0}
          durFrames={S}
        />
      </Slot>

      <Slot index={4} kind="spotlight">
        <Spotlight x={62} y={48} radius={16} label="did you see it?" accent="gold" durFrames={S} />
      </Slot>

      <Slot index={5} kind="item_card">
        <ItemCard name={"NETHERITE\nPICKAXE"} sub="max tier" accent="diamond" durFrames={S} />
      </Slot>

      <Slot index={6} kind="counter">
        <Counter value={247} label="DIED" unit="TIMES" accent="redstone" durFrames={S} />
      </Slot>

      <Slot index={7} kind="speech_bubble">
        <SpeechBubble
          text="Maybe we should not do this?"
          x={50}
          y={62}
          speaker="ALDEANO"
          accent="grass"
          durFrames={S}
        />
      </Slot>

      <Slot index={8} kind="captions (karaoke)">
        <Captions
          lines={[
            {
              start_sec: 0,
              end_sec: 2.0,
              words: [
                { text: "esto", start_sec: 0.0, end_sec: 0.45 },
                { text: "va", start_sec: 0.45, end_sec: 0.8 },
                { text: "a", start_sec: 0.8, end_sec: 1.0 },
                { text: "salir", start_sec: 1.0, end_sec: 1.5 },
                { text: "mal", start_sec: 1.5, end_sec: 2.0 },
              ],
            },
            {
              start_sec: 2.1,
              end_sec: 4.0,
              emphasis: true,
              words: [
                { text: "muy", start_sec: 2.1, end_sec: 2.6 },
                { text: "mal", start_sec: 2.6, end_sec: 4.0 },
              ],
            },
          ]}
        />
      </Slot>

      {/* Los otros dos estilos de subtítulo. Están aquí para poder compararlos
          con el karaoke de arriba sobre el MISMO fondo: la decisión de usarlos
          casi siempre es "¿se lee esto sobre este bioma?". */}
      <Slot index={9} kind="captions (palabra)">
        <Captions
          lines={[
            {
              start_sec: 0,
              end_sec: 3.2,
              estilo: "palabra",
              words: [
                { text: "wood", start_sec: 0.0, end_sec: 0.7 },
                { text: "stone", start_sec: 0.7, end_sec: 1.4 },
                { text: "iron", start_sec: 1.4, end_sec: 2.1 },
                { text: "diamonds", start_sec: 2.1, end_sec: 3.2 },
              ],
            },
          ]}
        />
      </Slot>

      <Slot index={10} kind="captions (bloque)">
        <Captions
          lines={[
            {
              start_sec: 0,
              end_sec: 3.6,
              estilo: "bloque",
              words: [
                { text: "and", start_sec: 0.0, end_sec: 0.3 },
                { text: "then", start_sec: 0.3, end_sec: 1.2 },
                { text: "this", start_sec: 1.2, end_sec: 2.2 },
                { text: "appeared", start_sec: 2.2, end_sec: 3.6 },
              ],
            },
          ]}
        />
      </Slot>

      <Slot index={11} kind="zoom + accents">
        <MemeText text="THE 6 ACCENTS" accent="white" position="top" durFrames={S} />
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 18 }}>
            {(["grass", "diamond", "gold", "redstone", "purple", "white"] as const).map((k) => (
              <div
                key={k}
                style={{
                  width: 110,
                  height: 110,
                  background: C[k],
                  borderRadius: 18,
                  boxShadow: "0 0 0 6px #0B0C10",
                }}
              />
            ))}
          </div>
        </AbsoluteFill>
      </Slot>
    </AbsoluteFill>
  );
};
