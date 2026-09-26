/* ORD-0357 acceptance, final leg: the trips tab has its own sub-tab, and the copy control lives behind it.

The previous pass got as far as `/v8/trips` and stopped - that screen carries a `trips-tab-bookings` anchor and
only 114 characters of visible text, so the inbox panel is one more tap away. This pass makes that tap, presses
the 复制行程链接 control when it appears, reads the clipboard back inside the page, quotes the message line, and then
opens the copied link in a device that has never seen the app, comparing the two screens by a hash of the rendered
text rather than by memory.

It also copies out the 114-character trips screen verbatim, because how little a user sees there is itself a
reading.

One browser launch, two fresh contexts, no proxy, clipboard permission only in my own context; the tunnel password
is read from the named file and used only as httpCredentials.
Usage: node r7_copy_link_r4.cjs <outDir> <journey-id>
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
    url: location.href, text_len: body.length, text: body.slice(0, 2400),
    copy_button_present: !!copy, copy_button_disabled: copy ? !!copy.disabled : null,
    copy_button_text: copy ? (copy.innerText || '').trim() : null,
    copy_button_field_attr: copy ? copy.getAttribute('data-cnx-field') : null,
    copy_button_top: copy ? Math.round(copy.getBoundingClientRect().top) : null,
    copy_button_in_view: copy ? (copy.getBoundingClientRect().top >= 0
      && copy.getBoundingClientRect().bottom <= innerHeight) : null,
    message_present: !!msg, message_text: msg ? (msg.innerText || '').trim() : null,
    message_field_attr: msg ? msg.getAttribute('data-cnx-field') : null,
    testids: Array.from(document.querySelectorAll('[data-testid]')).map((n) => n.getAttribute('data-testid')),
    buttons: Array.from(document.querySelectorAll('button')).map((b) => ({
      text: (b.innerText || '').trim().slice(0, 36), aria: b.getAttribute('aria-label'),
      testid: b.getAttribute('data-testid'), disabled: !!b.disabled })).filter((x) => x.text || x.aria || x.testid),
    body_sha: body ? await digest(body) : null, ls_keys: Object.keys(localStorage),
    journey_id: localStorage.getItem('citynexus.v8.journey_id'),
    is_secure_context: window.isSecureContext, clipboard_api: !!navigator.clipboard,
    receipts: body.match(/\bCNX-[A-Z0-9]{6,12}\b/g) || [],
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
  const out = { started_at: new Date().toISOString(), base: BASE, journey_id: JID, launches: 1, contexts: 2 };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const legs1 = [];
  const a = await newCtx(browser, JID, legs1);
  await a.page.goto(BASE + '/v8/trips', { waitUntil: 'load', timeout: 90000 });
  await a.page.waitForTimeout(9000);
  out.trips_as_landed = await a.page.evaluate(STATE);
  out.shots = { trips: await shot(a.page, 'I1_trips_as_landed') };
  const tab = a.page.locator('[data-testid="trips-tab-bookings"]').first();
  out.tab_found = await tab.count();
  if (out.tab_found) {
    out.tab_press = await tab.click({ timeout: 5000 }).then(() => 'clicked')
      .catch((e) => 'click_failed: ' + String(e.message).slice(0, 70));
    await a.page.waitForTimeout(4000);
    out.on_bookings = await a.page.evaluate(STATE);
    out.shots.bookings = await shot(a.page, 'I2_bookings_tab');
  }
  const where = (out.on_bookings && out.on_bookings.copy_button_present) ? out.on_bookings : out.trips_as_landed;
  if (where.copy_button_present) {
    out.press = await a.page.locator('[data-testid="journey-link-copy"]').first()
      .click({ timeout: 5000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 70));
    await a.page.waitForTimeout(1800);
    out.after_press = await a.page.evaluate(STATE);
    out.clipboard = await a.page.evaluate(() => navigator.clipboard.readText().catch((e) => 'READ_FAILED: ' + e.name));
    out.shots.copied = await shot(a.page, 'I3_after_copy');
  } else {
    out.press = 'CONTROL_NOT_PRESENT_ON_EITHER_TAB';
    out.clipboard = null;
  }
  out.legs1 = legs1.slice();
  await a.c.close();

  const link = typeof out.clipboard === 'string' && /^https?:\/\//.test(out.clipboard) ? out.clipboard : null;
  if (link) {
    const legs2 = [];
    const b = await newCtx(browser, null, legs2);
    await b.page.goto(link, { waitUntil: 'load', timeout: 90000 });
    await b.page.waitForTimeout(15000);
    out.reopen = await b.page.evaluate(STATE);
    out.reopen_legs = legs2.slice();
    out.shots.reopen = await shot(b.page, 'I4_reopened_link');
    out.acceptance = {
      link, reopened_url: out.reopen.url,
      same_rendered_text_as_the_copy_screen: out.reopen.body_sha === (out.after_press || where).body_sha,
      copy_screen_len: (out.after_press || where).text_len, reopen_len: out.reopen.text_len,
      copy_screen_sha: (out.after_press || where).body_sha, reopen_sha: out.reopen.body_sha,
      journey_id_now_in_the_device: out.reopen.journey_id, ls_keys: out.reopen.ls_keys,
      control_still_there: out.reopen.copy_button_present,
      reopen_text_head: out.reopen.text.slice(0, 600),
      buttons_copy_screen: (out.after_press || where).buttons.map((x) => x.text).slice(0, 20),
      buttons_reopen: out.reopen.buttons.map((x) => x.text).slice(0, 20) };
    await b.c.close();
  } else {
    out.acceptance = 'SKIPPED - the clipboard never gave back a URL';
  }
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r7_copy_link_r4.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ trips_len: out.trips_as_landed.text_len, tab_found: out.tab_found,
    tab_press: out.tab_press, bookings: out.on_bookings ? { len: out.on_bookings.text_len,
      copy: out.on_bookings.copy_button_present, disabled: out.on_bookings.copy_button_disabled,
      text: out.on_bookings.copy_button_text, top: out.on_bookings.copy_button_top,
      in_view: out.on_bookings.copy_button_in_view, testids: out.on_bookings.testids.filter(
        (x) => /inbox|journey-link|bookings/.test(x)) } : null,
    press: out.press, clipboard: out.clipboard, message: out.after_press ? out.after_press.message_text : null,
    msg_field: out.after_press ? out.after_press.message_field_attr : null,
    acceptance: out.acceptance, secure: out.trips_as_landed.is_secure_context }, null, 1));
  console.log('TRIPS AS LANDED:\n' + out.trips_as_landed.text.slice(0, 600));
  await browser.close();
})().catch((e) => { console.error('R7C4 FAILED: ' + String((e && e.message) || e)); process.exit(9); });
