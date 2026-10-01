/* ORD-0391 screen read-back pass 2 - the two arms pass 1 could not reach.
 *
 * Pass 1 poisoned the read on a cold device, so the copy that depends on "this device holds a read-only
 * copy" never appeared: the app writes that copy during a *healthy* boot (V8Experience refreshes
 * /offline-snapshot into Dexie and sets the flag from the verified read-back). Here the visit is made
 * in the order a traveller makes it: load the trip while the origin answers, confirm the copy row is
 * really on the device, then switch the stub and re-read.
 *
 * The second family is the studio panel's refusal line (LocaleContext's studio.requestRefused), which
 * needs a mutation on that face to be refused rather than a journey read.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const HERE = __dirname;
const BASE = 'http://localhost:4541';
const STUB = 'http://127.0.0.1:7042';
const JOURNEY_ID = '22222222-2222-4222-8222-222222222222';
const VIEWPORT = { width: 390, height: 844 };

const setScenario = (name) => fetch(STUB + '/__scenario', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }),
}).then((r) => r.json());

async function openPage(browser, locale) {
  const ctx = await browser.newContext({
    viewport: VIEWPORT, locale: locale === 'zh' ? 'zh-CN' : 'en-US', deviceScaleFactor: 1,
  });
  const net = [];
  ctx.on('response', (res) => {
    const u = res.url();
    if (u.includes('/api/v1/')) {
      net.push({ p: u.replace(/^https?:\/\/[^/]+/, ''), status: res.status(),
        ct: res.headers()['content-type'] || null });
    }
  });
  const page = await ctx.newPage();
  await page.addInitScript((seed) => {
    localStorage.setItem('citynexus.locale', seed.locale);
    localStorage.setItem('citynexus.v8.journey_id', seed.journeyId);
  }, { locale: locale === 'zh' ? 'zh-CN' : 'en-US', journeyId: JOURNEY_ID });
  return { ctx, page, net };
}

async function readScreen(page) {
  return page.evaluate(() => {
    const txt = (sel) => {
      const el = document.querySelector(sel);
      return el ? (el.textContent || '').trim() : null;
    };
    const nodes = [];
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const t = (n.nodeValue || '').trim();
      if (t.length > 0) nodes.push(t);
    }
    return {
      reason: txt('[data-testid="failure-reason"]'),
      telemetry: txt('[data-testid="failure-attribution-line"]'),
      studioError: txt('[data-testid="v12-request-error"]'),
      bodyChars: (document.body.innerText || '').length,
      textNodes: nodes,
      buttons: Array.from(document.querySelectorAll('button')).slice(0, 40)
        .map((b) => ({ testid: b.getAttribute('data-testid'), label: (b.textContent || '').trim().slice(0, 40),
          disabled: b.disabled === true })),
    };
  });
}

const countOfflineRows = (page) => page.evaluate(() => new Promise((resolve) => {
  const req = indexedDB.open('citynexus-offline', 1);
  req.onerror = () => resolve({ error: 'OPEN_FAILED' });
  req.onsuccess = () => {
    const db = req.result;
    if (!db.objectStoreNames.contains('journeys')) return resolve({ error: 'NO_STORE',
      stores: Array.from(db.objectStoreNames) });
    const c = db.transaction('journeys', 'readonly').objectStore('journeys').count();
    c.onsuccess = () => resolve({ rows: c.result });
    c.onerror = () => resolve({ error: 'COUNT_FAILED' });
  };
}));

async function cachedCopyArm(browser, locale, scenario) {
  const name = 'c2_' + scenario + '_' + locale;
  await setScenario('off');
  const { ctx, page, net } = await openPage(browser, locale);
  await page.goto(BASE + '/v8/hub', { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.waitForTimeout(6000);
  const healthy = await readScreen(page);
  const rows = await countOfflineRows(page);
  /* now make the origin fail the same read, and ask the screen to read it again */
  const spec = await setScenario(scenario);
  const before = net.length;
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 60_000 });
  let view = false;
  try {
    await page.waitForSelector('[data-testid="failure-view"]', { timeout: 15_000 });
    view = true;
  } catch (e) { /* recorded, not assumed */ }
  await page.waitForTimeout(1200);
  const read = await readScreen(page);
  await page.screenshot({ path: path.join(HERE, 'shots', name + '.png') });
  await ctx.close();
  return { name, family: 'cached_copy_failure', scenario, locale, failure_view: view,
    offline_rows_after_healthy_boot: rows, healthy_body_chars: healthy.bodyChars,
    rules_live: (spec.spec.rules || []).length, read,
    journey_calls_after_reload: net.slice(before).filter((x) => x.p.includes('/journeys')).slice(0, 4) };
}

async function studioArm(browser, locale) {
  const name = 'c2_studio_refused_' + locale;
  await setScenario('off');
  const { ctx, page, net } = await openPage(browser, locale);
  await page.goto(BASE + '/v8/hub', { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.waitForTimeout(5000);
  const spec = await setScenario('studio_refused');
  let opened = false, clicked = null, enabled = null, drag = null, panel = null;
  try {
    /* The studio face is a registry panel reached from the drawer, not a route that mounts on its own
       URL for this store, so the nav entry is clicked the way a traveller reaches it. */
    const label = locale === 'zh' ? '行程工作台' : /Trip Studio|Studio/i;
    const nav = page.getByRole('button', { name: label }).first();
    if (await nav.count()) await nav.click({ timeout: 8000 });
    await page.waitForTimeout(3000);
    panel = await page.locator('[data-testid="v12-trip-studio"]').count();
    if (!panel) {
      await page.goto(BASE + '/v8/studio', { waitUntil: 'domcontentloaded', timeout: 60_000 });
      await page.waitForTimeout(3000);
      panel = await page.locator('[data-testid="v12-trip-studio"]').count();
    }
    opened = true;
    const btn = page.locator('[data-testid="v12-preview-impact"]');
    enabled = (await btn.count()) ? await btn.first().isEnabled() : null;
    if (enabled === false) {
      const items = page.locator('[data-testid="v12-trip-studio"] li');
      const n = await items.count();
      if (n >= 2) {
        const a = await items.nth(0).boundingBox();
        const b = await items.nth(1).boundingBox();
        if (a && b) {
          await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
          await page.mouse.down();
          for (let i = 1; i <= 8; i++) {
            await page.mouse.move(a.x + a.width / 2, a.y + (b.y - a.y) * (i / 8) + b.height / 2);
          }
          await page.mouse.up();
          await page.waitForTimeout(1200);
        }
        drag = { items: n, preview_enabled_after_drag: await btn.first().isEnabled() };
        enabled = drag.preview_enabled_after_drag;
      } else {
        drag = { items: n, note: 'no reorderable list items found on this face' };
      }
    }
    if (enabled) {
      await btn.first().click();
      clicked = 'v12-preview-impact';
      await page.waitForTimeout(3500);
    }
  } catch (e) { opened = false; }
  const read = await readScreen(page);
  await page.screenshot({ path: path.join(HERE, 'shots', name + '.png') });
  await setScenario('off');
  await ctx.close();
  return { name, family: 'studio_refusal', locale, route_reached: opened, panel_mounted: panel,
    preview_enabled: enabled, drag, clicked, rules_live: (spec.spec.rules || []).length,
    url: page.url(),
    refused_calls: net.filter((x) => x.status >= 400).slice(0, 8), read };
}

(async () => {
  const browser = await chromium.launch({ timeout: 120_000 });
  const states = [];
  const studioOnly = process.env.CNX_STUDIO_ONLY === '1';
  for (const locale of ['zh', 'en']) {
    if (!studioOnly) {
      for (const scenario of ['server_error', 'html_200', 'empty_200']) {
        states.push(await cachedCopyArm(browser, locale, scenario));
        process.stdout.write('.');
      }
    }
    states.push(await studioArm(browser, locale));
    process.stdout.write('.');
  }
  await browser.close();
  fs.writeFileSync(path.join(HERE, studioOnly ? 'walk_r3.json' : 'walk_r2.json'), JSON.stringify({
    base: BASE, stub: STUB, viewport: VIEWPORT, journey_id: JOURNEY_ID, states_walked: states.length,
    states,
  }, null, 1));
  console.log('\n' + JSON.stringify(states.map((s) => ({
    n: s.name, fv: s.failure_view, rows: s.offline_rows_after_healthy_boot,
    reason: !!((s.read || {}).reason), studio: !!((s.read || {}).studioError),
  }))));
})();
