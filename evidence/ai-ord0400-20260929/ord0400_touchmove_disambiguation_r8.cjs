// ORD-0400 remaining arm: who is right about touchmove -- cmdr's r4 or my r5?
//
// cmdr concluded at CITYNEXUS_AGENT_CONTROL.md:18368 that this box's gesture generator cannot
// emit touchmove, so only a handset can answer "can a thumb drag the drawer". My r5 read
// touchmove=14 with the drawer actually moving 649 px. Both cannot be right unless the CONTEXT
// differs, so this run measures the one variable most likely to differ: `hasTouch`.
//
// Four arms = {hasTouch true,false} x {pointer inside the drawer, pointer outside it}, each with
// page-received event counters AND the behavioural pixel deltas, so a counter alone can never be
// mistaken for movement, and movement alone can never be mistaken for a delivered event.
//
// Stack: my own uvicorn on 8733 over ord0400_live.db (journey 3602a4ca-7713-4f68-beae-53b8383e3d85
// was created through POST /travelers then POST /journeys), my own `vite preview` on 4803 proxying
// /api/v1 there, tip f662905ec4cafe05687d33a05dcbc7ca8031de43, viewport 390x844.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://127.0.0.1:4803/";
const JOURNEY = "3602a4ca-7713-4f68-beae-53b8383e3d85";
const OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_touchmove_disambiguation_r8.json";

const BOOTSTRAP = () => {
  window.__cnEv = { touchstart: 0, touchmove: 0, touchend: 0 };
  for (const t of ["touchstart", "touchmove", "touchend"]) {
    window.addEventListener(t, (e) => { window.__cnEv[t] += 1; }, { capture: true, passive: true });
  }
};

const READ = () => {
  const nav = document.querySelector("#v8-nav-drawer");
  return {
    drawer: nav ? nav.scrollTop : null,
    doc: document.documentElement.scrollTop,
    ev: { ...window.__cnEv },
  };
};

async function oneArm(browser, hasTouch, label, x, y) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch,
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const res = { hasTouch, site: label, point: [x, y] };
  try {
    await page.addInitScript(BOOTSTRAP);
    await page.goto(BASE, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
    await page.evaluate((id) => {
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.demo.journey_id", id);
    }, JOURNEY);
    await page.reload({ waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
    await page.waitForSelector(".v8-mobile-menu", { timeout: 30000 }).catch(() => {});
    await page.locator(".v8-mobile-menu").first().click({ timeout: 10000 }).catch(() => {});
    await page.waitForSelector("#v8-nav-drawer", { timeout: 8000 }).catch(() => {});
    const opened = (await page.locator("#v8-nav-drawer").count()) > 0;
    res.drawer_opened = opened;
    if (!opened) return res;

    res.top_element = await page.evaluate((p) => {
      const el = document.elementFromPoint(p.x, p.y);
      return el ? el.tagName + (el.id ? "#" + el.id : "") : "none";
    }, { x, y });

    await page.evaluate(() => {
      const n = document.querySelector("#v8-nav-drawer");
      if (n) n.scrollTop = 0;
      document.documentElement.scrollTop = 0;
      window.__cnEv = { touchstart: 0, touchmove: 0, touchend: 0 };
    });
    const before = await page.evaluate(READ);
    const yFrom = y + 240;
    const yTo = y - 240;
    const send = (type, yy) =>
      cdp.send("Input.dispatchTouchEvent", {
        type,
        touchPoints: type === "touchEnd" ? [] : [{ x, y: yy, radiusX: 12, radiusY: 12, force: 1 }],
      });
    let dispatch_errors = [];
    try {
      await send("touchStart", yFrom);
      for (let i = 1; i <= 14; i++) {
        await send("touchMove", yFrom - ((yFrom - yTo) * i) / 14);
        await page.waitForTimeout(16);
      }
      await send("touchEnd", yTo);
    } catch (e) {
      dispatch_errors.push(String(e).slice(0, 120));
    }
    await page.waitForTimeout(700);
    const after = await page.evaluate(READ);
    res.before = { drawer: before.drawer, doc: before.doc };
    res.after = { drawer: after.drawer, doc: after.doc };
    res.events_received_by_page = after.ev;
    res.drawer_delta = (after.drawer ?? 0) - (before.drawer ?? 0);
    res.doc_delta = (after.doc ?? 0) - (before.doc ?? 0);
    res.dispatch_errors = dispatch_errors;
  } finally {
    await context.close();
  }
  return res;
}

(async () => {
  const browser = await chromium.launch();
  const rep = { base: BASE, journey_id: JOURNEY, arms: [] };
  rep.arms.push(await oneArm(browser, true, "inside_drawer", 150, 422));
  rep.arms.push(await oneArm(browser, true, "outside_drawer", 350, 422));
  rep.arms.push(await oneArm(browser, false, "inside_drawer", 150, 422));
  rep.arms.push(await oneArm(browser, false, "outside_drawer", 350, 422));

  rep.verdict = {};
  for (const a of rep.arms) {
    a.key = `hasTouch=${a.hasTouch} site=${a.site}`;
    rep.verdict[a.key] = {
      touchmove_delivered: (a.events_received_by_page || {}).touchmove,
      drawer_delta: a.drawer_delta,
      doc_delta: a.doc_delta,
    };
  }
  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  for (const a of rep.arms) {
    console.log(`${a.key.padEnd(34)} opened=${a.drawer_opened} top=${a.top_element}` +
      ` touchmove=${(a.events_received_by_page || {}).touchmove}` +
      ` drawer_delta=${a.drawer_delta} doc_delta=${a.doc_delta}` +
      ` err=${(a.dispatch_errors || []).join("|")}`);
  }
  console.log("RECEIPT=" + OUT);
  await browser.close();
})();
