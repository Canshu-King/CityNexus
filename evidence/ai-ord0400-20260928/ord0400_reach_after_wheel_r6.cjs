// ORD-0400 r6: after wheeling, does every drawer item become hit-testable? (requirement (1))
//
// Same private stack as r5: my own uvicorn on 8733 over ord0400_live.db, my own `vite preview`
// on 4803 proxying /api/v1 there, tip 869a5b4d6424406451738afdb50ea20e6ef686f3, viewport 390x844.
// Journey 3602a4ca-7713-4f68-beae-53b8383e3d85 was made through POST /travelers then
// POST /journeys against that same private database.
//
// Question answered, and only this one: with the wheel pointed inside the drawer, how many of the
// items can be made to hit-test to themselves, and which stay unreachable. This is NOT a handset
// thumb measurement.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://127.0.0.1:4803/";
const JOURNEY = "3602a4ca-7713-4f68-beae-53b8383e3d85";
const OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_reach_after_wheel_r6.json";
const SHOT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0400_r6_drawer_bottom.png";

const STATE = () => {
  const nav = document.querySelector("#v8-nav-drawer");
  if (!nav) return { nav_present: false };
  const items = Array.prototype.slice
    .call(nav.querySelectorAll("button"))
    .filter((el) => !el.classList.contains("v8-quiet-button"));
  return {
    nav_present: true,
    scrollTop: nav.scrollTop,
    clientHeight: nav.clientHeight,
    scrollHeight: nav.scrollHeight,
    at_bottom: nav.scrollTop + nav.clientHeight >= nav.scrollHeight - 2,
    items: items.map((el) => {
      const r = el.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2);
      const cy = Math.round(r.y + r.height / 2);
      const top = document.elementFromPoint(cx, cy);
      return {
        label: (el.textContent || "").trim().slice(0, 26),
        box_y: Math.round(r.y),
        centre_on_screen: cy >= 0 && cy < window.innerHeight,
        fully_inside_client: r.top >= 0 && r.bottom <= nav.clientHeight,
        self_hit: top === el || el.contains(top),
        top_element: top ? top.tagName : "none",
      };
    }),
  };
};

function tally(s) {
  return {
    items: s.items.length,
    centre_on_screen: s.items.filter((i) => i.centre_on_screen).length,
    self_hit: s.items.filter((i) => i.self_hit).length,
    scrollTop: s.scrollTop,
    at_bottom: s.at_bottom,
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
  const page = await context.newPage();
  const rep = { base: BASE, journey_id: JOURNEY, steps: [] };

  await page.goto(BASE, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.evaluate((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.demo.journey_id", id);
  }, JOURNEY);
  await page.reload({ waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.waitForSelector(".v8-mobile-menu", { timeout: 30000 }).catch(() => {});
  await page.locator(".v8-mobile-menu").first().click({ timeout: 10000 }).catch(() => {});
  await page.waitForSelector("#v8-nav-drawer", { timeout: 8000 }).catch(() => {});

  const first = await page.evaluate(STATE);
  rep.baseline = tally(first);
  rep.baseline_items = first.items;

  // wheel inside the drawer, one notch at a time, until it stops moving
  await page.mouse.move(150, 422);
  for (let k = 0; k < 24; k++) {
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(120);
    const s = await page.evaluate(STATE);
    rep.steps.push(tally(s));
    if (s.at_bottom) {
      rep.reached_bottom_at_step = k + 1;
      rep.final_state = s;
      break;
    }
  }
  if (!rep.final_state) rep.final_state = await page.evaluate(STATE);
  rep.final_tally = tally(rep.final_state);
  rep.unreachable_labels = rep.final_state.items
    .filter((i) => !i.self_hit)
    .map((i) => `${i.label} (box_y=${i.box_y}, centre_on_screen=${i.centre_on_screen}, top=${i.top_element})`);
  await page.screenshot({ path: SHOT }).catch(() => {});

  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  console.log("baseline  ", JSON.stringify(rep.baseline));
  console.log("steps     ", rep.steps.map((s) => `${s.scrollTop}/${s.self_hit}`).join(" "));
  console.log("bottom_at_step", rep.reached_bottom_at_step, "| final", JSON.stringify(rep.final_tally));
  console.log("unreachable_after_bottom", JSON.stringify(rep.unreachable_labels));
  console.log("RECEIPT=" + OUT);
  await browser.close();
})();
