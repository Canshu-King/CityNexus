/**
 * P0-2 acceptance -- the fixed dock must offer two ways out of a stalled round.
 *
 * Evidence the ruling asks for is "press 重试这一轮 for real and record the 503 -> same Task receipt".
 * Task identity is read from the request line the browser itself sends (/agent/goal-tasks/<uuid>/run|resume),
 * never from a DOM attribute, because "the button exists" is not "the same round was resumed".
 * A round only becomes recoverable when the server says so; if the model answers instead, this tool prints
 * NO_RECOVERABLE_STATE_OBSERVED with what the dock really showed -- it never fabricates the state by writing
 * storage or by asserting on the source code.
 *
 * Refuses to click unless exactly one tab is the live cockpit (3 layer tabs + the dock), for the reason
 * press_resume_r2 documented: localStorage is per-origin, so two tabs can both claim the same journey.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.RECOV_LOG || "dock-recovery-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const now = () => new Date().toISOString();
const MSG = process.env.RECOV_MSG || "先别加新地点。这一趟里还有哪一段没核实？";

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();

const markOf = (page) => page.evaluate(() => ({
  tabs: document.querySelectorAll('[data-testid^="rev-mission-layer-"]').length,
  dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
  recovery: Boolean(document.querySelector('[data-testid="rev-dock-recovery"]')),
  status: flat(document.querySelector('[data-testid="rev-dock-status"]')?.textContent).slice(0, 90),
  shape: `${window.innerWidth}x${window.innerHeight}`,
  pointer: (() => { try { return flat(localStorage.getItem("citynexus.revolution.firstlook.journey")).slice(0, 8); } catch { return ""; } })(),
})).catch(() => null);

const qualified = [];
for (const [index, candidate] of context.pages().entries()) {
  const mark = await markOf(candidate);
  say(`CANDIDATE_${index} url=${candidate.url()} mark=${JSON.stringify(mark)}`);
  if (mark && mark.tabs === 3 && mark.dock) qualified.push(candidate);
}
if (qualified.length !== 1) {
  say(`REFUSE qualifying_tabs=${qualified.length} -- 两页都自称这一趟时按错就是污染别人的走查，也不许用新标签页假装成它`);
  await browser.close().catch(() => undefined);
  process.exit(0);
}
const page = qualified[0];

const calls = [];
page.on("request", (request) => {
  const m = request.url().match(/\/agent\/goal-tasks\/([0-9a-fA-F-]{36})\/(run|resume)/);
  if (m) calls.push({ at: now(), kind: m[2], task: m[1].slice(0, 8), method: request.method(), status: null });
});
page.on("response", (response) => {
  const m = response.url().match(/\/agent\/goal-tasks\/([0-9a-fA-F-]{36})\/(run|resume)/);
  if (!m) return;
  const row = calls.findLast((c) => c.task === m[1].slice(0, 8) && c.kind === m[2] && c.status === null);
  if (row) { row.status = response.status(); row.at_end = now(); }
});

const probeRecovery = () => page.evaluate(() => {
  const read = (sel) => {
    const node = document.querySelector(sel);
    if (!node) return null;
    const box = node.getBoundingClientRect();
    const cx = Math.round(box.left + box.width / 2);
    const cy = Math.round(box.top + box.height / 2);
    const top = document.elementFromPoint(cx, cy);
    return { text: flat(node.textContent), y: Math.round(box.y), x: Math.round(box.x),
      centre: [cx, cy], disabled: node.disabled, covers_it: Boolean(top && !node.contains(top)),
      topmost: flat(top?.className || top?.tagName || "(none)").slice(0, 40),
      inViewport: box.top >= 0 && box.bottom <= window.innerHeight };
  };
  return { row: read('[data-testid="rev-dock-recovery"]'),
    retry: read('[data-testid="rev-dock-retry-round"]'),
    browse: read('[data-testid="rev-dock-browse-found"]'),
    scrollY: Math.round(window.scrollY), shape: `${window.innerWidth}x${window.innerHeight}` };
});

let mark = await markOf(page);
say(`START ${JSON.stringify(mark)}`);
if (!mark.recovery) {
  const sent = await page.evaluate(() => {
    const box = document.getElementById("rev-mission-chat-input");
    if (!box) return "no composer";
    return { enabled: !box.disabled, value: box.value };
  });
  say(`SEND_PRE ${JSON.stringify(sent)}`);
  try {
    await page.locator("#rev-mission-chat-input").fill(MSG);
    await page.locator('.rev-mission-chat-dock button[type="submit"]').click();
    say(`SENT at ${now()} text=${MSG}`);
  } catch (error) {
    say(`SEND_FAILED ${flat(error.message).slice(0, 120)} -- 打不出去就不许假装走过这一轮`);
    await browser.close().catch(() => undefined);
    process.exit(0);
  }
  for (let tick = 1; tick <= 60; tick += 1) {
    await page.waitForTimeout(5000);
    mark = await markOf(page);
    say(`POLL_${tick * 5}s ${JSON.stringify({ recovery: mark.recovery, status: mark.status })}`);
    if (mark.recovery) break;
  }
}
if (!(mark && mark.recovery)) {
  say(`NO_RECOVERABLE_STATE_OBSERVED last=${JSON.stringify(mark)} calls=${JSON.stringify(calls)}`);
  await page.screenshot({ path: path.join(OUT, "dock-recovery-no-state.png"), type: "png" }).catch(() => undefined);
  await browser.close().catch(() => undefined);
  process.exit(0);
}

const beforeShot = "dock-recovery-1-before.png";
await page.screenshot({ path: path.join(OUT, beforeShot), type: "png" }).catch(() => undefined);
const first = await probeRecovery();
say(`RECOVERY_ROW ${JSON.stringify(first)}`);
say(`SHOT ${beforeShot}`);
const taskBefore = calls.filter((c) => c.kind === "run").at(-1);
say(`BASELINE_TASK ${JSON.stringify(taskBefore)}`);

if (!first.retry || first.retry.disabled || first.retry.covers_it) {
  say(`REFUSE_PRESS retry_button disabled=${first.retry?.disabled} covers_it=${first.retry?.covers_it} topmost=${first.retry?.topmost}`);
} else {
  await page.mouse.click(first.retry.centre[0], first.retry.centre[1]);
  say(`PRESSED 重试这一轮 at ${now()}`);
  let settled = null;
  for (let tick = 1; tick <= 48; tick += 1) {
    await page.waitForTimeout(5000);
    const snap = await markOf(page);
    const resume = calls.filter((c) => c.kind === "resume");
    say(`RESUME_POLL_${tick * 5}s recovery=${snap.recovery} status=${JSON.stringify(snap.status).slice(0, 70)} resume_calls=${JSON.stringify(resume)}`);
    if (resume.length && resume.at(-1).status !== null) { settled = resume.at(-1); break; }
  }
  const after = await probeRecovery();
  say(`RESUME_RECEIPT ${JSON.stringify(settled)} same_task=${Boolean(settled && taskBefore && settled.task === taskBefore.task)}`);
  await page.screenshot({ path: path.join(OUT, "dock-recovery-2-after-retry.png"), type: "png" }).catch(() => undefined);
  say("SHOT dock-recovery-2-after-retry.png");
  say(`AFTER_RETRY_ROW ${JSON.stringify(after)}`);
}

if (first.browse && !first.browse.covers_it) {
  await page.mouse.click(first.browse.centre[0], first.browse.centre[1]);
  await page.waitForTimeout(900);
  const landed = await page.evaluate(() => ({
    mapPressed: document.querySelector('[data-testid="rev-mission-layer-map"]')?.getAttribute("aria-pressed"),
    agentPressed: document.querySelector('[data-testid="rev-mission-layer-agent"]')?.getAttribute("aria-pressed"),
    cards: document.querySelectorAll(".rev-mission-place-card, .rev-map-place-card").length,
    strip: flat(document.querySelector(".cn-mission-os")?.textContent).slice(0, 220),
    pointer: flat(localStorage.getItem("citynexus.revolution.firstlook.journey")).slice(0, 8),
  }));
  say(`BROWSE_RESULT ${JSON.stringify(landed)}`);
  await page.screenshot({ path: path.join(OUT, "dock-recovery-3-after-browse.png"), type: "png" }).catch(() => undefined);
  say("SHOT dock-recovery-3-after-browse.png");
} else {
  say(`BROWSE_NOT_PRESSED ${JSON.stringify(first.browse)}`);
}
say("NOTE 唯一的写入动作是发送一条旅客消息与两次点击（重试这一轮 / 先浏览已找到的地点）；未写 storage、未调接口、未起新标签页");
await browser.close().catch(() => undefined);
