/* ORD-0300 cross-check: the same tap with NO instrument at all - no fetch wrapper, no localStorage hook.
   If the card is identical, the "server answered 500 / screen says unreachable" reading is the product's,
   not something my wrapper caused. */
const { chromium } = require('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend/node_modules/playwright');
const fs = require('fs');

const OUT = 'D:/moodle/_hjp3_0300_0925';
const state = JSON.parse(fs.readFileSync(OUT + '/o0300_state.json', 'utf-8'));
const JOURNEY = state.seed.journey_id;
const TEXT = '想傍晚在老城慢慢走一圈，别太赶';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:' + state.face.port + '/', { waitUntil: 'load', timeout: 60000 });
  await page.evaluate((j) => localStorage.setItem('citynexus.v8.journey_id', j), JOURNEY);
  await page.reload({ waitUntil: 'load' });
  const hub = page.locator('[data-testid="hub-plan-with-ai"]');
  await hub.waitFor({ state: 'visible', timeout: 25000 });
  await hub.click();
  await page.locator('[data-testid="plan-ai-input"]').waitFor({ state: 'visible', timeout: 15000 });
  await page.locator('[data-testid="plan-ai-input"]').fill(TEXT);
  fs.writeFileSync(OUT + '/sheet_ready.flag', String(Date.now()));
  while (!fs.existsSync(OUT + '/lock_armed.flag')) await sleep(200);
  const t0 = Date.now();
  await page.locator('[data-testid="plan-ai-submit"]').click();
  let card = null;
  while (Date.now() - t0 < 60000) {
    const s = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="plan-ai-result"]');
      return { text: el ? el.innerText : null, status: el ? el.getAttribute('data-result-status') : null,
               details: document.querySelectorAll('details').length,
               counter: (function () { const l = document.querySelector('[data-testid="plan-ai-elapsed"]');
                                        return l ? l.innerText : null; })() };
    });
    if (s.text) { card = Object.assign({ ms: Date.now() - t0 }, s); break; }
    await sleep(300);
  }
  await sleep(3000);
  const after = await page.evaluate(() => {
    const el = document.querySelector('[data-testid="plan-ai-result"]');
    return { text: el ? el.innerText : null, status: el ? el.getAttribute('data-result-status') : null,
             details: document.querySelectorAll('details').length };
  });
  await page.screenshot({ path: OUT + '/shots_O0300-plaincard-end.png' });
  const out = { ran_at: new Date().toISOString(), port: state.face.port, measured_on: state.measured_on,
                bundle_sha256: state.face.served_sha256, instrumented: false, first_card: card, card_after_3s: after };
  fs.writeFileSync(OUT + '/cell_plain_w2.json', JSON.stringify(out, null, 1), 'utf-8');
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})();
