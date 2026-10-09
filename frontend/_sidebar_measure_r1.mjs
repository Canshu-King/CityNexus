// Sidebar instrument: drives a real Chromium against a running dev server and
// measures collapse motion, icon boxes, drawer motion and scroll behaviour.
// Every verdict is computed from sampled frames, never written as a literal.
import { chromium } from "playwright";
import { writeFileSync } from "node:fs";

const URL_BASE = process.argv[2] ?? "http://localhost:5611";
const JOURNEY =
  process.argv[3] ?? "d13611bd-8c60-4c76-b1ef-200e2e2aff23";
const OUT = process.argv[4] ?? "_sidebar_measure_r1.json";

const wait = async (fn, ms, step = 120) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await fn()) return true;
    await new Promise((r) => setTimeout(r, step));
  }
  return false;
};

const browser = await chromium.launch();
const results = {};

async function newPage(contextOpts) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ...contextOpts,
  });
  await ctx.addInitScript((jid) => {
    localStorage.setItem("citynexus.v8.journey_id", jid);
    localStorage.removeItem("citynexus.v8.sidebar_collapsed");
  }, JOURNEY);
  const page = await ctx.newPage();
  await page.goto(`${URL_BASE}/v8/hub`, { waitUntil: "domcontentloaded" });
  const ok = await wait(
    () => page.locator(".v8-product-shell").count().then((n) => n > 0),
    15000,
  );
  if (!ok) throw new Error("product shell never appeared");
  return { ctx, page };
}

/* ── A. desktop collapse ─────────────────────────────────────────────── */
{
  const { ctx, page } = await newPage();
  const before = await page.evaluate(() => {
    const sb = document.querySelector(".v8-sidebar");
    return {
      width: +sb.getBoundingClientRect().width.toFixed(1),
      toggle_present: Boolean(document.querySelector(".v8-sidebar-toggle")),
      collapsed_attr: sb.getAttribute("data-collapsed"),
    };
  });

  // Sample the collapse over a fixed *time* window, not a fixed frame count:
  // 14 frames at whatever rate the machine happens to hit can straddle the whole
  // 220ms transition and read a single value, which is an instrument fault, not a
  // product one. 700ms covers the transition plus slack.
  const track = await page.evaluate(async () => {
    const sb = document.querySelector(".v8-sidebar");
    const toggle = document.querySelector(".v8-sidebar-toggle");
    if (!toggle) return { frames: [], no_toggle: true };
    toggle.click();
    const frames = [];
    const t0 = performance.now();
    while (performance.now() - t0 < 700) {
      await new Promise((r) => requestAnimationFrame(r));
      frames.push(+sb.getBoundingClientRect().width.toFixed(1));
    }
    return { frames, no_toggle: false };
  });
  const widthTrack = track.frames;
  await page.waitForTimeout(400);

  const after = await page.evaluate(() => {
    const sb = document.querySelector(".v8-sidebar");
    const btn = sb.querySelector(".v8-nav button");
    const svg = btn.querySelector("svg");
    const span = btn.querySelector("span");
    const sb_r = sb.getBoundingClientRect();
    const svg_r = svg.getBoundingClientRect();
    return {
      width: +sb_r.width.toFixed(1),
      collapsed_attr: sb.getAttribute("data-collapsed"),
      persisted: localStorage.getItem("citynexus.v8.sidebar_collapsed"),
      icon_w: +svg_r.width.toFixed(1),
      icon_h: +svg_r.height.toFixed(1),
      icon_offset_from_button_center_x: +(
        (svg_r.left + svg_r.right) / 2 -
        (btn.getBoundingClientRect().left + btn.getBoundingClientRect().right) / 2
      ).toFixed(2),
      label_opacity: getComputedStyle(span).opacity,
      nav_icons: [...sb.querySelectorAll(".v8-nav button svg")].map((s) => {
        const b = s.getBoundingClientRect();
        return { w: +b.width.toFixed(1), h: +b.height.toFixed(1) };
      }),
      sidebar_overflow_y: getComputedStyle(sb).overflowY,
    };
  });

  // While collapsed, nothing inside the rail may stick out of it.
  const clipped = await page.evaluate(() => {
    const sb = document.querySelector(".v8-sidebar");
    const sr = sb.getBoundingClientRect();
    const bad = [];
    let raw_outside = 0;
    for (const el of sb.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      if (r.left >= sr.left - 0.6 && r.right <= sr.right + 0.6) continue;
      // Only the *visible* rectangle can stick out: intersect the element box
      // with every ancestor that clips horizontally.
      let left = r.left;
      let right = r.right;
      for (let a = el.parentElement; a && sb.contains(a); a = a.parentElement) {
        const ov = getComputedStyle(a).overflowX;
        if (ov === "hidden" || ov === "clip") {
          const ar = a.getBoundingClientRect();
          left = Math.max(left, ar.left);
          right = Math.min(right, ar.right);
        }
      }
      raw_outside++;
      if (right - left > 0.6 && (left < sr.left - 0.6 || right > sr.right + 0.6)) {
        bad.push({
          cls: String(el.className || el.tagName),
          parent: String(
            el.parentElement
              ? el.parentElement.className || el.parentElement.tagName
              : "",
          ),
          visible_left: +left.toFixed(1),
          visible_right: +right.toFixed(1),
          raw_left: +r.left.toFixed(1),
          raw_right: +r.right.toFixed(1),
        });
      }
    }
    const user = sb.querySelector(".v8-user");
    const ur = user.getBoundingClientRect();
    return {
      overflowing: bad.slice(0, 6),
      overflowing_count: raw_outside,
      real_overflow_count: bad.length,
      user_box: { w: +ur.width.toFixed(1), h: +ur.height.toFixed(1) },
      rail_width: +sr.width.toFixed(1),
    };
  });

  // Expand again, then check the active marker stays inside the rail.
  if (!track.no_toggle) {
    await page.click(".v8-sidebar-toggle");
    await page.waitForTimeout(400);
  }
  const expanded = await page.evaluate(() => {
    const sb = document.querySelector(".v8-sidebar");
    const active = sb.querySelector(".v8-nav button.active");
    const marker = getComputedStyle(active, ":before");
    return {
      width: +sb.getBoundingClientRect().width.toFixed(1),
      marker_left: marker.left,
      marker_bg: marker.backgroundColor,
    };
  });

  const nonSquare = after.nav_icons.filter((i) => Math.abs(i.w - i.h) > 0.01);

  results.desktop_collapse = {
    before_width: before.width,
    toggle_present: before.toggle_present,
    width_frames: widthTrack,
    distinct_width_frames: new Set(widthTrack).size,
    collapse_toggle_present: !track.no_toggle,
    collapsed_width: after.width,
    collapsed_attr: after.collapsed_attr,
    persisted_flag: after.persisted,
    icon_when_collapsed: { w: after.icon_w, h: after.icon_h },
    icon_center_offset_x: after.icon_offset_from_button_center_x,
    label_opacity_when_collapsed: after.label_opacity,
    non_square_icons_when_collapsed: nonSquare.length,
    total_icons: after.nav_icons.length,
    expanded_back_width: expanded.width,
    active_marker_left: expanded.marker_left,
    sidebar_overflow_y: after.sidebar_overflow_y,
    collapsed_clipped_count: clipped.overflowing_count,
    collapsed_real_overflow_count: clipped.real_overflow_count,
    collapsed_clipped_samples: clipped.overflowing,
    collapsed_user_box: clipped.user_box,
  };
  await ctx.close();
}

/* ── B. short viewport: sticky + internal scroll ─────────────────────── */
{
  const { ctx, page } = await newPage({
    viewport: { width: 1440, height: 620 },
  });
  results.short_viewport = await page.evaluate(() => {
    const sb = document.querySelector(".v8-sidebar");
    const r0 = sb.getBoundingClientRect();
    const canScrollInternally = sb.scrollHeight > sb.clientHeight;
    sb.scrollTop = 400;
    const scrolled = sb.scrollTop;
    sb.scrollTop = 0;
    window.scrollTo(0, 500);
    const r1 = sb.getBoundingClientRect();
    window.scrollTo(0, 0);
    const lastLabel = [...sb.querySelectorAll(".v8-nav button span")].pop();
    return {
      position: getComputedStyle(sb).position,
      sidebar_height: +r0.height.toFixed(1),
      viewport_height: window.innerHeight,
      content_height: sb.scrollHeight,
      scrollable_internally: canScrollInternally,
      internal_scroll_achieved: scrolled,
      top_before_page_scroll: +r0.top.toFixed(1),
      top_after_page_scroll: +r1.top.toFixed(1),
      stays_pinned: Math.abs(r1.top - r0.top) < 1.5,
      last_nav_label: lastLabel ? lastLabel.textContent : null,
    };
  });
  await ctx.close();
}

/* ── C. mobile drawer ────────────────────────────────────────────────── */
{
  const { ctx, page } = await newPage({
    viewport: { width: 390, height: 844 },
  });
  const openTrack = await page.evaluate(async () => {
    document.querySelector(".v8-mobile-menu").click();
    const frames = [];
    const t0 = performance.now();
    while (performance.now() - t0 < 700) {
      await new Promise((r) => requestAnimationFrame(r));
      const d = document.querySelector("#v8-nav-drawer");
      if (d) frames.push(+d.getBoundingClientRect().left.toFixed(1));
    }
    return frames;
  });
  await page.waitForTimeout(350);

  const opened = await page.evaluate(() => {
    const d = document.querySelector("#v8-nav-drawer");
    const all = [
      ...d.querySelectorAll(":scope > div:not(.v8-nav-drawer-head) > button"),
    ];
    // The entry for the current route is legitimately tinted, so the plain
    // (non-active) row is the one that proves the global blue block is gone.
    const btn = all.find((b) => !b.classList.contains("active")) || all[0];
    const svg = btn.querySelector("svg");
    const bb = btn.getBoundingClientRect();
    const ib = svg.getBoundingClientRect();
    return {
      intended_rule_matches: d.querySelectorAll(":scope > button").length,
      nested_buttons: all.length,
      btn_display: getComputedStyle(btn).display,
      btn_bg: getComputedStyle(btn).backgroundColor,
      btn_height: +bb.height.toFixed(1),
      any_button_still_global_blue: all
        .map((b) => getComputedStyle(b).backgroundColor)
        .filter((c) => c === "rgb(66, 89, 216)").length,
      min_btn_height: Math.min(
        ...all.map((b) => +b.getBoundingClientRect().height.toFixed(1)),
      ),
      max_btn_height: Math.max(
        ...all.map((b) => +b.getBoundingClientRect().height.toFixed(1)),
      ),
      max_icon_edge: Math.max(
        ...all
          .map((b) => b.querySelector("svg"))
          .filter(Boolean)
          .map((s) => +s.getBoundingClientRect().width.toFixed(1)),
      ),
      icon_w: +ib.width.toFixed(1),
      icon_h: +ib.height.toFixed(1),
      drawer_padding_bottom: getComputedStyle(d).paddingBottom,
      body_overflow: getComputedStyle(document.body).overflow,
      anim_name: getComputedStyle(d).animationName,
      anim_dur: getComputedStyle(d).animationDuration,
    };
  });

  // Reachability of the last entry inside the drawer.
  const reach = await page.evaluate(() => {
    const d = document.querySelector("#v8-nav-drawer");
    const btns = [
      ...d.querySelectorAll(":scope > div:not(.v8-nav-drawer-head) > button"),
    ];
    const last = btns[btns.length - 1];
    const lr = last.getBoundingClientRect();
    const inView = lr.top >= 0 && lr.bottom <= window.innerHeight;
    if (!inView) d.scrollTop = 9999;
    const lr2 = last.getBoundingClientRect();
    const cx = lr2.left + lr2.width / 2;
    const cy = lr2.top + lr2.height / 2;
    const hit = document.elementFromPoint(cx, cy);
    return {
      last_label: last.querySelector("span").textContent,
      reachable_after_internal_scroll: Boolean(
        hit && (hit === last || last.contains(hit)),
      ),
      drawer_scrollable: d.scrollHeight > d.clientHeight,
    };
  });

  // Closing must animate out and then unmount.
  const closeTrack = await page.evaluate(async () => {
    const d = document.querySelector("#v8-nav-drawer");
    d.parentElement
      .querySelector(".v8-drawer-backdrop")
      .click();
    const frames = [];
    const t0 = performance.now();
    while (performance.now() - t0 < 500) {
      await new Promise((r) => requestAnimationFrame(r));
      const cur = document.querySelector("#v8-nav-drawer");
      if (cur) frames.push(+cur.getBoundingClientRect().left.toFixed(1));
    }
    return { frames, still_mounted_mid: Boolean(document.querySelector("#v8-nav-drawer")) };
  });
  await page.waitForTimeout(600);
  const unmounted = await page
    .locator("#v8-nav-drawer")
    .count()
    .then((n) => n === 0);
  const bodyAfter = await page.evaluate(
    () => getComputedStyle(document.body).overflow,
  );

  results.mobile_drawer = {
    open_frames: openTrack,
    distinct_open_frames: new Set(openTrack).size,
    ...opened,
    ...reach,
    close_frames: closeTrack.frames,
    distinct_close_frames: new Set(closeTrack.frames).size,
    unmounted_after_close: unmounted,
    body_overflow_after_close: bodyAfter,
  };
  await ctx.close();
}

/* ── D. reduced motion ───────────────────────────────────────────────── */
{
  const { ctx, page } = await newPage({ reducedMotion: "reduce" });
  results.reduced_motion = await page.evaluate(() => {
    const sb = document.querySelector(".v8-sidebar");
    const cs = getComputedStyle(sb);
    return {
      transition_property: cs.transitionProperty,
      transition_duration: cs.transitionDuration,
    };
  });
  if (await page.locator(".v8-sidebar-toggle").count()) {
    await page.click(".v8-sidebar-toggle");
    await page.waitForTimeout(150);
  }
  results.reduced_motion.collapses_anyway = await page.evaluate(
    () =>
      document.querySelector(".v8-sidebar").getAttribute("data-collapsed"),
  );
  await ctx.close();
}

await browser.close();

results.verdicts = {
  collapse_animates: results.desktop_collapse.distinct_width_frames > 3,
  collapse_toggle_exists: results.desktop_collapse.collapse_toggle_present === true,
  icons_stay_square_when_collapsed:
    results.desktop_collapse.non_square_icons_when_collapsed === 0,
  collapsed_rail_has_no_overflow:
    results.desktop_collapse.collapsed_real_overflow_count === 0,
  drawer_styled_now:
    results.mobile_drawer.icon_w === 17 &&
    results.mobile_drawer.min_btn_height >= 44 &&
    results.mobile_drawer.max_icon_edge <= 18 &&
    results.mobile_drawer.any_button_still_global_blue === 0 &&
    results.mobile_drawer.max_btn_height <= 60 &&
    results.mobile_drawer.btn_bg === "rgba(0, 0, 0, 0)",
  drawer_open_animates: results.mobile_drawer.distinct_open_frames > 3,
  drawer_close_animates: results.mobile_drawer.distinct_close_frames > 3,
  drawer_unmounts_after_close: results.mobile_drawer.unmounted_after_close,
  background_locked_while_open:
    results.mobile_drawer.body_overflow === "hidden",
  sidebar_pinned_on_short_viewport:
    results.short_viewport.stays_pinned === true,
  sidebar_scrolls_internally: results.short_viewport.scrollable_internally,
  last_nav_reachable: results.mobile_drawer.reachable_after_internal_scroll,
  reduced_motion_disables_transition:
    /0s/.test(results.reduced_motion.transition_duration),
};

writeFileSync(OUT, JSON.stringify(results, null, 2), "utf8");
const v = results.verdicts;
for (const k of Object.keys(v)) console.log(`${v[k] ? "PASS" : "FAIL"} ${k}`);
console.log(`SIDEBAR_MEASURE_DONE out=${OUT}`);
