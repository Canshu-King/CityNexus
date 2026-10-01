/* ORD-0538 · the hit test the roadmap asks for, on rendered text, in both language arms.
 *
 * r3 changes the scroll the assertion is taken at, and says why with numbers.  r1 asserted the centre
 * hit after Playwright's `scrollIntoViewIfNeeded()`, which scrolls the *least* amount that makes a box
 * visible -- and "visible" does not know that `.v8-mobile-nav` is `position: fixed` over the bottom
 * 76 px.  Measured on the Chinese arm at 390x844: box top 762, nav top 768, document scroll offset 0,
 * centre resolves to `nav.v8-mobile-nav`.  One traveller drag later (`block: "center"`) the same
 * control resolves to `button.cn-access-row-action` at (69, 422).  So the control is liftable and the
 * red was the instrument's, not the product's; the fix belongs in this file, not in the stylesheet.
 *
 * What is still asserted, in both language arms:
 *   the centre of a control, positioned the way a traveller can position it, resolves to that control;
 *   the whole box clears the fixed bar -- a control whose bottom still sits in the nav band has not
 *     actually been freed;
 *   the tap target is at least 44 px tall at this width (Amendment F: 44 px is the mobile floor).
 * The opening position (document at offset 0) is measured and reported beside it, never asserted: a
 * panel longer than the viewport necessarily has content under the fold at that offset, and calling
 * that a defect would be the vacuous kind of green-in-reverse.
 *
 * argv: node ord0538_arm_r3.cjs <preview-base> <no_anything|roles_empty|reachability> <zh-CN|en>
 *       <journeyId> <ownerId>
 */
const { chromium } = require("playwright");

const BASE = process.argv[2];
const CASE = process.argv[3];
const LOCALE = process.argv[4];
const JOURNEY = process.argv[5];
const OWNER = process.argv[6];
/* Two shapes, because the touch floor is not one number in this tree: 44 px belongs to the phone
   arm and 30 px to the desktop pointer (Amendment F, and the standing ruling ORD-0462 wrote into
   `access.css`).  The check names carry the shape and the floor they used. */
const SHAPE = process.argv[7] || "390x844";
const [VIEW_W, VIEW_H] = SHAPE.split("x").map((n) => parseInt(n, 10));
const VIEWPORT = { width: VIEW_W, height: VIEW_H };
const FLOOR_PX = VIEW_W <= 680 ? 44 : 30;
const AT = `[${LOCALE}@${SHAPE}]`;
const REACHABILITY = CASE === "reachability";
/* Three shapes are measured as walls, not asserted as arms: with no trip listed, with trips listed and
   no reference stored, and with a reference the list does not know.  All three are how the fifth empty
   cell would have to be reached, and what paints in each is the finding -- the panel is not mounted,
   so nothing inside it can be tapped or tested. */
const WALL = REACHABILITY || CASE === "roles_no_pick" || CASE === "roles_no_ref";

const CELLS = {
  roles_empty: [
    { testid: "access-role-ladder-empty", action: "access-empty-reload-roles" },
  ],
  no_anything: [
    { testid: "access-activity-empty", action: "access-empty-reload-activity" },
    { testid: "access-roster-empty", action: "access-empty-focus-invite" },
    { testid: "access-grant-empty", action: "access-empty-issue-link-grant" },
  ],
};

/* What each action is supposed to *do*.  A centre that resolves to the control only proves the tap
   lands; ORD-0527 was exactly the case where taps landed on controls that did nothing.  So each
   action is clicked and its own effect is read back: the door it re-asks has to be asked, the field
   it moves to has to hold focus, the write has to come back as a row. */
const EFFECT = {
  "access-empty-reload-activity": { kind: "request", needle: "/agent-feed" },
  "access-empty-reload-roles": { kind: "request", needle: "/acl/roles" },
  "access-empty-focus-invite": { kind: "focus", testid: "access-invite-visibility" },
  "access-empty-pick-trip": { kind: "focus", testid: "access-journey-picker" },
  "access-empty-issue-link-grant": { kind: "write" },
  "access-empty-open-today": { kind: "navigate" },
};

const failures = [];
const checks = [];
const ok = (name, held, reading) => {
  checks.push({ check: name, held: !!held, reading: reading === undefined ? null : reading });
  if (!held) failures.push(name);
};
const report = (name, reading) => {
  checks.push({ check: name, held: null, reading: reading });
};

const HIT = (testid) => {
  const want = document.querySelector(`[data-testid="${testid}"]`);
  if (!want) return { absent: true };
  const rect = want.getBoundingClientRect();
  const nav = document.querySelector(".v8-mobile-nav");
  const shown = nav && getComputedStyle(nav).display !== "none";
  const nb = shown ? nav.getBoundingClientRect() : null;
  const cx = Math.round(rect.left + rect.width / 2);
  const cy = Math.round(rect.top + rect.height / 2);
  const top = document.elementFromPoint(cx, cy);
  return {
    point: { cx, cy },
    top: top ? top.tagName.toLowerCase() + "." + (top.className || "") : null,
    is_the_control: top === want,
    width_px: Math.round(rect.width),
    height_px: Math.round(rect.height),
    box_top_px: Math.round(rect.top),
    box_bottom_px: Math.round(rect.bottom),
    nav_visible: !!nb,
    nav_top_px: nb ? Math.round(nb.top) : null,
    scroll_top_px: Math.round((document.scrollingElement || document.documentElement).scrollTop),
  };
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: VIEWPORT });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });

  const requests = [];
  page.on("request", (r) => requests.push(r.url()));

  /* For `roles_no_pick` the reference has to exist and has to be one the list does not know: with the
     key simply absent the shell paints its own onboarding wizard and this panel never mounts -- the
     same measured wall the `reachability` case ran into.  A stored id the list cannot match is the
     shape where the panel is up, nothing is picked, and the picker is the way forward. */
  const UNKNOWN_REFERENCE = "00000000-0000-4000-8000-000000000538";
  const seeded = CASE === "no_anything" || CASE === "roles_empty" ? JOURNEY
    : CASE === "roles_no_pick" ? UNKNOWN_REFERENCE : null;

  await page.addInitScript(([locale, journey]) => {
    window.localStorage.setItem("citynexus.locale", locale);
    if (journey) window.localStorage.setItem("citynexus.v8.journey_id", journey);
    else window.localStorage.removeItem("citynexus.v8.journey_id");
  }, [LOCALE, seeded]);

  await page.goto(BASE + "/v8/access", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(CASE === "reachability" ? 3200 : 5200);

  if (WALL) {
    const seen = await page.evaluate(() => ({
      panel: document.querySelectorAll('[data-testid="access-panel"]').length,
      trips_empty_cell: document.querySelectorAll('[data-testid="access-trips-empty"]').length,
      ladder_empty_cell: document.querySelectorAll('[data-testid="access-role-ladder-empty"]').length,
      testids: Array.from(document.querySelectorAll("[data-testid]"))
        .map((el) => el.getAttribute("data-testid")).slice(0, 24),
      words: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 220),
    }));
    process.stdout.write(JSON.stringify({ case: CASE, locale: LOCALE, wall: seen,
                                          failures: [] }) + String.fromCharCode(10));
    await browser.close();
    process.exit(0);
  }

  const cells = [];
  for (const cell of CELLS[CASE]) {
    const found = await page.evaluate(({ testid, action }) => {
      const el = document.querySelector(`[data-testid="${testid}"]`);
      const btn = document.querySelector(`[data-testid="${action}"]`);
      /* A missing cell and a missing screen are different findings; a red that cannot say which it
         saw is the kind that gets "fixed" in the wrong file. */
      if (!el) return { present: 0, panel_mounted:
        document.querySelectorAll('[data-testid="access-panel"]').length,
        painted: Array.from(document.querySelectorAll("[data-testid]"))
          .map((e) => e.getAttribute("data-testid")).slice(0, 10),
        words: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 90) };
      const words = el.innerText.replace(/\s+/g, " ").trim();
      return {
        present: 1,
        words,
        has_action: !!btn && el.contains(btn),
        action_words: btn ? btn.innerText.replace(/\s+/g, " ").trim() : null,
        uuid_in_words: /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(words),
        token_in_words: /token|令牌/.test(words),
      };
    }, cell);
    cells.push({ ...cell, ...found });
  }

  for (const cell of cells) {
    ok(`${AT} ${cell.testid} is on screen`, cell.present === 1,
       { present: cell.present, panel_mounted: cell.panel_mounted, painted: cell.painted,
         words: cell.words });
    if (!cell.present) continue;
    ok(`${AT} ${cell.testid} carries an action`, cell.has_action === true, cell.action_words);
    ok(`${AT} ${cell.testid} says no uuid and no field name`,
       cell.uuid_in_words === false && cell.token_in_words === false,
       { uuid: cell.uuid_in_words, token: cell.token_in_words, words: cell.words.slice(0, 90) });
    const loc = page.locator(`[data-testid="${cell.action}"]`).first();
    if ((await loc.count()) === 0) {
      ok(`${AT} ${cell.action} exists to be hit`, false, 0);
      continue;
    }

    /* Where the panel leaves it before anybody touches anything. Reported, not asserted. */
    await page.evaluate(() => {
      const se = document.scrollingElement || document.documentElement;
      se.scrollTop = 0;
    });
    await page.waitForTimeout(200);
    const opening = await page.evaluate(HIT, cell.action);
    report(`${AT} ${cell.action} reading at the opening scroll offset`, opening);

    /* The asserted shape: the traveller drags the panel until the control sits mid-screen. */
    await page.evaluate((t) => {
      document.querySelector(`[data-testid="${t}"]`)
        .scrollIntoView({ block: "center", inline: "nearest" });
    }, cell.action);
    await page.waitForTimeout(300);
    const hit = await page.evaluate(HIT, cell.action);
    ok(`${AT} ${cell.action} centre hit after a traveller scroll`,
       hit.is_the_control === true, { at_opening_scroll: opening.point, hit });
    ok(`${AT} ${cell.action} clears the fixed bar entirely once scrolled`,
       hit.nav_top_px === null || hit.box_bottom_px <= hit.nav_top_px,
       { nav_visible: hit.nav_visible, box_bottom_px: hit.box_bottom_px,
         nav_top_px: hit.nav_top_px });
    ok(`${AT} ${cell.action} is at least ${FLOOR_PX} px tall at ${SHAPE}`,
       hit.height_px >= FLOOR_PX, { height_px: hit.height_px, width_px: hit.width_px });
    cell.opening = opening;
    cell.hit = hit;
  }

  /* Every action but the write is clicked here and its effect read back; the write is the next
     section, because it changes the very cell this arm is standing on. */
  for (const cell of cells) {
    const want = EFFECT[cell.action] || {};
    if (cell.present !== 1 || want.kind === "write" || want.kind === undefined) {
      report(`${AT} ${cell.action} effect`, "not clicked here: " + (want.kind || "no effect named"));
      continue;
    }
    const loc = page.locator(`[data-testid="${cell.action}"]`).first();
    if ((await loc.count()) === 0) continue;
    await page.evaluate((t) => {
      document.querySelector(`[data-testid="${t}"]`)
        .scrollIntoView({ block: "center", inline: "nearest" });
    }, cell.action);
    const asked_before = want.kind === "request"
      ? requests.filter((u) => u.indexOf(want.needle) >= 0).length : 0;
    await loc.click({ timeout: 8000 }).catch(() => { /* the hit checks above already own this red */ });
    await page.waitForTimeout(want.kind === "request" ? 2600 : 700);
    if (want.kind === "request") {
      const asked_after = requests.filter((u) => u.indexOf(want.needle) >= 0).length;
      ok(`${AT} ${cell.action} re-asks the door it names (${want.needle})`,
         asked_after > asked_before, { before: asked_before, after: asked_after });
    } else {
      const held = await page.evaluate((t) => {
        const el = document.activeElement;
        return el ? el.getAttribute("data-testid") === t : false;
      }, want.testid);
      const who = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? el.tagName.toLowerCase() + "." + (el.getAttribute("data-testid") || el.className || "")
                  : null;
      });
      ok(`${AT} ${cell.action} moves the pointer to ${want.testid}`, held === true,
         { active: who });
    }
  }

  /* The one action that writes: the row has to come back from the door, not from this device. */
  let before = null, after = null;
  if (CASE === "no_anything") {
    before = await page.evaluate(() =>
      document.querySelectorAll('[data-testid="access-grant-row"]').length);
    const grant = page.locator('[data-testid="access-empty-issue-link-grant"]').first();
    let click_error = null;
    if ((await grant.count()) > 0) {
      await page.evaluate((t) => {
        document.querySelector(`[data-testid="${t}"]`)
          .scrollIntoView({ block: "center", inline: "nearest" });
      }, "access-empty-issue-link-grant");
      /* A control something else is sitting on cannot be clicked: that is the pointer-interception
         error, and under the `pin` generation it is the finding. It has to land as a reading here,
         not as a thrown instrument. */
      await grant.click({ timeout: 8000 }).catch((e) => {
        click_error = String((e && e.message) || e).split("\n")[0].slice(0, 140);
      });
      await page.waitForTimeout(3200);
    }
    after = await page.evaluate(() => ({
      rows: document.querySelectorAll('[data-testid="access-grant-row"]').length,
      still_empty_cell: document.querySelectorAll('[data-testid="access-grant-empty"]').length,
      refused: (() => {
        const el = document.querySelector('[data-testid="access-roster-refused"]');
        return el ? el.innerText.replace(/\s+/g, " ").trim() : null;
      })(),
      first_row: (() => {
        const el = document.querySelector('[data-testid="access-grant-row"]');
        return el ? el.innerText.replace(/\s+/g, " ").trim().slice(0, 140) : null;
      })(),
    }));
    ok(`${AT} the invitation action wrote a row the screen can read back`,
       before === 0 && after.rows >= 1 && after.still_empty_cell === 0 && click_error === null,
       { before, click_error, after });
    ok(`${AT} the read-back names the visibility in words, not a machine token`,
       after.rows >= 1 && !/LINK_READ|VISIBILITY_|http_status/.test(after.first_row || ""),
       (after.first_row || "").slice(0, 90));
  }

  await browser.close();
  const out = { case: CASE, locale: LOCALE, viewport: `${VIEWPORT.width}x${VIEWPORT.height}`,
                cells, checks, grant_rows_before: before, grant_rows_after: after,
                console_errors: errors, failures };
  process.stdout.write(JSON.stringify(out) + String.fromCharCode(10));
  process.stderr.write(`${CASE}/${LOCALE} failures: ${JSON.stringify(failures)}${String.fromCharCode(10)}`);
  process.exit(failures.length === 0 ? 0 : 1);
})().catch((e) => {
  process.stderr.write("instrument threw: " + String((e && e.message) || e) + String.fromCharCode(10));
  process.stdout.write(JSON.stringify({ case: CASE, locale: LOCALE, failures:
    ["instrument threw: " + String((e && e.message) || e).slice(0, 160)] }) + String.fromCharCode(10));
  process.exit(1);
});
