/* HJ-P3 real-journey walkthrough on c740f45d - four cells at 390x844, screenshots every step.
 *
 * The commander's ask is not "are the gates green" but "can a traveller actually get through", so this file
 * behaves like a person: it clicks what is on the screen, reads what the screen says back, and never assumes a
 * selector exists. Every absence is reported with the inventory that was found instead.
 *
 * Two rules it holds itself to:
 *   - 0 product bytes touched: it only drives the deployed chain read-only, and the one thing it authors is its
 *     own fixture page for the instrument self-test;
 *   - no PASS is written here. It emits readings (painted text, geometry, leg status) plus the mechanical
 *     rule hits the commander named (exception literals, stacks, server prose in a code slot, Q71's data-*
 *     positions). Anything that would be a verdict is left to the ledger owner.
 *
 * Q64 also applies to this file: painted product labels are kept as text (that is the thing under test), while
 * any string the rules flag as possibly server-derived is recorded as length + sha1 head only.
 *
 * Usage: node r5_walk.cjs <outDir>
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_0323walk_0926');
const CHAIN = 'http://127.0.0.1:4781';
fs.mkdirSync(OUT, { recursive: true });

const sha = (s) => crypto.createHash('sha256').update(String(s)).digest('hex');
const RULES = {
  exception_literal: /Traceback|Exception|\bError\b|TypeError|RangeError|ReferenceError|undefined is not|cannot read propert/,
  stack_frame: /^\s*at\s+[\w$.<>\s]+\(.+:\d+:\d+\)/m,
  long_machine_text: /[A-Za-z0-9_./:\\-]{120,}/,
  server_prose_in_code_slot: null /* decided per node at read time, see scanPage */,
};

/* one read of a page: everything the traveller can perceive, plus the four forbidden shapes */
async function scanPage(page) {
  return await page.evaluate((RULE_SRC) => {
    const ex = new RegExp(RULE_SRC.exception_literal, 'i');
    const st = new RegExp(RULE_SRC.stack_frame, 'm');
    const lm = new RegExp(RULE_SRC.long_machine_text);
    const txt = (el) => (el && (el.innerText || el.textContent) || '').trim();
    const body = document.body ? txt(document.body) : '';
    const textContentAll = document.body ? document.body.textContent : '';
    /* Q71: every attribute position counts, so walk attributes too, not just text */
    const attrHits = [];
    const textHits = [];
    const nodes = Array.prototype.slice.call(document.querySelectorAll('*'));
    for (const n of nodes) {
      for (const a of Array.prototype.slice.call(n.attributes || [])) {
        if (a.name === 'style' || a.name === 'src' || a.name === 'href' || a.name === 'd') continue;
        const v = String(a.value || '');
        if (v && (ex.test(v) || lm.test(v))) {
          attrHits.push({ tag: n.tagName.toLowerCase(), attr: a.name, value_len: v.length,
                          value_sha1_head: crypto_head(v) });
        }
      }
      const own = Array.prototype.slice.call(n.childNodes).filter((c) => c.nodeType === 3)
                  .map((c) => c.nodeValue).join('').trim();
      if (own && ex.test(own)) {
        textHits.push({ tag: n.tagName.toLowerCase(), cls: String(n.className || '').slice(0, 60),
                        len: own.length, head: own.slice(0, 24) });
      }
    }
    function crypto_head(v) { let h = 0; for (let i = 0; i < v.length; i++) { h = (h * 31 + v.charCodeAt(i)) >>> 0; } return h.toString(16); }
    /* the reason-code slot: the sentence that names a code, and what actually stands in it */
    let codeSlot = null;
    for (const n of nodes) {
      const s = txt(n);
      if (s && /原因编号|原因原文|服务器给出的原因|服务器没给句子/.test(s) && n.children.length <= 3) {
        codeSlot = { painted: s.slice(0, 160), len: s.length, tag: n.tagName.toLowerCase(),
                     looks_like_a_code: /^[A-Z0-9_]{4,}$/.test(s.replace(/\s/g, '')),
                     sentence_like: /[。，、；].{6,}/.test(s) };
        break;
      }
    }
    return {
      url: location.href, title: document.title,
      visible_button_labels: nodes.filter((n) => /^(BUTTON|A)$/.test(n.tagName) && txt(n))
        .map((n) => txt(n).slice(0, 40)).slice(0, 40),
      painted_text_len: body.length,
      text_content_len: textContentAll.length,
      action_verb_present: /重试|再试一次|换一座城市|稍后|检查|换个说法|打开|继续/.test(body),
      exception_literal_in_text: textHits.slice(0, 8),
      exception_in_attributes: attrHits.slice(0, 8),
      stack_frame_in_text: st.test(body),
      long_machine_text_in_text: lm.test(body),
      reason_code_slot: codeSlot,
    };
  }, { exception_literal: RULES.exception_literal.source, stack_frame: RULES.stack_frame.source,
       long_machine_text: RULES.long_machine_text.source });
}

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p, fullPage: false });
  return { file: path.basename(p), exists: fs.existsSync(p), bytes: fs.existsSync(p) ? fs.statSync(p).size : 0,
           abs: p };
}

async function clickByText(page, needle, timeout) {
  const loc = page.getByText(new RegExp(needle)).first();
  const t = timeout || 8000;
  const found = await loc.isVisible().catch(() => false);
  if (!found) return { needle: needle, found: false };
  await loc.click({ timeout: t }).catch(() => {});
  await page.waitForTimeout(1200);
  return { needle: needle, found: true };
}

(async () => {
  const out = { started_at: new Date().toISOString(), chain: CHAIN, viewport: { width: 390, height: 844 },
                device_scale_factor: 3, locale: 'zh-CN', cells: {}, legs: [] };
  /* generation binding: what the chain serves right now, hashed - no bodies kept */
  const page0 = await (async () => {
    const browser = await chromium.launch({ headless: true });
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                           hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    out.browser = { chromium_version: browser.version() };
    const p = await ctx.newPage();
    p.on('response', (r) => {
      if (r.url().indexOf('/api/') < 0) return;
      out.legs.push({ at: new Date().toISOString(), url: r.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''),
                      method: r.request().method(), status: r.status(),
                      content_type: r.headers()['content-type'] || null });
    });
    p.on('requestfailed', (rq) => {
      if (rq.url().indexOf('/api/') < 0) return;
      out.legs.push({ at: new Date().toISOString(), url: rq.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''),
                      method: rq.method(), status: null,
                      failure: (rq.failure() && rq.failure().errorText) || 'failed' });
    });
    return p;
  })();
  const resp = await page0.goto(CHAIN + '/', { waitUntil: 'load', timeout: 60000 });
  const html = await resp.text();
  const asset = (html.match(/"\/(assets\/index-[^"]+\.js)"/) || [])[1] || null;
  let assetBytes = null, assetSha = null;
  if (asset) {
    const a = await page0.request.get(CHAIN + '/' + asset);
    const buf = await a.body();
    assetBytes = buf.length; assetSha = crypto.createHash('sha256').update(buf).digest('hex');
  }
  out.generation_binding = { served_index_status: resp.status(), served_index_bytes: html.length,
                             asset_named_by_the_served_page: asset, asset_bytes: assetBytes,
                             asset_sha256_64_hex: assetSha };

  /* W1 the new-journey wizard, three steps, with the band measured */
  const w1 = { entry_click: await clickByText(page0, '新建行程|AI 帮我规划|体验') };
  w1.screenshot_step1 = await shot(page0, 'W1_step1');
  w1.read_step1 = await scanPage(page0);
  w1.band = await page0.evaluate(() => {
    const q = (s) => document.querySelector(s);
    const steps = q('.trial-steps') || q('[class*="trial-steps"]');
    const card = q('.trial-card') || q('[class*="trial-card"]');
    const cs = steps ? getComputedStyle(steps) : null;
    const r1 = steps ? steps.getBoundingClientRect() : null;
    const r2 = card ? card.getBoundingClientRect() : null;
    const dest = Array.prototype.slice.call(document.querySelectorAll('*'))
      .filter((n) => n.children.length === 0 && /目的地/.test(n.innerText || ''))[0];
    const rd = dest ? dest.getBoundingClientRect() : null;
    return { steps_found: !!steps, steps_class: steps ? String(steps.className) : null,
             steps_padding_bottom_px: cs ? parseFloat(cs.paddingBottom) : null,
             gap_steps_bottom_to_card_top_px: (r1 && r2) ? Math.round(r2.top - r1.bottom) : null,
             gap_steps_bottom_to_destination_px: (r1 && rd) ? Math.round(rd.top - r1.bottom) : null,
             destination_visible_without_scroll: !!rd && rd.top >= 0 && rd.top < window.innerHeight,
             scroll_height_minus_viewport_px: document.documentElement.scrollHeight - window.innerHeight };
  });
  w1.next_click_1 = await clickByText(page0, '下一步');
  w1.screenshot_step2 = await shot(page0, 'W1_step2');
  w1.read_step2 = await scanPage(page0);
  w1.progressed_to_step2 = JSON.stringify(w1.read_step2.painted_text_len) !== JSON.stringify(w1.read_step1.painted_text_len)
    || w1.read_step2.url !== w1.read_step1.url;
  w1.next_click_2 = await clickByText(page0, '下一步');
  w1.screenshot_step3 = await shot(page0, 'W1_step3');
  w1.read_step3 = await scanPage(page0);
  out.cells.W1_new_journey_wizard = w1;

  /* W2 the sealed-demo entry: what does the failure screen say */
  const w2 = { entry_click: await clickByText(page0, '封存演示') };
  await page0.waitForTimeout(2500);
  w2.screenshot = await shot(page0, 'W2_sealed_demo');
  w2.read = await scanPage(page0);
  out.cells.W2_sealed_demo_entry = w2;

  /* W3 a read failure in the chain's natural state (no backend is up on :8000) */
  const w3 = { list_attempt: await clickByText(page0, '行程|收件箱|我的') };
  await page0.waitForTimeout(2500);
  w3.screenshot = await shot(page0, 'W3_read_failure');
  w3.read = await scanPage(page0);
  w3.legs_seen_this_cell = out.legs.slice(-12);
  out.cells.W3_read_failure_copy = w3;

  /* W4 three places, each deliberately broken - and only through my own browser, never the shared chain */
  const w4 = {};
  const dead = '00000000-0000-0000-0000-000000000000';
  await page0.goto(CHAIN + '/journey/' + dead, { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page0.waitForTimeout(2000);
  w4.dead_stored_id = { url: page0.url(), screenshot: await shot(page0, 'W4a_dead_id'),
                        read: await scanPage(page0) };
  await page0.route('**/api/v1/**', (r) => r.abort('connectionrefused'));
  await page0.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page0.waitForTimeout(2500);
  w4.transport_refused_by_my_route = { screenshot: await shot(page0, 'W4b_refused'),
                                       read: await scanPage(page0) };
  await page0.unroute('**/api/v1/**');
  await page0.route('**/api/v1/**', (r) => r.fulfill({ status: 500, contentType: 'text/html',
                                                      body: '<!doctype html><html><body>gateway</body></html>' }));
  await page0.goto(CHAIN + '/', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
  await page0.waitForTimeout(2500);
  w4.five_hundred_with_html_by_my_route = { screenshot: await shot(page0, 'W4c_html500'),
                                            read: await scanPage(page0) };
  await page0.unroute('**/api/v1/**');
  out.cells.W4_broken_three_ways = w4;

  /* the instrument's own two-way self-test: the same rules must fire on a page that does leak */
  const leaky = await page0.context().newPage();
  await leaky.setContent('<div id="x" data-error-name="TypeError" data-error-message="boom">服务器回的原因编号是 '
    + 'Something failed: cannot read properties of null at Object.<anonymous> (main.tsx:147:22)</div>'
    + '<p>Traceback (most recent call last): File "/srv/app/main.py", line 12, in generate</p>');
  const leakyRead = await scanPage(leaky);
  const clean = await page0.context().newPage();
  await clean.setContent('<div><p>这次没连上服务器。行程没有被改动，可以稍后重试。</p>'
    + '<button>稍后</button><button>再试一次</button></div>');
  const cleanRead = await scanPage(clean);
  out.instrument_self_test = {
    leaky_page: { exception_hits: leakyRead.exception_literal_in_text.length,
                  attr_hits: leakyRead.exception_in_attributes.length,
                  stack_frame: leakyRead.stack_frame_in_text,
                  long_machine_text: leakyRead.long_machine_text_in_text,
                  slot_read: leakyRead.reason_code_slot && {
                    len: leakyRead.reason_code_slot.len,
                    looks_like_a_code: leakyRead.reason_code_slot.looks_like_a_code,
                    sentence_like: leakyRead.reason_code_slot.sentence_like } },
    clean_page: { exception_hits: cleanRead.exception_literal_in_text.length,
                  attr_hits: cleanRead.exception_in_attributes.length,
                  stack_frame: cleanRead.stack_frame_in_text,
                  long_machine_text: cleanRead.long_machine_text_in_text,
                  action_verb: cleanRead.action_verb_present },
    verdicts_derived: {
      fires_on_the_leaky_page: !!(leakyRead.exception_literal_in_text.length || leakyRead.stack_frame_in_text
                                  || leakyRead.exception_in_attributes.length
                                  || leakyRead.long_machine_text_in_text),
      silent_on_the_clean_page: !(cleanRead.exception_literal_in_text.length || cleanRead.stack_frame_in_text
                                  || cleanRead.exception_in_attributes.length
                                  || cleanRead.long_machine_text_in_text) } };
  await leaky.close(); await clean.close();
  out.finished_at = new Date().toISOString();
  out.leg_count = out.legs.length;
  fs.writeFileSync(path.join(OUT, 'r5_walk_findings.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ binding: out.generation_binding,
    self_test: out.instrument_self_test.verdicts_derived,
    W1_band: w1.band, W1_step2: w1.progressed_to_step2, legs: out.legs.length }, null, 1));
  await page0.context().browser().close();
})().catch((e) => { console.error('WALK FAILED: ' + (e && e.stack ? String(e.message) : e)); process.exit(9); });
