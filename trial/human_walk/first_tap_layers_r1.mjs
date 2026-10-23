/**
 * P0-1 acceptance -- every key entry on the first screen must land on the FIRST tap.
 *
 * The ruling names three shapes (360x780, 390x844, 430x932), each twice: cold first screen and after the page
 * has been scrolled.  A tap is done with the real mouse at the element's own centre, so an overlapping sticky
 * row cannot be papered over by Playwright's forced click; `covers_it` from elementFromPoint is printed for the
 * same reason (it names the blocker instead of leaving a bare red).
 *
 * "cold" prefers a real reload of the live tab -- sessionStorage (the traveller's bearer) survives a reload in
 * the same tab, so the cockpit can come back genuinely cold.  If the reload does not restore three layer tabs
 * the arm degrades to scroll-to-top and says so; a silent substitution would be a fake cold start.
 *
 * Read-only apart from clicks and scrolling in the tab it already owns.  No storage writes, no API calls.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.TAP_LOG || "first-tap-layers-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const SHAPES = ["360x780", "390x844", "430x932"];
const TABS = [
  ["rev-mission-layer-map", "地图"],
  ["rev-mission-layer-timeline", "日程"],
  ["rev-mission-layer-agent", "对话"],
  ["rev-mission-layer-map", "返回"],
];

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();

const markOf = (page) => page.evaluate(() => ({
  tabs: document.querySelectorAll('[data-testid^="rev-mission-layer-"]').length,
  dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
  shape: `${window.innerWidth}x${window.innerHeight}`,
  scrollY: Math.round(window.scrollY),
  pointer: (() => { try { return String(localStorage.getItem("citynexus.revolution.firstlook.journey") || ""); } catch { return ""; } })(),
})).catch(() => null);

let page = null;
const qualified = [];
for (const [index, candidate] of context.pages().entries()) {
  const mark = await markOf(candidate);
  say(`CANDIDATE_${index} url=${candidate.url()} mark=${JSON.stringify({ ...mark, pointer: flat(mark?.pointer).slice(0, 8) })}`);
  if (mark && mark.tabs === 3) qualified.push(candidate);
}
if (qualified.length !== 1) {
  say(`REFUSE qualifying_tabs=${qualified.length} -- 指针按源共享（_tab_probe_r4 实测），两页都挂驾驶舱时我不知道该按哪一页，按下就是污染别人的走查`);
  await browser.close().catch(() => undefined);
  process.exit(0);
}
page = qualified[0];
const journey0 = flat(await page.evaluate(() => localStorage.getItem("citynexus.revolution.firstlook.journey")));
say(`JOURNEY_POINTER ${journey0.slice(0, 8)} (canary id, first 8 chars)`);

const probe = (id) => page.evaluate((testId) => {
  const node = document.querySelector(`[data-testid="${testId}"]`);
  if (!node) return { present: false };
  const box = node.getBoundingClientRect();
  const cx = Math.round(box.left + box.width / 2);
  const cy = Math.round(box.top + box.height / 2);
  const top = document.elementFromPoint(cx, cy);
  const label = (top?.getAttribute("data-testid") || top?.className || top?.tagName || "(none)").toString();
  return { present: true, centre: [cx, cy], y: Math.round(box.y), h: Math.round(box.height),
    covers_it: Boolean(top && !node.contains(top)), topmost: flat(label).slice(0, 46),
    pressed: node.getAttribute("aria-pressed"), scrollY: Math.round(window.scrollY) };
}, id).catch((e) => ({ error: flat(e.message).slice(0, 60) }));

for (const shape of SHAPES) {
  const [w, h] = shape.split("x").map(Number);
  await page.setViewportSize({ width: w, height: h }).catch((e) => say(`VIEWPORT_FAIL ${shape} ${flat(e.message).slice(0, 60)}`));
  for (const arm of ["cold", "scrolled"]) {
    let used = "reload";
    await page.reload({ waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => undefined);
    await page.waitForTimeout(2500);
    let mark = await markOf(page);
    if (!mark || mark.tabs !== 3) {
      used = "scroll_to_top_fallback";
      await page.evaluate(() => window.scrollTo(0, 0)).catch(() => undefined);
      await page.waitForTimeout(700);
      mark = await markOf(page);
    }
    if (arm === "scrolled") {
      await page.evaluate(() => window.scrollBy(0, 520)).catch(() => undefined);
      await page.waitForTimeout(600);
    }
    const shapeMark = await markOf(page);
    say(`SHAPE ${shape} ARM ${arm} VIA ${used} mark=${JSON.stringify({ ...shapeMark, pointer: flat(shapeMark?.pointer).slice(0, 8) })}`);
    if (!shapeMark || shapeMark.tabs !== 3) { say(`SKIP_${shape}_${arm} layer tabs=${shapeMark?.tabs ?? "null"}`); continue; }

    let firstTapSuccess = 0;
    for (const [id, label] of TABS) {
      const before = await probe(id);
      if (!before.present) { say(`TAP ${label} ${id} ABSENT`); continue; }
      await page.mouse.click(before.centre[0], before.centre[1]);
      await page.waitForTimeout(650);
      const after = await probe(id);
      const activated = after.pressed === "true";
      if (label !== "返回" && activated) firstTapSuccess += 1;
      say(`TAP ${label} ${id} before=${JSON.stringify(before)} after_pressed=${after.pressed} FIRST_TAP=${activated ? "HIT" : "MISS"}`);
      const shot = `firsttap-${shape}-${arm}-${id.replace("rev-mission-layer-", "")}.png`;
      await page.screenshot({ path: path.join(OUT, shot), type: "png" }).catch(() => undefined);
      say(`SHOT ${shot}`);
    }
    say(`FIRST_TAP_SUCCESS=${firstTapSuccess}/3 shape=${shape} arm=${arm}`);
    const kept = flat(await page.evaluate(() => localStorage.getItem("citynexus.revolution.firstlook.journey")));
    say(`JOURNEY_KEPT ${kept === journey0 ? "same" : "DIFFERENT"} pointer=${kept.slice(0, 8)}`);
  }
}
say("NOTE 只在本工具已经选中的那一枚标签页里点击与滚动；未动 storage、未调接口、未改视口以外的设置");
await browser.close().catch(() => undefined);
