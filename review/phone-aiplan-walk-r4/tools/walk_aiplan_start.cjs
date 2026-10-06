/* The real unknown-success moment: with the AI switch OFF, press 开始规划 and read what the screen says.
 * If it refuses with a sentence, success is tellable. If it silently does nothing or claims success, it is
 * the "不知道成没成" defect the building targets. */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");
const OUT = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_aiplan_start.json";
(async () => {
  const run = { schema: "CNX_BUILDING_WALK_AIPLAN_START", started: new Date().toString(),
    steps: [], page_errors: [], console_errors: [], api: [] };
  const b = await chromium.launch();
  const ctx = await b.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  p.on("console", (m) => { if (m.type() === "error") run.console_errors.push(String(m.text()).slice(0, 200)); });
  p.on("response", async (r) => {
    const u = r.url();
    if (/\/(plans|extract|intake|agent)/.test(u) && !u.includes("/assets/")) {
      let d = ""; try { d = (await r.text()).slice(0, 240); } catch (e) {}
      run.api.push({ url: u.replace(/[0-9a-f-]{36}/g, "<id>"), method: r.request().method(), status: r.status(), detail: d });
    }
  });
  const sheetText = () => p.evaluate(() => {
    const el = document.querySelector("[data-testid='plan-ai-sheet']");
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    return { present: !!el, text: el ? strip(el.innerText).slice(0, 1400) : "",
      spinner: document.querySelectorAll("[aria-busy='true'],.v8-spinner").length,
      disabled: Array.from((el || document).querySelectorAll("button")).map((x) => ({ w: strip(x.innerText).slice(0, 20), d: !!x.disabled })).filter((x) => /开始规划|规划/.test(x.w)) };
  });
  await p.goto("http://127.0.0.1:4881", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1500);
  const demo = p.locator("button").filter({ hasText: /使用封存的演示行程/ }).first();
  if (await demo.count()) { await demo.click(); await p.waitForTimeout(2500); }
  await p.locator("[data-testid='hub-plan-with-ai']").click();
  await p.waitForTimeout(1000);
  run.opened = await sheetText();
  // press 开始规划
  const start = p.locator("[data-testid='plan-ai-sheet'] button").filter({ hasText: /开始规划/ }).first();
  let pressed = false, disabled = false;
  if (await start.count()) {
    disabled = await start.isDisabled();
    if (!disabled) { await start.click(); pressed = true; }
  }
  run.start_press = { pressed, disabled };
  await p.waitForTimeout(8000);
  const after = await sheetText();
  run.after_start = after;
  run.steps.push(run.opened, after);
  await p.screenshot({ path: OUT.replace(/\.json$/, "_after_start.png"), fullPage: true });
  run.api_on_start = run.api.filter((a) => a.method === "POST");
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  await b.close();
  console.log("start_pressed=" + pressed + " disabled=" + disabled);
  console.log("POSTS_on_start=" + JSON.stringify(run.api_on_start.map((a) => a.status + " " + a.url)));
  console.log("SHEET_AFTER_START:\n" + after.text.slice(0, 700));
})().catch((e) => { console.error("AISTART_FAIL " + e); process.exit(1); });