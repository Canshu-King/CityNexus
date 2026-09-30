const { chromium } = require("playwright");
const BASE = process.env.CNX_BASE || "http://localhost:4491";
const KEY = "citynexus.v8.map_pick.22222222-2222-4222-8222-222222222222";
const ID = "3a58c470-524c-5854-aa39-6c37a350eb80";
const read = (page) => page.evaluate(() => Array.from(document.querySelectorAll(".v9-map-marker")).map((e) => (e.textContent || "").trim() + ":" + (e.getAttribute("aria-pressed") || "-") + (e.classList.contains("selected") ? "*" : "")));
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript(([k, v]) => { localStorage.setItem("citynexus.locale", "zh-CN"); localStorage.setItem(k, v); }, [KEY, ID]);
  await page.goto(BASE + "/v8/map", { waitUntil: "domcontentloaded" });
  const entry = page.getByRole("button", { name: /封存的演示|sealed demo/i }).first();
  if (await entry.isVisible({ timeout: 6000 }).catch(() => false)) { await entry.click(); await page.waitForTimeout(2000); await page.goto(BASE + "/v8/map"); }
  await page.waitForSelector(".v9-map-marker", { timeout: 40000 });
  await page.waitForTimeout(3000);
  const steps = { after_boot_restore: await read(page) };
  const click = async (label) => {
    const h = await page.evaluateHandle((l) => Array.from(document.querySelectorAll(".v9-map-marker")).find((e) => (e.textContent || "").trim() === l) || null, label);
    const el = h.asElement(); if (!el) return "no-element";
    await el.click(); await page.waitForTimeout(1200); return await read(page);
  };
  steps.after_click_2 = await click("2");
  steps.after_click_1 = await click("1");
  const glass = await page.locator('[data-testid="v8-map-selected-stop"]').first().textContent();
  steps.glass_now = (glass || "").replace(/\s+/g, " ").trim();
  console.log(JSON.stringify(steps, null, 1));
  await b.close();
})().catch((e) => { console.error("FAIL", String(e)); process.exit(1); });
