/* Press 「AI 帮我规划」 and read the sheet it is supposed to open (data-testid=plan-ai-sheet):
 * does the modal appear, and does it tell the user what will happen / that AI is not configured? */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");
const OUT = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_aisheet.json";
(async () => {
  const run = { schema: "CNX_BUILDING_WALK_AISHEET", started: new Date().toString(), page_errors: [], console_errors: [] };
  const b = await chromium.launch();
  const ctx = await b.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  p.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });
  await p.goto("http://127.0.0.1:4881", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1500);
  const demo = p.locator("button").filter({ hasText: /使用封存的演示行程/ }).first();
  if (await demo.count()) { await demo.click(); await p.waitForTimeout(2500); }
  // press the AI button by testid, the same control the earlier walk hit-tested and pressed
  await p.locator("[data-testid='hub-plan-with-ai']").click();
  await p.waitForTimeout(1200);
  const sheet = await p.evaluate(() => {
    const el = document.querySelector("[data-testid='plan-ai-sheet']");
    if (!el) return { present: false };
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    return { present: true, text: strip(el.innerText).slice(0, 1200),
      has_input: !!el.querySelector("[data-testid='plan-ai-input']"),
      controls: Array.from(el.querySelectorAll("button,[role='button']")).map((b) => strip(b.innerText).slice(0, 30)).filter(Boolean).slice(0, 12) };
  });
  run.sheet = sheet;
  await p.screenshot({ path: OUT.replace(/\.json$/, "_sheet.png"), fullPage: true });
  // does it say anything about the runtime / AI availability?
  if (sheet.present) {
    run.says_runtime = /未配置|没有接|不可用|不能|需要配置|没有开|AI|模型|provider/i.test(sheet.text);
  }
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await b.close();
  console.log("SHEET_PRESENT=" + sheet.present + " has_input=" + (sheet.has_input || false));
  console.log("SHEET_TEXT:\n" + (sheet.text || "").slice(0, 700));
})().catch((e) => { console.error("AISHEET_FAIL " + e); process.exit(1); });