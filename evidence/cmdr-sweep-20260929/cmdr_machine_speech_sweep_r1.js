/* CMDR machine-speech sweep r1 - how much machine text is still PAINTED on a Chinese screen?
 *
 * Why: ORD-0422, ORD-0423, ORD-0425 and ORD-0433 all claim to have taken machine wording off the
 * traveller's screen.  Nobody has measured the residue.  This walks the real routes in the zh arm and
 * counts text that is actually painted -- not attributes (Q71 made data-* the sanctioned channel), not
 * nodes hidden by `display:none`, not the contents of a closed <details>.
 *
 * A text node counts when it is: (1) inside a visible element (offset chain + non-zero client rects),
 * (2) matches one of the machine shapes below, and (3) not inside a <code>/<pre>/<script>/<style>.
 * Shapes: UPPER_SNAKE identifiers, IANA zone ids, dotted/lower_snake keys, and bare ALL-CAPS words of
 * 4+ letters that are not ordinary UI acronyms (the small allow-list is printed so it is auditable).
 *
 * Usage: node cmdr_machine_speech_sweep_r1.js <base> <out-file> [locale]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "zh";
if (!BASE || !OUT) { console.error("usage: node cmdr_machine_speech_sweep_r1.js <base> <out-file> [locale]"); process.exit(2); }

const ROUTES = ["/v8/hub", "/v8/live", "/v8/map", "/v8/studio", "/v8/stay", "/v8/discover",
  "/v8/bookings", "/v8/agent", "/v8/authoritative", "/v8/intelligence", "/v8/twin",
  "/v8/trash", "/v8/trips", "/v8/me"];

const ALLOW = ["UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT", "COPILOT"];

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  const entry = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }
  const results = {};
  for (const route of ROUTES) {
    await page.goto(BASE.replace(/\/$/, "") + route, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(2200);
    const r = await page.evaluate((allow) => {
      const shapes = [
        { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/ },
        { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/ },
        { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/ },
        { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/ },
      ];
      const painted = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        const text = (n.nodeValue || "").trim();
        if (text.length < 3) continue;
        const el = n.parentElement;
        if (!el) continue;
        if (el.closest("script,style,code,pre,noscript")) continue;
        const det = el.closest("details");
        if (det && !det.open) continue;
        const rectCount = (() => { const rg = document.createRange(); rg.selectNodeContents(n); return rg.getClientRects().length; })();
        if (rectCount === 0) continue;
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0) continue;
        for (const s of shapes) {
          const m = text.match(s.re);
          if (!m) continue;
          if (s.kind === "ALLCAPS_WORD" && allow.includes(m[0])) continue;
          if (s.kind === "ALLCAPS_WORD" && /[_]/.test(m[0])) continue;
          painted.push({ kind: s.kind, token: m[0], text_head: text.slice(0, 90),
                         tag: el.tagName.toLowerCase(), cls: (el.className || "").toString().slice(0, 60) });
          break;
        }
      }
      return { totalTextNodesScanned: painted.length, items: painted.slice(0, 40),
               documentChars: (document.body.innerText || "").length,
               kinds: painted.reduce((a, p) => (a[p.kind] = (a[p.kind] || 0) + 1, a), {}) };
    }, ALLOW);
    results[route] = r;
  }
  await ctx.close();
  const routesWithHits = Object.entries(results).filter(([, v]) => v.totalTextNodesScanned > 0).map(([k]) => k);
  const tokenUniverse = {};
  Object.values(results).forEach((v) => v.items.forEach((i) => { tokenUniverse[i.token] = (tokenUniverse[i.token] || 0) + 1; }));
  const report = {
    instrument: "cmdr_machine_speech_sweep_r1", base: BASE, locale: LOCALE, entryAssets: entry,
    routesWalked: ROUTES.length, viewport: "390x844",
    allowListForAllCaps: ALLOW,
    routesWithPaintedMachineText: routesWithHits.length,
    routes_with_hits: routesWithHits,
    totalPaintedHits: Object.values(results).reduce((a, v) => a + v.totalTextNodesScanned, 0),
    distinctTokens: Object.keys(tokenUniverse).length,
    topTokens: Object.entries(tokenUniverse).sort((a, b) => b[1] - a[1]).slice(0, 25),
    perRoute: results, pageErrors,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, entry, routesWalked: ROUTES.length,
    routesWithPaintedMachineText: report.routesWithPaintedMachineText,
    totalPaintedHits: report.totalPaintedHits, distinctTokens: report.distinctTokens,
    topTokens: report.topTokens.slice(0, 12), pageErrors: pageErrors.length }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
