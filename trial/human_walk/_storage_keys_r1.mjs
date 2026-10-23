import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const page = browser.contexts()[0].pages()[0];
const out = await page.evaluate(() => ({
  url: location.origin,
  localKeys: Object.keys(localStorage).sort(),
  sessionKeys: Object.keys(sessionStorage).sort(),
  journeyish: Object.keys(localStorage).filter((k) => /journey|revolution|v8/i.test(k)).map((k) => `${k}=${String(localStorage.getItem(k)).slice(0, 60)}`),
}));
console.log(JSON.stringify(out, null, 1));
await browser.close().catch(() => undefined);
