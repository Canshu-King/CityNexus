/**
 * P0-1 first-tap proof, r3 -- r2 threw away its own journey line, and this file says how.
 *
 * r2 (first-tap-layers-2.txt) printed `pointer=""` on every line and therefore `JOURNEY_KEPT same` from two
 * EMPTY strings: inside page.evaluate I called `flat()`, a helper that only exists on the Node side.  The thrown
 * ReferenceError was swallowed by my own try/catch, so the "same Journey" half of the acceptance was vacuous --
 * exactly the failure mode I am not allowed to publish.  r3 normalises the string inside the page function, and
 * prints the origin so the key names can be checked against _storage_keys_r1.mjs.
 *
 * r2's tap numbers still stand (they came from aria-pressed, not from the broken field): 360x780 and 390x844
 * cold-at-top gave FIRST_TAP_SUCCESS=3/3 with covers_it=false on every press.  r3 re-measures all three shapes
 * and adds one honesty fix: the "after scroll" arm used to scroll from wherever the previous arm left the page
 * (the app's own scrollIntoView moves it), so it now always starts from scrollTo(0,0) and then scrolls 600 px.
 *
 * Counting rule kept from r2: a tap only counts when the switcher row is genuinely on this screen.  If the row
 * is above the viewport or below the fold the arm prints where it is and does NOT claim a first-tap pass.
 * Real mouse presses at the element's own centre; no forced clicks, no storage writes, no API calls.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.TAP_LOG || "first-tap-layers-3.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const SHAPES = ["360x780", "390x844", "430x932"];
const IDS = ["rev-mission-layer-map", "rev-mission-layer-timeline", "rev-mission-layer-agent"];

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();

const rowState = (page) => page.evaluate((ids) => {
  const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const nodes = ids.map((id) => document.querySelector(`[data-testid="${id}"]`));
  const box = nodes[0] ? nodes[0].getBoundingClientRect() : null;
  let pointer = "(err)";
  try { pointer = norm(localStorage.getItem("citynexus.revolution.firstlook.journey")).slice(0, 40) || "(empty)"; } catch { pointer = "(throw)"; }
  return { found: nodes.filter(Boolean).length, viewportH: window.innerHeight, scrollY: Math.round(window.scrollY),
    rowY: box ? Math.round(box.y) : null, rowBottom: box ? Math.round(box.bottom) : null,
    origin: location.origin, pointer };
}, IDS).catch((error) => ({ error: flat(error.message).slice(0, 90) }));

const qualified = [];
for (const [index, candidate] of context.pages().entries()) {
  const state = await rowState(candidate);
  say(`CANDIDATE_${index} url=${candidate.url()} state=${JSON.stringify(state)}`);
  if (state && state.found === 3) qualified.push(candidate);
}
if (qualified.length !== 1) {
  say(`REFUSE qualifying_tabs=${qualified.length} -- 两页都挂驾驶舱时该按哪一页不该由我猜（localStorage 按源共享，_tab_probe_r4 实测）`);
  await browser.close().catch(() => undefined);
  process.exit(0);
}
const page = qualified[0];
const first = await rowState(page);
if (!first.pointer || first.pointer === "(empty)" || first.pointer.startsWith("(")) {
  say(`REFUSE no_journey_pointer ${JSON.stringify(first)} -- 「同一个 Journey 没丢」这一半没有读数就不能判，不许写同`);
  await browser.close().catch(() => undefined);
  process.exit(0);
}
say(`JOURNEY_POINTER_CANARY ${first.pointer}`);

for (const shape of SHAPES) {
  const [w, h] = shape.split("x").map(Number);
  await page.setViewportSize({ width: w, height: h }).catch((e) => say(`VIEWPORT_FAIL ${shape} ${flat(e.message).slice(0, 60)}`));
  await page.reload({ waitUntil: "domcontentloaded", timeout: 40000 }).catch((e) => say(`RELOAD_FAIL ${shape} ${flat(e.message).slice(0, 60)}`));
  await page.waitForFunction((ids) => ids.every((id) => document.querySelector(`[data-testid="${id}"]`)), IDS, { timeout: 25000 })
    .catch((e) => say(`WAIT_ROW_FAIL ${shape} ${flat(e.message).slice(0, 70)}`));
  for (const arm of ["cold_top", "after_scroll"]) {
    await page.evaluate(() => window.scrollTo(0, 0));
    if (arm === "after_scroll") await page.evaluate(() => window.scrollBy(0, 600));
    await page.waitForTimeout(900);
    const state = await rowState(page);
    const where = state.error ? "ERROR"
      : state.rowY === null ? "NO_ROW"
      : (state.rowY >= 0 && state.rowBottom <= state.viewportH) ? "on_screen"
      : state.rowY > state.viewportH ? "below_fold" : "above_viewport";
    say(`SHAPE ${shape} ARM ${arm} where=${where} state=${JSON.stringify(state)}`);
    if (where !== "on_screen") { say(`NOT_TAPPED ${shape}/${arm} -- 这一档键不在视口内，不计进 FIRST_TAP，也不许写成旅客点得到`); continue; }

    let hit = 0;
    for (const id of [...IDS, "rev-mission-layer-map"]) {
      const probe = await page.evaluate((testId) => {
        const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
        const node = document.querySelector(`[data-testid="${testId}"]`);
        if (!node) return { present: false };
        const box = node.getBoundingClientRect();
        const cx = Math.round(box.left + box.width / 2);
        const cy = Math.round(box.top + box.height / 2);
        const top = document.elementFromPoint(cx, cy);
        return { present: true, centre: [cx, cy], y: Math.round(box.y), pressed: node.getAttribute("aria-pressed"),
          covers_it: Boolean(top && !node.contains(top)),
          topmost: norm(top?.getAttribute?.("data-testid") || top?.className || top?.tagName || "(nothing here)").slice(0, 44) };
      }, id).catch((error) => ({ error: flat(error.message).slice(0, 80) }));
      if (probe.error) { say(`TAP_ERROR ${id} ${probe.error} -- 仪表坏了，不等于屏上没这个键`); continue; }
      if (!probe.present) { say(`TAP_ABSENT ${id} -- 逐字查过 data-testid 确实没有`); continue; }
      const wasReturn = id === "rev-mission-layer-map" && hit > 0;
      await page.mouse.click(probe.centre[0], probe.centre[1]);
      await page.waitForTimeout(700);
      const after = await page.evaluate((testId) => {
        const node = document.querySelector(`[data-testid="${testId}"]`);
        return { pressed: node?.getAttribute("aria-pressed") ?? null };
      }, id).catch(() => ({ pressed: null }));
      const activated = after.pressed === "true";
      if (!wasReturn && activated) hit += 1;
      say(`TAP ${id} first_press=${!wasReturn} covers_it=${probe.covers_it} topmost=${probe.topmost} centre=${JSON.stringify(probe.centre)} row_y=${probe.y} after_pressed=${after.pressed} RESULT=${activated ? "HIT" : "MISS"}`);
      const shot = `firsttap3-${shape}-${arm}-${id.replace("rev-mission-layer-", "")}${wasReturn ? "b" : ""}.png`;
      await page.screenshot({ path: path.join(OUT, shot), type: "png" }).catch(() => undefined);
      say(`SHOT ${shot}`);
    }
    say(`FIRST_TAP_SUCCESS=${hit}/3 shape=${shape} arm=${arm}`);
    const kept = await rowState(page);
    say(`JOURNEY_KEPT ${kept.pointer === first.pointer ? "same" : "DIFFERENT"} pointer=${kept.pointer}`);
  }
}
say("NOTE 动作只有换视口、刷新、滚动到指定位置与中心点真鼠标点击；未写 storage、未调接口、未起新标签页");
await browser.close().catch(() => undefined);
