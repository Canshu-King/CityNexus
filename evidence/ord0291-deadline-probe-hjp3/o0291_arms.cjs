/* ORD-0291 T-c constant probe - the arms, measured durably.
 *
 *   node o0291_arms.cjs read  X      8487 12000     (silent origin; when does the read leg self-terminate?)
 *   node o0291_arms.cjs write Xhalf  8485  6000     (healthy backend + held write lock; does a WRITE leg move?)
 *
 * One page context per invocation, fresh profile => no Service Worker / CacheStorage carried between arms.
 * Every leg the page sends is wrapped so its method, status, elapsed time and error NAME are recorded from
 * the client's own seat; the screen assertions read rendered innerText, never data-* attributes.
 */
const { chromium } = require('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend/node_modules/playwright');
const fs = require('fs');

const OUT = 'D:/moodle/_hjp3_0291_0925';
const JOURNEY = '91f78c9b-b768-46c9-a62e-4ac09b6609da';
const REQUEST_TEXT = '想傍晚在老城慢慢走一圈，别太赶';

const stage = process.argv[2];
const arm = process.argv[3];
const port = Number(process.argv[4]);
const constantMs = Number(process.argv[5]);
const runId = process.env.RUN_ID || 'O0291-manual';
const TAG = process.env.TAG ? '_' + process.env.TAG : '';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const INSTRUMENT = (journey) => {
  try { localStorage.setItem('citynexus.v8.journey_id', journey); } catch (e) { /* private mode */ }
  window.__legs = [];
  const t0 = Date.now();
  const orig = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const rec = {
      url, method, api: url.indexOf('/api/') >= 0,
      sent_ms_since_load_start: Date.now() - t0,
      sent_wall: new Date().toISOString(),
      has_signal: !!(init && init.signal),
      request_body: (init && typeof init.body === 'string') ? init.body.slice(0, 160) : null,
      request_headers_idempotency_key: (init && init.headers && (init.headers['Idempotency-Key'] || init.headers['idempotency-key'])) || null,
    };
    window.__legs.push(rec);
    const s = Date.now();
    try {
      const res = await orig.apply(window, arguments);
      rec.status = res.status;
      rec.content_type = res.headers.get('content-type');
      try {
        const txt = await res.clone().text();
        rec.bytes = txt.length;
        rec.body_head = txt.slice(0, 200);
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

/* the deadline sentence, as the traveller reads it (zh template is `等了 ${X/1000} 秒，这台服务器一个字也没回答`) */
const SCREEN = () => {
  const text = document.body ? document.body.innerText : '';
  const line = (text.split('\n').find((l) => /等了\s*\d+\s*秒|No answer from this server in/.test(l)) || null);
  const shown = line ? (line.match(/等了\s*(\d+)\s*秒|in (\d+) seconds/) || []).slice(1, 3).filter(Boolean)[0] || null : null;
  return {
    deadline_line: line,
    seconds_shown: shown === undefined ? null : shown,
    says_no_answer: /一个字也没回答|No answer from this server/.test(text),
    elapsed_counter: (function () {
      const el = document.querySelector('[data-testid="plan-ai-live"]');
      const p = el ? el.querySelector('[data-testid="plan-ai-elapsed"]') : null;
      return p ? p.innerText : null;
    })(),
    result_card: (function () {
      const el = document.querySelector('[data-testid="plan-ai-result"]');
      return el ? el.innerText : null;
    })(),
    server_reason_rendered: (function () {
      const el = document.querySelector('[data-testid="plan-ai-reason"]');
      return el ? el.innerText : null;
    })(),
    submit_visible: !!document.querySelector('[data-testid="hub-plan-with-ai"]'),
  };
};

async function runRead(page) {
  const t0 = Date.now();
  await page.goto('http://127.0.0.1:' + port + '/', { waitUntil: 'commit', timeout: 60000 });
  const budgetMs = 30000;
  let first = null;
  const timeline = [];
  while (Date.now() - t0 <= budgetMs) {
    const s = await page.evaluate(SCREEN);
    const ms = Date.now() - t0;
    if (s.deadline_line) {
      if (!first) {
        first = { ms, seconds_shown: s.seconds_shown, deadline_line: s.deadline_line };
        await page.screenshot({ path: OUT + '/shots_' + runId + '-' + arm + '-read-trigger' + TAG + '.png' });
      }
    }
    timeline.push({ ms, has_line: !!s.deadline_line, counter: s.elapsed_counter });
    if (first && ms - first.ms >= 3000) break;
    await sleep(200);
  }
  const legs = await page.evaluate(() => window.__legs);
  const end = await page.evaluate(SCREEN);
  await page.screenshot({ path: OUT + '/shots_' + runId + '-' + arm + '-read-end' + TAG + '.png' });
  return {
    arm, port, constant_ms: constantMs, face_serves: 'dist_' + arm, origin: 'silent 127.0.0.1:8595 (accepts, never answers)',
    first_trigger: first,
    trigger_moves_expected_seconds: constantMs / 1000,
    stable_3s_later: !!(first && end.deadline_line),
    api_legs: legs.filter((l) => l.api),
    hung_legs: legs.filter((l) => l.api && l.status === undefined && l.client_error === undefined).length,
    timeline_sample: timeline.filter((t) => t.has_line).slice(0, 3),
    timeline_points: timeline.length,
  };
}

async function runWrite(page) {
  await page.goto('http://127.0.0.1:' + port + '/', { waitUntil: 'load', timeout: 60000 });
  const hub = page.locator('[data-testid="hub-plan-with-ai"]');
  const reached = await hub.waitFor({ state: 'visible', timeout: 25000 }).then(() => true).catch(() => false);
  if (!reached) {
    const s = await page.evaluate(SCREEN);
    return { arm, port, hub_reached: false, screen: s };
  }
  await hub.click();
  await page.locator('[data-testid="plan-ai-input"]').waitFor({ state: 'visible', timeout: 15000 });
  await page.locator('[data-testid="plan-ai-input"]').fill(REQUEST_TEXT);
  /* on the write-lock rig the hub must render before the lock is armed, so the driver signals the window;
     on the selective origin there is nothing to wait for - the origin itself never answers the POST */
  const needsWindow = !process.env.NO_LOCK;
  let armedWaitMs = 0;
  if (needsWindow) {
    fs.writeFileSync(OUT + '/sheet_ready.flag', String(Date.now()));
    const flag = OUT + '/lock_armed.flag';
    const flagWait0 = Date.now();
    while (!fs.existsSync(flag)) {
      if (Date.now() - flagWait0 > 90000) throw new Error('lock flag never appeared');
      await sleep(200);
    }
    armedWaitMs = Date.now() - flagWait0;
  }
  const t0 = Date.now();
  await page.locator('[data-testid="plan-ai-submit"]').click();
  let card = null;
  const timeline = [];
  const budgetMs = Number(process.env.CAP_MS || 70000);
  for (;;) {
    const legs = await page.evaluate(() => window.__legs);
    const posts = legs.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD');
    const s = await page.evaluate(SCREEN);
    const ms = Date.now() - t0;
    if (s.deadline_line && !card) {
      card = { ms, seconds_shown: s.seconds_shown, deadline_line: s.deadline_line };
      await page.screenshot({ path: OUT + '/shots_' + runId + '-' + arm + '-write-deadline-card' + TAG + '.png' });
    }
    timeline.push({ ms, counter: s.elapsed_counter, posts_settled: posts.filter((p) => p.status !== undefined || p.client_error).length });
    const settled = posts.find((p) => p.status !== undefined || p.client_error);
    if (settled && ms > 3000) break;
    if (ms > budgetMs) break;
    await sleep(250);
  }
  const legs = await page.evaluate(() => window.__legs);
  const end = await page.evaluate(SCREEN);
  await page.screenshot({ path: OUT + '/shots_' + runId + '-' + arm + '-write-end' + TAG + '.png' });
  const posts = legs.filter((l) => l.api && l.method !== 'GET' && l.method !== 'HEAD');
  return {
    arm, port, constant_ms: constantMs, face_serves: 'dist_' + arm,
    hub_reached: true, request_text: REQUEST_TEXT, request_text_length: REQUEST_TEXT.length,
    rig: process.env.RIG || 'write-lock rig (backend 127.0.0.1:8493 with a bounded write-lock window)',
    ms_from_fill_to_lock_window: armedWaitMs,
    write_legs: posts,
    deadline_card_during_flight: card,
    counter_at_end: end.elapsed_counter,
    result_card: end.result_card,
    server_reason_rendered: end.server_reason_rendered,
    max_counter_seen: timeline.reduce((a, t) => Math.max(a, parseInt(String(t.counter || '').replace(/\D/g, '')) || 0), 0),
    timeline_points: timeline.length,
    timeline_tail: timeline.slice(-3),
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, hasTouch: true,
    isMobile: false, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
  });
  await context.addInitScript(INSTRUMENT, JOURNEY);
  const page = await context.newPage();
  const reading = stage === 'read' ? await runRead(page) : await runWrite(page);
  reading.run_id = runId;
  reading.run_tag = process.env.TAG || '(untagged)';
  reading.stage = stage;
  reading.measured_at = new Date().toISOString();
  reading.viewport = '390x844 zh-CN';
  const f = OUT + '/arm_readings_' + stage + '_' + arm + TAG + '.json';
  fs.writeFileSync(f, JSON.stringify(reading, null, 1), 'utf-8');
  console.log('WROTE ' + f);
  console.log(JSON.stringify({
    stage, arm, first_trigger: reading.first_trigger || null,
    deadline_card_during_flight: reading.deadline_card_during_flight || null,
    write_leg_status: (reading.write_legs || []).map((p) => ({ u: p.url.split('/').pop(), s: p.status, ms: p.elapsed_ms, e: p.client_error })),
    hub_reached: reading.hub_reached,
  }, null, 1));
  await browser.close();
})();
