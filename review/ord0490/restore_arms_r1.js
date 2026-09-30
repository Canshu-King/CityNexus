/*
 * ORD-0490 -- the same address, read on both sides of the owner's 找回.
 *
 * ORD-0465 gave the recycle-bin state a name on this screen.  A name is only worth giving if the
 * state it names can end, so this instrument walks ONE address through three shapes and reads the
 * screen each time:
 *
 *   1. in the bin        -- the refusal face, named by the server's code, and the trip's own title
 *                           must NOT be on it;
 *   2. brought back      -- the traveller taps the one control the refusal face offers
 *                           (`shared-refresh`), the same page re-reads the same token, and this time
 *                           the day list, the stop names and the map are drawn;
 *   3. back in the bin   -- the owner drops it again and the already-open screen has to notice.
 *
 * Step 2 is the claim the order makes and the one a cached answer could fake: a browser that replayed
 * its own earlier 409 would still show a refusal after a real restore, and a browser that replayed
 * the 200 would show a trip its owner has just thrown away again.  So both the in-place tap and a
 * cold reload of the address are measured, and every request this device makes is logged and judged:
 * the receiving screen sends GETs and nothing else, and the 找回 is done through the owner's own door
 * against the backend, from this file, not from the traveller's browser.
 *
 * The trip here is `seed.journeys.restorable`, which `lane_seed_r1.py` bins through
 * `DELETE /api/v1/journeys/{id}`.  The ORD-0465 arms' own binned trip is left alone and a final
 * cross-isolation arm checks that it is still refusing -- two instruments sharing one row would make
 * whichever ran last decide whether the other can pass.
 *
 * Judged against the built bundle served on :4931 by `cmdr_static_api_proxy_r1.py --api 8731`, on
 * this lane's own sqlite file.  `http.request` is used for the doors so no `HTTP_PROXY` value can
 * stand between this file and the port it names -- the Node equivalent of `ProxyHandler({})`.
 */
const fs = require("fs");
const http = require("http");
const path = require("path");
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(REPO, "frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const BACKEND_PORT = 8731;
const shotDir = path.join(REPO, "review/ord0490");
fs.mkdirSync(shotDir, { recursive: true });

const seed = JSON.parse(fs.readFileSync(path.join(LANE, "run/seed_report.json"), "utf-8"));
const URL_UNDER_TEST = seed.urls.restorable;
const TOKEN = seed.tokens.restorable;
const JOURNEY_ID = seed.journeys.restorable;
const TITLE = "被主人找回之后还要再读的那一趟";
const BIN_WORDS = ["放进了自己的回收站"];
const BIN_CODE = "SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN";

const DESKTOP = { width: 1280, height: 900 };
const MOBILE = { width: 390, height: 844 };
const SHARED_DOOR = "/api/v1/shared/journeys/";

const results = [];
let browser = null;

function record(arm, pass, detail) {
  results.push({ arm, pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"}  ${arm}${pass ? "" : "  " + JSON.stringify(detail).slice(0, 400)}`);
}

/** One owner-door call, straight to the port this lane owns. */
function door(method, apiPath) {
  return new Promise((resolve, reject) => {
    const request = http.request(
      { host: "127.0.0.1", port: BACKEND_PORT, path: apiPath, method,
        headers: { "Content-Type": "application/json" } },
      (answer) => {
        const chunks = [];
        answer.on("data", (chunk) => chunks.push(chunk));
        answer.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf-8");
          let body = null;
          try { body = JSON.parse(raw || "null"); } catch { body = { unparsed: raw.slice(0, 200) }; }
          resolve({ status: answer.statusCode, body, bytes: Buffer.byteLength(raw, "utf-8") });
        });
      },
    );
    request.on("error", reject);
    request.end();
  });
}

/** A page that keeps its own account of what it asked and what the shared door answered. */
async function newPage(viewport, locale) {
  const context = await browser.newContext({
    viewport, locale, hasTouch: viewport.width < 500, isMobile: viewport.width < 500,
    deviceScaleFactor: viewport.width < 500 ? 3 : 1,
  });
  const page = await context.newPage();
  const log = { requests: [], doors: [] };
  page.on("request", (request) => log.requests.push({ method: request.method(), url: request.url() }));
  page.on("response", async (response) => {
    if (response.url().includes(SHARED_DOOR)) {
      let body = "UNPARSEABLE";
      try { body = await response.json(); } catch { /* a body this device cannot read is still a body */ }
      log.doors.push({ status: response.status(), content_type: response.headers()["content-type"], body });
    }
  });
  page.__log = log;
  return { page, context, log };
}

async function waitForScreen(page) {
  await page.waitForSelector('[data-testid="shared-screen"]', { timeout: 20000 });
  await page.waitForFunction(() => {
    const el = document.querySelector('[data-testid="shared-screen"]');
    return el && el.getAttribute("data-shared-state") !== "loading";
  }, { timeout: 15000 }).catch(() => null);
  await page.waitForTimeout(900);
}

async function coldLoad(viewport, locale = "zh-CN") {
  const opened = await newPage(viewport, locale);
  await opened.page.goto(FRONT + URL_UNDER_TEST, { waitUntil: "domcontentloaded" });
  await waitForScreen(opened.page);
  return opened;
}

const screenState = (page) => page.getAttribute('[data-testid="shared-screen"]', "data-shared-state");
const bodyText = (page) => page.innerText("body").then((t) => t.replace(/\s+/g, " "));
const stopNames = (page) => page.$$eval('[data-testid="shared-stop-name"]', (els) =>
  els.map((el) => el.textContent.trim())).catch(() => []);
const dayCount = (page) => page.$$eval('[data-testid="shared-day"]', (els) => els.length).catch(() => 0);

/** Tap the one control the refusal face offers, and hold the door's fresh answer for the caller. */
async function tapRefresh(page) {
  // A tap that asks the door nothing has to be reported as a red arm, not as a driver error: the
  // mutation control switches this line off deliberately, and an abort would hide every arm after it
  // (`red-by-design and .serial hides siblings` -- this lane's own trap list).
  let response = null;
  try {
    [response] = await Promise.all([
      page.waitForResponse((r) => r.url().includes(SHARED_DOOR), { timeout: 12000 }),
      page.click('[data-testid="shared-refresh"]'),
    ]);
  } catch {
    return { status: "NO RESPONSE AFTER THE TAP", body: null };
  }
  let body = "UNPARSEABLE";
  try { body = await response.json(); } catch { /* as above */ }
  await waitForScreen(page);
  return { status: response.status(), body };
}

function onlyGetsFromTheBrowser(log) {
  return log.requests.filter((r) => r.method !== "GET").map((r) => `${r.method} ${r.url}`);
}

(async () => {
  browser = await chromium.launch({ channel: "chrome", headless: true });

  /* ------------------------------------------------- prime: the trip starts in the bin */
  // This instrument moves the row out of the bin and back in, so it has to say where it began rather
  // than trusting the last run: `DELETE` on a trip already in the bin answers 409
  // `JOURNEY_ALREADY_DELETED` (`backend/app/main.py:3033-3037`), which is the same fact, already true.
  // Without this, a re-run after an aborted one would report `bin_face/*` red for a reason that has
  // nothing to do with the screen.
  const primed = await door("DELETE", `/api/v1/journeys/${JOURNEY_ID}`);
  record("primed/the_trip_is_in_the_bin_before_the_first_read",
    primed.status === 204 || (primed.status === 409 && primed.body && primed.body.error &&
      primed.body.error.reason_code === "JOURNEY_ALREADY_DELETED"),
    { delete_status: primed.status,
      reason_code: primed.body && primed.body.error ? primed.body.error.reason_code : undefined });

  /* ---------------------------------------------- shape 1: the trip is in the recycle bin */
  for (const [shape, viewport] of [["mobile", MOBILE], ["desktop", DESKTOP]]) {
    const opened = await coldLoad(viewport);
    const text = await bodyText(opened.page);
    const state = await screenState(opened.page);
    const doorAnswer = opened.log.doors.at(-1);
    const code = doorAnswer && doorAnswer.body && doorAnswer.body.error
      ? doorAnswer.body.error.reason_code : undefined;
    await opened.page.screenshot({ path: path.join(shotDir, `before_${shape}.png`),
      fullPage: shape === "mobile" });
    record(`bin_face/${shape}`,
      state === "refused" && doorAnswer && doorAnswer.status === 409 && code === BIN_CODE &&
        BIN_WORDS.every((word) => text.includes(word)) && !text.includes(TITLE) &&
        onlyGetsFromTheBrowser(opened.log).length === 0 && opened.log.doors.length === 1,
      { state, door_status: doorAnswer && doorAnswer.status, code, expected: BIN_CODE,
        words_on_screen: BIN_WORDS.every((w) => text.includes(w)), title_on_screen: text.includes(TITLE),
        write_calls: onlyGetsFromTheBrowser(opened.log), door_calls: opened.log.doors.length });
    if (shape === "mobile") {
      global.__binFace = opened;   // the same page is tapped in shape 2 -- a reload would not prove that
    } else {
      await opened.context.close();
    }
  }

  /* ------------------------- the control the traveller is given on that face has to be tappable */
  {
    const opened = global.__binFace;
    const locator = opened.page.locator('[data-testid="shared-refresh"]');
    await locator.scrollIntoViewIfNeeded();
    await opened.page.waitForTimeout(250);
    const box = await locator.boundingBox();
    const centreHit = await opened.page.evaluate(() => {
      const owner = document.querySelector('[data-testid="shared-refresh"]');
      const hit = document.elementFromPoint(
        owner.getBoundingClientRect().x + owner.getBoundingClientRect().width / 2,
        owner.getBoundingClientRect().y + owner.getBoundingClientRect().height / 2,
      );
      return Boolean(owner && hit && (hit === owner || owner.contains(hit)));
    });
    const insideColumn = await opened.page.evaluate(() => {
      const width = document.documentElement.clientWidth;
      const el = document.querySelector('[data-testid="shared-refresh"]');
      return { right: Math.round(el.getBoundingClientRect().right), width,
               overflows: document.documentElement.scrollWidth > width + 1 };
    });
    record("bin_face/refresh_control_is_tappable_on_the_phone",
      box.height >= 44 && box.width >= 44 && centreHit &&
        insideColumn.right <= insideColumn.width + 0.5 && !insideColumn.overflows,
      { height: Math.round(box.height), width: Math.round(box.width), centre_hit: centreHit, ...insideColumn });
  }

  /* ---------------- the rows ORD-0474 filled in have to be readable, not merely present */
  {
    const opened = global.__binFace;
    const rows = await opened.page.evaluate(() => {
      const want = ["shared-refusal-code", "shared-refused-content_type",
        "shared-refused-body_bytes", "shared-refused-http_status", "shared-refused-receipt"];
      return want.map((id) => {
        const el = document.querySelector(`[data-testid="${id}"]`);
        if (!el) return { id, missing: true };
        const box = el.getBoundingClientRect();
        return { id, missing: false, text: el.innerText.trim(),
                 top: Math.round(box.top), bottom: Math.round(box.bottom),
                 left: Math.round(box.left), right: Math.round(box.right) };
      });
    });
    const present = rows.filter((row) => !row.missing);
    const blank = present.filter((row) => !row.text);
    // Two rows sharing a vertical band is what "ran into one another" looks like measured: the phone
    // column wrapped the combined text, so no single judge reading one element's text can see it.
    const sharingALine = [];
    for (let a = 0; a < present.length; a += 1) {
      for (let b = a + 1; b < present.length; b += 1) {
        const x = present[a];
        const y = present[b];
        if (x.top < y.bottom - 1 && y.top < x.bottom - 1) sharingALine.push(`${x.id} / ${y.id}`);
      }
    }
    record("bin_face/each_measured_row_is_on_a_line_of_its_own",
      rows.every((row) => !row.missing) && blank.length === 0 && sharingALine.length === 0,
      { missing: rows.filter((r) => r.missing).map((r) => r.id), blank: blank.map((r) => r.id),
        sharing_a_line: sharingALine,
        rendered: present.map((r) => `${r.id}@${r.top}-${r.bottom}`) });
  }

  /* -------------------------------------------------- the owner brings it back, through its door */
  const restored = await door("POST", `/api/v1/journeys/${JOURNEY_ID}/undelete`);
  record("owner_door/restore_answered_200_for_this_trip",
    restored.status === 200 && restored.body && restored.body.id === JOURNEY_ID,
    { status: restored.status, echoes_id: restored.body && restored.body.id === JOURNEY_ID,
      reason_code: restored.body && restored.body.error ? restored.body.error.reason_code : undefined });

  /* ------------------------- shape 2: the SAME page, tapped again, reads the trip back */
  {
    const opened = global.__binFace;
    const answer = await tapRefresh(opened.page);
    const state = await screenState(opened.page);
    const text = await bodyText(opened.page);
    const names = await stopNames(opened.page);
    const days = await dayCount(opened.page);
    const panel = await opened.page.$('[data-testid="v8-maplibre-panel"]');
    // The pins are overlaid after the map's own style settles, which is a later tick than the panel
    // mounting.  Reading before it reports 0 and blames the door for the map's clock.
    await opened.page
      .waitForFunction(() => document.querySelectorAll(".maplibregl-marker").length >= 3, { timeout: 12000 })
      .catch(() => null);
    const markers = await opened.page.$$eval(".v8-maplibre-canvas .maplibregl-marker", (els) => els.length)
      .catch(() => 0);
    await opened.page.screenshot({ path: path.join(shotDir, "after_refresh_mobile.png"), fullPage: true });
    record("restored_face/same_page_rereads_into_the_trip",
      answer.status === 200 && answer.body && answer.body.plan_state === "PLAN_PRESENT" &&
        answer.body.id === JOURNEY_ID && state === "ready" && text.includes(TITLE) &&
        names.length === 3 && days === 2 && Boolean(panel) && markers === 3 &&
        // The emptiness this order must not fall into: "it reads again", with nothing drawn.
        names.every((n) => n !== "") && !names.some((n) => /^stop-\d$/.test(n)) &&
        onlyGetsFromTheBrowser(opened.log).length === 0 && opened.log.doors.length === 2,
      { door_status: answer.status, plan_state: answer.body && answer.body.plan_state,
        body_id_matches_trip: answer.body && answer.body.id === JOURNEY_ID, state,
        title_on_screen: text.includes(TITLE), stops: names, days, map_panel: Boolean(panel), markers,
        door_calls: opened.log.doors.length, write_calls: onlyGetsFromTheBrowser(opened.log) });
    const tokenPainted = text.includes(TOKEN);
    const rawIso = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text);
    const upperSnake = text.match(/\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b/g) || [];
    record("restored_face/no_token_no_bare_instant_no_machine_word",
      !tokenPainted && !rawIso && upperSnake.length === 0,
      { token_painted: tokenPainted, raw_iso: rawIso, upper_snake: upperSnake });
  }

  /* ------------------- shape 2, the other way in: a cold load of the same address reads ready */
  {
    const opened = await coldLoad(DESKTOP);
    const state = await screenState(opened.page);
    const text = await bodyText(opened.page);
    const answer = opened.log.doors.at(-1);
    await opened.page.screenshot({ path: path.join(shotDir, "after_reload_desktop.png") });
    record("restored_face/cold_reload_of_the_same_address_reads_ready",
      state === "ready" && answer && answer.status === 200 && text.includes(TITLE) &&
        (await stopNames(opened.page)).length === 3,
      { state, door_status: answer && answer.status, title_on_screen: text.includes(TITLE) });
    await opened.context.close();
  }

  /* ------------------------- shape 3: back in the bin, and the open screen has to notice */
  {
    const dropped = await door("DELETE", `/api/v1/journeys/${JOURNEY_ID}`);
    const opened = global.__binFace;
    const answer = await tapRefresh(opened.page);
    const state = await screenState(opened.page);
    const text = await bodyText(opened.page);
    await opened.page.screenshot({ path: path.join(shotDir, "back_in_bin_mobile.png") });
    record("back_in_bin/the_open_screen_refuses_again",
      dropped.status === 204 && answer.status === 409 && answer.body && answer.body.error &&
        answer.body.error.reason_code === BIN_CODE && state === "refused" &&
        BIN_WORDS.every((word) => text.includes(word)) && !text.includes(TITLE),
      { delete_status: dropped.status, door_status: answer.status,
        code: answer.body && answer.body.error ? answer.body.error.reason_code : undefined,
        state, title_still_on_screen: text.includes(TITLE) });
    await opened.context.close();
    delete global.__binFace;
  }

  /* ---------------- cross-isolation: the ORD-0465 arms' own binned trip was never touched here */
  {
    const other = await door("GET", `/api/v1/shared/journeys/${seed.tokens.binned}`);
    record("cross_isolation/ord0465_own_binned_trip_still_refuses",
      other.status === 409 && other.body && other.body.error &&
        other.body.error.reason_code === BIN_CODE && !JSON.stringify(other.body).includes("会被丢进回收站"),
      { status: other.status, code: other.body && other.body.error ? other.body.error.reason_code : undefined });
  }

  /* and the trip this instrument moved is left in the bin, so the file can be run twice in a row */
  const finalDoor = await door("GET", `/api/v1/shared/journeys/${TOKEN}`);
  record("world_left_as_found",
    finalDoor.status === 409 && finalDoor.body && finalDoor.body.error &&
      finalDoor.body.error.reason_code === BIN_CODE,
    { status: finalDoor.status, code: finalDoor.body && finalDoor.body.error ? finalDoor.body.error.reason_code : undefined });

  const failed = results.filter((r) => !r.pass);
  const out = {
    url_under_test: URL_UNDER_TEST,
    trip_id: JOURNEY_ID,
    front: FRONT,
    backend: `http://127.0.0.1:${BACKEND_PORT}`,
    lane_db: seed.lane_db,
    arms: results.length,
    passed: results.length - failed.length,
    failed: failed.map((f) => f.arm),
    results,
  };
  fs.writeFileSync(path.join(shotDir, "restore_arms_r1.json"), JSON.stringify(out, null, 2), { encoding: "utf-8" });
  console.log(`\nARMS=${results.length} PASSED=${results.length - failed.length} FAILED=${failed.length}`);
  await browser.close();
  process.exit(failed.length ? 1 : 0);
})().catch(async (error) => {
  console.error("DRIVER_ERROR", error && error.message);
  fs.writeFileSync(path.join(shotDir, "restore_arms_r1.json"),
    JSON.stringify({ driver_error: String(error && error.message), results }, null, 2), { encoding: "utf-8" });
  if (browser) await browser.close();
  process.exit(2);
});
