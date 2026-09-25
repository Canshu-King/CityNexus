/* ORD-0300 C2 pairing - page-side witness for one leg, read four ways.
 *
 * The challenge I am answering: in my ORD-0300 C2 cell, "the server answered 500" and "the screen said
 * unreachable" were two readings of two things that merely looked alike. So every leg here is pinned by a
 * token MY proxy mints (the product never sees it, a client cannot guess it):
 *   (a) proxy log   - did THIS leg reach the product, and what status came back for that token;
 *   (b) page fetch  - the app's own fetch: resolved with a Response (status/ok/token) or rejected;
 *   (c) body read   - the app asked that very response for its body through Response.prototype.json and the
 *                     parse failed: proof the answer was physically in the page's hands;
 *   (d) painted card- what the traveller reads, plus whether 技术详情 exists at all.
 * (c) is the one that decides it: on the old generation (a)/(b)/(c) all say "500 arrived" while (d) says
 * 「连不上服务端」 with zero detail blocks, because the sheet's own formatting crash lands in its catch.
 * React swallows that exception, so there is no console trace - the failed body parse IS the trace.
 *
 * Usage: node c2_cells.cjs <faceBase> <journeyId> <outFile> <mode:lock|abort_control>
 *                                   <readyFlagPath> <text>
 */
const fs = require('fs');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const FACE = process.argv[2];
const JOURNEY = process.argv[3];
const OUT = process.argv[4];
const MODE = process.argv[5] || 'lock';
const READY = process.argv[6];
const TEXT = process.argv[7] || '想傍晚在老城慢慢走一圈，别太赶';
const PORT = Number(FACE.split(':').pop());

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* painted text is what is judged; data-* attributes are collected only as a cross-check */
const SCREEN = () => {
  const txt = (el) => (el ? el.innerText : null);
  const card = document.querySelector('[data-testid="plan-ai-result"]');
  const toggle = document.querySelector('[data-testid="plan-ai-detail-toggle"]');
  const kind = document.querySelector('[data-testid="plan-ai-detail-kind"]');
  const reason = document.querySelector('[data-testid="plan-ai-reason"]');
  const body = document.body ? document.body.innerText : '';
  return {
    result_card_painted: txt(card),
    network_card_painted: body.indexOf('连不上服务端') >= 0,
    http500_card_painted: body.indexOf('服务端处理失败') >= 0,
    detail_toggle_present: !!toggle,
    details_elements_present: document.querySelectorAll('details').length,
    reason_label_painted: txt(kind),
    reason_value_painted: txt(reason),
    cross_check_data_result_status: card ? card.getAttribute('data-result-status') : null,
    cross_check_data_reason_origin: kind ? kind.getAttribute('data-reason-origin') : null,
    body_has_no_readble_answer_note: body.indexOf('no readable answer reached this device') >= 0
      || body.indexOf('这台设备自己的读数') >= 0,
    busy_present: !!document.querySelector('[data-testid="plan-ai-busy"]'),
  };
};

const INSTRUMENT = () => {
  window.__legs = [];
  window.__consumed = [];
  const of = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const rec = { url: url, method: (init && init.method) || (input && input.method) || 'GET',
                  api: url.indexOf('/api/') >= 0, sent_at_wall: new Date().toISOString(),
                  sent_at: Date.now() };
    if (rec.api && rec.method === 'POST' && init && init.body) rec.request_body = String(init.body).slice(0, 140);
    let res;
    try {
      res = await of.call(window, input, init);
    } catch (e) {
      rec.fetch_rejected = true;
      rec.reject_name = (e && e.name) || 'unknown';
      rec.reject_message = String((e && e.message) || e).slice(0, 150);
      rec.elapsed_ms = Date.now() - rec.sent_at;
      window.__legs.push(rec);
      throw e;
    }
    rec.fetch_rejected = false;
    rec.status = res.status;
    rec.ok = res.ok;
    rec.content_type = res.headers.get('content-type');
    rec.pair_token = res.headers.get('x-hjp3-pair');
    rec.elapsed_ms = Date.now() - rec.sent_at;
    window.__legs.push(rec);
    return res;
  };
  const oj = Response.prototype.json;
  Response.prototype.json = async function () {
    const ent = { url: this.url, status: this.status, pair_id: this.headers.get('x-hjp3-pair'),
                  at_wall: new Date().toISOString() };
    try {
      const v = await oj.call(this);
      ent.parsed = true;
      ent.top_type = typeof v;
      ent.top_keys = v && typeof v === 'object' ? Object.keys(v).slice(0, 8) : null;
      window.__consumed.push(ent);
      return v;
    } catch (e) {
      ent.parsed = false;
      ent.error_name = (e && e.name) || 'unknown';
      ent.error_message = String((e && e.message) || e).slice(0, 150);
      window.__consumed.push(ent);
      throw e;                       /* exactly what the app would have got; nothing is rewritten */
    }
  };
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                            hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  await context.addInitScript(INSTRUMENT);
  await context.addInitScript((j) => {
    try { localStorage.setItem('citynexus.v8.journey_id', j); } catch (e) { /* ignore */ }
  }, JOURNEY);
  const page = await context.newPage();
  const page_errors = [];
  const cdp = [];
  page.on('pageerror', (e) => page_errors.push({ name: e && e.name, text: String((e && e.message) || e).slice(0, 200) }));
  /* the browser network stack's own witness, independent of my wrapper */
  page.on('response', (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    cdp.push({ url: r.url().replace(/^http:\/\/127.0.0.1:\d+/, ''), status: r.status(),
               pair_id: r.headers()['x-hjp3-pair'], content_type: r.headers()['content-type'],
               failure: null, at_wall: new Date().toISOString() });
  });
  page.on('requestfailed', (rq) => {
    if (rq.url().indexOf('/api/') < 0) return;
    cdp.push({ url: rq.url().replace(/^http:\/\/127.0.0.1:\d+/, ''), status: null, pair_id: null,
               content_type: null, failure: (rq.failure() && rq.failure().errorText) || 'failed',
               at_wall: new Date().toISOString() });
  });
  if (MODE === 'abort_control') {
    /* a TRUE transport death: this leg never reaches the product, so the proxy log stays silent about it.
       If the painted card is then indistinguishable from the arrived-and-crashed case, the card alone can
       never tell them apart - which is the whole point of pairing by token. */
    await page.route('**/api/v1/journeys/*/agent/commands', (route) => {
      if (route.request().method() === 'POST') return route.abort('failed');
      return route.continue();
    });
  }

  await page.goto('http://127.0.0.1:' + PORT + '/', { waitUntil: 'load', timeout: 60000 });
  const hub = page.locator('[data-testid="hub-plan-with-ai"]');
  const hubReached = await hub.waitFor({ state: 'visible', timeout: 25000 }).then(() => true).catch(() => false);
  if (!hubReached) {
    fs.writeFileSync(OUT, JSON.stringify({ hub_reached: false, mode: MODE }, null, 1), { encoding: 'utf-8' });
    await browser.close();
    console.log(JSON.stringify({ hub_reached: false }));
    return;
  }
  await hub.click();
  const input = page.locator('[data-testid="plan-ai-input"]');
  const sheetOpened = await input.waitFor({ state: 'visible', timeout: 15000 }).then(() => true).catch(() => false);
  if (!sheetOpened) {
    fs.writeFileSync(OUT, JSON.stringify({ hub_reached: true, sheet_opened: false, mode: MODE }, null, 1),
                     { encoding: 'utf-8' });
    await browser.close();
    console.log(JSON.stringify({ hub_reached: true, sheet_opened: false }));
    return;
  }
  await input.fill(TEXT);
  await sleep(400);
  if (MODE === 'lock' && READY) fs.writeFileSync(READY, String(Date.now()));  // the rig takes the lock on sight

  const t0 = Date.now();
  await page.locator('[data-testid="plan-ai-submit"]').click();
  let card = null;
  const samples = [];
  for (let i = 0; i < 230; i++) {
    await sleep(500);
    const st = await page.evaluate(SCREEN);
    samples.push({ ms: Date.now() - t0, status: st.cross_check_data_result_status,
                   details: st.details_elements_present, busy: st.busy_present });
    if (st.cross_check_data_result_status && !st.busy_present) { card = st; break; }
    if (Date.now() - t0 > 120000) break;
  }
  await sleep(3000);
  const after = await page.evaluate(SCREEN);
  const collected = await page.evaluate(() => ({ legs: window.__legs || [], consumed: window.__consumed || [] }));
  fs.writeFileSync(OUT, JSON.stringify({
    mode: MODE, port: PORT, journey: JOURNEY, hub_reached: true, sheet_opened: true,
    card: card, after_open: after, legs: collected.legs, consumed: collected.consumed, cdp: cdp,
    page_errors: page_errors, samples: samples.slice(-6), sample_count: samples.length,
    waited_ms: Date.now() - t0,
  }, null, 1), { encoding: 'utf-8' });
  await browser.close();
  const w = collected.legs.find((l) => l.method === 'POST' && l.url.indexOf('agent/commands') >= 0) || {};
  const c = collected.consumed.find((x) => (x.url || '').indexOf('agent/commands') >= 0) || {};
  console.log(JSON.stringify({ mode: MODE, result_status: after.cross_check_data_result_status,
    network_card: after.network_card_painted, http500_card: after.http500_card_painted,
    details: after.details_elements_present, fetch_rejected: w.fetch_rejected, status: w.status,
    token: w.pair_token, body_parsed: c.parsed, body_err: c.error_name }));
})().catch((e) => { console.log('RUNNER-ERROR ' + String(e).slice(0, 200)); process.exit(4); });
