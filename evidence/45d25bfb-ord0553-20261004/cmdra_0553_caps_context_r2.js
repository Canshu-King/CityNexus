/* ORD-0553 census r2 -- every painted machine token on every route, with the field that answered it.
 *
 * r1 read one screen (the authoritative route).  The commander's judgement on that order is a fleet rule,
 * not a one-screen rule: "every status name the backend can answer must have a wording, and a wording must
 * not be the server's own token."  So this walks the same 14 routes the sweep walks, in one arm per run, and
 * for each painted machine-shape token records the DOM slot plus whether that exact string was answered by
 * the server in a response this screen received -- which is what separates a server word (dirty) from a
 * component's own style word (leave it alone).
 *
 * usage: node cmdra_0553_caps_context_r2.js <base> <out.json> <zh|en>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "en";
if (!BASE || !OUT) { console.error("usage: node cmdra_0553_caps_context_r2.js <base> <out.json> <zh|en>"); process.exit(2); }

const ROUTES = ["/v8/hub", "/v8/live", "/v8/map", "/v8/studio", "/v8/stay", "/v8/discover",
  "/v8/bookings", "/v8/agent", "/v8/authoritative", "/v8/intelligence", "/v8/twin",
  "/v8/trash", "/v8/trips", "/v8/me"];

const SHAPES = [
  { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/ },
  { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/ },
  { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/ },
  { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/ },
];
const ALLOW = ["UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT"];

async function main() {
  const t0 = Date.now();
  const log = (m) => console.error("T+" + ((Date.now() - t0) / 1000).toFixed(1) + "s " + m);
  log("launch");
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  const bodies = [];
  const seen = {};
  page.on("response", (res) => {
    const url = res.url();
    if (!/\/api\//.test(url)) return;
    const path = url.replace(/^https?:\/\/[^/]+/, "");
    const h = res.headers();
    const key = path.split("?")[0];
    if (seen[key]) return;
    seen[key] = 1;
    // Metadata only: reading every body over CDP is what stalled the walk (measured -- 420s produced no file).
    // The server-word index is built afterwards by replaying these endpoints against the backend directly.
    bodies.push({ url: path, status: res.status(), ctype: (h["content-type"] || "").slice(0, 48),
                  bytes: Number(h["content-length"] || "0") });
  });

  log("base goto");
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  log("base loaded");
  const entry = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }

  log("demo clicked, walk start");
  const perRoute = {};
  for (const route of ROUTES) {
    log("route " + route);
    try {
      await page.goto(BASE.replace(/\/$/, "") + route, { waitUntil: "domcontentloaded", timeout: 25000 });
    } catch (e) {
      perRoute[route] = { hits: [], docChars: 0, goto_error: String(e).slice(0, 120) };
      continue;
    }
    log("  goto returned for " + route);
    await page.waitForTimeout(2500);
    log("  evaluate start " + route);
    perRoute[route] = await page.evaluate((cfg) => {
      const hits = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        const text = (n.nodeValue || "").trim();
        if (text.length < 3) continue;
        const el = n.parentElement;
        if (!el || el.closest("script,style,code,pre,noscript")) continue;
        const det = el.closest("details");
        if (det && !det.open) continue;
        const rg = document.createRange();
        rg.selectNodeContents(n);
        if (rg.getClientRects().length === 0) continue;
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0) continue;
        for (const s of cfg.shapes) {
          const re = new RegExp(s.re, "g");
          let m;
          while ((m = re.exec(text)) !== null) {
            const tok = m[0];
            if (!tok) { re.lastIndex += 1; continue; }
            if (s.kind === "ALLCAPS_WORD" && (cfg.allow.includes(tok) || /_/.test(tok))) continue;
            const anc = [];
            let cur = el;
            for (let i = 0; i < 4 && cur; i += 1) {
              anc.push(cur.tagName.toLowerCase() + ((cur.className || "").toString().trim() ? "." + cur.className.toString().trim().replace(/\s+/g, ".") : ""));
              cur = cur.parentElement;
            }
            hits.push({ kind: s.kind, token: tok, text_head: text.slice(0, 110),
              tag: el.tagName.toLowerCase(), cls: (el.className || "").toString().slice(0, 70),
              standalone_line: text === tok, ancestors: anc });
          }
        }
      }
      return { hits, docChars: (document.body.innerText || "").length };
    }, { shapes: SHAPES.map((s) => ({ kind: s.kind, re: s.re.source })), allow: ALLOW });
  }

  log("walk done");
  let valueIndex = {};
  const idxPath = process.argv[5] || "";
  if (idxPath && fs.existsSync(idxPath)) valueIndex = JSON.parse(fs.readFileSync(idxPath, "utf8"));

  const census = {};
  for (const [route, r] of Object.entries(perRoute)) {
    for (const h of r.hits) {
      const c = (census[h.token] = census[h.token] || { token: h.token, kind: h.kind, routes: {}, slots: {},
        server_answered_fields: valueIndex[h.token] || [], provenance: (valueIndex[h.token] || []).length ? "server-answer" : "not-in-any-response" });
      c.routes[route] = (c.routes[route] || 0) + 1;
      c.slots[h.cls || h.tag] = (c.slots[h.cls || h.tag] || 0) + 1;
    }
  }

  const report = {
    instrument: "cmdra_0553_caps_context_r2",
    script_sha256: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    base: BASE, locale: LOCALE, viewport: "390x844", entryAssets: entry, routesWalked: ROUTES.length,
    apiResponses: bodies.length, apiResponseList: bodies,
    server_index_file: idxPath || "(none -- classification done by _census_r5.py)",
    indexed_server_strings: Object.keys(valueIndex).length,
    totals: {
      painted_hits: Object.values(perRoute).reduce((a, r) => a + r.hits.length, 0),
      distinct_tokens: Object.keys(census).length,
      routes_with_hits: Object.entries(perRoute).filter(([, r]) => r.hits.length).length,
      server_answer_tokens: Object.values(census).filter((c) => c.provenance === "server-answer").length,
      style_only_tokens: Object.values(census).filter((c) => c.provenance === "not-in-any-response").length,
    },
    pageErrors: pageErrors, perRoute, census,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  log("file written");
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify({ out: OUT, locale: LOCALE, entry, totals: report.totals,
    server_answer_tokens: Object.values(census).filter((c) => c.provenance === "server-answer")
      .map((c) => c.token).sort(), pageErrors: pageErrors.length }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
