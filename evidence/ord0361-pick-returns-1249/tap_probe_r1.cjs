/**
 * ORD-0361 rebase readiness, measured at the current tip instead of argued.
 *
 * The order's requirement is one sentence: 地图点选要有可观察后果.  Since this lane's branch was cut,
 * ORD-0390 landed map <-> card two-way selection and ORD-0417 landed "a tap paints the stop's name on
 * the glass".  So the question is no longer "does a tap do nothing" -- it is which half of what my
 * branch carried is still missing on these bytes.  This probe answers that by doing what a traveller
 * does, and by reading only rendered text:
 *
 *   1. markers: are they controls (role / tabIndex / aria-pressed) or painted dots?
 *   2. tap one: what text changes on the glass, before -> after?
 *   3. keyboard: does Enter on a marker do the same thing as the tap?
 *   4. reload: does the pick survive re-entering the page, and is anything journey-scoped in storage?
 *
 * Step 4 is the half my branch had and the line may not; the receipt prints storage keys verbatim so a
 * reader can see what is and is not persisted rather than taking my word for it.
 */
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = process.env.CNX_BASE || "http://localhost:4491";
const OUT = process.env.CNX_OUT || "tap_probe.json";
const SHOT = process.env.CNX_SHOT || "tap_probe.png";
const LOCALE = process.env.CNX_LOCALE || "zh-CN";

const snap = async (page) => ({
  selected_stop: await page.locator('[data-testid="v8-map-selected-stop"]').first()
    .textContent().then((t) => (t || "").replace(/\s+/g, " ").trim()).catch(() => null),
  selected_stop_count: await page.locator('[data-testid="v8-map-selected-stop"]').count(),
  facts_heading: await page.locator(".v8-map-facts h1, .v8-map-facts h2").first()
    .textContent().then((t) => (t || "").replace(/\s+/g, " ").trim()).catch(() => null),
  markers: await page.evaluate(() => Array.from(document.querySelectorAll(".v9-map-marker")).map((el) => ({
    text: (el.textContent || "").trim(),
    role: el.getAttribute("role"),
    tabindex: el.getAttribute("tabindex"),
    aria_label: el.getAttribute("aria-label"),
    aria_pressed: el.getAttribute("aria-pressed"),
    box: (() => { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) }; })(),
  }))),
  storage: await page.evaluate(() => {
    const o = {};
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.indexOf("citynexus") === 0) o[k] = String(localStorage.getItem(k)).slice(0, 60);
    }
    return o;
  }),
});

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
                                        locale: LOCALE === "en" ? "en-US" : "zh-CN" });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
  await page.addInitScript((v) => { try { localStorage.setItem("citynexus.locale", v); } catch (e) {} }, LOCALE);

  await page.goto(`${BASE}/v8/map`, { waitUntil: "domcontentloaded", timeout: 60000 });
  const entry = page.getByRole("button", { name: /封存的演示|sealed demo/i }).first();
  let entryUsed = null;
  if (await entry.isVisible({ timeout: 8000 }).catch(() => false)) {
    entryUsed = (await entry.textContent()) || null;
    await entry.click();
    await page.waitForTimeout(2500);
    await page.goto(`${BASE}/v8/map`, { waitUntil: "domcontentloaded", timeout: 60000 });
  }
  await page.waitForSelector('[data-testid="v8-maplibre-panel"]', { timeout: 45000 });
  await page.waitForSelector(".v9-map-marker", { timeout: 45000 });
  await page.waitForTimeout(2500);
  const before = await snap(page);

  // tap the third located stop's marker, by the number painted on it
  const target = (before.markers.filter((m) => /^\d+$/.test(m.text)))[2] || null;
  let tapResult = { attempted: false };
  if (target) {
    const handle = await page.evaluateHandle((label) => {
      const els = Array.from(document.querySelectorAll(".v9-map-marker"));
      return els.find((e) => (e.textContent || "").trim() === label) || null;
    }, target.text);
    const el = handle.asElement();
    if (el) {
      await el.click();
      await page.waitForTimeout(1500);
      const afterTap = await snap(page);
      tapResult = {
        attempted: true,
        marker_label: target.text,
        marker_aria_label_tapped: target.aria_label,
        selected_stop_before: before.selected_stop,
        selected_stop_after: afterTap.selected_stop,
        heading_before: before.facts_heading,
        heading_after: afterTap.facts_heading,
        pressed_before: before.markers.map((m) => m.aria_pressed),
        pressed_after: afterTap.markers.map((m) => m.aria_pressed),
        name_changed: before.selected_stop !== afterTap.selected_stop,
        heading_changed: before.facts_heading !== afterTap.facts_heading,
        after: afterTap,
      };
      await page.screenshot({ path: SHOT });
      // keyboard: Enter on the first marker must do the same kind of thing a tap does
      const first = (afterTap.markers.filter((m) => /^\d+$/.test(m.text)))[0];
      let keyboard = { attempted: false };
      if (first) {
        const h2 = await page.evaluateHandle((label) => {
          const els = Array.from(document.querySelectorAll(".v9-map-marker"));
          return els.find((e) => (e.textContent || "").trim() === label) || null;
        }, first.text);
        const e2 = h2.asElement();
        if (e2) {
          await e2.focus();
          const focused = await page.evaluate(() => document.activeElement &&
            (document.activeElement.className || "") + "|" + (document.activeElement.textContent || "").trim());
          await page.keyboard.press("Enter");
          await page.waitForTimeout(1200);
          const afterKey = await snap(page);
          keyboard = {
            attempted: true, marker_label: first.text, active_element_after_focus: focused,
            selected_stop_after_enter: afterKey.selected_stop,
            changed_by_enter: afterKey.selected_stop !== afterTap.selected_stop,
          };
        }
      }
      tapResult.keyboard = keyboard;
      // reload: does the pick survive re-entering the page?
      await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForSelector(".v9-map-marker", { timeout: 45000 });
      await page.waitForTimeout(2500);
      const afterReload = await snap(page);
      tapResult.reload = {
        selected_stop_after_reload: afterReload.selected_stop,
        heading_after_reload: afterReload.facts_heading,
        pressed_after_reload: afterReload.markers.map((m) => m.aria_pressed),
        storage_after_reload: afterReload.storage,
        pick_survived_reload: afterReload.selected_stop === afterTap.selected_stop
          && afterReload.selected_stop !== null,
      };
    }
  }

  const receipt = {
    order: "ORD-0361",
    instrument: "tap_probe_r1",
    base_url: BASE,
    locale: LOCALE,
    route: "/v8/map",
    entry_button_used: entryUsed,
    markers_total: before.markers.length,
    markers_that_are_controls: before.markers.filter((m) => m.role === "button" && m.tabindex === "0").length,
    markers_with_aria_pressed: before.markers.filter((m) => m.aria_pressed !== null).length,
    marker_min_box: Math.min.apply(null, before.markers.map((m) => m.box.w).concat([0])),
    before: before,
    tap: tapResult,
    console_errors: errors,
    screenshot: SHOT,
  };
  fs.writeFileSync(OUT, JSON.stringify(receipt, null, 1));
  console.log(JSON.stringify({
    markers_total: receipt.markers_total,
    markers_that_are_controls: receipt.markers_that_are_controls,
    markers_with_aria_pressed: receipt.markers_with_aria_pressed,
    before_selected_stop: before.selected_stop,
    tap: { name_changed: tapResult.name_changed, heading_changed: tapResult.heading_changed,
           after: tapResult.selected_stop_after, heading_after: tapResult.heading_after },
    keyboard: tapResult.keyboard,
    reload: tapResult.reload && { pick_survived_reload: tapResult.reload.pick_survived_reload,
                                  after: tapResult.reload.selected_stop_after_reload,
                                  storage: tapResult.reload.storage_after_reload },
    console_errors: errors.length,
  }, null, 1));
  await browser.close();
})().catch((e) => { console.error("PROBE_FAILED", String(e)); process.exit(1); });
