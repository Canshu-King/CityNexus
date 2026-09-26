/* Cell A on b6a8ea5c: the 「看支持的目的地」 block, closed and open, copied verbatim, then checked against what
the server actually answers per city name.

Why both halves: ORD-0346 changed this block from a spelling table to the server's own answers, and the commander
needs to know whether the change is only inside the fold. So this pass reads the block as it renders before any
click (the text a traveller sees on arrival), then after opening it (the group headings and their items), and
separately asks the SAME read route the UI asks, once per city name that appeared on screen, and records which
support state came back. Names on screen that the server does not support are listed; nothing is inferred.

Lane and limits: own Chromium, headless, 390x844 at DPR 3, touch on, zh-CN, one fresh context, no proxy (this
shell's HTTP(S)_PROXY points at a dead local port); the tunnel password is read from the file the commander named
and passed to the context as httpCredentials only - it is never printed and never written to a file. Read-only
navigation plus one click to open a fold; no form is filled, nothing is submitted.
Usage: node r6_dest_block.cjs <outDir>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_b6a8_0926');
const BASE = 'https://administrator-personality-supervisor-peers.trycloudflare.com';
const AUTH = fs.readFileSync('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt', 'utf8').trim().split(/\s+/);
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

const REGION_TEXT = () => {
  const ex = /Traceback|Exception|\bError\b|TypeError|RangeError|undefined is not|cannot read propert/i;
  const pick = (label) => {
    const all = Array.from(document.querySelectorAll('details, section, div'));
    const host = all.find((n) => (n.innerText || '').indexOf(label) >= 0
      && (n.innerText || '').length < 2200);
    return host || null;
  };
  const label = '看支持的目的地';
  const host = pick(label);
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
  return {
    label_found_in_dom: !!host,
    host_tag: host ? host.tagName.toLowerCase() : null,
    host_is_details: host ? host.tagName.toLowerCase() === 'details' : null,
    host_open_attr: host ? host.hasAttribute('open') : null,
    host_inner_text: host ? host.innerText : null,
    host_inner_text_len: host ? (host.innerText || '').length : null,
    summary_text: host ? (host.querySelector('summary,button,[role=button]') || {}).innerText || null : null,
    inner_buttons: host ? Array.from(host.querySelectorAll('button')).map((b) => (b.innerText || '').trim()) : [],
    details_count: document.querySelectorAll('details').length,
    body_inner_len: (document.body.innerText || '').length,
    exception_in_text: ex.test(document.body.innerText || ''),
    attr_hits: hits,
  };
};

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, viewport: { width: 390, height: 844 },
                clicks: 0, keystrokes: 0, writes_submitted: 0, legs: [], cells: {} };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  const page = await ctx.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let resp_bytes = null;
    try { resp_bytes = (await r.body()).length; } catch (e) { resp_bytes = 'READ_FAILED'; }
    out.legs.push({ at: new Date().toISOString(), url: r.url().replace(/^https?:\/\/[^/]+/, ''),
                    m: r.request().method(), status: r.status(), ct: r.headers()['content-type'] || null,
                    req_bytes: (r.request().postData() || '').length, resp_bytes,
                    server_header: r.headers()['server'] || null });
  });
  page.on('requestfailed', (rq) => {
    if (rq.url().indexOf('/api/') < 0) return;
    out.legs.push({ url: rq.url().replace(/^https?:\/\/[^/]+/, ''), m: rq.method(), status: null,
                    failure: (rq.failure() && rq.failure().errorText) || 'failed' });
  });

  await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(2500);
  out.served_asset = await page.evaluate(() => {
    const s = document.querySelector('script[src*="assets/index-"]');
    return s ? s.getAttribute('src') : null;
  });
  const hashHits = (cell) => {
    // the values that tripped the word list are hashed here and the raw strings are dropped, so a server
    // sentence can never ride into an evidence file (UI_EVIDENCE_EXPOSURE_GATE_V1 / Q71)
    (cell.attr_hits || []).forEach((h) => {
      h.value_sha256 = SHA(Buffer.from(h.raw_for_node_side_hashing, 'utf8'));
      h.is_data_attribute = h.attr.indexOf('data-') === 0;
      delete h.raw_for_node_side_hashing;
    });
    return cell;
  };
  out.cells.A1_closed = hashHits(await page.evaluate(REGION_TEXT));
  out.shot_closed = await shot(page, 'A1_dest_closed');

  const before = out.legs.length;
  const entry = page.getByText('看支持的目的地', { exact: false }).first();
  out.entry_found = await entry.count() > 0;
  if (out.entry_found) { await entry.click({ timeout: 6000 }).catch((e) => { out.entry_click_error = String(e.message).slice(0, 80); }); out.clicks += 1; }
  await page.waitForTimeout(1500);
  out.cells.A2_open = hashHits(await page.evaluate(REGION_TEXT));
  out.shot_open = await shot(page, 'A2_dest_open');
  out.legs_for_the_open_click = out.legs.slice(before);

  /* the names on the screen, and what the server answers for each of them */
  const names = await page.evaluate(() => {
    const host = Array.from(document.querySelectorAll('details, section, div'))
      .find((n) => (n.innerText || '').indexOf('看支持的目的地') >= 0 && (n.innerText || '').length < 2200);
    if (!host) return [];
    const txt = host.innerText || '';
    const seen = [];
    for (const m of txt.matchAll(/[\u4e00-\u9fa5]{2,4}(?=[\s、，,。]|$)/g)) {
      const w = m[0];
      if (!seen.includes(w)) seen.push(w);
    }
    const btn = Array.from(host.querySelectorAll('button')).map((b) => (b.innerText || '').trim());
    return { token_list: seen, buttons: btn };
  });
  out.screen_tokens = names;
  const cities = (await page.$$eval('button', (bs) => bs.map((b) => (b.innerText || '').trim()))).filter(Boolean);
  out.all_page_buttons = cities;
  const probeNames = Array.from(new Set([].concat(names.token_list || [], cities)
    .filter((x) => typeof x === 'string' && x.length >= 2 && x.length <= 6 && /^[\u4e00-\u9fa5]+$/.test(x))));
  const cap = {};
  for (const c of probeNames) {
    const r = await page.request.get(BASE + '/api/v1/destinations/capability?query=' + encodeURIComponent(c));
    let code = null, keys = [], receipt = null, support = null;
    try {
      const j = await r.json();
      const e = j.error || j;
      code = (e && e.code) || null;
      receipt = (e && e.error_receipt_id) || (j.error && j.error.error_receipt_id) || null;
      keys = Object.keys(j).slice(0, 30);
      support = j.support_state || (j.data && j.data.support_state) || (j.capability && j.capability.support_state) || null;
      if (Array.isArray(j.destinations)) { support = 'DESTINATION_LIST_len_' + j.destinations.length;
        keys = keys.concat(['destinations[]:' + Object.keys(j.destinations[0] || {}).slice(0, 12).join('|')]); }
      if (Array.isArray(j.matches)) { support = 'MATCHES_len_' + j.matches.length;
        keys = keys.concat(['matches[]:' + Object.keys(j.matches[0] || {}).slice(0, 12).join('|')]); }
    } catch (err) { code = 'NOT_JSON'; }
    cap[c] = { http_status: r.status(), resp_bytes: (await r.body()).length, content_type: (r.headers()['content-type'] || null),
               error_code: code, support_state: support, top_keys: keys, error_receipt_id: receipt };
    await page.waitForTimeout(120);
  }
  out.capability_per_name = cap;
  out.names_probed = probeNames.length;
  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r6_dest_block.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ served_asset: out.served_asset, closed_len: out.cells.A1_closed.host_inner_text_len,
    open_len: out.cells.A2_open.host_inner_text_len, details_before: out.cells.A1_closed.details_count,
    details_after: out.cells.A2_open.details_count, names_probed: out.names_probed,
    legs: out.legs.length }, null, 1));
  console.log('CLOSED:\n' + (out.cells.A1_closed.host_inner_text || '(none)'));
  console.log('OPEN:\n' + (out.cells.A2_open.host_inner_text || '(none)'));
  await browser.close();
})().catch((e) => { console.error('A FAILED: ' + String((e && e.message) || e)); process.exit(9); });
