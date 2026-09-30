/* ORD-0476 slice 2 -- walk the footprint screen on a rendered page and report the four readings the
 * order asks for: the entry's row name, the hit result, the screen title's rendered words, the testids.
 *
 * It runs at 390 x 844 because that is the shape the control has to survive: the bottom bar is drawn
 * over the itinerary at narrow widths, so "the button exists" is not the claim -- a point at its own
 * centre must resolve back to it.  `boundingBox()` is read as x/y/width/height (it has no .w/.h), the
 * row is scrolled into view first, and every assertion reads `innerText` rather than an attribute,
 * because a data-testid proves the DOM exists, not that anything was said.
 *
 * usage: node footprint_screen_walk_r1.cjs <base-url>
 */
const { chromium } = require("playwright");

const BASE = process.argv[2];
if (!BASE) {
  process.stderr.write("usage: node footprint_screen_walk_r1.cjs <base-url>\n");
  process.exit(2);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 200)); });
  const out = { base: BASE, viewport: { width: 390, height: 844 }, console_errors: [] };

  const read = () =>
    page.evaluate(() => {
      const q = (s) => document.querySelector(s);
      const txt = (el) => (el ? el.innerText.replace(/\s+/g, " ").trim() : null);
      const panel = q('[data-testid="footprint-panel"]');
      return {
        panel_present: !!panel,
        panel_title: txt(q(".cn-footprints .cnx-eyebrow")),
        panel_head: txt(panel ? panel.querySelector("h2") : null),
        rows: Array.from(document.querySelectorAll('[data-testid="footprint-row"]'))
          .map((li) => li.innerText.replace(/\s+/g, " ").trim()),
        empty_text: txt(q('[data-testid="footprint-empty"]')),
        failed_text: txt(q('[data-testid="footprint-failed"]')),
        tally: txt(q('[data-testid="footprint-tally"]')),
        body_has_machine_tokens: ["CHECKIN_DUPLICATE_STAMP", "CHECKIN_PLACE_UNKNOWN",
          "CHECKIN_ACTIVITY_UNKNOWN", "nav.footprints", "checkin.title", "[object Object]",
          "undefined", "reason_code"].filter((token) => (document.body.innerText || "").includes(token)),
      };
    });

  // enter the sealed stage, then take the route the drawer label now exists for
  await page.goto(BASE + "/v8/trips", { waitUntil: "load" });
  const enter = page.locator('button:has-text("使用封存的演示行程")');
  out.entered_wizard_by_click = (await enter.count()) > 0;
  if (out.entered_wizard_by_click) await enter.first().click();
  await page.waitForSelector('[data-testid="trip-stop"]', { timeout: 40000 });

  // ---- reading 1 and 2: the entry's row, and whether a press at its centre lands on it
  const control = page.locator('[data-testid="stop-checkin"]').first();
  await control.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  const box = await control.boundingBox();
  out.entry = await page.evaluate(() => {
    const stop = document.querySelector('[data-testid="trip-stop"]');
    const btn = document.querySelector('[data-testid="stop-checkin"]');
    return {
      row_title: stop ? (stop.querySelector(".trip-stop-body b") || {}).innerText : null,
      control_words: btn ? btn.innerText.trim() : null,
      control_aria: btn ? btn.getAttribute("aria-label") : null,
      row_testids: stop ? Array.from(stop.querySelectorAll("[data-testid]")).map((e) => e.getAttribute("data-testid")) : [],
      trip_stop_testid_present: !!stop,
    };
  });
  out.hit = null;
  if (box) {
    const cx = Math.round(box.x + box.width / 2);
    const cy = Math.round(box.y + box.height / 2);
    out.hit = await page.evaluate(
      ({ cx, cy }) => {
        const top = document.elementFromPoint(cx, cy);
        const btn = document.querySelector('[data-testid="stop-checkin"]');
        const inner = (el) => (el ? el.tagName.toLowerCase() + "." + (el.className || "") : null);
        return {
          point: { cx, cy },
          box: { x: box_x(), width: box_w() },
          element_at_point: inner(top),
          is_the_control: top === btn,
          is_inside_the_control: !!(top && btn && btn.contains(top)),
          swallowed_by_row: !!(top && top.closest('[data-testid="trip-stop"]') && top !== btn && !btn.contains(top)),
        };
        function box_x() { return btn ? Math.round(btn.getBoundingClientRect().x) : null; }
        function box_w() { return btn ? Math.round(btn.getBoundingClientRect().width) : null; }
      },
      { cx, cy },
    );
    out.hit.control_width_px = box.width;
    out.hit.control_height_px = box.height;
  }

  // ---- the footprint screen before anything is stamped: the named empty state
  await page.goto(BASE + "/v8/footprints", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="footprint-panel"]', { timeout: 40000 });
  await page.waitForTimeout(2500);
  out.screen_before_any_stamp = await read();

  // ---- stamp for real, from the itinerary, and read the screen again
  await page.goto(BASE + "/v8/trips", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="stop-checkin"]', { timeout: 40000 });
  const firstControl = page.locator('[data-testid="stop-checkin"]').first();
  await firstControl.scrollIntoViewIfNeeded();
  out.stamp_words_before_press = (await firstControl.innerText()).trim();
  await firstControl.click();
  await page.waitForTimeout(3000);
  out.stamp_words_after_press = (await page.locator('[data-testid="stop-checkin"]').first().innerText()).trim();

  await page.goto(BASE + "/v8/footprints", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="footprint-row"]', { timeout: 40000 });
  out.screen_after_stamp = await read();

  // ---- the duplicate: press the same stop again. The server refuses, the row is re-read, and
  //      nothing is overwritten -- so the stamp count must not move and the notice must be this
  //      screen's own sentence.
  await page.goto(BASE + "/v8/trips", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="stop-checkin"]', { timeout: 40000 });
  const again = page.locator('[data-testid="stop-checkin"]').first();
  await again.scrollIntoViewIfNeeded();
  await again.click();
  await page.waitForTimeout(3000);
  out.duplicate = await page.evaluate(() => {
    const notice = document.querySelector('[data-testid="stop-checkin-notice"]');
    return {
      notice_words: notice ? notice.innerText.replace(/\s+/g, " ").trim() : null,
      control_words: (document.querySelector('[data-testid="stop-checkin"]') || {}).innerText,
    };
  });
  await page.goto(BASE + "/v8/footprints", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="footprint-panel"]', { timeout: 40000 });
  await page.waitForTimeout(2500);
  out.screen_after_duplicate = await read();

  out.console_errors = errors;
  await browser.close();
  process.stdout.write(JSON.stringify(out, null, 1) + "\n");
})().catch((e) => {
  process.stderr.write(String((e && e.message) || e) + "\n");
  process.exit(2);
});
