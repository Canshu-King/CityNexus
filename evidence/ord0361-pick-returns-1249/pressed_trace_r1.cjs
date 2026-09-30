const { chromium } = require("playwright");
const BASE = process.env.CNX_BASE || "http://localhost:4491";
const KEY = "citynexus.v8.map_pick.22222222-2222-4222-8222-222222222222";
const ID = "3a58c470-524c-5854-aa39-6c37a350eb80";
const read = (page) => page.evaluate(() => Array.from(document.querySelectorAll(".v9-map-marker")).map((e) => ({
  t: (e.textContent || "").trim(), p: e.getAttribute("aria-pressed"), sel: e.classList.contains("selected"),
  label: e.getAttribute("aria-label") })));
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript(([k, v]) => { localStorage.setItem("citynexus.locale", "zh-CN"); localStorage.setItem(k, v); }, [KEY, ID]);
  await page.goto(BASE + "/v8/map", { waitUntil: "domcontentloaded" });
  const entry = page.getByRole("button", { name: /封存的演示|sealed demo/i }).first();
  if (await entry.isVisible({ timeout: 6000 }).catch(() => false)) { await entry.click(); await page.waitForTimeout(2000); await page.goto(BASE + "/v8/map"); }
  await page.waitForSelector(".v9-map-marker", { timeout: 40000 });
  const out = {};
  for (const ms of [0, 1500, 3000, 6000]) {
    if (ms) await page.waitForTimeout(ms);
    out["at_" + ms] = { markers: await read(page), glass: await page.locator('[data-testid="v8-map-selected-stop"]').first().textContent().then((t) => (t || "").replace(/\s+/g, " ").trim()).catch(() => null) };
  }
  console.log(JSON.stringify(out, null, 1));
  await b.close();
})().catch((e) => { console.error("FAIL", String(e)); process.exit(1); });
