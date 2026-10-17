/* Issue #27 的 live 臂：手机链真地址、真后端、真刷新，不用任何 route 桩。
 *
 * 它回答的是模拟双成员那套答不了的两个问题：
 *   一、真服务器答过之后，盘上到底有没有留下那两把旧键；
 *   二、刷新之后屏幕上剩下什么话——是"没有可恢复的历史"，还是把空态演成还在分析。
 *
 * 跑法：node _cmdr_qoder27_live_reload_r1.cjs
 * 依赖：指挥线自己的 :4783（静态 dist + /api 反代到 :8011），不碰 :8000/:4781/:4782/:8693。
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const BASE = process.env.CNX_LIVE_BASE ?? "http://127.0.0.1:4783";
const JOURNEY = process.env.CNX_LIVE_JOURNEY ?? "22222222-2222-4222-8222-222222222222";
const PREFIX = /^citynexus\.(copilot\.history|native-hermes\.timeline)\./;

async function openCopilot(page) {
  await page.evaluate(() => {
    const e = document.querySelector('[data-testid="v8-mobile-menu"]');
    if (e) e.click();
  });
  await page.waitForTimeout(700);
  await page.evaluate(() => {
    const e = document.querySelector('[data-testid="v8-drawer-entry-agent"]');
    if (e) e.click();
  });
  await page.waitForTimeout(1400);
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  await ctx.addInitScript((jid) => {
    window.localStorage.setItem("citynexus.v8.journey_id", jid);
    window.localStorage.setItem("citynexus.theme", "light");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
  }, JOURNEY);
  const page = await ctx.newPage();

  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const health = await page.evaluate(async () => {
    const r = await fetch("/api/v1/health");
    return { status: r.status, body: await r.json() };
  });
  console.log("health http_status=" + health.status + " ai=" + health.body.ai);
  await openCopilot(page);
  const dock = page.getByTestId("v15-copilot");
  const dockVisible = await dock.isVisible().catch(() => false);
  console.log("copilot visible=" + dockVisible);

  await page.getByTestId("v15-copilot-input").fill("帮我核对今天的安排");
  const stamp = Date.now();
  await page.getByTestId("v15-copilot-submit").click();
  await page.waitForTimeout(6000);
  const afterSend = await page.evaluate(() => Object.keys(window.localStorage).filter((k) => /^citynexus\.(copilot\.history|native-hermes\.timeline)\./.test(k)));
  const bodyBefore = await page.locator('[data-testid="v15-copilot"]').innerText();
  await page.screenshot({ path: "qoder27_evidence/live-aftersend.png" });
  console.log("keys_after_real_send=" + JSON.stringify(afterSend));
  console.log("reply_rendered=" + (bodyBefore.includes("帮我核对今天的安排") ? "yes" : "no"));

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(2200);
  await openCopilot(page);
  await page.waitForTimeout(1500);
  const bodyAfter = await page.locator('[data-testid="v15-copilot"]').innerText();
  const keysAfterReload = await page.evaluate(() => Object.keys(window.localStorage).filter((k) => /^citynexus\.(copilot\.history|native-hermes\.timeline)\./.test(k)));
  await page.screenshot({ path: "qoder27_evidence/live-afterreload.png" });
  console.log("keys_after_reload=" + JSON.stringify(keysAfterReload));
  console.log("transcript_survives_reload=" + (bodyAfter.includes("帮我核对今天的安排") ? "yes (缺陷)" : "no"));
  console.log("dock_text_after_reload=" + JSON.stringify(bodyAfter.replace(/\s+/g, " ").slice(0, 260)));
  console.log("claims_still_working=" + /正在核对|正在为你处理|分析中/.test(bodyAfter));
  await browser.close();
  console.log("done at " + new Date(stamp).toISOString());
})();
