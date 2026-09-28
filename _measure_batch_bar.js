/* Why are 完成 and 新建一批 not in the same band at 390px? Measure it instead of guessing:
   print each button's box, its own computed flex/min-height, and the container's computed
   display/direction/wrap/width, at four real widths. */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = "http://127.0.0.1:4817";
const WIDTHS = [320, 360, 390, 430];

const read = () => {
  const box = (el) => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) };
  };
  const cs = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    return {
      display: s.display,
      dir: s.flexDirection,
      wrap: s.flexWrap,
      width: s.width,
      gap: s.gap,
      marginLeft: s.marginLeft,
      alignItems: s.alignItems,
    };
  };
  const bar = document.querySelector(".v8-batch-bar");
  const act = document.querySelector(".v8-batch-actions");
  const btns = Array.from(act ? act.querySelectorAll("button") : []);
  return {
    bar_box: box(bar),
    bar_cs: cs(bar),
    act_box: box(act),
    act_cs: cs(act),
    buttons: btns.map((el) => ({
      label: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 10),
      box: box(el),
      cs: { display: getComputedStyle(el).display, flex: getComputedStyle(el).flex, minH: getComputedStyle(el).minHeight, ws: getComputedStyle(el).whiteSpace },
    })),
  };
};

(async () => {
  const scene = await (await fetch(BASE + "/api/v1/demo/scene")).json();
  const journey = String(scene.journey_id);
  const browser = await chromium.launch();
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ locale: "zh-CN", viewport: { width, height: 844 } });
    await ctx.addInitScript((seed) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", "zh-CN");
      localStorage.setItem("citynexus.v8.journey_id", seed);
    }, journey);
    const page = await ctx.newPage();
    await page.goto(BASE + "/v8/hub", { waitUntil: "load" });
    await page.waitForSelector('[data-testid="today-hero"]', { timeout: 120_000 }).catch(() => {});
    await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
    await page.waitForSelector('[data-testid="v13-discovery-goal"]', { timeout: 120_000 }).catch(() => {});
    await page.locator('select[aria-label]').first().selectOption("replay").catch(() => {});
    await page.locator('[data-testid="v13-discover-submit"]').click();
    await page
      .waitForSelector('[data-testid="v13-discovery-batch-bar"]', { timeout: 90_000 })
      .catch(() => {});
    await page.waitForTimeout(600);
    const r = await page.evaluate(read);
    const ys = (r.buttons || []).map((b) => b.box?.y);
    console.log(
      width,
      "same_band:",
      ys.length === 2 ? Math.abs(ys[0] - ys[1]) < Math.max(r.buttons[0].box.h, r.buttons[1].box.h) : "n/a",
      JSON.stringify(r),
    );
    await ctx.close();
  }
  await browser.close();
})();
