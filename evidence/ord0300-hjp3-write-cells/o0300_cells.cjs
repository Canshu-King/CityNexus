/* ORD-0300: the two cells, re-measured on the landed tip 90d29a17… with that generation's own bundle.
   Both sides are read: the fields the server actually sent, and the words painted on the screen.
   stage w2     - one bounded write-lock window, real tap on 开始规划, read both sides of the refusal
   stage wnamed - two lock windows inside one request so its 45 s write budget can actually be exhausted;
                  the point is to get an answer that CARRIES a server sentence and see whether the screen
                  quotes it verbatim under 「服务器给出的原因」 (== , never `in`)
   stage tb     - the same bundle behind a selective origin (reads answered, POST swallowed): does the
                  client ever bound its own write?  A duration here is a reading, not an assertion (Q25).
*/
const { chromium } = require('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend/node_modules/playwright');
const fs = require('fs');

const OUT = 'D:/moodle/_hjp3_0300_0925';
const state = JSON.parse(fs.readFileSync(OUT + '/o0300_state.json', 'utf-8'));
const JOURNEY = state.seed.journey_id;
const TEXT = '想傍晚在老城慢慢走一圈，别太赶';
const RUN = process.env.RUN_ID || 'O0300';
const stage = process.argv[2];
const PORT = Number(process.env.PORT_OVERRIDE || (stage === 'tb' ? state.silent.face.port : state.face.port));
const BUNDLE_SHA = process.env.BUNDLE_SHA || state.face.served_sha256;
const BUNDLE_ASSET = process.env.BUNDLE_ASSET || state.face.served_asset;
const CAP = Number(process.env.CAP_MS || 70000);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const INSTRUMENT = (journey) => {
  try { localStorage.setItem('citynexus.v8.journey_id', journey); } catch (e) { /* ignore */ }
  window.__legs = [];
  const t0 = Date.now();
  const orig = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const rec = { url, method, api: url.indexOf('/api/') >= 0, sent_ms_since_load: Date.now() - t0,
                  sent_wall: new Date().toISOString(), has_signal: !!(init && init.signal),
                  request_body: (init && typeof init.body === 'string') ? init.body.slice(0, 200) : null };
    window.__legs.push(rec);
    const s = Date.now();
    try {
      const res = await orig.apply(window, arguments);
      rec.status = res.status;
      rec.content_type = res.headers.get('content-type');
      try {
        const txt = await res.clone().text();
        rec.bytes = txt.length;
        rec.body_head = txt.slice(0, 400);
        try {
          const j = JSON.parse(txt);
          rec.server_envelope = { has_error_object: !!(j && typeof j.error === 'object' && j.error),
                                  error_code: (j && j.error && j.error.code) || null,
                                  error_message: (j && j.error && typeof j.error.message === 'string') ? j.error.message : null,
                                  reason_code: (j && j.error && j.error.reason_code) || null,
                                  top_level_detail: (typeof j?.detail === 'string') ? j.detail : null };
        } catch (e) { rec.server_envelope = { unparsable_body: true }; }
      } catch (e) { rec.bytes_read_error = String(e && e.message).slice(0, 120); }
      rec.elapsed_ms = Date.now() - s;
      return res;
    } catch (e) {
      rec.client_error = (e && e.name ? e.name + ': ' : '') + String((e && e.message) || e);
      rec.elapsed_ms = Date.now() - s;
      throw e;
    }
  };
};

/* everything asserted here is painted text; data-* is collected only as a cross-check */
const SCREEN = () => {
  const txt = (el) => (el ? el.innerText : null);
  const kind = document.querySelector('[data-testid="plan-ai-detail-kind"]');
  const reason = document.querySelector('[data-testid="plan-ai-reason"]');
  const toggle = document.querySelector('[data-testid="plan-ai-detail-toggle"]');
  const live = document.querySelector('[data-testid="plan-ai-live"]');
  const body = document.body ? document.body.innerText : '';
  return {
    result_card: txt(document.querySelector('[data-testid="plan-ai-result"]')),
    detail_toggle_present: !!toggle,
    detail_open: (function () { const d = document.querySelector('details.plan-ai-detail'); return d ? d.open : null; })(),
    reason_label_painted: txt(kind),
    reason_value_painted: txt(reason),
    reason_label_testid: kind ? kind.getAttribute('data-testid') : null,
    cross_check_data_reason_origin: kind ? kind.getAttribute('data-reason-origin') : null,
    cross_check_data_result_tone: (function () {
      const el = document.querySelector('[data-testid="plan-ai-result"]');
      return el ? el.getAttribute('data-result-tone') : null;
    })(),
    elapsed_line: live ? txt(live.querySelector('[data-testid="plan-ai-elapsed"]')) : null,
    deadline_sentence_on_screen: /等了\s*\d+\s*秒|No answer from this server in/.test(body),
    submit_visible: !!document.querySelector('[data-testid="hub-plan-with-ai"]'),
    result_card_html: (function () {
      const el = document.querySelector('[data-testid="plan-ai-result"]');
      return el ? el.outerHTML.slice(0, 900) : null;
    })(),
    sheet_region_text: (function () {
      const el = document.querySelector('[data-testid="plan-ai-sheet"]');
      return el ? el.innerText.slice(0, 900) : null;
    })(),
    details_elements_present: document.querySelectorAll('details').length,
  };
};

async function openSheet(page) {
  await page.goto('http://127.0.0.1:' + PORT + '/', { waitUntil: 'load', timeout: 60000 });
  const hub = page.locator('[data-testid="hub-plan-with-ai"]');
  const ok = await hub.waitFor({ state: 'visible', timeout: 25000 }).then(() => true).catch(() => false);
  if (!ok) return { hub_reached: false, screen: await page.evaluate(SCREEN) };
  await hub.click();
  await page.locator('[data-testid="plan-ai-input"]').waitFor({ state: 'visible', timeout: 15000 });
  await page.locator('[data-testid="plan-ai-input"]').fill(TEXT);
  return { hub_reached: true };
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                            hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  await context.addInitScript(INSTRUMENT, JOURNEY);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push({ at: Date.now(), name: e && e.name, text: String((e && e.message) || e).slice(0, 300) }));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push({ at: Date.now(), console: m.type(), text: m.text().slice(0, 300) }); });
  const opened = await openSheet(page);
  if (!opened.hub_reached) {
    fs.writeFileSync(OUT + '/cell_' + stage + '_' + RUN + '.json',
                    JSON.stringify({ stage, run_id: RUN, hub_reached: false, opened }, null, 1), 'utf-8');
    await browser.close();
    return console.log('HUB NOT REACHED - nothing measured');
  }
  if (process.env.NEED_LOCK === '1') {
    fs.writeFileSync(OUT + '/sheet_ready.flag', String(Date.now()));
    const flag = OUT + '/lock_armed.flag';
    const w0 = Date.now();
    while (!fs.existsSync(flag)) {
      if (Date.now() - w0 > 120000) throw new Error('lock flag never appeared');
      await sleep(200);
    }
  }
  const t0 = Date.now();
  await page.locator('[data-testid="plan-ai-submit"]').click();
  let firstDeadlineLine = null;
  const timeline = [];
  const postSettle = [];
  for (;;) {
    const legs = await page.evaluate(() => window.__legs);
    const posts = legs.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD');
    const s = await page.evaluate(SCREEN);
    const ms = Date.now() - t0;
    if (s.deadline_sentence_on_screen && !firstDeadlineLine) {
      firstDeadlineLine = { ms, line: (s.result_card || '').split('\n').find((x) => /等了\s*\d+\s*秒/.test(x)) || null };
      await page.screenshot({ path: OUT + '/shots_' + RUN + '-' + stage + '-deadline.png' });
    }
    if (s.detail_toggle_present && !s.detail_open) {
      // the 技术详情 region is a closed <details>: its text is not painted, so open it before reading
      await page.locator('[data-testid="plan-ai-detail-toggle"]').click().catch(() => {});
    }
    timeline.push({ ms, tone: s.cross_check_data_result_tone, label: s.reason_label_painted,
                    value: s.reason_value_painted, counter: s.elapsed_line,
                    card: (s.result_card || '').replace(/s+/g, ' ').slice(0, 64) });
    const settled = posts.find((p) => p.status !== undefined || p.client_error);
    if (settled && ms > 2500) {
      // keep watching: a later re-render is allowed to CHANGE the sentence, and that is itself the reading
      for (let k = 0; k < 16; k++) {
        await sleep(500);
        const s2 = await page.evaluate(SCREEN);
        const legs2 = await page.evaluate(() => window.__legs);
        postSettle.push({ ms: Date.now() - t0, card: (s2.result_card || '').split(String.fromCharCode(10)).join(' ').slice(0, 70),
                          label: s2.reason_label_painted, value: s2.reason_value_painted,
                          details: s2.details_elements_present,
                          write_legs: legs2.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD').length });
      }
      break;
    }
    if (ms > CAP) break;
    await sleep(250);
  }
  const legs = await page.evaluate(() => window.__legs);
  const screen = await page.evaluate(SCREEN);
  await page.screenshot({ path: OUT + '/shots_' + RUN + '-' + stage + '-end.png' });
  const posts = legs.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD');
  const out = { stage, run_id: RUN, port: PORT, measured_on: state.measured_on,
                bundle_sha256: BUNDLE_SHA, bundle_asset: BUNDLE_ASSET, port_override_used: !!process.env.PORT_OVERRIDE,
                journey_id: JOURNEY, request_text: TEXT, hub_reached: true,
                tap_ms_wall: new Date(t0).toISOString(),
                write_legs: posts, all_api_legs: legs.filter((l) => l.api),
                first_client_deadline_line: firstDeadlineLine,
                screen_after_open_details: screen,
                screen_states_observed: timeline.filter((r, i, a) => !i || r.label !== a[i - 1].label || r.value !== a[i - 1].value || r.card !== a[i - 1].card),
                timeline_points: timeline.length, cap_ms: CAP, page_errors_and_console: errors,
                screen_after_settle_watch: postSettle[postSettle.length - 1] || null,
                settle_watch_states: postSettle.filter((r, i, a) => !i || r.card !== a[i - 1].card || r.label !== a[i - 1].label || r.value !== a[i - 1].value) };  fs.writeFileSync(OUT + '/cell_' + stage + '_' + RUN + '.json', JSON.stringify(out, null, 1), 'utf-8');
  console.log(JSON.stringify({ stage, legs: posts.map((p) => ({ u: p.url.split('/').pop(), s: p.status,
    ct: p.content_type, b: p.bytes, ms: p.elapsed_ms, code: p.server_envelope && p.server_envelope.error_code,
    msg: p.server_envelope && p.server_envelope.error_message ? p.server_envelope.error_message.slice(0, 60) : null })),
    label: screen.reason_label_painted, value: (screen.reason_value_painted || '').slice(0, 70),
    deadline: firstDeadlineLine }, null, 1));
  await browser.close();
}

run().catch((e) => { console.log('ERROR ' + String(e).slice(0, 300)); process.exit(1); });
