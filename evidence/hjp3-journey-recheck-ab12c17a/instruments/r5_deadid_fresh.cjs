/* Re-measure baseline item ② (a journey id that does not exist) in a FRESH browser context on `ab12c17a`.

Why this file exists: my single allowed re-run of the journey (`r5_recheck.cjs`) opened /journey/<dead id> in the
SAME context it had just used to fill and advance the wizard, and it painted 287 characters where the previous
generation painted 158 from a clean context. That difference is confounded by my own carry-over, so it is not a
product reading. This pass does one navigation and nothing else: no typing, no clicks, no submit, no wizard.

It also fixes a second flaw of the previous instrument: attribute values were hashed as the string
"deferred_to_node_side" instead of over the bytes, so this pass hashes them for real and keeps the plain value only
for `data-*` anchor names, which are DOM contract words rather than server payload.

Read-only against the deployed chain.
Usage: node r5_deadid_fresh.cjs <outDir>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_0323walk_0926');
const CHAIN = 'http://127.0.0.1:4781';
const DEAD = '00000000-0000-0000-0000-000000000000';
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const out = { started_at: new Date().toISOString(), chain: CHAIN, url_asked: CHAIN + '/journey/' + DEAD,
                clicks: 0, keystrokes: 0, legs: [], };
  const browser = await chromium.launch({ headless: true });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  page.on('response', (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    out.legs.push({ url: r.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: r.request().method(),
                    status: r.status(), ct: r.headers()['content-type'] || null });
  });
  page.on('requestfailed', (rq) => {
    if (rq.url().indexOf('/api/') < 0) return;
    out.legs.push({ url: rq.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: rq.method(), status: null,
                    failure: (rq.failure() && rq.failure().errorText) || 'failed' });
  });

  await page.goto(out.url_asked, { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3500);

  out.before_opening_details = await page.evaluate(() => ({
    url: location.href, inner_len: (document.body.innerText || '').length,
    text_content_len: (document.body.textContent || '').length,
    details_count: document.querySelectorAll('details').length,
    buttons: Array.prototype.slice.call(document.querySelectorAll('button')).map((b) => (b.innerText || '').trim().slice(0, 28)),
    localStorage_keys: Object.keys(localStorage),
    session_contains_a_journey_id: (function () {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (/citynexus.*journey/i.test(k)) return k;
      }
      return null;
    })()
  }));
  out.painted_before = (await page.evaluate(() => document.body.innerText || '')).slice(0, 900);

  const opened = await page.evaluate(() => {
    const ds = Array.prototype.slice.call(document.querySelectorAll('details'));
    ds.forEach((d) => { d.open = true; });
    const ex = /Traceback|Exception|\bError\b|TypeError|RangeError|undefined is not|cannot read propert/i;
    const hits = [];
    for (const n of document.querySelectorAll('*')) {
      for (const a of Array.prototype.slice.call(n.attributes || [])) {
        if (['style', 'src', 'href', 'd', 'class'].includes(a.name)) continue;
        if (a.value && ex.test(String(a.value))) {
          hits.push({ tag: n.tagName.toLowerCase(), attr: a.name, value_len: String(a.value).length,
                      raw_value_for_node_side_hashing: String(a.value) });
        }
      }
    }
    const body = document.body.innerText || '';
    const tc = document.body.textContent || '';
    return { url: location.href, inner_len: body.length, text_content_len: tc.length,
             details_count: ds.length, exception_in_text: ex.test(body), attr_hits: hits,
             tail_lines: body.split('\n').filter(Boolean).slice(-4),
             carries_my_filled_wizard_values: /天津站|天津滨海国际机场|CNY 3000/.test(body) };
  });
  /* the attribute values are hashed here, on the Node side, and the raw strings are dropped rather than
     published - a value that reads like an exception must not become evidence text (Q64 / Q71) */
  opened.attr_hits.forEach((h) => {
    h.value_sha256 = SHA(Buffer.from(h.raw_value_for_node_side_hashing, 'utf8'));
    h.is_data_attribute = h.attr.indexOf('data-') === 0;
    delete h.raw_value_for_node_side_hashing;
  });
  out.after_opening_details = opened;
  out.painted_after = (await page.evaluate(() => document.body.innerText || '')).slice(0, 900);

  const png = path.join(OUT, 'RC_4_dead_id_fresh.png');
  await page.screenshot({ path: png });
  out.screenshot = { file: path.basename(png), exists: fs.existsSync(png),
                     bytes: fs.existsSync(png) ? fs.statSync(png).size : 0, sha256: SHA(fs.readFileSync(png)) };
  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r5_deadid_fresh.json'), JSON.stringify(out, null, 1));
  const raw = JSON.parse(JSON.stringify(out));
  console.log(JSON.stringify({ inner_len: raw.after_opening_details.inner_len,
    text_content_len: raw.after_opening_details.text_content_len, details: raw.after_opening_details.details_count,
    exception: raw.after_opening_details.exception_in_text, carries_filled_values:
      raw.after_opening_details.carries_my_filled_wizard_values,
    tail: raw.after_opening_details.tail_lines, buttons: raw.before_opening_details.buttons,
    ls_keys: raw.before_opening_details.localStorage_keys, legs: raw.legs,
    shot: raw.screenshot }, null, 1));
  await browser.close();
})().catch((e) => { console.error('DEADID FRESH FAILED: ' + String((e && e.message) || e)); process.exit(9); });
