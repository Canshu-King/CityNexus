/* ORD-0301 pass 3 - the page's own witness for one leg, read four ways, inside the same hop.
 *
 * Why this file exists as a NEW name: CMDR-0925-2128 forbids rewriting a published instrument path, and
 * `c2_cells.cjs` is published. What changes here is not cosmetic - the commander's correction (2) says the
 * server-side reading and the screen-side reading must be taken in ONE proxy chain, so this reader no longer
 * carries any "what did the backend answer" claim of its own: it records, for the leg the page itself sent,
 *   (a) the pairing id that arrived in this very response header (`pair_id`, minted by p3proxy.py),
 *   (b) the app's own fetch outcome (resolved Response: status/ok/content-type, or a rejection),
 *   (c) whether the app's own `Response.prototype.json` call parsed, and what top-level keys it saw,
 *   (d) the painted card: the sentence the traveller reads, the attribution label, and whether a 技术详情
 *       block exists in the DOM at all.
 * The server side of the same leg comes from the proxy's audit line for that same id - one request, two ends,
 * no second probe.
 *
 * Usage: node p3_cells.cjs <faceBase> <journeyId> <outFile> <scenario> <readyFlag> [--shot]
 *   scenario: product  (the leg is answered by the product through the chain)
 *             lock     (the rig grabs the write lock when the ready flag appears)
 *             spec     (this hop answers the leg; behaviourally identical from the page's side)
 *             abort    (a true transport death: the leg never reaches the hop)
 */
const fs = require('fs');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const FACE = process.argv[2];
const JOURNEY = process.argv[3];
const OUT = process.argv[4];
const SCENARIO = process.argv[5] || 'product';
const READY = process.argv[6];
const SHOT = process.argv.indexOf('--shot') > 0;
/* Positional text is argv[7]; a flag in that slot is not a request. The first two lock arms of this pass
   died because my own runner put `--shot` there, the sheet saw a 6-character request, and
   `aria-disabled` did exactly what ORD-0066 (甲) designed it to do. */
const TEXT = (process.argv[7] && !process.argv[7].startsWith('--') ? process.argv[7] : null)
  || '想傍晚在老城慢慢走一圈，别太赶';
const PORT = Number(FACE.split(':').pop());
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* judged on RENDERED TEXT; data-* attributes ride along only as a cross-check of the same fact.
   `textContent` is captured beside `innerText` on purpose: a collapsed <details> makes innerText read
   empty for everything inside it, and the first pilot arm of this pass proved that blind spot by scoring
   「服务器给出的原因」 as absent when it was present-but-folded. The reader below opens the block, so the
   text it reports is text a traveller reaches by tapping 技术详情. */
const SCREEN = () => {
  const txt = (el) => (el ? el.innerText : null);
  const raw = (el) => (el ? el.textContent : null);
  const card = document.querySelector('[data-testid="plan-ai-result"]');
  const kind = document.querySelector('[data-testid="plan-ai-detail-kind"]');
  const reason = document.querySelector('[data-testid="plan-ai-reason"]');
  const body = document.body ? document.body.innerText : '';
  const details0 = document.querySelector('.plan-ai-result details');
  return {
    result_card_painted: txt(card),
    result_card_text_content: raw(card),
    card_title_painted: card && card.querySelector('b') ? card.querySelector('b').innerText : null,
    card_body_painted: card && card.querySelector('p') ? card.querySelector('p').innerText : null,
    reason_label_painted: txt(kind),
    reason_value_painted: txt(reason),
    reason_label_text_content: raw(kind),
    reason_value_text_content: raw(reason),
    details_elements_present: document.querySelectorAll('details').length,
    details_open_attribute: details0 ? !!details0.open : null,
    detail_toggle_present: !!document.querySelector('[data-testid="plan-ai-detail-toggle"]'),
    network_card_painted: body.indexOf('连不上服务端') >= 0,
    http_failed_card_painted: body.indexOf('服务端处理失败') >= 0,
    refused_card_painted: body.indexOf('这个要求被明确拒绝') >= 0,
    server_attribution_painted: body.indexOf('服务器给出的原因') >= 0,
    device_attribution_painted: body.indexOf('这台设备自己的读数') >= 0,
    unreadable_answer_note_painted: body.indexOf('no readable answer reached this device') >= 0,
    whole_page_contains_server_label: (document.body ? document.body.textContent : '')
      .indexOf('服务器给出的原因') >= 0,
    whole_page_contains_device_label: (document.body ? document.body.textContent : '')
      .indexOf('这台设备自己的读数') >= 0,
    next_step_painted: (() => {
      const n = document.querySelector('[data-testid="plan-ai-next-step"]');
      return n ? n.innerText : null;
    })(),
    cross_check_data_result_status: card ? card.getAttribute('data-result-status') : null,
    cross_check_data_reason_origin: kind ? kind.getAttribute('data-reason-origin') : null,
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
    if (rec.api && rec.method === 'POST' && init && init.body) rec.request_body = String(init.body).slice(0, 160);
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
    rec.pair_id = res.headers.get('x-hjp3-pair');
    rec.elapsed_ms = Date.now() - rec.sent_at;
    window.__legs.push(rec);
    return res;
  };
  const oj = Response.prototype.json;
  Response.prototype.json = async function () {
    const ent = { url: this.url, status: this.status, pair_id: this.headers.get('x-hjp3-pair'),
                  content_type: this.headers.get('content-type'), at_wall: new Date().toISOString() };
    try {
      const v = await oj.call(this);
      ent.parsed = true;
      ent.top_type = typeof v;
      ent.top_keys = v && typeof v === 'object' ? Object.keys(v).slice(0, 8) : null;
      ent.error_keys = v && typeof v === 'object' && v.error && typeof v.error === 'object'
        ? Object.keys(v.error).slice(0, 8) : null;
      ent.error_message_type = v && v.error ? typeof v.error.message : null;
      ent.detail_type = v && typeof v === 'object' ? typeof v.detail : null;
      window.__consumed.push(ent);
      return v;
    } catch (e) {
      ent.parsed = false;
      ent.error_name = (e && e.name) || 'unknown';
      ent.error_message = String((e && e.message) || e).slice(0, 150);
      window.__consumed.push(ent);
      throw e;                      /* exactly what the app would have got; nothing is rewritten */
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
  page.on('pageerror', (e) => page_errors.push({ name: e && e.name,
                                                 text: String((e && e.message) || e).slice(0, 200) }));
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
  if (SCENARIO === 'abort') {
    await page.route('**/api/v1/journeys/*/agent/commands', (route) => {
      if (route.request().method() === 'POST') return route.abort('failed');
      return route.continue();
    });
  }

  await page.goto('http://127.0.0.1:' + PORT + '/', { waitUntil: 'load', timeout: 60000 });
  const hub = page.locator('[data-testid="hub-plan-with-ai"]');
  const hubReached = await hub.waitFor({ state: 'visible', timeout: 25000 }).then(() => true).catch(() => false);
  if (!hubReached) {
    fs.writeFileSync(OUT, JSON.stringify({ hub_reached: false, scenario: SCENARIO }, null, 1));
    await browser.close();
    console.log(JSON.stringify({ hub_reached: false }));
    return;
  }
  await hub.click();
  const input = page.locator('[data-testid="plan-ai-input"]');
  const sheetOpened = await input.waitFor({ state: 'visible', timeout: 15000 })
    .then(() => true).catch(() => false);
  if (!sheetOpened) {
    fs.writeFileSync(OUT, JSON.stringify({ hub_reached: true, sheet_opened: false, scenario: SCENARIO }, null, 1));
    await browser.close();
    console.log(JSON.stringify({ hub_reached: true, sheet_opened: false }));
    return;
  }
  await input.fill(TEXT);
  await sleep(400);
  if (SCENARIO === 'lock' && READY) fs.writeFileSync(READY, String(Date.now()));

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
    if (Date.now() - t0 > 150000) break;
  }
  await sleep(2500);
  const after = await page.evaluate(SCREEN);
  /* open 技术详情 the way a traveller would, then read what the opened block actually says */
  let opened = null;
  let open_attempt = { toggle: 'no_toggle_present' };
  if (after.detail_toggle_present) {
    const t = page.locator('[data-testid="plan-ai-detail-toggle"]');
    const wasOpen = await t.evaluate((el) => !!(el.parentElement && el.parentElement.open))
      .catch(() => null);
    open_attempt = { clicked: false, was_already_open: wasOpen };
    if (!wasOpen) {
      open_attempt.clicked = await t.click({ timeout: 5000 }).then(() => true).catch(() => false);
      await sleep(600);
    }
    opened = await page.evaluate(SCREEN);
    open_attempt.details_open_after = opened.details_open_attribute;
  }
  const collected = await page.evaluate(() => ({ legs: window.__legs || [],
                                                 consumed: window.__consumed || [] }));
  if (SHOT) {
    const el = await page.$('[data-testid="plan-ai-sheet"]');
    if (el) await el.screenshot({ path: OUT.replace(/\.json$/, '.png') });
  }
  fs.writeFileSync(OUT, JSON.stringify({
    scenario: SCENARIO, port: PORT, journey: JOURNEY, hub_reached: true, sheet_opened: true,
    card: card, after_open: after, after_details_opened: opened, open_attempt: open_attempt,
    legs: collected.legs, consumed: collected.consumed, cdp: cdp,
    page_errors: page_errors, samples: samples.slice(-8), sample_count: samples.length,
    waited_ms: Date.now() - t0,
  }, null, 1));
  await browser.close();
  const w = collected.legs.find((l) => l.method === 'POST' && l.url.indexOf('agent/commands') >= 0) || {};
  const c = collected.consumed.find((x) => (x.url || '').indexOf('agent/commands') >= 0) || {};
  const o = opened || after;
  console.log(JSON.stringify({ scenario: SCENARIO, status: after.cross_check_data_result_status,
    title: after.card_title_painted, label: o.reason_label_text_content,
    reason: o.reason_value_text_content, details: after.details_elements_present,
    opened_label_rendered: o.reason_label_painted, origin: after.cross_check_data_reason_origin,
    fetch_rejected: w.fetch_rejected, page_saw: w.status, pair_id: w.pair_id,
    body_parsed: c.parsed, parse_err: c.error_name, top_keys: c.top_keys }));
})().catch((e) => { console.log('RUNNER-ERROR ' + String(e).slice(0, 200)); process.exit(4); });
