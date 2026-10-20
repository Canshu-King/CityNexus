/* Building walk, cell ten, step one: name the two control families the census keeps reporting.
 *
 * The published census lists a 42-tall thing whose words are the Copilot opener on eight of seventeen
 * screens (testid null, so the row alone does not say what it is) and a 40-tall tab strip on the trips
 * page.  Before any CSS this arm records, for each candidate: the element's tag/class/role, its painted and
 * pressable box, where a centre hit-test actually lands, and what a press changes on screen — a chip that
 * opens a panel and a tab that swaps a list are different defects from a chip that just sits there, and the
 * fix for "cannot be hit" is not the fix for "hits but nothing answers".
 * argv: node tap_families_r1.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/tap_families.json";
const run = { schema: "CNX_TAP_FAMILIES_R1", base: BASE, viewport: { width: 390, height: 844 },
  started: new Date().toString(), screens: [], taps: [], errors: [] };

const SRC = (sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  el.scrollIntoViewIfNeeded();
  const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
  const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
  let minx = cx, maxx = cx, miny = cy, maxy = cy;
  for (let dx = -40; dx <= 40; dx += 2) for (let dy = -40; dy <= 40; dy += 2) {
    const t = document.elementFromPoint(cx + dx, cy + dy);
    if (t && (t === el || el.contains(t))) { minx = Math.min(minx, cx + dx); maxx = Math.max(maxx, cx + dx);
      miny = Math.min(miny, cy + dy); maxy = Math.max(maxy, cy + dy); }
  }
  const top = document.elementFromPoint(cx, cy);
  return { sel, tag: el.tagName, cls: String(el.className || "").slice(0, 54),
    role: el.getAttribute("role"), testid: el.getAttribute("data-testid"),
    words: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 30),
    painted: [Math.round(b.width), Math.round(b.height)],
    pressable: [Math.round(maxx - minx + 2), Math.round(maxy - miny + 2)],
    centre_lands: !!top && (top === el || el.contains(top)),
    centre_hit: top ? (top.getAttribute("data-testid") || top.tagName) : null,
    pe: s.pointerEvents, cursor: s.cursor, min_h: s.minHeight, tabindex: el.getAttribute("tabindex") };
};

async function go(page, entry) {
  const m = page.locator("[data-testid='v8-mobile-menu']").first();
  await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await page.waitForTimeout(900);
  const e2 = page.locator("[data-testid='v8-drawer-entry-" + entry + "']").first();
  await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await page.waitForTimeout(1800);
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.errors.push(String(e).slice(0, 160)));
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1600);

  // find the Copilot opener wherever it lives: by visible words, not by a guessed class
  for (const scr of ["hub", "trips", "map"]) {
    if (scr !== "hub") await go(page, scr);
    const found = await page.evaluate((src) => {
      const out = [];
      const cands = Array.from(document.querySelectorAll("button,[role='button'],a")).filter((el) => {
        const b = el.getBoundingClientRect(); const t = (el.innerText || "").trim();
        return b.height > 0 && /Copilot/i.test(t) && b.height < 44;
      });
      cands.slice(0, 2).forEach((el) => {
        el.setAttribute("data-cnx-probe", String(out.length));
        out.push({ marker: "[data-cnx-probe='" + (out.length) + "']", words: el.innerText.trim().slice(0, 26) });
      });
      const tabs = Array.from(document.querySelectorAll("button,[role='tab'],a")).filter((el) => {
        const b = el.getBoundingClientRect(); const t = (el.innerText || "").trim();
        return b.height > 0 && b.height < 44 && ["行程", "住宿", "预订", "花费"].indexOf(t) >= 0;
      });
      tabs.slice(0, 4).forEach((el) => {
        el.setAttribute("data-cnx-probe", "tab-" + out.length + "-" + el.innerText.trim());
        out.push({ marker: "[data-cnx-probe='tab-" + (out.length) + "-" + el.innerText.trim() + "']",
          words: el.innerText.trim() });
      });
      return out;
    }, null);
    const rows = [];
    for (const c of found) {
      const r = await page.evaluate(({ c, src }) => eval(src)(c.marker), { c, src: SRC.toString() });
      if (r) rows.push({ ...r, words_found: c.words });
    }
    run.screens.push({ screen: scr, path: await page.evaluate(() => location.pathname), rows });
    await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(1200);
    if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
    await page.waitForTimeout(1500);
  }

  // does a press answer? the Copilot opener should change what is on screen
  const opener = run.screens[0].rows.find((r) => /Copilot/i.test(r.words || ""));
  if (opener) {
    const before = await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").length);
    await page.locator(opener.sel).first().click();
    await page.waitForTimeout(2000);
    const after = await page.evaluate(() => ({
      chars: document.body.innerText.replace(/\s+/g, " ").length,
      dock: !!document.querySelector("[data-testid*='copilot' i],[class*='copilot' i]") }));
    run.taps.push({ what: opener.sel, words: opener.words, chars_before: before,
      chars_after: after.chars, answered: after.chars !== before || after.dock, dock_present: after.dock });
  }
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ screens: run.screens.map(s => ({ screen: s.screen, path: s.path,
    rows: s.rows.map(r => ({ words: r.words_found || r.words, tag: r.tag, cls: (r.cls || "").slice(0, 30),
      painted: r.painted, pressable: r.pressable, pe: r.pe, cursor: r.cursor, min_h: r.min_h,
      lands: r.centre_lands, hit: r.centre_hit, role: r.role, tabindex: r.tabindex })) })),
    taps: run.taps, errors: run.errors.length }, null, 1));
  await browser.close();
})();
