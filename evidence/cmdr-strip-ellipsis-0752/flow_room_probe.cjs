const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  for (const w of [320, 390]) {
    const p = await b.newPage({ viewport: { width: w, height: 820 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light"); localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    const r = await p.evaluate(() => {
      const cs = getComputedStyle(document.querySelector(".v8-content") || document.body);
      const shell = getComputedStyle(document.querySelector(".v8-product-shell") || document.body);
      const strip = document.querySelector(".cn-hero-strip");
      let n = strip, fixed_ancestors = [];
      while (n) { const s = getComputedStyle(n); if (s.position === "fixed" || s.position === "absolute" || s.maxHeight !== "none") fixed_ancestors.push((n.className || n.tagName).toString().split(" ")[0] + ":" + s.position + "/" + s.maxHeight); n = n.parentElement; }
      const root = getComputedStyle(document.documentElement);
      return { content_pad_bottom: cs.paddingBottom, shell_pad_bottom: shell.paddingBottom,
               nav_clearance: root.getPropertyValue("--cn-nav-clearance").trim(), bar_h: (() => { const e = document.querySelector(".v8-mobile-nav"); return e ? Math.round(e.getBoundingClientRect().height) : null; })(),
               strip_ancestors_pinned: fixed_ancestors.join(", ") || "无（全在正常流里）", strip_h: Math.round(strip.getBoundingClientRect().height) };
    });
    console.log(w, JSON.stringify(r));
    await p.close();
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
