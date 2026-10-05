// ORD-0556 follow-up: why did /v8/trash never become "ready" under this lane's reader?
//
// The reader (bookings_caps_reader_r1.js) waits for the screen's own h1/h2 before it counts anything.
// This probe does NOT gate on a heading: it waits a fixed beat after load and records what is actually
// painted -- heading counts, the panel's own test ids, kicker text, body length, the API calls made and
// their statuses. One route per invocation, so each reading stays attributable.
const fs = require("fs");
// Same absolute module path this lane's proven reader uses (bookings_caps_reader_r1.js:17): this probe
// lives under review/, not frontend/, so a bare `require("playwright")` resolves to nothing.
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

(async () => {
  const base = process.argv[2];
  const out = process.argv[3];
  const locale = process.argv[4];
  const route = process.argv[5];
  // The shell stores the *dictionary* key, and this lane's proven reader seeds it as `en-GB` / `zh-CN`
  // (bookings_caps_reader_r1.js). Passing the bare `en` / `zh` argv value through is what made the
  // dictionary fall back to the default arm, so the two scales would not have read the same screen.
  const DICT = locale === "zh" ? "zh-CN" : "en-GB";

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: DICT });
  await ctx.addInitScript(([loc]) => {
    localStorage.setItem("citynexus.locale", loc);
    localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
  }, [DICT]);
  const page = await ctx.newPage();
  const errors = [];
  const calls = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
  page.on("response", (r) => {
    if (r.url().indexOf("/api/") >= 0) {
      calls.push({ url: r.url().replace(/^.*?\/\/[^/]+/, ""), status: r.status() });
    }
  });

  const t0 = Date.now();
  // `base` arrives with a trailing slash and `route` with a leading one: `//v8/trash` does not match this
  // app's router and silently renders the hub, which is how the first run of this leg "read" three
  // identical screens. Same normalisation the proven reader uses (bookings_caps_reader_r1.js:52).
  await page.goto(base.replace(/\/+$/, "") + route, { waitUntil: "load", timeout: 60000 });
  await page.waitForTimeout(6000);

  const facts = await page.evaluate(() => {
    const ids = ["journey-trash-panel", "trash-no-viewer", "trash-loading", "trash-empty",
                 "trash-read-failed", "trash-row-title", "trash-outcome", "v8-lede"];
    const texts = (sel) => Array.from(document.querySelectorAll(sel))
      .map((e) => (e.innerText || "").trim().slice(0, 60)).filter(Boolean);
    const q = (sel) => document.querySelector(sel);
    return {
      url: location.href,
      h1_count: document.querySelectorAll("h1").length,
      h2_count: document.querySelectorAll("h2").length,
      h1_text: texts("h1"),
      h2_text: texts("h2"),
      kicker_text: texts("span.v8-kicker"),
      present: ids.reduce((a, id) => { a[id] = !!q('[data-testid="' + id + '"]'); return a; }, {}),
      body_chars: (document.body.innerText || "").length,
      inner_head: (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 300),
      caps_words: ((document.body.innerText || "").match(/\b[A-Z]{4,}\b/g) || []).slice(0, 12),
    };
  });
  facts.wall_ms = Date.now() - t0;
  facts.page_errors = errors;
  facts.api_calls = calls;

  fs.writeFileSync(out, JSON.stringify({ route: route, locale: locale, facts: facts }, null, 1) + "\n", "utf8");
  const shown = Object.keys(facts.present).filter((k) => facts.present[k]);
  console.log(JSON.stringify({ route: route, locale: locale, h1: facts.h1_count, h2: facts.h2_count,
    testids: shown, chars: facts.body_chars, api: calls.length, errors: errors.length,
    kicker: facts.kicker_text.slice(0, 2) }));
  await browser.close();
})();
