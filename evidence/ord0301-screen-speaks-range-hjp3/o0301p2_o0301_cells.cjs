/* ORD-0301: one outcome class per arm, both sides read for every row.
   Server side  = the HTTP answer this very leg produced (status, content-type, bytes, envelope fields,
                  who produced it) as recorded by the page's own fetch AND by the origin's accounting.
   Screen side  = the words painted (innerText), whether 「连不上服务端」 appeared, whether a <details>
                  技术详情 block exists at all, and what label/value it paints.

  env ARM=<name> FACE_PORT=<p> POLICY_STAMP=<stamp> [NEED_LOCK=1] [INSTRUMENTED=0] [CAP_MS=..]
*/
const { chromium } = require('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend/node_modules/playwright');
const fs = require('fs');

const OUT = 'D:/moodle/_hjp3_0301_0925';
const TAG = fs.readFileSync(OUT + '/current_state_tag.txt', 'utf-8').trim();
const state = JSON.parse(fs.readFileSync(OUT + '/' + TAG + '_state.json', 'utf-8'));
const JOURNEY = state.seed.journey_id;
const TEXT = '想傍晚在老城慢慢走一圈，别太赶';
const RUN = process.env.RUN_ID || 'O0301-0000';
const ARM = process.env.ARM || 'unnamed';
const PORT = Number(process.env.FACE_PORT || state.faces[1].port);
const STAMP = process.env.POLICY_STAMP || 'none';
const INSTRUMENTED = process.env.INSTRUMENTED !== '0';
const CAP = Number(process.env.CAP_MS || 45000);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* Records what the page itself received, and separately what the app did with it: a rejection of
   response.json() is a different fact from a rejection of fetch(), and ORD-0300 could not tell them
   apart. Both are now logged. */
const INSTRUMENT = (journey) => {
  try { localStorage.setItem('citynexus.v8.journey_id', journey); } catch (e) { /* ignore */ }
  window.__legs = [];
  window.__json_errors = [];
  const t0 = Date.now();
  const orig = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const rec = { url, method, api: url.indexOf('/api/') >= 0, sent_ms_since_load: Date.now() - t0,
                  sent_wall: new Date().toISOString(), has_signal: !!(init && init.signal),
                  request_body: (init && typeof init.body === 'string') ? init.body.slice(0, 160) : null };
    window.__legs.push(rec);
    const s = Date.now();
    try {
      const res = await orig.apply(window, arguments);
      rec.status = res.status;
      rec.content_type = res.headers.get('content-type');
      try {
        const txt = await res.clone().text();
        rec.bytes = txt.length;
        rec.body_head = txt.slice(0, 300);
        try {
          const j = JSON.parse(txt);
          rec.server_envelope = { error_code: (j && j.error && j.error.code) || null,
                                  error_message: (j && j.error && typeof j.error.message === 'string') ? j.error.message : null,
                                  reason_code: (j && j.error && j.error.reason_code) || null,
                                  top_level_detail: (j && typeof j.detail === 'string') ? j.detail : null };
        } catch (e) { rec.server_envelope = { unparsable_body: true }; }
      } catch (e) { rec.bytes_read_error = String(e && e.message).slice(0, 140); }
      rec.elapsed_ms = Date.now() - s;
      return res;
    } catch (e) {
      rec.client_error = (e && e.name ? e.name + ': ' : '') + String((e && e.message) || e).slice(0, 160);
      rec.elapsed_ms = Date.now() - s;
      throw e;
    }
  };
  const origJson = Response.prototype.json;
  Response.prototype.json = function () {
    const self = this;
    return origJson.apply(this, arguments).catch((e) => {
      window.__json_errors.push({ status: self.status, url: self.url, content_type: (self.headers.get('content-type') || null),
                                  error_name: e && e.name, error_message: String((e && e.message) || e).slice(0, 160),
                                  at_ms: Date.now() - t0 });
      throw e;
    });
  };
};

/* everything judged here is painted text; data-* attributes are collected only as a cross-check */
const SCREEN = () => {
  const txt = (el) => (el ? el.innerText : null);
  const kind = document.querySelector('[data-testid="plan-ai-detail-kind"]');
  const reason = document.querySelector('[data-testid="plan-ai-reason"]');
  const toggle = document.querySelector('[data-testid="plan-ai-detail-toggle"]');
  const card = document.querySelector('[data-testid="plan-ai-result"]');
  const body = document.body ? document.body.innerText : '';
  return {
    result_card: txt(card),
    network_card_painted: body.indexOf('连不上服务端') >= 0,
    detail_toggle_present: !!toggle,
    details_elements_present: document.querySelectorAll('details').length,
    detail_open: (function () { const d = document.querySelector('details.plan-ai-detail'); return d ? d.open : null; })(),
    reason_label_painted: txt(kind),
    reason_value_painted: txt(reason),
    cross_check_data_result_status: card ? card.getAttribute('data-result-status') : null,
    cross_check_data_reason_origin: kind ? kind.getAttribute('data-reason-origin') : null,
    deadline_sentence_on_screen: /等了\s*\d+\s*秒|No answer from this server in/.test(body),
    body_head: body.slice(0, 400),
    submit_visible: !!document.querySelector('[data-testid="hub-plan-with-ai"]'),
  };
};

async function openSheet(page) {
  await page.goto('http://127.0.0.1:' + PORT + '/', { waitUntil: 'load', timeout: 60000 });
  const hub = page.locator('[data-testid="hub-plan-with-ai"]');
  const ok = await hub.waitFor({ state: 'visible', timeout: 20000 }).then(() => true).catch(() => false);
  if (!ok) return { hub_reached: false };
  await hub.click();
  const input = page.locator('[data-testid="plan-ai-input"]');
  const sheetOk = await input.waitFor({ state: 'visible', timeout: 12000 }).then(() => true).catch(() => false);
  if (!sheetOk) return { hub_reached: true, sheet_opened: false, screen: await page.evaluate(SCREEN) };
  await input.fill(TEXT);
  return { hub_reached: true, sheet_opened: true };
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                            hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  if (INSTRUMENTED) {
    await context.addInitScript(INSTRUMENT, JOURNEY);
  } else {
    /* the no-instrument reproduction still has to point the shell at MY journey; that is one
       localStorage write, not an observation hook, and without it the app opens on onboarding */
    await context.addInitScript((j) => { try { localStorage.setItem('citynexus.v8.journey_id', j); } catch (e) { /* ignore */ } }, JOURNEY);
  }
  const page = await context.newPage();
  const errors = [];
  const failed = [];
  page.on('pageerror', (e) => errors.push({ kind: 'pageerror', name: e && e.name, text: String((e && e.message) || e).slice(0, 260) }));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push({ kind: 'console', text: m.text().slice(0, 260) }); });
  page.on('requestfailed', (r) => { if (r.url().indexOf('/api/') >= 0)
    failed.push({ url: r.url().split('/api/')[1].slice(0, 90), method: r.method(), failure: r.failure() && r.failure().errorText }); });
  if (process.env.ROUTE_ABORT === '1') {
    /* 真·传输失败：浏览器这一发根本没拿到任何 HTTP 回答（不是代理替应用答，也不是我吞掉的响应）。
       只掐被点那一腿，其余路由照常，免得把别的类别混进来。 */
    await page.route('**/agent/commands', (route) => route.request().method() === 'POST'
      ? route.abort('failed') : route.continue());
  }
  const opened = await openSheet(page);
  const out = { arm: ARM, run_id: RUN, face_port: PORT, policy_stamp: STAMP, instrumented: INSTRUMENTED,
                measured_on: state.measured_on, bundle_sha256: state.bundle_facts.served_sha256,
                bundle_asset: state.bundle_facts.served_asset, journey_id: JOURNEY, request_text: TEXT,
                opened, cap_ms: CAP };
  if (!opened.hub_reached || !opened.sheet_opened) {
    const t0 = Date.now();
    const seen = [];
    while (Date.now() - t0 < CAP) {
      await sleep(1000);
      const s = await page.evaluate(SCREEN);
      seen.push({ ms: Date.now() - t0, network_card: s.network_card_painted, deadline: s.deadline_sentence_on_screen,
                  body_head: s.body_head.slice(0, 160) });
      if (s.deadline_sentence_on_screen || s.network_card_painted) break;
    }
    const s = await page.evaluate(SCREEN);
    out.no_sheet = { screen: s, watch: seen.filter((r, i, a) => !i || r.body_head !== a[i - 1].body_head) };
    if (INSTRUMENTED) {
      out.no_sheet.legs = await page.evaluate(() => window.__legs);
      out.no_sheet.json_errors = await page.evaluate(() => window.__json_errors);
    }
    out.request_failures = failed; out.page_events = errors;
    fs.writeFileSync(OUT + '/cell_' + ARM + '_' + RUN + '.json', JSON.stringify(out, null, 1), 'utf-8');
    await page.screenshot({ path: OUT + '/shots_' + RUN + '-' + ARM + '-end.png' });
    await browser.close();
    return console.log(JSON.stringify({ arm: ARM, hub_reached: opened.hub_reached, sheet_opened: !!opened.sheet_opened,
      network_card: s.network_card_painted, deadline: s.deadline_sentence_on_screen }, null, 1));
  }
  if (process.env.NEED_LOCK === '1') {
    fs.writeFileSync(OUT + '/sheet_ready.flag', String(Date.now()));
    const flag = OUT + '/lock_armed.flag';
    if (fs.existsSync(flag)) fs.unlinkSync(flag);
    const w0 = Date.now();
    while (!fs.existsSync(flag)) {
      if (Date.now() - w0 > 120000) throw new Error('lock flag never appeared');
      await sleep(200);
    }
  }
  const t0 = Date.now();
  await page.locator('[data-testid="plan-ai-submit"]').click();
  const timeline = [];
  let firstDeadlineLine = null;
  for (;;) {
    const legs = INSTRUMENTED ? await page.evaluate(() => window.__legs) : [];
    const posts = legs.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD');
    const s = await page.evaluate(SCREEN);
    const ms = Date.now() - t0;
    if (s.deadline_sentence_on_screen && !firstDeadlineLine) {
      firstDeadlineLine = { ms, card: (s.result_card || '').split('\n')[0] };
    }
    if (s.detail_toggle_present && !s.detail_open) {
      await page.locator('[data-testid="plan-ai-detail-toggle"]').click().catch(() => {});
    }
    timeline.push({ ms, network_card: s.network_card_painted, status: s.cross_check_data_result_status,
                    card_first_line: (s.result_card || '').split('\n')[0],
                    label: s.reason_label_painted, value: (s.reason_value_painted || '').slice(0, 90),
                    details: s.details_elements_present });
    const settled = INSTRUMENTED ? posts.find((p) => p.status !== undefined || p.client_error)
                                : !!s.cross_check_data_result_status;
    if (settled && ms > 2000) break;
    if (ms > CAP) break;
    await sleep(200);
  }
  /* after the leg settles, the card is allowed to change again; the last state is what the traveller
     ends up reading, so watch it for a few seconds instead of trusting one sample */
  const settle = [];
  for (let k = 0; k < 12; k++) {
    await sleep(500);
    const s2 = await page.evaluate(SCREEN);
    settle.push({ ms: Date.now() - t0, network_card: s2.network_card_painted, status: s2.cross_check_data_result_status,
                  card_first_line: (s2.result_card || '').split('\n')[0], label: s2.reason_label_painted,
                  value: (s2.reason_value_painted || '').slice(0, 90), details: s2.details_elements_present });
  }
  const legs = INSTRUMENTED ? await page.evaluate(() => window.__legs) : [];
  const jsonErrors = INSTRUMENTED ? await page.evaluate(() => window.__json_errors) : [];
  const screen = await page.evaluate(SCREEN);
  await page.screenshot({ path: OUT + '/shots_' + RUN + '-' + ARM + '-end.png' });
  out.tap_ms_wall = new Date(t0).toISOString();
  out.write_legs = legs.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD');
  out.all_api_legs_count = legs.filter((l) => l.api).length;
  out.json_rejections = jsonErrors;
  out.first_client_deadline_line = firstDeadlineLine;
  out.screen_final = screen;
  out.timeline_states = timeline.filter((r, i, a) => !i || r.status !== a[i - 1].status || r.card_first_line !== a[i - 1].card_first_line || r.label !== a[i - 1].label || r.details !== a[i - 1].details);
  out.settle_states = settle.filter((r, i, a) => !i || r.status !== a[i - 1].status || r.card_first_line !== a[i - 1].card_first_line || r.details !== a[i - 1].details);
  out.request_failures = failed;
  out.page_events = errors;
  fs.writeFileSync(OUT + '/cell_' + ARM + '_' + RUN + '.json', JSON.stringify(out, null, 1), 'utf-8');
  console.log(JSON.stringify({ arm: ARM, run: RUN, legs: out.write_legs.map((p) => ({ s: p.status, ct: p.content_type,
      b: p.bytes, ms: p.elapsed_ms, err: p.client_error, code: p.server_envelope && p.server_envelope.error_code })),
    net_card: screen.network_card_painted, status_attr: screen.cross_check_data_result_status,
    first_line: (screen.result_card || '').split('\n')[0], details: screen.details_elements_present,
    label: screen.reason_label_painted, value: (screen.reason_value_painted || '').slice(0, 70),
    req_failed: failed.map((f) => f.failure) }, null, 1));
  await browser.close();
}

run().catch((e) => { console.log('ERROR ' + String(e).slice(0, 300)); process.exit(1); });
