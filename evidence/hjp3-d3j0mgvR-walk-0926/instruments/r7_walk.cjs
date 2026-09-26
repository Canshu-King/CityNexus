/* One Chromium lane, four fresh contexts, on the newest phone bundle (the copy-link acceptance is the point).

Why four contexts inside ONE browser launch: the commander warned again about the tile channel - repeated launches
degrade it and contaminate every later basemap reading on this lane - so the launch happens once and isolation comes
from a new context per cell. That is also the lesson from my own last confounded reading, where the wizard draft
rode along into a different URL.

Cells:
  A  walk the three-step wizard and press 确认创建, then find the ORD-0357 affordance that copies the journey's own
     link, click it, and read the clipboard back inside the page (nothing is pasted anywhere else)
  B  a brand-new context that only navigates to that copied link - does the traveller land on the same screen the
     copy came from? The comparison is a hash of the rendered text plus the visible button list, not my memory
  C  a brand-new context whose stored journey id the server does not know, reading the rejection copy verbatim
     (the item the commander re-listed first)
  D  a brand-new context seeded with the real journey id, then the device is counted: IndexedDB databases, the row
     count of every store in the offline database, cache keys and their entry counts, whether a sentence containing
     「已保存」 renders anywhere across the tabs I can reach

Readings only. No product byte is touched; nothing here repairs what it sees. The tunnel password is read from the
file the commander named and used as httpCredentials only - it is never printed and never written to an artefact.
Usage: node r7_walk.cjs <outDir>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_d3j0_0926');
const BASE = 'https://jets-saints-tomatoes-eric.trycloudflare.com';
const AUTH = fs.readFileSync('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt', 'utf8').trim().split(/\s+/);
const DEAD = '00000000-0000-0000-0000-000000000000';
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

const SNAP = () => {
  const body = document.body ? (document.body.innerText || '') : '';
  const ex = /Traceback|Exception|\bError\b|TypeError|RangeError|undefined is not|cannot read propert/i;
  const hits = [];
  for (const n of document.querySelectorAll('*')) {
    for (const a of Array.from(n.attributes || [])) {
      if (['style', 'src', 'href', 'd', 'class'].includes(a.name)) continue;
      if (a.value && ex.test(String(a.value))) hits.push({ tag: n.tagName.toLowerCase(), attr: a.name,
                                                           value_len: String(a.value).length });
    }
  }
  return {
    url: location.href, text_len: body.length, text: body.slice(0, 2400),
    buttons: Array.from(document.querySelectorAll('button')).map((b) => ({
      text: (b.innerText || '').trim().slice(0, 40), disabled: !!b.disabled,
      top: Math.round(b.getBoundingClientRect().top), testid: b.getAttribute('data-testid'),
      cls: String(b.className).slice(0, 34) })),
    saved_sentences: body.match(/[^\n]*已保存[^\n]*/g) || [],
    claims_offline: /网络不可用|无法连接|离线|请检查网络/.test(body),
    names_404: /404|不存在|没找到|找不到|已被删除|无此行程/.test(body),
    denies_network: /不是网络|这不是网络问题|并非网络/.test(body),
    pending: /正在创建|正在载入|已等待/.test(body),
    receipts: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
    exception_in_text: ex.test(body), attr_hits: hits,
    details_count: document.querySelectorAll('details').length,
    details: Array.from(document.querySelectorAll('details')).map((d) => ({
      open: d.open, summary: ((d.querySelector('summary') || {}).innerText || '').trim().slice(0, 40),
      inner_len: (d.innerText || '').length })),
    aria_live: Array.from(document.querySelectorAll('[aria-live]')).map((n) => ({
      level: n.getAttribute('aria-live'), text: (n.innerText || '').trim().slice(0, 300) })),
    ls: Object.keys(localStorage).map((k) => ({ key: k, len: (localStorage.getItem(k) || '').length })),
    sw_controller: !!navigator.serviceWorker.controller,
    inputs_placeholder: Array.from(document.querySelectorAll('input')).map((i) => i.placeholder).filter(Boolean),
    copy_affordances: Array.from(document.querySelectorAll('button,[role=button],a'))
      .filter((n) => /复制|copy/i.test((n.innerText || '') + ' ' + (n.getAttribute('aria-label') || '')
                                       + ' ' + (n.getAttribute('data-testid') || '')))
      .map((n) => ({ tag: n.tagName.toLowerCase(), text: (n.innerText || '').trim().slice(0, 40),
                     testid: n.getAttribute('data-testid'), aria: n.getAttribute('aria-label'),
                     href: n.getAttribute('href') })),
  };
};

const DEVICE = () => new Promise((resolve) => {
  const out = { databases: null, target_db: null, store_names: [], rows: {}, caches_keys: null,
                cache_entry_counts: {}, errors: [] };
  indexedDB.databases().then((dbs) => {
    out.databases = dbs.map((d) => ({ name: d.name, version: d.version }));
    const t = dbs.map((d) => d.name).find((n) => /offline/i.test(n)) || null;
    out.target_db = t;
    if (!t) return finish(out);
    const req = indexedDB.open(t);
    req.onerror = () => { out.errors.push('open refused'); finish(out); };
    req.onsuccess = () => {
      const db = req.result;
      out.store_names = Array.from(db.objectStoreNames || []);
      if (!out.store_names.length) return finish(out);
      let left = out.store_names.length;
      out.rows = {};
      out.store_names.forEach((s) => {
        try {
          const c = db.transaction(s, 'readonly').objectStore(s).count();
          c.onsuccess = () => { out.rows[s] = c.result; if (!--left) finish(out); };
          c.onerror = () => { out.rows[s] = 'COUNT_FAILED'; if (!--left) finish(out); };
        } catch (e) { out.rows[s] = 'TX_FAILED'; if (!--left) finish(out); }
      });
    };
  }).catch((e) => { out.errors.push(String(e.message || e).slice(0, 80)); finish(out); });
  function finish(o) {
    if (o.store_names.length && Object.keys(o.rows).length === 0) o.rows = 'NOT_COUNTED';
    if (!window.caches) { o.caches_keys = 'NO_CACHES_API'; return resolve(o); }
    caches.keys().then((ks) => {
      o.caches_keys = ks; let left = ks.length;
      if (!left) return resolve(o);
      ks.forEach((k) => caches.open(k).then((c) => c.keys()).then((list) => {
        o.cache_entry_counts[k] = list.length; if (!--left) resolve(o);
      }).catch(() => { o.cache_entry_counts[k] = 'KEYS_FAILED'; if (!--left) resolve(o); }));
    }).catch(() => { o.caches_keys = 'KEYS_FAILED'; resolve(o); });
  }
});

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

async function newCtx(browser, seed) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         permissions: ['clipboard-read', 'clipboard-write'],
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  await ctx.addInitScript(([id]) => {
    if (id) localStorage.setItem('citynexus.v8.journey_id', id);
    else Object.keys(localStorage).filter((k) => /citynexus/.test(k)).forEach((k) => localStorage.removeItem(k));
  }, [seed]);
  const legs = [];
  const page = await ctx.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let rb = null, receipt = null, code = null;
    try {
      const b = await r.body(); rb = b.length;
      if (r.status() >= 400) {
        try { const j = JSON.parse(Buffer.from(b).toString('utf8'));
              receipt = (j.error && j.error.error_receipt_id) || j.error_receipt_id || null;
              code = (j.error && j.error.code) || j.code || null; } catch (e) { receipt = 'NOT_JSON'; }
      }
    } catch (e) { rb = rb === null ? 'READ_FAILED' : rb; }
    legs.push({ at: new Date().toISOString(), url: r.url().replace(/^https?:\/\/[^/]+/, ''),
                m: r.request().method(), status: r.status(), ct: r.headers()['content-type'] || null,
                req_bytes: (r.request().postData() || '').length, resp_bytes: rb,
                from_service_worker: r.fromServiceWorker(), server_receipt_id: receipt, server_code: code });
  });
  page.on('requestfailed', (rq) => {
    if (rq.url().indexOf('/api/') < 0) return;
    legs.push({ url: rq.url().replace(/^https?:\/\/[^/]+/, ''), m: rq.method(), status: null,
                failure: (rq.failure() && rq.failure().errorText) || 'failed' });
  });
  return { ctx, page, legs };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, viewport: { width: 390, height: 844 },
                launches: 1, contexts: 4, cells: {} };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();

  /* A: create a journey, then use ORD-0357 to copy its own link */
  const a = await newCtx(browser, null);
  await a.page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await a.page.waitForTimeout(2500);
  out.served_asset = await a.page.evaluate(() => (document.querySelector('script[src*="assets/index-"]') || {}).src || null);
  await a.page.locator('input[placeholder^="例如"]').first().fill('天津');
  const places = a.page.locator('input[placeholder*="站"], input[placeholder*="机场"], input[placeholder*="地点"]');
  for (let i = 0; i < await places.count(); i++) await places.nth(i).fill(i ? '天津滨海国际机场' : '天津站').catch(() => {});
  const dts = a.page.locator('input[type="datetime-local"]');
  for (let i = 0; i < await dts.count(); i++) await dts.nth(i).fill(i ? '2026-10-03T20:00' : '2026-10-02T10:00');
  const adv = a.page.getByRole('button', { name: '高级设置', exact: false }).first();
  if (await adv.count()) await adv.click({ timeout: 3000 }).catch(() => {});
  const nums = a.page.locator('input[type="number"], input[inputmode="numeric"]');
  const num_count = await nums.count();
  for (let i = 0; i < num_count; i++) await nums.nth(i).fill(i ? '1000' : '3000').catch(() => {});
  out.budget_fields_before_typing = num_count;
  out.advance = [];
  for (const i of [1, 2]) {
    const before = await a.page.evaluate(() => (document.body.innerText || '').length);
    const r = await a.page.getByRole('button', { name: '下一步', exact: true }).first()
      .click({ timeout: 6000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 60));
    await a.page.waitForTimeout(1500);
    const after = await a.page.evaluate(() => (document.body.innerText || '').length);
    out.advance.push({ press: r, before, after, changed: before !== after });
  }
  out.cells.A_review = await a.page.evaluate(SNAP);
  out.shots = { A_review: await shot(a.page, 'A1_review') };
  const lb = a.legs.length;
  await a.page.getByRole('button', { name: '确认创建', exact: true }).first().click({ timeout: 6000 })
    .then(() => { out.cells.A_press = 'clicked'; }).catch((e) => { out.cells.A_press = 'click_failed: ' + e.message.slice(0, 60); });
  await a.page.waitForTimeout(16000);
  out.cells.A_after = await a.page.evaluate(SNAP);
  out.cells.A_legs = a.legs.slice(lb);
  out.cells.A_stored_id = await a.page.evaluate(() => localStorage.getItem('citynexus.v8.journey_id'));
  out.shots.A_after = await shot(a.page, 'A2_after_confirm');
  /* the copy affordance: look for anything that mentions 复制 on whatever screen we are on */
  let copy = out.cells.A_after.copy_affordances;
  if (!copy.length) {
    for (const label of ['我的', '行程工作台', '旅行票夹', '恢复与执行']) {
      const b = a.page.getByRole('button', { name: label, exact: false }).first();
      if (!await b.count()) continue;
      await b.click({ timeout: 4000 }).catch(() => {});
      await a.page.waitForTimeout(2000);
      const s = await a.page.evaluate(SNAP);
      if (s.copy_affordances.length) {
        copy = s.copy_affordances;
        out.cells.A_copy_found_on_tab = { label, snapshot_text_len: s.text_len, buttons: s.buttons.map((x) => x.text) };
        break;
      }
    }
  }
  out.cells.A_copy_affordances = copy;
  out.shots.A_copy = await shot(a.page, 'A3_copy_affordance');
  out.cells.A_clipboard = 'NOT_READ';
  if (copy.length) {
    const btn = a.page.locator('[data-testid*="copy"], button:has-text("复制"), [role=button]:has-text("复制")').first();
    out.cells.A_copy_press = await btn.click({ timeout: 5000 }).then(() => 'clicked')
      .catch((e) => 'click_failed: ' + String(e.message).slice(0, 60));
    await a.page.waitForTimeout(1500);
    out.cells.A_clipboard = await a.page.evaluate(() => navigator.clipboard.readText().catch((e) => 'READ_FAILED: ' + e.name));
    out.cells.A_toast_lines = (await a.page.evaluate(() => (document.body.innerText || '').match(/[^\n]*(复制|链接|剪贴)[^\n]*/g)) || []);
    out.shots.A_copied = await shot(a.page, 'A4_after_copy');
  }
  const jid = out.cells.A_stored_id;
  await a.ctx.close();

  /* B: a brand-new context that only opens the copied link */
  const link = typeof out.cells.A_clipboard === 'string' && /^https?:\/\//.test(out.cells.A_clipboard)
    ? out.cells.A_clipboard : null;
  if (link) {
    const b = await newCtx(browser, null);
    await b.page.goto(link, { waitUntil: 'load', timeout: 90000 });
    await b.page.waitForTimeout(14000);
    out.cells.B_reopen = await b.page.evaluate(SNAP);
    out.cells.B_legs = b.legs.slice();
    out.cells.B_ls_after = await b.page.evaluate(() => ({ journey_id: localStorage.getItem('citynexus.v8.journey_id'),
                                                          keys: Object.keys(localStorage) }));
    out.shots.B_reopen = await shot(b.page, 'B1_reopened_link');
    const aText = (out.cells.A_after.text || '');
    const bText = out.cells.B_reopen.text || '';
    out.cells.B_same_screen_as_the_copy_came_from = {
      a_text_len: aText.length, b_text_len: bText.length,
      a_text_sha: SHA(aText), b_text_sha: SHA(bText), identical_prefix_2000: aText.slice(0, 2000) === bText.slice(0, 2000),
      a_buttons: out.cells.A_after.buttons.map((x) => x.text), b_buttons: out.cells.B_reopen.buttons.map((x) => x.text),
      b_url: out.cells.B_reopen.url };
    await b.ctx.close();
  } else {
    out.cells.B_reopen = 'SKIPPED - no link came back from the clipboard';
  }

  /* C: a stored id the server does not know */
  const c = await newCtx(browser, DEAD);
  await c.page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await c.page.waitForTimeout(9000);
  out.cells.C_closed = await c.page.evaluate(SNAP);
  out.shots.C_closed = await shot(c.page, 'C1_dead_id_closed');
  await c.page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
  await c.page.waitForTimeout(700);
  out.cells.C_open = await c.page.evaluate(SNAP);
  out.shots.C_open = await shot(c.page, 'C2_dead_id_open');
  out.cells.C_ls_after = await c.page.evaluate(() => ({ journey_id: localStorage.getItem('citynexus.v8.journey_id'),
                                                        keys: Object.keys(localStorage) }));
  out.cells.C_legs = c.legs.slice();
  await c.ctx.close();

  /* D: the real journey boot, then count the device */
  if (jid) {
    const d = await newCtx(browser, jid);
    await d.page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
    const t0 = Date.now();
    await d.page.waitForTimeout(12000);
    out.cells.D_boot_ms_first_read = Date.now() - t0;
    out.cells.D_hub = await d.page.evaluate(SNAP);
    out.cells.D_device = await d.page.evaluate(DEVICE);
    out.shots.D_hub = await shot(d.page, 'D1_real_journey_hub');
    const tab_scan = [];
    for (const label of ['我的', '旅行票夹', '恢复与执行', '行程工作台']) {
      const b = d.page.getByRole('button', { name: label, exact: false }).first();
      if (!await b.count()) { tab_scan.push({ label, affordance_present: false }); continue; }
      await b.click({ timeout: 4000 }).catch(() => {});
      await d.page.waitForTimeout(2200);
      const s = await d.page.evaluate(SNAP);
      tab_scan.push({ label, affordance_present: true, text_len: s.text_len, saved_sentences: s.saved_sentences,
                      details_count: s.details_count, receipts: s.receipts, copy_affordances: s.copy_affordances });
    }
    out.cells.D_tab_scan = tab_scan;
    out.cells.D_device_after_walk = await d.page.evaluate(DEVICE);
    out.cells.D_legs = d.legs.slice();
    out.shots.D_walked = await shot(d.page, 'D2_after_tab_walk');
    await d.ctx.close();
  }

  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r7_walk.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ served_asset: out.served_asset, press: out.cells.A_press,
    stored_id: out.cells.A_stored_id ? out.cells.A_stored_id.slice(0, 8) : null,
    clipboard: typeof out.cells.A_clipboard === 'string' ? out.cells.A_clipboard.slice(0, 120) : out.cells.A_clipboard,
    copy_affordances: out.cells.A_copy_affordances,
    C_head: (out.cells.C_closed.text || '').slice(0, 400),
    C_receipts_closed: out.cells.C_closed.receipts, C_receipts_open: out.cells.C_open.receipts,
    D_device: out.cells.D_device, D_saved: (out.cells.D_tab_scan || []).map((x) => [x.label, x.saved_sentences]) },
    null, 1));
  await browser.close();
})().catch((e) => { console.error('R7 FAILED: ' + String((e && e.message) || e)); process.exit(9); });
