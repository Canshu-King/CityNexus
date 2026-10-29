/**
 * One traveller, one tab, all the way to the departure door -- on the stack that carries tonight's fixes.
 *
 * Why this exists: every gate line the walkthrough quotes for 选用 and 出发 was measured on the older
 * stack (human4), and the photo fix, the honest-tile fix, the expired-credential fix and the trips-panel
 * fix all landed after that walk.  The acceptance sheet asks for one future-dated goal on the SAME
 * Journey reaching research -> A/B/C -> a chosen version -> reload -> departure, so this walks it end to
 * end in a single tab and reads the screen at each door, including the button the traveller needs and
 * does not get (rev-plan-select) and the words the departure card says about why.
 *
 * r13 adds one thing over r11: after the freeze door answers, the two sentences this morning's
 *   knife put on the screen are read -- the per-hop refusal list on the card and the drawer's own
 *   mode labels in the agent layer -- each from the layer that actually holds it.
 * r11 adds one thing over r10: after the route door is pressed, the page is reloaded and the card
 * re-opened, and the band, the ask-count sentence and the to-do lines are read again (STEP_12B2).
 *
 * r10 adds one thing over r9: the route door is pressed up to three times, with the band, the
 * ask-count sentence and the to-do route-line count read between presses (see the block comment).
 *
 * Nothing is seeded and no API shortcut is used: the goal is typed, the consent chips are tapped, the
 * send key is pressed, the Agent's own question is answered by clicking one of its choices, research is
 * started by its own button, and every reading below is rendered text.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const WEB = process.env.WALK_BASE || "http://127.0.0.1:14436/revolution";
const START = process.env.WALK_START_DATE || "2026-12-03";
const STORY = process.env.WALK_STORY || "12 月 3 日到 12 月 4 日在北京玩两天，人均预算 800。第一天上午爬八达岭长城，下午回故宫，晚上去鸟巢看灯光；第二天上午逛天坛，下午去南锣鼓巷。不要太赶。";
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const SHOT_PREFIX = process.env.WALK_SHOT_PREFIX || "walk77";
const stream = fs.openSync(path.join(SHOTS, process.env.WALK_LOG || "walk-77-log.txt"), "a");
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const context = browser.contexts()[0] || await browser.newContext();
const page = await context.newPage();
await page.setViewportSize({ width: 414, height: 900 });
page.setDefaultTimeout(8000);
const cdp = await context.newCDPSession(page);
// The screen said 「这次未能保存…可以重试」 and nothing else, which is the exact thing the ruling
// names as the defect.  Before changing any copy, catch what the server actually answered.
page.on("response", (response) => {
  if (response.status() < 400) return;
  response.text().then((body) => say(`HTTP_${response.status()} ${response.url().split("/api/v1")[1] ?? response.url()} ${flat(body).slice(0, 300)}`))
    .catch(() => say(`HTTP_${response.status()} ${response.url().split("/api/v1")[1] ?? ""} (body unreadable)`));
});
const shot = async (name) => {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await page.bringToFront().catch(() => undefined);
      const deadline = new Promise((_, reject) => setTimeout(() => reject(new Error("no frame")), 15000));
      const capture = await Promise.race([cdp.send("Page.captureScreenshot", { format: "png" }), deadline]);
      fs.writeFileSync(path.join(SHOTS, name), Buffer.from(capture.data, "base64"));
      say(`SHOT ${name} bytes=${fs.statSync(path.join(SHOTS, name)).size}`);
      return true;
    } catch (error) { say(`SHOT_RETRY ${name} ${flat(error.message).slice(0, 30)}`); await new Promise((r) => setTimeout(r, 3000)); }
  }
  say(`SHOT_FAILED ${name}`);
  return false;
};
const body = async (limit = 400) => flat(await page.locator("body").innerText({ timeout: 4000 }).catch(() => "")).slice(0, limit);
const read = async (locator, limit = 400) => flat(await locator.innerText({ timeout: 4000 }).catch(() => "(unreadable)")).slice(0, limit);
const setField = async (testId, value) => {
  const field = page.getByTestId(testId);
  const tag = await field.evaluate((n) => n.tagName).catch(() => "?");
  if (tag === "SELECT") await field.selectOption({ label: value }).catch(async () => field.selectOption(value));
  else await field.fill(String(value));
  return String(await field.inputValue().catch(() => "(unreadable)"));
};
const settle = async (minutes, pattern, extra) => {
  for (let poll = 1; poll <= minutes * 6; poll += 1) {
    await page.waitForTimeout(10000);
    const busy = new RegExp(pattern).test(await body(300));
    if (!busy && poll >= 2 && (!extra || await extra())) { say(`SETTLED ticks=${poll} elapsed_s=${poll * 10}`); return true; }
    if (poll % 6 === 0) say(`WAIT_${poll * 10}s busy=${busy}`);
  }
  say(`SETTLE_TIMEOUT pattern=${pattern}`);
  return false;
};
const layerTo = async (testId) => {
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const button = page.getByTestId(testId);
    await button.scrollIntoViewIfNeeded().catch(() => undefined);
    const clicked = await button.click({ timeout: 5000 }).then(() => true).catch(() => false);
    await page.waitForTimeout(2500);
    if (!clicked) {
      // "The tap did nothing" is only a fact once we know what the finger hit.  A fixed chat dock
      // (WorkspaceActions.css:82, z-index 39) can sit on top of the layer tabs after a scroll, and
      // gallery_recheck_r3.mjs measured exactly that: first tap swallowed, second one through
      // (walk-50-log.txt:9 and :10).  Name the interceptor instead of guessing.
      const who = await page.evaluate((wanted) => {
        const node = document.querySelector(`[data-testid='${wanted}']`);
        if (!node) return { present: false };
        const box = node.getBoundingClientRect();
        const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        const describe = (element) => element
          ? element.tagName.toLowerCase() + (element.className ? "." + String(element.className).split(" ")[0] : "")
          : "(none)";
        const dock = document.querySelector(".rev-mission-chat-dock");
        const dockBox = dock ? dock.getBoundingClientRect() : null;
        return { present: true, box: { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) },
          hit_test: describe(hit), covers_it: Boolean(hit) && !node.contains(hit) && hit !== node,
          dock: dockBox ? { top: Math.round(dockBox.top), bottom: Math.round(dockBox.bottom) } : null,
          overlap_with_dock: dockBox ? (box.bottom > dockBox.top && box.top < dockBox.bottom) : false };
      }, testId);
      say(`LAYER_BLOCKED ${testId} attempt=${attempt} ${JSON.stringify(who)}`);
    }
    say(`LAYER ${testId} attempt=${attempt} clicked=${clicked}`);
    if (clicked) return true;
    await page.waitForTimeout(2500);
  }
  return false;
};
const variantState = () => page.evaluate(() => ({
  cards: document.querySelectorAll(".rev-goal-variant-card").length,
  tabs: [...document.querySelectorAll("[id^='rev-v3-variant-tab-']")].map((t) => t.innerText.replace(/\s+/g, " ").trim().slice(0, 14)),
  chosen: [...document.querySelectorAll(".rev-goal-variant-card button")].map((b) => b.innerText.replace(/\s+/g, " ").trim()).filter((t) => t.includes("已选")),
  selectButtons: document.querySelectorAll("[data-testid='rev-plan-select']").length,
  slots: document.querySelectorAll(".rev-goal-draft-slot").length,
}));

say(`WALK55_START ${new Date().toISOString()} ${WEB}`);
await page.goto(WEB, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(3500);
await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(3500);
say(`STEP_01 ${await body(150)}`);

await page.getByTestId("rev-trip-goal").fill(STORY);
await page.getByLabel(/目的地/).first().fill("北京");
await page.getByText("日期与天数", { exact: false }).first().click();
await page.getByTestId("rev-trip-start-date").fill(START);
say(`STEP_02 days=${await setField("rev-trip-duration", 2)}`);
await page.getByText("更多偏好", { exact: false }).first().click();
await page.waitForTimeout(700);
say(`STEP_02 party=${await setField("rev-trip-party-size", 2)} budget=${await setField("rev-trip-budget", 600)}`);
await page.getByRole("button", { name: /继续规划/ }).first().click();
await page.waitForTimeout(5000);
const strip = page.locator(".rev-mission-chat-dock > .rev-mission-chat-consent");
await strip.locator("label").nth(0).click({ timeout: 5000 }).catch(() => say("CONSENT_STRIP_ABSENT"));
await strip.locator("label").nth(1).click({ timeout: 5000 }).catch(() => undefined);
await page.waitForTimeout(700);
await page.locator("#rev-mission-chat-input").fill("先别问太多，按我说的直接安排。");
await page.locator(".rev-mission-chat-dock button[type=submit]").click({ timeout: 6000 }).catch((e) => say(`SEND_ERR ${flat(e.message).slice(0, 50)}`));
say(`STEP_03 sent_at ${new Date().toISOString()}`);
await settle(5, "回复中|Agent 正在处理|正在推进|正在研究");
const choices = page.locator(".rev-agent-choices button");
if (await choices.count().catch(() => 0) > 0) {
  say(`STEP_04 choices=${await choices.count()} first=${flat(await choices.first().innerText().catch(() => "")).slice(0, 40)}`);
  await choices.first().click({ timeout: 6000 }).catch(() => undefined);
  await settle(4, "回复中|Agent 正在处理|正在推进");
}
await page.locator(".rev-agent-start-research").click({ timeout: 8000 }).catch((e) => say(`START_RESEARCH_ERR ${flat(e.message).slice(0, 50)}`));
await settle(16, "正在推进|正在研究", async () => (await page.locator(".rev-goal-draft-slot").count()) > 0);
say(`STEP_05_DRAFT slots=${await page.locator(".rev-goal-draft-slot").count()}`);

await layerTo("rev-mission-layer-map");
const stripRows = await page.evaluate(() => [...document.querySelectorAll(".cn-place-photo")].map((card) => ({
  text: card.innerText.replace(/\s+/g, " ").trim().slice(0, 60),
  picture: Boolean(card.querySelector("img[alt$='实景照片']")),
  ask: [...card.querySelectorAll(".cn-place-photo-fallback button")].map((b) => b.innerText.replace(/\s+/g, " ").trim()),
  answer: [...card.querySelectorAll(".cn-place-photo-fallback span")].map((b) => b.innerText.replace(/\s+/g, " ").trim()),
})));
say(`STEP_06_MAP ${JSON.stringify(stripRows)}`);
await shot(`${SHOT_PREFIX}-06-map-strip.png`);

await layerTo("rev-mission-layer-agent");
await page.locator("#rev-mission-chat-input").fill("按轻松少走、省钱、本地特色三种想法各出一版，让我三选一。");
await page.locator(".rev-mission-chat-dock button[type=submit]").click({ timeout: 6000 }).catch((e) => say(`VARIANTS_SEND_ERR ${flat(e.message).slice(0, 50)}`));
say(`STEP_07 variants_sent_at ${new Date().toISOString()}`);
await settle(6, "回复中|Agent 正在处理|正在推进|正在研究");
await layerTo("rev-mission-layer-timeline");
say(`STEP_08_VARIANTS ${JSON.stringify(await variantState())}`);
await shot(`${SHOT_PREFIX}-08-three-versions.png`);

// r15 picks the version that keeps 八达岭长城 in it, on purpose.  walk-81 clicked the first card
// (A · 轻松少走版, walk-81-log.txt:39 and :42) and that version dropped the Great Wall day, so every hop
// in its plan was short enough for the walking door to answer and the transit arm never fired -- which
// leaves 「公共交通」那一行在抽屉里 still unproven on a real screen.  A traveller who says "I want the
// wall" clicks that card; this finds the same card by its own rendered text and presses its own button.
const cards = page.locator(".rev-goal-variant-card");
const cardCount = await cards.count().catch(() => 0);
let pick = -1;
for (let index = 0; index < cardCount; index += 1) {
  const text = flat(await cards.nth(index).innerText().catch(() => ""));
  if (/八达岭|长城/.test(text)) { pick = index; say(`STEP_09_CARD_${index} ${text.slice(0, 60)}`); break; }
  say(`STEP_09_CARD_${index} ${text.slice(0, 60)}`);
}
const choose = pick >= 0 ? cards.nth(pick).getByRole("button", { name: /选用这份安排/ }).first()
  : page.getByRole("button", { name: /选用这份安排/ }).first();
say(`STEP_09_choose_visible=${await choose.isVisible().catch(() => false)} picked_card=${pick}`);
if (await choose.isVisible().catch(() => false)) {
  await choose.click({ timeout: 8000 }).catch((e) => say(`CHOOSE_ERR ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(7000);
  say(`STEP_09_AFTER ${JSON.stringify(await variantState())}`);
  await shot(`${SHOT_PREFIX}-09-chosen.png`);
}
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);
await layerTo("rev-mission-layer-timeline");
say(`STEP_10_AFTER_RELOAD ${JSON.stringify(await variantState())} screen=${await body(160)}`);
await shot(`${SHOT_PREFIX}-10-after-reload.png`);

const departure = page.locator(".rev-v3-departure");
if (!(await departure.isVisible().catch(() => false))) {
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch((e) => say(`OPENER_ERR ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(2500);
}
if (!(await departure.isVisible().catch(() => false))) {
  say("DEPARTURE_NOT_ON_TIMELINE trying 我的旅程");
  await page.getByText("我的旅程", { exact: false }).first().click({ timeout: 6000 }).catch(() => undefined);
  await page.waitForTimeout(4000);
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch((e) => say(`OPENER_ERR2 ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(2500);
}
say(`STEP_11_DEPARTURE_VISIBLE=${await departure.isVisible().catch(() => false)}`);
say(`STEP_11_CARD ${await read(departure, 700)}`);
// STEP_12A (r17): the traveller closes the gap between two of their own rows, on purpose, so it is the
// LAST door that answers.  walk-84 hit 赶路时间不够 only because the model happened to pack ten rows into
// two days; walk-85's plan was loose and the door never spoke.  Setting the second row to start the minute
// the first one ends makes it certain -- and it is a real action in a real input, not a seeded API state.
const timeFields = departure.locator('input[type="time"]');
const stampsBefore = await timeFields.evaluateAll((nodes) => nodes.map((n) => ({
  label: n.getAttribute("aria-label") || "", value: n.value }))).catch(() => []);
say(`STEP_12A_STAMPS_BEFORE ${JSON.stringify(stampsBefore).slice(0, 420)}`);
// r18: WALK_KEEP_GAP=1 leaves the traveller's own gaps alone, so the selection door lets this plan through
// and the walk can keep going past it to the departed state.  r17 stays exactly as the receipts cite it.
if (process.env.WALK_KEEP_GAP === "1") {
  say(`STEP_12A_GAP_KEPT rows=${stampsBefore.length} (WALK_KEEP_GAP=1: 这一趟不改时间，要走到出发之后)`);
} else if (stampsBefore.length >= 4 && stampsBefore[1].value) {
  await timeFields.nth(2).fill(stampsBefore[1].value).catch((e) => say(`STEP_12A_FILL_ERR ${flat(e.message).slice(0, 60)}`));
  const stampsAfter = await timeFields.evaluateAll((nodes) => nodes.map((n) => n.value)).catch(() => []);
  say(`STEP_12A_STAMPS_AFTER ${JSON.stringify(stampsAfter).slice(0, 260)} zero_gap_written=${stampsAfter[1] === stampsAfter[2]}`);
} else {
  say(`STEP_12A_NOT_ENOUGH_FIELDS=${stampsBefore.length}`);
}
await departure.locator("input[type=checkbox]").first().click({ timeout: 6000 }).catch((e) => say(`TICK_ERR ${flat(e.message).slice(0, 60)}`));
await page.waitForTimeout(1200);
await departure.getByRole("button", { name: /保存为正式候选方案/ }).first().click({ timeout: 8000 }).catch((e) => say(`SAVE_ERR ${flat(e.message).slice(0, 60)}`));
for (let poll = 1; poll <= 14; poll += 1) {
  await page.waitForTimeout(4000);
  const status = await read(page.locator(".rev-v3-departure p[role=status]").first(), 200);
  if (status && status !== "(unreadable)") { say(`STEP_12_SAVE_STATUS ${status}`); break; }
  if (poll === 14) say("STEP_12_SAVE_STATUS (none after 56s)");
}
say(`STEP_12_CARD_AFTER ${await read(departure, 900)}`);
await shot(`${SHOT_PREFIX}-12-departure-after-save.png`);
// The route door: press what the card offers and read back what the provider answered.
const routeState = page.getByTestId("rev-v3-route-state");
const askCountHere = page.getByTestId("rev-v3-ask-count");
say(`STEP_12B_ROUTE_BEFORE ${await read(routeState, 220)}`);
let routeAfter = "";
// A person who reads "还有 2 段没有来源回答" presses this again; so does the instrument.  Between every
// press it reads the band, the sentence above the ask button, and how many 转场路线 lines the to-do block
// still lists -- that trio is the positive arm of the rule that drops rows only once a snapshot froze.
for (let round = 1; round <= 3; round += 1) {
  await page.getByTestId("rev-v3-freeze-routes").first().click({ timeout: 8000 }).catch((e) => say(`FREEZE_ERR_${round} ${flat(e.message).slice(0, 70)}`));
  for (let poll = 1; poll <= 14; poll += 1) {
    await page.waitForTimeout(5000);
    routeAfter = await read(routeState, 220);
    if (routeAfter && !/还没有向高德核实/.test(routeAfter) && poll > 1) break;
    if (poll === 14) say(`STEP_12B_ROUTE_STATE_ROUND_${round} (no answer after 70s)`);
  }
  const cardNow = await read(departure, 1400);
  say(`STEP_12B_ROUND_${round} BAND ${routeAfter}`);
  say(`STEP_12B_ROUND_${round} ASK_COUNT ${await read(askCountHere, 160)}`);
  say(`STEP_12B_ROUND_${round} TODO_ROUTE_LINES=${(cardNow.match(/转场路线/g) || []).length} FROZEN=${/已冻结进这版方案/.test(routeAfter)}`);
  await shot(`${SHOT_PREFIX}-12b-round-${round}.png`);
  if (/已冻结进这版方案/.test(routeAfter)) { say(`STEP_12B_FROZEN_ON_ROUND=${round}`); break; }
}
say(`STEP_12B_ROUTE_AFTER ${routeAfter}`);
// STEP_12B3a: the per-hop refusal list, read off the rendered card in the timeline layer.
const hopLines = () => page.getByTestId("rev-v3-hop-refusal").allInnerTexts().catch(() => []);
say(`STEP_12B3_HOP_REFUSALS ${JSON.stringify(await hopLines())}`);
await shot(`${SHOT_PREFIX}-12b2-before-reload.png`);
// STEP_12B2: the traveller's own refresh.  The freeze happened; does the card still know it?
await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(12000);
await layerTo("rev-mission-layer-timeline");
if (!(await departure.isVisible().catch(() => false))) {
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch((e) => say(`REOPEN_ERR_12B2 ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(3500);
}
say(`STEP_12B2_DEPARTURE_VISIBLE=${await departure.isVisible().catch(() => false)}`);
say(`STEP_12B2_ROUTE_STATE_AFTER_RELOAD ${await read(routeState, 220)}`);
say(`STEP_12B3_HOP_REFUSALS_AFTER_RELOAD ${JSON.stringify(await hopLines())}`);
// STEP_12B3b: the drawer, in the agent layer, after the task was re-fetched -- the rows the freeze wrote
// are the ones whose mode label is being checked.
await layerTo("rev-mission-layer-agent");
await page.waitForTimeout(2500);
// A closed <details> renders no inner text, so allInnerTexts() came back as one empty string on
// walk-78 (walk-78-log.txt:71) -- that is the instrument being blind, not the screen being wrong.
await page.locator(".rev-agent-research-drawer summary").first().evaluate((node) => { node.closest("details").open = true; }).catch(() => undefined);
await page.waitForTimeout(1200);
say(`STEP_12B3_DRAWER_TITLE ${flat(await page.locator(".rev-agent-research-drawer summary").first().innerText().catch(() => "(none)"))}`);
const drawerLines = await page.getByTestId("rev-amap-research-route").allInnerTexts().catch(() => []);
say(`STEP_12B3_DRAWER_ROWS ${JSON.stringify(drawerLines)}`);
say(`STEP_12B3_DRAWER_TRANSIT_LABELED=${drawerLines.filter((line) => line.includes("公共交通")).length} `
  + `WALK_LABELED=${drawerLines.filter((line) => line.includes("步行")).length}`);
// r14 adds three readings over r13, all of them about the same row: does the drawer show the transport
// the freeze actually measured (mode label AND the deep link's mode parameter), and can a person read the
// numbers it prints?  walk-80 measured TRANSIT_LABELED=0 with the band claiming one transit segment
// (walk-80-log.txt:39 against :62), and 「41748 秒」 for a 52 km hop.
const linkModes = await page.evaluate(() => [...document.querySelectorAll("[data-testid='rev-amap-research-route'] a")]
  .map((anchor) => new URL(anchor.href).searchParams.get("mode")));
say(`STEP_12B3_DRAWER_LINK_MODES ${JSON.stringify(linkModes)}`);
say(`STEP_12B3_DRAWER_RAW_SECONDS=${drawerLines.filter((line) => /秒/.test(line)).length} `
  + `READABLE_UNITS=${drawerLines.filter((line) => /公里|小时|分钟/.test(line)).length} `
  + `LINE_NAMES ${JSON.stringify((await page.getByTestId("rev-amap-research-lines").allInnerTexts().catch(() => [])).map(flat))}`);
const panelSteps = (await page.locator(".rev-workspace-task-steps li").allInnerTexts().catch(() => [])).map(flat);
await page.locator(".rev-workspace-task-steps").first()
  .evaluate((node) => { node.closest("details").open = true; }).catch(() => undefined);
await page.waitForTimeout(900);
const panelStepsOpen = (await page.locator(".rev-workspace-task-steps li").allInnerTexts().catch(() => [])).map(flat);
say(`STEP_12B3_PANEL_ROUTE_LINES ${JSON.stringify(panelStepsOpen.filter((text) => /路线 · /.test(text)).slice(0, 6))} `
  + `RAW=${panelStepsOpen.filter((text) => /路线 · [0-9.]+ (米|公里) · [0-9]+ 秒/.test(text)).length} CLOSED_READ=${panelSteps.length} OPEN_READ=${panelStepsOpen.length}`);
await shot(`${SHOT_PREFIX}-12b4-agent-drawer.png`);
await layerTo("rev-mission-layer-timeline");
await page.waitForTimeout(2000);
say(`STEP_12B2_ASK_COUNT ${await read(askCountHere, 160)}`);
const cardAfterReload = await read(departure, 1400);
say(`STEP_12B2_TODO_ROUTE_LINES=${(cardAfterReload.match(/转场路线/g) || []).length} `
  + `TODO_PLACE_LINES=${(cardAfterReload.match(/具体地点|还没有确定地点/g) || []).length}`);
await shot(`${SHOT_PREFIX}-12b3-after-reload.png`);
await shot(`${SHOT_PREFIX}-12b-routes-verified.png`);
// STEP_12C: the price door. A ticket no source answered is the traveller's decision to make, and the
// screen has to show both roads -- accept it as unknown, or send the Agent to find a priced place.
const priceState = page.getByTestId("rev-v3-price-state");
say(`STEP_12C_PRICE_BEFORE ${await read(priceState, 260)}`);
const accept = page.getByTestId("rev-v3-accept-price");
if (await accept.isVisible().catch(() => false)) {
  await shot(`${SHOT_PREFIX}-12c-price-unknown.png`);
  await accept.click({ timeout: 8000 }).catch((e) => say(`PRICE_ERR ${flat(e.message).slice(0, 60)}`));
  let priceAfter = "(unreadable)";
  for (let poll = 0; poll < 12; poll += 1) {
    await page.waitForTimeout(5000);
    priceAfter = await read(page.getByTestId("rev-v3-price-state"), 260);
    if (priceAfter && priceAfter !== "(unreadable)") break;
  }
  say(`STEP_12C_PRICE_AFTER ${priceAfter}`);
  await shot(`${SHOT_PREFIX}-12c-price-accepted.png`);
} else {
  say("STEP_12C_PRICE_AFTER (no accept door on this card)");
}
// STEP_12D: the ask door, measured honestly.  r4 read the pane's head and gave up on "busy" after a
// regex that never matches, so it proved nothing about the reply; r5 counts the Agent's turns before the
// press, then waits for the traveller's own sentence to appear AND for a new Agent turn after it.
const askCount = page.getByTestId("rev-v3-ask-count");
const pane = page.locator('[data-testid="rev-mission-agent-pane"]').first();
const paneText = async () => flat(await pane.innerText({ timeout: 6000 }).catch(() => ""));
const agentTurns = async () => (await paneText()).split("CityNexus Agent").length - 1;
say(`STEP_12D_ASK_COUNT ${await read(askCount, 160)}`);
const askHow = page.getByTestId("rev-v3-ask-how");
say(`STEP_12D_ASK_HOW_BEFORE_PRESS ${await read(askHow, 210)}`);
await layerTo("rev-mission-layer-agent");
const turnsBefore = await agentTurns();
const textBefore = await paneText();
await layerTo("rev-mission-layer-timeline");
const ask = page.getByTestId("rev-v3-ask-agent");
say(`STEP_12D_ASK_BUTTON=${await ask.count().catch(() => -1)}`);
if (await ask.first().isVisible().catch(() => false)) {
  await ask.first().click({ timeout: 8000 }).catch((e) => say(`ASK_ERR ${flat(e.message).slice(0, 70)}`));
  await page.waitForTimeout(3000);
  say(`STEP_12D_ASK_HOW ${await read(page.getByTestId("rev-v3-ask-how"), 200)}`);
  const composer = page.locator("#rev-mission-chat-input");
  const filled = await composer.inputValue().catch(() => "(no input found)");
  say(`STEP_12D_COMPOSER_CHARS=${filled.length} HEAD=${filled.slice(0, 170)}`);
  const send = page.locator(".rev-mission-chat-dock button[type=submit]").first();
  say(`STEP_12D_SEND_VISIBLE=${await send.isVisible().catch(() => false)} ENABLED=${await send.isEnabled().catch(() => false)}`);
  await send.click({ timeout: 8000 }).catch((e) => say(`SEND_ERR ${flat(e.message).slice(0, 70)}`));
  await page.waitForTimeout(2500);
  say(`STEP_12E_DOCK_STATUS_RIGHT_AFTER_SEND ${await read(page.getByTestId("rev-dock-status"), 200)}`);
  await layerTo("rev-mission-layer-agent");
  let sentAt = 0, answeredAt = 0, failedAt = 0;
  for (let poll = 1; poll <= 34; poll += 1) {
    const text = await paneText();
    if (!sentAt && text.includes("出发前还缺这几项")) sentAt = poll * 8;
    if (!answeredAt && (text.split("CityNexus Agent").length - 1) > turnsBefore) answeredAt = poll * 8;
    if (!failedAt && (text.includes("模型服务暂不可用") || text.includes("上一轮没有答完"))) failedAt = poll * 8;
    if ((sentAt && answeredAt) || failedAt) break;
    await page.waitForTimeout(8000);
  }
  const text = await paneText();
  say(`STEP_12D_SENT=${sentAt ? `${sentAt}s` : "not on screen after 272s"} ANSWERED=${answeredAt ? `${answeredAt}s` : "no new agent turn"} FAILED=${failedAt ? `${failedAt}s` : "no failure line on screen"} TURNS_BEFORE=${turnsBefore} TURNS_AFTER=${text.split("CityNexus Agent").length - 1}`);
  say(`STEP_12F_DOCK_STATUS_AFTER_WAIT ${await read(page.getByTestId("rev-dock-status"), 220)}`);
  say(`STEP_12F_PANE_TAIL_HAS_FAILURE_TEXT=${text.includes("模型服务暂不可用")} ANSWER_MARK=${text.includes("这条回复没有改动日程")}`);
  say(`STEP_12D_PANE_HEADLINE ${text.slice(textBefore.length, textBefore.length + 260) || "(no new text)"}`);
  say(`STEP_12D_PANE_TAIL ${text.slice(-1400) || "(unreadable)"}`);
  await shot(`${SHOT_PREFIX}-12d-reply.png`);
  await layerTo("rev-mission-layer-timeline");
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch((e) => say(`REOPEN_ERR ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(3000);
  say(`STEP_12E_DEPARTURE_VISIBLE=${await page.locator(".rev-v3-departure").first().isVisible().catch(() => false)}`);
  say(`STEP_12E_CARD_AFTER_ASK ${await read(page.locator(".rev-v3-departure").first(), 500)}`);
  say(`STEP_12E_ASK_COUNT_AFTER_ASK ${await read(askCount, 160)}`);
  say(`STEP_12E_ASK_HOW_AFTER_SETTLE ${await read(askHow, 210)}`);
} else {
  say("STEP_12D_ASK_BUTTON_NOT_SHOWN (nothing left to ask, or no saved plan)");
}
say(`STEP_13_WORKBENCH ${await read(page.locator('[data-testid="rev-plan-workbench"]').first(), 700)}`);
const select = page.getByTestId("rev-plan-select");
say(`STEP_13_SELECT_BUTTONS=${await select.count().catch(() => -1)} VISIBLE=${await select.first().isVisible().catch(() => false)}`);
await shot(`${SHOT_PREFIX}-13-workbench.png`);
if (await select.first().isVisible().catch(() => false)) {
  await select.first().click({ timeout: 8000 }).catch((e) => say(`SELECT_ERR ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(6000);
  say(`STEP_14_AFTER_SELECT ${await read(page.locator('[data-testid="rev-plan-workbench"]').first(), 500)}`);
  await shot(`${SHOT_PREFIX}-14-after-select.png`);
  // STEP_15: depart. The traveller's own 确认出发 press, then a reload, then what the screen reads back.
  const start = page.getByTestId("rev-plan-start");
  say(`STEP_15_START_VISIBLE=${await start.isVisible().catch(() => false)}`);
  if (await start.isVisible().catch(() => false)) {
    await start.click({ timeout: 8000 }).catch((e) => say(`START_ERR ${flat(e.message).slice(0, 60)}`));
    let startedText = "(unreadable)";
    for (let poll = 0; poll < 12; poll += 1) {
      await page.waitForTimeout(5000);
      startedText = await read(page.locator('[data-testid="rev-plan-workbench"]').first(), 500);
      if (startedText && startedText !== "(unreadable)" && /正在使用|已开始|旅程已开始|ACTIVE/.test(startedText)) break;
    }
    say(`STEP_15_AFTER_START ${startedText}`);
    await shot(`${SHOT_PREFIX}-15-active.png`);
    // STEP_17 (r18): the traveller is departed.  What is the day-by-day pane now, and can they still reach
    // their own rows?  The pane swaps its whole body when the journey turns ACTIVE, so this is read from the
    // screen rather than inferred from the component.
    const pane = page.getByTestId("rev-mission-timeline-pane");
    await layerTo("rev-mission-layer-timeline");
    await page.waitForTimeout(1800);
    say(`STEP_17_ACTIVE_PANE ${await read(pane, 900)}`);
    say(`STEP_17_ACTIVE_PANE_CONTROLS time_inputs=${await pane.locator('input[type="time"]').count().catch(() => -1)} `
      + `buttons=${await pane.locator("button").count().catch(() => -1)} `
      + `links=${await pane.locator("a").count().catch(() => -1)}`);
    await shot(`${SHOT_PREFIX}-17-active-pane.png`);
    await page.reload({ waitUntil: "networkidle" }).catch(() => undefined);
    await page.waitForTimeout(6000);
    say(`STEP_16_AFTER_RELOAD ${await read(page.locator('[data-testid="rev-plan-workbench"]').first(), 500)}`);
    await shot(`${SHOT_PREFIX}-16-reloaded.png`);
    await layerTo("rev-mission-layer-timeline");
    await page.waitForTimeout(1800);
    say(`STEP_18_AFTER_RELOAD_PANE ${await read(pane, 900)}`);
    say(`STEP_18_AFTER_RELOAD_HEADLINE ${await read(page.locator(".cn-mission-card, .cn-mission-hero").first(), 300)}`);
    await shot(`${SHOT_PREFIX}-18-reloaded-pane.png`);
  } else {
    say(`STEP_15_NO_START_CONTROL ${await read(page.locator('[data-testid="rev-plan-workbench"]').first(), 300)}`);
  }
}
say(`WALK_END ${new Date().toISOString()}`);
await page.close().catch(() => undefined);
process.exit(0);
