import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
for (const [i, tab] of context.pages().entries()) {
  const pointer = await tab.evaluate(() => { try { return localStorage.getItem("citynexus.revolution.firstlook.journey") || "(none)"; } catch { return "(err)"; } }).catch(() => "(evalfail)");
  const ids = await tab.evaluate(() => ({ n: document.querySelectorAll("[data-testid]").length, list: [...document.querySelectorAll("[data-testid]")].slice(0, 8).map((x) => x.getAttribute("data-testid")), body: document.body.innerText.replace(/\s+/g, " ").slice(0, 60) })).catch((e) => ({ n: -1, list: [], body: "(unreadable) " + e.message.slice(0, 40) }));
  console.log(`TAB_${i} url=${tab.url()} pointer=${String(pointer).slice(0, 60)} testids=${ids.n} list=${JSON.stringify(ids.list)} body=${ids.body}`);
}
await browser.close().catch(() => undefined);
