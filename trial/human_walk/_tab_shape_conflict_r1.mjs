/**
 * Why did first_tap_layers_r1 say "tabs:3" from one evaluate and "ABSENT" from the next?
 * Both readings claim the same page, so one of them is lying.  This does the same sequence in ONE evaluate:
 * resize to 360x780, reload, wait, then count the prefix AND look up each exact testid, plus print what the
 * document title/heading says, so the answer is a fact about the page rather than about my reading order.
 */
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const pages = browser.contexts()[0].pages();
console.log(`PAGES ${pages.length}`);
const page = pages[0];
await page.setViewportSize({ width: 360, height: 780 });
await page.reload({ waitUntil: "domcontentloaded", timeout: 30000 }).catch((e) => console.log("RELOAD_FAIL", e.message.slice(0, 60)));
await page.waitForTimeout(3000);
const one = await page.evaluate(() => {
  const ids = ["rev-mission-layer-map", "rev-mission-layer-timeline", "rev-mission-layer-agent"];
  const byPrefix = Array.from(document.querySelectorAll('[data-testid^="rev-mission-layer-"]')).map((n) => n.getAttribute("data-testid"));
  const rows = Array.from(document.querySelectorAll(".cn-mission-layer-tabs")).map((n) => {
    const style = getComputedStyle(n);
    const box = n.getBoundingClientRect();
    return { display: style.display, position: style.position, top: style.top, zIndex: style.zIndex,
      y: Math.round(box.y), h: Math.round(box.height),
      children: n.querySelectorAll("button").length };
  });
  const exact = ids.map((id) => {
    const n = document.querySelector(`[data-testid="${id}"]`);
    if (!n) return { id, found: false };
    const box = n.getBoundingClientRect();
    const cx = Math.round(box.left + box.width / 2);
    const cy = Math.round(box.top + box.height / 2);
    const top = document.elementFromPoint(cx, cy);
    return { id, found: true, y: Math.round(box.y), h: Math.round(box.height), centre: [cx, cy],
      visible: box.width > 0 && box.height > 0, pressed: n.getAttribute("aria-pressed"),
      covers_it: Boolean(top && !n.contains(top)),
      topmost: String(top?.getAttribute?.("data-testid") || top?.className || top?.tagName || "(none)").slice(0, 40) };
  });
  return { shape: `${window.innerWidth}x${window.innerHeight}`, scrollY: Math.round(window.scrollY),
    bodyChildren: document.body.children.length, iframes: document.querySelectorAll("iframe").length,
    byPrefix, rows, exact, h1: (document.querySelector("h1")?.textContent || "").trim().slice(0, 24),
    dock: Boolean(document.querySelector(".rev-mission-chat-dock")) };
});
console.log(JSON.stringify(one, null, 1));
await browser.close().catch(() => undefined);
