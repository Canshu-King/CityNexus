/* ORD-0553 r3 -- where does a painted CAPS token come from on /v8/authoritative?
 *
 * The commander reads one standalone `COMPLETED` and one standalone `ARRIVED` on the en arm of this
 * screen.  Static grep over the six panels mounted here does not converge on a render site, so this
 * probe stops guessing: it reads every visible text node that matches the sweep's four machine shapes
 * and prints, for each one, the element's own class, its ancestor class chain, and the full text of
 * the nearest block -- and alongside that it keeps every API response body this screen received, so a
 * token can be matched against the exact field value the server answered.
 *
 * A token that equals a status/state value in a captured response body is a server answer.  A token
 * that appears nowhere in any response body, only in the bundle's own copy, is a style word.  The
 * probe decides with the two lists printed; it does not assert.
 *
 * usage: node cmdra_0553_caps_context_r1.js <base> <out.json> <zh|en>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "en";
if (!BASE || !OUT) {
  console.error("usage: node cmdra_0553_caps_context_r1.js <base> <out.json> <zh|en>");
  process.exit(2);
}

const SHAPES = [
  { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/g },
  { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/g },
  { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/g },
  { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/g },
];
const ALLOW = ["UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT"];
const TESTIDS = ["recovery-required-panel", "plan-version-history", "v12-authoritative-panel",
  "v12-trip-studio", "v14-preventive", "v14-recovery-truth", "v12-authoritative-page"];

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));

  /* Every JSON the screen asked for, so a token on screen can be traced to a field the server answered. */
  const bodies = [];
  page.on("response", async (res) => {
    const url = res.url();
    if (!/\/api\//.test(url)) return;
    let json = null;
    try { json = await res.json(); } catch { return; }
    bodies.push({ url: url.replace(/^https?:\/\/[^/]+/, ""), status: res.status(), payload: json });
  });

  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  const entry = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }
  await page.goto(BASE.replace(/\/$/, "") + "/v8/authoritative", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);

  const screen = await page.evaluate((cfg) => {
    const chain = (el) => {
      const parts = [];
      let cur = el;
      for (let i = 0; i < 5 && cur && cur.tagName; i += 1) {
        const cls = (cur.className || "").toString().trim().replace(/\s+/g, ".");
        const tid = cur.getAttribute && cur.getAttribute("data-testid");
        parts.push(cur.tagName.toLowerCase() + (tid ? `[${tid}]` : "") + (cls ? "." + cls : ""));
        cur = cur.parentElement;
      }
      return parts;
    };
    const blockText = (el) => {
      let cur = el;
      for (let i = 0; i < 6 && cur; i += 1) {
        const t = (cur.textContent || "").replace(/\s+/g, " ").trim();
        if (t && t.length <= 220) return { tag: cur.tagName.toLowerCase(), text: t };
        cur = cur.parentElement;
      }
      return { tag: el.tagName.toLowerCase(), text: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 220) };
    };
    const visible = (n, el) => {
      if (el.closest("script,style,code,pre,noscript")) return false;
      const det = el.closest("details");
      if (det && !det.open) return false;
      const rg = document.createRange();
      rg.selectNodeContents(n);
      if (rg.getClientRects().length === 0) return false;
      const cs = getComputedStyle(el);
      return !(cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0);
    };
    const hits = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const text = (n.nodeValue || "").trim();
      if (text.length < 3) continue;
      const el = n.parentElement;
      if (!el || !visible(n, el)) continue;
      for (const s of cfg.shapes) {
        const re = new RegExp(s.re.source, "g");
        let m;
        while ((m = re.exec(text)) !== null) {
          const tok = m[0];
          if (s.kind === "ALLCAPS_WORD" && (cfg.allow.includes(tok) || /_/.test(tok))) continue;
          hits.push({ kind: s.kind, token: tok, node_text: text.slice(0, 140),
            tag: el.tagName.toLowerCase(), cls: (el.className || "").toString().slice(0, 70),
            standalone_line: text === tok, ancestors: chain(el), block: blockText(el) });
        }
      }
    }
    const panels = {};
    for (const tid of cfg.testids) {
      const el = document.querySelector(`[data-testid="${tid}"]`);
      panels[tid] = el ? (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 400) : null;
    }
    return { hits, panels,
      journeyId: localStorage.getItem("citynexus.v8.journey_id") || "",
      docChars: (document.body.innerText || "").length };
  }, { shapes: SHAPES.map((s) => ({ kind: s.kind, re: { source: s.re.source } })), allow: ALLOW, testids: TESTIDS });

  /* Cross-check: does each painted token appear as a *value* in any response this screen got? */
  const valueIndex = {};
  const walk = (v, path) => {
    if (v === null || v === undefined) return;
    if (typeof v === "string") { (valueIndex[v] = valueIndex[v] || []).push(path); return; }
    if (Array.isArray(v)) { v.forEach((x, i) => walk(x, `${path}[${i}]`)); return; }
    if (typeof v === "object") { for (const [k, x] of Object.entries(v)) walk(x, `${path}.${k}`); }
  };
  for (const b of bodies) walk(b.payload, b.url);

  const tokens = [...new Set(screen.hits.map((h) => h.token))];
  const traced = tokens.map((t) => ({
    token: t,
    painted_in: screen.hits.filter((h) => h.token === t).map((h) => `${h.tag}.${h.cls || "-"}`),
    standalone_lines: screen.hits.filter((h) => h.token === t && h.standalone_line).length,
    server_field_paths: (valueIndex[t] || []).slice(0, 6),
    provenance: (valueIndex[t] || []).length ? "value-the-server-answered" : "not-in-any-response-body",
  }));

  const report = {
    instrument: "cmdra_0553_caps_context_r1",
    script_sha256: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    base: BASE, locale: LOCALE, viewport: "390x844", entryAssets: entry,
    journeyId: screen.journeyId, docChars: screen.docChars,
    apiResponses: bodies.map((b) => ({ url: b.url, status: b.status })),
    paintedTokens: tokens, traced, hits: screen.hits, panels: screen.panels, pageErrors,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify({ out: OUT, locale: LOCALE, entry, journeyId: screen.journeyId,
    paintedTokens: tokens, traced, pageErrors: pageErrors.length }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
