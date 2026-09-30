/* ORD-0485 -- read the import screen's evidence pill on the candidate generation, the same way
 * walk_phone_r2 read it on the tip, so the two readings are comparable field by field.
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\export\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4862";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/import_g1_r1.json";
const W = 390, H = 844;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const page = await ctx.newPage();
  const errors = [];
  const writes = [];
  page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 160)));
  page.on("response", (r) => { if (r.request().method() !== "GET") writes.push(r.url()); });
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);
  await page.locator("[data-testid='trial-tianjin-demo']").first().click({ timeout: 8000 });
  await page.waitForTimeout(9000);
  await page.goto(BASE + "/v8/import", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);
  const snap = await page.evaluate(() => {
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden"
        && Number(s.opacity) !== 0; };
    const all = (sel) => Array.from(document.querySelectorAll(sel)).filter(vis);
    const pill = all(".v8-evidence-label").map((e) => (e.innerText || "").replace(/\s+/g, " ").trim());
    const bodyText = document.body.innerText || "";
    return { path: location.pathname, chars: bodyText.length, head: bodyText.slice(0, 1200),
      evidence_labels: pill,
      testids: all("[data-testid]").map((e) => e.getAttribute("data-testid")),
      key_shapes: Array.from(new Set(bodyText.match(/[a-z][a-zA-Z0-9]{2,}\.[a-zA-Z][a-zA-Z0-9]+/g) || [])),
      pill_contains_leaked_key: pill.some((p) => /poiImport\./.test(p)) };
  });
  const entry = await page.evaluate(() => {
    const m = document.querySelector("script[src*='assets/index-']");
    return m ? m.getAttribute("src") : null;
  });
  const out = { tool: "import_g1_r1", base: BASE, served_entry_asset: entry,
    arm: "L_import_on_candidate", page_errors: errors.length, page_error_list: errors,
    non_get_requests: writes.length, reading: snap,
    screenshot_file: null };
  try {
    const png = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/L_import_candidate.png";
    await page.screenshot({ path: png, timeout: 9000, animations: "disabled" });
    out.screenshot_file = "L_import_candidate.png";
    out.screenshot_bytes = fs.statSync(png).size;
  } catch (e) {
    out.screenshot_file = null;
    out.screenshot_reason = "SHOT_NOT_TAKEN_" + String(e.message).slice(0, 60);
  }
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2), "utf8");
  console.log(JSON.stringify({ base: BASE, entry, labels: snap.evidence_labels,
    leaked: snap.pill_contains_leaked_key, key_shapes: snap.key_shapes,
    errors: errors.length, chars: snap.chars, testids: snap.testids.length }, null, 1));
  await browser.close();
})();
