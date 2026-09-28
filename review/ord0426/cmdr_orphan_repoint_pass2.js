/* ORD-0426 pass 2 — two gaps in my own pass-1 readings, closed here rather than shipped.
 *
 * (a) DEAD_LEGACY was asserted for layout rules like `.v8-live-grid` without ever asking what the
 *     rule's ROLE is.  A class-only selector has no ancestor prefix to probe, so pass 1 reported
 *     "basis none".  Here the role is recovered by a naming-family probe: take the classes that DO
 *     exist on screen and share the rule's prefix (`.v8-live-grid` -> `.v8-live-main`, `.v8-live-now`),
 *     and their nearest common ancestor is the container the rule was written for.  If that
 *     container is on screen but computes a different value than the rule wants, the rule is not
 *     legacy — it is an orphan the markup grew past.
 * (b) pass 1 only kept 12 h1 samples, all from one shape, so "h1 does not scale with the viewport"
 *     was not measurable.  Here every requested width is walked and each h1's computed font-size is
 *     recorded next to --cn-fs-display and the shipped byte offsets of the three competing rules.
 *
 * Usage: node cmdr_orphan_repoint_pass2.js <base> <out-dir> <src-root> <dist-css> <pass1.json>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2];
const OUT = process.argv[3];
const SRC = process.argv[4];
const DIST_CSS = process.argv[5];
const PASS1 = process.argv[6];
const TIP = process.argv[7];
if (!/^[0-9a-f]{40}$/.test(TIP)) { console.log("ABORT: the 7th argument must be the 40-hex generation under test"); process.exit(2); }
const WIDTHS = (process.env.PASS2_WIDTHS || "320,360,390,414,800,1280").split(",")
  .map((w) => ({ width: Number(w), height: w === 653 || Number(w) < 700 ? 850 : 900 }));
const ROUTES = (process.env.PASS2_ROUTES || "hub,live,map,studio,stay,twin,intelligence,agent,trips,me").split(",");

const blank = (t) => t.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[\S\s]/g, (c) => (c === "\n" ? "\n" : " ")));
const lineOf = (text, idx) => { let n = 1; for (let i = 0; i < idx; i++) if (text[i] === "\n") n++; return n; };
function parse(file) {
  const raw = fs.readFileSync(file, "utf-8");
  const text = blank(raw);
  const rules = [];
  const walk = (from, to, media) => {
    let i = from, start = from;
    while (i < to) {
      const ch = text[i];
      if (ch === "{") {
        const rp = text.slice(start, i);
        const prelude = rp.trim();
        const base = start + (rp.length - rp.trimStart().length);
        let d = 1, j = i + 1;
        while (j < to && d > 0) { if (text[j] === "{") d++; else if (text[j] === "}") d--; j++; }
        const bodyEnd = j - 1;
        if (/^@(media|supports)/.test(prelude)) walk(i + 1, bodyEnd, prelude.replace(/\s+/g, " "));
        else if (!prelude.startsWith("@")) {
          const body = text.slice(i + 1, bodyEnd);
          let dd = 0, cur = "", seg = 0;
          const parts = [];
          for (let k = 0; k < prelude.length; k++) {
            const c = prelude[k];
            if (cur === "" && /\s/.test(c)) { seg = k + 1; continue; }
            if (c === "(" || c === "[") dd++;
            else if (c === ")" || c === "]") dd--;
            if (c === "," && dd === 0) { if (cur.trim()) parts.push([cur.trim(), seg]); cur = ""; seg = k + 1; continue; }
            cur += c;
          }
          if (cur.trim()) parts.push([cur.trim(), seg]);
          const decls = {};
          body.split(";").forEach((x) => { const q = x.indexOf(":"); if (q < 0) return;
            const p2 = x.slice(0, q).trim(), v = x.slice(q + 1).replace(/!important/g, "").trim();
            if (p2 && v && !p2.startsWith("@")) decls[p2] = v; });
          parts.forEach(([sel, off]) => rules.push({
            selector: sel.replace(/\s+/g, " ").trim(), file: path.basename(file),
            line: lineOf(raw, base + off), media, decls, group: prelude.replace(/\s+/g, " ").trim() }));
        }
        i = bodyEnd + 1; start = i; continue;
      }
      if (ch === "}") { i++; start = i; continue; }
      i++;
    }
  };
  walk(0, text.length, null);
  return rules;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const rules = [];
  ["src/styles.css", "src/design-tokens.css"].forEach((f) => parse(path.join(SRC, f)).forEach((r) => rules.push(r)));
  const shippedNorm = fs.readFileSync(DIST_CSS, "utf-8").replace(/\s+/g, "");
  rules.forEach((r) => { r.shipped_offset = shippedNorm.indexOf(r.selector.replace(/\s+/g, "")); });

  const p1 = JSON.parse(fs.readFileSync(PASS1, "utf-8"));
  const deadSel = p1.rows.filter((r) => r.class === "DEAD_LEGACY").map((r) => r.selector);
  const specs = deadSel.map((sel) => {
    const r = rules.filter((x) => x.selector === sel);
    return { selector: sel, sources: r.map((x) => `${x.file}:${x.line}`),
      decls: r[0] ? r[0].decls : {}, group: r[0] ? r[0].group : null,
      family: (sel.match(/[.#]?([a-z0-9]+(?:-[a-z0-9]+)+)/i) || [null, null])[1] };
  }).filter((s) => s.family);

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const pageErrors = [];
  const familyProbes = {};
  const titleTable = [];

  for (const shape of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: shape.width, height: shape.height } });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
    await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(4000); }
    for (const route of ROUTES) {
      await page.goto(`${BASE.replace(/\/$/, "")}/v8/${route}`, { waitUntil: "load", timeout: 90000 });
      await page.waitForTimeout(2500);
      const res = await page.evaluate(({ specs, rulesMeta, visual }) => {
        const rootCS = getComputedStyle(document.documentElement);
        const norm = (s) => String(s == null ? "" : s).toLowerCase().replace(/\s+/g, " ").trim();
        const resolve = (v) => !v ? v : String(v).replace(/var\((--[a-z0-9-]+)[^)]*\)/gi,
          (m, n) => rootCS.getPropertyValue(n).trim() || m);
        const vis = (el) => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
        const out = {};
        for (const sp of specs) {
          // elements that share the rule's naming family but are NOT the rule's own class
          const kin = Array.from(document.querySelectorAll("[class]")).filter((el) => {
            const cs = String(el.className || "");
            return cs.split(/\s+/).some((c) => c.includes(sp.family) && !sp.selector.includes(c));
          }).filter(vis);
          if (!kin.length) { out[sp.selector] = { kin: 0, container: null, diffs: [] }; continue; }
          // nearest common ancestor of the family members = the container the rule was written for
          let anc = kin[0];
          while (anc && !kin.every((k) => anc === k || anc.contains(k))) anc = anc.parentElement;
          if (!anc || anc.tagName.toLowerCase() === "body") { out[sp.selector] = { kin: kin.length, container: null, diffs: [] }; continue; }
          const cs = getComputedStyle(anc);
          const b = anc.getBoundingClientRect();
          const diffs = [];
          for (const p of Object.keys(sp.decls)) {
            if (!visual.includes(p)) continue;
            const w = resolve(sp.decls[p]), g = cs.getPropertyValue(p);
            if (norm(w) !== norm(g) && !norm(g).startsWith(norm(w)) && !norm(w).startsWith(norm(g))) diffs.push([p, w, g]);
          }
          out[sp.selector] = { kin: kin.length, kin_classes: kin.slice(0, 4).map((k) => String(k.className).slice(0, 44)),
            container: { tag: anc.tagName.toLowerCase(), classes: String(anc.className || "").slice(0, 60),
              rect: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)],
              computed: Object.fromEntries(Object.keys(sp.decls).filter((p) => visual.includes(p)).map((p) => [p, cs.getPropertyValue(p)])) },
            diffs, own_hits: document.querySelectorAll(sp.selector).length };
        }
        // title arm for this width
        const titles = [];
        for (const el of Array.from(document.querySelectorAll("h1")).filter(vis)) {
          const cs2 = getComputedStyle(el);
          const rg = document.createRange();
          rg.selectNodeContents(el);
          titles.push({ text: (el.textContent || "").trim().slice(0, 32),
            font_size: cs2.fontSize, line_height: cs2.lineHeight,
            token_display: rootCS.getPropertyValue("--cn-fs-display").trim(),
            token_title: rootCS.getPropertyValue("--cn-fs-title").trim(),
            textRectLines: rg.getClientRects().length,
            rect: [Math.round(el.getBoundingClientRect().x), Math.round(el.getBoundingClientRect().y),
                   Math.round(el.getBoundingClientRect().width), Math.round(el.getBoundingClientRect().height)] });
        }
        return { rules: out, titles };
      }, { specs, rulesMeta: rules.map((r) => ({ sel: r.selector, off: r.shipped_offset })),
        visual: ["display", "grid-template-columns", "grid-template-rows", "gap", "flex-direction",
          "justify-content", "align-items", "min-height", "padding", "margin", "border-radius",
          "font-size", "color", "height", "width"] });
      Object.entries(res.rules).forEach(([sel, v]) => {
        const rec = familyProbes[sel] || (familyProbes[sel] = { best: null, seen: [] });
        if (v.container && (!rec.best || (v.diffs || []).length > (rec.best.diffs || []).length)) rec.best = { ...v, screen: `${shape.width}/${route}` };
        if (v.container) rec.seen.push({ ...v, screen: `${shape.width}/${route}` });
      });
      res.titles.forEach((t) => titleTable.push({ width: shape.width, route, ...t }));
    }
    await ctx.close();
  }
  const competing = {};
  for (const sel of [".v8-page h1", ".v8-page h2"]) {
    competing[sel] = rules.filter((r) => r.selector === sel)
      .map((r) => `${r.file}:${r.line}${r.media ? " [" + r.media + "]" : ""} ${r.decls["font-size"] || ""} @${r.shipped_offset}`);
  }
  await browser.close();

  const reclassified = Object.entries(familyProbes).map(([sel, v]) => {
    const sp = specs.find((s) => s.selector === sel);
    const b = v.best;
    return { selector: sel, source: sp.sources, family: sp.family,
      kin_elements: b ? b.kin : 0, kin_classes: b ? b.kin_classes : null,
      container: b ? b.container : null, diffs: b ? b.diffs : [], own_hits: b ? b.own_hits : 0,
      class: b && b.diffs.length ? "ORPHAN_LAYOUT_RULE_WANTS_REPOINT" : "DEAD_LEGACY_CONFIRMED_NO_CONTAINER",
      screens_with_container: v.seen.length };
  }).sort((a, b) => b.diffs.length - a.diffs.length);

  const byWidth = {};
  titleTable.forEach((t) => { (byWidth[t.width] = byWidth[t.width] || []).push(t.font_size); });
  const receipt = {
    at: new Date().toISOString(), base: BASE, served_tip: TIP, widths: WIDTHS.map((w) => w.width), routes: ROUTES,
    dead_from_pass1: deadSel.length, competing_h1_h2_rules_in_shipped_order: competing,
    token_values: { "--cn-fs-display": "-- see titles", },
    h1_font_size_by_width: Object.fromEntries(Object.entries(byWidth).map(([k, v]) => [k, Array.from(new Set(v))])),
    h1_rows: titleTable.slice(0, 40), family_probe_counts:
      reclassified.reduce((a, r) => (a[r.class] = (a[r.class] || 0) + 1, a), {}),
    reclassified, pageerrors: pageErrors,
  };
  fs.writeFileSync(path.join(OUT, "orphan_repoint_pass2.json"), JSON.stringify(receipt, null, 1), "utf-8");
  console.log(JSON.stringify({ widths: receipt.h1_font_size_by_width,
    competing: receipt.competing_h1_h2_rules_in_shipped_order,
    counts: receipt.family_probe_counts }, null, 1));
  reclassified.filter((r) => r.class === "ORPHAN_LAYOUT_RULE_WANTS_REPOINT").slice(0, 8)
    .forEach((r) => console.log("REPOINT", r.source.join("|"), r.selector, "kin=" + r.kin_elements,
      JSON.stringify(r.container), JSON.stringify(r.diffs).slice(0, 150)));
})().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
