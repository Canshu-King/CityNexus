/* ORD-0444 -- read the 收藏 face off a rendered screen, in one named state.
 *
 * It presses the face's own 「重读一次」 rather than reloading the document, so what is asserted is
 * the component's read path, and it reports `innerText` -- the words a person can see -- not the
 * `data-testid` attributes it used to find them (the standing rule: an assertion that reads an
 * attribute proves the DOM exists, not that anything was said).
 *
 * usage: node prod_r3_screen_walk.cjs <base-url> <state-label>
 */
const { chromium } = require("playwright");

const BASE = process.argv[2] || "http://localhost:60186";
const STATE = process.argv[3] || "unlabelled";
const MACHINE_TOKENS = [
  "PLACE_NOT_FOUND", "COLLECTION_FOLDER_NOT_FOUND", "PLACE_ALREADY_IN_COLLECTION",
  "MEMBER_TRAVELER_UNKNOWN", "nav.collections", "agent.readResultAnnounce",
  "[object Object]", "undefined", "NaN", "traveler_id", "reason_code", "/api/v1",
];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const console_errors = [];
  page.on("console", (m) => { if (m.type() === "error") console_errors.push(m.text().slice(0, 160)); });
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });

  // the wizard offers the sealed stage; the journey view is where the face mounts
  const enter = page.locator('button:has-text("使用封存的演示行程")');
  const entered = (await enter.count()) > 0;
  if (entered) await enter.first().click();

  await page.waitForSelector('[data-testid="collection-panel"]', { timeout: 30000 });
  const btn = page.locator('[data-testid="collection-retry"]');
  const disabled_before = await btn.isDisabled();
  if (!disabled_before) await btn.click();
  await page.waitForTimeout(2500);

  const read = await page.evaluate((tokens) => {
    const txt = (el) => (el ? el.innerText.replace(/\s+/g, " ").trim() : null);
    const q = (s) => document.querySelector(s);
    const body = document.body.innerText || "";
    return {
      bundle: Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src")),
      panel_text: txt(q('[data-testid="collection-panel"]')),
      shelf_rows: Array.from(document.querySelectorAll('[data-testid="collection-shelf"]'))
        .map((li) => li.innerText.replace(/\s+/g, " ").trim()),
      item_rows: Array.from(document.querySelectorAll('[data-testid="collection-item"]'))
        .map((li) => li.innerText.replace(/\s+/g, " ").trim()),
      tally: txt(q('[data-testid="collection-tally"]')),
      empty_text: txt(q('[data-testid="collection-empty"]')),
      failure_text: txt(q('[data-testid="collection-failure"]')),
      panel_chars: (txt(q('[data-testid="collection-panel"]')) || "").length,
      machine_tokens_in_body: tokens.filter((t) => body.includes(t)),
      cjk_in_panel: ((txt(q('[data-testid="collection-panel"]')) || "").match(/[一-鿿]/g) || []).length,
    };
  }, MACHINE_TOKENS);

  await browser.close();
  process.stdout.write(JSON.stringify({
    state_label: STATE, base: BASE, entered_wizard_by_click: entered,
    retry_disabled_before_press: disabled_before, console_errors, ...read,
  }, null, 1) + "\n");
})().catch((e) => { process.stderr.write(String(e && e.message ? e.message : e) + "\n"); process.exit(2); });
