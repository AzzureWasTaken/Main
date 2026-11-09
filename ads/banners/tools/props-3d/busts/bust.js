import * as THREE from 'three';

const q = new URLSearchParams(location.search);
const W = +q.get('w') || 2400, H = +q.get('h') || 1000;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const loader = new THREE.TextureLoader();
const load = (name) => new Promise((res, rej) => loader.load('tex/' + name, (t) => {
  t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false; t.colorSpace = THREE.SRGBColorSpace; res(t);
}, undefined, rej));

// ---- UV mapping for Minecraft boxes (same layout skinview3d uses) ----
function setUVs(g, u, v, w, h, d, tw, th, mirror = false) {
  const fv = (x1, y1, x2, y2) => [
    new THREE.Vector2(x1 / tw, 1 - y2 / th), new THREE.Vector2(x2 / tw, 1 - y2 / th),
    new THREE.Vector2(x2 / tw, 1 - y1 / th), new THREE.Vector2(x1 / tw, 1 - y1 / th)];
  const F = (x1, y1, x2, y2) => mirror ? fv(x2, y1, x1, y2) : fv(x1, y1, x2, y2);
  const top = F(u + d, v, u + w + d, v + d);
  const bottom = F(u + w + d, v, u + w * 2 + d, v + d);
  const left = F(u, v + d, u + d, v + d + h);
  const front = F(u + d, v + d, u + w + d, v + d + h);
  const right = F(u + w + d, v + d, u + w + d * 2, v + h + d);
  const back = F(u + w + d * 2, v + d, u + w * 2 + d * 2, v + h + d);
  const px = mirror ? left : right, nx = mirror ? right : left;
  const order = (f) => [f[3], f[2], f[0], f[1]];
  const bot = (f) => [f[0], f[1], f[3], f[2]];
  const arr = [];
  for (const f of [order(px), order(nx), order(top), bot(bottom), order(front), order(back)])
    for (const p of f) arr.push(p.x, p.y);
  g.attributes.uv.set(new Float32Array(arr));
  g.attributes.uv.needsUpdate = true;
}
function boxMesh(mat, w, h, d, u, v, tw, th, inflate = 0, mirror = false) {
  const g = new THREE.BoxGeometry(w + 2 * inflate, h + 2 * inflate, d + 2 * inflate);
  setUVs(g, u, v, w, h, d, tw, th, mirror);
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true;
  return m;
}
const mat = (map, alphaTest = 0.01) => new THREE.MeshLambertMaterial({ map, transparent: true, alphaTest, side: THREE.FrontSide });

// ---- Voxel-extruded 2D item (swords, torch, map) ----
function itemModel(tex, thick = 1, scale = 1) {
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
  mesh.castShadow = true;
  const g = new THREE.Group(); g.add(mesh); g.scale.setScalar(scale);
  return g;
}

// ---- Player ----
async function makePlayer({ skin, slim = false, armor = null }) {
  const sk = await load(skin);
  const sm = mat(sk);
  const aw = slim ? 3 : 4;
  const P = new THREE.Group();
  const torso = new THREE.Group(); torso.position.set(0, 12, 0); P.add(torso);
  // body + jacket
  const body = boxMesh(sm, 8, 12, 4, 16, 16, 64, 64); body.position.y = 6; torso.add(body);
  const jacket = boxMesh(sm, 8, 12, 4, 16, 32, 64, 64, 0.25); jacket.position.y = 6; torso.add(jacket);
  // head + hat
  const head = new THREE.Group(); head.position.y = 12; torso.add(head);
  const hm = boxMesh(sm, 8, 8, 8, 0, 0, 64, 64); hm.position.y = 4; head.add(hm);
  const hat = boxMesh(sm, 8, 8, 8, 32, 0, 64, 64, 0.5); hat.position.y = 4; head.add(hat);
  // arms: pivot at shoulder
  function arm(side) {
    const right = side === 'r';
    const pivot = new THREE.Group();
    pivot.position.set((right ? -1 : 1) * (4 + aw / 2), 10, 0);
    const holder = new THREE.Group(); holder.rotation.x = -Math.PI / 2; pivot.add(holder); // arm extends along pivot +z
    const a = boxMesh(sm, aw, 12, 4, right ? 40 : 32, right ? 16 : 48, 64, 64); a.position.y = -4; holder.add(a);
    const s = boxMesh(sm, aw, 12, 4, right ? 40 : 48, right ? 32 : 48, 64, 64, 0.25); s.position.y = -4; holder.add(s);
    torso.add(pivot);
    return { pivot, holder };
  }
  const R = arm('r'), L = arm('l');
  // legs
  function leg(side) {
    const right = side === 'r';
    const pivot = new THREE.Group(); pivot.position.set(right ? -2 : 2, 12, 0);
    const l = boxMesh(sm, 4, 12, 4, right ? 0 : 16, right ? 16 : 48, 64, 64); l.position.y = -6; pivot.add(l);
    const p = boxMesh(sm, 4, 12, 4, right ? 0 : 0, right ? 32 : 48, 64, 64, 0.25); p.position.y = -6; pivot.add(p);
    P.add(pivot); return pivot;
  }
  const RL = leg('r'), LL = leg('l');
  // armor
  if (armor) {
    const a1 = mat(await load(armor + '_layer_1.png'), 0.1), a2 = mat(await load(armor + '_layer_2.png'), 0.1);
    const h2 = boxMesh(a1, 8, 8, 8, 0, 0, 64, 32, 1.0); h2.position.y = 4; head.add(h2);
    const c2 = boxMesh(a1, 8, 12, 4, 16, 16, 64, 32, 1.0); c2.position.y = 6; torso.add(c2);
    const ra = boxMesh(a1, 4, 12, 4, 40, 16, 64, 32, 1.0); ra.position.y = -4; R.holder.add(ra);
    const la = boxMesh(a1, 4, 12, 4, 40, 16, 64, 32, 1.0, true); la.position.y = -4; L.holder.add(la);
    const bootsR = boxMesh(a1, 4, 12, 4, 0, 16, 64, 32, 1.0); bootsR.position.y = -6; RL.add(bootsR);
    const bootsL = boxMesh(a1, 4, 12, 4, 0, 16, 64, 32, 1.0, true); bootsL.position.y = -6; LL.add(bootsL);
    const belt = boxMesh(a2, 8, 12, 4, 16, 16, 64, 32, 0.5); belt.position.y = 6; torso.add(belt);
    const lgR = boxMesh(a2, 4, 12, 4, 0, 16, 64, 32, 0.5); lgR.position.y = -6; RL.add(lgR);
    const lgL = boxMesh(a2, 4, 12, 4, 0, 16, 64, 32, 0.5, true); lgL.position.y = -6; LL.add(lgL);
  }
  return { group: P, torso, head, R, L, RL, LL, aw };
}

// aim a limb's pivot toward a world point (arm extends along pivot +z)
function aim(limb, target, roll = 0) {
  limb.pivot.lookAt(target);
  limb.pivot.rotateZ(roll);
}
// attach an item at the hand (end of the arm), blade continuing along the arm
function hold(limb, model, { roll = 0, off = [0, -9.5, 0.0], rot = -Math.PI * 0.75, shift = 6 } = {}) {
  const g = new THREE.Group();
  model.position.set(shift, shift, 0);       // sprite handle (bottom-left) to origin
  const spin = new THREE.Group(); spin.add(model); spin.rotation.z = rot;
  const rollG = new THREE.Group(); rollG.add(spin); rollG.rotation.y = roll;
  g.add(rollG); g.position.set(...off);
  limb.holder.add(g);
}


// ---- one character bust: head + upper body, turned toward the banner's centre
const skin = q.get('skin') || 'steve.png';
const slim = q.get('slim') === '1';
const P = await makePlayer({ skin, slim });
scene.add(P.group);
P.group.rotation.y = THREE.MathUtils.degToRad(+(q.get('turn') || 28));
P.head.rotation.y = THREE.MathUtils.degToRad(+(q.get('look') || 8));
P.head.rotation.x = THREE.MathUtils.degToRad(+(q.get('nod') || -4));
P.head.rotation.z = THREE.MathUtils.degToRad(+(q.get('tilt') || 0));
const pose = q.get('pose') || 'wave';
const DOWN = Math.PI / 2;                       // in this rig an arm at rotation 0 points forward; +90deg hangs it down
P.R.pivot.rotation.set(DOWN - 0.08, 0, -0.06); P.L.pivot.rotation.set(DOWN - 0.08, 0, 0.06);
if (pose === 'wave') P.R.pivot.rotation.set(-DOWN + 0.35, 0, -0.55);           // right arm up and out
if (pose === 'cheer') { P.R.pivot.rotation.set(-DOWN + 0.3, 0, -0.45); P.L.pivot.rotation.set(-DOWN + 0.3, 0, 0.45); }
if (pose === 'point') P.R.pivot.rotation.set(0.15, 0.5, 0);                    // right arm forward toward the text
scene.add(new THREE.AmbientLight(0xffffff, 1.5));
const key = new THREE.DirectionalLight(0xffffff, 1.9); key.position.set(-40, 70, 80); scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(50, 10, 40); scene.add(fill);
const half = 13;
const cam = new THREE.OrthographicCamera(-half, half, half, -half, 1, 500);
cam.position.set(0, 26, 200); cam.lookAt(0, 26, 0);
renderer.render(scene, cam);
window.__done = true;
