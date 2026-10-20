/* Building walk r3: does tapping the WORDS flip the auto-execution switch -- and by which event?
 *
 * r2 tapped the label with a raw touchscreen tap and saw no state change, which is not the same as "the
 * words are dead": a browser activates the wrapped control from a label only on a real click, and a touch
 * tap may never produce one.  So r3 counts the events instead of guessing from the outcome: it listens for
 * click on the input, change on the input, and toggle on the row, then sends a click at the words, and
 * separately a touch tap at the same point, and reports which route moved the state.
 * argv: node walk_me_toggle_r3.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/me_toggle_r3.json";
const run = { schema: "CNX_BUILDING_ME_TOGGLE_R3", base: BASE, arms: [], errors: [] };

async function gotoMe(page) {
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1500);
  const m = page.locator("[data-testid='v8-mobile-menu']").first();
  await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await page.waitForTimeout(900);
  const e2 = page.locator("[data-testid='v8-drawer-entry-me']").first();
  await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await page.waitForTimeout(1300);
}

async function arm(page) {
  return page.evaluate(() => {
    const el = document.querySelector("[data-testid='me-mode-toggle']");
    if (!el) return null;
    el.scrollIntoViewIfNeeded();
    window.__cnx = { input_click: 0, input_change: 0, label_click: 0, checked: el.checked };
    el.addEventListener("click", () => { window.__cnx.input_click++; });
    el.addEventListener("change", () => { window.__cnx.input_change++; window.__cnx.checked = el.checked; });
    const lab = el.closest("label");
    if (lab) lab.addEventListener("click", () => { window.__cnx.label_click++; });
    const b = el.getBoundingClientRect(), lb = lab ? lab.getBoundingClientRect() : null;
    return { input_box: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)],
             label_box: lb ? [Math.round(lb.x), Math.round(lb.y), Math.round(lb.width), Math.round(lb.height)] : null,
             checked_at_arm: el.checked };
  });
}

async function probe(page, how) {
  const geo = await page.evaluate(() => {
    const el = document.querySelector("[data-testid='me-mode-toggle']");
    const lab = el.closest("label");
    const lb = lab.getBoundingClientRect();
    return { x: Math.round(lb.x + 6), y: Math.round(lb.y + lb.height / 2) };
  });
  if (how === "mouse") await page.mouse.click(geo.x, geo.y);
  else await page.touchscreen.tap(geo.x, geo.y);
  await page.waitForTimeout(1200);
  const state = await page.evaluate(() => {
    const el = document.querySelector("[data-testid='me-mode-toggle']");
    const row = el.closest("label").parentElement;
    const t = (row.innerText || "").replace(/\s+/g, " ");
    return { counts: window.__cnx, checked_now: el.checked, says_on: /自动执行已开启/.test(document.body.innerText) };
  });
  return { how, point: geo, ...state };
}

(async () => {
  const browser = await chromium.launch();
  for (const how of ["mouse", "touch"]) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true,
      hasTouch: true, serviceWorkers: "block" });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => run.errors.push(String(e).slice(0, 160)));
    try {
      await gotoMe(page);
      const armed = await arm(page);
      if (!armed) { run.arms.push({ how, error: "NO_TOGGLE" }); await ctx.close(); continue; }
      const r = await probe(page, how);
      run.arms.push({ how, armed, ...r,
        moved: r.checked_now !== armed.checked_at_arm,
        fired_input_click: r.counts.input_click - 0, fired_change: r.counts.input_change });
      await ctx.close();
    } catch (e) { run.arms.push({ how, error: String(e).slice(0, 200) }); try { await ctx.close(); } catch (_) {} }
  }
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify(run.arms.map(a => ({ how: a.how, moved: a.moved,
    checked: [a.armed && a.armed.checked_at_arm, a.checked_now], counts: a.counts,
    point: a.point, input_box: a.armed && a.armed.input_box, label_box: a.armed && a.armed.label_box,
    error: a.error || null })), null, 1));
  await browser.close();
})();
