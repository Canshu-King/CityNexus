/* ORD-0504 · final on-screen verification after the button was moved off the primary style:
 * the refusal must still offer the way to the paste door, and the row must hold one primary. */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const PATCHED = "http://127.0.0.1:8793";
const BACKEND = "http://127.0.0.1:8790";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0504";
(async () => {
  const journeys = await (await fetch(`${BACKEND}/api/v1/journeys`)).json();
  const fz = journeys.find((j) => j.city_code === "CN-FUZHOU") || journeys[0];
  const browser = await chromium.launch();
  const report = { journey: fz.id, city: fz.city_code, shapes: {} };
  for (const shape of ["phone", "desktop"]) {
    const ctx = await browser.newContext(shape === "phone"
      ? { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN" }
      : { viewport: { width: 1280, height: 900 }, locale: "zh-CN" });
    const p = await ctx.newPage();
    await p.goto(`${PATCHED}/v8/${fz.id}`, { waitUntil: "domcontentloaded" });
    await p.waitForTimeout(2400);
    await p.locator('[data-testid="hub-plan-with-ai"]').click({ timeout: 8000 });
    await p.waitForTimeout(1200);
    await p.locator('[data-testid="plan-ai-sheet"] textarea').fill("帮我排一天，想喝咖啡");
    await p.locator('[data-testid="plan-ai-sheet"] button', { hasText: /开始规划/ }).click({ timeout: 8000 });
    const deadline = Date.now() + 150000;
    while (Date.now() < deadline) {
      if ((await p.locator('[data-testid="plan-ai-import-entry"]').count()) > 0) break;
      await p.waitForTimeout(1500);
    }
    const counts = await p.evaluate(() => {
      const q = (s) => Array.from(document.querySelectorAll(s)).filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
      const entry = document.querySelector('[data-testid="plan-ai-import-entry"]');
      return {
        visible_primary_buttons: q(".v8-primary-button, .v8-primary").length,
        entry_present: !!entry,
        entry_classes: entry ? entry.className : null,
        entry_label: entry ? (entry.textContent || "").replace(/\s+/g, " ").trim() : null,
        count_line: (document.querySelector('[data-testid="plan-ai-catalogue-count"]') || {}).innerText || null,
        next_step: (document.querySelector('[data-testid="plan-ai-next-step"]') || {}).innerText || null,
      };
    });
    if (counts.entry_present) {
      await p.locator('[data-testid="plan-ai-import-entry"]').click({ timeout: 8000 });
      await p.waitForTimeout(2600);
      counts.after_press = { url: p.url(), poi_panel: await p.locator('[data-testid="poi-import"]').count() };
    }
    const file = path.join(OUT, `final_${shape}.png`);
    await p.screenshot({ path: file, fullPage: true });
    counts.shot = { file: file.split(path.sep).join("/"), bytes: fs.statSync(file).size };
    report.shapes[shape] = counts;
    await ctx.close();
  }
  await browser.close();
  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `verify_final_r1_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.split(path.sep).join("/"), phone_primaries: report.shapes.phone.visible_primary_buttons, desktop_entry: report.shapes.desktop.after_press }));
})().catch((e) => { console.error("FINAL_VERIFY_FAILED", e.message); process.exit(1); });
