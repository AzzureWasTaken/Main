// Renders one Minecraft prop (a textured block or an extruded item) on a transparent square canvas.
//   props.html?kind=block&top=grass_block_top&side=grass_block_side&bottom=dirt&tint=7cbd6b
//   props.html?kind=item&tex=diamond_sword&ry=-0.5&rz=0
import * as THREE from 'three';

const q = new URLSearchParams(location.search);
const S = +q.get('size') || 600;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(S, S);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const loader = new THREE.TextureLoader();
const load = (n) => new Promise((res, rej) => loader.load('ptex/' + n + '.png', (t) => {
  t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  t.colorSpace = THREE.SRGBColorSpace; res(t);
}, undefined, rej));

function tinted(tex, hex) {             // grass_block_top is grey in the game files; the game tints it per biome
  const c = document.createElement('canvas'); c.width = c.height = 16;
  const x = c.getContext('2d'); x.drawImage(tex.image, 0, 0);
  const d = x.getImageData(0, 0, 16, 16), t = new THREE.Color('#' + hex);
  for (let i = 0; i < d.data.length; i += 4) {
    d.data[i] *= t.r; d.data[i + 1] *= t.g; d.data[i + 2] *= t.b;
  }
  x.putImageData(d, 0, 0);
  const out = new THREE.CanvasTexture(c);
  out.magFilter = THREE.NearestFilter; out.minFilter = THREE.NearestFilter; out.generateMipmaps = false; out.colorSpace = THREE.SRGBColorSpace;
  return out;
}

function itemModel(tex, thick = 1) {
  const c = document.createElement('canvas'); c.width = c.height = 16;
  const x = c.getContext('2d'); x.drawImage(tex.image, 0, 0, 16, 16);
  const data = x.getImageData(0, 0, 16, 16).data;
  const cells = [];
  for (let j = 0; j < 16; j++) for (let i = 0; i < 16; i++) {
    const k = (j * 16 + i) * 4; if (data[k + 3] > 100) cells.push([i, j, data[k], data[k + 1], data[k + 2]]);
  }
  const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, thick), new THREE.MeshLambertMaterial({ color: 0xffffff }), cells.length);
  const m = new THREE.Matrix4(), col = new THREE.Color();
  cells.forEach(([i, j, r, g, b], n) => {
    m.makeTranslation(i + 0.5 - 8, 7.5 - j, 0); mesh.setMatrixAt(n, m);
    mesh.setColorAt(n, col.setRGB(r / 255, g / 255, b / 255, THREE.SRGBColorSpace));
  });
  return mesh;
}

const kind = q.get('kind') || 'block';
let obj;
if (kind === 'block') {
  const side = await load(q.get('side'));
  let top = await load(q.get('top') || q.get('side'));
  const bottom = await load(q.get('bottom') || q.get('side'));
  if (q.get('tint')) top = tinted(top, q.get('tint'));
  const mat = (t) => new THREE.MeshLambertMaterial({ map: t });
  obj = new THREE.Mesh(new THREE.BoxGeometry(16, 16, 16), [mat(side), mat(side), mat(top), mat(bottom), mat(side), mat(side)]);
  obj.rotation.set(+(q.get('rx') ?? 0.52), +(q.get('ry') ?? 0.785), 0, 'XYZ');
} else {
  obj = itemModel(await load(q.get('tex')), +(q.get('thick') || 1.2));
  obj.rotation.set(+(q.get('rx') || 0), +(q.get('ry') || -0.45), +(q.get('rz') || 0), 'YXZ');
}
scene.add(obj);

scene.add(new THREE.AmbientLight(0xffffff, 1.35));
const key = new THREE.DirectionalLight(0xffffff, 2.1); key.position.set(-30, 60, 50); scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(40, -10, 30); scene.add(fill);

const half = kind === 'block' ? 15.5 : 11.5;
const cam = new THREE.OrthographicCamera(-half, half, half, -half, 1, 500);
cam.position.set(0, 0, 100); cam.lookAt(0, 0, 0);
renderer.render(scene, cam);
window.__done = true;
