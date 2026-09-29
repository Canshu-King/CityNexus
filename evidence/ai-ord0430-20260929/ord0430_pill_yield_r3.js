// ORD-0430 round 3 -- the two-direction ruler for "yield by relocating".
//
// Commander criterion (ledger CMDR 03:31, section 3), taken literally:
//   (a) covering_arms must reach zero, and
//   (b) the hit test at the centre of the relocated pill's VISIBLE rectangle must come back
//       on the pill itself, and panel_opened must recover to every arm.
// Hiding is not allowed as the means, so this ruler also records, per rest, whether the dock is
// present, opaque, pointer-reactive and inside the viewport -- four independent witnesses that
// the control is still there.
//
// Both text measures are reported and neither is dropped: `box` = the readable element's border
// box, `ink` = Range.getClientRects() of the glyphs. They disagree because a block-level heading
// spans the content column, so an empty line-end still counts under `box`.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4826";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0430_r3_readings";
const ARM = process.argv[4] || "after";

const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];
const SCREENS = (process.env.SCREENS_CSV || "twin,discover,intelligence").split(",");
const READABLE = "h1,h2,h3,h4,h5,p,li,dt,dd,th,td,label,figcaption,summary";
const ACTIONABLE = 'button, a[href], input, select, textarea, [role="button"]';

const PROBE = async (cfg) => {
  const dock = document.querySelector('[data-testid="v18-copilot-dock"]');
  const vh = window.innerHeight;
  const nav = document.querySelector(".v8-mobile-nav");
  const out = {
    path: location.pathname,
    pill_present: !!dock,
    served_bundle: Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src")).filter(Boolean),
    viewport: { w: window.innerWidth, h: vh },
    nav: nav ? { top: Math.round(nav.getBoundingClientRect().top), bottom: Math.round(nav.getBoundingClientRect().bottom) } : null,
    horizontal_overflow: {
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      overflow_gt: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    },
    rests: [],
  };
  if (!dock) return out;
  const readAttrs = () => ({
    yield_to_surface: dock.getAttribute("data-yield-to-surface"),
    rest_overlap: dock.getAttribute("data-rest-overlap"),
    idle_compact: dock.getAttribute("data-idle-compact"),
    yield_slot: dock.getAttribute("data-yield-slot"),
    classes: String(dock.className),
  });
  const painted = () => {
    const r = dock.getBoundingClientRect();
    return { left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height) };
  };
  const inkRects = (sel) => {
    const acc = [];
    document.querySelectorAll(sel).forEach((el) => {
      if (dock.contains(el) || el.contains(node_is_dock_parent(el))) return;
      const rg = document.createRange();
      rg.selectNodeContents(el);
      Array.from(rg.getClientRects()).forEach((r) => {
        if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < vh) acc.push({ tag: el.tagName, text: (el.textContent || "").trim().slice(0, 50), left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) });
      });
    });
    return acc;
  };
  // a node that contains the dock is the scroll shell; skip it or everything looks covered
  function node_is_dock_parent(el) {
    return el === dock ? el : (el.getBoundingClientRect().width >= window.innerWidth && el.contains(dock) ? el : null);
  }
  const boxRects = (sel) => {
    const acc = [];
    document.querySelectorAll(sel).forEach((el) => {
      if (dock.contains(el) || el.contains(dock)) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.bottom < 0 || r.top > vh) return;
      acc.push({ tag: el.tagName, text: (el.textContent || "").trim().slice(0, 50), left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) });
    });
    return acc;
  };
  const px = (a, b) => {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return w > 1 && h > 1 ? Math.round(w * h) : 0;
  };

  const scroller = document.scrollingElement || document.documentElement;
  const max = scroller.scrollHeight - scroller.clientHeight;
  const stops = Array.from(new Set([0, Math.round(max / 2), max]));
  for (const target of stops) {
    scroller.scrollTop = target;
    // let the dock's settled-scroll measurement (220 ms debounce) plus the 140 ms move finish;
    // a busy wait would block the very timer and paint frames the relocation needs
    await new Promise((res) => window.setTimeout(res, 900));
    const p = painted();
    const a = readAttrs();
    const ink = inkRects(cfg.READABLE);
    const box = boxRects(cfg.READABLE);
    const ctl = boxRects(cfg.ACTIONABLE);
    const inkHits = ink.filter((r) => px(r, p) > 0);
    const boxHits = box.filter((r) => px(r, p) > 0);
    const ctlHits = ctl.filter((r) => px(r, p) > 0);
    const cx = Math.round((p.left + p.right) / 2);
    const cy = Math.round((p.top + p.bottom) / 2);
    const at = document.elementFromPoint(cx, cy);
    const cs = getComputedStyle(dock);
    out.rests.push({
      scrollTop: Math.round(scroller.scrollTop),
      painted: p,
      attrs: a,
      ink_covered: inkHits.length,
      box_covered: boxHits.length,
      controls_covered: ctlHits.length,
      max_ink_overlap_px: inkHits.reduce((m, r) => Math.max(m, px(r, p)), 0),
      max_box_overlap_px: boxHits.reduce((m, r) => Math.max(m, px(r, p)), 0),
      first_ink_covered: inkHits.length ? inkHits[0].tag + " " + inkHits[0].text : null,
      first_box_covered: boxHits.length ? boxHits[0].tag + " " + boxHits[0].text : null,
      hit_at_centre: at ? at.tagName + "." + String(at.className || "").slice(0, 18) : "none",
      hit_is_pill: !!(at && dock.contains(at)),
      visible_witnesses: {
        in_viewport: p.left >= 0 && p.top >= 0 && p.right <= window.innerWidth && p.bottom <= vh,
        opacity: cs.opacity,
        visibility: cs.visibility,
        pointer_events: cs.pointerEvents,
        transform: cs.transform === "none" ? "none" : "matrix",
        painted_nonzero: p.w > 0 && p.h > 0,
      },
    });
  }
  scroller.scrollTop = 0;
  return out;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rep = { base: BASE, arm: ARM, criterion: "covering reaches zero AND relocated centre hit returns the pill AND panel opens on every arm", screens: [] };
  for (const screen of SCREENS) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    const r = { screen, locales: {} };
    for (const locale of ["zh-CN", "en"]) {
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      await page.evaluate((l) => localStorage.setItem("citynexus.locale", l), locale);
      await page.goto(BASE + "/v8/" + screen, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      for (const label of ENTRY) {
        const loc = page.getByText(label, { exact: false }).first();
        if (await loc.count()) { await loc.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(2000); break; }
      }
      await page.goto(BASE + "/v8/" + screen, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      await page.waitForTimeout(2600);
      const probe = await page.evaluate(PROBE, { READABLE, ACTIONABLE });
      // reachability: click the centre of whatever the pill is now painted as, then look for the panel
      const last = probe.rests[probe.rests.length - 1] || null;
      let clickUsed = null;
      if (last) {
        const c = { x: Math.round((last.painted.left + last.painted.right) / 2), y: Math.round((last.painted.top + last.painted.bottom) / 2) };
        clickUsed = c;
        await page.mouse.click(c.x, c.y);
        await page.waitForTimeout(1200);
      }
      probe.reachability = {
        click_used: clickUsed,
        panel_opened: (await page.locator(".cn-copilot-panel").count()) > 0,
      };
      r.locales[locale] = probe;
    }
    rep.screens.push(r);
    await ctx.close();
  }
  await browser.close();
  const file = OUT + "/pill_yield_" + ARM + "_r3.json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const s of rep.screens) {
    for (const loc of Object.keys(s.locales)) {
      const p = s.locales[loc];
      const rs = p.rests || [];
      const ink = rs.filter((x) => x.ink_covered > 0).length;
      const box = rs.filter((x) => x.box_covered > 0).length;
      const hit = rs.filter((x) => x.hit_is_pill).length;
      const free = rs.filter((x) => x.visible_witnesses.in_viewport && x.visible_witnesses.opacity === "1" && x.visible_witnesses.visibility === "visible" && x.visible_witnesses.pointer_events !== "none" && x.visible_witnesses.painted_nonzero).length;
      console.log(`${s.screen}/${loc} bundle=${(p.served_bundle || [])[0]} rests=${rs.length}` +
        ` ink_covering=${ink} box_covering=${box} centre_hit_pill=${hit} fully_visible=${free}` +
        ` max_ink=${rs.reduce((m, x) => Math.max(m, x.max_ink_overlap_px), 0)}` +
        ` opened=${p.reachability && p.reachability.panel_opened}` +
        ` slot=${rs.length ? rs[0].attrs.yield_slot : "?"}`);
      if (ink) console.log(`   still covering ink: ${JSON.stringify(rs.filter((x) => x.ink_covered > 0).map((x) => [x.scrollTop, x.painted, x.first_ink_covered]))}`.slice(0, 260));
    }
  }
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
