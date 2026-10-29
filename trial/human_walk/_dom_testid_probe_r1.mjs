import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const page = browser.contexts()[0].pages()[0];
const out = await page.evaluate(() => ({
  shape: `${window.innerWidth}x${window.innerHeight}`,
  scrollY: Math.round(window.scrollY),
  prefixed: Array.from(document.querySelectorAll('[data-testid^="rev-mission-layer-"]')).map(n => ({
    id: n.getAttribute("data-testid"), tag: n.tagName,
    display: getComputedStyle(n).display, y: Math.round(n.getBoundingClientRect().y),
    h: Math.round(n.getBoundingClientRect().height),
  })),
  tabRow: (() => { const n = document.querySelector(".cn-mission-layer-tabs"); return n ? {display: getComputedStyle(n).display, position: getComputedStyle(n).position, top: getComputedStyle(n).top, y: Math.round(n.getBoundingClientRect().y)} : null; })(),
  buttons: document.querySelectorAll("button").length,
  h1: (document.querySelector("h1")?.textContent || "").trim().slice(0, 30),
}));
console.log(JSON.stringify(out, null, 1));
await browser.close().catch(() => undefined);
