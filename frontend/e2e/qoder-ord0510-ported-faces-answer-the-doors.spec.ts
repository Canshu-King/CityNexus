/**
 * The ported faces must answer the doors, not remember the taps.
 *
 * Slice 1's front-end half came over from the Qoder product tree (ORD-0444 container, ORD-0476
 * footprints, ORD-0500 per-stop refusals, ORD-0510 the way into a shelf).  A typecheck says those
 * files hang together; it cannot say a control writes through its door, that the line under it is
 * drawn from a fresh read, or that a second tap writes nothing.  So this spec drives the real backend
 * this run started -- no `route.fulfill`, no stubbed list -- and reads the store back through the same
 * door the screen used, so a screen that invented a state is caught by the row the server holds.
 *
 * What each arm can fail on, said up front because "it renders" is not the claim:
 *   A  a stamp appears on the footprint screen only because `GET /journeys/{id}/checkins` returned it,
 *      in the trip's own timezone, with the two cells that must never be blank filled in words;
 *   B  a second tap on a stamped stop answers 409 and says so in this screen's own sentence, to that
 *      stop alone, and the tally does not move -- the unchanged count is the discriminating half;
 *   C  a place lands on a shelf because `POST /collections/{id}/items` wrote it and
 *      `GET /collections` read it back, and a repeat tap names the state without doubling the row;
 *   D  whose shelves those are.  A second traveller's credential sees none of them, and with no
 *      credential at all the screen asks nothing -- the request log is the witness for that, because a
 *      sentence about scope is worth only as much as the network record behind it.
 *
 * Identity is one browser context per traveller, not a rewrite of sessionStorage inside a tab: the
 * seed of each page is an `addInitScript`, which replays on every navigation, so a switched bearer
 * would be silently restored by the next `goto`.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { expect, test } from "@playwright/test";
import { evidencePath } from "./_qoderEvidence";
import {
  VIEWPORT,
  ask,
  checkinsPath,
  flat,
  openAs,
  stage,
  tokenFor,
} from "./_qoderOrd0510Stage";

const FILE = "e2e/qoder-ord0510-ported-faces-answer-the-doors.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
test.use({ viewport: VIEWPORT, hasTouch: true });

const SHELF_NAME = "收藏架 r3";

function write(name: string, body: unknown) {
  const p = evidencePath("qoder-ord0510", name + ".json");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(body, null, 1), "utf8");
  console.log("O510GATE " + name + " " + JSON.stringify(body));
}

test("qoder-ord0510-a — 足迹屏上那一行是服务器给的，不是按钮的记忆", async ({ browser, request }) => {
  test.setTimeout(240_000);
  const ID = "qoder-ord0510-a";
  const s = await stage(request, ID);
  const held0 = await ask(request, "GET", checkinsPath(s.journeyId), { token: s.token });
  const { page } = await openAs(browser, s, s.token, "/v8/trips");

  await expect(page.getByTestId("trip-itinerary")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("footprint-panel")).toBeVisible();
  if (held0.length === 0) {
    await expect(page.getByTestId("footprint-empty")).toBeVisible({ timeout: 20_000 });
  }

  const stop = page.getByTestId("trip-stop").first();
  const entry = stop.getByTestId("stop-checkin");
  const title = (await stop.locator(".trip-stop-body b").first().innerText()).trim();
  await expect(entry, node(ID, "the stop carries no check-in control")).toBeVisible();
  await expect(entry).toHaveAttribute("data-state", "fresh");

  await entry.click();
  await expect(entry, node(ID, `"${title}" never reached 已打卡 after the tap`)).toHaveAttribute(
    "data-state",
    "stamped",
    { timeout: 20_000 },
  );

  // The panel under the list is a separate surface with its own read; make it ask again.
  await page.getByTestId("footprint-retry").click();
  const row = page.getByTestId("footprint-row").filter({ hasText: title });
  await expect(row, node(ID, `no footprint row came back for "${title}"`)).toHaveCount(1, { timeout: 20_000 });
  const rowText = flat(await row.innerText());
  expect(rowText, node(ID, `a stamp with no note left the cell empty: "${rowText}"`)).toContain("没写备注");
  expect(rowText, node(ID, `the row does not name where the stamp came from: "${rowText}"`)).toContain("网页端打的");
  await expect(page.getByTestId("footprint-day-zone"), node(ID, "the day line names no zone")).toContainText(
    s.timezone,
  );

  const held = await ask(request, "GET", checkinsPath(s.journeyId), { token: s.token });
  await expect(page.getByTestId("footprint-tally")).toContainText(`${held.length} 枚足迹`);
  expect(
    /CHECKIN_[A-Z_]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-/.test(
      flat(await page.getByTestId("footprint-panel").innerText()),
    ),
    node(ID, "a reason code or a uuid is painted on the footprint screen"),
  ).toBe(false);
  write("A_footprint", {
    stop_title: title,
    row_text: rowText,
    stamps_on_server_before: held0.length,
    stamps_on_server: held.length,
    zone: s.timezone,
  });
});

test("qoder-ord0510-b — 再按一次只对它那一站说，数目不动", async ({ browser, request }) => {
  test.setTimeout(240_000);
  const ID = "qoder-ord0510-b";
  const s = await stage(request, ID);
  const { page } = await openAs(browser, s, s.token, "/v8/trips");
  await expect(page.getByTestId("trip-itinerary")).toBeVisible({ timeout: 30_000 });

  // A stop of its own, so arm A's stamp cannot be mistaken for this one's answer.
  const entry = page.getByTestId("trip-stop").nth(1).getByTestId("stop-checkin");
  await entry.click();
  await expect(entry).toHaveAttribute("data-state", "stamped", { timeout: 20_000 });
  // The server's count is taken first and the panel is then PINNED to it.  The tally is a re-read,
  // and a re-read needs a bound rather than a wait on a row that was already on the screen: the
  // first cut of this arm read the tally straight after `footprint-retry` and measured the panel's
  // previous answer (arm A's stamp alone), so the duplicate arm appeared to move the count it was
  // there to prove cannot move.  Arm A's stamp stays in the store -- this arm asserts against the
  // number the read door gives, whatever it is, not against a hand-written one.
  const onServerBefore = (await ask(request, "GET", checkinsPath(s.journeyId), { token: s.token })).length;
  await page.getByTestId("footprint-retry").click();
  await expect(page.getByTestId("footprint-tally")).toContainText(
    `${onServerBefore} 枚足迹`,
    { timeout: 20_000 },
  );
  const tallyBefore = flat(await page.getByTestId("footprint-tally").innerText());

  await entry.click(); // the door answers 409 for this stop
  const notice = page.getByTestId("stop-checkin-notice");
  await expect(notice, node(ID, "the second tap produced no answer at all")).toBeVisible({ timeout: 20_000 });
  const text = flat(await notice.innerText());
  expect(text, node(ID, `the 409 was not named as a duplicate: "${text}"`)).toContain("这一站已经打过卡了");
  expect(text, node(ID, `the answer points at no moment: "${text}"`)).toMatch(/\d{1,2}月\d{1,2}日/);
  expect(text, node(ID, `a reason code or a uuid reached the screen: "${text}"`)).not.toMatch(
    /CHECKIN_[A-Z_]+|[0-9a-f]{8}-[0-9a-f]{4}-/,
  );

  // ORD-0500's whole point: one stop's answer, not one screen's.
  await expect(
    page.getByTestId("stop-checkin-notice"),
    node(ID, "one stop's refusal was painted under several stops"),
  ).toHaveCount(1);

  const onServerAfter = (await ask(request, "GET", checkinsPath(s.journeyId), { token: s.token })).length;
  expect(
    onServerAfter,
    node(ID, `the duplicate tap wrote a stamp: ${onServerBefore} -> ${onServerAfter}`),
  ).toBe(onServerBefore);
  await page.getByTestId("footprint-retry").click();
  await expect(page.getByTestId("footprint-tally")).toContainText(
    `${onServerBefore} 枚足迹`,
    { timeout: 20_000 },
  );
  const tallyAfter = flat(await page.getByTestId("footprint-tally").innerText());
  expect(
    tallyAfter,
    node(ID, `the duplicate tap moved the screen's tally: "${tallyBefore}" -> "${tallyAfter}"`),
  ).toBe(tallyBefore);
  write("B_duplicate", {
    notice_text: text,
    tally_before: tallyBefore,
    tally_after: tallyAfter,
    stamps_on_server_before: onServerBefore,
    stamps_on_server_after: onServerAfter,
  });
});

test("qoder-ord0510-c — 收进架子这一枚，是读门说它在那儿", async ({ browser, request }) => {
  test.setTimeout(240_000);
  const ID = "qoder-ord0510-c";
  const s = await stage(request, ID);
  const shelves0 = await ask(request, "GET", "/api/v1/collections", { token: s.token });
  const shelf =
    shelves0.find((f: any) => f.name === SHELF_NAME) ??
    (await ask(request, "POST", "/api/v1/collections", { token: s.token, data: { name: SHELF_NAME } }));

  const { page } = await openAs(browser, s, s.token, "/v8/discover");
  await expect(page.getByTestId("collection-panel")).toBeVisible({ timeout: 30_000 });
  const card = page.getByTestId("collection-shelf").filter({ hasText: SHELF_NAME });
  await expect(card, node(ID, "the shelf the door holds is not on the screen")).toBeVisible({ timeout: 20_000 });

  await page.goto("/v8/trips", { waitUntil: "load", timeout: 90_000 });
  const entry = page.locator('[data-testid="collect-entry"]:not([disabled])').first();
  await expect(entry, node(ID, "no stop offered a way into the container")).toBeVisible({ timeout: 30_000 });
  await entry.click();
  const picker = page.getByTestId("collect-picker");
  await expect(picker).toBeVisible();
  const option = picker.getByTestId("collect-shelf").filter({ hasText: SHELF_NAME }).first();
  await expect(option, node(ID, "the picker did not list my own shelf")).toBeVisible({ timeout: 20_000 });
  await option.click();

  const result = page.getByTestId("collect-result");
  await expect(result, node(ID, "the collect control answered nothing")).toBeVisible({ timeout: 20_000 });
  const line = flat(await result.innerText());
  expect(line, node(ID, `the answer names no shelf: "${line}"`)).toContain(SHELF_NAME);
  expect(line, node(ID, `the answer does not say where it is placed: "${line}"`)).toContain("已收在");

  const list1 = await ask(request, "GET", "/api/v1/collections", { token: s.token });
  const onShelf = list1.find((f: any) => f.id === shelf.id);
  const items = onShelf?.items ?? [];
  expect(items.length, node(ID, `the screen claims a place the shelf does not hold (${items.length})`)).toBe(1);
  expect(
    s.placeIds.includes(String(items[0].place_id)),
    node(ID, `the row on the shelf is not one of this trip's places: ${items[0].place_id}`),
  ).toBe(true);

  // Same shelf, same place, second tap: named as already held, and still one row underneath.
  // The picker is NOT re-opened here.  `CollectInto`'s entry toggles, and its onClick clears the
  // answer line first, so tapping the entry again shut the very picker this step clicks in and
  // detached the row it waits for -- which is what made this arm time out rather than fail.  The
  // shelf row from the first open is still up, and the wait below is on text the first answer does
  // not contain, so it cannot pass on the previous line.
  await picker.getByTestId("collect-shelf").filter({ hasText: SHELF_NAME }).first().click();
  const result2 = page.getByTestId("collect-result");
  await expect(result2, node(ID, "the repeat tap answered nothing")).toContainText(
    "这一枚已经在这个架子上",
    { timeout: 20_000 },
  );
  const again = flat(await result2.innerText());
  expect(again, node(ID, `a reason code or a uuid reached the screen: "${again}"`)).not.toMatch(
    /COLLECTION_[A-Z_]+|[0-9a-f]{8}-[0-9a-f]{4}-/,
  );
  const list2 = await ask(request, "GET", "/api/v1/collections", { token: s.token });
  expect(
    list2.find((f: any) => f.id === shelf.id).item_count,
    node(ID, "the repeat tap wrote a second row"),
  ).toBe(1);

  await page.goto("/v8/discover", { waitUntil: "load", timeout: 90_000 });
  const card2 = page.getByTestId("collection-shelf").filter({ hasText: SHELF_NAME });
  await expect(card2.getByTestId("collection-item")).toHaveCount(1, { timeout: 20_000 });
  await expect(card2.getByTestId("collection-item")).toContainText("没写备注");
  await expect(page.getByTestId("collection-tally")).toContainText("1 枚地点");
  write("C_collect", {
    shelf_id: shelf.id,
    result_line: line,
    repeat_line: again,
    items_after_first_tap: items.length,
    item_count_after_repeat: list2.find((f: any) => f.id === shelf.id).item_count,
  });
});

test("qoder-ord0510-d — 架子是谁的是凭据说的；没有凭据就什么都没问", async ({ browser, request }) => {
  test.setTimeout(240_000);
  const ID = "qoder-ord0510-d";
  const s = await stage(request, ID);
  const other = await ask(request, "POST", "/api/v1/travelers", {
    data: { display_name: "另一位 r3", timezone: "Asia/Shanghai", locale: "en-GB" },
  });
  const otherToken = tokenFor(String(other.id));

  const asOwner = await openAs(browser, s, s.token, "/v8/discover");
  await expect(
    asOwner.page.getByTestId("collection-shelf").filter({ hasText: SHELF_NAME }),
    node(ID, "the owner was not handed their own shelf"),
  ).toBeVisible({ timeout: 30_000 });
  await asOwner.close();

  const asOther = await openAs(browser, s, otherToken, "/v8/discover");
  await expect(
    asOther.page.getByTestId("collection-empty"),
    node(ID, "another traveller was handed this traveller's shelves"),
  ).toBeVisible({ timeout: 20_000 });
  await expect(asOther.page.getByTestId("collection-panel")).not.toContainText(SHELF_NAME);
  await asOther.page.goto("/v8/trips", { waitUntil: "load", timeout: 90_000 });
  const otherEntry = asOther.page.locator('[data-testid="collect-entry"]:not([disabled])').first();
  await otherEntry.click();
  await expect(
    asOther.page.getByTestId("collect-no-shelf"),
    node(ID, "the picker offered a shelf that is not this traveller's"),
  ).toBeVisible({ timeout: 20_000 });
  await asOther.close();

  // With no credential the screen asks nothing, and the page's own request log is the witness.
  const asAnonymous = await openAs(browser, s, null, "/v8/discover");
  await expect(asAnonymous.page.getByTestId("collection-no-traveler")).toBeVisible({ timeout: 20_000 });
  const sentence = flat(await asAnonymous.page.getByTestId("collection-no-traveler").innerText());
  expect(
    sentence,
    node(ID, `the empty state does not say where scope comes from: "${sentence}"`),
  ).toContain("不认点名的 id");
  const shelfReads = asAnonymous.asked.filter((url) => url.includes("/api/v1/collections"));
  write("D_scope", {
    other_traveler_id: other.id,
    collection_requests_with_no_credential: shelfReads.length,
    asked_urls: asAnonymous.asked.filter((u) => u.includes("/api/v1/")).slice(0, 12),
    empty_sentence: sentence,
  });
  expect(
    shelfReads.length,
    node(ID, `the screen asked the shelf door ${shelfReads.length} times with no credential`),
  ).toBe(0);
  await asAnonymous.close();
});
