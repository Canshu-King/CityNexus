/* Cell A again, but read at three moments: before the tap, the instant after it, and after the app's own
per-city questions have all come back.

Why a second instrument and not the readings from the first pass: opening that block makes the app ask
`GET /api/v1/destinations/capability?query=<name>` once per advertised name (the legs proved it), so the text I
copied 1.5 s after the tap said `还没问过服务器 / not-asked` under all eleven names - a state that was on its way
out. Reading it once would have let me file "ORD-0346 groups nothing" on a transient frame, so this pass waits for
the legs to go quiet and reads again, and it keeps all three states.

Group membership is measured, not inferred: for each advertised name the DOM is climbed until an ancestor whose
text begins with one of the three group headings is found, and that heading is what the screen attributes the
name to.

Lane and limits unchanged: own headless Chromium, 390x844@3, touch, zh-CN, one fresh context, no proxy; tunnel
password read from the named file and passed as httpCredentials only. Read-only: one tap to open a fold, 0 form
input, 0 submissions.
Usage: node r6_dest_block_r3.cjs <outDir>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_b6a8_0926');
const BASE = 'https://administrator-personality-supervisor-peers.trycloudflare.com';
const AUTH = fs.readFileSync('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt', 'utf8').trim().split(/\s+/);
const ADVERTISED = ['厦门', '北京', '上海', '天津', '福州', '广州', '深圳', '成都', '杭州', '东京', '新加坡'];
const HEADINGS = ['已支持：服务器认得它，而且目录里有东西', '需联网才能解析：服务器现在认不出这个名字',
                  '未知或无数据：这一轮拿不出可规划的判定'];
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

const READ = (arg) => {
  const names = arg.names, heads = arg.heads;
  const all = Array.from(document.querySelectorAll('details, section, div'));
  const host = all.find((n) => (n.innerText || '').indexOf('看支持的目的地') >= 0
    && (n.innerText || '').length < 3000);
  const bodyText = host ? host.innerText : null;
  const per = {};
  for (const nm of names) {
    let node = null;
    for (const n of document.querySelectorAll('button,li,span,div,p')) {
      const t = (n.innerText || '').trim();
      if (t === nm || t.split('\n')[0] === nm) { node = n; break; }
    }
    if (!node) { per[nm] = { on_screen: false }; continue; }
    let a = node, heading = null;
    // innermost ancestor that carries a heading wins: the first pass kept climbing and let the outermost
    // heading overwrite it, which reported all eleven names under one group and contradicted the text
    for (let i = 0; i < 12 && a; i++) {
      const txt = (a.innerText || '');
      if (txt.length < 1400) {
        const h = heads.find((x) => txt.indexOf(x) >= 0);
        if (h) { heading = h; break; }
      }
      a = a.parentElement;
    }
    let anc = node;
    for (let i = 0; i < 6 && anc; i++) {
      const txt = (anc.innerText || '').split('\n').filter(Boolean);
      if (txt.length > 1 && txt[0] === nm) { own = txt.slice(1, 5); break; }
      anc = anc.parentElement;
    }
    per[nm] = { on_screen: true, attributed_heading: heading, lines_under_name: own,
                role: node.getAttribute('role'), tag: node.tagName.toLowerCase(),
                aria_expanded: node.getAttribute('aria-expanded') };
  }
  const counts = {};
  for (const h of heads) counts[h] = Object.values(per).filter((v) => v.attributed_heading === h).length;
  return { host_found: !!host, host_inner_text_len: bodyText ? bodyText.length : null,
           host_inner_text: bodyText, group_heading_counts: counts,
           names_on_screen: Object.keys(per).filter((k) => per[k].on_screen),
           per_name: per, details_count: document.querySelectorAll('details').length,
           toggle_aria: (() => {
             const t = Array.from(document.querySelectorAll('button,[role=button]'))
               .find((b) => (b.innerText || '').indexOf('看支持的目的地') >= 0);
             return t ? { tag: t.tagName.toLowerCase(), aria_expanded: t.getAttribute('aria-expanded'),
                          role: t.getAttribute('role'), text: (t.innerText || '').trim(),
                          visible_height: Math.round(t.getBoundingClientRect().height) } : null;
           })(),
           body_inner_len: (document.body.innerText || '').length };
};

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, viewport: { width: 390, height: 844 },
                clicks: 0, keystrokes: 0, legs: [], advertised: ADVERTISED, headings: HEADINGS };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  const page = await ctx.newPage();
  const capLegs = [];
  page.on('response', async (r) => {
    const u = r.url();
    if (u.indexOf('/api/') < 0) return;
    let rb = null;
    try { rb = (await r.body()).length; } catch (e) { rb = 'READ_FAILED'; }
    const row = { at_ms: Date.now(), url: u.replace(/^https?:\/\/[^/]+/, ''), m: r.request().method(),
                  status: r.status(), ct: r.headers()['content-type'] || null,
                  req_bytes: (r.request().postData() || '').length, resp_bytes: rb };
    out.legs.push(row);
    if (u.indexOf('/api/v1/destinations/capability') >= 0) capLegs.push(row);
  });
  await page.goto(BASE + '/', { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(3000);
  out.served_asset = await page.evaluate(() => (document.querySelector('script[src*="assets/index-"]') || {}).src || null);
  out.state_1_closed = await page.evaluate(READ, { names: ADVERTISED, heads: HEADINGS });
  out.shot_1_closed = await shot(page, 'A3_1_closed');

  const t0 = Date.now();
  await page.getByText('看支持的目的地', { exact: false }).first().click({ timeout: 6000 });
  out.clicks += 1;
  await page.waitForTimeout(700);
  out.state_2_just_opened = await page.evaluate(READ, { names: ADVERTISED, heads: HEADINGS });
  out.shot_2_just_opened = await shot(page, 'A3_2_just_opened');

  /* wait until the app's own capability legs stop arriving, then read a third time */
  let last = capLegs.length, stable = 0;
  while (Date.now() - t0 < 45000 && stable < 6) {
    await page.waitForTimeout(500);
    if (capLegs.length === last) { stable += 1; } else { stable = 0; last = capLegs.length; }
  }
  out.capability_legs_seen = capLegs.length;
  out.capability_leg_rows = capLegs;
  out.settled_wait_ms = Date.now() - t0;
  out.state_3_settled = await page.evaluate(READ, { names: ADVERTISED, heads: HEADINGS });
  out.shot_3_settled = await shot(page, 'A3_3_settled');
  out.changed_between_just_opened_and_settled = JSON.stringify(out.state_2_just_opened.host_inner_text)
    !== JSON.stringify(out.state_3_settled.host_inner_text);
  out.leg_count = out.legs.length;
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r6_dest_block_r3.json'), JSON.stringify(out, null, 1));
  const s3 = out.state_3_settled;
  console.log(JSON.stringify({ served_asset: out.served_asset, cap_legs: out.capability_legs_seen,
    settled_wait_ms: out.settled_wait_ms, closed_len: out.state_1_closed.host_inner_text_len,
    just_opened_len: out.state_2_just_opened.host_inner_text_len, settled_len: s3.host_inner_text_len,
    changed: out.changed_between_just_opened_and_settled, counts: s3.group_heading_counts,
    toggle_aria: s3.toggle_aria }, null, 1));
  console.log('SETTLED TEXT:\n' + (s3.host_inner_text || '(none)').slice(0, 2600));
  await browser.close();
})().catch((e) => { console.error('A2 FAILED: ' + String((e && e.message) || e)); process.exit(9); });
