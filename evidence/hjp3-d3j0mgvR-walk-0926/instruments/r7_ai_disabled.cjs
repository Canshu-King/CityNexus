/* One click, one reading: the trips screen sends the traveller to 先让 AI 帮你规划 while health says the AI is
 switched off by operations - so what does that button actually do on this build?

Nothing here is inferred. The guidance sentence was copied off `/v8/trips` in the previous pass, and `/api/v1/health`
answered 113 B with `ai_state=DISABLED_BY_OPS`. The only open question is what the traveller meets when they follow
that advice, so this pass presses 一次「AI 帮我规划」 and reads the screen and the legs afterwards.

One browser launch, one fresh context seeded with the journey created earlier, no proxy. The tunnel password is read
from the named file and used as httpCredentials only. I make no claim about map tiles on this lane.
Usage: node r7_ai_disabled.cjs <outDir> <journey-id>
*/
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_d3j0_0926');
const JID = process.argv[3];
const BASE = 'https://jets-saints-tomatoes-eric.trycloudflare.com';
const AUTH = fs.readFileSync('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt', 'utf8').trim().split(/\s+/);
const SHA = (b) => crypto.createHash('sha256').update(b).digest('hex');
fs.mkdirSync(OUT, { recursive: true });

const SNAP = () => {
  const body = document.body ? (document.body.innerText || '') : '';
  return { url: location.href, text_len: body.length, text: body.slice(0, 2600),
           buttons: Array.from(document.querySelectorAll('button')).map((b) => ({
             text: (b.innerText || '').trim().slice(0, 36), disabled: !!b.disabled,
             aria: b.getAttribute('aria-label'), testid: b.getAttribute('data-testid') })),
           testids: Array.from(document.querySelectorAll('[data-testid]')).map((n) => n.getAttribute('data-testid')),
           dialogs: Array.from(document.querySelectorAll('[role=dialog],.v8-sheet,[class*=sheet]')).map((n) => ({
             cls: String(n.className).slice(0, 40), text_len: (n.innerText || '').length,
             text_head: (n.innerText || '').slice(0, 200) })),
           aria_live: Array.from(document.querySelectorAll('[aria-live]')).map((n) => (n.innerText || '').trim().slice(0, 200)),
           receipts: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
           pending: /正在|稍后|排队/.test(body), scroll_overflow_px: document.documentElement.scrollHeight - innerHeight };
};

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, journey_id: JID, launches: 1, contexts: 1,
                clicks: 0, legs: [] };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                         httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  await ctx.addInitScript(([id]) => { localStorage.setItem('citynexus.v8.journey_id', id); }, [JID]);
  const page = await ctx.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let rb = null, receipt = null, code = null;
    try {
      const b = await r.body(); rb = b.length;
      if (r.status() >= 400) {
        try { const j = JSON.parse(Buffer.from(b).toString('utf8'));
              receipt = (j.error && j.error.error_receipt_id) || null; code = (j.error && j.error.code) || null; }
        catch (e) { receipt = 'NOT_JSON'; }
      }
    } catch (e) { rb = 'READ_FAILED'; }
    out.legs.push({ url: r.url().replace(/^https?:\/\/[^/]+/, ''), m: r.request().method(), status: r.status(),
                    ct: r.headers()['content-type'] || null, req_bytes: (r.request().postData() || '').length,
                    resp_bytes: rb, server_receipt_id: receipt, server_code: code });
  });
  await page.goto(BASE + '/v8/trips', { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(9000);
  out.before = await page.evaluate(SNAP);
  out.shots = { before: await shot(page, 'J1_trips_before') };
  const lb = out.legs.length;
  const btn = page.locator('button').filter({ hasText: 'AI 帮我规划' }).first();
  out.button_found = await btn.count();
  out.button_state = out.button_found ? await btn.evaluate((n) => ({ disabled: !!n.disabled,
    text: (n.innerText || '').trim(), top: Math.round(n.getBoundingClientRect().top) })) : null;
  if (out.button_found) {
    out.press = await btn.click({ timeout: 5000 }).then(() => 'clicked')
      .catch((e) => 'click_failed: ' + String(e.message).slice(0, 70));
    out.clicks += 1;
    await page.waitForTimeout(9000);
    out.after = await page.evaluate(SNAP);
    out.legs_for_the_press = out.legs.slice(lb);
    out.shots.after = await shot(page, 'J2_after_press');
    /* if a sheet or panel opened, read what it offers */
    out.after_offer = (out.after.text.match(/[^\n]*(AI|规划|不可用|关|停用|稍后|试)[^\n]*/g) || []).slice(0, 12);
  }
  out.health = (() => {
    const h = out.legs.find((l) => l.url === '/api/v1/health');
    return h ? [h.status, h.resp_bytes] : null;
  })();
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r7_ai_disabled.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ before_len: out.before.text_len, button: out.button_state, press: out.press,
    after_len: out.after ? out.after.text_len : null, legs_for_the_press: (out.legs_for_the_press || []).map(
      (l) => [l.m, l.url, l.status, l.req_bytes, l.resp_bytes, l.server_code, l.server_receipt_id]),
    after_offer: out.after_offer, dialogs: out.after ? out.after.dialogs : null,
    aria_live: out.after ? out.after.aria_live : null, health: out.health }, null, 1));
  console.log('AFTER TEXT:\n' + (out.after ? out.after.text.slice(0, 1200) : '(none)'));
  await ctx.close();
  await browser.close();
})().catch((e) => { console.error('R7AI FAILED: ' + String((e && e.message) || e)); process.exit(9); });
