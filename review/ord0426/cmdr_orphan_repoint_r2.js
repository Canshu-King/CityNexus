/* ORD-0426 — triage the 27 "no consumer" selectors by what is ON SCREEN, not by class names.  v2.
 *
 * v1's defect, disclosed because it is exactly the trap this order is about: for a class-only
 * selector it fell back to querySelectorAll("*"), whose first element is <html>, so every property
 * looked wrong and 18 rules were "REPOINT".  A role must be argued from structure, not from any
 * element that happens to exist.  Three bases, strongest first:
 *   group_sibling    another selector in the same declaration block matches -> the rule's intent
 *                    already reaches those elements; the unused class is a naming problem.
 *   ancestor_context the longest prefix of the selector that does match -> candidates are elements
 *                    inside it (its children, or its descendants with the rule's tag).
 *   leaf_tag         the leaf names a tag (a.v8-cta -> a) -> visible elements of that tag inside
 *                    .v8-page/main, never html/body.
 * Otherwise there is no role evidence on the walked surfaces -> DEAD_LEGACY.
 *
 * The title arm answers the commander's real worry directly: every h1/h2/h3 that paints, what it
 * computes, what --cn-fs-display / --cn-fs-title resolve to, and WHICH rule wins the cascade for
 * font-size on that element (all parsed selectors from both files, ordered by bundle position).
 * Line counts use Range.getClientRects().length per the order's instrument lesson.
 *
 * Usage: node cmdr_orphan_repoint_r2.js <base> <out-dir> <src-root> <dist-css> <in-census.json>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2];
const OUT = process.argv[3];
const SRC = process.argv[4];
const DIST_CSS = process.argv[5];
const CENSUS = process.argv[6];
const TIP = process.argv[7];
if (!/^[0-9a-f]{40}$/.test(TIP)) { console.log("ABORT: the 7th argument must be the 40-hex generation under test"); process.exit(2); }
const LOCALES = (process.env.CENSUS_LOCALES || "zh,en").split(",");
const SHAPES = (process.env.CENSUS_SHAPES || "390x844,320x653,414x896").split(",")
  .map((s) => ({ width: Number(s.split("x")[0]), height: Number(s.split("x")[1]) }));
const ROUTES = (process.env.CENSUS_ROUTES ||
  "hub,live,map,studio,stay,discover,bookings,agent,authoritative,intelligence,twin,trash,trips,me").split(",");

const blankComments = (t) => t.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[\S\s]/g, (c) => (c === "\n" ? "\n" : " ")));
const lineIndex = (text, idx) => { let n = 1; for (let i = 0; i < idx; i++) if (text[i] === "\n") n++; return n; };
function splitTopLevel(prelude) {
  const out = []; let d = 0, cur = "", segStart = 0;
  for (let k = 0; k < prelude.length; k++) {
    const ch = prelude[k];
    if (cur === "" && /\s/.test(ch)) { segStart = k + 1; continue; }
    if (ch === "(" || ch === "[" || ch === "{") d++;
    else if (ch === ")" || ch === "]" || ch === "}") d--;
    if (ch === "," && d === 0) { if (cur.trim()) out.push([cur.trim(), segStart]); cur = ""; segStart = k + 1; continue; }
    cur += ch;
  }
  if (cur.trim()) out.push([cur.trim(), segStart]);
  return out;
}
function parseDecls(body) {
  const out = {};
  body.split(";").forEach((d) => {
    const i = d.indexOf(":"); if (i < 0) return;
    const p = d.slice(0, i).trim(), v = d.slice(i + 1).replace(/!important/g, "").trim();
    if (p && v && !p.startsWith("@")) out[p] = v;
  });
  return out;
}
function parseCss(file) {
  const raw = fs.readFileSync(file, "utf-8");
  const text = blankComments(raw);
  const rules = [];
  let order = 0;
  const walk = (from, to, media) => {
    let i = from, start = from;
    while (i < to) {
      const ch = text[i];
      if (ch === "{") {
        const rawPrelude = text.slice(start, i);
        const prelude = rawPrelude.trim();
        const base = start + (rawPrelude.length - rawPrelude.trimStart().length);
        let depth = 1, j = i + 1;
        while (j < to && depth > 0) { if (text[j] === "{") depth++; else if (text[j] === "}") depth--; j++; }
        const bodyEnd = j - 1;
        if (/^@(media|supports|layer|container)/.test(prelude)) walk(i + 1, bodyEnd, prelude.replace(/\s+/g, " "));
        else if (!prelude.startsWith("@")) {
          const body = text.slice(i + 1, bodyEnd);
          splitTopLevel(prelude).forEach(([sel, off]) => {
            if (!sel || sel.includes("{")) return;
            rules.push({ selector: sel.replace(/\s+/g, " ").trim(), file: path.basename(file),
              line: lineIndex(raw, base + off), media, decls: parseDecls(body),
              group: prelude.replace(/\s+/g, " ").trim(), order: order++ });
          });
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

const THIRD_PARTY = /maplibregl-|mapboxgl-|leaflet-/;
const VISUAL = ["font-size", "font-weight", "line-height", "letter-spacing", "color", "background",
  "background-color", "display", "grid-template-columns", "grid-template-rows", "flex-direction",
  "gap", "padding", "margin", "min-height", "height", "width", "border-radius", "border-color",
  "text-transform", "opacity", "transform", "justify-content", "align-items", "position", "flex"];

(async () => {
  fs.mkdirSync(path.join(OUT, "shots"), { recursive: true });
  const cssFiles = ["src/styles.css", "src/design-tokens.css"].map((f) => path.join(SRC, f));
  const allRules = [];
  cssFiles.forEach((f) => parseCss(f).forEach((r) => allRules.push(r)));
  const census = JSON.parse(fs.readFileSync(CENSUS, "utf-8"));
  const wanted = census.all_zero_rows.filter((r) => r.class === "DEAD_RULE_NO_CONSUMER").map((r) => r.selector);

  /* The cascade order is measured from the bytes the browser loaded, not from the order I read the
     two source files: design-tokens.css:235 sits AFTER styles.css:178 in the shipped CSS, which is
     why h1 computes 34px and the 30px media rule never paints.  Assuming the order would have made
     me name the wrong winner. */
  const shippedNorm = DIST_CSS && fs.existsSync(DIST_CSS)
    ? fs.readFileSync(DIST_CSS, "utf-8").replace(/\s+/g, "") : null;
  const shippedOffset = (sel) => {
    if (!shippedNorm) return null;
    const i = shippedNorm.indexOf(sel.replace(/\s+/g, ""));
    return i >= 0 ? i : null;
  };
  allRules.forEach((r) => { r.shipped_offset = shippedOffset(r.selector);
    r.in_shipped = r.shipped_offset !== null; });

  const specs = wanted.map((sel) => {
    const hits = allRules.filter((r) => r.selector === sel);
    const leaf = sel.replace(/>|\+|~/g, " ").split(/\s+/).filter(Boolean).pop() || "";
    const leafTag = leaf.replace(/[.:#[][\s\S]*/, "");
    return { selector: sel, sources: hits.map((h) => `${h.file}:${h.line}`),
      group: hits[0] ? hits[0].group : null, media: hits[0] ? hits[0].media : null,
      decls: hits[0] ? hits[0].decls : {}, leaf, leafTag: leafTag || null,
      siblings: hits.length ? splitTopLevel(hits[0].group).map(([s]) => s.replace(/\s+/g, " ").trim()).filter((s) => s !== sel) : [],
      prefixes: (() => { const p = sel.replace(/>|\+|~/g, " ").split(/\s+/).filter(Boolean);
        const out = []; for (let n = p.length - 1; n >= 1; n--) out.push(p.slice(0, n).join(" ")); return out; })() };
  });

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const pageErrors = [], sweeps = [], loadedCss = new Set();
  const perRule = {};
  const allSelectorsForCascade = allRules
    .filter((r) => r.in_shipped)
    .map((r) => ({ sel: r.selector, file: r.file, line: r.line,
      order: r.shipped_offset, decls: Object.keys(r.decls), media: r.media }));

  for (const locale of LOCALES) {
    for (const shape of SHAPES) {
      const ctx = await browser.newContext({ viewport: shape, hasTouch: true });
      const page = await ctx.newPage();
      page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
      await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
      const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
      if (await seal.count()) { await seal.click(); await page.waitForTimeout(4000); }
      if (locale === "en") {
        const en = page.getByText("EN", { exact: true }).first();
        if (await en.count()) { await en.click(); await page.waitForTimeout(2500); }
      }
      for (const route of ROUTES) {
        await page.goto(`${BASE.replace(/\/$/, "")}/v8/${route}`, { waitUntil: "load", timeout: 90000 });
        await page.waitForTimeout(2500);
        const res = await page.evaluate(({ specs, allSelectors, visual }) => {
          const rootCS = getComputedStyle(document.documentElement);
          const norm = (s) => String(s == null ? "" : s).toLowerCase()
            .replace(/none repeat scroll 0% 0% \/ auto padding-box border-box/, "").replace(/\s+/g, " ").trim();
          const resolve = (v) => !v ? v : String(v).replace(/var\((--[a-z0-9-]+)[^)]*\)/gi,
            (m, name) => rootCS.getPropertyValue(name).trim() || m);
          const textLines = (el) => { const r = document.createRange(); r.selectNodeContents(el); return r.getClientRects().length; };
          const vis = (el) => { const b = el.getBoundingClientRect();
            return b.width > 0 && b.height > 0 && b.top < innerHeight && b.bottom > 0; };
          const notRoot = (el) => { const t = el.tagName.toLowerCase();
            if (t === "html" || t === "body" || t === "main") return false;
            const b = el.getBoundingClientRect();
            return b.width <= innerWidth * 0.98 && b.height <= innerHeight * 1.6; };
          const diffsFor = (el, decls) => {
            const cs = getComputedStyle(el); const out = [];
            for (const p of Object.keys(decls)) {
              if (!visual.includes(p)) continue;
              const w = resolve(decls[p]), g = cs.getPropertyValue(p);
              if (!w) continue;
              const nw = norm(w), ng = norm(g);
              if (nw === ng || nw.startsWith(ng + " ") || ng.startsWith(nw + " ")) continue;
              out.push([p, w, g]);
            }
            return out;
          };
          const describe = (el, decls, basis, via) => {
            const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
            return { basis, via, tag: el.tagName.toLowerCase(), classes: String(el.className || "").slice(0, 70),
              id: el.id || null, text: (el.textContent || "").trim().slice(0, 34),
              rect: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)],
              textRectLines: textLines(el), diffs: diffsFor(el, decls),
              computed_font: cs.fontSize };
          };

          const out = {};
          for (const sp of specs) {
            let own = 0;
            try { own = document.querySelectorAll(sp.selector).length; } catch (e) { own = -1; }
            const sib = sp.siblings.map((s) => { try { return [s, document.querySelectorAll(s).length]; } catch (e) { return [s, -1]; } });
            const rec = { own, siblings: sib, role: [], basis: "none" };

            const sibHit = sib.filter(([, n]) => n > 0);
            if (sibHit.length) {
              rec.basis = "group_sibling";
              // the element the sibling half reaches is the role; check whether it got the rule's value
              for (const [s, n] of sibHit.slice(0, 2)) {
                for (const el of Array.from(document.querySelectorAll(s)).filter((e) => vis(e) && notRoot(e)).slice(0, 3)) {
                  rec.role.push(describe(el, sp.decls, "group_sibling", s));
                }
              }
            } else {
              let prefixFound = null;
              for (const p of sp.prefixes) {
                try { const els = Array.from(document.querySelectorAll(p)).filter(vis); if (els.length) { prefixFound = { p, els }; break; } } catch (e) {}
              }
              if (prefixFound) {
                rec.basis = "ancestor_context";
                for (const host of prefixFound.els.slice(0, 4)) {
                  const inside = sp.leafTag
                    ? Array.from(host.querySelectorAll(sp.leafTag))
                    : Array.from(host.children);
                  for (const el of inside.filter((e) => vis(e) && notRoot(e)).slice(0, 3)) {
                    rec.role.push(describe(el, sp.decls, "ancestor_context", prefixFound.p + " > " + (sp.leafTag || "*")));
                  }
                }
              } else if (sp.leafTag) {
                rec.basis = "leaf_tag";
                const scope = document.querySelector(".v8-page") || document.querySelector("main") || document.body;
                for (const el of Array.from(scope.querySelectorAll(sp.leafTag)).filter((e) => vis(e) && notRoot(e)).slice(0, 3)) {
                  rec.role.push(describe(el, sp.decls, "leaf_tag", sp.leafTag));
                }
              }
            }
            if (THIRD_PARTY_TEST(sp.selector)) {
              const cls = (sp.selector.match(/\.[a-z0-9-]*(?:maplibregl|mapboxgl)[a-z0-9-]*/i) || [null])[0];
              rec.third_party_class = cls;
              rec.third_party_hits = cls ? document.querySelectorAll(cls).length : 0;
              rec.third_party_gesture_node = document.querySelectorAll(".maplibregl-cooperative-gesture-screen").length;
            }
            out[sp.selector] = rec;
            function THIRD_PARTY_TEST(s) { return /maplibregl-|mapboxgl-|leaflet-/.test(s); }
          }

          /* title arm: every heading that paints, its computed size, the token values, and who wins */
          const tokens = {};
          for (const t of ["--cn-fs-display", "--cn-fs-title", "--cn-lh-tight"]) tokens[t] = rootCS.getPropertyValue(t).trim();
          const titleArm = [];
          for (const el of Array.from(document.querySelectorAll("h1, h2, h3"))) {
            if (!vis(el) || !notRoot(el)) continue;
            const cs = getComputedStyle(el);
            const b = el.getBoundingClientRect();
            const contenders = [];
            for (const r of allSelectors) {
              let m = false;
              try { m = el.matches(r.sel); } catch (e) { continue; }
              if (!m) continue;
              for (const p of ["font-size", "font-weight", "line-height", "letter-spacing", "color"]) {
                if (r.decls.includes(p)) contenders.push({ prop: p, file: r.file, line: r.line, sel: r.sel, order: r.order, media: r.media });
              }
            }
            contenders.sort((a, b2) => a.order - b2.order);
            const winner = {};
            contenders.forEach((c) => { winner[c.prop] = `${c.file}:${c.line} ${c.sel}${c.media ? " {" + c.media + "}" : ""}`; });
            titleArm.push({ tag: el.tagName.toLowerCase(), classes: String(el.className || "").slice(0, 60),
              id: el.id || null, text: (el.textContent || "").trim().slice(0, 40),
              rect: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)],
              textRectLines: textLines(el),
              computed: { "font-size": cs.fontSize, "font-weight": cs.fontWeight,
                "line-height": cs.lineHeight, "letter-spacing": cs.letterSpacing, "color": cs.color },
              fs_display_px: tokens["--cn-fs-display"], fs_title_px: tokens["--cn-fs-title"],
              on_display_档位: norm(cs.fontSize) === norm(tokens["--cn-fs-display"]),
              on_title_档位: norm(cs.fontSize) === norm(tokens["--cn-fs-title"]),
              winner_font_size: winner["font-size"] || null,
              contenders_font_size_count: contenders.filter((c) => c.prop === "font-size").length,
              contenders: contenders.map((c) => `${c.file}:${c.line} ${c.sel} [${c.prop}]${c.media ? " @" + c.media : ""}`).slice(0, 14) });
          }
          out.__titleArm = titleArm;
          out.__tokens = tokens;
          return out;
        }, { specs, allSelectors: allSelectorsForCascade, visual: VISUAL });

        const title = res.__titleArm || [];
        const tokens = res.__tokens || {};
        Object.entries(res).forEach(([sel, v]) => {
          if (sel === "__titleArm" || sel === "__tokens") return;
          const rec = perRule[sel] || (perRule[sel] = { own_max: 0, sib_max: {}, role: [], third: {} });
          if (v.own > rec.own_max) rec.own_max = v.own;
          (v.siblings || []).forEach(([s, n]) => { rec.sib_max[s] = Math.max(rec.sib_max[s] || 0, n); });
          (v.role || []).forEach((r) => { if (rec.role.length < 24) rec.role.push({ ...r, screen: `${locale}/${shape.width}x${shape.height}/${route}` }); });
          rec.third = { class: v.third_party_class, hits: v.third_party_hits, gesture_node: v.third_party_gesture_node };
        });
        title.forEach((t) => sweeps.push({ locale, shape: `${shape.width}x${shape.height}`, route, tokens, heading: t }));
      }
      const assets = await page.evaluate(() => performance.getEntriesByType("resource")
        .map((x) => x.name).filter((n) => /\.(css|js)$/.test(n)).map((n) => n.split("/").pop()));
      assets.forEach((c) => loadedCss.add(c));
      await ctx.close();
    }
  }
  await browser.close();

  const rows = specs.map((sp) => {
    const rec = perRule[sp.selector] || { own_max: 0, sib_max: {}, role: [], third: {} };
    const covered = Object.entries(rec.sib_max).filter(([, n]) => n > 0).map(([s]) => s);
    const role = rec.role.filter((r) => r.diffs.length);
    const third = THIRD_PARTY.test(sp.selector);
    let cls;
    if (third) cls = "THIRD_PARTY_DOM_NOT_DEAD";
    else if (rec.own_max > 0) cls = "NO_LONGER_NO_CONSUMER_ON_THIS_TIP";
    else if (covered.length && role.length === 0) cls = "INTENT_APPLIED_VIA_GROUP_SIBLING";
    else if (covered.length) cls = "INTENT_APPLIED_VIA_GROUP_SIBLING";
    else if (role.length) cls = "ORPHAN_LAYOUT_RULE_WANTS_REPOINT";
    else cls = "DEAD_LEGACY";
    role.sort((a, b) => b.diffs.length - a.diffs.length || (b.rect[2] * b.rect[3]) - (a.rect[2] * a.rect[3]));
    const grp = sp.group ? allRules.filter((r) => r.group === sp.group) : [];
    return { selector: sp.selector, source_on_this_tip: sp.sources, group: sp.group, media: sp.media,
      group_rules_in_shipped_order: grp.map((r) => `${r.file}:${r.line} ${r.sel} @${r.shipped_offset}`).slice(0, 6),
      own_hits_max: rec.own_max, sibling_hits: rec.sib_max, covered_by_sibling: covered,
      role_basis: rec.role[0] ? rec.role[0].basis : "none", role_candidates: role.slice(0, 3),
      third_party: third ? rec.third : null, class: cls };
  });
  rows.sort((a, b) => ({ ORPHAN_LAYOUT_RULE_WANTS_REPOINT: 3, NO_LONGER_NO_CONSUMER_ON_THIS_TIP: 3,
    INTENT_APPLIED_VIA_GROUP_SIBLING: 2, THIRD_PARTY_DOM_NOT_DEAD: 1, DEAD_LEGACY: 0 })[b.class]
    - ({ ORPHAN_LAYOUT_RULE_WANTS_REPOINT: 3, NO_LONGER_NO_CONSUMER_ON_THIS_TIP: 3,
      INTENT_APPLIED_VIA_GROUP_SIBLING: 2, THIRD_PARTY_DOM_NOT_DEAD: 1, DEAD_LEGACY: 0 })[a.class]
    || (b.role_candidates[0] ? b.role_candidates[0].diffs.length : 0) - (a.role_candidates[0] ? a.role_candidates[0].diffs.length : 0));

  const headingsOffToken = sweeps.filter((s) => s.heading.tag === "h1" && !s.heading.on_display_档位);
  const shippedSorted = (x) => x;
  const receipt = {
    at: new Date().toISOString(), base: BASE, served_tip: TIP,
    css_assets_loaded: Array.from(loadedCss), rules_parsed_on_this_tip: allRules.length,
    wanted_from_ord0421: wanted.length,
    scenarios: { locales: LOCALES, shapes: SHAPES.map((s) => `${s.width}x${s.height}`), routes: ROUTES },
    heading_samples: sweeps.length,
    class_counts: rows.reduce((a, r) => (a[r.class] = (a[r.class] || 0) + 1, a), {}),
    h1_off_display_档位: headingsOffToken.length,
    h1_samples: sweeps.filter((s) => s.heading.tag === "h1").slice(0, 12).map((s) => ({
      screen: `${s.locale}/${s.shape}/${s.route}`, text: s.heading.text, classes: s.heading.classes,
      computed_font_size: s.heading.computed["font-size"], token_fs_display: s.heading.fs_display_px,
      on_档位: s.heading.on_display_档位, winner: s.heading.winner_font_size,
      contenders_font_size_count: s.heading.contenders_font_size_count,
      textRectLines: s.heading.textRectLines, rect: s.heading.rect })),
    h2_samples: sweeps.filter((s) => s.heading.tag === "h2").slice(0, 10).map((s) => ({
      screen: `${s.locale}/${s.shape}/${s.route}`, text: s.heading.text, classes: s.heading.classes,
      computed_font_size: s.heading.computed["font-size"], token_fs_title: s.heading.fs_title_px,
      on_档位: s.heading.on_title_档位, winner: s.heading.winner_font_size,
      contenders_font_size_count: s.heading.contenders_font_size_count,
      textRectLines: s.heading.textRectLines })),
    rows, pageerrors: pageErrors,
  };
  fs.writeFileSync(path.join(OUT, "orphan_repoint_r2.json"), JSON.stringify(receipt, null, 1), "utf-8");
  console.log(JSON.stringify({ rules: allRules.length, wanted: wanted.length, heading_samples: sweeps.length,
    class_counts: receipt.class_counts, h1_off_档位: receipt.h1_off_display_档位 }, null, 1));
  receipt.h1_samples.slice(0, 4).forEach((h) => console.log("H1", h.screen, JSON.stringify(h.computed_font_size),
    "token", h.token_fs_display_px, "on_档位", h.on_档位, "winner", h.winner, "lines", h.textRectLines));
  rows.filter((r) => r.class === "ORPHAN_LAYOUT_RULE_WANTS_REPOINT").slice(0, 10).forEach((r) =>
    console.log("REPOINT", r.source_on_this_tip.join("|"), r.selector, "basis", r.role_basis,
      JSON.stringify(r.role_candidates[0] || {}).slice(0, 170)));
})().catch((e) => { console.log("FATAL", String(e).slice(0, 400)); process.exit(9); });
