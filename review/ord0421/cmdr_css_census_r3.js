/* ORD-0421 — CSS dead-rule census, r3.  Reads only; no product byte is written.
 *
 * r2's mistake, kept on purpose so the next reader does not repeat it: it probed only the LAST
 * compound of a selector (`h1`, `div`, `p`), so a rule whose ancestor context merely wasn't on the
 * walked screens got called dead — 267 false "dead" rules out of 887.  The discriminator has to be
 * the context, not the leaf:
 *
 *   exact    = document.querySelectorAll(<selector>)
 *   ancestor = the selector minus its last compound            -> is the context mounted at all?
 *   inside   = within an ancestor element, the last compound    -> is the leaf present under it?
 *   token    = does the leaf's class/id appear in frontend/src  -> does any component emit it?
 *
 * A rule is a real defect only when the context IS mounted and the leaf IS under it, yet the full
 * selector matches nothing — that is a combinator/attribute that can never hold, exactly the
 * `#v8-nav-drawer > button` family the commander hit.  Everything else is labelled, not counted.
 *
 * Usage: node cmdr_css_census_r3.js <base> <out-dir> <src-root> <dist-css-file>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2];
const OUT = process.argv[3];
const SRC = process.argv[4];
const DIST_CSS = process.argv[5];

const LOCALES = (process.env.CENSUS_LOCALES || "zh,en").split(",");
const SHAPES = (process.env.CENSUS_SHAPES || "390x844,320x653,414x896").split(",")
  .map((s) => ({ width: Number(s.split("x")[0]), height: Number(s.split("x")[1]) }));
const ALL_ROUTES = ["hub", "live", "map", "studio", "stay", "discover", "bookings", "agent",
  "authoritative", "intelligence", "twin", "trash", "trips", "me"];
const ROUTES = process.env.CENSUS_ROUTES ? process.env.CENSUS_ROUTES.split(",") : ALL_ROUTES;

/* ------------------------------ css parsing ------------------------------ */
// Blank comments out but KEEP their newlines: replacing a 4-line comment with 4 spaces would shift
// every line number that follows it, and this file's whole purpose is to hand out path:line.
const blankComments = (t) => t.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[\S\s]/g, (c) => (c === "\n" ? "\n" : " ")));
function lineIndex(text, idx) {
  let line = 1, seen = 0;
  for (let i = 0; i < idx; i++) if (text[i] === "\n") { line++; seen = i; }
  return line;
}
function splitTopLevel(prelude) {
  // returns [selectorText, offsetWithinPrelude] — the offset is what makes the path:line honest:
  // the prelude starts right after the PREVIOUS rule's `}`, which sits one line above the selector.
  const out = [];
  let d = 0, cur = "", segStart = 0, lead = 0;
  for (let k = 0; k < prelude.length; k++) {
    const ch = prelude[k];
    if (cur === "" && /\s/.test(ch)) { segStart = k + 1; continue; }
    if (ch === "(" || ch === "[" || ch === "{") d++;
    else if (ch === ")" || ch === "]" || ch === "}") d--;
    if (ch === "," && d === 0) {
      if (cur.trim()) out.push([cur.trim(), segStart]);
      cur = ""; segStart = k + 1; continue;
    }
    cur += ch;
  }
  if (cur.trim()) out.push([cur.trim(), segStart]);
  return out;
}
function parseDecls(body) {
  const out = {};
  body.split(";").forEach((d) => {
    const i = d.indexOf(":");
    if (i < 0) return;
    const prop = d.slice(0, i).trim();
    const val = d.slice(i + 1).replace(/!important/g, "").trim();
    if (prop && val && !prop.startsWith("@")) out[prop] = val;
  });
  return out;
}
function parseCss(file) {
  const raw = fs.readFileSync(file, "utf-8");
  const text = blankComments(raw);
  const rules = [];
  const walk = (from, to, media) => {
    let i = from, preludeStart = from;
    while (i < to) {
      const ch = text[i];
      if (ch === "{") {
        const rawPrelude = text.slice(preludeStart, i);
        const prelude = rawPrelude.trim();
        const preludeBase = preludeStart + (rawPrelude.length - rawPrelude.trimStart().length);
        let depth = 1, j = i + 1;
        while (j < to && depth > 0) { if (text[j] === "{") depth++; else if (text[j] === "}") depth--; j++; }
        const bodyEnd = j - 1;
        if (/^@(media|supports|layer|container)/.test(prelude)) {
          walk(i + 1, bodyEnd, prelude.replace(/\s+/g, " "));
        } else if (!prelude.startsWith("@")) {
          const body = text.slice(i + 1, bodyEnd);
          splitTopLevel(prelude).forEach(([sel, off]) => {
            if (!sel || sel.includes("{")) return;
            rules.push({ selector: sel.replace(/\s+/g, " ").trim(), file: path.basename(file),
              line: lineIndex(raw, preludeBase + off),
              media, decls: parseDecls(body) });
          });
        }
        i = bodyEnd + 1; preludeStart = i; continue;
      }
      if (ch === "}") { i++; preludeStart = i; continue; }
      i++;
    }
  };
  walk(0, text.length, null);
  return rules;
}

/* --------------------------- selector decomposition --------------------------- */
const STRIPPABLE = ["hover", "focus", "focus-visible", "focus-within", "active", "visited",
  "disabled", "enabled", "checked", "indeterminate", "valid", "invalid", "required", "optional",
  "read-only", "read-write", "placeholder-shown", "user-valid", "user-invalid", "default"];
const STRUCTURAL = [":first-child", ":last-child", ":nth-child", ":nth-of-type", ":only-child",
  ":empty", ":root", ":scope", ":only-of-type", ":nth-last-child"];
const STATE_PSEUDO = new RegExp(":(?:" + STRIPPABLE.join("|") + ")\\b");
const stripStates = (s) => {
  let x = s.replace(/::[a-z-]+(\([^)]*\))?/g, "");
  for (const n of STRIPPABLE) x = x.replace(new RegExp(":" + n + "(\\([^)]*\\))?", "g"), "");
  x = x.replace(/:not\([^()]*(?:\([^()]*\)[^()]*)*\)/g, "");
  return x.trim();
};
const splitCombinators = (s) => s.replace(/>|\+|~|\s+/g, "\u0001").split("\u0001").filter(Boolean);
function partsOf(sel) {
  const clean = stripStates(sel);
  const parts = splitCombinators(clean);
  const leaf = parts.length ? parts[parts.length - 1] : "";
  const ancestor = parts.length > 1 ? parts.slice(0, -1).join(" ") : null;
  return { leaf, ancestor };
}
function leafTokens(sel) {
  const { leaf } = partsOf(sel);
  const t = [];
  const idm = /#([A-Za-z0-9_-]+)/.exec(leaf);
  if (idm) t.push("#" + idm[1]);
  const cls = leaf.match(/\.([A-Za-z0-9_-]+)/g) || [];
  cls.forEach((c) => t.push(c));
  return t;
}


/* The drawer is opened through the DOM, not through a coordinate click: once it is up, its own
   backdrop intercepts a pointer click on the hamburger and Playwright waits forever.  This census
   needs the subtree mounted, not a hit-test proof (hit-testing is ORD-0419's job). */
async function openDrawer(page) {
  return page.evaluate(() => {
    const b = document.querySelector('[aria-controls="v8-nav-drawer"]');
    if (!b) return false;
    if (b.getAttribute("aria-expanded") !== "true") b.click();
    return true;
  });
}

const VISUAL = ["color", "background", "background-color", "background-image", "font-size",
  "font-weight", "display", "width", "height", "padding", "margin", "border", "border-radius",
  "opacity", "visibility", "gap", "position", "transform", "filter", "z-index", "flex",
  "grid-template-columns", "min-height", "max-height", "overflow", "text-align", "text-decoration",
  "box-shadow", "align-items", "justify-content", "flex-direction", "cursor", "line-height",
  "letter-spacing", "aspect-ratio", "object-fit", "content"];

(async () => {
  fs.mkdirSync(path.join(OUT, "shots"), { recursive: true });
  const cssFiles = ["src/styles.css", "src/design-tokens.css"].map((f) => path.join(SRC, f));
  const rules = [];
  cssFiles.forEach((f) => parseCss(f).forEach((r) => rules.push(r)));

  const uniq = [], uniqIndex = new Map(), leaf = [], anc = [];
  rules.forEach((r) => {
    if (uniqIndex.has(r.selector)) return;
    uniqIndex.set(r.selector, uniq.length);
    uniq.push(r.selector);
    const p = partsOf(r.selector);
    leaf.push(p.leaf);
    anc.push(p.ancestor);
  });

  // does any component actually emit the leaf's class/id?  scan frontend/src once, CSS excluded.
  const srcBlob = (() => {
    let acc = "";
    const walkDir = (d) => {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const f = path.join(d, e.name);
        if (e.isDirectory()) { if (e.name !== "node_modules") walkDir(f); continue; }
        if (/\.(tsx|ts|jsx|js|html)$/.test(e.name)) acc += fs.readFileSync(f, "utf-8") + "\n";
      }
    };
    walkDir(path.join(SRC, "src"));
    return acc;
  })();
  const tokenInSource = {};
  uniq.forEach((s) => {
    const ts = leafTokens(s);
    tokenInSource[s] = ts.length ? ts.map((t) => ({ token: t, present: srcBlob.includes(t.slice(1)) })) : null;
  });

  const shippedText = DIST_CSS && fs.existsSync(DIST_CSS) ? fs.readFileSync(DIST_CSS, "utf-8").replace(/\s+/g, "") : null;
  const shippedOf = {};
  uniq.forEach((s) => {
    if (shippedText === null) { shippedOf[s] = "NOT_CHECKED"; return; }
    shippedOf[s] = shippedText.includes(s.replace(/\s+/g, "")) ||
      shippedText.includes(s.replace(/\s+/g, "").replace(/>/g, ""));
  });

  const N = uniq.length;
  const maxExact = new Array(N).fill(0), maxAnc = new Array(N).fill(0), maxInside = new Array(N).fill(0);
  const screensZeroButContext = uniq.map(() => []);
  const errors = {};
  const sweepRows = [];
  const loadedCss = new Set();

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const pageErrors = [];

  const sweepOn = async (page, label, meta) => {
    const res = await page.evaluate((payload) => {
      const out = [];
      const { u, l, a } = payload;
      for (let i = 0; i < u.length; i++) {
        let e = -1, an = -1, ins = -1, err = null;
        try { e = document.querySelectorAll(u[i]).length; } catch (ex) { err = String(ex).slice(0, 60); }
        if (a[i]) { try { an = document.querySelectorAll(a[i]).length; } catch (ex) { an = -1; } }
        if (an > 0 && l[i]) {
          ins = 0;
          try {
            for (const host of Array.from(document.querySelectorAll(a[i])).slice(0, 40)) {
              ins += host.querySelectorAll(l[i]).length;
            }
          } catch (ex) { ins = -1; }
        }
        out.push([e, an, ins, err]);
      }
      return out;
    }, { u: uniq, l: leaf, a: anc });
    res.forEach((row, i) => {
      const [e, an, ins, err] = row;
      if (err) errors[uniq[i]] = err;
      if (e > maxExact[i]) maxExact[i] = e;
      if (an > maxAnc[i]) maxAnc[i] = an;
      if (ins > maxInside[i]) maxInside[i] = ins;
      if (e === 0 && ins > 0) {
        if (!screensZeroButContext[i].includes(label)) screensZeroButContext[i].push(label);
      }
    });
    const css = await page.evaluate(() => performance.getEntriesByType("resource")
      .map((x) => x.name).filter((n) => n.endsWith(".css")).map((n) => n.split("/").pop()));
    css.forEach((c) => loadedCss.add(c));
    sweepRows.push({ ...meta, label, nonzero_exact: res.filter((r) => r[0] > 0).length,
      zero_exact: res.filter((r) => r[0] === 0).length, rejected: res.filter((r) => r[3]).length, css });
    console.log(label, "nonzero_exact", res.filter((r) => r[0] > 0).length, "/", N);
  };
  const a_no_context = (i) => anc[i] === null;
  const maxLeaf = (i) => maxInside[i];

  /* leaf-only counting for context-free selectors happens in a second evaluate pass below */
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
      const meta = { locale, shape: `${shape.width}x${shape.height}` };
      for (const route of ROUTES) {
        await page.goto(`${BASE.replace(/\/$/, "")}/v8/${route}`, { waitUntil: "load", timeout: 90000 });
        await page.waitForTimeout(2500);
        await sweepOn(page, `${locale}/${shape.width}x${shape.height}/${route}`, meta);
        const opened = await openDrawer(page);
        if (opened) {
          await page.waitForTimeout(1000);
          await sweepOn(page, `${locale}/${shape.width}x${shape.height}/${route}+drawer`, meta);
          if (route === "hub" && shape.width === 390) {
            await page.locator("#v8-nav-drawer").screenshot({
              path: path.join(OUT, "shots", `drawer_${locale}_390.png`) }).catch(() => {});
          }
        }
      }
      await ctx.close();
    }
  }

  /* ---- probe the candidates: context mounted, full selector never matched ---- */
  const cand = [];
  for (let i = 0; i < N; i++) {
    if (maxExact[i] !== 0 || errors[uniq[i]]) continue;
    // only a selector that HAS an ancestor context can be proven dead by this discriminator:
    // context mounted + leaf present under it + the full selector still matching nothing.
    // A single-compound selector gets judged by its token, not by a probe that could find the
    // same tag anywhere on the page (that was r2's false-positive engine).
    if (anc[i] && maxAnc[i] > 0 && maxInside[i] > 0) cand.push(i);
  }

  const pctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const ppage = await pctx.newPage();
  ppage.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  await ppage.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  const sealP = ppage.getByText("使用封存的演示行程", { exact: false }).first();
  if (await sealP.count()) { await sealP.click(); await ppage.waitForTimeout(4000); }
  let onScreen = null;
  const gotoScreen = async (label) => {
    const route = label.split("/").pop().replace("+drawer", "");
    if (route !== onScreen) {
      await ppage.goto(`${BASE.replace(/\/$/, "")}/v8/${route}`, { waitUntil: "load", timeout: 90000 });
      await ppage.waitForTimeout(2500);
      onScreen = route;
    }
    if (label.includes("+drawer")) { await openDrawer(ppage); await ppage.waitForTimeout(1000); }
  };

  const probes = {};
  for (const i of cand) {
    const sel = uniq[i];
    const props = Object.keys(rules.find((r) => r.selector === sel).decls).filter((k) => VISUAL.includes(k)).slice(0, 10);
    const where = screensZeroButContext[i][0] || "hub";
    await gotoScreen(where);
    probes[i] = await ppage.evaluate(({ sel, anc, leaf, props }) => {
      const full = document.querySelectorAll(sel).length;
      let hosts = [];
      try { hosts = anc ? Array.from(document.querySelectorAll(anc)) : Array.from(document.body.children); } catch (e) { return { error: String(e).slice(0, 60) }; }
      const contextSet = new Set(hosts);
      const found = [];
      for (const h of hosts.slice(0, 60)) {
        for (const el of Array.from(h.querySelectorAll(leaf || "*"))) {
          found.push(el);
          if (found.length >= 24) break;
        }
        if (found.length >= 24) break;
      }
      if (!found.length) return { full, hosts: hosts.length, found: 0, samples: [] };
      const samples = found.slice(0, 24).map((target) => {
        const cs = getComputedStyle(target);
        const b = target.getBoundingClientRect();
        const computed = {};
        props.forEach((p) => (computed[p] = cs.getPropertyValue(p)));
        const pt = target.parentElement;
        return { tag: target.tagName.toLowerCase(), classes: String(target.className || "").slice(0, 90),
          text: (target.textContent || "").trim().slice(0, 40),
          rect: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)],
          inViewport: b.width > 0 && b.height > 0 && b.top < innerHeight && b.bottom > 0,
          parentTag: pt ? pt.tagName.toLowerCase() : null,
          parentIsContext: !!pt && contextSet.has(pt),
          hasIconChild: !!target.querySelector("svg"),
          computed };
      });
      // the defect shape is a leaf that IS under the context but NOT a direct child of it
      // representative = a wrapped leaf that carries an icon, i.e. one of the nav rows themselves,
      // not the drawer's own close button which is styled by .v8-quiet-button on purpose.
      const wrapped = samples.filter((s) => !s.parentIsContext && s.parentTag);
      const rows = wrapped.filter((s) => s.hasIconChild);
      return { full, hosts: hosts.length, found: found.length, samples,
        wrapped_count: wrapped.length,
        distinct_signatures: Array.from(new Set(samples.map((s) => JSON.stringify(s.computed)))).length,
        first_wrapped: rows[0] || wrapped[0] || null,
        wrapped_row_like: rows.length, first_direct: samples.find((s) => s.parentIsContext) || null };
    }, { sel, anc: anc[i], leaf: leaf[i], props });
  }
  await browser.close();

  /* ---- classify every zero-exact selector ---- */
  const rowsOut = [];
  for (let i = 0; i < N; i++) {
    const sel = uniq[i];
    if (maxExact[i] > 0) continue;
    const owning = rules.filter((r) => r.selector === sel);
    const decls = owning[0].decls;
    const sig = Object.keys(decls).filter((k) => VISUAL.includes(k));
    const pr = probes[i] || {};
    const ts = tokenInSource[sel];
    const tokensMissing = ts ? ts.filter((t) => !t.present).map((t) => t.token) : [];
    const cls = (() => {
      if (errors[sel]) return "NOT_SURE_INSTRUMENT_REJECTED";
      if (shippedOf[sel] === false) return "NOT_SURE_NOT_IN_LOADED_CSS";
      if (/::[a-z-]+/.test(sel)) return "STATEFUL_NOT_DEAD";
      if (tokensMissing.length) return "DEAD_RULE_NO_CONSUMER";
      if (STATE_PSEUDO.test(sel) || STRUCTURAL.some((s) => sel.includes(s))) return "STATEFUL_NOT_DEAD";
      if (pr.found > 0 && pr.full === 0) return "DEAD_RULE_TARGET_PRESENT";
      if (anc[i] && maxAnc[i] === 0) return "NOT_SURE_CONTEXT_NOT_MOUNTED";
      return "NOT_SURE_LEAF_NOT_FOUND";
    })();
    const visible = (pr.first_wrapped || pr.samples?.[0])?.inViewport ? 3 : 0;
    const rank = ({ DEAD_RULE_TARGET_PRESENT: 100, DEAD_RULE_NO_CONSUMER: 40 })[cls] || 0;
    const showTarget = pr.first_wrapped || (pr.samples && pr.samples[0]) || null;
    rowsOut.push({
      selector: sel, source: owning.map((r) => `${r.file}:${r.line}`),
      media: owning.map((r) => r.media).filter(Boolean)[0] || null,
      shipped_in_loaded_css: shippedOf[sel],
      exact_hits_max: 0, context: anc[i], context_hits_max: anc[i] ? maxAnc[i] : "n/a (no ancestor)",
      leaf: leaf[i], leaf_under_context_max: maxInside[i],
      leaf_tokens_absent_from_source: tokensMissing,
      screens_where_context_mounted_but_rule_matched_nothing: screensZeroButContext[i].slice(0, 8),
      class: cls, why: (cls === "DEAD_RULE_TARGET_PRESENT"
        ? `上下文在屏上（${pr.hosts} 枚）、叶子在其内确实存在（探到 ${pr.found} 枚，其中 ${pr.wrapped_count} 枚并不是它的直接子级），完整选择器仍 0 命中`
        : cls === "DEAD_RULE_NO_CONSUMER" ? `叶子类名/id 在 frontend/src 的 ts/tsx/html 里一次都没出现：${tokensMissing.join(", ")}`
        : ""),
      target_probe: showTarget ? { tag: showTarget.tag, classes: showTarget.classes, text: showTarget.text,
        rect: showTarget.rect, in_viewport: showTarget.inViewport, parent_tag: showTarget.parentTag,
        parent_is_the_context: showTarget.parentIsContext, leaves_found: pr.found,
        leaves_not_direct_child: pr.wrapped_count ?? null, distinct_computed_signatures: pr.distinct_signatures ?? null } : null,
      rule_sets: Object.fromEntries(sig.map((k) => [k, decls[k]]).filter((x) => x[1] !== "")),
      computed_of_target: (showTarget && showTarget.computed) || null,
      visual_props: sig, rank: rank + visible + (sig.length ? 2 : 0),
    });
  }
  rowsOut.sort((a, b) => b.rank - a.rank || a.selector.localeCompare(b.selector));
  const classCounts = rowsOut.reduce((a, r) => (a[r.class] = (a[r.class] || 0) + 1, a), {});

  const receipt = {
    at: new Date().toISOString(), base: BASE, served_tip: "8a7665be2061a2f38aa2227f81c57003ca4caacb",
    css_assets_loaded: Array.from(loadedCss), dist_css: DIST_CSS,
    rules_parsed: rules.length, unique_selectors: N,
    rules_by_file: cssFiles.map((f) => ({ file: path.basename(f), rules: rules.filter((r) => r.file === path.basename(f)).length })),
    scenarios: { locales: LOCALES, shapes: SHAPES.map((s) => `${s.width}x${s.height}`), routes: ROUTES, drawer_open_swept: true },
    sweeps: sweepRows.length, sweep_rows: sweepRows,
    zero_exact: rowsOut.length, class_counts: classCounts,
    dead_rules_target_present: rowsOut.filter((r) => r.class === "DEAD_RULE_TARGET_PRESENT"),
    dead_rules_no_consumer: rowsOut.filter((r) => r.class === "DEAD_RULE_NO_CONSUMER").length,
    stateful_not_dead: rowsOut.filter((r) => r.class === "STATEFUL_NOT_DEAD").length,
    not_sure_total: rowsOut.filter((r) => r.class.startsWith("NOT_SURE")).length,
    all_zero_rows: rowsOut, pageerrors: pageErrors,
  };
  fs.writeFileSync(path.join(OUT, "census_r3.json"), JSON.stringify(receipt, null, 1), "utf-8");
  console.log("=== SUMMARY ===");
  console.log(JSON.stringify({ rules: rules.length, unique: N, zero_exact: rowsOut.length,
    class_counts: classCounts, sweeps: sweepRows.length }, null, 1));
  receipt.dead_rules_target_present.slice(0, 25).forEach((d) => console.log(
    "DEAD", d.source.join("|"), JSON.stringify(d.selector), "ctx=" + d.context,
    "ctxHits=" + d.context_hits_max, "leafUnderCtx=" + d.leaf_under_context_max,
    JSON.stringify(d.target_probe || {}).slice(0, 120)));
})().catch((e) => { console.log("FATAL", String(e).slice(0, 500)); process.exit(9); });
