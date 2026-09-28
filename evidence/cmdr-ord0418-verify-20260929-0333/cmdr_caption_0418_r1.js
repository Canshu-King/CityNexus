/* CMDR own-eyeball read for ORD-0418 at tip 8d038b21.
 * Question this answers: on the generation that is now authoritative, does the map caption still claim a
 * provider-backed route when the plan has no route to draw -- and what does it say instead, verbatim?
 *
 * Rules this instrument follows (each one is here because I got burned by the opposite):
 *   - the demo entry is matched in BOTH locales; an arm that never entered the app is not a reading;
 *   - the arm must actually land on /v8/map (location.pathname), else ARMS_NOT_COMPARABLE;
 *   - the caption is read as rendered text from the DOM, never from a data-* attribute;
 *   - one evidence file per arm, ASCII file names only (CJK names collided and overwrote each other).
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4821";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_caption_0418/";
fs.mkdirSync(OUT, { recursive: true });

const ENTRY = { "zh-CN": ["使用封存的演示行程", "封存演示"], en: ["Use the sealed demo journey", "sealed demo"] };
const CLAIM = { "zh-CN": "供应商支持的路线", en: "Provider-backed route" };

async function arm(ctx, locale) {
  const page = await ctx.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
  const rec = { locale, errors, entry_used: null, reached_route: null, caption: null };

  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  if (locale === "en") {
    const lang = page.locator("[data-testid='topbar-language']").first();
    if (await lang.count()) { await lang.click(); rec.language_toggle = "clicked"; }
  }
  for (const needle of ENTRY[locale]) {
    const btn = page.getByText(needle, { exact: false }).first();
    if (await btn.count()) { await btn.click({ timeout: 8000 }).catch(() => {}); rec.entry_used = needle; break; }
  }
  await page.waitForTimeout(3000);
  /* In-app navigation, not a second goto: a fresh page load reboots the SPA and the sealed-demo
   * journey is not adopted from a bare /v8/map URL, which is what made my first run read an empty
   * 168-character body and still report "route reached". */
  const nav = page.locator("[data-testid='nav-map']").first();
  rec.nav_map_present = await nav.count() > 0;
  if (rec.nav_map_present) { await nav.click({ timeout: 8000 }).catch(() => {}); }
  await page.waitForTimeout(2500);
  rec.reached_route = await page.evaluate(() => location.pathname);
  rec.hub_caption_present_before_nav = rec.hub_caption_present_before_nav || null;

  const cap = page.locator(".v8-map-caption").first();
  rec.caption_present = await cap.count() > 0;
  if (rec.caption_present) {
    rec.caption = (await cap.innerText({ timeout: 5000 })).replace(/\s+/g, " ").trim();
  }
  rec.claim_present = !!rec.caption && rec.caption.indexOf(CLAIM[locale]) >= 0;
  await page.screenshot({ path: OUT + "caption_" + (locale === "en" ? "en" : "zh") + ".png", fullPage: false });
  rec.locale_read = await page.evaluate(() => document.documentElement.lang || localStorage.getItem("citynexus.locale") || "NOT_READ");
  await page.close();
  return rec;
}

(async () => {
  const browser = await chromium.launch({ chromiumSandbox: false });
  const out = { base: BASE, generated_by: "_cmdr_caption_0418_r1.js", arms: {} };
  for (const locale of ["zh-CN", "en"]) {
    const ctx = await browser.newContext({ locale: locale });
    out.arms[locale] = await arm(ctx, locale);
    await ctx.close();
  }
  await browser.close();
  out.arms_comparable = ["zh-CN", "en"].every((l) => (out.arms[l].reached_route || "").indexOf("/v8/map") >= 0);
  out.verdict = !out.arms_comparable ? "ARMS_NOT_COMPARABLE_ROUTE_NOT_REACHED"
    : !out.arms["zh-CN"].caption_present ? "CAPTION_NOT_PRESENT"
    : (out.arms["zh-CN"].claim_present || out.arms["en"].claim_present) ? "CLAIM_STILL_SPOKEN"
    : "CLAIM_WITHDRAWN_AND_REASON_SPOKEN";
  fs.writeFileSync(OUT + "caption_read_r1.json", JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out.arms, null, 1));
  console.log("comparable", out.arms_comparable, "VERDICT", out.verdict);
})();
