// X arm tail: after the traveller presses the hand beside the refusal sentence, actually walk the
// explore screen -- find a real place, let the screen turn it into a formal plan place, then take
// the 选用 / 出发 doors on the same journey and read the map against the activity count.
// Every step surveys the screen first, so a miss reports what the traveller could see instead of
// silently pressing nothing.
const survey = async (label) => {
  const seen = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll("button,[role='button'],input,select,a[data-testid]")).slice(0, 90);
    return nodes.filter((node) => {
      const box = node.getBoundingClientRect();
      return box.width > 4 && box.height > 4;
    }).map((node) => ({
      tag: node.tagName,
      id: node.getAttribute("data-testid") || "",
      name: String(node.getAttribute("aria-label") || node.innerText || node.placeholder || "").replace(/\s+/g, " ").slice(0, 44),
      dis: Boolean(node.disabled),
    }));
  });
  note(`SURVEY_${label} ${JSON.stringify(seen).slice(0, 3000)} t=${elapsed()}`);
  return seen;
};

const byTestId = (id) => page.locator(`[data-testid="${id}"]`);
const byTestIdPrefix = (prefix) => page.locator(`[data-testid^="${prefix}"]`);
const pressNear = async (locator, label, timeout = 15000) => {
  if (!(await locator.count())) { note(`MISS ${label} absent t=${elapsed()}`); return false; }
  const target = locator.first();
  if (!(await target.isVisible().catch(() => false))) { note(`MISS ${label} hidden t=${elapsed()}`); return false; }
  const hit = await target.evaluate((node) => {
    node.scrollIntoView({ block: "center" });
    const box = node.getBoundingClientRect();
    const cx = box.left + box.width / 2;
    const cy = box.top + box.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return { hitSelf: top === node || node.contains(top), cx, cy, disabled: Boolean(node.disabled) };
  }).catch(() => null);
  note(`HIT ${label} ${JSON.stringify(hit)} t=${elapsed()}`);
  if (!hit || !hit.hitSelf || hit.disabled) return false;
  await page.mouse.click(hit.cx, hit.cy);
  await page.waitForTimeout(1500);
  return true;
};
const typeInto = async (locator, value, label) => {
  if (!(await locator.count())) { note(`MISS type-${label} absent t=${elapsed()}`); return false; }
  const box = locator.first();
  if (!(await box.isVisible().catch(() => false))) { note(`MISS type-${label} hidden t=${elapsed()}`); return false; }
  await box.click({ timeout: 8000 }).catch(() => undefined);
  await box.fill(value).catch(() => undefined);
  note(`TYPED ${label} ${JSON.stringify(await box.inputValue().catch(() => ""))} t=${elapsed()}`);
  return true;
};

note(`EXPLORE_STAGE_PROBE area=${await byTestId("rev-quick-area").count()} category=${await byTestId("rev-quick-category").count()} results=${await byTestId("rev-quick-results").count()} explore=${await byTestId("rev-quick-explore").count()} t=${elapsed()}`);
await survey("EXPLORE_ENTRY");

// Step 1 — the area pane: look the city up and take the geocoder's own centre.
if (await byTestId("rev-quick-area").count()) {
  await typeInto(page.locator('[data-testid="rev-quick-area"] input'), "北京市", "CITY");
  await pressNear(byTestId("rev-quick-find-city"), "find-city");
  for (let i = 0; i < 30 && !(await byTestId("rev-quick-city-results").count()); i += 1) await page.waitForTimeout(1000);
  const cityButtons = page.locator('[data-testid="rev-quick-city-results"] button');
  note(`CITY_RESULTS ${await cityButtons.count()} ${JSON.stringify((await cityButtons.allInnerTexts().catch(() => [])).slice(0, 3)).slice(0, 300)} t=${elapsed()}`);
  if (await cityButtons.count()) {
    await pressNear(cityButtons, "city-first");
    await page.waitForTimeout(2000);
    if (await byTestId("rev-quick-use-approx-center").count()) await pressNear(byTestId("rev-quick-use-approx-center"), "use-approx-center");
    await survey("AFTER_AREA");
  } else {
    note("NO_CITY_RESULT_SCREEN t=" + elapsed());
    await byTestId("rev-quick-photon-search").count() && pressNear(byTestId("rev-quick-photon-search"), "photon-search");
    await survey("AFTER_PHOTON");
  }
}

// Step 2 — the interest pane: name one place the traveller actually wants, and search.
for (let i = 0; i < 20 && !(await byTestId("rev-quick-results").count()); i += 1) await page.waitForTimeout(1500);
note(`RESULTS_PANE ${await byTestId("rev-quick-results").count()} t=${elapsed()}`);
await survey("INTEREST_OR_RESULTS");
const nameBox = page.locator('input[placeholder*="例如"]');
if (await nameBox.count()) {
  await typeInto(nameBox, "天坛", "PLACE_NAME");
  const searchButton = page.getByRole("button", { name: /搜索|查找|看结果/ });
  await pressNear(searchButton, "place-name-search");
  for (let i = 0; i < 40 && !(await byTestId("rev-quick-place-card").count()); i += 1) await page.waitForTimeout(1500);
}
await page.waitForTimeout(2000);

// Step 3 — read every card the provider returned, then look for the door that makes one of them
// the plan's place.
const cards = byTestIdPrefix("rev-quick-select-");
const cardCount = await cards.count();
const cardTexts = await page.locator('[data-testid="rev-quick-place-card"]').allInnerTexts().catch(() => []);
const blockers = await byTestIdPrefix("rev-quick-place-blocker-").allInnerTexts().catch(() => []);
note(`CARDS ${cardCount} t=${elapsed()}`);
note(`CARD_TEXTS ${JSON.stringify(cardTexts.slice(0, 4)).slice(0, 1200)}`);
note(`CARD_BLOCKERS ${JSON.stringify(blockers.slice(0, 6)).slice(0, 900)}`);
let formal = byTestIdPrefix("rev-quick-formal-");
note(`FORMAL_KEYS ${await formal.count()} t=${elapsed()}`);
if (!(await formal.count()) && cardCount) {
  // The cards carry their own fact-refresh door; use it on the first card the provider can name.
  const details = page.locator("details.rev-quick-place-blocker");
  note(`FACTS_DETAILS ${await details.count()} t=${elapsed()}`);
  for (let i = 0; i < Math.min(3, await details.count()); i += 1) {
    await details.nth(i).evaluate((node) => { node.open = true; }).catch(() => undefined);
  }
  const factKeys = byTestIdPrefix("rev-quick-facts-");
  note(`FACTS_KEYS ${await factKeys.count()} t=${elapsed()}`);
  for (let i = 0; i < Math.min(2, await factKeys.count()); i += 1) {
    await pressNear(factKeys.nth(i), `facts-${i}`);
    for (let k = 0; k < 20 && (await byTestIdPrefix("rev-quick-formal-").count()) === 0; k += 1) await page.waitForTimeout(2000);
    if ((await byTestIdPrefix("rev-quick-formal-").count()) > 0) break;
  }
  formal = byTestIdPrefix("rev-quick-formal-");
  note(`FORMAL_AFTER_FACTS ${await formal.count()} t=${elapsed()}`);
  await survey("EXPLORE_CARDS_FINAL");
}

// Step 4 — take the formal door, then read what the plan screen says.
const quickAlert = async () => (await page.locator(".rev-quick-alert").allInnerTexts().catch(() => [])).join(" ").slice(0, 400);
if (await formal.count()) {
  const pressed = await pressNear(formal, "formal-select", 20000);
  note(`FORMAL_PRESSED ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(6000);
  note(`FORMAL_ALERT ${JSON.stringify(await quickAlert())}`);
  note(`FORMAL_BODY ${JSON.stringify((await bodyText()).replace(/\s+/g, " ").slice(0, 600))} t=${elapsed()}`);
  await shot(`${TAG}-x-after-formal`);
} else {
  note(`NO_FORMAL_DOOR cards=${cardCount} alert=${JSON.stringify(await quickAlert())} t=${elapsed()}`);
  await shot(`${TAG}-x-no-formal-door`);
}

const planGaps = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
note(`X_PLAN_GAPS ${JSON.stringify(planGaps).slice(0, 800)} t=${elapsed()}`);
const xSelect = page.locator('[data-testid="rev-plan-select"]');
const xStart = page.locator('[data-testid="rev-plan-start"]');
const xSelectState = (await xSelect.count()) ? await xSelect.first().isEnabled().catch(() => false) : false;
note(`X_SELECT ${await xSelect.count()} enabled=${xSelectState} X_START ${await xStart.count()} t=${elapsed()}`);
await survey("PLAN_AFTER_FORMAL");
if (await xSelect.count() && xSelectState) {
  await pressNear(xSelect, "select-final", 30000);
  await page.waitForTimeout(6000);
  const refusal = await page.locator(".rev-plan-message, [role='alert']").allInnerTexts().catch(() => []);
  note(`X_SELECT_REFUSAL ${JSON.stringify(refusal.slice(0, 2)).slice(0, 700)} t=${elapsed()}`);
  await shot(`${TAG}-x-after-select`);
  const readyStart = (await xStart.count()) ? await xStart.first().isEnabled().catch(() => false) : false;
  note(`X_START_READY ${await xStart.count()} enabled=${readyStart} t=${elapsed()}`);
  if (readyStart) {
    await pressNear(xStart, "start-journey", 40000);
    for (let i = 0; i < 40; i += 1) {
      const txt = await bodyText();
      if (/正在使用|旅程已开始|下一站/.test(txt)) break;
      await page.waitForTimeout(3000);
    }
    await page.waitForTimeout(4000);
    note(`X_ACTIVE_BODY ${JSON.stringify((await bodyText()).replace(/\s+/g, " ").slice(0, 700))} t=${elapsed()}`);
    await shot(`${TAG}-x-active`);
    const activityCount = await page.locator('[data-testid="rev-activity-row"], .rev-activity').count().catch(() => 0);
    note(`X_ACTIVITY_ROWS ${activityCount} t=${elapsed()}`);
    // The map arm of the same journey: the plan's stops must be on it, and their number must be the
    // schedule's number.
    await pressNear(page.getByRole("button", { name: /^地图$/ }), "map-layer", 20000);
    await page.waitForTimeout(4000);
    note(`X_MAP_COUNT_LINE ${JSON.stringify(await page.evaluate(() => (document.body.innerText.match(/地图地点 \d+ 处 · 高德地点 \d+ 处/) || [null])[0]))} t=${elapsed()}`);
    note(`X_MAP_PLANNED_TAGS ${await page.locator('[data-testid="rev-map-planned-stop"]').count()}`);
    note(`X_MAP_LIST_ITEMS ${await page.locator('ol[aria-label="地图地点"] li').count()}`);
    await shot(`${TAG}-x-map`);
  }
}
note(`X_END alert=${JSON.stringify(await quickAlert())} errors=${JSON.stringify(errors.slice(0, 3))} t=${elapsed()}`);
await ctx.close();
