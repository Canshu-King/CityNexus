// ORD-0400 r7: per-item reachability -- can EVERY drawer item be brought to a hit-testable position?
//
// r6 showed that at the bottom offset only 3 of 14 items hit-test to themselves, which is a
// position effect of a scroll container, not a per-item verdict. The honest test for requirement
// (1) is per item: put that item in the middle of the client, then ask whether its centre
// hit-tests to itself.
//
// The scroll position is set programmatically here; that is legitimate only because r5 and r6
// independently proved the WHEEL moves this same container (scrollTop 0 -> 3668 by wheel notches),
// so an offset set by script is an offset a pointer can also arrive at. Both facts are recorded
// in the receipt so nobody has to take that on trust.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://127.0.0.1:4803/";
const JOURNEY = "3602a4ca-7713-4f68-beae-53b8383e3d85";
const OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_per_item_reachability_r10.json";

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
  });
  const page = await context.newPage();
  const rep = { base: BASE, journey_id: JOURNEY, wheel_proof: null, items: [] };

  await page.goto(BASE, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.evaluate((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.demo.journey_id", id);
  }, JOURNEY);
  await page.reload({ waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.waitForSelector(".v8-mobile-menu", { timeout: 30000 }).catch(() => {});
  await page.locator(".v8-mobile-menu").first().click({ timeout: 10000 }).catch(() => {});
  await page.waitForSelector("#v8-nav-drawer", { timeout: 8000 }).catch(() => {});

  // prove the wheel owns this scroll position, once, up front
  await page.mouse.move(150, 422);
  const wBefore = await page.evaluate(() => document.querySelector("#v8-nav-drawer").scrollTop);
  await page.mouse.wheel(0, 900);
  await page.waitForTimeout(400);
  const wAfter = await page.evaluate(() => document.querySelector("#v8-nav-drawer").scrollTop);
  rep.wheel_proof = { before: wBefore, after: wAfter, delta: wAfter - wBefore, moves_drawer: wAfter > wBefore };
  await page.evaluate(() => { document.querySelector("#v8-nav-drawer").scrollTop = 0; });

  const count = await page.evaluate(() =>
    Array.prototype.slice
      .call(document.querySelectorAll("#v8-nav-drawer button"))
      .filter((el) => !el.classList.contains("v8-quiet-button")).length);

  for (let idx = 0; idx < count; idx++) {
    const r = await page.evaluate((i) => {
      const nav = document.querySelector("#v8-nav-drawer");
      const items = Array.prototype.slice
        .call(nav.querySelectorAll("button"))
        .filter((el) => !el.classList.contains("v8-quiet-button"));
      const el = items[i];
      const box = el.getBoundingClientRect();
      const target = Math.max(0, Math.min(nav.scrollHeight - nav.clientHeight,
        nav.scrollTop + box.top - (nav.clientHeight / 2 - box.height / 2)));
      nav.scrollTop = target;
      const r2 = el.getBoundingClientRect();
      const cx = Math.round(r2.x + r2.width / 2);
      const cy = Math.round(r2.y + r2.height / 2);
      const top = document.elementFromPoint(cx, cy);
      return {
        index: i,
        label: (el.textContent || "").trim().slice(0, 26),
        scrollTop_after: nav.scrollTop,
        clientHeight: nav.clientHeight,
        scrollHeight: nav.scrollHeight,
        centre: [cx, cy],
        fully_inside_client: r2.top >= 0 && r2.bottom <= nav.clientHeight,
        self_hit: top === el || el.contains(top),
        top_element: top ? top.tagName : "none",
      };
    }, idx);
    rep.items.push(r);
  }

  rep.summary = {
    item_count: rep.items.length,
    reachable_by_centre_hit: rep.items.filter((i) => i.self_hit).length,
    unreachable: rep.items.filter((i) => !i.self_hit).map((i) => `${i.label} @scrollTop=${i.scrollTop_after}`),
  };
  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  console.log("wheel_proof", JSON.stringify(rep.wheel_proof));
  console.log("summary", JSON.stringify(rep.summary));
  console.log("RECEIPT=" + OUT);
  await browser.close();
})();
