/**
 * P0-1 first-tap proof, r2 -- r1's "FIRST_TAP_SUCCESS=0/3" was my instrument lying, and this file says how.
 *
 * r1 (trial/human_walk/first_tap_layers_r1.mjs, log first-tap-layers-1.txt) printed `TAP … ABSENT` for all three
 * tabs while its own `markOf` said the row exists.  Cause: probe() returns {error} when evaluate throws, and r1
 * tested only `!before.present`, so a destroyed execution context (reload still in flight) read as "the button is
 * not there".  A swallowed cause is worse than a silent ruler, so r2 (1) never folds an error into absence,
 * (2) waits for the row to exist instead of sleeping, and (3) classifies where the row actually is before it
 * presses anything: `on_screen` / `below_fold` / `above_viewport`.
 *
 * Why classification matters for this ruling: 「第一次就点中」 only means something if the entry is on the screen
 * the traveller is looking at.  At 360/390/430 wide, cold (scrollY=0), the layer switcher sits far down the page
 * behind the hero and the draft, so a real traveller scrolls first; counting that as a failed tap would be a fake
 * red, and pretending it away would be a fake green.  r2 reports the geometry, taps only what is on screen, and
 * names the blocker with elementFromPoint when a tap misses (the original defect was 遮挡, not absence).
 *
 * Viewports, arms and the tap order are what the ruling names: 360x780, 390x844, 430x932, cold and after page
 * scroll, 地图→日程→对话→返回, one press each, same Journey required.  Real mouse presses at the element's own
 * centre; no forced clicks, no storage writes, no API shortcuts.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.TAP_LOG || "first-tap-layers-2.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const SHAPES = ["360x780", "390x844", "430x932"];
const IDS = ["rev-mission-layer-map", "rev-mission-layer-timeline", "rev-mission-layer-agent"];
const LABELS = { "rev-mission-layer-map": "地图", "rev-mission-layer-timeline": "日程", "rev-mission-layer-agent": "对话" };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();

const rowState = (page) => page.evaluate((ids) => {
  const viewportH = window.innerHeight;
  const nodes = ids.map((id) => document.querySelector(`[data-testid="${id}"]`));
  const found = nodes.filter(Boolean).length;
  const box = nodes[0] ? nodes[0].getBoundingClientRect() : null;
  return { found, viewportH, scrollY: Math.round(window.scrollY),
    rowY: box ? Math.round(box.y) : null, rowBottom: box ? Math.round(box.bottom) : null,
    pointer: (() => { try { return flat(localStorage.getItem("citynexus.revolution.firstlook.journey")).slice(0, 8); } catch { return ""; } })() };
}, IDS).catch((error) => ({ error: flat(error.message).slice(0, 90) }));

const qualified = [];
for (const [index, candidate] of context.pages().entries()) {
  const state = await rowState(candidate);
  say(`CANDIDATE_${index} url=${candidate.url()} state=${JSON.stringify(state)}`);
  if (state && state.found === 3) qualified.push(candidate);
}
if (qualified.length !== 1) {
  say(`REFUSE qualifying_tabs=${qualified.length} -- 指针按源共享（_tab_probe_r4 实测），两页都挂驾驶舱时按哪一页都不该由我猜`);
  await browser.close().catch(() => undefined);
  process.exit(0);
}
const page = qualified[0];
const journey0 = (await rowState(page)).pointer;
say(`JOURNEY_POINTER_CANARY ${journey0}`);

for (const shape of SHAPES) {
  const [w, h] = shape.split("x").map(Number);
  await page.setViewportSize({ width: w, height: h }).catch((e) => say(`VIEWPORT_FAIL ${shape} ${flat(e.message).slice(0, 60)}`));
  await page.reload({ waitUntil: "domcontentloaded", timeout: 40000 }).catch((e) => say(`RELOAD_FAIL ${shape} ${flat(e.message).slice(0, 60)}`));
  await page.waitForFunction((ids) => ids.every((id) => document.querySelector(`[data-testid="${id}"]`)), IDS, { timeout: 25000 })
    .catch((e) => say(`WAIT_ROW_FAIL ${shape} ${flat(e.message).slice(0, 70)}`));
  for (const arm of ["cold_top", "after_scroll"]) {
    if (arm === "cold_top") await page.evaluate(() => window.scrollTo(0, 0));
    else await page.evaluate(() => window.scrollBy(0, 600));
    await page.waitForTimeout(900);
    const state = await rowState(page);
    const where = state.error ? "ERROR"
      : state.rowY === null ? "NO_ROW"
      : (state.rowY >= 0 && state.rowBottom <= state.viewportH) ? "on_screen"
      : state.rowY > state.viewportH ? "below_fold" : "above_viewport";
    say(`SHAPE ${shape} ARM ${arm} where=${where} state=${JSON.stringify(state)}`);
    if (where !== "on_screen") { say(`NOT_TAPPED ${shape}/${arm} -- 键不在这一屏 visible 范围内；这一档不计进 FIRST_TAP，也不许写成人能点中`); continue; }

    let hit = 0;
    for (const id of [...IDS, "rev-mission-layer-map"]) {
      const probe = await page.evaluate((testId) => {
        const node = document.querySelector(`[data-testid="${testId}"]`);
        if (!node) return { present: false };
        const box = node.getBoundingClientRect();
        const cx = Math.round(box.left + box.width / 2);
        const cy = Math.round(box.top + box.height / 2);
        const top = document.elementFromPoint(cx, cy);
        return { present: true, centre: [cx, cy], y: Math.round(box.y), pressed: node.getAttribute("aria-pressed"),
          covers_it: Boolean(top && !node.contains(top)),
          topmost: String(top?.getAttribute?.("data-testid") || top?.className || top?.tagName || "(nothing here)").slice(0, 44) };
      }, id).catch((error) => ({ error: flat(error.message).slice(0, 80) }));
      if (probe.error) { say(`TAP_ERROR ${id} ${probe.error} -- 这是仪表坏了，不是屏上没这个键`); continue; }
      if (!probe.present) { say(`TAP_ABSENT ${id} -- 逐字查过 data-testid 确实没有`); continue; }
      const wasReturn = id === "rev-mission-layer-map" && hit > 0;
      await page.mouse.click(probe.centre[0], probe.centre[1]);
      await page.waitForTimeout(700);
      const after = await page.evaluate((testId) => {
        const node = document.querySelector(`[data-testid="${testId}"]`);
        return { pressed: node?.getAttribute("aria-pressed") ?? null, scrollY: Math.round(window.scrollY) };
      }, id).catch(() => ({ pressed: null }));
      const activated = after.pressed === "true";
      if (!wasReturn && activated) hit += 1;
      say(`TAP ${id} first_press=${!wasReturn} covers_it=${probe.covers_it} topmost=${probe.topmost} centre=${JSON.stringify(probe.centre)} after_pressed=${after.pressed} RESULT=${activated ? "HIT" : "MISS"}`);
      const shot = `firsttap2-${shape}-${arm}-${id.replace("rev-mission-layer-", "")}.png`;
      await page.screenshot({ path: path.join(OUT, shot), type: "png" }).catch(() => undefined);
      say(`SHOT ${shot}`);
    }
    say(`FIRST_TAP_SUCCESS=${hit}/3 shape=${shape} arm=${arm} (only where=on_screen counted)`);
    const kept = (await rowState(page)).pointer;
    say(`JOURNEY_KEPT ${kept === journey0 ? "same" : "DIFFERENT"} pointer=${kept}`);
  }
}
say("NOTE 动作只有换视口、刷新、滚动与在中心点上的真鼠标点击；没写 storage、没调接口、没起新标签页");
await browser.close().catch(() => undefined);
