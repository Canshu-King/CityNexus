/**
 * Play-trial smoke, r2 -- r1 stopped one step short of a real traveller and then reported the door as closed.
 *
 * r1 (play-stack-smoke-2.txt) typed a sentence that named 北京, pressed 继续规划 →, and read "nothing happened":
 * the browser's own required-field bubble sat on 目的地 (see play-stack-2-after-press.png).  That reading was
 * correct about the press but wrong about the cause I implied -- the destination field was empty, and the app
 * never takes a city from the sentence.  r2 walks the whole first-screen path a person would: read the hint,
 * fill the destination, press, and read what the app produced.
 *
 * Still no seeding: real keystrokes, real centre clicks, and everything lands in the play canary DB.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.SMOKE_LOG || "play-stack-smoke-3.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const URL = process.env.SMOKE_URL || "http://127.0.0.1:14461/revolution";
const GOAL = "12 月 3 日到 12 月 4 日在北京玩两天，人均预算 800，不要太赶。";
const CITY = "北京";

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const page = await context.newPage();
await page.setViewportSize({ width: 390, height: 844 });
const readForm = () => page.evaluate(() => {
  const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const node = document.querySelector('button[type="submit"]');
  const box = node?.getBoundingClientRect();
  return {
    h1: norm(document.querySelector("h1")?.textContent).slice(0, 40),
    hint: norm(document.querySelector('[data-testid="rev-trip-destination-hint"]')?.textContent).slice(0, 90) || "(no hint node)",
    city: document.querySelector('[data-testid="rev-firstlook-city"]')?.value ?? "(missing)",
    party: document.querySelector('[data-testid="rev-trip-party-size"]')?.value,
    budget: document.querySelector('[data-testid="rev-trip-budget"]')?.value,
    submit: norm(node?.textContent).slice(0, 20),
    submitCentre: box && node ? [Math.round(box.left + box.width / 2), Math.round(box.top + box.height / 2)] : null,
  };
});

try {
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 40000 });
  await page.waitForSelector('[data-testid="rev-trip-goal"]', { timeout: 25000 });
  say(`COLD ${JSON.stringify(await readForm())}`);

  await page.locator('[data-testid="rev-trip-goal"]').fill(GOAL);
  await page.waitForTimeout(700);
  say(`AFTER_GOAL ${JSON.stringify(await readForm())}`);
  await page.screenshot({ path: path.join(OUT, "play-stack3-1-goal-typed.png"), type: "png" }).catch(() => undefined);
  say("SHOT play-stack3-1-goal-typed.png");

  const first = await readForm();
  if (!first.submitCentre) { say("REFUSE_PRESS no submit button"); }
  else {
    await page.mouse.click(first.submitCentre[0], first.submitCentre[1]);
    await page.waitForTimeout(2500);
    const afterEmpty = await readForm();
    const emptyPointer = await page.evaluate(() => { try { return String(localStorage.getItem("citynexus.revolution.firstlook.journey") || "(none)").slice(0, 20); } catch { return "(err)"; } });
    say(`PRESS_WITH_EMPTY_CITY pointer=${emptyPointer} form=${JSON.stringify(afterEmpty)}`);
    await page.screenshot({ path: path.join(OUT, "play-stack3-2-empty-city-press.png"), type: "png" }).catch(() => undefined);
    say("SHOT play-stack3-2-empty-city-press.png");
  }

  await page.locator('[data-testid="rev-firstlook-city"]').fill(CITY);
  await page.waitForTimeout(700);
  say(`AFTER_CITY ${JSON.stringify(await readForm())}`);
  const ready = await readForm();
  if (!ready.submitCentre) { say("REFUSE_PRESS second attempt: no submit button"); }
  else {
    await page.mouse.click(ready.submitCentre[0], ready.submitCentre[1]);
    await page.waitForTimeout(9000);
    const done = await page.evaluate(() => {
      const norm = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
      return {
        heading: norm(document.querySelector("h1,h2")?.textContent).slice(0, 40),
        tabs: document.querySelectorAll('[data-testid^="rev-mission-layer-"]').length,
        dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
        cards: document.querySelectorAll(".rev-goal-draft-slot").length,
        body: norm(document.body.innerText).slice(0, 300),
        pointer: (() => { try { return norm(localStorage.getItem("citynexus.revolution.firstlook.journey")).slice(0, 46); } catch { return "(err)"; } })(),
        bearer: (() => { try { return sessionStorage.getItem("citynexus.traveler.bearer") ? "present_in_sessionStorage(value not printed)" : "(none)"; } catch { return "(err)"; } })(),
      };
    });
    say(`AFTER_CITY_PRESS ${JSON.stringify(done)}`);
    await page.screenshot({ path: path.join(OUT, "play-stack3-3-after-journey.png"), type: "png" }).catch(() => undefined);
    say("SHOT play-stack3-3-after-journey.png");
  }
} catch (error) {
  say(`SMOKE_FAILED ${flat(error.message).slice(0, 170)}`);
} finally {
  await page.close().catch(() => undefined);
}
say("NOTE 冷开一个标签页、输入一句话与城市名、按屏上那枚提交键两次；凭证只报在不在，值没有打印");
await browser.close().catch(() => undefined);
