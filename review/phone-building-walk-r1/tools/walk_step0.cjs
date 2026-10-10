/* Building walk step 0: what does a person SEE on the very first screen at 390px?
 *
 * Not a guess from the source: open the phone shape, read document.body.innerText (the words a person
 * reads), and list every visible [data-testid] plus every pressable control with its rendered words.
 * That table is the starting point for the booking walk -- if the first screen already speaks in codes,
 * mode names or internal ids, that is a "看不懂" finding before any tap happens.
 *
 * argv: node walk_step0.cjs <base> <out.json> <width> <height>
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4881";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_step0.json";
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

(async () => {
  const run = { step: "first_screen", base: BASE_URL, viewport: { width: W, height: H },
                started: new Date().toString(), page_errors: [], console_errors: [] };
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H },
    deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });
  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2500);
  run.url_after_load = page.url();
  run.state = await page.evaluate(() => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden" && Number(s.opacity) !== 0; };
    const body = document.body.innerText || "";
    const pressables = Array.from(document.querySelectorAll("button,[role='button'],a")).filter(vis)
      .map((el) => ({ tag: el.tagName, testid: el.getAttribute("data-testid") || null,
                      words: strip(el.innerText).slice(0, 60), disabled: !!el.disabled,
                      href: el.getAttribute("href") || null,
                      aria: el.getAttribute("aria-label") || null }));
    const testids = {};
    Array.from(document.querySelectorAll("[data-testid]")).filter(vis).forEach((el) => {
      const k = el.getAttribute("data-testid");
      testids[k] = (testids[k] || 0) + 1;
    });
    const nav = Array.from(document.querySelectorAll("nav a, nav button")).filter(vis)
      .map((el) => strip(el.innerText)).filter(Boolean);
    // words that look like machine values leaking onto the screen
    const suspicious = [];
    const patterns = [
      [/\b[A-Z][A-Z0-9_]{3,}\b/g, "UPPER_SNAKE_TOKEN"],
      [/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g, "UUID"],
      [/\b(400|401|403|404|409|422|500|502|503)\b/g, "HTTP_STATUS"],
      [/\b\d{4}-\d{2}-\d{2}T[\d:]+/g, "RAW_TIMESTAMP"],
      [/\b(null|undefined|true|false|NaN)\b/g, "CODE_LITERAL"],
    ];
    for (const [re, kind] of patterns) {
      const m = body.match(re);
      if (m) suspicious.push({ kind, hits: Array.from(new Set(m)).slice(0, 8) });
    }
    return { path: location.pathname, rendered_chars: body.length,
             body_text: strip(body).slice(0, 3000), pressables, testids, nav, suspicious };
  });
  await page.screenshot({ path: OUT.replace(/\.json$/, "_shot.png"), fullPage: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await browser.close();
  console.log("STEP0 path=" + run.state.path + " chars=" + run.state.rendered_chars +
    " pressables=" + run.state.pressables.length + " nav=" + JSON.stringify(run.state.nav) +
    " suspicious=" + JSON.stringify(run.state.suspicious));
  console.log("BODY:\n" + run.state.body_text.slice(0, 800));
})().catch((e) => { console.error("STEP0_FAIL " + e); process.exit(1); });