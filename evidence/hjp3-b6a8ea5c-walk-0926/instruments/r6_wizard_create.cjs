/* Cell B on b6a8ea5c: walk the three-step wizard like a traveller, press 确认创建, and find out what the failure
screen is allowed to say now that a real backend answers.

Three things are read because the commander asked for exactly them: whether the press reaches a journey at all,
whether the screen now carries a SERVER-issued receipt number (ORD-0332's `CNX-…` shape) rather than "HTTP 500" or
a client-invented id, and whether that number is the same one the server sent for that very request. The pairing is
done inside one leg: the response body of the failing POST is read for the single field
`error.error_receipt_id`, and only that identifier plus status/content-type/byte counts are written to the
artefact - no server sentence, no raw body (UI_EVIDENCE_EXPOSURE_GATE_V1).

Two lessons from my own previous pass are built in: the review screen is photographed BEFORE the press (last time
both shots followed it), and the node being pressed is recorded by role, text, disabled state and position.

Lane: own headless Chromium, 390x844@3, touch, zh-CN, fresh context, no proxy; the tunnel password goes in as
httpCredentials only. The only thing submitted is my own traveller attempt on my own device state.
Usage: node r6_wizard_create.cjs <outDir>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_b6a8_0926');
const BASE = 'https://administrator-personality-supervisor-peers.trycloudflare.com';
const AUTH = fs.readFileSync('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt', 'utf8').trim().split(/\s+/);
const RECEIPT = /\bCNX-[A-Z0-9]{6,12}\b/g;
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

async function readScreen(page) {
  return await page.evaluate(() => {
    const ex = /Traceback|Exception|\bError\b|TypeError|RangeError|undefined is not|cannot read propert/i;
    const body = document.body ? (document.body.innerText || '') : '';
    const hits = [];
    for (const n of document.querySelectorAll('*')) {
      for (const a of Array.from(n.attributes || [])) {
        if (['style', 'src', 'href', 'd', 'class'].includes(a.name)) continue;
        if (a.value && ex.test(String(a.value))) {
          hits.push({ tag: n.tagName.toLowerCase(), attr: a.name, value_len: String(a.value).length,
                      raw_for_node_side_hashing: String(a.value) });
        }
      }
    }
    return { url: location.href, text_len: body.length, body_text_head: body.slice(0, 1600),
             receipts_on_screen: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
             buttons: Array.from(document.querySelectorAll('button')).map((b) => ({
               text: (b.innerText || '').trim().slice(0, 30), disabled: !!b.disabled,
               top: Math.round(b.getBoundingClientRect().top), cls: String(b.className).slice(0, 40) })),
             links: Array.from(document.querySelectorAll('a')).map((a) => ({ text: (a.innerText || '').trim().slice(0, 24),
               href: a.getAttribute('href') })).filter((x) => x.text),
             details_count: document.querySelectorAll('details').length,
             details_summaries: Array.from(document.querySelectorAll('details summary')).map((s) => (s.innerText || '').trim().slice(0, 60)),
             aria_live: Array.from(document.querySelectorAll('[aria-live]')).map((n) => ({
               level: n.getAttribute('aria-live'), text: (n.innerText || '').trim().slice(0, 200) })),
             exception_in_text: ex.test(body), attr_hits: hits,
             ls: Object.keys(localStorage).map((k) => ({ key: k, len: (localStorage.getItem(k) || '').length })) };
  });
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, viewport: { width: 390, height: 844 },
                keystrokes: 'typed into four fields by me', legs: [], cells: {} };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  const page = await ctx.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let rb = null;
    try { rb = (await r.body()).length; } catch (e) { rb = 'READ_FAILED'; }
    const leg = { at: new Date().toISOString(), url: r.url().replace(/^https?:\/\/[^/]+/, ''),
                  m: r.request().method(), status: r.status(), ct: r.headers()['content-type'] || null,
                  req_bytes: (r.request().postData() || '').length, resp_bytes: rb,
                  idempotency_key_sent: !!r.request().headers()['idempotency-key'] };
    if (leg.status >= 400 && /json/.test(leg.ct || '')) {
      // same-request pairing: the identifier the server put in THIS response, read off the same leg the
      // browser sent - no replay, no second request. Only the identifier field is kept, never a sentence.
      try { const j = JSON.parse(Buffer.from(await r.body()).toString('utf8'));
            leg.server_receipt_id = (j.error && j.error.error_receipt_id) || j.error_receipt_id || null;
            leg.server_code_field = (j.error && j.error.code) || j.code || null; }
      catch (e) { leg.server_receipt_id = 'NOT_JSON'; }
    }
    out.legs.push(leg);
  });

  await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(2500);
  out.served_asset = await page.evaluate(() => (document.querySelector('script[src*="assets/index-"]') || {}).src || null);

  await page.locator('input[placeholder^="例如"]').first().fill('天津');
  const places = page.locator('input[placeholder*="机场"], input[placeholder*="站"], input[placeholder*="地点"]');
  const pc = await places.count();
  out.place_field_count = pc;
  for (let i = 0; i < pc; i++) await places.nth(i).fill(i === 0 ? '天津站' : '天津滨海国际机场').catch(() => {});
  const dts = page.locator('input[type="datetime-local"]');
  for (let i = 0; i < await dts.count(); i++) await dts.nth(i).fill(i ? '2026-10-03T20:00' : '2026-10-02T10:00');
  const advanced = page.getByRole('button', { name: '高级设置', exact: false }).first();
  if (await advanced.count()) await advanced.click({ timeout: 3000 }).catch(() => {});
  const budgets = page.locator('input[type="number"], input[inputmode="numeric"]');
  for (let i = 0; i < await budgets.count(); i++) {
    const v = await budgets.nth(i).inputValue().catch(() => '');
    if (!v) await budgets.nth(i).fill(i ? '1000' : '3000').catch(() => {});
  }
  out.advance = [];
  for (const i of [1, 2]) {
    const before = await page.evaluate(() => (document.body.innerText || '').length);
    const r = await page.getByRole('button', { name: '下一步', exact: true }).first()
      .click({ timeout: 6000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 60));
    await page.waitForTimeout(1500);
    const after = await page.evaluate(() => (document.body.innerText || '').length);
    out.advance.push({ press: r, text_len_before: before, text_len_after: after, changed: before !== after });
  }
  const review = await readScreen(page);
  review.attr_hits.forEach((h) => { h.value_sha256 = SHA(Buffer.from(h.raw_for_node_side_hashing, 'utf8'));
                                    delete h.raw_for_node_side_hashing; });
  out.cells.B1_review_before_press = { text_len: review.text_len, buttons: review.buttons,
                                       details_count: review.details_count, receipts_on_screen: review.receipts_on_screen,
                                       ls: review.ls };
  out.shot_review = await shot(page, 'B1_review_before_press');

  const submit = review.buttons.filter((b) => b.text === '确认创建');
  out.cells.B2_node_pressed_candidates = submit;
  const lb = out.legs.length;
  const press = submit.length ? await page.getByRole('button', { name: '确认创建', exact: true }).first()
    .click({ timeout: 6000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 60))
    : 'no_button_named_确认创建';
  await page.waitForTimeout(9000);
  const after = await readScreen(page);
  after.attr_hits.forEach((h) => { h.value_sha256 = SHA(Buffer.from(h.raw_for_node_side_hashing, 'utf8'));
                                   delete h.raw_for_node_side_hashing; });
  const legsAfter = out.legs.slice(lb);
  const jid = await page.evaluate(() => localStorage.getItem('citynexus.v8.journey_id'));
  out.cells.B3_after_press = { press_result: press, legs: legsAfter, url_after: after.url,
                               text_len: after.text_len, body_text_head: after.body_text_head,
                               receipts_on_screen: after.receipts_on_screen, buttons: after.buttons,
                               links: after.links, details_count: after.details_count,
                               details_summaries: after.details_summaries, aria_live: after.aria_live,
                               exception_in_text: after.exception_in_text, attr_hits: after.attr_hits,
                               stored_journey_id: jid, ls: after.ls,
                               still_on_the_wizard: /还需要填写|确认创建|目的地与时间/.test(after.body_text_head) };
  out.shot_after = await shot(page, 'B2_after_confirm');
  /* open every fold so a sentence that hides inside one is read, not guessed at */
  const opened = await page.evaluate(() => {
    Array.from(document.querySelectorAll('details')).forEach((d) => { d.open = true; });
    const body = document.body.innerText || '';
    return { text_len: body.length, receipts: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
             tail: body.split('\n').filter(Boolean).slice(-10) };
  });
  out.cells.B4_after_opening_every_fold = opened;
  out.shot_opened = await shot(page, 'B3_after_opening_folds');

  /* same-request pairing, computed from the legs the browser itself recorded */
  out.pairing = legsAfter.filter((l) => l.status >= 400).map((l) => ({
    leg: [l.m, l.url, l.status, l.req_bytes, l.resp_bytes].join(' '),
    server_receipt_id_on_that_leg: l.server_receipt_id || null,
    server_code_field_on_that_leg: l.server_code_field || null,
    that_id_also_visible_on_screen: !!(l.server_receipt_id && after.receipts_on_screen.indexOf(l.server_receipt_id) >= 0) }));
  out.receipt_on_screen = after.receipts_on_screen;
  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r6_wizard_create.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ served_asset: (out.served_asset || '').split('/').pop(), advance: out.advance,
    press, legs_after_press: legsAfter.map((l) => [l.m, l.url, l.status, l.req_bytes, l.resp_bytes]),
    stored_journey_id: jid, still_on_wizard: out.cells.B3_after_press.still_on_the_wizard,
    receipts_on_screen: after.receipts_on_screen, details: after.details_count,
    pairing: out.pairing }, null, 1));
  console.log('AFTER TEXT (first 900):\n' + after.body_text_head.slice(0, 900));
  await browser.close();
})().catch((e) => { console.error('B FAILED: ' + String((e && e.message) || e)); process.exit(9); });
