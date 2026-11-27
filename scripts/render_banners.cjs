// Render banners_bmtm/*.html to print PNGs (3435 x 4122 px, 25 x 30 cm at ~350 dpi).
(async () => {
//   node scripts/render_banners.cjs [filter]
const { chromium } = require('playwright');
const { readdirSync, mkdirSync } = require('fs');
const { join } = require('path');

const dir = 'banners_bmtm', out = join(dir, 'png');
mkdirSync(out, { recursive: true });
const filter = process.argv[2] || '';
const files = readdirSync(dir).filter(f => f.endsWith('.html') && f.includes(filter)).sort();
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 1080 }, deviceScaleFactor: 3435 / 900 });
for (const f of files) {
  await page.goto('file://' + join(process.cwd(), dir, f));
  await page.waitForSelector('body[data-ready="1"]', { timeout: 20000 });
  await page.screenshot({ path: join(out, f.replace('.html', '.png')) });
  console.log('rendered', f);
}
await browser.close();
})();
