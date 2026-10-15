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

// =====================================================================
const [netherSword, diaSword, torchTex, mapTex] = await Promise.all([
  load('netherite_sword.png'), load('diamond_sword.png'), load('torch.png'), load('map.png')]);

const A = await makePlayer({ skin: 'steve.png', armor: 'netherite' });
const B = await makePlayer({ skin: 'alex.png', slim: true, armor: 'diamond' });
const E = await makePlayer({ skin: 'makena.png' });
scene.add(A.group, B.group, E.group);

const CLASH = new THREE.Vector3(0, 35, 5);
// -- duelist A (left), faces right/camera
A.group.position.set(-22, 0, 0); A.group.rotation.y = THREE.MathUtils.degToRad(42);
B.group.position.set(22, 0, 2); B.group.rotation.y = THREE.MathUtils.degToRad(-42);
for (const [P, front, back] of [[A, A.LL, A.RL], [B, B.RL, B.LL]]) {
  front.rotation.x = -0.62; back.rotation.x = 0.5;
  P.torso.rotation.x = 0.14; P.head.rotation.x = -0.05;
}
scene.updateMatrixWorld(true);
hold(A.R, itemModel(netherSword, 1, 1.3), { roll: Math.PI / 2 });
hold(B.R, itemModel(diaSword, 1, 1.3), { roll: Math.PI / 2 });
aim(A.R, new THREE.Vector3(7, 41, 4), 0);
aim(B.R, new THREE.Vector3(-7, 41, 6), 0);
A.L.pivot.rotation.set(0.9, 0, -0.35); B.L.pivot.rotation.set(0.9, 0, 0.35);

// -- explorer: striding along with a torch held up
E.group.position.set(-68, 0, -10); E.group.rotation.y = THREE.MathUtils.degToRad(35);
E.RL.rotation.x = -0.55; E.LL.rotation.x = 0.5; E.torso.rotation.x = 0.05; E.head.rotation.y = -0.25;
E.group.updateMatrixWorld(true);
const torch = itemModel(torchTex, 2, 1.0);
hold(E.R, torch, { roll: 0, rot: 0, shift: 0, off: [0, -9.5, 0] });
E.R.pivot.rotation.set(-2.0, 0.0, -0.12);   // raised forward and up
E.L.pivot.rotation.set(0.55, 0, 0.12);      // swinging back
// torch flame
for (const [dx, dy, s2, c] of [[0, 0, 2.6, 0xffe27a], [0, 1.8, 2.0, 0xffa02a], [0, 3.2, 1.2, 0xff6a14]]) {
  const f = new THREE.Mesh(new THREE.BoxGeometry(s2, s2, s2), new THREE.MeshBasicMaterial({ color: c }));
  f.position.set(dx, -9.5 - 5 - 6 + dy * 0, 0); f.userData.flame = true; E.R.holder.add(f);
  f.position.set(0, -9.5 - 5.5 - 0.0 + 0, 0); f.position.y = -9.5 - 6.2 - dy; // top of the stick, further along the arm
}

// ---- sparks ----
const sparks = new THREE.Group(); scene.add(sparks);
const sparkMat = [0xfff2a8, 0xffb43a, 0xff7a1e].map((c) => new THREE.MeshBasicMaterial({ color: c }));
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
for (let i = 0; i < 46; i++) {
  const s = 0.35 + rnd() * 0.9;
  const m = new THREE.Mesh(new THREE.BoxGeometry(s, s, s), sparkMat[(rnd() * 3) | 0]);
  const a = rnd() * Math.PI * 2, r = 1.5 + Math.pow(rnd(), 1.4) * 11;
  m.position.set(CLASH.x + Math.cos(a) * r, CLASH.y + Math.sin(a) * r * 0.85, CLASH.z + (rnd() - 0.5) * 6);
  m.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3);
  sparks.add(m);
}
for (const [dx, dy, s] of [[0, 0, 2.6], [-3, 0, 1.4], [3, 0, 1.4], [0, 3, 1.4], [0, -3, 1.4]]) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(s, s, s), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  m.position.set(CLASH.x + dx, CLASH.y + dy, CLASH.z + 1); m.rotation.z = Math.PI / 4; sparks.add(m);
}

// ---- lights ----
scene.add(new THREE.AmbientLight(0xc8b8b0, 1.35));
const key = new THREE.DirectionalLight(0xfff2e6, 2.0); key.position.set(-24, 130, 70); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, { left: -90, right: 60, top: 70, bottom: -20, near: 1, far: 400 });
scene.add(key);
const rim = new THREE.DirectionalLight(0xff5a3a, 1.2); rim.position.set(70, 50, -70); scene.add(rim);
const lava = new THREE.DirectionalLight(0xff8a3a, 0.35); lava.position.set(0, -60, 60); scene.add(lava);
const clashLight = new THREE.PointLight(0xffc070, 420, 90, 2); clashLight.position.copy(CLASH).add(new THREE.Vector3(0, 0, 8)); scene.add(clashLight);
const torchLight = new THREE.PointLight(0xff9a3a, 500, 70, 2); scene.add(torchLight);
scene.updateMatrixWorld(true); { const w = new THREE.Vector3(); E.R.holder.getWorldPosition(w); torchLight.position.copy(w).add(new THREE.Vector3(0, 10, 10)); }

// ground shadow catcher
const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 200), new THREE.ShadowMaterial({ opacity: 0.38 }));
ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);

// ---- subject selection + camera ----
const only = q.get('only') || 'all';
if (only === 'duel') { E.group.visible = false; torchLight.visible = false; }
if (only === 'explorer') { A.group.visible = false; B.group.visible = false; clashLight.visible = false; sparks.visible = false; }
if (only === 'explorer') {   // bring the explorer to the origin
  E.group.position.set(0, 0, 0); scene.updateMatrixWorld(true);
  const w = new THREE.Vector3(); E.R.holder.getWorldPosition(w); torchLight.position.copy(w).add(new THREE.Vector3(0, 10, 10));
}
const ppu = +q.get('ppu') || 0;
const aspect = W / H;
let cam;
if (ppu) {   // near-orthographic: far camera, narrow fov, exact pixels per unit at the subject
  const d = 600, fov = 2 * Math.atan(H / (2 * ppu * d)) * 180 / Math.PI;
  cam = new THREE.PerspectiveCamera(fov, aspect, 1, 2000);
  const ty = +q.get('ty') || 22, tx = +q.get('tx') || 0;
  const el = (+q.get('el') || 8) * Math.PI / 180;
  cam.position.set(tx, ty + d * Math.sin(el), d * Math.cos(el)); cam.lookAt(tx, ty, 0);
} else {
  cam = new THREE.PerspectiveCamera(+q.get('fov') || 26, aspect, 1, 1000);
  cam.position.set(+q.get('cx') || -8, +q.get('cy') || 26, +q.get('cz') || 190);
  cam.lookAt(+q.get('tx') || -22, 20, 0);
}
renderer.render(scene, cam);
window.__done = true;
