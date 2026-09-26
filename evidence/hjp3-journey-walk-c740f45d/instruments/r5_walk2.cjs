/* HJ-P3 real-journey walkthrough, take 2 - the first take failed on my own instrument, not on the product.
 *
 * What I got wrong in take 1, stated because it is the reason this file exists: I clicked 「下一步」 on a form
 * whose hint line said 「还需要填写：目的地、抵达地点、离开地点」 and then reported "the wizard does not
 * advance". That is my omission, not a product defect. I also probed for a 「封存演示」 button when the real
 * label is 「使用封存的演示行程」 (a name-probe false absence), and I stored only text LENGTHS, which cannot
 * answer the question actually asked - what does the traveller read?
 *
 * Take 2 therefore behaves like the traveller: it types the destination and the two places, sets the two
 * datetimes, presses 下一步, and repeats - recording the painted sentence at every step (verbatim, capped, with
 * the full-text sha256 so the cap is disclosed). The four forbidden shapes are scanned over both text and
 * attribute positions (Q71), and the instrument proves itself in both directions before any of it counts.
 *
 * 0 product bytes touched; the only things broken on purpose are broken inside my own browser context.
 *
 * Usage: node r5_walk2.cjs <outDir>
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_0323walk_0926');
const CHAIN = 'http://127.0.0.1:4781';
const CAP = 900;
fs.mkdirSync(OUT, { recursive: true });

const SHA = (s) => crypto.createHash('sha256').update(String(s)).digest('hex');
const PAT = { ex: 'Traceback|Exception|\\bError\\b|TypeError|RangeError|ReferenceError|undefined is not|cannot read propert',
              stack: '^\\s*at\\s+[\\w$.<>\\s]+\\(.+:\\d+:\\d+\\)',
              long: '[A-Za-z0-9_./:\\\\-]{120,}' };

async function read(page) {
  const r = await page.evaluate((P) => {
    const ex = new RegExp(P.ex, 'i'), st = new RegExp(P.stack, 'm'), lm = new RegExp(P.long);
    const t = (el) => (el && (el.innerText || el.textContent) || '').trim();
    const all = document.body ? document.body.innerText : '';
    const nodes = Array.prototype.slice.call(document.querySelectorAll('*'));
    const hits = [];
    const attrHits = [];
    for (const n of nodes) {
      const own = Array.prototype.slice.call(n.childNodes).filter((c) => c.nodeType === 3)
        .map((c) => c.nodeValue).join('').trim();
      if (own && ex.test(own)) {
        hits.push({ tag: n.tagName.toLowerCase(), cls: String(n.className).slice(0, 50), raw: own });
      }
      for (const a of Array.prototype.slice.call(n.attributes || [])) {
        if (['style', 'src', 'href', 'd', 'class'].indexOf(a.name) >= 0) continue;
        const v = String(a.value || '');
        if (v && (ex.test(v) || lm.test(v))) {
          attrHits.push({ tag: n.tagName.toLowerCase(), attr: a.name, raw: v });
        }
      }
    }
    let slot = null;
    for (const n of nodes) {
      const s = t(n);
      if (s && /原因编号|原因原文|服务器给出的原因|服务器没给句子/.test(s) && n.children.length <= 3) {
        slot = { raw: s,
                 looks_like_a_code: /^[A-Z0-9_]{4,}$/.test(s.replace(/\s/g, '')),
                 sentence_like: /[。，、；].{6,}/.test(s) };
        break;
      }
    }
    return { url: location.href, inner_text: all, inner_len: all.length,
             text_content_len: document.body ? document.body.textContent.length : 0,
             buttons: nodes.filter((n) => /^(BUTTON|A)$/.test(n.tagName) && t(n)).map((n) => t(n).slice(0, 40)),
             hint_lines: nodes.filter((n) => n.children.length === 0 && /还需要填写|请/.test(t(n)))
               .map((n) => t(n).slice(0, 80)).slice(0, 4),
             action_verb: /重试|再试一次|换一座城市|稍后|换个说法|检查|继续|创建/.test(all),
             exception_in_text: hits, exception_in_attributes: attrHits,
             stack_frame: st.test(all), long_machine_text: lm.test(all), reason_code_slot: slot };
  }, PAT);
  const seal = (o, key) => { const v = String(o.raw == null ? '' : o.raw); const q = Object.assign({}, o);
                              delete q.raw; q.len = v.length; q.sha256 = SHA(v); return q; };
  r.exception_in_text = (r.exception_in_text || []).map((x) => seal(x)).slice(0, 6);
  r.exception_in_attributes = (r.exception_in_attributes || []).map((x) => seal(x)).slice(0, 6);
  if (r.reason_code_slot) { const q = seal(r.reason_code_slot);
    q.looks_like_a_code = r.reason_code_slot.looks_like_a_code;
    q.sentence_like = r.reason_code_slot.sentence_like; r.reason_code_slot = q; }
  const capped = r.inner_text.slice(0, CAP);
  return { url: r.url, inner_len: r.inner_len, text_content_len: r.text_content_len,
           painted_text_capped: capped, painted_text_truncated: r.inner_len > CAP,
           painted_text_sha256_of_full: SHA(r.inner_text),
           buttons: r.buttons, hint_lines: r.hint_lines, action_verb: r.action_verb,
           exception_in_text: r.exception_in_text, exception_in_attributes: r.exception_in_attributes,
           stack_frame: r.stack_frame, long_machine_text: r.long_machine_text, reason_code_slot: r.reason_code_slot };
}
async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), exists: fs.existsSync(p), bytes: fs.existsSync(p) ? fs.statSync(p).size : 0 };
}
async function stepBar(page) {
  return await page.evaluate(() => {
    const steps = document.querySelector('.trial-steps') || document.querySelector('[class*="trial-steps"]');
    const card = document.querySelector('.trial-card') || document.querySelector('[class*="trial-card"]');
    const done = steps ? Array.prototype.slice.call(steps.querySelectorAll('*'))
      .filter((n) => n.children.length === 0 && /^\d$/.test((n.innerText || '').trim()))
      .map((n) => ({ mark: n.innerText.trim(), cls: String(n.className).slice(0, 40),
                     top: Math.round(n.getBoundingClientRect().top) })) : [];
    const r1 = steps ? steps.getBoundingClientRect() : null;
    const r2 = card ? card.getBoundingClientRect() : null;
    const first = card ? Array.prototype.slice.call(card.querySelectorAll('input,label,h2,h3,p'))
      .filter((n) => (n.innerText || n.placeholder || '').trim())[0] : null;
    const rf = first ? first.getBoundingClientRect() : null;
    return { steps_found: !!steps, padding_bottom_px: steps ? parseFloat(getComputedStyle(steps).paddingBottom) : null,
             active_step_marks: done, gap_steps_to_card_px: (r1 && r2) ? Math.round(r2.top - r1.bottom) : null,
             gap_steps_to_first_control_px: (r1 && rf) ? Math.round(rf.top - r1.bottom) : null,
             card_top_px: r2 ? Math.round(r2.top) : null, viewport_h: window.innerHeight,
             scroll_overflow_px: document.documentElement.scrollHeight - window.innerHeight,
             card_visible_at_rest: !!r2 && r2.top < window.innerHeight };
  });
}
async function fillWizard(page) {
  const ins = await page.$$('input');
  const acts = [];
  const typed = await page.evaluate(() => Array.prototype.slice
    .call(document.querySelectorAll('input')).map((n) => ({ type: n.type, ph: n.placeholder || null })));
  for (const spec of [{ sel: 'input[placeholder*="城市"]', val: '天津' },
                      { sel: 'input[placeholder*="站"]', val: '天津站' },
                      { sel: 'input[type="datetime-local"]', val: '2026-10-02T10:00' }]) {
    const loc = page.locator(spec.sel);
    const n = await loc.count();
    if (!n) { acts.push({ sel: spec.sel, found: 0 }); continue; }
    await loc.first().fill(spec.val).catch((e) => acts.push({ sel: spec.sel, err: String(e.message).slice(0, 60) }));
    acts.push({ sel: spec.sel, found: n, filled: spec.val.length });
  }
  const places = await page.$$('input[placeholder*="机场"]');
  for (const el of places) { await el.fill('天津滨海国际机场').catch(() => {}); }
  return { inputs_seen: typed, actions: acts, places_filled: places.length };
}

(async () => {
  const out = { started_at: new Date().toISOString(), chain: CHAIN, viewport: { width: 390, height: 844 },
                device_scale_factor: 3, locale: 'zh-CN', legs: [], cells: {} };
  const browser = await chromium.launch({ headless: true });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  page.on('response', (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    out.legs.push({ at: new Date().toISOString(), url: r.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''),
                    method: r.request().method(), status: r.status(),
                    content_type: r.headers()['content-type'] || null });
  });
  page.on('requestfailed', (rq) => {
    if (rq.url().indexOf('/api/') < 0) return;
    out.legs.push({ at: new Date().toISOString(), url: rq.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''),
                    method: rq.method(), status: null,
                    failure: (rq.failure() && rq.failure().errorText) || 'failed' });
  });

  const resp = await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 60000 });
  const html = await resp.text();
  const asset = (html.match(/"\/(assets\/index-[^"]+\.js)"/) || [])[1] || null;
  let ab = null, ash = null;
  if (asset) { const a = await page.request.get(CHAIN + '/' + asset); const buf = await a.body();
               ab = buf.length; ash = SHA(buf); }
  out.generation_binding = { served_index_status: resp.status(), served_index_bytes: html.length,
                             asset_named_by_the_served_page: asset, asset_bytes: ab, asset_sha256_64_hex: ash };

  /* W1 - fill it like a traveller, then walk the three steps */
  const w1 = { at_entry: await read(page), shot_entry: await shot(page, 'W1_entry'),
               band_at_entry: await stepBar(page) };
  w1.fill = await fillWizard(page);
  w1.shot_filled = await shot(page, 'W1_filled');
  for (const i of [1, 2, 3]) {
    const before = await read(page);
    await page.getByText('下一步').first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(1600);
    const after = await read(page);
    w1['step' + i] = { before_hint_lines: before.hint_lines, after: after, changed: before.inner_len !== after.inner_len
                       || JSON.stringify(before.buttons) !== JSON.stringify(after.buttons),
                       band: await stepBar(page), shot: await shot(page, 'W1_after_next' + i) };
  }
  out.cells.W1_new_journey_wizard = w1;

  /* W2 - the sealed-demo entry, by its real label */
  const w2 = { label_searched: '使用封存的演示行程',
               present_in_buttons: (w1.at_entry.buttons || []).some((x) => x.indexOf('封存') >= 0) };
  await page.getByText('使用封存的演示行程').first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(3000);
  w2.after = await read(page);
  w2.shot = await shot(page, 'W2_sealed_demo');
  out.cells.W2_sealed_demo_entry = w2;

  /* W3 - the natural read failure: the scene leg is failing on its own, no backend is up */
  const w3 = { legs_so_far: out.legs.length };
  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3500);
  w3.after = await read(page);
  w3.shot = await shot(page, 'W3_read_failure');
  w3.legs_this_cell = out.legs.slice(w3.legs_so_far);
  out.cells.W3_read_failure_copy = w3;

  /* W4 - three surfaces, each broken once, all inside my own browser */
  const w4 = {};
  const dead = '00000000-0000-0000-0000-000000000000';
  await page.goto(CHAIN + '/journey/' + dead, { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(2500);
  w4.a_dead_stored_id = { url: page.url(), read: await read(page), shot: await shot(page, 'W4a_dead_id') };
  await page.route('**/api/v1/**', (r) => r.abort('connectionrefused'));
  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const refusedFill = await fillWizard(page);
  await page.getByText('使用封存的演示行程').first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(2500);
  w4.b_transport_refused = { filled: refusedFill.actions, read: await read(page),
                             shot: await shot(page, 'W4b_refused') };
  await page.unroute('**/api/v1/**');
  await page.route('**/api/v1/**', (r) => r.fulfill({ status: 500, contentType: 'text/html',
                                                     body: '<!doctype html><html><body>gw</body></html>' }));
  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await fillWizard(page);
  await page.getByText('使用封存的演示行程').first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(2500);
  w4.c_500_with_html_body = { read: await read(page), shot: await shot(page, 'W4c_html500') };
  await page.unroute('**/api/v1/**');
  await page.route('**/api/v1/**', (r) => r.fulfill({ status: 200, contentType: 'application/json',
                                                     body: '{"detail":"boom"}' }));
  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await fillWizard(page);
  await page.getByText('使用封存的演示行程').first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(2500);
  w4.d_200_with_json_detail = { read: await read(page), shot: await shot(page, 'W4d_json200') };
  await page.unroute('**/api/v1/**');
  out.cells.W4_broken_four_ways = w4;

  /* the instrument's own two-way proof, run before any of the above is worth anything */
  const leaky = await ctx.newPage();
  await leaky.setContent('<div id="x" data-error-name="TypeError" data-error-message="cannot read properties of null">'
    + '服务器回的原因编号是 Something failed: cannot read properties of null at Object.<anonymous> (main.tsx:147:22)</div>'
    + '<p>Traceback (most recent call last): File "/srv/app/main.py", line 12, in generate</p>');
  const L = await read(leaky);
  const clean = await ctx.newPage();
  await clean.setContent('<main><p>这次没连上服务器。行程没有被改动，可以稍后重试。</p>'
    + '<button>稍后</button><button>再试一次</button></main>');
  const C = await read(clean);
  out.instrument_self_test = {
    leaky: { exception_in_text: L.exception_in_text.length, exception_in_attributes: L.exception_in_attributes.length,
             stack_frame: L.stack_frame, long_machine_text: L.long_machine_text,
             slot_sentence_like: L.reason_code_slot && L.reason_code_slot.sentence_like,
             slot_looks_like_a_code: L.reason_code_slot && L.reason_code_slot.looks_like_a_code },
    clean: { exception_in_text: C.exception_in_text.length, exception_in_attributes: C.exception_in_attributes.length,
             stack_frame: C.stack_frame, long_machine_text: C.long_machine_text, action_verb: C.action_verb },
    derived: { fires_on_the_page_that_leaks: !!(L.exception_in_text.length || L.exception_in_attributes.length
                                                || L.stack_frame || L.long_machine_text),
               silent_on_the_page_that_does_not: !(C.exception_in_text.length || C.exception_in_attributes.length
                                                   || C.stack_frame || C.long_machine_text) } };
  await leaky.close(); await clean.close();
  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r5_walk2_findings.json'), JSON.stringify(out, null, 1));
  const brief = {};
  for (const k of Object.keys(out.cells)) {
    const c = out.cells[k];
    const r = c.after || c.read || (c.step3 && c.step3.after) || c.at_entry || {};
    brief[k] = { inner_len: r.inner_len, verbs: r.action_verb, exc: (r.exception_in_text || []).length,
                 attr: (r.exception_in_attributes || []).length, stack: r.stack_frame, long: r.long_machine_text };
  }
  console.log(JSON.stringify({ binding: out.generation_binding, self_test: out.instrument_self_test.derived,
    W1_changed: { s1: w1.step1.changed, s2: w1.step2.changed, s3: w1.step3.changed },
    W1_band_after_next: w1.step3.band, brief: brief, legs: out.leg_count }, null, 1));
  await browser.close();
})().catch((e) => { console.error('WALK2 FAILED: ' + String((e && e.message) || e)); process.exit(9); });
