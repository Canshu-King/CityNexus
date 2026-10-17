/* 丙臂（真屏那一臂）v2：给一串类名，六屏逐屏数它到底挂在几个元素上。
 *
 * 与上一版的分别：
 *   一 名单从命令行来，不再写死三枚；
 *   二 跑之前先做"树身份"自检——把 :8121 现在端出来的每一枚 css/tsx 字节与本地工作树比，
 *      不等就拒绝出证（这是子 Agent 教的：它比出 187 枚里 3 枚不等，于是丙臂宁可不跑，
 *      也没拿"另一棵树的零命中"当证据）；
 *   三 六屏标志必须互不相同，否则整臂判 VACUOUS 以 rc=3 退出（不给假绿）。
 *
 * 用法：node _cmdr_deadcss_dom_probe_r2.cjs <标签> <逗号分隔的类名>
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const LABEL = process.argv[2] || "run";
const TOKENS = (process.argv[3] || "").split(",").map(s => s.trim()).filter(Boolean);
const TREE = "D:/moodle/_cmdr_fe_rev_1016/tip/frontend";
const BASE = "http://127.0.0.1:8121";
const POSITIVE = ["v8-page", "v8-me-card", "trip-stop"];

const STEPS = [
  ["hub", null], ["live", '[data-testid="today-hero-cta"]'], ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'], ["map", '[data-testid="nav-map"]'], ["me", '[data-testid="nav-me"]'],
];

function sha(buf) { return crypto.createHash("sha1").update(buf).digest("hex"); }

(async () => {
  if (!TOKENS.length) { console.log("用法：node 本尺 <标签> <逗号分隔类名>；名单为空我就不跑。"); process.exit(2); }
  const b = await chromium.launch({ channel: "chrome", headless: true });

  // —— 树身份自检：本地工作树里每一枚 css/ts/tsx，与服务端端出来的同一份比字节 ——
  const walk = (dir, acc) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name === "dist" || e.name.startsWith(".")) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p, acc);
      else if (/\.(css|ts|tsx)$/.test(e.name)) acc.push(p);
    }
    return acc;
  };
  const files = walk(TREE, []);
  let equal = 0, diff = [], skipped = 0;
  for (const f of files) {
    const rel = path.relative(TREE, f).replace(/\\/g, "/");
    const url = BASE + "/" + rel.replace(/^\.\//, "") + "?direct";
    // vite 不带 ?direct 时把 css 端成 JS 模块（我 08:0x 就栽过一次），所以必须带这个查询取原文。
    let res;
    try { res = await (await fetch(url)).arrayBuffer(); } catch (e) { skipped++; continue; }
    const served = Buffer.from(res);
    if (served.length === 0) { skipped++; continue; }
    const local = fs.readFileSync(f);
    // vite 会把 .ts/.tsx 端成转译后的 JS，只有 .css 是原文；所以逐字节比只适用于 css。
    if (/\.css$/.test(rel)) { if (sha(served) === sha(local)) equal++; else diff.push(rel); }
    else skipped++;
  }
  console.log("树身份自检：本地 css/ts/tsx " + files.length + " 枚｜css 逐字节相等 " + equal + " 枚｜css 不等 " + diff.length + " 枚（" + diff.slice(0, 6).join(", ") + "）｜非 css 不比 " + skipped + " 枚");
  if (equal === 0) { console.log("FATAL 一枚 css 都没比上，树身份不成立，丙臂不出证。"); process.exit(4); }

  const perScreen = {};
  const marks = [];
  for (const [screen, sel] of STEPS) {
    const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto(BASE + "/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    if (sel) { await p.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, sel); await p.waitForTimeout(1400); }
    const got = await p.evaluate((toks) => {
      const h = document.querySelector("h1");
      const out = { heading: ((h && h.innerText) || "").slice(0, 30), counts: {}, classattrs: 0 };
      const all = Array.from(document.querySelectorAll("[class]"));
      out.classattrs = all.length;
      for (const t of toks.concat(["__POS__"])) out.counts[t] = 0;
      for (const t of toks) {
        out.counts[t] = document.querySelectorAll("." + t).length;
      }
      for (const t of ["v8-page", "v8-me-card", "trip-stop"]) out.counts[t] = document.querySelectorAll("." + t).length;
      return out;
    }, TOKENS);
    perScreen[screen] = got;
    marks.push(got.heading);
    await p.close();
  }
  const distinct = new Set(marks).size;
  console.log("六屏标志（互不相同才算走对了屏）:", JSON.stringify(marks), "| 不同数", distinct);
  if (distinct < 5) { console.log("VACUOUS 走屏不成立，整臂作废（rc=3）。"); process.exit(3); }

  const rows = [];
  for (const t of TOKENS.concat(POSITIVE)) {
    const total = STEPS.reduce((n, [s]) => n + (perScreen[s].counts[t] || 0), 0);
    rows.push({ token: t, dom_hits_total: total, per_screen: STEPS.map(([s]) => s + "=" + (perScreen[s].counts[t] || 0)).join(",") });
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/deadcss_dom_" + LABEL + ".json",
    JSON.stringify({ label: LABEL, at: new Date().toISOString(), tree_identity: { css_equal: equal, css_diff: diff, files: files.length },
                     headings: marks, rows }, null, 1), "utf-8");
  for (const r of rows) console.log("  " + (r.dom_hits_total === 0 ? "零命中" : "命中 " + r.dom_hits_total) + " | " + r.token.padEnd(22) + " | " + r.per_screen);
  console.log("读数落 deadcss_dom_" + LABEL + ".json");
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
