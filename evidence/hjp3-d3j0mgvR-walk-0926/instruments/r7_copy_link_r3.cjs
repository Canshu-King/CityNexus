/* ORD-0357 acceptance, third attempt at finding the control - and the reason the first two missed it is itself
a reading.

What happened: on `/v8/hub` the visible text of a button is 「旅行票夹」, yet
`getByRole('button', { name: '旅行票夹', exact: false })` found nothing. So this pass clicks by the DOM text it can
see and by the stable `data-testid` anchors the hub exposes (nav-trips, nav-me, …), and it records, for every
stop, the button's own accessible-name fields (aria-label, textContent, testid) so the gap between what a screen
reader would announce and what the eye reads is measured rather than assumed.

Then the real question: press 复制行程链接, read the clipboard back inside the page, quote the message line, and
open that copied link in a device that never saw the app - and compare the two screens by a hash of the rendered
text.

One browser launch, two fresh contexts, no proxy, clipboard permission only on my own context.
Usage: node r7_copy_link_r3.cjs <outDir> <journey-id>
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

const STATE = async () => {
  const digest = async (t) => {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(t));
    return Array.from(new Uint8Array(buf)).map((x) => x.toString(16).padStart(2, '0')).join('');
  };
  const body = document.body ? (document.body.innerText || '') : '';
  const q = (s) => document.querySelector(s);
  const copy = q('[data-testid="journey-link-copy"]');
  const msg = q('[data-testid="journey-link-message"]');
  return {
    url: location.href, text_len: body.length, text_head: body.slice(0, 1400),
    copy_button_present: !!copy, copy_button_disabled: copy ? !!copy.disabled : null,
    copy_button_text: copy ? (copy.innerText || '').trim() : null,
    copy_button_field_attr: copy ? copy.getAttribute('data-cnx-field') : null,
    copy_button_top: copy ? Math.round(copy.getBoundingClientRect().top) : null,
    copy_button_in_view: copy ? (copy.getBoundingClientRect().top >= 0
      && copy.getBoundingClientRect().bottom <= innerHeight) : null,
    message_present: !!msg, message_text: msg ? (msg.innerText || '').trim() : null,
    message_field_attr: msg ? msg.getAttribute('data-cnx-field') : null,
    buttons: Array.from(document.querySelectorAll('button')).map((b) => ({
      text: (b.innerText || '').trim().slice(0, 40), aria: b.getAttribute('aria-label'),
      testid: b.getAttribute('data-testid'), title: b.getAttribute('title') })).filter((x) => x.text || x.aria || x.testid),
    testids: Array.from(document.querySelectorAll('[data-testid]')).map((n) => n.getAttribute('data-testid')),
    body_sha: body ? await digest(body) : null, ls_keys: Object.keys(localStorage),
    journey_id: localStorage.getItem('citynexus.v8.journey_id'),
    is_secure_context: window.isSecureContext, clipboard_api: !!navigator.clipboard,
  };
};

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

async function newCtx(browser, seed, legs) {
  const c = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                       hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai',
                                       permissions: ['clipboard-read', 'clipboard-write'],
                                       httpCredentials: { origin: BASE, username: AUTH[0], password: AUTH[1] } });
  await c.addInitScript(([id]) => {
    if (id) localStorage.setItem('citynexus.v8.journey_id', id);
    else Object.keys(localStorage).filter((k) => /citynexus/.test(k)).forEach((k) => localStorage.removeItem(k));
  }, [seed]);
  const page = await c.newPage();
  page.on('response', async (r) => {
    if (r.url().indexOf('/api/') < 0) return;
    let rb = null;
    try { rb = (await r.body()).length; } catch (e) { rb = 'READ_FAILED'; }
    legs.push({ url: r.url().replace(/^https?:\/\/[^/]+/, ''), m: r.request().method(), status: r.status(),
                ct: r.headers()['content-type'] || null, resp_bytes: rb,
                from_service_worker: r.fromServiceWorker() });
  });
  return { c, page };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, journey_id: JID, launches: 1, contexts: 2,
                stops: [] };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const legs1 = [];
  const a = await newCtx(browser, JID, legs1);
  await a.page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 90000 });
  await a.page.waitForTimeout(13000);
  out.hub = await a.page.evaluate(STATE);
  out.shots = { hub: await shot(a.page, 'H1_hub') };

  const wanted = [['nav-trips', '[data-testid="nav-trips"]'], ['nav-me', '[data-testid="nav-me"]'],
                  ['旅行票夹-by-text', null], ['行程工作台-by-text', null], ['收件箱-by-text', null]];
  for (const [label, sel] of wanted) {
    const clicker = sel ? a.page.locator(sel).first()
      : a.page.locator('button').filter({ hasText: label.replace('-by-text', '') }).first();
    const found = await clicker.count();
    const stop = { label, selector: sel || 'button:has-text', found, before_url: (out.last || out.hub).url };
    if (!found) { out.stops.push(stop); continue; }
    stop.role_name_probe = await a.page.getByRole('button', { name: label.replace('-by-text', ''), exact: false })
      .count().catch(() => 'ERR');
    await clicker.click({ timeout: 5000 }).catch((e) => { stop.click_error = String(e.message).slice(0, 70); });
    await a.page.waitForTimeout(3500);
    const st = await a.page.evaluate(STATE);
    out.last = st;
    stop.after = { url: st.url, text_len: st.text_len, copy_button_present: st.copy_button_present,
                   copy_button_disabled: st.copy_button_disabled, copy_button_text: st.copy_button_text,
                   copy_button_top: st.copy_button_top, copy_button_in_view: st.copy_button_in_view,
                   message_text: st.message_text, testids_with_inbox_or_link: st.testids.filter(
                     (x) => /inbox|journey-link|bookings/.test(x)) };
    out.stops.push(stop);
    if (st.copy_button_present) { out.found_stop = label; out.on_copy_screen = st;
                                  out.shots.found = await shot(a.page, 'H2_found_control'); break; }
  }

  if (out.on_copy_screen) {
    out.press = await a.page.locator('[data-testid="journey-link-copy"]').first()
      .click({ timeout: 5000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 70));
    await a.page.waitForTimeout(1800);
    out.after_press = await a.page.evaluate(STATE);
    out.clipboard = await a.page.evaluate(() => navigator.clipboard.readText().catch((e) => 'READ_FAILED: ' + e.name));
    out.shots.copied = await shot(a.page, 'H3_after_copy');
    out.legs1 = legs1.slice();
  } else {
    out.press = 'CONTROL_NOT_FOUND_ON_ANY_STOP';
    out.legs1 = legs1.slice();
    out.all_testids_by_stop = out.stops.map((s) => ({ label: s.label, after: s.after && s.after.url,
      testids: (out.last && out.last.testids) || null }));
  }
  await a.c.close();

  const link = typeof out.clipboard === 'string' && /^https?:\/\//.test(out.clipboard) ? out.clipboard : null;
  if (link) {
    const legs2 = [];
    const b = await newCtx(browser, null, legs2);
    await b.page.goto(link, { waitUntil: 'load', timeout: 90000 });
    await b.page.waitForTimeout(14000);
    out.reopen = await b.page.evaluate(STATE);
    out.reopen_legs = legs2.slice();
    out.shots.reopen = await shot(b.page, 'H4_reopened');
    out.acceptance = {
      link: link, reopened_url: out.reopen.url,
      same_rendered_text_as_the_copy_screen: out.reopen.body_sha === out.after_press.body_sha,
      copy_screen_len: out.after_press.text_len, reopen_len: out.reopen.text_len,
      copy_screen_sha: out.after_press.body_sha, reopen_sha: out.reopen.body_sha,
      journey_id_in_the_new_device: out.reopen.journey_id, ls_keys: out.reopen.ls_keys,
      control_still_there: out.reopen.copy_button_present,
      buttons_copy_screen: out.after_press.buttons.map((x) => x.text).slice(0, 24),
      buttons_reopen: out.reopen.buttons.map((x) => x.text).slice(0, 24) };
    await b.c.close();
  } else {
    out.acceptance = 'SKIPPED - the clipboard never gave back a URL';
  }
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r7_copy_link_r3.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ hub_buttons_missing_for_role: out.stops.map((s) => [s.label, s.found, s.role_name_probe]),
    found: out.found_stop || null, on_screen: out.on_copy_screen ? { url: out.on_copy_screen.url,
      disabled: out.on_copy_screen.copy_button_disabled, text: out.on_copy_screen.copy_button_text,
      top: out.on_copy_screen.copy_button_top, in_view: out.on_copy_screen.copy_button_in_view } : null,
    press: out.press, clipboard: out.clipboard, message: out.after_press ? out.after_press.message_text : null,
    secure: out.hub.is_secure_context, acceptance: out.acceptance }, null, 1));
  await browser.close();
})().catch((e) => { console.error('R7C3 FAILED: ' + String((e && e.message) || e)); process.exit(9); });
