// ORD-0400 probe r3: reach the V8 shell, then ask which input can scroll the drawer.
//
// r2 could not test anything: with no backend the app parks on the pre-journey onboarding screen,
// which deliberately has no shell (see `frontend/src/app/V8Experience.tsx:1417`), so the drawer
// node did not exist at all (.v8-mobile-menu count = 0).
//
// r3 primes the one reference the shell reads -- `citynexus.v8.journey_id` (V8Experience.tsx:742) --
// through localStorage only. Nothing is written to any database, no request is sent anywhere but
// localhost, and the journey id is deliberately one this server does not have: the drawer's scroll
// behaviour cannot depend on journey data, and a dead id is exactly what the read path classifies
// as JOURNEY_NOT_FOUND without disturbing the shell.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://localhost:4831/";
const OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_drawer_scroll_probe_r3.json";
const SHOT_A = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_drawer_top_r3.png";
const SHOT_B = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_drawer_after_touch_drag_r3.png";

function readNav() {
  const nav = document.querySelector("#v8-nav-drawer");
  if (!nav) return { nav_present: false };
  const cs = getComputedStyle(nav);
  const items = Array.prototype.slice.call(nav.querySelectorAll(":scope > button"));
  return {
    nav_present: true,
    nav_client_height: nav.clientHeight,
    nav_scroll_height: nav.scrollHeight,
    nav_overflow_y: cs.overflowY,
    nav_z_index: cs.zIndex,
    nav_touch_action: cs.touchAction,
    nav_overscroll: cs.overscrollBehaviorY,
    nav_scroll_top: nav.scrollTop,
    backdrop_count: document.querySelectorAll(".v8-drawer-backdrop").length,
    backdrop_z: document.querySelector(".v8-drawer-backdrop")
      ? getComputedStyle(document.querySelector(".v8-drawer-backdrop")).zIndex
      : null,
    item_count: items.length,
    items: items.map(function (el) {
      const r = el.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2);
      const cy = Math.round(r.y + r.height / 2);
      const top = document.elementFromPoint(cx, cy);
      return {
        label: (el.textContent || "").trim().slice(0, 26),
        box_y: Math.round(r.y),
        in_viewport: r.y >= 0 && r.bottom <= window.innerHeight,
        centre_on_screen: cx >= 0 && cy >= 0 && cx < window.innerWidth && cy < window.innerHeight,
        self_hit: top === el || el.contains(top),
        hit_tag: top ? top.tagName.toLowerCase() : "none",
      };
    }),
  };
}

function summarise(m) {
  if (!m || !m.nav_present) return { nav_present: false };
  const hits = m.items
    .map(function (i, k) { return i.self_hit ? k : -1; })
    .filter(function (k) { return k >= 0; });
  return {
    nav_present: true,
    nav_scroll_top: m.nav_scroll_top,
    nav_client_height: m.nav_client_height,
    nav_scroll_height: m.nav_scroll_height,
    item_count: m.item_count,
    in_viewport: m.items.filter(function (i) { return i.in_viewport; }).length,
    centre_on_screen: m.items.filter(function (i) { return i.centre_on_screen; }).length,
    self_hit: hits.length,
    first_hit: hits.length ? hits[0] : -1,
    last_hit: hits.length ? hits[hits.length - 1] : -1,
    labels_not_reachable: m.items
      .filter(function (i) { return !i.self_hit; })
      .map(function (i) { return i.label; }),
  };
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
  });
  const cdpSession = await context.newCDPSession(await context.newPage());
  const page = context.pages()[0];
  const cdp = cdpSession;

  // prime the shell reference before the app reads it
  await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 45000 }).catch(() => {});
  await page.evaluate(() => {
    localStorage.setItem("citynexus.v8.journey_id", "ord0400-probe-no-such-journey");
  });
  await page.reload({ waitUntil: "networkidle", timeout: 45000 }).catch(() => {});

  const rep = { base: BASE, viewport: "390x844", hasTouch: true, arms: {} };
  rep.title = await page.title();
  rep.menu_button_count = await page.locator(".v8-mobile-menu").count();
  rep.bottom_nav_count = await page.locator(".v8-bottom-nav, nav.v8-bottom-nav").count();
  rep.body_text_head = (await page.locator("body").innerText().catch(() => "")).slice(0, 200);

  await page.locator(".v8-mobile-menu").first().click({ timeout: 12000 }).catch((e) => {
    rep.click_error = String(e).slice(0, 140);
  });
  await page.waitForSelector("#v8-nav-drawer", { timeout: 8000 }).catch(() => {});
  rep.drawer_after_click = await page.locator("#v8-nav-drawer").count();

  const base = await page.evaluate(readNav);
  rep.arms.baseline = summarise(base);
  rep.arms.baseline_full = base;
  await page.screenshot({ path: SHOT_A }).catch(() => {});

  await page.evaluate(() => {
    const n = document.querySelector("#v8-nav-drawer");
    if (n) n.scrollTop = 99999;
  });
  await page.waitForTimeout(250);
  rep.arms.programmatic = summarise(await page.evaluate(readNav));
  await page.evaluate(() => {
    const n = document.querySelector("#v8-nav-drawer");
    if (n) n.scrollTop = 0;
  });
  await page.waitForTimeout(200);

  const box = await page.locator("#v8-nav-drawer").boundingBox().catch(() => null);
  rep.arms.drawer_box = box;
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + 300);
    const b = await page.evaluate(() => document.querySelector("#v8-nav-drawer").scrollTop);
    await page.mouse.wheel(0, 600);
    await page.waitForTimeout(600);
    const a = await page.evaluate(() => document.querySelector("#v8-nav-drawer").scrollTop);
    rep.arms.wheel = { pointer_over: "drawer centre", before: b, after: a, delta: a - b, scrolled: a > b };
    rep.arms.wheel_state = summarise(await page.evaluate(readNav));
    await page.evaluate(() => { document.querySelector("#v8-nav-drawer").scrollTop = 0; });
    await page.waitForTimeout(200);

    const tb = await page.evaluate(() => document.querySelector("#v8-nav-drawer").scrollTop);
    const x = box.x + box.width / 2;
    const yFrom = box.y + 640;
    const yTo = box.y + 150;
    const send = function (type, y) {
      return cdp.send("Input.dispatchTouchEvent", {
        type: type,
        touchPoints: type === "touchEnd" ? [] : [{ x: x, y: y, radiusX: 12, radiusY: 12, force: 1 }],
      });
    };
    await send("touchStart", yFrom);
    for (let i = 1; i <= 16; i++) {
      await send("touchMove", yFrom - ((yFrom - yTo) * i) / 16);
      await page.waitForTimeout(16);
    }
    await send("touchEnd", yTo);
    await page.waitForTimeout(800);
    const ta = await page.evaluate(() => document.querySelector("#v8-nav-drawer").scrollTop);
    const post = summarise(await page.evaluate(readNav));
    rep.arms.touch_drag = {
      emulated: true,
      label: "CDP touch events, NOT a handset thumb",
      before: tb,
      after: ta,
      delta: ta - tb,
      scrolled: ta > tb,
      self_hit_after: post.self_hit,
      last_hit_after: post.last_hit,
      unreachable_labels_after: post.labels_not_reachable,
    };
    await page.screenshot({ path: SHOT_B }).catch(() => {});
  }

  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  console.log("menu_button_count", rep.menu_button_count, "| drawer_after_click", rep.drawer_after_click);
  console.log("baseline    ", JSON.stringify(rep.arms.baseline).slice(0, 400));
  console.log("programmatic", JSON.stringify(rep.arms.programmatic).slice(0, 220));
  console.log("wheel       ", JSON.stringify(rep.arms.wheel));
  console.log("wheel_state ", JSON.stringify(rep.arms.wheel_state).slice(0, 220));
  console.log("touch_drag  ", JSON.stringify(rep.arms.touch_drag).slice(0, 400));
  console.log("RECEIPT=" + OUT);
  await browser.close();
})();
