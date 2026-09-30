/*
 * ORD-0465 - walk the share-receiving screen on a real browser, on this lane's own front.
 *
 * Each arm asserts two separate things, because the order asks for both and they can disagree:
 *   the machine-readable half -- the `error.reason_code` this browser actually received in the body
 *   of the response to /api/v1/shared/journeys/..., captured off the network, not off the DOM; and
 *   the human half -- the words rendered on the screen, read out of the DOM's rendered text.
 * A screen that printed the right sentence while the body carried a different code would pass one and
 * fail the other, and only the pair means "the screen reads the server".
 *
 * Judged against the BUILT bundle served on :4931, not `npm run dev`, so these numbers describe the
 * artifact that ships. The backend on :8731 is this lane's own sqlite file.
 */
const fs = require("fs");
const path = require("path");
// Resolved by absolute path: this instrument lives outside the frontend tree, so a bare
// `require("playwright")` would search from run/ and find nothing.
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(LANE, "wt/frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const shotDir = path.join(REPO, "review/ord0465");
fs.mkdirSync(shotDir, { recursive: true });

const seed = JSON.parse(fs.readFileSync(path.join(LANE, "run/seed_report.json"), "utf-8"));
const T = seed.tokens;

const DESKTOP = { width: 1280, height: 900 };
const MOBILE = { width: 390, height: 844 };

const results = [];
let browser = null;

async function newPage(viewport, locale) {
  const context = await browser.newContext({
    viewport,
    locale,
    hasTouch: viewport.width < 500,
    isMobile: viewport.width < 500,
    deviceScaleFactor: viewport.width < 500 ? 3 : 1,
  });
  return context.newPage();
}

/** One navigation, with the door's own answer captured off the wire. */
async function open(page, url) {
  let door = null;
  let doorRead = Promise.resolve();
  const grab = (response) => {
    if (response.url().includes("/api/v1/shared/journeys/")) {
      door = { status: response.status(), url: response.url() };
      // The body is a second, later tick: hold the promise so the caller can await the reading
      // instead of racing it and reporting a `body: null` that only means "not yet".
      doorRead = response
        .json()
        .then((body) => {
          door.body = body;
        })
        .catch(() => {
          door.body = "UNPARSEABLE";
        });
    }
  };
  const requests = [];
  const countRequest = (request) => requests.push({ method: request.method(), url: request.url() });
  page.on("response", grab);
  page.on("request", countRequest);
  await page.goto(FRONT + url, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="shared-screen"]', { timeout: 20000 });
  await page.waitForTimeout(1200);
  const settled = await Promise.race([
    page.waitForFunction(() => {
      const el = document.querySelector('[data-testid="shared-screen"]');
      return el && el.getAttribute("data-shared-state") !== "loading";
    }, { timeout: 15000 }).then(() => true).catch(() => false),
    new Promise((resolve) => setTimeout(() => resolve(false), 16000)),
  ]);
  page.off("response", grab);
  page.off("request", countRequest);
  await doorRead;
  const state = await page.getAttribute('[data-testid="shared-screen"]', "data-shared-state");
  return {
    settled,
    state,
    door,
    requests,
    // The shared door is the only server call this screen is allowed to make.
    sharedDoorCalls: requests.filter((r) => r.url.includes("/api/v1/shared/journeys/")),
    writeCalls: requests.filter((r) => r.method !== "GET"),
    text: (await page.innerText("body")).replace(/\s+/g, " "),
  };
}

function record(arm, pass, detail) {
  results.push({ arm, pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"}  ${arm}  ${pass ? "" : JSON.stringify(detail).slice(0, 320)}`);
}

function codeIn(body) {
  return body && body.error ? body.error.reason_code : undefined;
}

async function refusalArm(name, url, expectedCode, expectedWords, forbiddenWords) {
  for (const [shape, viewport] of [["desktop", DESKTOP], ["mobile", MOBILE]]) {
    const page = await newPage(viewport, "zh-CN");
    const read = await open(page, url);
    const gotCode = codeIn(read.door && read.door.body);
    const wordsOnScreen = expectedWords.every((word) => read.text.includes(word));
    const forbiddenOnScreen = (forbiddenWords || []).filter((word) => read.text.includes(word));
    const onlyGetOneDoor =
      read.writeCalls.length === 0 && read.sharedDoorCalls.length === 1;
    await page.screenshot({ path: path.join(shotDir, `refusal_${name}_${shape}.png`) });
    record(`refusal/${name}/${shape}`,
      read.settled && gotCode === expectedCode && wordsOnScreen &&
        forbiddenOnScreen.length === 0 && onlyGetOneDoor,
      // `settled` is printed because it is the one conjunct with no reading beside it: an earlier
      // pass of this arm went red on a cold browser context with every value below correct, and the
      // detail could not say which of the five had failed. A red that cannot be diagnosed is not a
      // measurement -- and the fix here is to print more, not to widen the wall.
      { state: read.state, settled: read.settled, body_code: gotCode,
        door_status: read.door && read.door.status,
        expected: expectedCode, words_on_screen: wordsOnScreen,
        forbidden_found: forbiddenOnScreen, write_calls: read.writeCalls,
        shared_door_calls: read.sharedDoorCalls.length });
    await page.context().close();
  }
}

(async () => {
  browser = await chromium.launch({ channel: "chrome", headless: true });

  /* ---------------------------------------------------------------- the four states, by name */
  await refusalArm("unknown", `/v8/shared/${"z".repeat(32)}`, "SHARE_GRANT_UNKNOWN",
    ["这台服务器从来没有过这条链接"], []);
  await refusalArm("revoked", seed.urls.revoked, "SHARE_GRANT_REVOKED",
    ["已经收回了这条链接"], ["厦门两日"]);
  await refusalArm("expired", seed.urls.expired, "SHARE_GRANT_EXPIRED",
    ["那个时刻已经过去了"], ["已经收回", "厦门两日"]);
  await refusalArm("recycle_bin", seed.urls.binned, "SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN",
    ["放进了自己的回收站"], ["会被丢进回收站的那一趟", "厦门两日"]);
  await refusalArm("private", seed.urls.private, "SHARE_GRANT_NOT_LINK_READABLE",
    ["不是按「链接可读」分享的"], ["厦门两日"]);

  /* ------------------------------------------------------------------ the success arm */
  for (const [shape, viewport] of [["desktop", DESKTOP], ["mobile", MOBILE]]) {
    const page = await newPage(viewport, "zh-CN");
    const read = await open(page, seed.urls.valid);
    const stopNames = await page.$$eval('[data-testid="shared-stop-name"]', (els) =>
      els.map((el) => el.textContent.trim()),
    );
    const dayCount = await page.$$eval('[data-testid="shared-day"]', (els) => els.length);
    const doorStatus = read.door && read.door.status;
    const planState = read.door && read.door.body && read.door.body.plan_state;
    const titleOnScreen = read.text.includes("厦门两日 · 别人分享给我的那一趟");
    const stopText = (await page.innerText('[data-testid="shared-stop-name"]').catch(() => "")) || "";
    // The forbidden emptiness: a ready state whose body holds no visible stop.
    const emptyForAllThat = read.state === "ready" && stopNames.length === 0;
    await page.screenshot({
      path: path.join(shotDir, `success_${shape}.png`),
      fullPage: shape === "mobile",
    });
    record(`success/${shape}`,
      read.settled && doorStatus === 200 && planState === "PLAN_PRESENT" &&
        titleOnScreen && dayCount === 2 && stopNames.length === 3 && !emptyForAllThat &&
        stopText !== "" && read.writeCalls.length === 0,
      { state: read.state, door_status: doorStatus, plan_state: planState,
        title_on_screen: titleOnScreen, days: dayCount, stops: stopNames,
        write_calls: read.writeCalls.map((r) => `${r.method} ${r.url}`) });
    await page.context().close();
  }

  /* ------------------------- the stop's own name, not an id and not the planner's typed title */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    const read = await open(page, seed.urls.valid);
    const names = await page.$$eval('[data-testid="shared-stop-name"]', (els) =>
      els.map((el) => el.textContent.trim()),
    );
    const meta = await page.$$eval('[data-testid="shared-stop-meta"]', (els) =>
      els.map((el) => el.textContent.trim()),
    );
    const body = read.door.body;
    const doorNames = body.active_plan.stops.map((s) => s.place_name);
    const typedTitles = body.active_plan.stops.map((s) => s.title);
    const ids = body.active_plan.stops.map((s) => s.id);
    record("naming/place_name_not_the_typed_title",
      names.join("|") === doorNames.join("|") &&
        names.every((n) => !/^stop-\d$/.test(n)) &&
        !ids.some((id) => read.text.includes(id)) &&
        !typedTitles.some((t) => names.includes(t)),
      { rendered: names, from_door_place_name: doorNames, from_door_typed_title: typedTitles });
    // No bare ISO instant and no lock flag reaches the face of the screen.
    const rawIso = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(read.text);
    record("naming/no_bare_iso_instant_and_no_lock_word", !rawIso && !/locked|protected/i.test(read.text),
      { raw_iso_on_screen: rawIso, meta_lines: meta });
    // The property that caught a real defect here: a machine enumeration reaching a Chinese screen.
    // `activity_type` used to be painted through a label table that has no entry for it, so the page
    // read "sightseeing" between two Chinese headings. Anything shaped like a token -- UPPER_SNAKE,
    // or one of the specific vocabularies this answer carries -- must not be on the rendered face.
    const tokenish = read.text.match(/\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b/g) || [];
    const vocab = ["sightseeing", "visit", "transport", "SELECTED", "SUPERSEDED", "PLAN_PRESENT",
      "LINK_READ", "WGS84", "SHARE_GRANT"].filter((word) => read.text.includes(word));
    record("naming/no_machine_token_on_the_chinese_face",
      tokenish.length === 0 && vocab.length === 0,
      { upper_snake_found: tokenish, vocabulary_found: vocab });
    await page.context().close();
  }

  /* ------------------------------------------------------------------ the map is reused */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    await open(page, seed.urls.valid);
    const panel = await page.$('[data-testid="v8-maplibre-panel"]');
    const empty = await page.$('[data-testid="v8-map-empty"]');
    const markers = await page.$$eval(".v8-maplibre-canvas .maplibregl-marker", (els) => els.length)
      .catch(() => 0);
    record("map/real_map_component_mounted", Boolean(panel) && !empty,
      { panel: Boolean(panel), empty_state: Boolean(empty), markers });
    await page.screenshot({ path: path.join(shotDir, "map_panel.png") });
    await page.context().close();
  }

  /* ------------------------------------------ the plan-present-but-no-stops arm is a named arm */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    const read = await open(page, seed.urls.no_plan);
    // The property the order actually forbids is "loaded, and nothing on screen". The first version
    // of this judge asserted a body over 200 characters, which is not that property in either
    // direction -- it passes a page full of chrome around no explanation, and fails an honest
    // three-line sentence. Asserted instead: the state is named in its own words, the thing it is
    // naming (an empty day list) is genuinely absent, and the trip's own title is still there so the
    // reader knows which trip the sentence is about.
    const named = read.text.includes("这趟行程还没有选定的方案");
    const stopCells = await page.$$('[data-testid="shared-stop"]').catch(() => []);
    const dayCells = await page.$$('[data-testid="shared-day"]').catch(() => []);
    const titleStill = read.text.includes("还没有排定的那一趟");
    record("empty_guard/no_plan_is_said_not_blank",
      read.state === "ready" && named && stopCells.length === 0 && dayCells.length === 0 && titleStill,
      { state: read.state, plan_state: read.door.body.plan_state, named,
        stop_cells: stopCells.length, day_cells: dayCells.length, title_still: titleStill,
        body_len: read.text.length });
    await page.screenshot({ path: path.join(shotDir, "arm_no_plan.png") });
    await page.context().close();
  }

  /* -------------------------------------------------- no token in the address: nothing is asked */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    const read = await open(page, "/v8/shared/");
    record("address/no_token_asks_nothing",
      read.state === "no_token_in_address" && read.sharedDoorCalls.length === 0 &&
        read.text.includes("这个地址里没有分享暗号"),
      { state: read.state, door_calls: read.sharedDoorCalls.length, text_len: read.text.length });
    await page.screenshot({ path: path.join(shotDir, "arm_no_token.png") });
    await page.context().close();
  }

  /* --------------------------------------------------------- the route survives a hard reload */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    await open(page, seed.urls.valid);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="shared-screen"]', { timeout: 20000 });
    await page.waitForTimeout(1500);
    const state = await page.getAttribute('[data-testid="shared-screen"]', "data-shared-state");
    const path_ = await page.evaluate(() => window.location.pathname);
    const stillTitle = await page.innerText("body").then((t) => t.includes("厦门两日"));
    record("route/hard_reload_stays_on_the_screen",
      state === "ready" && path_ === `/v8/shared/${T.valid}` && stillTitle,
      { state, pathname: path_, title_still_on_screen: stillTitle });
    await page.screenshot({ path: path.join(shotDir, "after_reload.png") });
    await page.context().close();
  }

  /* ------------------------------------------------------------- the language switch is real */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    await open(page, seed.urls.expired);
    const before = await page.innerText("body");
    await page.click('[data-testid="shared-language"]');
    await page.waitForTimeout(700);
    const after = await page.innerText("body");
    record("i18n/switch_changes_the_words_on_screen",
      before.includes("那个时刻已经过去了") &&
        after.includes("that moment has passed") &&
        !after.includes("那个时刻已经过去了"),
      { zh_seen: before.includes("那个时刻已经过去了"), en_seen: after.includes("that moment has passed") });
    await page.screenshot({ path: path.join(shotDir, "after_language_switch.png") });
    await page.context().close();
  }

  /* ------------------------------------------------- touch targets: 44px on the phone, 30 on desktop */
  for (const [shape, viewport, expected] of [["mobile", MOBILE, 44], ["desktop", DESKTOP, 30]]) {
    const page = await newPage(viewport, "zh-CN");
    await open(page, seed.urls.revoked);
    const measured = {};
    for (const testId of ["shared-refresh", "shared-language"]) {
      const locator = page.locator(`[data-testid="${testId}"]`);
      await locator.scrollIntoViewIfNeeded();
      await page.waitForTimeout(250);
      const box = await locator.boundingBox();
      // An overlap check has to name what the finger actually landed on: `elementFromPoint` at the
      // centre must return this control or one of its own children, or the "target" is a different
      // element that happens to be somewhere with a data-testid.
      const centreHit = await page.evaluate(
        ([testId, x, y]) => {
          const owner = document.querySelector(`[data-testid="${testId}"]`);
          const hit = document.elementFromPoint(x, y);
          return Boolean(owner && hit && (hit === owner || owner.contains(hit)));
        },
        [testId, box.x + box.width / 2, box.y + box.height / 2],
      );
      measured[testId] = { h: Math.round(box.height), w: Math.round(box.width), centre_hit: centreHit };
    }
    const ok = Object.values(measured).every((m) =>
      // Both axes, not just the tall one: a 44px-high, 17px-wide button satisfies one and fails the
      // other. Desktop is held to the 30px the rest of the shell's quiet buttons use.
      shape === "mobile" ? m.h >= 44 && m.w >= 44 && m.centre_hit : m.h >= 30 && m.centre_hit,
    );
    // And a control that is 44px but hangs off the right edge of the phone is still not tappable, so
    // the same pass measures where it sits. This is what caught the language button at x=404 on a
    // 390px viewport.
    const overflow = await page.evaluate(() => {
      const width = document.documentElement.clientWidth;
      const outside = [];
      document
        .querySelectorAll('[data-testid="shared-refresh"], [data-testid="shared-language"]')
        .forEach((el) => {
          const box = el.getBoundingClientRect();
          if (box.right > width + 0.5 || box.left < -0.5) {
            outside.push({ testid: el.getAttribute("data-testid"), right: Math.round(box.right), width });
          }
        });
      return { outside, scroll_wider_than_viewport: document.documentElement.scrollWidth > width + 1 };
    });
    record(`touch/targets_${shape}`, ok && overflow.outside.length === 0 && !overflow.scroll_wider_than_viewport,
      { expected_min: expected, measured, outside_the_column: overflow.outside,
        page_overflows: overflow.scroll_wider_than_viewport });
    await page.screenshot({ path: path.join(shotDir, `targets_${shape}.png`) });
    await page.context().close();
  }

  /* ------------------- ORD-0474: the measured rows have to be RENDERED, not merely present in the DOM */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    await open(page, seed.urls.binned);
    const rows = await page.evaluate(() => {
      const want = ["shared-refusal-code", "shared-refused-content_type",
        "shared-refused-body_bytes", "shared-refused-http_status", "shared-refused-receipt"];
      const out = {};
      for (const id of want) {
        const el = document.querySelector(`[data-testid="${id}"]`);
        // `innerText`, not `textContent`: a closed <details> keeps every byte in the DOM and renders
        // none of them, which is exactly how these rows reached a reviewer as empty strings while the
        // previous judge still passed. textContent cannot see that defect; innerText can.
        out[id] = el ? { rendered: el.innerText.trim(), dom: el.textContent.trim(),
                         fold_open: el.closest("details") ? el.closest("details").open : null }
                      : { rendered: "ELEMENT ABSENT", dom: "ELEMENT ABSENT", fold_open: null };
      }
      return out;
    });
    const empty = Object.entries(rows).filter(([, v]) => !v.rendered || v.rendered === "ELEMENT ABSENT");
    const code = rows["shared-refusal-code"].rendered;
    const bytes = rows["shared-refused-body_bytes"].rendered;
    const status = rows["shared-refused-http_status"].rendered;
    const media = rows["shared-refused-content_type"].rendered;
    const receipt = rows["shared-refused-receipt"].rendered;
    const octets = parseInt(bytes.replace(/[^0-9]/g, ""), 10);
    record("ord0474/measured_rows_render_text",
      empty.length === 0 &&
        code.includes("SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN") &&
        /409/.test(status) && /application.json/.test(media) &&
        // The byte count is this device's own reading of the answer it received, so it has to be a
        // real number out of THIS response and never a placeholder.
        Number.isFinite(octets) && octets > 0 &&
        // The server does mint a receipt for a refusal. A line claiming none was given, about a body
        // that carried one, is the same class of defect as an empty line.
        !/NOT-EMITTED|no server receipt/.test(receipt),
      { empty_rows: empty.map(([k]) => k), code, status, media, bytes, receipt,
        fold_open: rows["shared-refusal-code"].fold_open });
    await page.screenshot({ path: path.join(shotDir, "refusal_details_open.png") });
    await page.context().close();
  }

  /* ---------------------------------- no token value is painted anywhere, in any arm */
  {
    const page = await newPage(DESKTOP, "zh-CN");
    const read = await open(page, seed.urls.valid);
    record("token/never_rendered", !read.text.includes(T.valid),
      { token_len: T.valid.length });
    await page.context().close();
  }

  const failed = results.filter((r) => !r.pass);
  const out = {
    front: FRONT,
    backend: "http://127.0.0.1:8731",
    lane_db: seed.lane_db,
    arms: results.length,
    passed: results.length - failed.length,
    failed: failed.map((f) => f.arm),
    results,
  };
  fs.writeFileSync(path.join(REPO, "review/ord0465/screen_arms_r1.json"),
    JSON.stringify(out, null, 2), { encoding: "utf-8" });
  console.log(`\nARMS=${results.length} PASSED=${results.length - failed.length} FAILED=${failed.length}`);
  await browser.close();
  process.exit(failed.length ? 1 : 0);
})().catch(async (error) => {
  console.error("DRIVER_ERROR", error && error.message);
  fs.writeFileSync(path.join(REPO, "review/ord0465/screen_arms_r1.json"),
    JSON.stringify({ driver_error: String(error && error.message), results }, null, 2),
    { encoding: "utf-8" });
  if (browser) await browser.close();
  process.exit(2);
});
