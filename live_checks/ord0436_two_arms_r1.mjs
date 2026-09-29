#!/usr/bin/env node
/**
 * ORD-0436 -- read the 成员与权限 screen in both languages, and report only what the browser held.
 *
 * Invoked by `ord0436_two_arms_r1.py`, which owns the two processes and proves the answers came from
 * this lane's backend and this lane's database. This file's job is the reading: what text is on the
 * screen, in which language, whether the two confirmation sentences really differ, and whether the
 * one control a traveller can use is under the finger at phone size.
 *
 * Every check reads rendered text (`innerText` / `allInnerTexts`), never a `data-*` attribute -- a
 * machine token in an attribute is not a sentence a traveller read. The attributes are collected
 * too, but only as identity (which row is which), and nothing passes on them.
 */
import { chromium } from "playwright";
// The ladder's domain is read from the artifacts the server publishes, not from a remembered
// list: `contracts/openapi.yaml` and the generated client, through `ord0436_contract_domain.mjs`.
import { contractDomain } from "./ord0436_contract_domain.mjs";
import { readFileSync } from "node:fs";

/** The shared dictionary's sentences for the scope keys the ACL door names. Read from the file
* the server's key indexes, so a screen that rendered a lane-local copy of the words would fail.
 */
function dictionaryScopes() {
  const body = readFileSync(`${REPO}/frontend/src/i18n/LocaleContext.tsx`, "utf8");
  const arms = { en: body.slice(body.indexOf("const en: Dict"), body.indexOf("const zhCN: Dict")), zh: body.slice(body.indexOf("const zhCN: Dict")) };
  const grab = (block) => Object.fromEntries([...block.matchAll(/^  \"member\.scope\.(\w+)\": \"([^\"]+)\",$/gm)].map((m) => [m[1], m[2]]));
  return { en: grab(arms.en), zh: grab(arms.zh) };
}


const BASE = process.env.CNX_BASE || "http://127.0.0.1:4802";
// Each arm reads its own trip. The invitation one arm issues is a server-side fact, and letting
// the other arm look at the same trip made its first row arrive already withdrawn -- a leaked
// precondition rather than a finding.
const journeyFor = (locale) =>
  process.env[`CNX_JOURNEY_${locale.toUpperCase().replace("-", "_")}`] || process.env.CNX_JOURNEY || "";
const OUT = process.env.CNX_OUT || ".";
const REPO = process.env.CNX_REPO || ".";
const VIEWPORT = { width: 390, height: 844 };

const squeeze = (value) => (value ?? "").replace(/\s+/g, " ").trim();

async function arm(browser, locale) {
  const JOURNEY = journeyFor(locale);
  const context = await browser.newContext({ viewport: VIEWPORT, locale });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error).slice(0, 200)));
  // The shell opens the create-a-trip onboarding when boot has no journey to load, and that screen
  // deliberately carries no nav (`Amendment F #1`). This reading is of a panel inside the product
  // shell, so the device has to arrive the way a traveller who already has a trip does: the same
  // two keys the shell itself writes, set before the first request.
  await page.addInitScript(
    ([language, journey]) => {
      window.localStorage.setItem("citynexus.locale", language);
      if (journey) window.localStorage.setItem("citynexus.v8.journey_id", journey);
    },
    [locale, JOURNEY],
  );

  await page.goto(`${BASE}/v8/access`, { waitUntil: "networkidle" });
  await page.locator('[data-testid="access-panel"]').first().waitFor({ state: "visible", timeout: 20000 });

  const read = {
    locale,
    title: squeeze(await page.locator('[data-testid="access-panel"] .v8-kicker').first().innerText()),
    pickerPresent: (await page.locator('[data-testid="access-journey-picker"]').count()) > 0,
    doorState: squeeze(await page.locator('[data-testid="access-door-state"]').first().innerText()),
    // Captured after the trip is chosen: the ladder is the ACL door's answer, and at first paint
     // there is no answer yet.
    roleRows: 0,
    roleText: [],
    roleAttributes: [],
    visibilityRows: (await page.locator('[data-testid="access-visibility-ladder"] li').allInnerTexts()).map(squeeze),
    visibilityAttributes: await page
      .locator('[data-testid="access-visibility-ladder"] li')
      .evaluateAll((rows) => rows.map((row) => row.getAttribute("data-level"))),
    confirmCases: await page
      .locator('[data-testid="access-confirm-table"] li')
      .evaluateAll((rows) =>
        rows.map((row) => ({
          when: row.getAttribute("data-case"),
          said: Array.from(row.querySelectorAll("span")).map((span) =>
            (span.textContent ?? "").replace(/\s+/g, " ").trim(),
          ),
        })),
      ),
    switchLines: await page
      .locator('[data-testid="access-switch-lines"] li')
      .evaluateAll((rows) =>
        rows.map((row) => ({
          move: row.getAttribute("data-switch"),
          said: (row.textContent ?? "").replace(/\s+/g, " ").trim(),
        })),
      ),
    inviteTtl: squeeze(await page.locator('[data-testid="access-invite-ttl"]').first().innerText()),
    inviteQuota: squeeze(await page.locator('[data-testid="access-invite-quota"]').first().innerText()),
    activityLines: [],
    activityAttributes: [],
    activityEmpty: false,
    activityFailed: false,
    pickerHit: null,
    walk: {
      before: null,
      afterCreate: null,
      confirmSaid: null,
      stillOpenAfterAsk: null,
      confirmStillVisible: null,
      confirmButtonPresent: null,
      afterRevoke: null,
    },
    rosterLine: null,
    activityCaveat: null,
    member: { rows: 0, scopeSaid: null, statesBefore: null, afterWithdraw: null, afterReload: null },
    disabledReasons: {},
    roleScopes: [],
  };

  if (read.pickerPresent && JOURNEY) {
    await page.selectOption('[data-testid="access-journey-picker"]', JOURNEY);
    await page
      .locator(
        '[data-testid="access-activity-list"], [data-testid="access-activity-empty"], [data-testid="access-activity-failed"]',
      )
      .first()
      .waitFor({ state: "visible", timeout: 20000 });
    await page.waitForFunction(
      () => !/正在问|Asking this server/.test(document.querySelector('[data-testid="access-door-state"]')?.textContent ?? ""),
      null,
      { timeout: 20000 },
    );
    // Re-read the door line only now. The value captured at first paint is the loading sentence, and
    // a reading that handed back "Asking this server…" as the server's answer would be reporting a
    // question as a fact.
    read.doorState = squeeze(
      await page.locator('[data-testid="access-door-state"]').first().innerText(),
    );
    // Same reason as above: the two invitation lines are answered by the sharing doors, so reading
    // them at first paint captured the loading state and reported "the server gave nothing" about a
    // server that had not been asked yet.
    read.inviteTtl = squeeze(await page.locator('[data-testid="access-invite-ttl"]').first().innerText());
    read.inviteQuota = squeeze(
      await page.locator('[data-testid="access-invite-quota"]').first().innerText(),
    );
    read.activityLines = (
      await page.locator('[data-testid="access-activity-list"] li .cn-access-what').allInnerTexts()
    ).map(squeeze);
    read.activityAttributes = await page
      .locator('[data-testid="access-activity-list"] li')
      .evaluateAll((rows) => rows.map((row) => row.getAttribute("data-event-type")));
    read.activityEmpty = (await page.locator('[data-testid="access-activity-empty"]').count()) > 0;
    read.activityFailed = (await page.locator('[data-testid="access-activity-failed"]').count()) > 0;
    const box = await page.locator('[data-testid="access-journey-picker"]').boundingBox();
    if (box) {
      const hit = await page.evaluate(
        ([x, y]) => {
          const element = document.elementFromPoint(x, y);
          return {
            tag: element?.tagName?.toLowerCase() ?? null,
            testId: element?.getAttribute?.("data-testid") ?? null,
          };
        },
        [box.x + box.width / 2, box.y + box.height / 2],
      );
      read.pickerHit = { box, ...hit };
    }

    // ---- ORD-0449: the step a traveller actually has to be able to take ---------------------
    // Issue an invitation with an expiry, watch the row come back from the server, then withdraw
    // it -- and prove the screen asks first: the row must still be un-revoked after the first tap.
    read.walk = { before: null, afterCreate: null, confirmSaid: null, afterRevoke: null };
    read.walk.before = (await page.locator('[data-testid="access-grant-row"]').count()) === 0
      ? "empty"
      : (await page.locator('[data-testid="access-grant-row"]').count());
    await page.fill('[data-testid="access-invite-expiry"]', "2026-12-06T08:00");
    await page.click('[data-testid="access-invite-submit"]');
    await page
      .locator('[data-testid="access-grant-row"]')
      .first()
      .waitFor({ state: "visible", timeout: 20000 });
    read.walk.afterCreate = squeeze(
      await page.locator('[data-testid="access-grant-row"] .cn-access-row-what').first().innerText(),
    );
    await page.click('[data-testid="access-grant-revoke"]');
    read.walk.confirmSaid = squeeze(
      await page.locator('[data-testid="access-confirm-pending"]').first().innerText(),
    );
    // The first tap only asks. Waiting before reading is the whole point of this arm: the first cut
    // read the attribute immediately after the tap and passed even against a mutant that withdrew at
    // once, because the write had not landed yet -- it was timing a race, not testing a rule. The
    // settle window is long enough for a local round trip (measured: the write answers in ~15 ms),
    // so a row that flips during it means the screen never asked.
    await page.waitForTimeout(1500);
    read.walk.stillOpenAfterAsk = await page
      .locator('[data-testid="access-grant-row"]')
      .first()
      .getAttribute("data-revoked");
    read.walk.confirmStillVisible =
      (await page.locator('[data-testid="access-confirm-pending"]').count()) > 0;
    // If the screen stopped asking, there is no confirmation to click. Reporting that as a failed
    // arm is the point; crashing the whole reading over it would leave the other arms with no
    // reading at all, which is how the first mutant run of this control ended up unattributable.
    read.walk.confirmButtonPresent =
      (await page.locator('[data-testid="access-confirm-yes"]').count()) > 0;
    if (read.walk.confirmButtonPresent) {
      await page.click('[data-testid="access-confirm-yes"]');
    }
    await page
      .locator('[data-testid="access-grant-row"][data-revoked="true"]')
      .first()
      .waitFor({ state: "visible", timeout: 20000 });
    read.walk.afterRevoke = squeeze(
      await page.locator('[data-testid="access-grant-row"][data-revoked="true"] .cn-access-row-what')
        .first()
        .innerText(),
    );
    // ---- ORD-0462: the member card, the sentence beside it, and what survives a reload ---------
    // A refusal the traveller can really bring about: an expiry in the past. The named code is
    // `SHARE_GRANT_EXPIRY_IN_PAST`; the screen must answer with the sentence for that code, not with
    // a status number, and it must not have issued anything.
    await page.fill('[data-testid="access-invite-expiry"]', "2020-01-01T08:00");
    await page.click('[data-testid="access-invite-submit"]');
    await page
      .locator('[data-testid="access-write-refused"]')
      .first()
      .waitFor({ state: "visible", timeout: 20000 });
    read.walk.pastRefusal = squeeze(
      await page.locator('[data-testid="access-write-refused"]').first().innerText(),
    );
    read.walk.grantRowsAfterRefusal = await page.locator('[data-testid="access-grant-row"]').count();

    read.member = { rows: 0, scopeSaid: null, statesBefore: null, afterWithdraw: null, afterReload: null };
    read.member.rows = await page.locator('[data-testid="access-member-row"]').count();
    read.member.scopeSaid = squeeze(
      await page.locator('[data-testid="access-member-row"] .cn-access-row-what').first().innerText(),
    );
    read.member.statesBefore = await page
      .locator('[data-testid="access-member-row"]')
      .first()
      .getAttribute("data-state");
    read.disabledReasons = {
      roleChange: squeeze(
        await page.locator('[data-testid="access-member-role-change"]').first().innerText(),
      ),
      selfExit: squeeze(
        await page.locator('[data-testid="access-member-self-exit"]').first().innerText(),
      ),
      roleChangeDisabledAttr: await page
        .locator('[data-testid="access-member-role-change"]')
        .first()
        .getAttribute("disabled"),
      selfExitDisabledAttr: await page
        .locator('[data-testid="access-member-self-exit"]')
        .first()
        .getAttribute("disabled"),
      reasonsOnScreen: squeeze(
        await page.locator('[data-testid="access-disabled-reasons"]').first().innerText(),
      ),
      // Greyed is part of the claim: a disabled control that looks enabled is a bug the DOM
      // attribute alone cannot show, so the computed style is what gets read.
      look: await page
        .locator('[data-testid="access-member-role-change"]')
        .first()
        .evaluate((element) => {
          const style = getComputedStyle(element);
          return { opacity: Number(style.opacity), cursor: style.cursor };
        }),
    };
    await page.click('[data-testid="access-member-withdraw"]');
    await page.click('[data-testid="access-confirm-yes"]');
    await page
      .locator('[data-testid="access-member-row"][data-state="MEMBER_WITHDRAWN"]')
      .first()
      .waitFor({ state: "visible", timeout: 20000 });
    read.member.afterWithdraw = squeeze(
      await page
        .locator('[data-testid="access-member-row"][data-state="MEMBER_WITHDRAWN"] .cn-access-row-what')
        .first()
        .innerText(),
    );
    // 刷新后还在: the withdrawn membership has to come back from the server, not from React state.
    await page.reload({ waitUntil: "networkidle" });
    await page.locator('[data-testid="access-panel"]').first().waitFor({ state: "visible", timeout: 20000 });
    await page.selectOption('[data-testid="access-journey-picker"]', JOURNEY);
    await page
      .locator('[data-testid="access-member-row"][data-state="MEMBER_WITHDRAWN"]')
      .first()
      .waitFor({ state: "visible", timeout: 20000 });
    read.member.afterReload = squeeze(
      await page
        .locator('[data-testid="access-member-row"][data-state="MEMBER_WITHDRAWN"] .cn-access-row-what')
        .first()
        .innerText(),
    );
    read.roleScopes = (
      await page
        .locator('[data-testid="access-role-ladder"] [data-testid="access-role-scope"]')
        .allInnerTexts()
    ).map(squeeze);
    read.roleRows = await page.locator('[data-testid="access-role-ladder"] li').count();
    read.roleText = (await page.locator('[data-testid="access-role-ladder"] li').allInnerTexts()).map(squeeze);
    read.roleAttributes = await page
      .locator('[data-testid="access-role-ladder"] li')
      .evaluateAll((rows) => rows.map((row) => row.getAttribute("data-role")));

    read.rosterLine = squeeze(
      await page
        .locator('[data-testid="access-roster-empty"], [data-testid="access-member-row"]')
        .first()
        .innerText(),
    );
    read.activityCaveat = squeeze(
      await page.locator('[data-testid="access-activity-caveat"]').first().innerText(),
    );

  }

  const bodyText = squeeze(await page.locator("body").innerText());
  const panelText = squeeze(await page.locator('[data-testid="access-panel"]').innerText());
  read.rawKeyLeak = bodyText.includes("access.");
  // A key is not the only way a template escapes: `{name}` with no value behind it is the same
  // failure wearing braces, and the arm below is what the first cut of this instrument missed.
  read.unfilledPlaceholders = (panelText.match(/\{[A-Za-z_]+\}/g) ?? []).slice(0, 6);
  // The language claim is about this screen, so it is counted on this screen's own text. The whole
  // page count travels beside it rather than replacing it: whatever Chinese the shell still renders
  // in an English device is a different order's finding, and hiding it here would lose it.
  read.cjkChars = (panelText.match(/[㐀-鿿]/g) || []).length;
  read.latinWords = (panelText.match(/[A-Za-z]{2,}/g) || []).length;
  read.wholePageCjkChars = (bodyText.match(/[㐀-鿿]/g) || []).length;
  read.doorStillLoading = /正在问|Asking this server/.test(read.doorState);
  read.overflowX = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  read.pageErrors = errors;
  // Reachability, measured the way a finger measures it: every ladder row's own centre point has to
  // resolve back to something inside this panel. A floating control from another feature that sits on
  // top of a row makes the row unreadable, and a text-only arm cannot see that.
  // Reachability, measured the way a finger measures it. Each ladder row is scrolled to the middle
  // of the viewport first -- `elementFromPoint` answers `null` for anything below the fold, and
  // "off-screen in a scrollable page" is not the defect being looked for. Then the row's own centre
  // point has to resolve back to something inside this panel: a floating control from another
  // feature sitting on top of a row makes that row unreadable, and a text-only arm cannot see it.
  read.coveredRows = [];
  const ladderRows = await page.locator(
    '[data-testid="access-role-ladder"] li, [data-testid="access-visibility-ladder"] li',
  );
  for (let index = 0; index < (await ladderRows.count()); index += 1) {
    const row = ladderRows.nth(index);
    // `scrollIntoViewIfNeeded` leaves a row wherever it was, which for the first ladder row means
    // its centre can still sit under the fixed bottom nav (measured: the 地图 label at y=816 of 844
    // answered the hit-test). Centre it in the reachable band first, or the arm reports its own
    // scrolling as a product defect.
    await row.evaluate((element) => {
      const nav = document.querySelector("[data-testid='v8-mobile-nav']") ?? null;
      const usable = nav ? nav.getBoundingClientRect().top : window.innerHeight;
      window.scrollTo(0, window.scrollY + element.getBoundingClientRect().top - usable / 2);
    });
    await page.evaluate(() => new Promise((done) => requestAnimationFrame(done)));
    const probe = await row.evaluate((element) => {
      const box = element.getBoundingClientRect();
      const panel = document.querySelector('[data-testid="access-panel"]');
      const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
      return {
        label: (element.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 24),
        in_viewport: box.y >= 0 && box.bottom <= window.innerHeight,
        hit_inside_panel: hit ? Boolean(panel?.contains(hit)) : false,
        hit_testid: hit?.getAttribute?.("data-testid") ?? hit?.tagName?.toLowerCase() ?? null,
        hit_where: hit
          ? {
              tag: hit.tagName.toLowerCase(),
              cls: (hit.className ?? "").toString().slice(0, 60),
              text: (hit.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 24),
              rect: (({ x, y, width, height }) => ({ x: Math.round(x), y: Math.round(y), w: Math.round(width), h: Math.round(height) }))(
                hit.getBoundingClientRect(),
              ),
              position: getComputedStyle(hit.closest("[class]") ?? hit).position,
            }
          : null,
      };
    });
    if (!probe.in_viewport || !probe.hit_inside_panel) read.coveredRows.push(probe);
  }
  await page.screenshot({ path: `${OUT}/access_${locale.replace("-", "_")}_r1.png`, fullPage: true });
  await context.close();
  return read;
}

const browser = await chromium.launch();
const zh = await arm(browser, "zh-CN");
const en = await arm(browser, "en");
await browser.close();

const checks = [];
const add = (name, ok, detail) => checks.push({ name, verdict: ok ? "PASS" : "FAIL", detail });
const byCase = Object.fromEntries((zh.confirmCases ?? []).map((row) => [row.when, row.said]));
const enByCase = Object.fromEntries((en.confirmCases ?? []).map((row) => [row.when, row.said]));

add("both arms rendered the panel", zh.title.length > 0 && en.title.length > 0, `${zh.title} / ${en.title}`);
add("the trip list came from the server", zh.pickerPresent && en.pickerPresent, `picker=${zh.pickerPresent}`);
add(
  "three roles, each with one scope sentence",
  zh.roleRows === 3 &&
    zh.roleAttributes.slice().sort().join(",") === "ADMIN,COLLABORATOR,OWNER" &&
    zh.roleText.every((line) => line.length > 6),
  `${zh.roleAttributes} :: ${zh.roleText.join(" | ")}`.slice(0, 240),
);
add(
  "every visibility level carries its consequence",
  zh.visibilityRows.length === 4 && zh.visibilityRows.every((line) => line.length > 8),
  `${zh.visibilityAttributes} :: ${zh.visibilityRows.join(" | ")}`.slice(0, 280),
);

// The seam arm compares the server's domain with what the screen offers. While no artifact names
// `ShareVisibility` it must not pass quietly: it asserts the screen says the doors are silent, and
// carries `seam_state` so a reader can see the comparison never happened.
const domain = contractDomain(REPO);
const offeredLevels = zh.visibilityAttributes ?? [];
add(
  "the ladder offers exactly the levels the server's own domain has",
  domain === null
    ? offeredLevels.length === 4 &&
        /一扇都没答|answered none of/.test(`${zh.doorState} ${en.doorState}`)
    : domain.levels.slice().sort().join(",") === offeredLevels.slice().sort().join(","),
  JSON.stringify({
    seam_state: domain === null ? "NOT_YET_CHECKABLE_no_ShareVisibility_in_contract_or_client" : "CHECKED",
    read_from: domain?.where ?? null,
    domain_levels: domain?.levels ?? [],
    screen_levels: offeredLevels,
  }).slice(0, 300),
);
add(
  "the confirmation split is two different sentences",
  Boolean(byCase["access.whenOtherGainsOnly"]?.[1]) &&
    Boolean(byCase["access.whenActorLosesStanding"]?.[1]) &&
    byCase["access.whenOtherGainsOnly"][1] !== byCase["access.whenActorLosesStanding"][1],
  JSON.stringify(byCase).slice(0, 340),
);
add(
  "an unread role gets the warning, not a clean pass",
  byCase["access.whenRoleUnread"]?.[1] === byCase["access.whenActorLosesStanding"]?.[1],
  JSON.stringify(byCase["access.whenRoleUnread"]),
);
add(
  "removal says what the other person loses, in both arms",
  Boolean(byCase.removal?.[1]) && Boolean(enByCase.removal?.[1]),
  JSON.stringify({ zh: byCase.removal, en: enByCase.removal }).slice(0, 240),
);
add(
  "private->public and public->private each name the other side",
  zh.switchLines.length === 2 && zh.switchLines[0].said !== zh.switchLines[1].said,
  JSON.stringify(zh.switchLines).slice(0, 300),
);
add(
  "the invitation states an expiry",
  zh.inviteTtl.length > 6 && en.inviteTtl.length > 6,
  `${zh.inviteTtl} || ${en.inviteTtl}`,
);
add(
  "the invitation counts, or says it was given no numbers",
  zh.inviteQuota.length > 6 && !/[{}]/.test(zh.inviteQuota) && !/[{}]/.test(en.inviteQuota),
  `${zh.inviteQuota} || ${en.inviteQuota}`,
);
const activityPairs = (zh.activityLines ?? []).map((line, index) => ({
  line,
  token: zh.activityAttributes[index],
}));
const asSentence = activityPairs.filter((pair) => !pair.line.includes(String(pair.token)));
const asToken = activityPairs.filter((pair) => pair.line.includes(String(pair.token)));
add(
  "activity rows the screen has words for read as sentences, not as the server's token",
  asSentence.length > 0 && asSentence.every((pair) => pair.line.length > 4 && !pair.line.includes("_")),
  JSON.stringify(asSentence).slice(0, 340),
);
// The one line allowed to carry a machine token is the confession that the screen has no words for
// it. Forbidding the token everywhere would have failed the honest sentence and passed a silence.
add(
  "an action this screen cannot name says so and quotes the token it was given",
  asToken.length > 0 &&
    asToken.every((pair) => /说不出人话|has no sentence for/.test(pair.line) && pair.line.includes(String(pair.token))),
  JSON.stringify(asToken).slice(0, 260),
);
add(
  "the sharing door's absence is named on screen, after the server answered",
  zh.doorState.length > 12 && en.doorState.length > 12 && !zh.doorStillLoading && !en.doorStillLoading,
  `${zh.doorState} || ${en.doorState}`.slice(0, 260),
);
add("no raw copy key reached either arm", !zh.rawKeyLeak && !en.rawKeyLeak, `zh=${zh.rawKeyLeak} en=${en.rawKeyLeak}`);
add(
  "no template placeholder reached either arm's screen",
  zh.unfilledPlaceholders.length === 0 && en.unfilledPlaceholders.length === 0,
  JSON.stringify({ zh: zh.unfilledPlaceholders, en: en.unfilledPlaceholders }),
);
add("the Chinese arm reads Chinese", zh.cjkChars > 80, `cjk=${zh.cjkChars}`);
add("the English arm reads English", en.cjkChars === 0 && en.latinWords > 40, `panelCjk=${en.cjkChars} latin=${en.latinWords}`);
add(
  "the one control is under the finger at 390x844",
  !!zh.pickerHit && zh.pickerHit.tag === "select" && zh.pickerHit.box.height >= 40 && zh.overflowX === 0,
  JSON.stringify({ tag: zh.pickerHit?.tag, h: zh.pickerHit?.box?.height, overflowX: zh.overflowX }),
);
add(
  "no ladder row is covered by something outside this panel",
  zh.coveredRows.length === 0 && en.coveredRows.length === 0,
  JSON.stringify({ zh: zh.coveredRows, en: en.coveredRows }).slice(0, 300),
);
add(
  "the invitation the traveller created comes back with an expiry the server was given",
  /到 .* 之前可开|Open until/.test(zh.walk.afterCreate ?? "") &&
    /到 .* 之前可开|Open until/.test(en.walk.afterCreate ?? ""),
  JSON.stringify({ zh: zh.walk.afterCreate, en: en.walk.afterCreate }).slice(0, 260),
);
add(
  "the screen asks before it withdraws anything, and the first tap changes nothing",
  /你自己的权限不变|Your own access does not change/.test(zh.walk.confirmSaid ?? "") &&
    zh.walk.stillOpenAfterAsk === "false" &&
    en.walk.stillOpenAfterAsk === "false" &&
    zh.walk.confirmStillVisible === true &&
    en.walk.confirmStillVisible === true &&
    zh.walk.confirmButtonPresent === true &&
    en.walk.confirmButtonPresent === true,
  JSON.stringify({ zh_confirm: zh.walk.confirmSaid, stillOpen: [zh.walk.stillOpenAfterAsk, en.walk.stillOpenAfterAsk], stillAsked: [zh.walk.confirmStillVisible, en.walk.confirmStillVisible] }).slice(0, 290),
);
add(
  "after the confirmation the row says withdrawn, in the language the device is in",
  /已于 .* 撤销|Withdrawn at/.test(zh.walk.afterRevoke ?? "") &&
    /已于 .* 撤销|Withdrawn at/.test(en.walk.afterRevoke ?? ""),
  JSON.stringify({ zh: zh.walk.afterRevoke, en: en.walk.afterRevoke }).slice(0, 260),
);
add(
  "the member door's answer is read out, empty included, and the activity caveat is on screen",
  (zh.rosterLine ?? "").length > 6 &&
    /还没往活动流里写|not written into this trip's activity stream/.test(zh.activityCaveat ?? "") &&
    /not written into this trip's activity stream|还没往活动流里写/.test(en.activityCaveat ?? ""),
  JSON.stringify({ roster: zh.rosterLine, caveat: zh.activityCaveat }).slice(0, 260),
);
const scopes = dictionaryScopes();
const scopeOf = (arm) => (arm === "zh-CN" ? scopes.zh : scopes.en);
add(
  "the role ladder is the door's three rows, each with the dictionary's own sentence for its key",
  zh.roleScopes.length === 3 &&
    en.roleScopes.length === 3 &&
    Object.keys(scopeOf("zh-CN")).length === 3 &&
    zh.roleScopes.every((line, i) => Object.values(scopeOf("zh-CN")).some((words) => line.startsWith(words)) && !line.includes("member.scope.")) &&
    en.roleScopes.every((line, i) => Object.values(scopeOf("en")).some((words) => line.startsWith(words)) && !line.includes("member.scope.")),
  JSON.stringify({ zh: zh.roleScopes, en: en.roleScopes, dictionary_keys: Object.keys(scopeOf("en")) }).slice(0, 320),
);
add(
  "a member row carries its scope sentence, and removing it is the server's answer, not the screen's",
  zh.member.rows >= 1 &&
    /能读这条行程、编辑地点。/.test(zh.member.scopeSaid ?? "") &&
    /Can read this trip and edit places./.test(en.member.scopeSaid ?? "") &&
    zh.member.statesBefore === "MEMBER_IN_FORCE" &&
    en.member.statesBefore === "MEMBER_IN_FORCE" &&
    /已在 .* 撤回|[Ww]ithdrawn at/.test(zh.member.afterWithdraw ?? "") &&
    /已在 .* 撤回|[Ww]ithdrawn at/.test(en.member.afterWithdraw ?? ""),
  JSON.stringify({ zh: zh.member, en: en.member }).slice(0, 320),
);
add(
  "the withdrawal is still there after a reload (it came from the server, not from component state)",
  /已在 .* 撤回|[Ww]ithdrawn at/.test(zh.member.afterReload ?? "") &&
    /已在 .* 撤回|[Ww]ithdrawn at/.test(en.member.afterReload ?? "") &&
    zh.member.afterReload === zh.member.afterWithdraw &&
    en.member.afterWithdraw.includes("MEMBER") === false,
  JSON.stringify({ zh: zh.member.afterReload, en: en.member.afterReload }).slice(0, 260),
);
add(
  "the two controls with no door are disabled and say why, in the language of the device",
  zh.disabledReasons.roleChangeDisabledAttr === "" &&
    zh.disabledReasons.selfExitDisabledAttr === "" &&
    zh.disabledReasons.roleChange === "改角色" &&
    zh.disabledReasons.selfExit === "我自己退出" &&
    zh.disabledReasons.reasonsOnScreen.length > 12 &&
    zh.disabledReasons.look.opacity < 1 &&
    zh.disabledReasons.look.cursor === "not-allowed" &&
    en.disabledReasons.look.opacity < 1 &&
    /改角色要等|我自己退出/.test(zh.disabledReasons.reasonsOnScreen) &&
    /waits for this server|door of its own/.test(en.disabledReasons.reasonsOnScreen),
  JSON.stringify({ zh: zh.disabledReasons, en: en.disabledReasons }).slice(0, 320),
);

add(
  "a refusal the traveller can cause is named by its code's sentence, and issues nothing",
  /那个到期时刻已经过去了/.test(zh.walk.pastRefusal ?? "") &&
    /already behind us/.test(en.walk.pastRefusal ?? "") &&
    zh.walk.grantRowsAfterRefusal === 1 &&
    en.walk.grantRowsAfterRefusal === 1,
  JSON.stringify({
    zh: zh.walk.pastRefusal,
    en: en.walk.pastRefusal,
    rows: [zh.walk.grantRowsAfterRefusal, en.walk.grantRowsAfterRefusal],
  }).slice(0, 300),
);

add(
  "neither arm threw a page error",
  zh.pageErrors.length === 0 && en.pageErrors.length === 0,
  JSON.stringify([zh.pageErrors, en.pageErrors]).slice(0, 240),
);

console.log(
  JSON.stringify(
    {
      zh,
      en,
      checks,
      all_pass: checks.every((check) => check.verdict === "PASS"),
      failed: checks.filter((check) => check.verdict === "FAIL").map((check) => check.name),
    },
    null,
    2,
  ),
);
