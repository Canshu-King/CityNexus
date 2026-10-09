/* Is the bottom nav really un-tappable (a product defect: "点不动"), or does my hit-test fail on nav?
 * Clicks the nav item's centre by coordinate and reports whether the screen actually changed. A real
 * phone finger taps the centre too, so if a coordinate click works, the control IS pressable and my
 * hit-test was the thing that was wrong. */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 },
    isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto("http://127.0.0.1:4881", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1500);
  const demo = p.locator("button").filter({ hasText: /使用封存的演示行程/ }).first();
  if (await demo.count()) { await demo.click(); await p.waitForTimeout(2200); }
  const results = {};
  for (const tab of ["今天", "行程", "地图", "Copilot", "我的"]) {
    const before = await p.evaluate(() => document.body.innerText.slice(0, 60));
    const info = await p.evaluate((t) => {
      const els = Array.from(document.querySelectorAll("button,[role='button'],a,nav *"))
        .filter((el) => (el.innerText || "").trim() === t);
      const el = els[els.length - 1] || els[0];
      if (!el) return { found: false };
      el.scrollIntoViewIfNeeded();
      const b = el.getBoundingClientRect();
      const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return { found: true, tag: el.tagName, cx, cy, w: b.width, h: b.height,
        topTag: top ? top.tagName : null, topText: top ? (top.innerText || "").trim().slice(0, 20) : null,
        elContainsTop: !!top && (top === el || el.contains(top)) };
    }, tab);
    if (info.found) {
      await p.mouse.click(info.cx, info.cy);
      await p.waitForTimeout(1500);
    }
    const after = await p.evaluate(() => document.body.innerText.slice(0, 60));
    results[tab] = { ...info, screen_changed: before !== after };
    console.log(tab + " -> " + JSON.stringify(results[tab]));
  }
  await b.close();
})().catch((e) => { console.error("NAVTEST_FAIL " + e); process.exit(1); });