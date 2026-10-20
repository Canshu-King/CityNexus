/* Building walk, cell six: the eleven screens behind the phone drawer.

CMDR-ORDER-1130 put the fact on record: every census on this line walked only the six bottom-nav screens,
and the drawer's other eleven have never been measured.  This tool is the "can a person actually get
there and does anything answer" leg of that gap (the contrast-ratio leg is the commander's own ruler).

It is deliberately not a DOM-existence walk: the drawer is a collapsed layer, so an entry that exists in
the DOM and is not on screen would read as "reachable" to a naive tool.  For each entry this requires
(1) the drawer itself proven open -- the entry must be a visible node whose centre hit-test lands on it,
(2) the route to actually change after the press, (3) the screen to render something with a box, and then
censuses what a person would meet: controls under the 44 px touch contract, horizontal overflow, machine
vocabulary that reached the screen, and any alert/status line.

Every screen resets by re-opening the drawer, so one screen's scroll position cannot pollute the next.

argv: node walk_drawer_screens_r1.cjs <base> <out.json> <shotdir>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/drawer_screens.json";
const SHOTS = process.argv[4] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/drawer_shots";

const run = { schema: "CNX_BUILDING_DRAWER_SCREENS_R1", base: BASE_URL,
  viewport: { width: 390, height: 844 }, started: new Date().toString(), screens: [], notes: [],
  page_errors: [], console_errors: [], outcome: "INCOMPLETE" };

async function readPage(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden"
        && Number(s.opacity) !== 0; };
    const doc = document.documentElement;
    const controls = Array.from(document.querySelectorAll("button,[role='button'],a[href],input[type='submit'],input[type='checkbox']"))
      .filter(vis);
    const under44 = controls.filter((el) => el.getBoundingClientRect().height < 44).map((el) => ({
      testid: el.getAttribute("data-testid") || null,
      words: strip(el.innerText || el.getAttribute("aria-label") || el.value).slice(0, 34),
      h: Math.round(el.getBoundingClientRect().height), w: Math.round(el.getBoundingClientRect().width) }));
    const overflow = Array.from(document.querySelectorAll(".v8-page *, body *")).filter(vis)
      .map((el) => el.getBoundingClientRect())
      .filter((b) => b.right > window.innerWidth + 2 && b.width > 8)
      .length;
    const body = document.body.innerText || "";
    const codes = [];
    for (const [re, kind] of [[/\b[A-Z][A-Z0-9_]{4,}\b/g, "UPPER_SNAKE"],
        [/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g, "UUID"],
        [/\b(400|401|403|404|409|422|500|502|503)\b/g, "HTTP_STATUS"],
        [/\b(null|undefined|NaN|true|false)\b/g, "CODE_LITERAL"]]) {
      const m = body.match(re);
      if (m) codes.push({ kind, hits: Array.from(new Set(m)).slice(0, 6) });
    }
    return { tag, path: location.pathname, control_count: controls.length,
             controls_under_44: under44, under_44_count: under44.length,
             overflowing_nodes: overflow, horizontal: doc.scrollWidth > doc.clientWidth + 2,
             scroll_width: doc.scrollWidth, client_width: doc.clientWidth,
             headings: Array.from(document.querySelectorAll("h1,h2,h3")).filter(vis)
               .map((e) => strip(e.innerText)).slice(0, 6),
             alerts: Array.from(document.querySelectorAll("[role='alert'],[role='status']")).filter(vis)
               .map((e) => strip(e.innerText).slice(0, 140)).slice(0, 4),
             machine_vocabulary: codes,
             empty_states: Array.from(document.querySelectorAll(".v8-empty-state,[data-testid$='-empty']"))
               .filter(vis).map((e) => strip(e.innerText).slice(0, 120)).slice(0, 4),
             zh_chars: (body.match(/[一-龥]/g) || []).length,
             body_text: strip(body).slice(0, 900) };
  }, tag);
}

async function pressTestId(page, testid, tag) {
  const loc = page.locator("[data-testid='" + testid + "']").first();
  if (await loc.count() === 0) return { tag, pressed: false, why: "NO_SUCH_TESTID" };
  const hit = await loc.evaluate((el) => {
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return { w: Math.round(b.width), h: Math.round(b.height), in_viewport: b.top >= 0 && b.bottom <= innerHeight,
             landed: !!top && (top === el || el.contains(top) || top.contains(el)),
             disabled: !!el.disabled, testid: el.getAttribute("data-testid") };
  });
  if (!hit.landed) return { tag, pressed: false, why: "HIT_TEST_MISSED", hit };
  await loc.click();
  await page.waitForTimeout(1300);
  return { tag, pressed: true, hit };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(m.text().slice(0, 200)); });

  await page.goto(BASE_URL + "/", { waitUntil: "networkidle", timeout: 60000 });
  run.notes.push(await pressTestId(page, "trial-tianjin-demo", "anchor_demo"));
  await page.waitForTimeout(1500);

  // prove the drawer opens before trusting a single entry reading
  run.notes.push(await pressTestId(page, "v8-mobile-menu", "open_drawer"));
  const drawer = await page.evaluate(() => Array.from(document.querySelectorAll("[data-testid]"))
    .map((el) => el.getAttribute("data-testid"))
    .filter((t) => /^v8-drawer-entry-/.test(t || "")));
  const drawerVisible = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll("[data-testid]")).filter((el) =>
      /^v8-drawer-entry-/.test(el.getAttribute("data-testid") || ""));
    return els.filter((el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden"; }).length;
  });
  run.drawer_entries_testids = drawer;
  run.drawer_entries_visible = drawerVisible;
  if (drawer.length === 0 || drawerVisible === 0) {
    run.outcome = "BLOCKED_DRAWER_NOT_PROVEN";
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
    console.log(JSON.stringify({ outcome: run.outcome, entries: drawer.length, visible: drawerVisible }));
    await browser.close();
    return;
  }

  fs.mkdirSync(SHOTS, { recursive: true });
  for (const testid of drawer) {
    const key = testid.replace("v8-drawer-entry-", "");
    // reset: come back through the drawer every time, never from whatever state the last screen left
    const onHub = await page.evaluate(() => location.pathname);
    if (!/\/v8\/hub|^\/$/.test(onHub) || !(await page.evaluate((t) => !!document.querySelector(
      "[data-testid='" + t + "']") && document.querySelector("[data-testid='" + t + "']").offsetParent,
      testid))) {
      await page.goto(BASE_URL + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(1200);
      run.notes.push(await pressTestId(page, "v8-mobile-menu", "reopen_for_" + key));
    }
    const before = await page.evaluate(() => location.pathname);
    const p = await pressTestId(page, testid, "enter_" + key);
    await page.waitForTimeout(1400);
    const stop = await readPage(page, key);
    stop.press = p;
    stop.path_before = before;
    stop.route_changed = stop.path !== before;
    const shot = path.join(SHOTS, "screen_" + key + ".png");
    await page.screenshot({ path: shot });
    stop.shot_bytes = fs.statSync(shot).size;
    run.screens.push(stop);
  }

  run.totals = {
    screens_walked: run.screens.length,
    routes_that_did_not_change: run.screens.filter((s) => !s.route_changed).length,
    presses_that_missed: run.screens.filter((s) => !s.press.pressed).length,
    screens_with_machine_vocabulary: run.screens.filter((s) => s.machine_vocabulary.length).length,
    screens_with_horizontal_overflow: run.screens.filter((s) => s.horizontal).length,
    controls_under_44_sum: run.screens.reduce((n, s) => n + s.under_44_count, 0),
    screens_with_no_heading: run.screens.filter((s) => s.headings.length === 0).length };
  run.outcome = "READ";
  run.finished = new Date().toString();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ outcome: run.outcome, entries: drawer.length, visible: drawerVisible,
    totals: run.totals,
    per_screen: run.screens.map((s) => ({ key: s.tag, path: s.path, moved: s.route_changed,
      pressed: s.press.pressed, why: s.press.why || null, ctrls: s.control_count, u44: s.under_44_count,
      over: s.overflowing_nodes, horiz: s.horizontal, codes: s.machine_vocabulary.map((c) => c.kind),
      heads: s.headings.length, zh: s.zh_chars })),
    page_errors: run.page_errors.length, console_errors: run.console_errors.length }, null, 1));
  await browser.close();
})();
