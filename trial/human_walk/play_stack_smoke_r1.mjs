/**
 * Smoke the double-click trial the way the owner will: open the play URL in a real browser tab, read the first
 * screen, type one sentence, press the button the screen offers, and read what came back.  No storage seeding,
 * no API shortcuts -- the only writes are the ones a traveller's own keystrokes cause, and they land in the
 * play canary database (citynexus_v3_play_1024.db), not in any stack the walkthroughs use.
 *
 * Every page.evaluate here declares its own `norm`: this family of instruments failed three times tonight
 * because a Node-side helper was called inside the page (first_tap_layers_r2's empty journey pointer,
 * play_stack_smoke_r1's first run).  instrument_lint_r1.mjs now checks that rule mechanically.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.SMOKE_LOG || "play-stack-smoke-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const URL = process.env.SMOKE_URL || "http://127.0.0.1:14461/revolution";
const GOAL = "12 月 3 日到 12 月 4 日在北京玩两天，人均预算 800，不要太赶。";

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const page = await context.newPage();
await page.setViewportSize({ width: 390, height: 844 });
try {
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 40000 });
  await page.waitForSelector('[data-testid="rev-trip-goal"]', { timeout: 25000 });
  const hero = await page.evaluate(() => {
    const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
    const submitNode = document.querySelector('button[type="submit"]');
    let submitBox = null;
    if (submitNode) {
      const box = submitNode.getBoundingClientRect();
      const cx = Math.round(box.left + box.width / 2);
      const cy = Math.round(box.top + box.height / 2);
      const top = document.elementFromPoint(cx, cy);
      submitBox = { y: Math.round(box.y), bottom: Math.round(box.bottom), viewport_h: window.innerHeight,
        centre: [cx, cy], covered: Boolean(top && !submitNode.contains(top)),
        topmost: norm(top?.className || top?.tagName).slice(0, 40) };
    }
    return { h1: norm(document.querySelector("h1")?.textContent).slice(0, 40),
      goalPlaceholder: document.querySelector('[data-testid="rev-trip-goal"]')?.placeholder ?? "",
      submit: norm(submitNode?.textContent).slice(0, 24), submitBox };
  });
  say(`FIRST_SCREEN ${JSON.stringify(hero)}`);
  await page.screenshot({ path: path.join(OUT, "play-stack-1-first-screen.png"), type: "png" }).catch(() => undefined);
  say("SHOT play-stack-1-first-screen.png");

  await page.locator('[data-testid="rev-trip-goal"]').fill(GOAL);
  await page.waitForTimeout(600);
  const derived = await page.evaluate(() => {
    const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
    return { party: document.querySelector('[data-testid="rev-trip-party-size"]')?.value,
      budget: document.querySelector('[data-testid="rev-trip-budget"]')?.value,
      chip: norm(document.querySelector(".rev-trip-request-form")?.textContent).slice(0, 140) };
  });
  say(`AFTER_TYPING ${JSON.stringify(derived)}`);

  const submit = await page.evaluate(() => {
    const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
    const node = document.querySelector('button[type="submit"]');
    if (!node) return null;
    const box = node.getBoundingClientRect();
    return { text: norm(node.textContent), centre: [Math.round(box.left + box.width / 2), Math.round(box.top + box.height / 2)], disabled: node.disabled };
  });
  if (!submit || submit.disabled) {
    say(`REFUSE_PRESS ${JSON.stringify(submit)}`);
  } else {
    await page.mouse.click(submit.centre[0], submit.centre[1]);
    await page.waitForTimeout(5000);
    const after = await page.evaluate(() => {
      const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
      return { url: location.href,
        heading: norm(document.querySelector("h1,h2")?.textContent).slice(0, 40),
        body: norm(document.body.innerText).slice(0, 260),
        tabs: document.querySelectorAll('[data-testid^="rev-mission-layer-"]').length,
        dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
        pointer: (() => { try { return norm(localStorage.getItem("citynexus.revolution.firstlook.journey")).slice(0, 46); } catch { return "(err)"; } })() };
    });
    say(`AFTER_PRESS "${submit.text}" ${JSON.stringify(after)}`);
    await page.screenshot({ path: path.join(OUT, "play-stack-2-after-press.png"), type: "png" }).catch(() => undefined);
    say("SHOT play-stack-2-after-press.png");
  }
} catch (error) {
  say(`SMOKE_FAILED ${flat(error.message).slice(0, 160)}`);
} finally {
  await page.close().catch(() => undefined);
}
say("NOTE 只开了一个新标签页、输入一句话、按了屏上那枚提交键；数据落在 play 专用 canary 库里");
await browser.close().catch(() => undefined);
