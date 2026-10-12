import { Composition, Still } from "remotion";
import { MarcaIP } from "./MarcaIP";
import { Short, type ShortProps } from "./Short";
import { Showcase } from "./Showcase";
import props from "./props.json";

const typed = props as unknown as ShortProps & {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
};

export const Root: React.FC = () => {
  return (
    <>
      {/* La composición real. `render.sh` reescribe props.json antes de cada
          render con el plan, el vídeo fuente y la duración del clip. */}
      <Composition
        id="Short"
        component={Short}
        durationInFrames={typed.durationInFrames || 900}
        fps={typed.fps || 30}
        width={typed.width || 1080}
        height={typed.height || 1920}
        defaultProps={typed}
      />

      {/* Catálogo visual de todas las plantillas, sin gameplay detrás.
          Sirve para dos cosas: ver de un vistazo qué hay disponible, y
          detectar que una plantilla se ha roto sin renderizar un short
          entero. Ábrelo con `npx remotion studio` → composición "Catalogo". */}
      <Composition
        id="Catalogo"
        component={Showcase}
        durationInFrames={30 * 48}
        fps={30}
        width={1080}
        height={1920}
      />
      {/* La marca de IP fija. No es un beat: sale como PNG suelto con
          `remotion still` y se superpone con ffmpeg al short ya montado.
          Ver `MarcaIP.tsx`. */}
      <Still
        id="MarcaIP"
        component={MarcaIP}
        width={1080}
        height={1920}
        defaultProps={{ texto: "your.text.here", accent: "redstone", variante: "a" }}
      />
    </>
  );
};
