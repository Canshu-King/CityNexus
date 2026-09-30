/* ORD-0503 · walk the 成员与权限 screen on the bytes this lane built, and read what paints.
 *
 * Two shapes: 1280x900 desktop and 390x844 touch.  Every assertion reads rendered text or a visible
 * control's own label -- a `data-*` attribute is never accepted as the screen, and this order in
 * particular removed two `data-disabled-reason` slots, so reading attributes here would have proven
 * the opposite of what is true.  At 390 a control also has to answer a point at its own centre,
 * because a row that a headless DOM check calls reachable can sit under the bottom bar.
 *
 * argv: node ord0503_walk_r1.cjs <preview-base> <journey-id-for-desktop> <journey-id-for-390> <out-dir>
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2];
const J_DESKTOP = process.argv[3];
const J_PHONE = process.argv[4];
const OUT = process.argv[5];
if (!BASE || !J_DESKTOP || !J_PHONE || !OUT) {
  process.stderr.write("usage: node ord0503_walk_r1.cjs <base> <desktop-journey> <phone-journey> <out>\n");
  process.exit(2);
}
fs.mkdirSync(OUT, { recursive: true });

/* The names this lane seeded its roster with. Matching a row by its rendered name is what makes a
   reading say "the row the traveller looked at" instead of "whatever row sat at index n". */
const PEOPLE = { b: "ORD0503-乙", c: "ORD0503-丙", owner: "ORD0503-甲" };

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const MACHINE = ["MEMBER_ADMIN_CAP_REACHED", "MEMBER_OWNER_CANNOT_LEAVE", "MEMBER_UNKNOWN",
  "MEMBER_MANAGE_NOT_PERMITTED", "MEMBER_ROLE_SELF_CHANGE_REFUSED", "MEMBER_OWNER_ROLE_IMMUTABLE",
  "MEMBER_ROLE_UNCHANGED", "MEMBER_ACTOR_NOT_IN_JOURNEY", "MEMBER_ACTOR_LAPSED",
  "MEMBER_SELF_EXIT_NOT_A_MEMBER", "MEMBER_ALREADY_WITHDRAWN", "actor_traveler_id", "reason_code",
  "[object Object]", "undefined", "undefined,"];

/* ORD-0436's own invite sentence names the field it signs with, in prose, on purpose: 「签名用的是这条
   行程自己的 traveler_id」. That is not a machine token leaking onto a row, so it is reported as a
   quoted sentence here instead of being counted as a hit. */
const FIELD_WORDS = ["traveler_id", "member_id", "invited_by"];

const read = (page) => page.evaluate(({ uuidSource, machineList, fieldWords }) => {
  const uuid = new RegExp(uuidSource, "i");
  const txt = (el) => (el ? el.innerText.replace(/\s+/g, " ").trim() : null);
  const all = document.body.innerText || "";
  const rows = Array.from(document.querySelectorAll('[data-testid="access-member-row"]'));
  return {
    panel_present: !!document.querySelector('[data-testid="access-panel"]'),
    roster_rows: rows.map((li) => txt(li)),
    role_change_buttons: document.querySelectorAll('[data-testid="access-member-role-change"]').length,
    self_exit_buttons: document.querySelectorAll('[data-testid="access-member-self-exit"]').length,
    role_choices_open: document.querySelectorAll('[data-testid="access-role-choices"]').length,
    role_options: Array.from(document.querySelectorAll('[data-testid="access-role-option"]'))
      .map((b) => txt(b)),
    admin_cap_words: txt(document.querySelector('[data-testid="access-admin-cap"]')),
    confirm_words: txt(document.querySelector('[data-testid="access-confirm-pending"]')),
    roster_refused: txt(document.querySelector('[data-testid="access-roster-refused"]')),
    invite_refused: txt(document.querySelector('[data-testid="access-write-refused"]')),
    disabled_reason_slots: Array.from(document.querySelectorAll("[data-disabled-reason]"))
      .map((el) => el.getAttribute("data-disabled-reason")),
    bare_uuids_on_screen: (all.match(new RegExp(uuidSource, "gi")) || []).length,
    uuid_regex_taken_from: uuidSource.slice(0, 24),
    uuid_sample_seen: (all.match(uuid) || [null])[0],
    machine_tokens: machineList.filter((token) => all.includes(token)),
    field_words_in_prose: (() => {
      const found = [];
      for (const token of fieldWords) {
        for (const el of Array.from(document.querySelectorAll("p, span, li"))) {
          const text = (el.innerText || "").replace(/\s+/g, " ").trim();
          if (text.includes(token) && text.length < 400) {
            found.push({ token, sentence: text.slice(0, 240), testid: el.getAttribute("data-testid") });
            break;
          }
        }
      }
      return found;
    })(),
    testids: Array.from(document.querySelectorAll("[data-testid]"))
      .map((el) => el.getAttribute("data-testid")),
  };
}, { uuidSource: UUID.source, machineList: MACHINE, fieldWords: FIELD_WORDS });

const centreHit = async (page, testid, nth) => {
  const loc = page.locator(`[data-testid="${testid}"]`).nth(nth ?? 0);
  if ((await loc.count()) === 0) return { testid, present: 0 };
  await loc.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  const box = await loc.boundingBox();
  if (!box) return { testid, present: 1, boundingBox: null };
  const cx = Math.round(box.x + box.width / 2);
  const cy = Math.round(box.y + box.height / 2);
  const answer = await page.evaluate(({ testid, cx, cy, nth }) => {
    const top = document.elementFromPoint(cx, cy);
    const want = document.querySelectorAll(`[data-testid="${testid}"]`)[nth];
    return {
      point: { cx, cy },
      element: top ? top.tagName.toLowerCase() + "." + (top.className || "") : null,
      is_the_control: top === want,
      width_px: Math.round(want.getBoundingClientRect().width),
      height_px: Math.round(want.getBoundingClientRect().height),
      disabled: !!want.disabled,
    };
  }, { testid, cx, cy, nth: nth ?? 0 });
  return answer;
};

const pickTrip = async (page, journeyId) => {
  await page.goto(`${BASE}/v8/${journeyId}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);
  await page.goto(`${BASE}/v8/access`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);
  const picker = page.locator('[data-testid="access-journey-picker"]');
  if ((await picker.count()) === 0) return { picker_present: 0 };
  await picker.selectOption(journeyId);
  await page.waitForSelector('[data-testid="access-member-row"]', { timeout: 40000 });
  await page.waitForTimeout(2500);
  return { picker_present: 1, options: (await picker.locator("option").allInnerTexts())
    .map((t) => t.replace(/\s+/g, " ").trim()) };
};

const press = async (page, selector, timeout = 15000) => {
  const loc = page.locator(selector).first();
  if ((await loc.count()) === 0) return { pressed: false, selector };
  await loc.click({ timeout });
  await page.waitForTimeout(1800);
  return { pressed: true, selector };
};

/* The control inside one particular roster row: the row index goes through `.nth()` on the locator,
   because `:nth-match` is not a pseudo this tree's Playwright resolves. */
const pressInRow = async (page, rowIndex, testid) => {
  const rows = page.locator('[data-testid="access-member-row"]');
  if ((await rows.count()) <= rowIndex) {
    return { pressed: false, reason: "row index past the roster", rowIndex };
  }
  const loc = rows.nth(rowIndex).locator(`[data-testid="${testid}"]`).first();
  if ((await loc.count()) === 0) {
    return { pressed: false, reason: "no such control in that row", rowIndex, testid };
  }
  await loc.click({ timeout: 15000 });
  await page.waitForTimeout(1800);
  return { pressed: true, rowIndex, testid };
};

(async () => {
  const browser = await chromium.launch();
  const report = { base: BASE, runs: {} };

  /* ---------------------------------------------------------- desktop: the writes, for real */
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 200)); });
    const run = { shape: "1280x900", actions: {} };
    run.picked = await pickTrip(page, J_DESKTOP);
    run.before = await read(page);
    await page.screenshot({ path: path.join(OUT, "desktop_1_roster.png"), fullPage: true });

    // 1. a promotion the door accepts: the first collaborator row, into 管理员
    const rowOf = async (needle) => page.locator('[data-testid="access-member-row"]', { hasText: needle });
    const secondCol = run.before.roster_rows.findIndex((t) => t.includes(PEOPLE.b));
    run.actions.role_open = await pressInRow(page, secondCol, "access-member-role-change");
    run.after_open_choices = await read(page);
    run.actions.option_admin = await press(page, `[data-testid="access-role-option"]:has-text("管理员")`);
    run.confirm_shown = await read(page);
    run.actions.confirm_yes = await press(page, `[data-testid="access-confirm-yes"]`);
    run.after_promotion = await read(page);
    await page.screenshot({ path: path.join(OUT, "desktop_2_promoted.png"), fullPage: true });

    // 2. the same move one seat past the cap: the named sentence has to come off the server
    const thirdCol = run.after_promotion.roster_rows.findIndex((t) => t.includes(PEOPLE.c));
    run.actions.role_open_2 = await pressInRow(page, thirdCol, "access-member-role-change");
    run.actions.option_admin_2 = await press(page, `[data-testid="access-role-option"]:has-text("管理员")`);
    run.actions.confirm_yes_2 = await press(page, `[data-testid="access-confirm-yes"]`);
    run.after_cap_refusal = await read(page);
    await page.screenshot({ path: path.join(OUT, "desktop_3_cap_refused.png"), fullPage: true });

    // 3. the owner pressing 我自己退出: refused by name, and nothing about the row changes
    run.actions.self_exit = await press(page, `[data-testid="access-member-self-exit"]`);
    run.exit_confirm = await read(page);
    run.actions.exit_yes = await press(page, `[data-testid="access-confirm-yes"]`);
    run.after_exit_refusal = await read(page);
    await page.screenshot({ path: path.join(OUT, "desktop_4_owner_exit_refused.png"), fullPage: true });
    run.console_errors = errors;
    report.runs.desktop = run;
    await page.close();
  }

  /* ---------------------------------------- 390x844: the same screen, reached with a fingertip */
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 200)); });
    const run = { shape: "390x844", actions: {} };
    run.picked = await pickTrip(page, J_PHONE);
    run.before = await read(page);
    run.hits = {
      role_change: await centreHit(page, "access-member-role-change", 0),
      withdraw: await centreHit(page, "access-member-withdraw", 0),
      self_exit: await centreHit(page, "access-member-self-exit", 0),
    };
    await page.screenshot({ path: path.join(OUT, "phone_1_roster.png"), fullPage: true });
    run.actions.role_open = await press(page, `[data-testid="access-member-role-change"]`);
    run.after_open = await read(page);
    run.hits.role_option = await centreHit(page, "access-role-option", 0);
    await page.screenshot({ path: path.join(OUT, "phone_2_choices_open.png"), fullPage: true });
    run.actions.option_admin = await press(page, `[data-testid="access-role-option"]:has-text("管理员")`);
    run.actions.confirm_yes = await press(page, `[data-testid="access-confirm-yes"]`);
    run.after_promotion = await read(page);
    await page.screenshot({ path: path.join(OUT, "phone_3_promoted.png"), fullPage: true });
    run.console_errors = errors;
    report.runs.phone = run;
    await page.close();
  }

  await browser.close();
  process.stdout.write(JSON.stringify(report, null, 1) + "\n");
})().catch((e) => {
  process.stderr.write(String((e && e.message) || e) + "\n");
  process.exit(2);
});
