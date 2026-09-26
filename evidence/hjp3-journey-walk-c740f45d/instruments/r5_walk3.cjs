/* HJ-P3 walkthrough take 3 - fills the form like a traveller, and opens 技术详情 before claiming anything.
 *
 * Two instrument faults from takes 1-2 are fixed here, because both would have produced a product claim out of
 * my own mistake:
 *   - the destination field's placeholder is 「例如：天津、东京、新加坡」; I selected on 城市 and filled nothing,
 *     then reported "the wizard does not advance". Now the selector is `input[placeholder^="例如"]` and the
 *     painted 「还需要填写…」 line is read out of the rendered text, not out of a DOM filter that missed it.
 *   - I read the page WITHOUT opening the collapsible 技术详情. A collapsed <details> paints nothing, so an
 *     "no exception text found" claim from that read is worthless. Every read here is taken twice: at rest, and
 *     after opening every details element.
 *
 * The claim I am actually testing is narrow and code-anchored: at this generation the sealed-demo handler
 * paints one fixed sentence for every thrown error (`trial.sealedUnreadable`), so I run the same click under
 * three different leg fates - refused, 500 with an empty text/plain body, and 200 whose JSON carries a canary -
 * and record, per fate, what the leg was and what the screen said.
 *
 * 0 product bytes touched; the only failures are manufactured inside my own browser context.
 * Usage: node r5_walk3.cjs <outDir>
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_0323walk_0926');
const CHAIN = 'http://127.0.0.1:4781';
const CANARY = 'CNXCANARY7788';
const CAP = 900;
fs.mkdirSync(OUT, { recursive: true });
const SHA = (s) => crypto.createHash('sha256').update(String(s)).digest('hex');
const PAT = { ex: 'Traceback|Exception|\\bError\\b|TypeError|RangeError|ReferenceError|undefined is not|cannot read propert|Failed to fetch',
              stack: '^\\s*at\\s+[\\w$.<>\\s]+\\(.+:\\d+:\\d+\\)', long: '[A-Za-z0-9_./:\\\\-]{120,}' };

async function read(page, canary) {
  const r = await page.evaluate((P) => {
    const ex = new RegExp(P.ex, 'i'), st = new RegExp(P.stack, 'm'), lm = new RegExp(P.long);
    const all = document.body ? document.body.innerText : '';
    const nodes = Array.prototype.slice.call(document.querySelectorAll('*'));
    const hits = [], attrHits = [], details = [];
    for (const n of nodes) {
      const own = Array.prototype.slice.call(n.childNodes).filter((c) => c.nodeType === 3)
        .map((c) => c.nodeValue).join('').trim();
      if (own && ex.test(own)) hits.push({ tag: n.tagName.toLowerCase(), cls: String(n.className).slice(0, 50), raw: own });
      for (const a of Array.prototype.slice.call(n.attributes || [])) {
        if (['style', 'src', 'href', 'd', 'class'].indexOf(a.name) >= 0) continue;
        const v = String(a.value || '');
        if (v && (ex.test(v) || lm.test(v))) attrHits.push({ tag: n.tagName.toLowerCase(), attr: a.name, raw: v });
      }
    }
    for (const d of Array.prototype.slice.call(document.querySelectorAll('details'))) {
      details.push({ open: !!d.open, summary: (d.querySelector('summary') || {}).innerText || null,
                     text_len_when_open: (d.innerText || '').trim().length });
    }
    return { url: location.href, inner: all, nodes: nodes.length, hits: hits.slice(0, 8),
             attrHits: attrHits.slice(0, 8), details: details, stack: st.test(all), long: lm.test(all),
             verbs: /重试|再试一次|换一座城市|稍后|换个说法|检查|继续|创建|新建/.test(all),
             need_line: (all.match(/还需要填写[^\n]*/) || [null])[0] };
  }, PAT);
  const seal = (o) => { const v = String(o.raw || ''); const q = { tag: o.tag, cls: o.cls, attr: o.attr };
                        delete q.raw; q.len = v.length; q.sha256 = SHA(v); return q; };
  return { url: r.url, inner_len: r.inner.length, nodes: r.nodes,
           painted_capped: r.inner.slice(0, CAP), painted_truncated: r.inner.length > CAP,
           painted_sha256_full: SHA(r.inner),
           need_line: r.need_line, action_verbs_present: r.verbs,
           details_elements: r.details, stack_frame: r.stack, long_machine_text: r.long,
           exception_in_text: r.hits.map(seal), exception_in_attributes: r.attrHits.map(seal),
           canary_in_text: canary ? r.inner.indexOf(canary) >= 0 : null,
           canary_in_attributes: canary ? r.attrHits.some((x) => String(x.raw).indexOf(canary) >= 0) : null };
}
async function openAllDetails(page) {
  return await page.evaluate(() => {
    const ds = Array.prototype.slice.call(document.querySelectorAll('details'));
    ds.forEach((d) => { d.open = true; });
    return ds.length;
  });
}
async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), exists: fs.existsSync(p), bytes: fs.existsSync(p) ? fs.statSync(p).size : 0 };
}
async function band(page) {
  return await page.evaluate(() => {
    const steps = document.querySelector('.trial-steps') || document.querySelector('[class*="trial-steps"]');
    const card = document.querySelector('.trial-card') || document.querySelector('[class*="trial-card"]');
    const dots = steps ? Array.prototype.slice.call(steps.querySelectorAll('[class*="trial-step"]'))
      .map((n) => ({ cls: String(n.className).slice(0, 48), text: (n.innerText || '').trim().slice(0, 24),
                     top: Math.round(n.getBoundingClientRect().top) })) : [];
    const r1 = steps ? steps.getBoundingClientRect() : null;
    const r2 = card ? card.getBoundingClientRect() : null;
    const cs = steps ? getComputedStyle(steps) : null;
    return { steps_found: !!steps, padding_bottom_px: cs ? parseFloat(cs.paddingBottom) : null,
             step_dots: dots.slice(0, 12), gap_steps_box_to_card_px: (r1 && r2) ? Math.round(r2.top - r1.bottom) : null,
             dot_row_top_px: r1 ? Math.round(r1.top) : null, card_top_px: r2 ? Math.round(r2.top) : null,
             visual_gap_dot_to_card_px: (dots.length && r2) ? Math.round(r2.top - dots[0].top) : null,
             viewport: window.innerHeight, scroll_overflow_px: document.documentElement.scrollHeight - window.innerHeight,
             card_visible_at_rest: !!r2 && r2.top < window.innerHeight };
  });
}
async function fillForm(page) {
  const acts = [];
  const dest = page.locator('input[placeholder^="例如"]').first();
  acts.push({ sel: 'input[placeholder^="例如"] (目的地)', found: await dest.count(), ok: false });
  if (await dest.count()) { await dest.fill('天津'); acts[acts.length - 1].ok = true; }
  const places = page.locator('input[placeholder*="机场"]');
  const np = await places.count();
  for (let i = 0; i < np; i++) await places.nth(i).fill(i ? '天津滨海国际机场' : '天津站').catch(() => {});
  const dts = page.locator('input[type="datetime-local"]');
  const nd = await dts.count();
  for (let i = 0; i < nd; i++) await dts.nth(i).fill(i ? '2026-10-03T20:00' : '2026-10-02T10:00').catch(() => {});
  acts.push({ places_filled: np, datetimes_filled: nd });
  return acts;
}
async function sealedUnderFate(page, ctx, fate, name) {
  const seen = [];
  await page.unroute('**/api/v1/**');
  if (fate === 'refused') await page.route('**/api/v1/**', (r) => r.abort('connectionrefused'));
  if (fate === 'empty500') await page.route('**/api/v1/**', (r) => r.fulfill({ status: 500,
                                                      contentType: 'text/plain; charset=utf-8', body: '' }));
  if (fate === 'canary200') await page.route('**/api/v1/**', (r) => r.fulfill({ status: 200,
                                        contentType: 'application/json', body: '{"detail":"' + CANARY + ' went wrong"}' }));
  const on = (rq) => { if (rq.url().indexOf('/api/v1/') >= 0) seen.push({ method: rq.method(), url: rq.url()
    .replace(/^http:\/\/127\.0\.0\.1:\d+/, '') }); };
  page.on('request', on);
  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(2000);
  await fillForm(page);
  await page.getByText('使用封存的演示行程').first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(2800);
  const atRest = await read(page, CANARY);
  const n = await openAllDetails(page);
  await page.waitForTimeout(500);
  const opened = await read(page, CANARY);
  const sh = await shot(page, name);
  page.off('request', on);
  return { fate: fate, leg_paths: seen, details_opened_by_me: n, at_rest: atRest, after_opening_details: opened,
           screenshot: sh };
}

(async () => {
  const out = { started_at: new Date().toISOString(), chain: CHAIN, viewport: { width: 390, height: 844 },
                canary: CANARY, cells: {} };
  const browser = await chromium.launch({ headless: true });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  out.legs = [];
  page.on('response', (r) => { if (r.url().indexOf('/api/') >= 0) out.legs.push({ url: r.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: r.request().method(), status: r.status(), ct: r.headers()['content-type'] || null }); });
  page.on('requestfailed', (rq) => { if (rq.url().indexOf('/api/') >= 0) out.legs.push({ url: rq.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: rq.method(), status: null, failure: (rq.failure() && rq.failure().errorText) || 'failed' }); });

  const resp = await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 60000 });
  const html = await resp.text();
  const asset = (html.match(/"\/(assets\/index-[^"]+\.js)"/) || [])[1] || null;
  const ab = asset ? await (await page.request.get(CHAIN + '/' + asset)).body() : null;
  out.generation_binding = { served_index_status: resp.status(), served_index_bytes: html.length,
                             asset_named_by_the_served_page: asset, asset_bytes: ab ? ab.length : null,
                             asset_sha256_64_hex: ab ? SHA(ab) : null };

  /* W1 - fill, then walk the three steps */
  const w1 = { at_rest: await read(page), band_at_rest: await band(page),
               shot_rest: await shot(page, 'W3_1_rest') };
  w1.fill = await fillForm(page);
  w1.after_fill = await read(page);
  w1.band_after_fill = await band(page);
  w1.shot_filled = await shot(page, 'W3_2_filled');
  w1.steps = [];
  for (let i = 1; i <= 3; i++) {
    const before = w1.steps.length ? w1.steps[w1.steps.length - 1].after : w1.after_fill;
    const clicked = await page.getByText('下一步').first().click({ timeout: 5000 }).then(() => true).catch(() => false);
    await page.waitForTimeout(1800);
    const after = await read(page);
    w1.steps.push({ press_next_returned: clicked, before_need_line: before.need_line, after: after,
                    advanced: before.inner_len !== after.inner_len || before.painted_sha256_full !== after.painted_sha256_full,
                    band: await band(page), shot: await shot(page, 'W3_3_next' + i) });
  }
  out.cells.W1_wizard_filled = w1;

  /* W2 - the sealed demo entry under three leg fates, details opened both times */
  out.cells.W2_sealed_demo_three_fates = {
    refused: await sealedUnderFate(page, ctx, 'refused', 'W3_4_fate_refused'),
    empty500: await sealedUnderFate(page, ctx, 'empty500', 'W3_5_fate_empty500'),
    canary200: await sealedUnderFate(page, ctx, 'canary200', 'W3_6_fate_canary200') };
  await page.unroute('**/api/v1/**');

  /* W3 - the chain's own natural state, no route touched by me */
  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const naturalRest = await read(page);
  await openAllDetails(page);
  out.cells.W3_natural_state_no_route = { at_rest: naturalRest,
                                          after_opening_details: await read(page),
                                          legs: out.legs.slice(-6), shot: await shot(page, 'W3_7_natural') };

  /* W4 - what is even reachable without a journey: the button inventory, not a claim about a route */
  out.cells.W4_reachable_surfaces_inventory = {
    visible_buttons: naturalRest.painted_capped.split('\n').filter((x) => x.trim()).slice(0, 40),
    inner_len: naturalRest.inner_len, note: 'no client-side router strings for /journey/<id> were found in the '
      + 'served bundle, so a dead stored id is not a reachable surface on this build; the list above is what a '
      + 'traveller can actually press right now' };

  /* the instrument's own two-way proof, this time including a collapsed-details trap */
  const leaky = await ctx.newPage();
  await leaky.setContent('<details><summary>技术详情</summary><p>TypeError: cannot read properties of null '
    + '(reading \'detail\')</p></details><div data-error-name="TypeError"></div>');
  const L0 = await read(leaky, null);
  await openAllDetails(leaky);
  const L1 = await read(leaky, null);
  const clean = await ctx.newPage();
  await clean.setContent('<main><p>这次没连上服务器。行程没有被改动，可以稍后重试。</p><button>稍后</button>'
    + '<button>再试一次</button></main>');
  const C = await read(clean, null);
  out.instrument_self_test = {
    leaky_collapsed: { exception_in_text: L0.exception_in_text.length, exception_in_attributes: L0.exception_in_attributes.length },
    leaky_after_opening: { exception_in_text: L1.exception_in_text.length, exception_in_attributes: L1.exception_in_attributes.length },
    clean: { exception_in_text: C.exception_in_text.length, exception_in_attributes: C.exception_in_attributes.length,
             action_verbs: C.action_verbs_present },
    derived: { detector_fires_once_the_block_is_open: L1.exception_in_text.length > 0 || L1.exception_in_attributes.length > 0,
               a_collapsed_read_would_have_missed_it: L0.exception_in_text.length === 0 && L1.exception_in_text.length > 0,
               detector_is_silent_on_a_clean_page: !(C.exception_in_text.length || C.exception_in_attributes.length) } };
  await leaky.close(); await clean.close();
  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r5_walk3_findings.json'), JSON.stringify(out, null, 1));
  const f = out.cells.W2_sealed_demo_three_fates;
  console.log(JSON.stringify({ binding: out.generation_binding, self_test: out.instrument_self_test.derived,
    wizard: { fill: w1.fill, advanced: w1.steps.map((s) => s.advanced), need_lines: w1.steps.map((s) => s.after.need_line) },
    band: w1.band_at_rest,
    fates: Object.keys(f).reduce((acc, k) => (acc[k] = { painted: (f[k].after_opening_details.painted_capped
      .match(/[^\n]*(封存演示|没读到|不是演示舞台)[^\n]*/) || [null])[0], exc_after_open: f[k].after_opening_details
      .exception_in_text.length, attr_after_open: f[k].after_opening_details.exception_in_attributes.length,
      canary_in_text: f[k].after_opening_details.canary_in_text }, acc), {}),
    legs: out.leg_count }, null, 1));
  await browser.close();
})().catch((e) => { console.error('WALK3 FAILED: ' + String((e && e.message) || e)); process.exit(9); });
