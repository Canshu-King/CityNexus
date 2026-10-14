/**
 * ORD-0437 / ORD-0524 slice 2 on *this* tree: paste text, get places, and prove each of the three
 * exits by what the server says afterwards.
 *
 * Why a spec of its own rather than a fifth arm of the slice-1 file: the import screen is not one of
 * the ported faces. It has its own write (the plan append) and, unique in this suite, it changes the
 * journey the seed built. It is therefore named and ordered to run LAST (`qoder-ord0537-*` sorts
 * after the 0510 files) so the six archived proofs stay byte-comparable, and it adds exactly one
 * visit to one active plan and nothing else.
 *
 * Where the paste vocabulary comes from, and why not from `GET /api/v1/places`: measured on this
 * run's own throwaway database, every CN-TIANJIN `Place` row carries provider_key
 * `citynexus-v9-domain`, which that read excludes (`main.py:16206`) while the parse door deliberately
 * does not (`main.py:27742`). So the places read came back as 0 rows for a city that holds 9. This
 * arm therefore asks the traveller's own itinerary projection for names -- which is what a traveller
 * pastes -- and then lets the parse door itself decide whether a name resolves. Nothing is hard-coded
 * to the 布景, and a reseeded or renamed journey still passes.
 *
 * What each leg is not allowed to fake:
 *   RESOLVED is the door's answer, not this file's guess about name matching.
 *   已加入 needs the row to come back from `readback_path`, on the day the panel claimed, with the day
 *     source the panel claimed. A 201 is not the proof -- the panel itself refuses to treat it as one.
 *   the replay is measured as *one* success sentence, not two: ORD-0524 removed the second one, and a
 *     place that is already on that day must answer 本来就在那一天 while 已加入 disappears.
 *   已收在 needs the shelf read (`GET /api/v1/collections`, scoped by the credential this branch's door
 *     requires) to hold the place id.
 *   只存不排 is measured as an absence: choosing the refused exit takes *both* write controls away.
 *   a link is measured as unread: named form, named host, zero invented rows.
 *   a parse must not tick anything (ORD-0524 ①): 已选 0 is asserted before the 全选 press.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { evidencePath } from "./_qoderEvidence";
import { VIEWPORT, ask, checkinsPath, openAs, stage } from "./_qoderOrd0510Stage";

const FILE = "e2e/qoder-ord0537-poi-import-arm.spec.ts";
const node = (detail: string) => `${FILE} :: ${detail}`;
test.use({ viewport: VIEWPORT, hasTouch: true });

/* Same rule as the slice-1 arms: a number that only lives in a console line is not evidence, because
   the log it was read out of sits outside the repository.  This writes the arm's whole measurement
   next to `reports/qoder-ord0510/*.json` so the claims in `fusion/QODER_RESULT.md` §6 can be checked
   against a file in the same commit. */
function write(name: string, body: unknown) {
  const p = evidencePath("qoder-ord0537", name + ".json");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(body, null, 1), "utf8");
}

const SHELF_NAME = "导入架子";
const JUNK_PHRASE = "zzz-没有这个地点-qqq";
/* A bare URL, with no words beside it: measured, "看这篇 <url>" is *not* link-only to this parser --
   the segment survives the URL strip as a phrase, so that paste legitimately produces one UNRESOLVED
   row and the empty state never appears. The pure link is the form the door refuses by name. */
const LINK_ONLY_PASTE = "https://www.xiaohongshu.com/explore/abcdef123456";

type Activity = {
  id: string;
  place_id?: string | null;
  title?: string;
  start_at?: string | null;
  activity_type?: string | null;
};

/** Ask the parse door which itinerary name this branch can actually resolve to one place. */
async function pickResolvable(
  request: APIRequestContext,
  journeyId: string,
  candidates: { id: string; name: string }[],
): Promise<{ place: { id: string; name: string }; probe: string[] }> {
  const probe: string[] = [];
  for (const place of candidates) {
    const res = await ask<{ items?: { title: string; status: string; place_id: string | null }[] }>(
      request,
      "POST",
      `/api/v1/journeys/${journeyId}/poi-import/parse`,
      { data: { text: place.name } },
    );
    const top = res.items?.[0];
    probe.push(`${place.name}=${top?.status ?? "no-item"}`);
    if (top && top.status === "RESOLVED" && top.place_id === place.id) return { place, probe };
  }
  throw new Error(
    `${node("no itinerary place answered RESOLVED to its own id")} (${probe.join(", ") || "no candidates"})`,
  );
}

test("qoder-ord0537-poi-import — 贴文本认出地点、同日重放不说第二次成功、三条去处各自兑现", async ({
  browser,
  request,
}) => {
  test.setTimeout(300_000);
  const s = await stage(request, "poi-import");

  const experience = await ask<{ active_plan?: { activities?: Activity[] } | null }>(
    request,
    "GET",
    `/api/v1/journeys/${s.journeyId}/experience`,
  );
  const activities = experience?.active_plan?.activities ?? [];
  expect(activities.length, node("this journey has no plan for the import to append to")).toBeGreaterThan(0);

  const dayOf = (a: Activity) => (a.start_at || "").slice(0, 10);
  const dates = activities.map(dayOf).filter(Boolean).sort();
  const firstDay = dates[0] ?? "";
  expect(firstDay.length, node("the plan has no day, so the automatic landing has no target"))
    .toBeGreaterThan(0);

  /* Candidates: places on the plan that sit on some day *other* than the plan's first. Those are the
     rows for which the automatic landing is a real write rather than a same-day replay, and the door's
     own duplicate rule is per day, so which day a name is already on decides what the screen may say. */
  const visitable = activities.filter((a) => a.place_id && dayOf(a) !== firstDay);
  expect(visitable.length, node(`every place on this plan is already on ${firstDay}, so nothing can be added`))
    .toBeGreaterThan(0);
  const { place: target, probe } = await pickResolvable(
    request,
    s.journeyId,
    visitable.map((a) => ({ id: String(a.place_id), name: String(a.title ?? "") })).filter((p) => p.name),
  );
  const targetDay = dayOf(visitable.find((a) => String(a.place_id) === target.id) as Activity);

  // A shelf for the collect exit, created through the same door the screen uses.
  const shelvesBefore = await ask<any[]>(request, "GET", "/api/v1/collections", { token: s.token });
  if (!shelvesBefore.some((f) => f.name === SHELF_NAME)) {
    await ask(request, "POST", "/api/v1/collections", { token: s.token, data: { name: SHELF_NAME } });
  }

  const { page, close } = await openAs(browser, s, s.token, "/v8/import");
  const log: Record<string, unknown> = {
    journey_id: s.journeyId,
    plan_rows_before: activities.length,
    first_day: firstDay,
    target_day: targetDay,
    resolve_probe: probe,
    target: target,
  };

  /* ---- the screen paints, the day is disclosed before anything is asked for ---- */
  await expect(page.getByTestId("poi-import"), node("the import screen did not mount on /v8/import"))
    .toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("poi-import-day-disclosure"), node("the landing day is not disclosed up front"))
    .toContainText(firstDay, { timeout: 20_000 });

  await page.getByTestId("poi-import-mode-screenshot").click();
  await expect(page.getByTestId("poi-import-mode-unsupported"), node("截图识别 is not refused by name"))
    .toBeVisible();
  await expect(page.getByTestId("poi-import-text"), node("the screenshot mode still offers a text box"))
    .toHaveCount(0);
  await page.getByTestId("poi-import-mode-text").click();

  /* ---- a link-only paste is answered as unread, host named, and invents no row ---- */
  await page.getByTestId("poi-import-text").fill(LINK_ONLY_PASTE);
  await page.getByTestId("poi-import-parse").click();
  await expect(page.getByTestId("poi-import-card"), node("the link-only parse never reached a phase"))
    .toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("poi-import-unsupported"), node("the link-only paste named no unread form"))
    .toContainText("LINK_ONLY");
  await expect(page.getByTestId("poi-import-unsupported"), node("the unread link's host was not named"))
    .toContainText("xiaohongshu.com");
  await expect(page.getByTestId("poi-import-empty"), node("a link-only paste invented rows")).toBeVisible();
  const invented = await page.getByTestId("poi-candidate-card").count();
  expect(invented, node(`the link-only paste painted ${invented} candidate rows`)).toBe(0);

  /* ---- 清空重写 acts on this screen's own input ---- */
  await page.getByTestId("poi-import-empty-clear").click();
  await expect(page.getByTestId("poi-import-card"), node("清空重写 left the result card mounted")).toHaveCount(0);
  await expect(page.getByTestId("poi-import-text"), node("清空重写 did not empty the box")).toHaveValue("");

  /* ---- exit 1, first press: text -> parse -> select -> write -> read back ---- */
  await page.getByTestId("poi-import-text").fill([target.name, JUNK_PHRASE].join("；"));
  await page.getByTestId("poi-import-parse").click();
  await expect(page.getByTestId("poi-import-card"), node("the text parse never finished"))
    .toHaveAttribute("data-phase", "success", { timeout: 20_000 });

  const rows = page.getByTestId("poi-candidate-card");
  await expect(rows, node("the paste did not become two rows")).toHaveCount(2);
  const targetRow = rows.filter({ hasText: target.name }).first();
  await expect(targetRow, node(`"${target.name}" is not the RESOLVED row`)).toHaveAttribute(
    "data-poi-status",
    "RESOLVED",
  );
  await expect(targetRow).toHaveAttribute("data-poi-addable", "yes");
  const junkRow = rows.filter({ hasText: JUNK_PHRASE }).first();
  await expect(junkRow, node("the junk row matched something")).toHaveAttribute("data-poi-status", "UNRESOLVED");
  await expect(junkRow.getByTestId("poi-candidate-reason"), node("the unmatched row states no reason"))
    .toBeVisible();

  /* ---- the card's own words are read from this branch's dictionary ----
     Seven of the nine `poiImport.card*` keys render on this screen.  The two that need two of our
     places answering one pasted line (要你选 and its reason) are not reachable from the seeded city's
     rows, so they stay proven at the door only
     (backend test_two_matches_become_the_travelers_choice_not_a_guess) -- saying "nine keys on glass"
     would be a claim this arm does not support. */
  await expect(
    targetRow.getByTestId("poi-candidate-state"),
    node("the RESOLVED row's status word is not the dictionary's"),
  ).toHaveText("已对上");
  await expect(
    targetRow.getByTestId("poi-candidate-phrase"),
    node("the resolved row did not echo the traveller's own line back"),
  ).toHaveText(`你写的是：${target.name}`);
  await expect(
    targetRow.locator(".v8-stay-impact b"),
    node("the resolved row carries no line counter"),
  ).toHaveText(/^第 \d+ 行$/);
  await expect(
    junkRow.getByTestId("poi-candidate-state"),
    node("the unresolved row's status word is not the dictionary's"),
  ).toHaveText("这里没有");
  await expect(
    junkRow.getByTestId("poi-candidate-reason"),
    node("the unresolved row's reason is not the dictionary's sentence"),
  ).toHaveText("这座城市的地点里没有能对上这一行的，所以不能添加。");

  /* One control, two states, both words painted -- the tick alone would be a state only a test can read. */
  const pick = targetRow.getByTestId("poi-card-select");
  await expect(pick, node("the addable card's toggle does not offer the pick")).toHaveText("选中");
  await pick.click();
  await expect(pick, node("tapping the card's own toggle did not pick it")).toHaveAttribute("data-picked", "true");
  /* `toContainText` here and not there: the picked state paints the tick span (`aria-hidden`, but its
     glyph is in the text node) next to the word, so the button's whole text is 已选中——点一下取消 with a
     leading ✓.  The unpicked state has an empty glyph span, which is why that one is pinned exactly. */
  await expect(pick, node("a picked card does not say how to unpick it")).toContainText("已选中——点一下取消");
  const deselectWord = await pick.innerText();
  await pick.click();
  await expect(pick, node("the card's toggle is not reversible")).toHaveAttribute("data-picked", "false");
  await expect(pick, node("after unpicking the word did not return")).toHaveText("选中");

  /* What was actually on the glass, kept in the evidence file so the count is a read and not a claim. */
  log.card_words = {
    matched: await targetRow.getByTestId("poi-candidate-state").innerText(),
    unresolved: await junkRow.getByTestId("poi-candidate-state").innerText(),
    unresolved_why: await junkRow.getByTestId("poi-candidate-reason").innerText(),
    phrase: await targetRow.getByTestId("poi-candidate-phrase").innerText(),
    line_counter: await targetRow.locator(".v8-stay-impact b").innerText(),
    select: await pick.innerText(),
    deselect: deselectWord,
  };

  await expect(page.getByTestId("poi-import-select-all"), node("nothing was addable to select")).toBeVisible();
  await expect(page.getByTestId("poi-import-selection-count"), node("the parse pre-selected rows"))
    .toContainText("已选 0");
  await page.getByTestId("poi-import-select-all").click();
  await expect(page.getByTestId("poi-import-select-all")).toHaveAttribute("data-picked", "true");
  const picked = await page.getByTestId("poi-import-selection-count").innerText();
  const counts = (picked.match(/已选 (\d+) \/ 可加 (\d+)/) ?? []).slice(1, 3).map(Number);
  expect(counts, node(`the count line does not read as 已选 n / 可加 m: "${picked}"`)).toEqual([1, 1]);

  await expect(page.getByTestId("poi-import-add"), node("the plan write stayed shut after 全选")).toBeEnabled();
  await page.getByTestId("poi-import-add").click();
  await expect(page.getByTestId("poi-import-added"), node("the plan write never said 已加入"))
    .toContainText("个地点已在", { timeout: 20_000 });
  await expect(page.getByTestId("poi-import-added")).toContainText(firstDay);
  await expect(page.getByTestId("poi-import-added-source"), node("the answer does not say whose day it was"))
    .toContainText("JOURNEY_FIRST_DAY");

  const afterAdd = await ask<{ active_plan?: { activities?: Activity[] } | null }>(
    request,
    "GET",
    `/api/v1/journeys/${s.journeyId}/experience`,
  );
  const afterAddActs = afterAdd?.active_plan?.activities ?? [];
  const addedRows = afterAddActs.filter((a) => String(a.place_id ?? "") === target.id);
  expect(
    addedRows.length,
    node(`"${target.name}" is 已加入 on the glass but the plan door holds ${addedRows.length} rows for it`),
  ).toBe(2);
  const landed = addedRows.filter((a) => dayOf(a) === firstDay);
  expect(landed.length, node(`no row for "${target.name}" landed on ${firstDay}`)).toBe(1);
  const junkRows = afterAddActs.filter((a) => String(a.title ?? "").includes(JUNK_PHRASE)).length;
  log.after_add = {
    plan_rows: afterAddActs.length,
    added_activity_id: landed[0].id,
    added_start_at: landed[0].start_at,
    junk_rows: junkRows,
  };
  expect(junkRows, node("the unmatched line was written anyway")).toBe(0);

  /* ---- exit 1, second press on the day the place is already on: one sentence, not two ---- */
  await page.getByTestId("poi-import-day").fill(targetDay);
  await expect(page.getByTestId("poi-import-landing-day"), node("the chosen day is not a row of text"))
    .toContainText(targetDay);
  await expect(page.getByTestId("poi-import-landing-day"), node("the screen does not say the day is the traveller's"))
    .toContainText("你选的日子");
  await page.getByTestId("poi-import-add").click();
  await expect(page.getByTestId("poi-import-already-present"), node("the replay was not reported as already there"))
    .toContainText("本来就在那一天", { timeout: 20_000 });
  await expect(page.getByTestId("poi-import-added"), node("a replay painted a second success sentence"))
    .toHaveCount(0);

  const afterReplay = await ask<{ active_plan?: { activities?: Activity[] } | null }>(
    request,
    "GET",
    `/api/v1/journeys/${s.journeyId}/experience`,
  );
  const replayRows = (afterReplay?.active_plan?.activities ?? []).filter(
    (a) => String(a.place_id ?? "") === target.id && dayOf(a) === targetDay,
  );
  expect(
    replayRows.length,
    node(`the replay put ${replayRows.length} rows on ${targetDay} for "${target.name}"`),
  ).toBe(1);
  log.after_replay = { plan_rows: (afterReplay?.active_plan?.activities ?? []).length };

  /* ---- exit 2: the chosen row onto a shelf, counted off the re-read ---- */
  await page.getByTestId("poi-import-exit-shelf").click();
  await expect(page.getByTestId("poi-import-shelves"), node("the shelf exit read no shelves"))
    .toBeVisible({ timeout: 20_000 });
  await page.getByTestId("poi-import-shelf").filter({ hasText: SHELF_NAME }).first().click();
  await page.getByTestId("poi-import-collect").click();
  await expect(page.getByTestId("poi-import-collected"), node("the batch collect never said 已收在"))
    .toContainText("枚已收在", { timeout: 20_000 });
  await expect(page.getByTestId("poi-import-collected")).toContainText(SHELF_NAME);

  const shelvesAfter = await ask<any[]>(request, "GET", "/api/v1/collections", { token: s.token });
  const shelf = shelvesAfter.find((f) => f.name === SHELF_NAME);
  expect(shelf, node(`the shelf "${SHELF_NAME}" is not what the read door returned`)).toBeTruthy();
  const held: string[] = (shelf.items ?? []).map((i: any) => String(i.place_id ?? ""));
  expect(held.includes(target.id), node(`已收在 on screen, but the shelf read does not hold ${target.id}`)).toBe(
    true,
  );
  log.shelf = { id: shelf.id, name: shelf.name, item_count: shelf.item_count, holds_target: true };

  /* ---- exit 3: 只存不排 is chosen by the absence of a door, not by a colour ---- */
  await page.getByTestId("poi-import-exit-store-only").click();
  await expect(page.getByTestId("poi-import-store-only-refused"), node("the refused exit said nothing"))
    .toBeVisible();
  await expect(page.getByTestId("poi-import-add"), node("the refused exit still offers the plan write"))
    .toHaveCount(0);
  await expect(page.getByTestId("poi-import-collect"), node("the refused exit still offers the shelf write"))
    .toHaveCount(0);

  /* ---- 去城市探索 is the shell's own navigate, so the empty cell has a real way out ---- */
  await page.getByTestId("poi-import-text").fill(LINK_ONLY_PASTE);
  await page.getByTestId("poi-import-parse").click();
  await expect(page.getByTestId("poi-import-empty-discover"), node("the empty state offers no way out"))
    .toBeVisible({ timeout: 20_000 });
  await page.getByTestId("poi-import-empty-discover").click();
  await expect(page, node("去城市探索 did not navigate")).toHaveURL(/\/v8\/discover/);
  await expect(page.getByTestId("prep-panel"), node("the discovery screen did not mount behind that nav"))
    .toBeVisible({ timeout: 20_000 });
  log.nav_landed_on = new URL(page.url()).pathname;

  /* The plan append must not mint stamps: the check-in read belongs to the slice-1 arms, and this run
     touches it only by reading. */
  const stamps = await ask<any[]>(request, "GET", checkinsPath(s.journeyId), { token: s.token });
  log.stamps_after_import = stamps.length;

  await close();
  write("import_arm", log);
  console.log("O537POI " + JSON.stringify(log));
});
