/**
 * ORD-0401 instrument -- is the pre-trip checklist's empty state reachable inside the first screen?
 *
 * The order's whole acceptance is a reachability claim, and this project has already been fooled by
 * one (ORD-0400: a drawer entry that was "clickable on my desktop" while it sat outside the viewport
 * on a phone).  So nothing here is inferred from CSS or from a `scrolled > 0` counter.  Each arm
 * reports:
 *   - the block stack above the panel, measured (which screen real estate is consumed before it),
 *   - the action's own box, its centre, and `document.elementFromPoint` at that centre,
 *   - `scrollable_ancestors` -- every ancestor that can scroll, and whether the scroll that
 *     eventually reveals the control is a *document* scroll or a *container* scroll,
 *   - two hit-tests, one before any scrolling and one after, because the acceptance requires both.
 *
 * Zero writes: the sealed-demo entry is a GET of /api/v1/demo/scene plus the ordinary screen reads
 * (`V8Experience.tsx:873`, ORD-0209 removed the POST path), and the two mutating legs are withheld
 * in the browser anyway.  Traffic is counted so the artifact disproves a write rather than asserting
 * it did not happen.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4781";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
const WIDTHS = (process.env.ORD0401_WIDTHS ?? "390").split(",").map(Number);
const TAG = process.env.ORD0401_TAG ?? "arm";
const HEIGHT = Number(process.env.ORD0401_HEIGHT ?? 844);
mkdirSync(OUT, { recursive: true });

const LOCALES = (process.env.ORD0401_LOCALES ?? "zh-CN,en-US").split(",");

const MEASURE = () => {
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      x: Math.round(r.x),
      y: Math.round(r.y),
      w: Math.round(r.width),
      h: Math.round(r.height),
      bottom: Math.round(r.bottom),
      display: cs.display,
      text: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 120),
      text_chars: (el.innerText || "").replace(/\s+/g, " ").trim().length,
    };
  };
  const describe = (el) =>
    el === null
      ? null
      : {
          tag: el.tagName.toLowerCase(),
          class: (typeof el.className === "string" ? el.className : "").slice(0, 90),
          testid: el.getAttribute?.("data-testid"),
          text: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 60),
        };

  const panel = document.querySelector('[data-testid="pretrip-checklist"]');
  const action = document.querySelector('[data-testid="pretrip-empty-action"]');
  const empty = document.querySelector('[data-testid="pretrip-empty"]');
  const items = document.querySelectorAll('[data-testid="pretrip-item"]');
  const band = document.querySelector('[data-testid="today-attention"]');
  const bandSection = band?.closest("section") ?? null;

  // Which scroller actually owns this page?  Walk every ancestor of the action and ask it.
  const scrollable = [];
  for (let el = action; el; el = el.parentElement) {
    const cs = getComputedStyle(el);
    const overflowY = cs.overflowY;
    const canScroll =
      el.scrollHeight - el.clientHeight > 1 && ["auto", "scroll"].includes(overflowY);
    if (canScroll) {
      scrollable.push({
        tag: el.tagName.toLowerCase(),
        class: (typeof el.className === "string" ? el.className : "").slice(0, 70),
        testid: el.getAttribute?.("data-testid"),
        overflow_y: overflowY,
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
        scrollable_overflow_px: el.scrollHeight - el.clientHeight,
        scroll_top: el.scrollTop,
      });
    }
  }

  const se = document.scrollingElement ?? document.documentElement;

  // The block stack, from the panel's own container upwards: whoever eats the first screen is
  // named here, block by block, in the order the DOM puts them on screen.
  const stack = [];
  let container = panel?.parentElement ?? null;
  while (container && container.querySelectorAll("[data-testid]").length < 3) container = container.parentElement;
  if (container) {
    for (const child of container.children) {
      const r = child.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      stack.push({
        class: (typeof child.className === "string" ? child.className : "").slice(0, 70),
        testid: child.querySelector?.("[data-testid]")?.getAttribute("data-testid") ?? null,
        child_index: Array.from(container.children).indexOf(child),
        y: Math.round(r.y + window.scrollY),
        h: Math.round(r.height),
        text: (child.innerText || "").replace(/\s+/g, " ").trim().slice(0, 60),
      });
    }
  }

  const centre = action
    ? { cx: Math.round(action.getBoundingClientRect().x + action.getBoundingClientRect().width / 2),
        cy: Math.round(action.getBoundingClientRect().y + action.getBoundingClientRect().height / 2) }
    : null;
  const hit = centre ? describe(document.elementFromPoint(centre.cx, centre.cy)) : null;

  const bandKicker = bandSection?.querySelector(".v8-kicker");

  return {
    document_scroll_height: se.scrollHeight,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scroll_position: { doc_top: se.scrollTop, body_top: document.body.scrollTop },
    panel: box(panel),
    panel_data_count: panel?.getAttribute("data-count") ?? null,
    panel_note: box(panel?.querySelector(".cn-pretrip-note") ?? null),
    panel_head_h2: box(panel?.querySelector("h2") ?? null),
    empty_row: box(empty),
    action: box(action),
    action_centre: centre,
    action_in_viewport: centre
      ? centre.cy >= 0 && centre.cy <= window.innerHeight &&
        centre.cx >= 0 && centre.cx <= window.innerWidth
      : null,
    // Positive number = how far below the fold the action's *centre* sits.
    action_px_below_fold: centre ? Math.max(0, centre.cy - window.innerHeight) : null,
    action_px_below_fold_by_bottom: action
      ? Math.max(0, Math.round(action.getBoundingClientRect().bottom) - window.innerHeight)
      : null,
    hit_test_before_scroll: hit,
    hit_test_matches_action: hit ? hit.tag === action.tagName.toLowerCase() : null,
    scrollable_ancestors: scrollable,
    scroll_kind: scrollable.length === 0 ? "document" : "container",
    container_stack: stack,
    stack_container: container
      ? {
          tag: container.tagName.toLowerCase(),
          class: (typeof container.className === "string" ? container.className : "").slice(0, 70),
          testid: container.getAttribute?.("data-testid") ?? null,
        }
      : null,
    attention_band: box(band),
    attention_band_state: band?.parentElement?.getAttribute("data-attention") ?? null,
    attention_band_kicker: bandKicker
      ? { display: getComputedStyle(bandKicker).display, text: bandKicker.innerText.trim() }
      : null,
    // DOM order is the position argument ORD-0384 is made of -- index within the shared container.
    dom_order: {
      attention_band: bandSection ? Array.from(container?.children ?? []).indexOf(bandSection) : null,
      panel: container ? Array.from(container.children).indexOf(panel) : null,
    },
    items_rendered: items.length,
  };
};

const browser = await chromium.launch();
const report = { base: BASE, tag: TAG, widths: WIDTHS, viewport_height: HEIGHT, arms: [] };

for (const locale of LOCALES) {
 for (const WIDTH of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width: WIDTH, height: HEIGHT } });
  const page = await ctx.newPage();
  const traffic = { reads: 0, writes: 0, write_urls: [] };
  page.on("request", (req) => {
    const url = req.url();
    if (!url.includes("/api/")) return;
    const method = req.method();
    if (method === "GET" || method === "HEAD") traffic.reads += 1;
    else {
      traffic.writes += 1;
      traffic.write_urls.push(`${method} ${url.replace(/^https?:\/\//, "")}`);
    }
  });
  // Belt and braces: no mutating leg may leave the browser at all.
  await page.route(
    (url) => url.pathname.startsWith("/api/") && url.protocol !== "blob:",
    async (route) => {
      if (route.request().method() !== "GET") {
        await route.fulfill({ status: 405, contentType: "application/json", body: '{"detail":"probe-withheld"}' });
        return;
      }
      await route.continue();
    },
  );
  await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);

  await page.goto(`${BASE}/v8`, { waitUntil: "load" });
  await page.waitForTimeout(1500);
  const demo = page.getByTestId("trial-tianjin-demo");
  if (await demo.count()) {
    await demo.click();
    await page
      .waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 })
      .catch(() => {});
  }
  await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
  await page.waitForTimeout(2500);

  // Which generation is this?  Read it off the browser's own resource entries, never from a
  // hard-coded asset name that would survive a generation swap and lie about what was measured.
  const generation = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((e) => e.name)
      .filter((n) => /\/assets\/index-.*\.js$/.test(n))
      .map((n) => n.split("/").pop()),
  );

  const before = await page.evaluate(MEASURE);
  await page.screenshot({ path: `${OUT}/${TAG}-${locale.replace("-", "_")}-${WIDTH}px-before-scroll.png` });

  // Second arm: scroll exactly as far as it takes to bring the control's centre on screen, and
  // record *which* scroller moved.  An arm that reports a hit after scrolling by an unknown
  // mechanism is the thing ORD-0400 was closed for.
  const scrollArm = await page.evaluate(() => {
    const action = document.querySelector('[data-testid="pretrip-empty-action"]');
    if (!action) return { scrolled: null, reason: "no action" };
    const before = {
      doc: document.scrollingElement.scrollTop,
      containers: [...document.querySelectorAll("*")]
        .filter((el) => el.scrollHeight - el.clientHeight > 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowY))
        .map((el) => ({
          cls: (el.className || "").toString().slice(0, 50),
          top: el.scrollTop,
        })),
    };
    action.scrollIntoView({ block: "center" });
    const after = {
      doc: document.scrollingElement.scrollTop,
      containers: [...document.querySelectorAll("*")]
        .filter((el) => el.scrollHeight - el.clientHeight > 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowY))
        .map((el) => ({
          cls: (el.className || "").toString().slice(0, 50),
          top: el.scrollTop,
        })),
    };
    return { before, after };
  });
  await page.waitForTimeout(400);
  const after = await page.evaluate(MEASURE);
  await page.screenshot({ path: `${OUT}/${TAG}-${locale.replace("-", "_")}-${WIDTH}px-after-scroll.png` });

  const docMoved =
    (scrollArm.after?.doc ?? 0) - (scrollArm.before?.doc ?? 0);
  const containerMoves = (scrollArm.after?.containers ?? []).map((a, i) => ({
    cls: a.cls,
    moved: a.top - (scrollArm.before?.containers?.[i]?.top ?? 0),
  })).filter((m) => m.moved !== 0);

  report.arms.push({
    locale,
    generation_assets: generation,
    api_traffic: traffic,
    before_scroll: before,
    scroll_arm: scrollArm,
    scroll_arm_verdict: {
      document_scroll_px: docMoved,
      container_scroll: containerMoves,
      scroll_kind: docMoved > 0 && containerMoves.length === 0 ? "document" : containerMoves.length ? "container" : "none",
    },
    after_scroll: after,
    verdict: {
      reachable_in_first_screen: before.action_in_viewport,
      hit_test_before: before.hit_test_matches_action,
      hit_test_after: after.hit_test_matches_action,
    },
  });
  await ctx.close();
 }
}

await browser.close();
writeFileSync(`${OUT}/hub_reachability_${TAG}.json`, JSON.stringify(report, null, 2));
const summary = report.arms.map((a) => ({
  locale: a.locale,
  generation: a.generation_assets,
  writes: a.api_traffic.writes,
  count: a.before_scroll.panel_data_count,
  action_y: a.before_scroll.action?.y,
  centre: a.before_scroll.action_centre?.cy,
  in_viewport: a.before_scroll.action_in_viewport,
  px_below_fold_centre: a.before_scroll.action_px_below_fold,
  px_below_fold_bottom: a.before_scroll.action_px_below_fold_by_bottom,
  doc_height: a.before_scroll.document_scroll_height,
  scrollable_ancestors: a.before_scroll.scrollable_ancestors.length,
  scroll_kind: a.before_scroll.scroll_kind,
  hit_before: a.before_scroll.hit_test_matches_action,
  hit_after: a.after_scroll.hit_test_matches_action,
  scroll_document_px: a.scroll_arm_verdict.document_scroll_px,
}));
console.log(JSON.stringify(summary, null, 2));
