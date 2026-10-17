/* Building walk: a person books a trip on a phone from a blank first screen, then tries to read the
 * day-by-day plan -- the part of the chain that needs a stay option.
 *
 * Why this route and not the sealed demo: measured on the live tip, the sealed demo journey's
 * `GET /api/v1/journeys/<id>/experience` answer carries options=0 and selected_option_id=null, so the
 * Hub day cards (frontend/src/app/V8Experience.tsx:3436) and the Studio day detail list (:3543) never
 * render at all -- which is itself a link in the chain to be measured, not assumed.  So this walk books
 * its own journey through the wizard, goes to 比较住宿, tries 生成住宿方案, and only then reads the
 * activity lines.  Every press must land (scrollIntoViewIfNeeded + elementFromPoint at the centre), and
 * every judgement is made from the words the browser actually rendered.
 *
 * argv: node walk_manual_daylist_r1.cjs <base> <out.json> <shotdir>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/tip1017_manual_daylist_before.json";
const SHOTS = process.argv[4] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/tip1017_manual_before";

const run = { schema: "CNX_BUILDING_MANUAL_DAYLIST_R1", base: BASE_URL,
  viewport: { width: 390, height: 844 }, started: new Date().toString(), steps: [], presses: [],
  fields: [], findings: [], page_errors: [], console_errors: [], verdict: null, outcome: "INCOMPLETE", shots: [] };

async function readScreen(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden"
        && Number(s.opacity) !== 0; };
    const latinRuns = (txt) => Array.from(new Set((txt.match(/[A-Za-z][A-Za-z .'-]{2,}/g) || [])
      .map((s) => s.trim()))).slice(0, 8);
    const dayCards = Array.from(document.querySelectorAll(".v8-day-card")).filter(vis).map((el) => {
      const p = el.querySelector("p");
      const txt = p ? strip(p.innerText) : "";
      return { site: "hub_day_card", heading: strip((el.querySelector("strong") || {}).innerText),
               text: txt, latin: latinRuns(txt), small: strip((el.querySelector("small") || {}).innerText) };
    });
    const rows = Array.from(document.querySelectorAll(".v8-activity")).filter(vis).map((el) => {
      const txt = strip((el.querySelector("span") || {}).innerText);
      return { site: "studio_activity_row", text: txt, latin: latinRuns(txt) };
    });
    const stayCards = Array.from(document.querySelectorAll("[data-testid='stay-offer-card']")).filter(vis)
      .map((el) => ({ site: "stay_offer_card", text: strip(el.innerText).slice(0, 120),
                      selected: el.className.includes("selected") }));
    const empty = Array.from(document.querySelectorAll("[data-testid]"))
      .filter((el) => /^stay-(no-options|generation-outcome|confirmed-line|budget-line|reload-absent)$/.test(el.getAttribute("data-testid") || ""))
      .filter(vis).map((el) => ({ testid: el.getAttribute("data-testid"), text: strip(el.innerText).slice(0, 200) }));
    const pressables = Array.from(document.querySelectorAll("button,[role='button'],a")).filter(vis)
      .map((el) => ({ testid: el.getAttribute("data-testid") || null,
                      words: strip(el.innerText || el.getAttribute("aria-label") || el.value).slice(0, 40),
                      disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true",
                      h: Math.round(el.getBoundingClientRect().height) })).slice(0, 30);
    const body = document.body.innerText || "";
    return { tag, path: location.pathname, day_cards: dayCards, activity_rows: rows, stay_cards: stayCards,
             stay_state: empty, pressables, zh_chars: (body.match(/[一-龥]/g) || []).length,
             body_text: strip(body).slice(0, 1800) };
  }, tag);
}

async function pressWord(page, re, tag) {
  const loc = page.locator("button,[role='button'],a").filter({ hasText: re }).first();
  if (await loc.count() === 0) return { tag, pressed: false, why: "NO_SUCH_CONTROL" };
  const hit = await loc.evaluate((el) => {
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { w: Math.round(b.width), h: Math.round(b.height), disabled: !!el.disabled,
             landed: !!top && (top === el || el.contains(top)),
             label: String(el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 36) };
  });
  if (hit.disabled) return { tag, pressed: false, why: "DISABLED", hit };
  if (!hit.landed) return { tag, pressed: false, why: "HIT_TEST_MISSED", hit };
  await loc.click();
  await page.waitForTimeout(1500);
  return { tag, pressed: true, hit };
}

async function pressTestId(page, testid, tag) {
  const loc = page.locator("[data-testid='" + testid + "']").first();
  if (await loc.count() === 0) return { tag, pressed: false, why: "NO_SUCH_TESTID" };
  const hit = await loc.evaluate((el) => {
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { w: Math.round(b.width), h: Math.round(b.height), disabled: !!el.disabled,
             landed: !!top && (top === el || el.contains(top) || (top && el.contains(top))) };
  });
  if (!hit.landed) return { tag, pressed: false, why: "HIT_TEST_MISSED", hit };
  await loc.click();
  await page.waitForTimeout(1500);
  return { tag, pressed: true, hit };
}

async function shot(page, name) {
  fs.mkdirSync(SHOTS, { recursive: true });
  const p = path.join(SHOTS, name + ".png");
  await page.screenshot({ path: p, fullPage: true });
  run.shots.push({ name, file: p, bytes: fs.statSync(p).size });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { (run.page_errors = run.page_errors || []).push(String(e).slice(0, 200)); });
  page.on("console", (m) => { if (m.type() === "error") (run.console_errors = run.console_errors || [])
    .push(m.text().slice(0, 200)); });

  await page.goto(BASE_URL + "/", { waitUntil: "networkidle", timeout: 60000 });
  run.steps.push(await readScreen(page, "first_screen"));
  await shot(page, "01_first_screen");

  for (const [testid, value] of [["trial-city", "北京"], ["trial-arrival", "北京站"], ["trial-departure", "天安门"]]) {
    const loc = page.locator("[data-testid='" + testid + "']").first();
    const present = await loc.count();
    if (!present) { run.fields.push({ testid, filled: false, why: "NO_SUCH_FIELD" }); continue; }
    const box = await loc.evaluate((el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return { w: Math.round(b.width), h: Math.round(b.height), tag: el.tagName,
               type: el.getAttribute("type") || null, visible: b.width > 0 && s.display !== "none" }; });
    await loc.fill(String(value));
    await page.waitForTimeout(400);
    const readback = await loc.evaluate((el) => el.value);
    run.fields.push({ testid, filled: true, box, readback });
  }
  await page.waitForTimeout(1200);
  run.steps.push(await readScreen(page, "after_fields"));

  let guard = 0;
  while (guard++ < 8) {
    const cur = await readScreen(page, "wizard" + guard);
    run.steps.push(cur);
    const confirm = cur.pressables.find((p) => /确认创建|创建行程|完成/.test(p.words) && !p.disabled);
    const next = cur.pressables.find((p) => /^下一步/.test(p.words) && !p.disabled);
    const target = confirm || next;
    if (!target) break;
    const r = await pressWord(page, new RegExp(target.words.slice(0, 6)), "wizard_press" + guard);
    run.presses.push(r);
    await shot(page, "02_wizard_" + guard);
    if (!r.pressed) break;
    if (confirm) break;
  }
  const created = await readScreen(page, "after_create");
  run.steps.push(created);
  await shot(page, "03_after_create");
  run.created_screen = { path: created.path, zh: created.zh_chars, day_cards: created.day_cards.length,
                         stay_cards: created.stay_cards.length,
                         has_creation_word: /已创建|创建成功|已为你创建/.test(created.body_text),
                         has_blocked_word: /还需要填写|请填写|不能为空|失败|错误|未识别/.test(created.body_text) };

  // now the stay leg, which is what gates the day-by-day plan
  const toStay = await pressWord(page, /比较住宿|选择住宿/, "open_stay");
  run.presses.push(toStay);
  await page.waitForTimeout(1200);
  const stay1 = await readScreen(page, "stay_first");
  run.steps.push(stay1);
  await shot(page, "04_stay_first");

  let stay2 = null;
  if (stay1.stay_cards.length === 0) {
    const gen = await pressTestId(page, "stay-generate", "generate_stay");
    run.presses.push(gen);
    await page.waitForTimeout(9000);
    stay2 = await readScreen(page, "stay_after_generate");
    run.steps.push(stay2);
    await shot(page, "05_stay_after_generate");
  }
  const stayReads = [stay1, stay2].filter(Boolean);
  const anyOptions = stayReads.some((s) => s.stay_cards.length > 0);

  let selected = null, hubBack = null;
  if (anyOptions) {
    const firstWith = stayReads.find((s) => s.stay_cards.length > 0);
    const idx = stayReads.indexOf(firstWith);
    const loc = page.locator("[data-testid='stay-offer-card']").first();
    const hit = await loc.evaluate((el) => { el.scrollIntoViewIfNeeded();
      const b = el.getBoundingClientRect();
      const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return { landed: !!top && (el.contains(top) || top === el), h: Math.round(b.height),
               words: String(el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 80) }; });
    selected = { tag: "pick_first_offer", pressed: hit.landed, hit, from_step: idx };
    run.presses.push(selected);
    if (hit.landed) { await loc.click(); await page.waitForTimeout(9000); }
    run.steps.push(await readScreen(page, "after_pick"));
    await shot(page, "06_after_pick");
    const back = await pressTestId(page, "nav-hub", "back_to_hub");
    run.presses.push(back);
    await page.waitForTimeout(1500);
    hubBack = await readScreen(page, "hub_after_pick");
    run.steps.push(hubBack);
    await shot(page, "07_hub_after_pick");
  }

  // fold: any activity line rendered on a Chinese screen that still carries a latin run
  for (const s of run.steps) {
    for (const line of (s.day_cards || []).concat(s.activity_rows || [])) {
      if (s.zh_chars < 40) { run.findings.push({ ...line, stop: s.tag, class: "SCREEN_NOT_CHINESE" }); continue; }
      if (line.latin.length > 0) run.findings.push({ ...line, stop: s.tag, class: "LATIN_RUN_ON_ZH_SCREEN" });
    }
  }
  const lines = run.steps.reduce((n, s) => n + (s.day_cards || []).length + (s.activity_rows || []).length, 0);
  run.line_count = lines;
  run.latin_line_count = run.findings.filter((f) => f.class === "LATIN_RUN_ON_ZH_SCREEN").length;

  if (!run.created_screen.has_creation_word && run.created_screen.has_blocked_word) run.verdict = "BLOCKED_AT_FORM";
  else if (!anyOptions) run.verdict = "NO_STAY_OPTIONS_REACHABLE";
  else if (lines === 0) run.verdict = "STAY_CHOSEN_BUT_NO_DAY_LINE_RENDERED";
  else if (run.latin_line_count > 0) run.verdict = "MIXED_LANGUAGE_ON_ZH_SCREEN";
  else run.verdict = "ALL_LINES_LOCALISED";
  run.outcome = "READ";
  run.finished = new Date().toString();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ verdict: run.verdict, base: BASE_URL, line_count: lines,
    latin_line_count: run.latin_line_count, created: run.created_screen,
    stay_option_counts: stayReads.map((s) => s.stay_cards.length),
    presses: run.presses.map((p) => ({ tag: p.tag, pressed: p.pressed, why: p.why || null })),
    fields: run.fields.map((f) => ({ testid: f.testid, filled: f.filled, readback: f.readback || null })),
    findings: run.findings.slice(0, 10),
    steps: run.steps.map((s) => ({ tag: s.tag, path: s.path, day: (s.day_cards || []).length,
      row: (s.activity_rows || []).length, stay: (s.stay_cards || []).length, zh: s.zh_chars })),
    page_errors: (run.page_errors || []).length, console_errors: (run.console_errors || []).length }, null, 1));
  await browser.close();
})();
