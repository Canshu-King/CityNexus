/* Building walk r4: the switch fires a change event and then snaps back -- with the network in the room.
 *
 * r3 showed a tap on the words DOES reach the input (input click + change both fire) and the control is
 * still in the same state a second later, with nothing on screen saying why.  Either the app refused the
 * change (a rule that deserves to be told) or it accepted it and re-rendered from a stale copy (a lie).
 * This arm records every request within two seconds of the tap, the HTTP status of each, the state word
 * the screen shows before and after, and any [role=alert]/[role=status] line that appeared.
 * argv: node walk_me_toggle_r4.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/me_toggle_r4.json";
const run = { schema: "CNX_BUILDING_ME_TOGGLE_R4", base: BASE, started: new Date().toString(),
  taps: [], requests: [], errors: [] };

const words = (page) => page.evaluate(() => {
  const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
  const el = document.querySelector("[data-testid='me-mode-toggle']");
  const lab = el && el.closest("label");
  const sec = lab ? lab.closest("section,div") : null;
  return { checked: el ? el.checked : null, disabled: el ? el.disabled : null,
    row: strip(lab ? lab.innerText : ""), section: strip(sec ? sec.innerText : "").slice(0, 220),
    says_on: /自动执行已开启/.test(document.body.innerText),
    says_advice_only: /仅提供建议/.test(document.body.innerText),
    alerts: Array.from(document.querySelectorAll("[role='alert'],[role='status']"))
      .filter(e => e.getBoundingClientRect().height > 0).map(e => strip(e.innerText).slice(0, 140)).slice(0, 5) };
});

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true,
    hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.errors.push(String(e).slice(0, 200)));
  page.on("request", (r) => { if (/api\/v1/.test(r.url())) run.requests.push({ t: Date.now(), method: r.method(), url: r.url().replace(/^.*api\/v1/, "/api/v1") }); });
  page.on("response", async (r) => {
    const m = run.requests.find((x) => x.url === r.url().replace(/^.*api\/v1/, "/api/v1") && !x.status);
    if (m) { m.status = r.status(); try { const b = await r.text(); m.body = b.slice(0, 260); } catch (_) {} }
  });
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1500);
  const m = page.locator("[data-testid='v8-mobile-menu']").first();
  await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await page.waitForTimeout(900);
  const e2 = page.locator("[data-testid='v8-drawer-entry-me']").first();
  await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await page.waitForTimeout(1300);

  for (let i = 0; i < 3; i++) {
    const before = await words(page);
    const cut = run.requests.length;
    const geo = await page.evaluate(() => {
      const el = document.querySelector("[data-testid='me-mode-toggle']");
      el.scrollIntoViewIfNeeded();
      const lb = el.closest("label").getBoundingClientRect();
      return { x: Math.round(lb.x + 6), y: Math.round(lb.y + lb.height / 2) };
    });
    await page.mouse.click(geo.x, geo.y);
    await page.waitForTimeout(2200);
    const after = await words(page);
    run.taps.push({ i, point: geo, before, after,
      changed: before.checked !== after.checked,
      new_requests: run.requests.slice(cut) });
  }
  run.finished = new Date().toString();
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify(run.taps.map(t => ({ i: t.i, checked: [t.before.checked, t.after.checked],
    changed: t.changed, says_on: [t.before.says_on, t.after.says_on],
    advice_only: [t.before.says_advice_only, t.after.says_advice_only],
    alerts: t.after.alerts, disabled: t.before.disabled,
    requests: t.new_requests.map(r => ({ m: r.method, u: r.url, s: r.status, b: (r.body || "").slice(0, 90) })) })), null, 1));
  await browser.close();
})();
