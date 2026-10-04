/* ORD-0556 -- one-screen reader for the bookings caps-word judgement.
 *
 * The counting rules below are copied from the commander's own instrument
 * (live_checks/cmdr_machine_speech_sweep_r1.js:46-77) -- same four shapes, same allow list, same skips
 * (script/style/code/pre, closed <details>, zero client rects, hidden/none/opacity-0). Only the route
 * list is different: this visits the two screens this order is about, because the 14-route sweep does not
 * finish against a vite-dev base (measured: the full sweep was killed at 900 s with routes averaging
 * ~64 s each). The rule text is quoted, not paraphrased, so a count from here is comparable to a count
 * from the sweep.
 *
 * It also measures the three labelled slots directly: the DOM text node, the rendered text and the
 * computed `text-transform`, because "is this caps in the source or caps from CSS" is exactly what the
 * order asks to decide, and that question needs all three numbers at once.
 *
 * Usage: node bookings_caps_reader_r1.js <base> <out-file> <locale:en|zh> [route ...]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "en";
const ROUTES = process.argv.slice(5).length ? process.argv.slice(5)
  : ["/v8/bookings", "/v8/inbox"];
if (!BASE || !OUT) { console.error("usage: node bookings_caps_reader_r1.js <base> <out> <locale> [routes]"); process.exit(2); }

const ALLOW = ["UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT", "COPILOT"];
const SHAPES = [
  { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/ },
  { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/ },
  { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/ },
  { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/ },
];

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE === "zh" ? "zh-CN" : "en-GB" });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  // The shell picks the trip up from localStorage (`citynexus.v8.journey_id`), which is how this lane's
  // own screen arms mount it. Seeding it beats clicking the sealed-demo entry: that control only appears
  // on some first screens (measured -- the English arm offered it, the Chinese arm had already gone
  // through), so a read that depends on it silently reads two different screens in two arms.
  await page.addInitScript(([id, which]) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", which);
  }, ["22222222-2222-4222-8222-222222222222", LOCALE === "zh" ? "zh-CN" : "en-GB"]);
  await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForFunction(() => (document.body.innerText || "").length > 400, null,
                             { timeout: 120000 });
  const results = {};
  for (const route of ROUTES) {
    await page.goto(BASE.replace(/\/$/, "") + route, { waitUntil: "domcontentloaded", timeout: 60000 });
    // A character-count threshold would be language-dependent (the Chinese arm says the same things in
    // far fewer characters -- measured), so readiness here is "the screen's own heading is painted".
    await page.waitForFunction(() => {
      const h = document.querySelector("h1,h2");
      return !!h && (h.innerText || "").trim().length > 3;
    }, null, { timeout: 120000 });
    await page.waitForTimeout(1200);
    const r = await page.evaluate((allow) => {
      const SHAPES = [
        { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/ },
        { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/ },
        { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/ },
        { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/ },
      ];
      const painted = [];
      const stats = { text_nodes: 0, too_short: 0, no_parent: 0, in_code_or_style: 0,
                      in_closed_details: 0, zero_client_rects: 0, hidden_style: 0 };
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        stats.text_nodes++;
        const text = (n.nodeValue || "").trim();
        if (text.length < 3) { stats.too_short++; continue; }
        const el = n.parentElement;
        if (!el) { stats.no_parent++; continue; }
        if (el.closest("script,style,code,pre,noscript")) { stats.in_code_or_style++; continue; }
        const det = el.closest("details");
        if (det && !det.open) { stats.in_closed_details++; continue; }
        const rg = document.createRange(); rg.selectNodeContents(n);
        if (rg.getClientRects().length === 0) { stats.zero_client_rects++; continue; }
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0) { stats.hidden_style++; continue; }
        for (const s of SHAPES) {
          const m = text.match(s.re);
          if (!m) continue;
          if (s.kind === "ALLCAPS_WORD" && allow.includes(m[0])) continue;
          if (s.kind === "ALLCAPS_WORD" && /[_]/.test(m[0])) continue;
          painted.push({ kind: s.kind, token: m[0], text_head: text.slice(0, 90),
                         tag: el.tagName.toLowerCase(), cls: (el.className || "").toString().slice(0, 60) });
          break;
        }
      }
      const slot = (needle) => {
        const el = Array.from(document.querySelectorAll("span,b,strong,small,p,h1,h2,h3"))
          .find((e) => (e.textContent || "").trim().toLowerCase() === needle.toLowerCase());
        if (!el) return { needle, present: false };
        const cs = getComputedStyle(el);
        return {
          needle,
          present: true,
          tag: el.tagName.toLowerCase(),
          cls: (el.className || "").toString().slice(0, 60),
          dom_text: (el.textContent || "").trim(),
          rendered_text: (el.innerText || "").trim(),
          computed_text_transform: cs.textTransform,
          dom_is_upper_case: (el.textContent || "").trim() === (el.textContent || "").trim().toUpperCase(),
          rendered_is_upper_case: (el.innerText || "").trim() === (el.innerText || "").trim().toUpperCase(),
        };
      };
      const leftovers = [];
      const walker2 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let m2;
      while ((m2 = walker2.nextNode()) && leftovers.length < 14) {
        const text = (m2.nodeValue || "").trim();
        if (text.length < 3) continue;
        const el = m2.parentElement;
        if (!el || el.closest("script,style,code,pre,noscript")) continue;
        const det = el.closest("details");
        if (det && !det.open) continue;
        const rg = document.createRange(); rg.selectNodeContents(m2);
        const rects = rg.getClientRects().length;
        const cs = getComputedStyle(el);
        leftovers.push({ text_head: text.slice(0, 40), cls: (el.className || "").toString().slice(0, 34),
                         rects: rects, display: cs.display, visibility: cs.visibility,
                         caps: (text.match(/[A-Z]{4,}/g) || []).slice(0, 3) });
      }
      return {
        items: painted,
        leftovers: leftovers,
        walk_stats: stats,
        inner_text_head: (document.body.innerText || "").slice(0, 300),
        key_fallback_anywhere: (document.body.innerText || "").includes("inbox.multimodal"),
        url_now: location.href,
        kinds: painted.reduce((a, p) => (a[p.kind] = (a[p.kind] || 0) + 1, a), {}),
        documentChars: (document.body.innerText || "").length,
        labels: [slot("Stay evidence"), slot("STAY EVIDENCE"), slot("Multimodal inbox"),
                 slot("MULTIMODAL INBOX"), slot("Authoritative memory"), slot("AUTHORITATIVE MEMORY")],
        screenTitle: (document.querySelector("h1,h2") || {}).innerText || "",
      };
    }, ALLOW);
    results[route] = r;
    console.log(LOCALE, route, "items", r.items.length, JSON.stringify(r.kinds));
  }
  require("fs").writeFileSync(OUT, JSON.stringify({
    instrument: "bookings_caps_reader_r1 (commander's sweep rules, two routes)",
    rules_copied_from: "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_machine_speech_sweep_r1.js:46-77",
    base: BASE, locale: LOCALE, routesWalked: ROUTES, allowListForAllCaps: ALLOW,
    viewport: { width: 390, height: 844 }, pageErrors, perRoute: results,
    written_at: new Date().toISOString(),
  }, null, 1));
  await browser.close();
}

main().catch((e) => { console.error(String(e).slice(0, 400)); process.exit(3); });
