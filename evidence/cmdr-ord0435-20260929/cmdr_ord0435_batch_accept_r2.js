/* CMDR ORD-0435 acceptance r2 - drive the POI batch the way a traveller does, and assert on rendered text.
 *
 * r1 was wrong, not the product: it never ran a discovery (the panel only renders cards after the goal
 * textarea holds >=3 chars and the submit button is pressed), and it treated "any visible button" as a
 * tick -- so its first click landed on the topbar hamburger, opened the drawer, and then reported
 * `batchBarPresent: false`. Its overlap check also returned "clears the nav" for a bar that did not
 * exist, which is a vacuous pass. r2 fixes both: every geometry assertion is gated on the bar existing,
 * and a missing prerequisite aborts the run instead of printing a green.
 *
 * Selection state is read from the control's OWN rendered label (`.v8-pick-box-text` flips between the
 * pick and unpick copy), never from `data-picked`/`aria-checked`.
 * Usage: node cmdr_ord0435_batch_accept_r2.js <base> <out-file> [locale]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "zh";
if (!BASE || !OUT) { console.error("usage: node cmdr_ord0435_batch_accept_r2.js <base> <out-file> [locale]"); process.exit(2); }

const GOAL = { zh: "想找便宜又好吃的夜市", en: "cheap and tasty night markets" };
const MACHINE = [/\\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\\b/, /\b(?:Asia|Europe|America|Pacific|Atlantic|Indian|Arctic|Antarctica|Australia)\/[A-Za-z_]+\b/, /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/];

async function barState(page) {
  return page.evaluate(() => {
    const bar = document.querySelector(".v8-batch-bar");
    const nav = document.querySelector(".v8-mobile-nav");
    const nr = nav ? nav.getBoundingClientRect() : null;
    if (!bar) return { present: false, mobileNavTop: nr ? Math.round(nr.top) : null };
    const r = bar.getBoundingClientRect();
    const count = bar.querySelector(".v8-batch-count");
    return {
      present: true,
      text: (bar.innerText || "").trim().replace(/\s+/g, " ").slice(0, 220),
      countText: count ? (count.innerText || "").trim() : null,
      rect: { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) },
      inViewport: r.top >= 0 && r.bottom <= window.innerHeight,
      mobileNavTop: nr ? Math.round(nr.top) : null,
      overlapsMobileNav: nr ? (r.bottom > nr.top && r.top < nr.bottom) : null,
      emptyStateShown: !!bar.querySelector(".v8-batch-empty"),
      finishDisabled: (bar.querySelector('[data-testid="v13-discovery-finish-batch"]') || {}).disabled ?? null,
    };
  });
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e).slice(0, 180)));
  const report = { instrument: "cmdr_ord0435_batch_accept_r2", base: BASE, locale: LOCALE, viewport: "390x844" };

  await page.goto(BASE.replace(/\/$/, "") + "/v8/discover", { waitUntil: "networkidle", timeout: 90000 });
  report.entryAssets = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }
  // close the drawer if a previous state left it open, so it cannot shadow the panel
  if (await page.locator("#v8-nav-drawer").count()) {
    const close = page.locator("#v8-nav-drawer .v8-quiet-button").first();
    if (await close.count()) { await close.click(); await page.waitForTimeout(600); }
  }
  report.drawerOpenBeforeRun = await page.locator("#v8-nav-drawer").count();

  const goal = page.locator("#v13-discovery-goal");
  report.goalFieldFound = await goal.count();
  if (!report.goalFieldFound) {
    report.fatal = "GOAL_FIELD_NOT_FOUND -- the discovery screen did not mount; nothing below was measured";
    fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2));
    await browser.close(); return;
  }
  await goal.fill(GOAL[LOCALE] || GOAL.zh);
  const submit = page.locator('[data-testid="v13-discover-submit"]');
  report.submitEnabledBeforeFill = !(await submit.first().isDisabled());
  await submit.first().click();
  const gotResult = await page.waitForSelector('[data-testid="v13-discovery-result"]', { timeout: 45000 })
    .then(() => true).catch(() => false);
  report.resultRendered = gotResult;
  if (!gotResult) {
    report.fatal = "NO_RESULT_AFTER_SUBMIT -- batch bar and ticks were therefore never reachable";
    report.barAfterSubmit = await barState(page);
    fs.writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2));
    await browser.close(); return;
  }
  await page.waitForTimeout(1500);

  report.before_ticks = await barState(page);
  report.tickControlsFound = await page.locator('[data-testid="v13-pick-candidate"]').count();

  const ticks = [];
  for (const i of [0, 1]) {
    const t = page.locator('[data-testid="v13-pick-candidate"]').nth(i);
    if (!(await t.count())) { ticks.push({ index: i, found: false }); continue; }
    await t.scrollIntoViewIfNeeded();
    const box = await t.boundingBox();
    if (!box) { ticks.push({ index: i, found: true, hasBox: false }); continue; }
    const x = Math.round(box.x + box.width / 2), y = Math.round(box.y + box.height / 2);
    const labelBefore = (await t.locator(".v8-pick-box-text").innerText()).trim();
    const hit = await page.evaluate(([px, py]) => {
      const el = document.elementFromPoint(px, py);
      return el ? { tag: el.tagName.toLowerCase(), inTick: !!(el.closest && el.closest('[data-testid="v13-pick-candidate"]')) } : null;
    }, [x, y]);
    await page.mouse.click(x, y);
    await page.waitForTimeout(1100);
    const labelAfter = (await t.locator(".v8-pick-box-text").innerText()).trim();
    ticks.push({ index: i, found: true, hasBox: true, clickPoint: [x, y], hitTest: hit,
                 labelBefore, labelAfter, labelChanged: labelBefore !== labelAfter });
  }
  report.ticks = ticks;
  report.after_two_ticks = await barState(page);

  // machine tokens inside the bar's own painted text
  const barText = report.after_two_ticks.text || "";
  report.barMachineTokens = MACHINE.map((re) => { const m = barText.match(new RegExp(re.source, "g")); return m ? m : []; }).flat();

  // read the count the traveller sees, then compare with how many ticks are on
  report.countDigitsVisibleToUser = (report.after_two_ticks.countText || "").match(/\d+/g);
  report.pickedLabelsOn = ticks.filter((t) => t.labelChanged).length;

  await page.screenshot({ path: OUT.replace(/\.json$/, "_screen.png") });
  report.screenshot = OUT.replace(/\.json$/, "_screen.png");
  report.pageErrors = errs;
  const b0 = report.before_ticks, b1 = report.after_two_ticks;
  report.verdict = {
    barExistsBeforeAnyTick: !!b0.present,
    emptyStateSentenceRendered: !!b0.emptyStateShown,
    barExistsAfterTicks: !!b1.present,
    countTextChanged: (b0.countText || "") !== (b1.countText || ""),
    countMatchesTicksOn: !!(report.countDigitsVisibleToUser && Number(report.countDigitsVisibleToUser[report.countDigitsVisibleToUser.length - 1]) === report.pickedLabelsOn && report.pickedLabelsOn > 0),
    barPaintedInsideViewport: b1.inViewport === true,
    barDoesNotCoverMobileNav: b1.present ? b1.overlapsMobileNav === false : "NOT_MEASURED_BAR_ABSENT",
    finishButtonEnabledAfterTicks: b1.finishDisabled === false,
    noMachineTokensInBar: report.barMachineTokens.length === 0,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, entry: report.entryAssets, tickControls: report.tickControlsFound,
    countTextBefore: b0.countText, countTextAfter: b1.countText, barTextAfter: (b1.text || "").slice(0, 120),
    verdict: report.verdict, pageErrors: errs.length }, null, 2));
  await browser.close();
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
