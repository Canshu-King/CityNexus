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

const BASE = process.env.CNX_BASE || "http://127.0.0.1:4802";
const JOURNEY = process.env.CNX_JOURNEY || "";
const OUT = process.env.CNX_OUT || ".";
const VIEWPORT = { width: 390, height: 844 };

const squeeze = (value) => (value ?? "").replace(/\s+/g, " ").trim();

async function arm(browser, locale) {
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
    roleRows: await page.locator('[data-testid="access-role-ladder"] li').count(),
    roleText: (await page.locator('[data-testid="access-role-ladder"] li').allInnerTexts()).map(squeeze),
    roleAttributes: await page
      .locator('[data-testid="access-role-ladder"] li')
      .evaluateAll((rows) => rows.map((row) => row.getAttribute("data-role"))),
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
  }

  const bodyText = squeeze(await page.locator("body").innerText());
  const panelText = squeeze(await page.locator('[data-testid="access-panel"]').innerText());
  read.rawKeyLeak = bodyText.includes("access.");
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
    zh.roleAttributes.join(",") === "OWNER,ADMIN,COLLABORATOR" &&
    zh.roleText.every((line) => line.length > 6),
  `${zh.roleAttributes} :: ${zh.roleText.join(" | ")}`.slice(0, 240),
);
add(
  "every visibility level carries its consequence",
  zh.visibilityRows.length === 5 && zh.visibilityRows.every((line) => line.length > 8),
  `${zh.visibilityAttributes} :: ${zh.visibilityRows.join(" | ")}`.slice(0, 280),
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
add("the Chinese arm reads Chinese", zh.cjkChars > 80, `cjk=${zh.cjkChars}`);
add("the English arm reads English", en.cjkChars === 0 && en.latinWords > 40, `panelCjk=${en.cjkChars} latin=${en.latinWords}`);
add(
  "the one control is under the finger at 390x844",
  !!zh.pickerHit && zh.pickerHit.tag === "select" && zh.pickerHit.box.height >= 40 && zh.overflowX === 0,
  JSON.stringify({ tag: zh.pickerHit?.tag, h: zh.pickerHit?.box?.height, overflowX: zh.overflowX }),
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
