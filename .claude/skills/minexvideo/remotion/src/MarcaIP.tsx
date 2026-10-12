import { AbsoluteFill } from "remotion";
import { C, FONT_CAPTION, accentOf, outline, shapeOutline, stepped, SAFE } from "./theme";

/**
 * Marca de IP permanente del servidor — la que va fija toda la duración del
 * short, no el `tip_banner` de la llamada a la acción.
 *
 * NO es un beat: no se declara en el plan ni pasa por `Short.tsx`. Se renderiza
 * como PNG suelto y `marca-ip/pon_marca_ip.sh` lo superpone con ffmpeg al short
 * YA montado, así que se le puede poner (o cambiar) la IP a un short terminado
 * sin repetir transcripción, plan y render. Se hace desde aquí y no con
 * `drawtext` para que la tipografía sea LA MISMA del karaoke, no un parecido:
 *
 *   npx remotion still src/index.ts MarcaIP salida.png --image-format=png  *     --props='{"texto":"your.text.here","accent":"redstone","variante":"a"}'
 *
 * Vive en la franja y ∈ [154, 235]: por debajo del 8% que tapa la barra de
 * estado del móvil (`SAFE.top`) y por encima del carril donde entran
 * `tip_banner` (0.12) y `meme_text`/`hook_title` (0.13). Es la única banda de
 * la pantalla que ningún beat usa nunca, así que la marca puede estar los 40 s
 * sin pisar nada.
 */
export type MarcaIPProps = { texto: string; accent: string; variante: string };

export const MarcaIP: React.FC<MarcaIPProps> = ({ texto, accent, variante }) => {
  const width = 1080;
  const height = 1920;
  const col = accentOf(accent);

  const size = width * 0.036;
  const base: React.CSSProperties = {
    fontFamily: FONT_CAPTION,
    fontWeight: 900,
    fontSize: size,
    lineHeight: 1,
    letterSpacing: "0.005em",
    textTransform: "uppercase",
    color: C.white,
    whiteSpace: "nowrap",
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div
        style={{
          position: "absolute",
          left: width * 0.043,
          top: height * SAFE.top + height * 0.004,
          display: "flex",
          alignItems: "center",
          gap: width * 0.013,
          opacity: 0.9,
        }}
      >
        {/* a — cuadrado de acento + texto contorneado, sin panel. */}
        {variante === "a" ? (
          <>
            <div
              style={{
                width: size * 0.5,
                height: size * 0.5,
                background: col,
                filter: shapeOutline(width * 0.0032),
              }}
            />
            <div style={{ ...base, textShadow: outline(width * 0.0042) }}>{texto}</div>
          </>
        ) : null}

        {/* b — solo texto contorneado. Lo más callado posible. */}
        {variante === "b" ? (
          <div style={{ ...base, textShadow: outline(width * 0.0042) }}>{texto}</div>
        ) : null}

        {/* c — placa oscura con esquinas en escalón, la lengua de TipBanner
            pero en miniatura y sin cabecera de color. */}
        {variante === "c" ? (
          <div style={{ filter: shapeOutline(width * 0.0032) }}>
            <div
              style={{
                clipPath: stepped(width * 0.009),
                background: "rgba(9,10,14,0.72)",
                padding: `${height * 0.007}px ${width * 0.026}px ${height * 0.008}px`,
                display: "flex",
                alignItems: "center",
                gap: width * 0.014,
              }}
            >
              <div style={{ width: size * 0.42, height: size * 0.42, background: col }} />
              <div style={{ ...base, textShadow: outline(width * 0.003) }}>{texto}</div>
            </div>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
