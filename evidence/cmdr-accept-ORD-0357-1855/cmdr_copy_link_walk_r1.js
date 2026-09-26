/* ORD-0357 first-hand acceptance: does the copy-journey-link control actually put the journey's own
 * link on the clipboard, on the phone face, over the public tunnel?
 *
 * It clicks the control and then reads the clipboard (permissions granted on the context) rather than
 * trusting an aria label or a data attribute -- a button that only *looks* wired up is exactly what
 * this feature would ship as if it worked.
 */
const { chromium } = require(process.env.PW_MODULE || "playwright");
const fs = require("fs");
const auth = fs.readFileSync(process.env.CNX_AUTH_FILE, "utf-8").trim().split("\t");
const BASE = process.argv[2] || "https://jets-saints-tomatoes-eric.trycloudflare.com";
const OUT = process.argv[3] || "patrol/copy_link_0357.json";
const JOURNEY = "22222222-2222-4222-8222-222222222222";

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    httpCredentials: { origin: BASE, username: auth[0], password: auth[1] } });
  await ctx.grantPermissions(["clipboard-read", "clipboard-write"], { origin: BASE });
  const page = await ctx.newPage();
  const report = { base: BASE, at: new Date().toString(), journey: JOURNEY, steps: [] };
  try {
    await page.goto(`${BASE}/v8/${JOURNEY}`, { waitUntil: "networkidle", timeout: 90000 });
    report.screen_head = (await page.locator("body").innerText()).replace(/\s+/g, " ").slice(0, 300);
    // The workbench that carries the control is opened from the Today screen; without this click the
    // control legitimately does not exist in the DOM yet, and that is not a defect.
    // Measured 18:5x: this screen has TWO nodes whose text mentions 工作台 -- a zero-size one (w=0,h=0)
    // that no human can click, and the visible 「打开行程工作台」. A `.first()` locator lands on the
    // hidden one and times out, so the opener is chosen by geometry, not by document order.
    const openers = page.locator("button:has-text(\"工作台\")");
    const n = await openers.count();
    report.opener_candidates = [];
    let opener = null;
    for (let i = 0; i < n; i += 1) {
      const box = await openers.nth(i).boundingBox().catch(() => null);
      const label = (await openers.nth(i).innerText().catch(() => "")).trim();
      report.opener_candidates.push({ i, label, box });
      if (box && box.width > 0 && box.height > 0 && !opener) opener = openers.nth(i);
    }
    report.opener_found = Boolean(opener);
    if (opener) {
      await opener.click({ timeout: 15000 }).catch(e => report.steps.push({ opener_click_error: String(e).slice(0, 120) }));
      await page.waitForTimeout(1500);
    }
    /* The workbench only renders under one of the panel's tabs (measured: `tab === "bookings"` in
     * V8Experience near the JourneyInboxWorkbench mount). Rather than hard-coding a label, walk every
     * tab that is actually clickable until the control appears -- if none of them ever shows it,
     * that IS the finding. */
    const tabLoc = page.locator('[role="tab"], button:has-text("预订"), button:has-text("订单"), button:has-text("行程"), button:has-text("inbox"), button:has-text("Inbox")');
    report.tabs_seen = await tabLoc.count();
    report.tabs_tried = [];
    let direct = page.locator('[data-testid="journey-link-copy"]');
    for (let i = 0; i < Math.min(await tabLoc.count(), 8); i += 1) {
      const box = await tabLoc.nth(i).boundingBox().catch(() => null);
      if (!box || box.width === 0 || box.height === 0) continue;
      const label = (await tabLoc.nth(i).innerText().catch(() => "")).trim().slice(0, 18);
      await tabLoc.nth(i).click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(900);
      direct = page.locator('[data-testid="journey-link-copy"]');
      const c = await direct.count();
      report.tabs_tried.push({ label, copy_controls: c });
      if (c > 0) break;
    }

    let visibleCopy = null;
    for (let i = 0; i < report.direct_found; i += 1) {
      const box = await direct.nth(i).boundingBox().catch(() => null);
      if (box && box.width > 0 && box.height > 0) { visibleCopy = direct.nth(i); break; }
    }
    report.copy_button_visible = Boolean(visibleCopy);
    if (visibleCopy) {
      await visibleCopy.click({ timeout: 15000 }).catch(e => report.steps.push({ click_error: String(e).slice(0, 120) }));
      await page.waitForTimeout(1500);
      report.clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(e => "READ_FAILED:" + String(e).slice(0, 90));
      report.message_cell = await page.locator('[data-testid="journey-link-message"]').innerText().catch(() => null);
      report.after_click_screen = (await page.locator("body").innerText()).replace(/\s+/g, " ").slice(0, 400);
    }
    const buttons = await page.locator("button, [role=button], a").evaluateAll(
      els => els.map(e => ({ text: (e.innerText || e.getAttribute("aria-label") || "").trim(),
                              testid: e.getAttribute("data-testid"), href: e.getAttribute("href") }))
               .filter(x => x.text || x.testid));
    report.controls_seen = buttons.length;
    const cand = buttons.filter(b => /复制|链接|copy|link/i.test((b.text || "") + " " + (b.testid || "")));
    report.candidates = cand;
    if (cand.length) {
      const loc = page.locator(`button:has-text("${cand[0].text || "x"}"), [data-testid="${cand[0].testid || "none"}"]`).first();
      await loc.click({ timeout: 15000 }).catch(e => report.steps.push({ click_error: String(e).slice(0, 120) }));
      await page.waitForTimeout(1200);
      report.clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(e => "READ_FAILED:" + String(e).slice(0, 90));
      report.after_click_screen = (await page.locator("body").innerText()).replace(/\s+/g, " ").slice(0, 300);
    }
  } catch (e) {
    report.fatal = String(e).slice(0, 200);
  }
  const ok = typeof report.clipboard === "string" && report.clipboard.includes(JOURNEY);
  const hasControl = Boolean(report.direct_found || (report.candidates && report.candidates.length));
  report.verdict = !hasControl ? "NO_COPY_CONTROL_FOUND" : (ok ? "CLIPBOARD_CARRIES_THE_JOURNEY_LINK" : "CONTROL_PRESENT_BUT_CLIPBOARD_NOT_SET");
  fs.mkdirSync(require("path").dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(report, null, 1));
  console.log(JSON.stringify({ verdict: report.verdict, controls_seen: report.controls_seen,
    candidates: report.candidates, clipboard: report.clipboard, click_error: report.steps }, null, 1));
  await browser.close();
})();
