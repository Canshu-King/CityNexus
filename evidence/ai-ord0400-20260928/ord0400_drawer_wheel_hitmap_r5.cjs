// ORD-0400 slice, two arms in the commander's r4 shape: wheel + top-element hit-test.
//
// Stack (all of it mine, nothing shared):
//   backend  127.0.0.1:8733  uvicorn on `ord0400_live.db` (55 tables, 0 journeys before this run)
//   frontend 127.0.0.1:4803  `vite preview` of tip 869a5b4d, /api/v1 proxied to 8733 via
//                            CITYNEXUS_BACKEND_PORT (frontend/vite.config.ts:141)
//
// Arms mirror `evidence/cmdr-ord0400-20260928/...` / cmdr's drawer_scroll_r4 keys exactly:
// base, drawer_opened, sites{drawer_box,siteA,siteB,siteC}, rows[{site,point,before,after,
// events{touchstart,touchmove,touchend,wheel},drawer_delta,doc_delta}]
// plus this order's own extra block `nav_reach` (item count, scrollHeight overflow, per-item
// in_viewport and centre self-hit), because the order asks whether items are reachable at all.
//
// Touch is dispatched but this box cannot emit touchmove over CDP (commander measured that at
// 21:51), so the touch counters are reported as observed and are NOT offered as an answer to
// "can a thumb drag it" -- that arm still needs a handset.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://127.0.0.1:4803/";
const OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_drawer_wheel_hitmap_r5.json";
const SHOT_BASE = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_r5_drawer_open.png";
const SHOT_END = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_r5_drawer_after_wheel.png";

const COUNTER_BOOTSTRAP = () => {
  window.__cnEv = { touchstart: 0, touchmove: 0, touchend: 0, wheel: 0 };
  const bump = (t) => (e) => { window.__cnEv[t] += 1; };
  for (const t of ["touchstart", "touchmove", "touchend", "wheel"]) {
    window.addEventListener(t, bump(t), { capture: true, passive: true });
  }
};

function navState() {
  const nav = document.querySelector("#v8-nav-drawer");
  if (!nav) return { nav_present: false };
  // items are wrapped: frontend/src/app/V8Experience.tsx:1974 renders each as <div><button>,
  // so `:scope > button` finds none. Take every drawer button except the close control.
  const items = Array.prototype.slice
    .call(nav.querySelectorAll("button"))
    .filter(function (el) { return !el.classList.contains("v8-quiet-button"); });
  return {
    nav_present: true,
    drawer_scroll_top: nav.scrollTop,
    drawer_client_height: nav.clientHeight,
    drawer_scroll_height: nav.scrollHeight,
    overflow_px: nav.scrollHeight - nav.clientHeight,
    doc_scroll_top: document.documentElement.scrollTop,
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
        centre_on_screen: cy >= 0 && cy < window.innerHeight,
        self_hit: top === el || el.contains(top),
        top_element_at_centre: top ? top.tagName + "." + String(top.className || "").split(" ")[0] : "none",
      };
    }),
  };
}

function hitAt(point) {
  const el = document.elementFromPoint(point.x, point.y);
  if (!el) return "none";
  const id = el.id ? "#" + el.id : "";
  const cls = el.className ? "." + String(el.className).split(" ")[0] : "";
  return el.tagName + id + cls;
}

async function snapshot(page) {
  return page.evaluate(() => ({
    drawer: document.querySelector("#v8-nav-drawer") ? document.querySelector("#v8-nav-drawer").scrollTop : null,
    doc: document.documentElement.scrollTop,
    ev: { ...window.__cnEv },
  }));
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const rep = { base: BASE, drawer_opened: false, sites: {}, rows: [] };

  await page.addInitScript(COUNTER_BOOTSTRAP);
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 60000 }).catch((e) => {
    rep.goto_error = String(e).slice(0, 140);
  });

  // How the shell is mounted, stated plainly: journey `3602a4ca-7713-4f68-beae-53b8383e3d85`
  // was created through the product's own POST /travelers then POST /journeys against MY OWN
  // sqlite (ord0400_live.db), so the id below is one the server really has. The shell reads it
  // from localStorage at frontend/src/app/V8Experience.tsx:742 -- that is the same key a normal
  // visit leaves behind, not an invented state.
  rep.journey_id_used = "3602a4ca-7713-4f68-beae-53b8383e3d85";
  rep.entry_buttons = (await page.locator("button").allInnerTexts()).map((s) => s.trim()).filter(Boolean).slice(0, 12);
  await page.evaluate((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.demo.journey_id", id);
  }, rep.journey_id_used);
  await page.reload({ waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.waitForSelector(".v8-mobile-menu", { timeout: 30000 }).catch(() => {});
  rep.menu_button_count = await page.locator(".v8-mobile-menu").count();
  rep.body_text_after_entry = (await page.locator("body").innerText().catch(() => "")).slice(0, 160);

  if (rep.menu_button_count > 0) {
    await page.locator(".v8-mobile-menu").first().click({ timeout: 10000 });
    await page.waitForSelector("#v8-nav-drawer", { timeout: 8000 }).catch(() => {});
  }
  rep.drawer_opened = (await page.locator("#v8-nav-drawer").count()) > 0;
  if (!rep.drawer_opened) {
    fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
    console.log("DRAWER_NOT_OPENED", JSON.stringify(rep).slice(0, 500));
    await browser.close();
    return;
  }

  const box = await page.locator("#v8-nav-drawer").boundingBox();
  rep.sites.drawer_box = [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)];
  const navFull = await page.evaluate(navState);
  rep.nav_reach = {
    item_count: navFull.item_count,
    drawer_client_height: navFull.drawer_client_height,
    drawer_scroll_height: navFull.drawer_scroll_height,
    overflow_px: navFull.overflow_px,
    in_viewport: navFull.items.filter((i) => i.in_viewport).length,
    self_hit: navFull.items.filter((i) => i.self_hit).length,
    items: navFull.items,
  };
  await page.screenshot({ path: SHOT_BASE }).catch(() => {});

  // named probe sites, same topology as cmdr's r4
  const sites = {
    A_body_outside: [350, 422],
    B_drawer_on_button: [150, 422],
    C_top_left: [20, 20],
    D_drawer_low_row: [Math.round(box.x + box.width / 2), Math.round(box.y + box.height - 60)],
  };
  for (const [name, [x, y]] of Object.entries(sites)) {
    rep.sites[name] = [x, y, await page.evaluate(hitAt, { x, y }).catch(() => "none")];
  }
  rep.sites.hitA = await page.evaluate((p) => {
    const el = document.elementFromPoint(p.x, p.y);
    return el ? el.tagName + (el.id ? "#" + el.id : "") : "none";
  }, { x: 350, y: 422 });

  // wheel arm, one row per site
  for (const [name, [x, y]] of Object.entries(sites)) {
    await page.evaluate(() => {
      const n = document.querySelector("#v8-nav-drawer");
      if (n) n.scrollTop = 0;
      document.documentElement.scrollTop = 0;
      window.__cnEv = { touchstart: 0, touchmove: 0, touchend: 0, wheel: 0 };
    });
    await page.waitForTimeout(120);
    const before = await snapshot(page);
    const topNow = await page.evaluate((p) => {
      const el = document.elementFromPoint(p.x, p.y);
      return el ? el.tagName + (el.id ? "#" + el.id : "") : "none";
    }, { x, y });
    await page.mouse.move(x, y);
    await page.mouse.wheel(0, 600);
    await page.waitForTimeout(500);
    const after = await snapshot(page);
    rep.rows.push({
      site: name,
      point: [x, y, topNow],
      before: { drawer: before.drawer, doc: before.doc },
      after: { drawer: after.drawer, doc: after.doc },
      events: after.ev,
      drawer_delta: (after.drawer ?? 0) - (before.drawer ?? 0),
      doc_delta: (after.doc ?? 0) - (before.doc ?? 0),
    });
  }

  // touch counters reported as observed; this box cannot emit touchmove (cmdr 21:51)
  await page.evaluate(() => {
    const n = document.querySelector("#v8-nav-drawer");
    if (n) n.scrollTop = 0;
    window.__cnEv = { touchstart: 0, touchmove: 0, touchend: 0, wheel: 0 };
  });
  const tBefore = await snapshot(page);
  const tx = Math.round(box.x + box.width / 2);
  const tyFrom = Math.round(box.y + box.height - 60);
  const tyTo = Math.round(box.y + 120);
  const send = (type, y) =>
    cdp.send("Input.dispatchTouchEvent", {
      type,
      touchPoints: type === "touchEnd" ? [] : [{ x: tx, y, radiusX: 12, radiusY: 12, force: 1 }],
    });
  try {
    await send("touchStart", tyFrom);
    for (let i = 1; i <= 14; i++) {
      await send("touchMove", tyFrom - ((tyFrom - tyTo) * i) / 14);
      await page.waitForTimeout(16);
    }
    await send("touchEnd", tyTo);
  } catch (e) {
    rep.touch_error = String(e).slice(0, 140);
  }
  await page.waitForTimeout(600);
  const tAfter = await snapshot(page);
  rep.touch_arm = {
    emulated: true,
    answered_thumb_drag: false,
    why: "cmdr measured at 21:51 that this box cannot emit touchmove over CDP; a handset is still required",
    before: { drawer: tBefore.drawer, doc: tBefore.doc },
    after: { drawer: tAfter.drawer, doc: tAfter.doc },
    events: tAfter.ev,
    drawer_delta: (tAfter.drawer ?? 0) - (tBefore.drawer ?? 0),
  };

  await page.screenshot({ path: SHOT_END }).catch(() => {});
  const post = await page.evaluate(navState);
  rep.nav_reach_after = {
    drawer_scroll_top: post.drawer_scroll_top,
    self_hit: post.items.filter((i) => i.self_hit).length,
    last_self_hit: (() => {
      let k = -1;
      post.items.forEach((it, idx) => { if (it.self_hit) k = idx; });
      return k;
    })(),
    items_reachable_by_any_input: post.items.filter((i) => i.self_hit).map((i) => i.label),
    items_unreachable: post.items.filter((i) => !i.self_hit).map((i) => i.label),
  };

  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  console.log("drawer_opened", rep.drawer_opened, "| menu_button_count", rep.menu_button_count);
  console.log("overflow_px", rep.nav_reach.overflow_px, "| items", rep.nav_reach.item_count,
    "| in_viewport", rep.nav_reach.in_viewport, "| self_hit", rep.nav_reach.self_hit);
  for (const r of rep.rows) {
    console.log(`wheel@${r.site.padEnd(18)} point=${r.point[0]},${r.point[1]},${r.point[2]}` +
      ` drawer_delta=${r.drawer_delta} doc_delta=${r.doc_delta} wheel_events=${r.events.wheel}`);
  }
  console.log("touch_arm", JSON.stringify(rep.touch_arm));
  console.log("RECEIPT=" + OUT);
  await browser.close();
})();
