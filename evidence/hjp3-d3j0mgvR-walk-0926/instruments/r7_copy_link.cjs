/* ORD-0357 acceptance on the phone: copy the journey's own link, then open it in a device that never saw the app.

The control is a product contract, not a guess - the served bundle carries `data-testid="journey-link-copy"` with
`data-cnx-field="journey_link_url"` and a sibling `journey-link-message`, plus four distinct failure sentences
(no journey open / insecure context / clipboard refused / success). This pass reads what the screen actually does:
finds the control, presses it, reads the clipboard back inside the page, quotes the message line, then hands the
copied URL to a brand-new context and compares the two screens by a hash of the rendered text and by the button
inventory - not by my memory of what I clicked.

One browser launch, two fresh contexts (the tile-channel warning again). Lane: 390x844@3, touch, zh-CN, no proxy;
clipboard permission granted only to my own context. Password used as httpCredentials only.
Usage: node r7_copy_link.cjs <outDir> <journey-id>
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
  const digest = async (t) => { const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(t));
    return Array.from(new Uint8Array(buf)).map((x) => x.toString(16).padStart(2, '0')).join(''); };
  const body = document.body ? (document.body.innerText || '') : '';
  const q = (s) => document.querySelector(s);
  const copy = q('[data-testid="journey-link-copy"]');
  const msg = q('[data-testid="journey-link-message"]');
  return {
    url: location.href, text_len: body.length, text_head: body.slice(0, 1200),
    copy_button_present: !!copy, copy_button_disabled: copy ? !!copy.disabled : null,
    copy_button_text: copy ? (copy.innerText || '').trim() : null,
    copy_button_field_attr: copy ? copy.getAttribute('data-cnx-field') : null,
    copy_button_top: copy ? Math.round(copy.getBoundingClientRect().top) : null,
    message_present: !!msg, message_text: msg ? (msg.innerText || '').trim() : null,
    message_field_attr: msg ? msg.getAttribute('data-cnx-field') : null,
    action_wrap_present: !!q('.journey-link-action'),
    inbox_markers: ['.journey-link-action', '[data-testid="journey-link-copy"]', '[data-testid="inbox-extract"]']
      .map((s) => ({ sel: s, found: !!q(s) })),
    buttons: Array.from(document.querySelectorAll('button')).map((b) => (b.innerText || '').trim()).filter(Boolean),
    testids: Array.from(document.querySelectorAll('[data-testid]')).map((n) => n.getAttribute('data-testid')),
    body_sha: body ? await digest(body) : null, ls_keys: Object.keys(localStorage),
    journey_id: localStorage.getItem('citynexus.v8.journey_id'),
  };
};

async function shot(page, name) {
  const p = path.join(OUT, name + '.png');
  await page.screenshot({ path: p });
  return { file: path.basename(p), abs: p, exists: fs.existsSync(p),
           bytes: fs.existsSync(p) ? fs.statSync(p).size : 0, sha256: SHA(fs.readFileSync(p)) };
}

async function ctx(browser, seed, legs) {
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
                ct: r.headers()['content-type'] || null, resp_bytes: rb });
  });
  return { c, page };
}

(async () => {
  const out = { started_at: new Date().toISOString(), base: BASE, journey_id: JID, launches: 1, contexts: 2 };
  const browser = await chromium.launch({ headless: true, args: ['--no-proxy-server'] });
  out.chromium_version = browser.version();
  const legs1 = [];
  const a = await ctx(browser, JID, legs1);
  await a.page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 90000 });
  await a.page.waitForTimeout(13000);
  out.at_hub = await a.page.evaluate(STATE);
  out.shots = { hub: await shot(a.page, 'G1_hub_with_journey') };
  if (!out.at_hub.copy_button_present) {
    /* the workbench entry is labelled 打开行程工作台 on this screen; try it, then re-read */
    const b = a.page.getByRole('button', { name: '打开行程工作台', exact: false }).first();
    out.tried_workbench = await b.count() > 0;
    if (out.tried_workbench) {
      await b.click({ timeout: 5000 }).catch((e) => { out.workbench_click_error = e.message.slice(0, 60); });
      await a.page.waitForTimeout(6000);
      out.after_workbench_click = await a.page.evaluate(STATE);
      out.shots.workbench = await shot(a.page, 'G2_workbench');
    }
  }
  const where = (out.after_workbench_click && out.after_workbench_click.copy_button_present)
    ? out.after_workbench_click : out.at_hub;
  out.copy_screen = where.url;
  if (where.copy_button_present) {
    out.press = await a.page.locator('[data-testid="journey-link-copy"]').first()
      .click({ timeout: 5000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 60));
    await a.page.waitForTimeout(1500);
    out.after_press = await a.page.evaluate(STATE);
    out.clipboard = await a.page.evaluate(() => navigator.clipboard.readText().catch((e) => 'READ_FAILED: ' + e.name));
    out.shots.copied = await shot(a.page, 'G3_after_copy');
  } else {
    out.press = 'NO_CONTROL_ON_EITHER_SCREEN';
    out.clipboard = null;
    out.testids_seen_on_both_screens = { hub: out.at_hub.testids,
                                         workbench: out.after_workbench_click ? out.after_workbench_click.testids : null };
  }
  out.legs1 = legs1.slice();
  await a.c.close();

  const link = typeof out.clipboard === 'string' && /^https?:\/\//.test(out.clipboard) ? out.clipboard : null;
  if (link) {
    const legs2 = [];
    const b2 = await ctx(browser, null, legs2);
    await b2.page.goto(link, { waitUntil: 'load', timeout: 90000 });
    await b2.page.waitForTimeout(14000);
    out.reopen = await b2.page.evaluate(STATE);
    out.reopen_legs = legs2.slice();
    out.shots.reopen = await shot(b2.page, 'G4_reopened_link');
    out.acceptance = {
      link_copied: link,
      reopened_url: out.reopen.url,
      same_rendered_text_as_the_copy_screen: out.reopen.body_sha === where.body_sha,
      copy_screen_text_len: where.text_len, reopen_text_len: out.reopen.text_len,
      copy_screen_sha: where.body_sha, reopen_sha: out.reopen.body_sha,
      journey_id_in_the_new_device: out.reopen.journey_id,
      ls_keys_in_the_new_device: out.reopen.ls_keys,
      buttons_on_the_copy_screen: where.buttons,
      buttons_after_reopen: out.reopen.buttons,
      copy_affordance_still_there_after_reopen: out.reopen.copy_button_present };
    await b2.c.close();
  } else {
    out.acceptance = 'SKIPPED - no URL came back from the clipboard';
  }
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r7_copy_link.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ copy_on_hub: out.at_hub.copy_button_present, tried_workbench: out.tried_workbench,
    after_click: out.after_workbench_click ? { url: out.after_workbench_click.url, copy: out.after_workbench_click.copy_button_present,
      disabled: out.after_workbench_click.copy_button_disabled, text: out.after_workbench_click.copy_button_text,
      top: out.after_workbench_click.copy_button_top } : null,
    press: out.press, clipboard: out.clipboard, message_after_press: out.after_press ? out.after_press.message_text : null,
    acceptance: out.acceptance && out.acceptance.same_rendered_text_as_the_copy_screen !== undefined
      ? { same_text: out.acceptance.same_rendered_text_as_the_copy_screen,
          new_device_journey_id: out.acceptance.journey_id_in_the_new_device,
          reopen_url: out.acceptance.reopened_url, still_there: out.acceptance.copy_affordance_still_there_after_reopen }
      : out.acceptance,
    testids_if_missing: out.testids_seen_on_both_screens }, null, 1));
  await browser.close();
})().catch((e) => { console.error('R7COPY FAILED: ' + String((e && e.message) || e)); process.exit(9); });
