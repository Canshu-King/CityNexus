/* After the fix: read the STUDIO day-detail activity list and count whether the English mode words
 * survive anywhere on the Chinese screen, and whether the mapped Chinese words appear. */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 },
    isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto("http://127.0.0.1:4881", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1500);
  const demo = p.locator("button").filter({ hasText: /使用封存的演示行程/ }).first();
  if (await demo.count()) { await demo.click(); await p.waitForTimeout(2500); }
  const ws = p.locator("button").filter({ hasText: /打开行程工作台/ }).first();
  if (await ws.count()) { await ws.click(); await p.waitForTimeout(2500); }
  const lists = await p.evaluate(() => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    return Array.from(document.querySelectorAll(".v8-activity-list")).map((l) => strip(l.innerText)).filter(Boolean);
  });
  const body = await p.evaluate(() => (document.body.innerText || "").replace(/\s+/g, " "));
  const eng = body.match(/Check in|Check out|Overnight/g) || [];
  const zh = body.match(/入住|退房|过夜/g) || [];
  console.log("STUDIO_LISTS:", JSON.stringify(lists).slice(0, 500));
  console.log("english_surviving:", JSON.stringify(eng), "| chinese_mapped:", JSON.stringify(zh));
  await b.close();
})().catch((e) => { console.error("STUDIO_FAIL " + e); process.exit(1); });