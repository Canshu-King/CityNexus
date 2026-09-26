/* One pass on the newest phone generation, measuring exactly the two things I listed as "cannot do".

The commander re-cut the bundle again (`index-D6IOFaQS.js`) and asked for a single re-run with my previous two
user-blocked items treated as a baseline: ① can step 3's 确认创建 actually create a journey now, and ② what does the
screen say for a journey id that does not exist. Nothing else is re-measured, no verdict is asserted, and the
node I press is recorded because last time `getByText` handed me a step-dot wearing the same words as the button.

Read-only against the deployed chain; the only thing authored here is screenshots and a JSON of readings.
Usage: node r5_recheck.cjs <outDir>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_0323walk_0926');
const CHAIN = 'http://127.0.0.1:4781';
const DEAD = '00000000-0000-0000-0000-000000000000';
fs.mkdirSync(OUT, { recursive: true });
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');

async function painted(page) {
  return await page.evaluate(() => {
    const t = (n) => (n.innerText || n.textContent || '').trim();
    const ds = Array.prototype.slice.call(document.querySelectorAll('details'));
    ds.forEach((d) => { d.open = true; });
    const ex = /Traceback|Exception|\bError\b|TypeError|RangeError|undefined is not|cannot read propert/i;
    const attrHits = [];
    for (const n of document.querySelectorAll('*')) {
      for (const a of Array.prototype.slice.call(n.attributes || [])) {
        if (['style', 'src', 'href', 'd', 'class'].includes(a.name)) continue;
        if (a.value && ex.test(String(a.value))) {
          attrHits.push({ tag: n.tagName.toLowerCase(), attr: a.name, len: String(a.value).length,
                          sha256: 'deferred_to_node_side' });
        }
      }
    }
    const body = document.body ? document.body.innerText : '';
    return { url: location.href, text: body, buttons: Array.prototype.slice.call(document.querySelectorAll('button'))
      .map((b) => ({ text: t(b).slice(0, 28), disabled: !!b.disabled,
                     top: Math.round(b.getBoundingClientRect().top), cls: String(b.className).slice(0, 40) })),
      details_count: ds.length, attr_hits: attrHits,
      exception_in_text: ex.test(body) };
  });
}
async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), exists: fs.existsSync(p), bytes: fs.existsSync(p) ? fs.statSync(p).size : 0,
           sha256: SHA(fs.readFileSync(p)) };
}

(async () => {
  const out = { started_at: new Date().toISOString(), chain: CHAIN, viewport: { width: 390, height: 844 },
                legs: [], cells: {} };
  const browser = await chromium.launch({ headless: true });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  page.on('response', (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    out.legs.push({ url: r.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: r.request().method(),
                    status: r.status(), ct: r.headers()['content-type'] || null,
                    req_bytes: (r.request().postData() || '').length });
  });
  page.on('requestfailed', (rq) => {
    if (rq.url().indexOf('/api/') < 0) return;
    out.legs.push({ url: rq.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: rq.method(), status: null,
                    failure: (rq.failure() && rq.failure().errorText) || 'failed' });
  });

  /* binding: what the chain serves this minute */
  const idx = await (await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 60000 })).text();
  const asset = (idx.match(/"\/(assets\/index-[^"]+\.js)"/) || [])[1] || null;
  let ab = null;
  if (asset) ab = await (await page.request.get(CHAIN + '/' + asset)).body();
  out.binding = { served_index_bytes: idx.length, asset_named_by_the_served_page: asset,
                  asset_bytes: ab ? ab.length : null, asset_sha256_64_hex: ab ? SHA(ab) : null };

  /* ① the baseline item: fill like a traveller, then press the real submit button */
  await page.locator('input[placeholder^="例如"]').first().fill('天津');
  const places = page.locator('input[placeholder*="机场"]');
  for (let i = 0; i < await places.count(); i++) await places.nth(i).fill(i ? '天津滨海国际机场' : '天津站');
  const dts = page.locator('input[type="datetime-local"]');
  for (let i = 0; i < await dts.count(); i++) await dts.nth(i).fill(i ? '2026-10-03T20:00' : '2026-10-02T10:00');
  for (const i of [1, 2]) {
    await page.getByRole('button', { name: '下一步', exact: true }).first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(1500);
  }
  const atReview = await painted(page);
  const submit = atReview.buttons.filter((b) => b.text === '确认创建');
  const legs_before = out.legs.length;
  const press = submit.length ? await page.getByRole('button', { name: '确认创建', exact: true }).first()
    .click({ timeout: 6000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 50))
    : 'no_button_named_确认创建';
  await page.waitForTimeout(4000);
  const afterConfirm = await painted(page);
  let stored = null;
  try { stored = await page.evaluate(() => localStorage.getItem('citynexus.v8.journey_id')); } catch (e) { stored = 'READ_FAILED'; }
  out.cells.C1_confirm_create = {
    node_pressed: submit, press_result: press,
    legs_after_press: out.legs.slice(legs_before),
    painted_at_review_capped: atReview.text.slice(0, 700),
    painted_after_capped: afterConfirm.text.slice(0, 700),
    still_on_wizard: /还需要填写|确认创建/.test(afterConfirm.text),
    stored_journey_id: stored,
    exception_in_text_after_opening_details: afterConfirm.exception_in_text,
    attribute_hits: afterConfirm.attr_hits,
    details_count: afterConfirm.details_count,
    screenshots: { review: await shot(page, 'RC_1_review'), after: await shot(page, 'RC_2_after_confirm') } };

  /* ② the other baseline item: a journey id that does not exist */
  await page.unroute('**/api/v1/**');
  const lb = out.legs.length;
  await page.goto(CHAIN + '/journey/' + DEAD, { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3500);
  const dead = await painted(page);
  out.cells.C2_dead_journey_id = {
    url_asked: CHAIN + '/journey/' + DEAD, url_rendered: dead.url,
    painted_capped: dead.text.slice(0, 700), painted_len: dead.text.length,
    buttons: dead.buttons.map((b) => b.text), exception_in_text_after_opening_details: dead.exception_in_text,
    attribute_hits: dead.attr_hits, legs_this_cell: out.legs.slice(lb),
    screenshot: await shot(page, 'RC_3_dead_id') };

  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r5_recheck_raw.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ binding: out.binding,
    C1: { press: out.cells.C1_confirm_create.press_result, legs: out.cells.C1_confirm_create.legs_after_press,
          still_on_wizard: out.cells.C1_confirm_create.still_on_wizard, stored: out.cells.C1_confirm_create.stored_journey_id,
          tail: out.cells.C1_confirm_create.painted_after_capped.split('\n').filter(Boolean).slice(-3) },
    C2: { painted_len: out.cells.C2_dead_journey_id.painted_len,
          tail: out.cells.C2_dead_journey_id.painted_capped.split('\n').filter(Boolean).slice(-3),
          legs: out.cells.C2_dead_journey_id.legs_this_cell } }, null, 1));
  await browser.close();
})().catch((e) => { console.error('RECHECK FAILED: ' + String((e && e.message) || e)); process.exit(9); });
