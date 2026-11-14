// Checks a TopG server page in headless Chromium: which banner file it shows, the HTTP status of that file,
// and whether the banner actually changes on screen (animated) over ~5 s.
//   node tools/topg-live-check.mjs 688395 [out.png]
import { createRequire } from 'module'; import { execSync } from 'child_process';
const require = createRequire(import.meta.url);
const { chromium } = require(execSync('npm root -g').toString().trim() + '/playwright');
import fs from 'fs'; import crypto from 'crypto';
const id = process.argv[2], out = process.argv[3];
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1200, height: 900 } });
const resp = []; p.on('response', r => { if (/uploads\/banners|premium\//.test(r.url())) resp.push(r.status() + ' ' + r.url()); });
await p.goto(`https://topg.org/minecraft-servers/server-${id}`, { waitUntil: 'networkidle', timeout: 60000 });
const el = await p.$('.srv-banner');
if (!el) { console.log('no banner on page'); await b.close(); process.exit(1); }
const info = await el.evaluate(e => { const m = e.querySelector('img,video'); return { tag: m.tagName, src: m.currentSrc || m.src, w: m.naturalWidth || m.videoWidth, h: m.naturalHeight || m.videoHeight }; });
const hs = [];
for (let k = 0; k < 6; k++) { const s = await el.screenshot(); if (k === 2 && out) fs.writeFileSync(out, s); hs.push(crypto.createHash('md5').update(s).digest('hex').slice(0, 8)); await p.waitForTimeout(900); }
console.log(JSON.stringify(info)); console.log(resp.join('\n'));
console.log('distinct on-screen frames over ~5 s:', new Set(hs).size, '(1 = still or black, >1 = animating)');
await b.close();
