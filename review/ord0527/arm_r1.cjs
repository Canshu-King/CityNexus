/* ORD-0527 · the two arms the order names, run against whatever bundle is in dist right now.
 *
 * arm_present -- the store has a seat for the traveller this trip belongs to.  The screen must then
 *                really list the two controls, each answering a point at its own centre after
 *                scrollIntoViewIfNeeded, and the identity line must name the person.  Readings are
 *                `innerText`; no assertion in this file reads a `data-*` value as the screen.
 * arm_absent   -- the store has the trip but no member row for that traveller.  Nothing may grow:
 *                zero role-change controls, zero leaving controls, and the named sentence that says
 *                why.  This is the counterexample to "the screen invented a control".
 *
 * exit 0 = the arm held; exit 1 = the arm went red (which is what the masked-identity and the base
 * generation are expected to produce).  The pass/fail of each run is the reading, not a comment.
 */
const { chromium } = require("playwright");

const BASE = process.argv[2];
const MODE = process.argv[3];
const JOURNEY = process.argv[4];
const TRAVELLER = process.argv[5];
const EXPECT_JSON = process.argv[6] === "true";
const SHAPE = (process.argv[7] || "390x844").split("x").map(Number);
if (!BASE || !MODE || !JOURNEY) {
  process.stderr.write("usage: node ord0527_arm_r1.cjs <base> <arm_present|arm_absent> <journeyId> <travellerId> [expectJson]\n");
  process.exit(2);
}

const failures = [];
const checks = [];
const ok = (name, condition, reading) => {
  checks.push({ check: name, held: !!condition, reading: reading === undefined ? null : reading });
  if (!condition) failures.push(name);
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: SHAPE[0], height: SHAPE[1] } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 180)); });

  // the shell's own reference, dropped in the way the shell drops it (V8Experience writes this key)
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate(([key, value]) => window.localStorage.setItem(key, value),
                     ["citynexus.v8.journey_id", JOURNEY]);
  if (EXPECT_JSON) {
    // counterexample: mask the identity read the way a device with a refused storage area behaves
    await page.addInitScript(() => {
      const real = window.localStorage.getItem.bind(window.localStorage);
      window.localStorage.getItem = (k) => (String(k).endsWith("journey_id") ? null : real(k));
    });
    await page.evaluate(([key]) => window.localStorage.removeItem(key), ["citynexus.v8.journey_id"]);
  }
  await page.goto(BASE + "/v8/" + JOURNEY, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2600);
  await page.goto(BASE + "/v8/access", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3200);

  const read = await page.evaluate(() => {
    const txt = (sel) => {
      const el = document.querySelector(sel);
      return el ? el.innerText.replace(/\s+/g, " ").trim() : null;
    };
    const count = (sel) => document.querySelectorAll(sel).length;
    const body = document.body.innerText || "";
    return {
      panel: count('[data-testid="access-panel"]'),
      identity_words: txt('[data-testid="access-identity"]'),
      stale_words: txt('[data-testid="access-reference-stale"]'),
      no_authority_words: txt('[data-testid="access-no-authority"]'),
      roster_rows: Array.from(document.querySelectorAll('[data-testid="access-member-row"]'))
        .map((li) => li.innerText.replace(/\s+/g, " ").trim()),
      role_change: count('[data-testid="access-member-role-change"]'),
      self_exit: count('[data-testid="access-member-self-exit"]'),
      ladder_empty: count('[data-testid="access-role-ladder-empty"]'),
      roster_empty: count('[data-testid="access-roster-empty"]'),
      picker_present: count('[data-testid="access-journey-picker"]'),
      uuids: (body.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi) || []).length,
      words_withdraw_family: ["移出", "移除", "退出", "withdraw", "Withdraw", "Leave"].filter((w) => body.includes(w)).length,
    };
  });
  const NL = String.fromCharCode(10);
  const emit = (extra) => process.stdout.write(JSON.stringify(
    { mode: MODE, shape: SHAPE.join("x"), read, checks, failures, held: failures.length === 0, ...(extra || {}) }) + NL);
  console.error(JSON.stringify({ mode: MODE, shape: SHAPE.join("x"), read }, null, 1));

  if (MODE === "read") {
    // no assertions: this mode exists for the before/after pair the order asks for, where the
    // reading itself is the deliverable
    await browser.close();
    emit();
    process.exit(0);
  }
  if (MODE === "arm_present") {
    ok("panel mounted", read.panel === 1, read.panel);
    ok("ladder is NOT the empty cell", read.ladder_empty === 0, read.ladder_empty);
    ok("roster lists the seeded seats", read.roster_rows.length >= 2, read.roster_rows.length);
    ok("identity line names the person", read.identity_words !== null
      && read.identity_words.includes("ORD0527-甲") && !/[0-9a-f]{8}-[0-9a-f]{4}/.test(read.identity_words),
      read.identity_words);
    ok("a role-change control is listed", read.role_change >= 1, read.role_change);
    ok("a leaving control is listed", read.self_exit >= 1, read.self_exit);
    ok("no bare uuid on the screen", read.uuids === 0, read.uuids);
    for (const testid of ["access-member-role-change", "access-member-self-exit"]) {
      const loc = page.locator(`[data-testid="${testid}"]`).first();
      if ((await loc.count()) === 0) {
        ok(`${testid} exists to be hit`, false, 0);
        continue;
      }
      await loc.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      const box = await loc.boundingBox();
      ok(`${testid} has a box`, box !== null, box && { w: Math.round(box.width) });
      if (box) {
        const cx = Math.round(box.x + box.width / 2);
        const cy = Math.round(box.y + box.height / 2);
        const hit = await page.evaluate(({ cx, cy, testid }) => {
          const top = document.elementFromPoint(cx, cy);
          const want = document.querySelector(`[data-testid="${testid}"]`);
          return { top: top ? top.tagName.toLowerCase() + "." + (top.className || "") : null,
                   is_the_control: top === want,
                   h: Math.round(want.getBoundingClientRect().height) };
        }, { cx, cy, testid });
        ok(`${testid} centre hit`, hit.is_the_control === true, hit);
        // the touch floor is 44 px; the desktop floor this tree ships is 30 px (Amendment F), so the
        // threshold follows the viewport instead of being asserted at both shapes.
        const floor = SHAPE[0] <= 500 ? 44 : 30;
        ok(`${testid} is at least ${floor} px tall`, hit.h >= floor, { height: hit.h, floor });
      }
    }
    // and the two doors answer for real from this screen.  A control that is not there is a recorded
    // failure -- an arm that crashes on the masked build would prove nothing about the arm.
    if (read.role_change === 0) {
      ok("role choices cannot open without a control", false, "no role-change control on the screen");
    } else {
      await page.locator('[data-testid="access-member-role-change"]').first().click();
    }
    await page.waitForTimeout(1200);
    const options = await page.locator('[data-testid="access-role-option"]').allInnerTexts();
    ok("role choices came from the seat door", options.length >= 1,
       options.map((o) => o.replace(/\s+/g, " ").trim()));
    if (options.length >= 1) {
      await page.locator('[data-testid="access-role-option"]').first().click();
      await page.waitForTimeout(900);
      const confirm = page.locator('[data-testid="access-confirm-yes"]');
      ok("a confirmation step is offered before the write", (await confirm.count()) >= 1,
         await confirm.count());
      if ((await confirm.count()) >= 1) {
        await confirm.click();
        await page.waitForTimeout(2600);
      }
    }
    const after = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="access-member-row"]');
      const refused = document.querySelector('[data-testid="access-roster-refused"]');
      return { first_row: el ? el.innerText.replace(/\s+/g, " ").trim() : null,
               refused: refused ? refused.innerText.replace(/\s+/g, " ").trim() : null };
    });
    ok("the write answered with a human sentence, not a code",
       after.refused === null || !/[A-Z_]{10,}/.test(after.refused), after.refused);
  } else {
    ok("no role-change control grew", read.role_change === 0, read.role_change);
    ok("no leaving control grew", read.self_exit === 0, read.self_exit);
    ok("the screen says it has no seat for you",
       read.identity_words !== null && read.identity_words.includes("成员行"), read.identity_words);
    ok("a way in is on the screen", read.picker_present >= 1, read.picker_present);
    ok("no bare uuid on the screen", read.uuids === 0, read.uuids);
  }

  await browser.close();
  console.error(JSON.stringify({ mode: MODE, failures, held: failures.length === 0 }, null, 1));
  process.stdout.write(JSON.stringify({ mode: MODE, read, checks, failures }) + "\n");
  process.exit(failures.length === 0 ? 0 : 1);
})().catch((e) => {
  process.stderr.write("instrument failure: " + String((e && e.message) || e) + "\n");
  process.exit(2);
});
