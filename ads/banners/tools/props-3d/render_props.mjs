import { chromium } from 'playwright-core';
// node render_props.mjs OUTDIR  — renders every prop below as a transparent 600x600 PNG
const OUT = process.argv[2];
const PROPS = {
  grass_block: 'kind=block&side=grass_block_side&top=grass_block_top&bottom=dirt&tint=7fbf5a',
  gold_block: 'kind=block&side=gold_block',
  diamond_block: 'kind=block&side=diamond_block',
  emerald_block: 'kind=block&side=emerald_block',
  tnt: 'kind=block&side=tnt_side&top=tnt_top&bottom=tnt_bottom',
  diamond_sword: 'kind=item&tex=diamond_sword&ry=-0.55',
  netherite_sword: 'kind=item&tex=netherite_sword&ry=-0.55',
  gold_ingot: 'kind=item&tex=gold_ingot&ry=-0.6&rx=0.25',
  diamond: 'kind=item&tex=diamond&ry=-0.55',
  emerald: 'kind=item&tex=emerald&ry=-0.55',
  firework_rocket: 'kind=item&tex=firework_rocket&ry=-0.55',
  nether_star: 'kind=item&tex=nether_star&ry=-0.4',
  golden_apple: 'kind=item&tex=golden_apple&ry=-0.5',
  totem_of_undying: 'kind=item&tex=totem_of_undying&ry=-0.5',
  minex_coin: 'kind=item&tex=minex_coin&ry=-0.35&thick=3.2&half=29.5',
  minex_wordmark: 'kind=item&tex=minex_wordmark&ry=-0.2&rx=0.1&thick=2&half=19',
};
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
const p = await b.newPage({ viewport: { width: 600, height: 600 } });
p.on('pageerror', (e) => console.log('[error]', e.message));
const only = process.argv[3] ? process.argv[3].split(',') : null;
for (const [name, qs] of Object.entries(PROPS)) {
  if (only && !only.includes(name)) continue;
  await p.goto('http://127.0.0.1:8765/props.html?' + qs);
  await p.waitForFunction(() => window.__done === true, null, { timeout: 60000 });
  await p.screenshot({ path: `${OUT}/${name}.png`, omitBackground: true });
  console.log('saved', name);
}
await b.close();
