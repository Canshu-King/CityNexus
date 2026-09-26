/* Closing the two questions my previous pass left open on b6a8ea5c: where the server's receipt actually lands,
and whether the device really keeps a copy behind an 「已保存」 style claim.

Why a new file and not a re-run of the last one: two of my own instrument gaps produced those open questions, and
each has a mechanical signal written here rather than smoothed over -
  * the rejection screen's 归因详情 fold was read as *text* only, so a receipt that the client puts in a
    `data-cnx-receipt` / `data-cnx-field` anchor would have scored as "no receipt on screen". The served bundle
    proves such anchors exist (`error_receipt_id`, a `^CNX-…{8}$` matcher and a literal `NOT-EMITTED` fallback),
    so this pass dumps those attributes by name instead of guessing from text;
  * the previous device-store probe resolved its promise without ever attaching the row counts it had collected,
    so `citynexus-offline` reported store names and a null row map. The counting is redone here, together with
    the cache entry counts and whether each leg was served by the service worker.

What is published stays inside the exposure gate: attribute NAMES, the receipt identifier (which the product
exists to show), byte counts, statuses and hashes of longer strings - never a server sentence, never a raw body.

Lane: own headless Chromium, 390x844@3, touch, zh-CN, one fresh context per case, no proxy. Password read from the
named file, used as httpCredentials only.
Usage: node r6_receipt_anchor_offline.cjs <outDir> <real-journey-id>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_b6a8_0926');
const REAL_ID = process.argv[3] || null;
const BASE = 'https://administrator-personality-supervisor-peers.trycloudflare.com';
const DEAD = '00000000-0000-0000-0000-000000000000';
const AUTH = fs.readFileSync('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt', 'utf8').trim().split(/\s+/);
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

const ANCHORS = async () => {
  const digest = async (t) => {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(t));
    return Array.from(new Uint8Array(buf)).map((x) => x.toString(16).padStart(2, '0')).join('');
  };
  const sel = '[data-cnx-field],[data-cnx-receipt],[data-testid],[aria-live],[role=alert]';
  const rows = [];
  for (const n of document.querySelectorAll(sel)) {
    const t = (n.innerText || '').trim();
    rows.push({ tag: n.tagName.toLowerCase(), testid: n.getAttribute('data-testid'),
                cnx_field: n.getAttribute('data-cnx-field'), cnx_receipt: n.getAttribute('data-cnx-receipt'),
                aria_live: n.getAttribute('aria-live'), role: n.getAttribute('role'),
                visible: !!(n.offsetParent || n.getClientRects().length),
                text_len: t.length, text_sha256: t ? await digest(t) : null,
                text_head: t.length ? t.slice(0, 40) : null,
                open: n.tagName.toLowerCase() === 'details' ? n.open : null });
  }
  const body = document.body.innerText || '';
  return { anchors: rows, receipts_in_text: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
           not_emitted_word_in_text: /NOT-EMITTED/.test(body),
           body_text_len: body.length,
           details_count: document.querySelectorAll('details').length,
           sw_controller: !!navigator.serviceWorker.controller };
};

const DEVICE_STORES = () => new Promise((resolve) => {
  const out = { databases: null, target_db: null, store_names: [], rows: {}, caches_keys: null,
                cache_entry_counts: {}, errors: [] };
  indexedDB.databases().then((dbs) => {
    out.databases = dbs.map((d) => ({ name: d.name, version: d.version }));
    const target = dbs.map((d) => d.name).find((n) => /offline/i.test(n)) || null;
    out.target_db = target;
    if (!target) return finish(out);
    const req = indexedDB.open(target);
    req.onerror = () => { out.errors.push('open refused'); finish(out); };
    req.onupgradeneeded = () => { out.errors.push('upgrade_needed_on_read'); };
    req.onsuccess = () => {
      const db = req.result;
      out.store_names = Array.from(db.objectStoreNames || []);
      if (!out.store_names.length) return finish(out);
      let pending = out.store_names.length;
      out.store_names.forEach((s) => {
        try {
          const c = db.transaction(s, 'readonly').objectStore(s).count();
          c.onsuccess = () => { out.rows[s] = c.result; if (!--pending) finish(out); };
          c.onerror = () => { out.rows[s] = 'COUNT_FAILED'; if (!--pending) finish(out); };
        } catch (e) { out.rows[s] = 'TX_FAILED'; if (!--pending) finish(out); }
      });
    };
  }).catch((e) => { out.errors.push(String(e.message || e).slice(0, 90)); finish(out); });
  function finish(o) {
    o.rows_attached = Object.keys(o.rows).length > 0 || o.target_db === null;
    if (!window.caches) { o.caches_keys = 'NO_CACHES_API'; return resolve(o); }
    caches.keys().then((ks) => {
      o.caches_keys = ks;
      let left = ks.length;
      if (!left) return resolve(o);
      ks.forEach((k) => caches.open(k).then((c) => c.keys()).then((list) => {
        o.cache_entry_counts[k] = list.length; if (!--left) resolve(o);
      }).catch(() => { o.cache_entry_counts[k] = 'KEYS_FAILED'; if (!--left) resolve(o); }));
    }).catch((e) => { o.caches_keys = 'KEYS_FAILED'; resolve(o); });
  }
});

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

async function newPage(browser, seedId, legs) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  await ctx.addInitScript(([id]) => {
    if (id) localStorage.setItem('citynexus.v8.journey_id', id);
    else Object.keys(localStorage).filter((k) => /citynexus/.test(k)).forEach((k) => localStorage.removeItem(k));
  }, [seedId]);
  const page = await ctx.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let b = null;
    try { b = await r.body(); } catch (e) { b = null; }
    const ct = r.headers()['content-type'] || null;
    const leg = { url: r.url().replace(/^https?:\/\/[^/]+/, ''), m: r.request().method(), status: r.status(),
                  content_type_on_the_page_side: ct, resp_bytes: b === null ? 'READ_FAILED' : b.length,
                  from_service_worker: r.fromServiceWorker() };
    if (b && /json/.test(ct || '') || (b && b.length && b[0] === 0x7b)) {
      try { const j = JSON.parse(Buffer.from(b).toString('utf8'));
            leg.server_receipt_id = (j.error && j.error.error_receipt_id) || j.error_receipt_id || null;
            leg.server_code = (j.error && j.error.code) || j.code || null; } catch (e) { leg.parse = 'NOT_JSON'; }
    }
    legs.push(leg);
  });
  return { ctx, page };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, dead_id: DEAD, real_id: REAL_ID, clicks: 0 };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();

  let legs = [];
  let { ctx, page } = await newPage(browser, DEAD, legs);
  await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(9000);
  out.dead_closed = await page.evaluate(ANCHORS);
  out.shot_dead_closed = await shot(page, 'F1_dead_closed');
  await page.evaluate(() => { document.querySelectorAll('details').forEach((d) => { d.open = true; }); });
  await page.waitForTimeout(600);
  out.dead_opened = await page.evaluate(ANCHORS);
  out.shot_dead_opened = await shot(page, 'F2_dead_opened');
  out.dead_legs = legs.slice();
  out.dead_ls_after = await page.evaluate(() => ({ journey_id: localStorage.getItem('citynexus.v8.journey_id'),
                                                   keys: Object.keys(localStorage) }));
  await ctx.close();

  if (REAL_ID) {
    legs = [];
    const r2 = await newPage(browser, REAL_ID, legs);
    page = r2.page; ctx = r2.ctx;
    await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
    await page.waitForTimeout(14000);
    out.real_settled = await page.evaluate(ANCHORS);
    out.real_device_stores = await page.evaluate(DEVICE_STORES);
    out.shot_real = await shot(page, 'F3_real_journey');
    /* walk the affordances that could carry a durability sentence, reading text length and hash per stop */
    const stops = [];
    for (const label of ['旅行票夹', '恢复与执行', '我的', '行程工作台']) {
      const b = page.getByRole('button', { name: label, exact: false }).first();
      const had = await b.count();
      if (!had) { stops.push({ label, affordance_present: false }); continue; }
      await b.click({ timeout: 4000 }).catch(() => {});
      out.clicks += 1;
      await page.waitForTimeout(2200);
      const s = await page.evaluate(ANCHORS);
      const saved = await page.evaluate(() => (document.body.innerText || '').match(/[^\n]*已保存[^\n]*/g) || []);
      stops.push({ label, affordance_present: true, body_text_len: s.body_text_len,
                   body_text_len_here: s.body_text_len, saved_sentences: saved.map((x) => x.slice(0, 60)),
                   details_count: s.details_count, receipts_in_text: s.receipts_in_text });
    }
    out.real_saved_scan = stops;
    out.real_device_stores_after_walk = await page.evaluate(DEVICE_STORES);
    out.real_legs = legs.slice();
    out.shot_real_walked = await shot(page, 'F4_after_tab_walk');
    await ctx.close();
  }
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r6_receipt_anchor_offline.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ dead_closed_anchors: out.dead_closed.anchors.map((a) => [a.testid, a.cnx_field,
      a.cnx_receipt, a.text_len, a.open]),
    dead_opened_anchors: out.dead_opened.anchors.map((a) => [a.testid, a.cnx_field, a.cnx_receipt, a.text_len, a.open]),
    receipts_in_text: [out.dead_closed.receipts_in_text, out.dead_opened.receipts_in_text],
    not_emitted_word: [out.dead_closed.not_emitted_word_in_text, out.dead_opened.not_emitted_word_in_text],
    dead_legs: out.dead_legs.map((l) => [l.m, l.url.slice(0, 56), l.status, l.content_type_on_the_page_side,
                                         l.resp_bytes, l.from_service_worker, l.server_receipt_id, l.server_code]),
    real_stores: out.real_device_stores, real_saved: (out.real_saved_scan || []).map((s) => [s.label, s.saved_sentences]) },
    null, 1));
  await browser.close();
})().catch((e) => { console.error('F FAILED: ' + String((e && e.message) || e)); process.exit(9); });
