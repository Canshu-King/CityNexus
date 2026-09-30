/* ORD-0444 -- walk the shelf face on a rendered page at 390 wide, and report what is actually said.

Same discipline as the sibling order's walk: assertions read `innerText` (the words a person sees),
never the `data-testid` that was only used to find them; the row is scrolled into view and a point at
the control's own centre must resolve back to it, because at this width the bottom bar overlaps
content that a headless DOM check would happily call reachable.

usage: node shelf_screen_walk_r1.cjs <base-url>
*/
const { chromium } = require("playwright");

const BASE = process.argv[2];
if (!BASE) {
  process.stderr.write("usage: node shelf_screen_walk_r1.cjs <base-url>\n");
  process.exit(2);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 200)); });
  const out = { base: BASE, viewport: { width: 390, height: 844 } };

  const read = () => page.evaluate(() => {
    const q = (s) => document.querySelector(s);
    const txt = (el) => (el ? el.innerText.replace(/\s+/g, " ").trim() : null);
    const panel = q('[data-testid="collection-panel"]');
    return {
      panel_present: !!panel,
      panel_words: txt(panel),
      shelf_rows: Array.from(document.querySelectorAll('[data-testid="collection-shelf"]'))
        .map((li) => li.innerText.replace(/\s+/g, " ").trim()),
      item_rows: Array.from(document.querySelectorAll('[data-testid="collection-item"]'))
        .map((li) => li.innerText.replace(/\s+/g, " ").trim()),
      empty_words: txt(q('[data-testid="collection-empty"]')),
      failed_words: txt(q('[data-testid="collection-failure"]')),
      no_traveler_words: txt(q('[data-testid="collection-no-traveler"]')),
      machine_tokens: ["PLACE_NOT_FOUND", "COLLECTION_FOLDER_NOT_FOUND",
        "PLACE_ALREADY_IN_COLLECTION", "MEMBER_TRAVELER_UNKNOWN", "nav.collections",
        "[object Object]", "undefined", "reason_code", "traveler_id"].filter(
          (t) => (document.body.innerText || "").includes(t)),
    };
  });

  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  const enter = page.locator('button:has-text("使用封存的演示行程")');
  out.entered_wizard_by_click = (await enter.count()) > 0;
  if (out.entered_wizard_by_click) await enter.first().click();
  await page.waitForSelector('[data-testid="collection-panel"]', { timeout: 40000 });
  await page.waitForTimeout(3000);
  out.screen_with_one_shelf = await read();

  // the retry control is the face's only action; it has to survive a real press at this width
  const retry = page.locator('[data-testid="collection-retry"]');
  await retry.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  const box = await retry.boundingBox();
  if (box) {
    const cx = Math.round(box.x + box.width / 2);
    const cy = Math.round(box.y + box.height / 2);
    out.retry_hit = await page.evaluate(({ cx, cy }) => {
      const top = document.elementFromPoint(cx, cy);
      const btn = document.querySelector('[data-testid="collection-retry"]');
      return {
        point: { cx, cy },
        element: top ? top.tagName.toLowerCase() + "." + (top.className || "") : null,
        is_the_control: top === btn,
        width_px: Math.round(btn.getBoundingClientRect().width),
        height_px: Math.round(btn.getBoundingClientRect().height),
      };
    }, { cx, cy });
    await retry.click();
    await page.waitForTimeout(2500);
    out.after_retry_press = await read();
  }

  out.console_errors = errors;
  await browser.close();
  process.stdout.write(JSON.stringify(out, null, 1) + "\n");
})().catch((e) => {
  process.stderr.write(String((e && e.message) || e) + "\n");
  process.exit(2);
});
