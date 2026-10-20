/* Building walk: the 智能守护 status pill -- does the word a traveller reads belong to their language?

Measured mechanism, not guessed: `frontend/src/i18n/LocaleContext.tsx:2534` is the only row in the
智能守护 family that still carries a latin word ("Guardian 就绪"), while its siblings say 智能守护 and
守护状态不可用; and `frontend/src/styles.css:175` gives `.v8-status-pill` `text-transform: uppercase`, so
what lands on the phone screen is "GUARDIAN 就绪".  This tool reads the pill exactly as the browser
renders it (innerText after text-transform), so the claim is about the screen, not about the source file.

argv: node walk_intel_pill_r1.cjs <base> <out.json> <shot.png>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/intel_pill.json";
const SHOT = process.argv[4] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/intel_pill.png";

const run = { schema: "CNX_BUILDING_INTEL_PILL_R1", base: BASE_URL, viewport: { width: 390, height: 844 },
  started: new Date().toString(), steps: [], pills: [], latin_pills: 0, verdict: null,
  page_errors: [], console_errors: [] };

async function readPills(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden"; };
    const pills = Array.from(document.querySelectorAll(".v8-status-pill")).filter(vis).map((el) => ({
      rendered: strip(el.innerText), transform: getComputedStyle(el).textTransform,
      h: Math.round(el.getBoundingClientRect().height),
      latin_capital: /[A-Z]{4,}/.test(strip(el.innerText)) }));
    const body = document.body.innerText || "";
    return { tag, path: location.pathname, pills, zh_chars: (body.match(/[一-龥]/g) || []).length,
             heads: Array.from(document.querySelectorAll("h1,h2")).filter(vis).map((e) => strip(e.innerText)) };
  }, tag);
}

async function pressTestId(page, testid, tag) {
  const loc = page.locator("[data-testid='" + testid + "']").first();
  if (await loc.count() === 0) return { tag, pressed: false, why: "NO_SUCH_TESTID" };
  const hit = await loc.evaluate((el) => { el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { landed: !!top && (top === el || el.contains(top) || top.contains(el)),
             h: Math.round(b.height), w: Math.round(b.width) }; });
  if (!hit.landed) return { tag, pressed: false, why: "HIT_TEST_MISSED", hit };
  await loc.click();
  await page.waitForTimeout(1500);
  return { tag, pressed: true, hit };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(m.text().slice(0, 200)); });

  await page.goto(BASE_URL + "/", { waitUntil: "networkidle", timeout: 60000 });
  run.steps.push(await pressTestId(page, "trial-tianjin-demo", "anchor_demo"));
  await page.waitForTimeout(1500);
  run.steps.push(await pressTestId(page, "v8-mobile-menu", "open_drawer"));
  run.steps.push(await pressTestId(page, "v8-drawer-entry-intelligence", "enter_intelligence"));
  const stop = await readPills(page, "intelligence");
  run.steps.push(stop);
  run.pills = stop.pills;
  run.latin_pills = stop.pills.filter((p) => p.latin_capital).length;
  if (stop.pills.length === 0) run.verdict = "NO_PILL_RENDERED";
  else if (run.latin_pills > 0 && stop.zh_chars > 40) run.verdict = "CAPITALISED_LATIN_WORD_ON_ZH_SCREEN";
  else run.verdict = "PILL_WORDS_IN_TRAVELER_LANGUAGE";
  fs.mkdirSync(path.dirname(SHOT), { recursive: true });
  await page.screenshot({ path: SHOT });
  run.shot = SHOT;
  run.finished = new Date().toString();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ verdict: run.verdict, path: stop.path, pills: run.pills,
    latin_pills: run.latin_pills, zh_chars: stop.zh_chars, heads: stop.heads,
    presses: run.steps.map((s) => ({ tag: s.tag, pressed: s.pressed, why: s.why || null })),
    page_errors: run.page_errors.length, console_errors: run.console_errors.length }, null, 1));
  await browser.close();
})();
