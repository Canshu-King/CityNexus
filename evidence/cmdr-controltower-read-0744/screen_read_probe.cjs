/* 控制塔那四格的屏读验收（我落的那笔"没读到就不许断言"，自己当用户走一遍才算数）。
 *
 * 路径：抽屉 → 「智能/控制塔」那一行 → 读 v17-runtime-status 那格与它左右三格此刻画的是什么。
 * 两种情形都要看到：
 *   甲 有 runtimeStatus（后端 /api/v1/agent/runtime-status 回东西）
 *   乙 没 runtimeStatus（我把那一枚请求掐成 404，模拟"服务器没送"）—— 这一臂才是这笔修复的正题
 * 每一臂都读：药丸文案、链路那行、证明那行、策略那格、以及"可行/受保护"两格（那两格还挂着待裁）。
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const READ = () => {
  const pick = (sel) => {
    const el = document.querySelector(sel);
    return el ? (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 120) : "NO_SUCH_ELEMENT";
  };
  const drawerRows = Array.from(document.querySelectorAll("#v8-nav-drawer [data-testid], .v8-nav-drawer [data-testid]"))
    .map(e => e.getAttribute("data-testid"));
  return {
    heading: pick("h1"),
    pill: pick(".v8-intel-hero .v8-status-pill"),
    chain: pick(".v8-chain"),
    runtimeCard: pick('[data-testid="v17-runtime-status"]'),
    facts: Array.from(document.querySelectorAll(".v8-intel-facts > div")).map(d => (d.innerText || "").replace(/\s+/g, " ").trim().slice(0, 90)),
    drawerRows: drawerRows.slice(0, 20),
    hasDrawer: !!document.querySelector("#v8-nav-drawer"),
  };
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const out = {};
  for (const arm of ["with_status", "no_status"]) {
    const p = await b.newPage({ viewport: { width: 1440, height: 950 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    if (arm === "no_status") {
      await p.route("**/api/v1/agent/runtime-status**", (r) => r.fulfill({ status: 404, contentType: "application/json", body: "{}" }));
      await p.route("**/api/v1/agent/status**", (r) => r.fulfill({ status: 404, contentType: "application/json", body: "{}" }));
    }
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    // 抽屉里那一条：按 testid 打开抽屉，再点「智能」那一行
    const opened = await p.evaluate(() => {
      const btn = document.querySelector('[data-testid="v8-mobile-menu"]') || document.querySelector("[data-testid='sidebar-collapse']");
      if (btn) btn.click();
      return btn ? "clicked " + btn.getAttribute("data-testid") : "NO_MENU_BUTTON";
    });
    await p.waitForTimeout(900);
    let rows = await p.evaluate(() => Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']"))
      .map(e => ({ tid: e.getAttribute("data-testid"), text: (e.innerText || "").replace(/\s+/g, " ").trim().slice(0, 26) })));
    const target = rows.find(r => /智能|控制塔|Intelligence|Control/i.test(r.text)) || null;
    let clicked = target ? "clicked " + target.tid : "NO_TARGET_ROW";
    if (target) {
      await p.evaluate((tid) => { const e = document.querySelector('[data-testid="' + tid + '"]'); if (e) e.click(); }, target.tid);
      await p.waitForTimeout(1600);
    }
    out[arm] = { opened, drawer_rows: rows.length, rows: rows.slice(0, 18), clicked, read: await p.evaluate(READ) };
    await p.screenshot({ path: "D:/moodle/_cmdr_fe_rev_1016/shots/controltower_" + arm + ".png", fullPage: false });
    await p.close();
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/controltower_read.json", JSON.stringify(out, null, 1), "utf-8");
  for (const arm of Object.keys(out)) {
    const r = out[arm];
    console.log("=== 臂", arm, "| 抽屉", r.opened, "| 行数", r.drawer_rows, "|", r.clicked);
    console.log("   屏标题:", r.read.heading);
    console.log("   药丸:", r.read.pill);
    console.log("   链路:", r.read.chain);
    console.log("   运行时格:", r.read.runtimeCard);
    r.read.facts.forEach((f, i) => console.log("   事实格", i + 1 + ":", f));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
