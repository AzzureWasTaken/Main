import { chromium } from 'playwright-core';
// node render_busts.mjs OUTDIR — every character faces right (toward the banner centre when placed on the left)
const OUT = process.argv[2];
const BUSTS = {
  steve: 'skin=steve.png&pose=rest&turn=30&look=6',
  alex: 'skin=alex.png&slim=1&pose=rest&turn=30&look=4',
  kai: 'skin=kai.png&pose=rest&turn=30&look=-6&tilt=4',
  sunny: 'skin=sunny.png&slim=1&pose=rest&turn=30&look=6&tilt=6',
  makena: 'skin=makena.png&slim=1&pose=rest&turn=28&look=4',
  zuri: 'skin=zuri.png&pose=rest&turn=32&look=4&tilt=-5',
};
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
const p = await b.newPage({ viewport: { width: 600, height: 600 } });
p.on('pageerror', (e) => console.log('[error]', e.message));
for (const [name, qs] of Object.entries(BUSTS)) {
  await p.goto('http://127.0.0.1:8765/bust.html?w=600&h=600&' + qs);
  await p.waitForFunction(() => window.__done === true, null, { timeout: 60000 });
  await p.screenshot({ path: `${OUT}/${name}.png`, omitBackground: true });
  console.log('saved', name);
}
await b.close();
