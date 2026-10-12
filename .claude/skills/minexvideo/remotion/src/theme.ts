/**
 * Paleta y tipografía — shorts de Minecraft en español, registro comedia/meme.
 *
 * Principio rector: el gameplay de Minecraft es un fondo RUIDOSO — verdes,
 * marrones, cielo azul, partículas, HUD. Cualquier texto que se ponga encima
 * compite con todo eso. Por eso TODO el texto de esta skill lleva contorno
 * negro grueso + sombra: no es un adorno, es lo único que garantiza que se
 * lea sobre una jungla o sobre nieve. Nunca pongas texto sin `outline()`.
 */
import { loadFont as loadLuckiest } from "@remotion/google-fonts/LuckiestGuy";
import { loadFont as loadBangers } from "@remotion/google-fonts/Bangers";
import { loadFont as loadMontserrat } from "@remotion/google-fonts/Montserrat";

/** Texto meme / hooks / remates. Cartoon, gruesa, redondeada. */
export const FONT_MEME = loadLuckiest("normal", { subsets: ["latin"] }).fontFamily;
/** Números, contadores, onomatopeyas. Estilo cómic. */
export const FONT_ACCENT = loadBangers("normal", { subsets: ["latin"] }).fontFamily;
/** Subtítulos. Prioridad absoluta: legibilidad, no personalidad. */
export const FONT_CAPTION = loadMontserrat("normal", {
  weights: ["700", "800", "900"],
  subsets: ["latin"],
}).fontFamily;

/** Paleta Minecraft. Los nombres son del juego a propósito — así el agente
 *  que escribe el plan elige color por SIGNIFICADO, no por estética. */
export const C = {
  /** Verde césped. Acento por defecto, "esto va bien". */
  grass: "#5FD11A",
  grassDeep: "#3A8C10",
  /** Cian diamante. Loot, logros, algo valioso. */
  diamond: "#37E0D0",
  /** Oro / XP. Números, cantidades, "récord". */
  gold: "#FFC01E",
  /** Rojo redstone. Peligro, fallo, muerte, el troll saliendo mal. */
  redstone: "#FF3B30",
  /** Morado encantamiento. Magia, secretos, "lo que no sabías". */
  purple: "#B45CFF",
  /** Fondos y paneles. */
  ink: "#0B0C10",
  night: "#171922",
  stone: "#6E7079",
  white: "#FFFFFF",
} as const;

export type AccentName = "grass" | "diamond" | "gold" | "redstone" | "purple" | "white";

export const accentOf = (name?: string): string =>
  (name && (C as Record<string, string>)[name]) || C.grass;

/**
 * Contorno negro grueso mediante 16 sombras en círculo + una sombra caída.
 *
 * Por qué 16 y no `-webkit-text-stroke`: el stroke nativo de WebKit se pinta
 * CENTRADO sobre el borde del glifo, así que se come el interior de las letras
 * y a grosores altos (los que hacen falta aquí) las vuelve ilegibles. Las
 * sombras en círculo pintan el contorno POR FUERA y dejan el glifo intacto.
 */
export const outline = (px: number, color = "#000000"): string => {
  const steps = 16;
  const shadows: string[] = [];
  for (let i = 0; i < steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    shadows.push(
      `${(Math.cos(a) * px).toFixed(2)}px ${(Math.sin(a) * px).toFixed(2)}px 0 ${color}`,
    );
  }
  // Sombra caída: despega el texto del gameplay para que no se funda con él.
  shadows.push(`0 ${(px * 1.1).toFixed(2)}px ${(px * 1.6).toFixed(2)}px rgba(0,0,0,0.55)`);
  return shadows.join(", ");
};

/**
 * Contorno negro alrededor de una FORMA, no de un texto.
 *
 * Mismo principio que `outline()`: N sombras repartidas en círculo. La
 * diferencia es que `drop-shadow` sigue el canal ALFA del elemento, así que
 * respeta un `clip-path` — que es lo que permite ponerle un borde negro limpio
 * a un panel de esquinas escalonadas o a un bocadillo con cola, sin anidar
 * divs ni pelearse con `box-shadow` (que se recorta con el clip y desaparece).
 */
export const shapeOutline = (px: number, color = "#000000"): string => {
  // Kernel CUADRADO (las 8 vecinas), no un círculo de sombras como en
  // `outline()`. Con el círculo, la unión de las copias redondea las esquinas
  // convexas: el panel sale con el clip escalonado pero el borde negro
  // alrededor curvado, y se pierde justo el efecto que se buscaba. Con las 8
  // vecinas la dilatación es cuadrada y la esquina sigue siendo esquina.
  const d = px.toFixed(2);
  const f = [
    `drop-shadow(${d}px 0 0 ${color})`, `drop-shadow(-${d}px 0 0 ${color})`,
    `drop-shadow(0 ${d}px 0 ${color})`, `drop-shadow(0 -${d}px 0 ${color})`,
    `drop-shadow(${d}px ${d}px 0 ${color})`, `drop-shadow(-${d}px ${d}px 0 ${color})`,
    `drop-shadow(${d}px -${d}px 0 ${color})`, `drop-shadow(-${d}px -${d}px 0 ${color})`,
  ];
  f.push(`drop-shadow(0 ${(px * 2).toFixed(1)}px ${(px * 3).toFixed(1)}px rgba(0,0,0,0.5))`);
  return f.join(" ");
};

/**
 * Esquinas ESCALONADAS, en `clip-path`.
 *
 * Es el detalle que decide si un panel se lee como Minecraft o como la
 * notificación de una app. El juego no tiene una sola esquina redondeada: todo
 * son bloques. Un `border-radius` sobre gameplay de Minecraft canta muchísimo,
 * y era justo lo que hacía feos el banner y el bocadillo.
 *
 * `s` es el lado del escalón en px.
 */
export const stepped = (s: number): string =>
  `polygon(${s}px 0px, calc(100% - ${s}px) 0px, calc(100% - ${s}px) ${s}px, ` +
  `100% ${s}px, 100% calc(100% - ${s}px), calc(100% - ${s}px) calc(100% - ${s}px), ` +
  `calc(100% - ${s}px) 100%, ${s}px 100%, ${s}px calc(100% - ${s}px), ` +
  `0px calc(100% - ${s}px), 0px ${s}px, ${s}px ${s}px)`;

/**
 * Lo mismo, pero con la cola del bocadillo saliendo por arriba o por abajo.
 * `a`/`b` son los bordes de la base de la cola y `tip` la punta, todos en px
 * desde la izquierda del elemento. `tailH` es cuánto sobresale.
 */
export const steppedWithTail = (
  s: number, tailH: number, a: number, b: number, tip: number,
  side: "top" | "bottom",
): string => {
  const T = `${tailH}px`;
  if (side === "bottom") {
    // El cuerpo ocupa de 0 a (100% - tailH); la cola baja hasta el 100%.
    return `polygon(${s}px 0px, calc(100% - ${s}px) 0px, calc(100% - ${s}px) ${s}px, 100% ${s}px, ` +
      `100% calc(100% - ${T} - ${s}px), calc(100% - ${s}px) calc(100% - ${T} - ${s}px), ` +
      `calc(100% - ${s}px) calc(100% - ${T}), ${b}px calc(100% - ${T}), ` +
      `${tip}px 100%, ${a}px calc(100% - ${T}), ` +
      `${s}px calc(100% - ${T}), ${s}px calc(100% - ${T} - ${s}px), ` +
      `0px calc(100% - ${T} - ${s}px), 0px ${s}px, ${s}px ${s}px)`;
  }
  // El cuerpo empieza en tailH; la cola sube hasta 0.
  return `polygon(${tip}px 0px, ${b}px ${T}, calc(100% - ${s}px) ${T}, ` +
    `calc(100% - ${s}px) calc(${T} + ${s}px), 100% calc(${T} + ${s}px), ` +
    `100% calc(100% - ${s}px), calc(100% - ${s}px) calc(100% - ${s}px), ` +
    `calc(100% - ${s}px) 100%, ${s}px 100%, ${s}px calc(100% - ${s}px), ` +
    `0px calc(100% - ${s}px), 0px calc(${T} + ${s}px), ${s}px calc(${T} + ${s}px), ` +
    `${s}px ${T}, ${a}px ${T})`;
};

/** Panel de cristal oscuro — para fichas de ítem, banners y bocadillos. */
export const glass = (accent: string) => ({
  background: "rgba(11,12,16,0.82)",
  border: `3px solid ${accent}`,
  boxShadow: `0 0 0 3px rgba(0,0,0,0.75), 0 12px 40px rgba(0,0,0,0.55), 0 0 28px ${accent}44`,
});

/**
 * Zonas seguras de YouTube Shorts en 9:16.
 * Arriba ~8% lo tapa el estado del móvil; abajo ~18% lo tapan el título, el
 * canal y la barra de acciones. Nada legible puede vivir ahí.
 */
export const SAFE = { top: 0.08, bottom: 0.18 } as const;
