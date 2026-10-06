/* Capture the real /experience payload during the manual booking so the day.activities strings are
 * ground truth (not inferred from rendered text). Writes the first selected-option day.activities it sees. */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt22\\frontend\\node_modules\\playwright");
const fs = require("fs");
(async () => {
  const OUT = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/walk_day_tokens.json";
  let captured = null;
  const b = await chromium.launch();
  const ctx = await b.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 },
    isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  p.on("response", async (r) => {
    if (captured || !r.url().includes("/experience")) return;
    try {
      const j = await r.json();
      const opts = j.options || [];
      const sel = opts.find((o) => o.id === j.selected_option_id) || opts[0];
      if (sel && (sel.days || []).length) {
        captured = { url: r.url().replace(/[0-9a-f-]{36}/, "<journey>"),
          selected_option_id: sel.id,
          days: sel.days.map((d) => ({ day: d.day, anchor: d.anchor, mode: d.mode, activities: d.activities })) };
      }
    } catch (e) { /* not json or no days */ }
  });
  await p.goto("http://127.0.0.1:4881", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1500);
  // manual fill
  await p.locator("[data-testid='trial-city']").fill("北京");
  await p.locator("[data-testid='trial-arrival']").fill("北京站");
  await p.locator("[data-testid='trial-departure']").fill("天安门");
  await p.waitForTimeout(600);
  for (let i = 0; i < 4; i++) {
    const btn = p.locator("button").filter({ hasText: /下一步|确认创建|创建行程|完成|生成/ }).first();
    if (!(await btn.count()) || await btn.isDisabled()) break;
    await btn.click(); await p.waitForTimeout(1600);
  }
  await p.waitForTimeout(1500);
  fs.writeFileSync(OUT, JSON.stringify({ captured: captured }, null, 1));
  console.log("CAPTURED:", JSON.stringify(captured ? captured.days.slice(0, 2) : null, null, 1));
  await b.close();
})().catch((e) => { console.error("CAPTURE_FAIL " + e); process.exit(1); });