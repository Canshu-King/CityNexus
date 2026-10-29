/**
 * Is the fixed chat dock taller than the space the screen reserves for it?
 *
 * Two presses in a row (replan-probe-4 and -5 logs, 2026-10-24) hit a TEXTAREA where a departure-card
 * button was: the probe asked `document.elementFromPoint(centre)` and got the composer back.  That can
 * mean two different things, and only one of them is my instrument's fault:
 *   - the card was mid-scroll, so the traveller would simply scroll and hit it; or
 *   - the pane's reserved bottom clearance is smaller than the band the dock actually occupies, so
 *     even at maximum scroll the last control of a card stays under the dock.
 * This measures the second question directly: scroll the pane's own scroller to its end, then read the
 * dock's rectangle and the button's centre against it, and report which rule supplies the clearance.
 *
 * Nothing is pressed, seeded or written here: this is a reading of layout.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const ORIGIN = process.env.RECOV_ORIGIN || "http://127.0.0.1:14492";
const LOG = path.join(SHOTS, process.env.LOG_NAME || "dock-clearance-probe-1-log.txt");
const lines = [];
const say = (text) => { lines.push(text); console.log(text); fs.writeFileSync(LOG, lines.join("\n") + "\n"); };
const flat = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 30000 });
const context = browser.contexts()[0];
const pages = context.pages().filter((row) => row.url().startsWith(ORIGIN));
if (pages.length !== 1) { say(`REFUSE same_origin_tabs=${pages.length} -- 一源多枚就没法说这屏是谁的`); process.exit(1); }
const page = pages[0];
await page.bringToFront();
await page.setViewportSize({ width: Number(process.env.VP_W || 390), height: Number(process.env.VP_H || 844) });
await page.waitForTimeout(1500);

// Open the timeline layer the way the traveller does, so the departure card is the one on screen.
await page.getByRole("tab", { name: /日程/ }).first().click({ timeout: 8000 })
  .catch((e) => say(`LAYER_TAB_ERR ${flat(e.message).slice(0, 70)}`));
await page.waitForTimeout(1200);

const reading = await page.evaluate(() => {
  const dock = document.querySelector(".rev-mission-chat-dock");
  if (!dock) return { error: "no dock on this screen" };
  const dockRect = dock.getBoundingClientRect();
  // The scroller is the element that actually scrolls: the one whose content overflows, nearest the card.
  // A textarea scrolls its own text, and the composer is one: that is not the pane scrolling, and
  // measuring against it says nothing about the dock.  Only block-level overflow counts.
  const candidates = [...document.querySelectorAll("*")].filter((node) => {
    const style = getComputedStyle(node);
    const tag = node.tagName;
    return !["TEXTAREA", "INPUT", "SELECT"].includes(tag)
      && /auto|scroll/.test(style.overflowY) && node.scrollHeight - node.clientHeight > 24;
  });
  const inner = candidates.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight))[0];
  const doc = document.scrollingElement || document.documentElement;
  // The document is the traveller's scroll whenever it overflows; otherwise the pane that does.
  const scroller = doc.scrollHeight - doc.clientHeight > 24 ? doc : (inner || doc);
  const before = scroller.scrollTop;
  scroller.scrollTop = scroller.scrollHeight;
  const controls = [...document.querySelectorAll(".rev-v3-departure button")].map((node) => {
    const rect = node.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return {
      label: (node.innerText || "").replace(/\s+/g, " ").trim().slice(0, 28),
      centre: [Math.round(cx), Math.round(cy)],
      topmost: top ? top.tagName : "(none)",
      under_dock: top ? dock.contains(top) : true,
      hits_it: top === node || (top ? node.contains(top) : false),
      gap_to_dock_top: Math.round(dockRect.top - cy),
      disabled: Boolean(node.disabled),
    };
  });
  const answered = {
    viewport: [window.innerWidth, window.innerHeight],
    dock: { top: Math.round(dockRect.top), bottom: Math.round(dockRect.bottom), height: Math.round(dockRect.height) },
    scroller: { tag: scroller.tagName, cls: String(scroller.className).slice(0, 60), scrollTop_before: Math.round(before),
                scrollTop_after: Math.round(scroller.scrollTop),
                scrollHeight: Math.round(scroller.scrollHeight), clientHeight: Math.round(scroller.clientHeight) },
    content_padding: [...document.querySelectorAll(".rev-firstlook-content, .rev-v3-departure, .cn-mission-os, .rev-mission-layer-timeline")]
      .map((node) => ({ cls: String(node.className).slice(0, 46),
                        padding_bottom: getComputedStyle(node).paddingBottom,
                        position: getComputedStyle(node).position })),
    controls,
  };
  scroller.scrollTop = before;
  return answered;
});
say(`AT_MAX_SCROLL ${JSON.stringify(reading)}`);
await page.screenshot({ path: path.join(SHOTS, "dock-clearance-01-at-bottom.png") }).catch(() => undefined);
say(`SHOT dock-clearance-01-at-bottom.png bytes=${fs.existsSync(path.join(SHOTS, "dock-clearance-01-at-bottom.png"))
  ? fs.statSync(path.join(SHOTS, "dock-clearance-01-at-bottom.png")).size : 0}`);
say("NOTE this instrument presses nothing; it only scrolls the pane's own scroller and reads rectangles");
say("DONE tab left open");
await browser.close().catch(() => undefined);
