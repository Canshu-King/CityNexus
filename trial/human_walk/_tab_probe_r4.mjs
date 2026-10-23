import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
for (const [i, tab] of context.pages().entries()) {
  const info = await tab.evaluate(() => ({
    cockpit: document.querySelectorAll('[data-testid^="rev-mission-layer-"]').length,
    welcome: Boolean(document.querySelector(".rev-mobile-welcome, [data-testid='rev-mobile-welcome']")),
    goalBox: (() => { const t = document.querySelector("#rev-mission-chat-input"); return t ? String(t.value).slice(0, 24) : "(none)"; })(),
    bearer_in_session: Boolean(sessionStorage.getItem("citynexus.trial.traveler_token")),
    dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
    slots: document.querySelectorAll(".rev-goal-draft-slot").length,
    scrollY: Math.round(window.scrollY),
    w: window.innerWidth, h: window.innerHeight,
  })).catch((e) => ({ err: e.message.slice(0, 60) }));
  console.log(`TAB_${i}`, JSON.stringify(info));
}
await browser.close().catch(() => undefined);
