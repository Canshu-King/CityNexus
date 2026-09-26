/* Cells C, D and E on b6a8ea5c: a stored journey id the server does not know, the same screen with its folds
opened, and what the device actually holds behind a 「已保存」 sentence.

Why one file: all three are the same boot seen from different devices states, and each needs a FRESH context -
the last thing I measured on this chain was a screen that only looked different because my own wizard draft rode
along in the same profile.

  C  `citynexus.v8.journey_id` set to an id the server has never heard of, then the page loads the way a user's
     phone would. Question asked of the screen: does it still say 「网络不可用 · 正在显示只读的已保存行程。」 for a
     404, and does a SERVER-issued `CNX-…` receipt reach the visible text, or only the inside of a fold? The
     receipt is paired with the same leg the browser recorded, not a replay.
  D  the same screen again with every `<details>` opened, so a sentence that hides in the fold is read rather
     than assumed absent, and both states are photographed.
  E  the durability claim measured on the device: the databases IndexedDB reports, the row count of every store
     in the offline database, whether a service worker controls the page, and what `caches.keys()` returns.

Also carried in the same launch: the journey my wizard pass really created, so a real boot into a real journey is
timed rather than described.

Lane: own headless Chromium, 390x844@3, touch, zh-CN, one fresh context per case, no proxy. The tunnel password is
read from the file the commander named and passed as httpCredentials only.
Usage: node r6_dead_id_saved.cjs <outDir> <real-journey-id>
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

const READ = () => {
  const ex = /Traceback|Exception|\bError\b|TypeError|RangeError|undefined is not|cannot read propert/i;
  const body = document.body ? (document.body.innerText || '') : '';
  const hits = [];
  for (const n of document.querySelectorAll('*')) {
    for (const a of Array.from(n.attributes || [])) {
      if (['style', 'src', 'href', 'd', 'class'].includes(a.name)) continue;
      if (a.value && ex.test(String(a.value))) hits.push({ tag: n.tagName.toLowerCase(), attr: a.name,
                                                           value_len: String(a.value).length,
                                                           raw_for_node_side_hashing: String(a.value) });
    }
  }
  return {
    url: location.href, text_len: body.length, text: body.slice(0, 2600),
    receipts_on_screen: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
    claims_offline: /网络不可用|无法连接|离线|请检查网络/.test(body),
    claims_saved_shown: /已保存/.test(body),
    names_not_found: /不存在|没找到|找不到|已被删除|无此行程/.test(body),
    denies_network_reading: /不是网络|并非网络|这不是网络问题/.test(body),
    pending_words: /正在载入|正在创建|已等待|载入中/.test(body),
    buttons: Array.from(document.querySelectorAll('button')).map((b) => ({ text: (b.innerText || '').trim().slice(0, 34),
      disabled: !!b.disabled, top: Math.round(b.getBoundingClientRect().top), cls: String(b.className).slice(0, 34) })),
    links: Array.from(document.querySelectorAll('a')).map((a) => ({ text: (a.innerText || '').trim().slice(0, 24),
      href: a.getAttribute('href') })).filter((x) => x.text),
    details_count: document.querySelectorAll('details').length,
    details: Array.from(document.querySelectorAll('details')).map((d) => ({ open: d.open,
      summary: (d.querySelector('summary') || {}).innerText || null, inner_len: (d.innerText || '').length })),
    aria_live: Array.from(document.querySelectorAll('[aria-live]')).map((n) => ({ level: n.getAttribute('aria-live'),
      text: (n.innerText || '').trim().slice(0, 240) })),
    exception_in_text: ex.test(body), attr_hits: hits,
    ls: Object.keys(localStorage).map((k) => ({ key: k, value_len: (localStorage.getItem(k) || '').length,
      looks_like_a_journey_id: /^[0-9a-f-]{36}$/.test(localStorage.getItem(k) || '') })),
    sw_controller: !!navigator.serviceWorker.controller,
  };
};

const DEVICE_STORES = async () => await new Promise((resolve) => {
  const done = (o) => resolve(o);
  const out = { indexedDB_databases: null, offline_store_rows: null, caches_keys: null, errors: [] };
  const step1 = indexedDB.databases ? indexedDB.databases() : Promise.reject(new Error('indexedDB.databases unsupported'));
  step1.then((dbs) => {
    out.indexedDB_databases = dbs.map((d) => ({ name: d.name, version: d.version }));
    const target = (dbs.map((d) => d.name).find((n) => /offline|citynexus/i.test(n)) || null);
    if (!target) { out.offline_store_rows = 'NO_OFFLINE_DATABASE'; return done2(out); }
    const req = indexedDB.open(target);
    req.onerror = () => { out.errors.push('open ' + target); done2(out); };
    req.onsuccess = () => {
      const db = req.result; const names = Array.from(db.objectStoreNames || []);
      const rows = {}; let pending = names.length;
      out.store_names = names;
      if (!pending) { out.offline_store_rows = rows; return done2(out); }
      names.forEach((s) => {
        try {
          const tx = db.transaction(s, 'readonly');
          const c = tx.objectStore(s).count();
          c.onsuccess = () => { rows[s] = c.result; if (!--pending) done2(out); };
          c.onerror = () => { rows[s] = 'COUNT_FAILED'; if (!--pending) done2(out); };
        } catch (e) { rows[s] = 'TX_FAILED'; if (!--pending) done2(out); }
      });
    };
  }).catch((e) => { out.errors.push(String(e.message || e).slice(0, 90)); done2(out); });
  function done2(o) {
    if (window.caches && caches.keys) {
      caches.keys().then((k) => { o.caches_keys = k; done(o); }).catch((e) => {
        o.errors.push('caches ' + String(e.message || e).slice(0, 60)); done(o); });
    } else { o.caches_keys = 'NO_CACHES_API'; done(o); }
  }
});

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}
const clean = (r) => { (r.attr_hits || []).forEach((h) => { h.value_sha256 = SHA(Buffer.from(h.raw_for_node_side_hashing, 'utf8'));
                                                          delete h.raw_for_node_side_hashing; }); return r; };

async function newPage(browser, seedId, legs) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  await ctx.addInitScript(([id]) => {
    if (id) { localStorage.setItem('citynexus.v8.journey_id', id); }
    else { Object.keys(localStorage).filter((k) => /citynexus/.test(k)).forEach((k) => localStorage.removeItem(k)); }
  }, [seedId]);
  const page = await ctx.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let rb = null, receipt = null, code = null;
    try { const b = await r.body(); rb = b.length;
      if (r.status() >= 400 && /json/.test(r.headers()['content-type'] || '')) {
        const j = JSON.parse(b.toString('utf8'));
        receipt = (j.error && j.error.error_receipt_id) || j.error_receipt_id || null;
        code = (j.error && j.error.code) || j.code || null;
      } } catch (e) { rb = rb === null ? 'READ_FAILED' : rb; receipt = receipt || 'NOT_JSON'; }
    legs.push({ at: new Date().toISOString(), url: r.url().replace(/^https?:\/\/[^/]+/, ''), m: r.request().method(),
                status: r.status(), ct: r.headers()['content-type'] || null,
                req_bytes: (r.request().postData() || '').length, resp_bytes: rb,
                server_receipt_id: receipt, server_code_field: code });
  });
  return { ctx, page };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, dead_id: DEAD, real_id: REAL_ID,
                clicks: 0, keystrokes: 0, cases: {} };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();

  /* C + D: a stored id the server does not know */
  let legs = [];
  let { ctx, page } = await newPage(browser, DEAD, legs);
  await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(12000);
  const c1 = clean(await page.evaluate(READ));
  out.cases.C1_dead_stored_id_as_it_lands = { read: c1, legs: legs.slice(),
                                              shot: await shot(page, 'C1_dead_id_closed') };
  const opened = await page.evaluate(() => {
    Array.from(document.querySelectorAll('details')).forEach((d) => { d.open = true; });
    const body = document.body.innerText || '';
    return { text_len: body.length, receipts: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
             text: body.slice(0, 2600), details: Array.from(document.querySelectorAll('details')).map((d) => ({
               summary: (d.querySelector('summary') || {}).innerText || null, inner_len: (d.innerText || '').length })) };
  });
  out.cases.C2_same_screen_with_every_fold_open = { read: opened, shot: await shot(page, 'C2_dead_id_open') };
  const after = await page.evaluate(() => ({ journey_id_left_in_localStorage: localStorage.getItem('citynexus.v8.journey_id'),
                                             keys: Object.keys(localStorage) }));
  out.cases.C3_device_state_after_the_rejection = after;
  out.cases.C4_journey_legs = legs.filter((l) => /journeys/.test(l.url));
  await ctx.close();

  /* E: what the device holds behind a durability sentence, measured on a real journey boot */
  if (REAL_ID) {
    legs = [];
    const r2 = await newPage(browser, REAL_ID, legs);
    page = r2.page; ctx = r2.ctx;
    const t0 = Date.now();
    await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
    const marks = [];
    for (let i = 0; i < 40; i++) {
      await page.waitForTimeout(4000);
      const s = clean(await page.evaluate(READ));
      marks.push({ at_ms: Date.now() - t0, text_len: s.text_len, pending: s.pending_words,
                   receipts: s.receipts_on_screen, buttons: s.buttons.map((b) => b.text).slice(0, 12),
                   claims_saved_shown: s.claims_saved_shown, claims_offline: s.claims_offline,
                   details_count: s.details_count });
      if (!s.pending_words && s.buttons.filter((b) => b.text).length > 3) break;
    }
    const settled = clean(await page.evaluate(READ));
    out.cases.E_real_journey_boot = { marks, waited_ms: Date.now() - t0, settled, legs: legs.slice(),
                                      device_stores: await page.evaluate(DEVICE_STORES),
                                      shot: await shot(page, 'E1_real_journey_settled') };
    await ctx.close();
  } else {
    out.cases.E_real_journey_boot = 'SKIPPED - no journey id passed in';
  }

  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r6_dead_id_saved.json'), JSON.stringify(out, null, 1));
  const c = out.cases.C1_dead_stored_id_as_it_lands.read;
  console.log(JSON.stringify({ dead_screen: { text_len: c.text_len, claims_offline: c.claims_offline,
    names_not_found: c.names_not_found, receipts: c.receipts_on_screen, details: c.details_count,
    buttons: c.buttons.map((b) => b.text).slice(0, 10), ls: c.ls },
    journey_legs: out.cases.C4_journey_legs.map((l) => [l.m, l.url.slice(0, 60), l.status, l.resp_bytes, l.server_receipt_id]),
    after_rejection: out.cases.C3_device_state_after_the_rejection,
    opened_receipts: out.cases.C2_same_screen_with_every_fold_open.read.receipts,
    E: out.cases.E_real_journey_boot === 'SKIPPED - no journey id passed in' ? 'skipped'
      : { waited_ms: out.cases.E_real_journey_boot.waited_ms, marks: out.cases.E_real_journey_boot.marks.length,
          stores: out.cases.E_real_journey_boot.device_stores } }, null, 1));
  console.log('C1 TEXT:\n' + (c.text || '').slice(0, 1500));
  await browser.close();
})().catch((e) => { console.error('C FAILED: ' + String((e && e.message) || e)); process.exit(9); });
