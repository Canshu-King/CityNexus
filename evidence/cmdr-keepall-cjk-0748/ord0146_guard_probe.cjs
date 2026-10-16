/* ORD-0146 那道保守护栏重跑一遍：给预订卡塞一枚 60 字符的长参考号，看行会不会被撑爆。
 * 我这条 keep-all 只作用在四枚读数标签上，理论上碰不到参考号；但这条护栏是别人真金白银修出来的
 * （508px 撑进 360px 视口），所以每次动这一族都要当场再量一遍，不是想一遍。
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const out = [];
  for (const w of [320, 360, 390]) {
    const p = await b.newPage({ viewport: { width: w, height: 800 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-trips"]'); if (e) e.click(); });
    await p.waitForTimeout(800);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="trips-tab-bookings"]'); if (e) e.click(); });
    await p.waitForTimeout(1100);
    const r = await p.evaluate((long) => {
      const card = document.querySelector(".v8-booking-card");
      if (!card) return { present: false };
      const div = card.querySelector(":scope > div");
      const target = div || card;
      const before = Math.round(card.getBoundingClientRect().right);
      // 找一枚能装参考号的文本节点：卡里最小的那段文本
      let host = null;
      for (const el of target.querySelectorAll("*")) {
        if (el.childElementCount !== 0) continue;
        const t = (el.textContent || "").trim();
        if (t.length > 3 && /mock|REF|CNX|[A-Za-z0-9_-]{6,}/i.test(t)) { host = el; break; }
      }
      if (!host) host = target.querySelector("p") || target.querySelector("strong") || target;
      const prev = host.textContent;
      host.textContent = long;
      const after = {
        card_right: Math.round(card.getBoundingClientRect().right),
        card_width: Math.round(card.getBoundingClientRect().width),
        host_lines: (() => { const rg = document.createRange(); rg.selectNodeContents(host); return new Set(Array.from(rg.getClientRects()).map(x => Math.round(x.top))).size; })(),
        host_widths: (() => { const rg = document.createRange(); rg.selectNodeContents(host); return Array.from(rg.getClientRects()).map(x => Math.round(x.width)); })(),
        doc_scrollW: document.documentElement.scrollWidth,
        viewport: window.innerWidth,
      };
      host.textContent = prev;
      return { present: true, before, injected: long.length, host_tag: host.tagName, ...after };
    }, "REF-" + "X".repeat(55));
    out.push({ width: w, ...r });
    await p.close();
  }
  console.log(JSON.stringify(out, null, 1));
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
