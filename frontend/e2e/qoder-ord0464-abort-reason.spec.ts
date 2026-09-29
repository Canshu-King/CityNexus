/* ORD-0464 · the gate for the question that stands in front of binning a trip.
 *
 * Seven arms. The journeys are real: each arm creates a traveller and a journey through the product's
 * own doors and calls the product's own `DELETE /api/v1/journeys/{id}`. Nothing here pretends a
 * deletion happened by rewriting a response -- the one arm that must *show a refusal on screen* (A6)
 * replays a 422 this same server really answered, byte for byte, and is labelled as a renderer arm.
 *
 * A1 the eight boxes on screen are exactly the vocabulary the generated client carries, and no machine
 *    token reaches the traveller's line;
 * A2 a declared reason lands as one `JOURNEY_DELETED` row in the traveller's own order, the screen says
 *    those reasons, and after a reload the screen still says them -- read off the server, not
 *    remembered in React state;
 * A3 skipping is its own state on screen and in the row, and is never rendered as a declaration;
 * A4 the note limit the box enforces is the limit this door really enforces (n accepted, n+1 refused);
 * A5 with nothing ticked the declaring button says why it waits, and the skip is still reachable;
 * A6 a named refusal from this server renders as its own sentence with its receipt, not as a generic
 *    "something went wrong" and not as the raw token;
 * A7 the sheet is actually tappable on a phone: scrolled into view, hit-tested at its own centre.
 *
 * How these were run is recorded with the order's receipts; the lane serves this tree's build and this
 * tree's sqlite copy, not `npm run dev` and not the shared preview database.
 */
import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import {
  ABORT_REASON_KEYS,
  abortCopy,
  fillAbort,
} from "../src/features/abort/journeyAbortCopy";

const FILE = "e2e/qoder-ord0464-abort-reason.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();
const LOCALE = "zh-CN";
const say = (key: string, params: Record<string, string | number> = {}) =>
  fillAbort(abortCopy(LOCALE, key as never), params);

const CITY = "CNX-DEMO";
const WINDOW = { start: "2027-05-06T02:00:00+00:00", end: "2027-05-08T10:00:00+00:00" };

async function createJourney(page: Page, arm: string): Promise<string> {
  const traveler = await page.request.post("/api/v1/travelers", {
    data: { display_name: `ORD-0464 ${arm}`, locale: "zh-CN", timezone: "Asia/Shanghai" },
  });
  expect(traveler.status(), node("stage", `建旅行者没有收，实读=${traveler.status()}`)).toBe(201);
  const journey = await page.request.post("/api/v1/journeys", {
    data: {
      traveler_id: (await traveler.json()).id,
      title: `ORD-0464 ${arm}`,
      city_code: CITY,
      timezone: "Asia/Shanghai",
      start_at: WINDOW.start,
      end_at: WINDOW.end,
      budget: { currency: "CNY", amount_minor: 500000 },
      planning_mode: "balanced",
    },
  });
  expect(journey.status(), node("stage", `建行程没有收，实读=${journey.status()}`)).toBe(201);
  return String((await journey.json()).id);
}

async function openHub(page: Page, journeyId: string, arm: string) {
  await page.addInitScript(
    ([id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", "zh-CN");
    },
    [journeyId],
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  const panel = page.getByTestId("journey-abort");
  await expect(panel, node(arm, "原因采集没有挂在今天屏上")).toBeVisible({ timeout: 30_000 });
  return panel;
}

/** The recorded fact, read from the door the screen itself reads. */
async function serverRecord(page: Page, journeyId: string) {
  const answer = await page.request.get(`/api/v1/journeys/${journeyId}/outcomes`);
  expect(answer.status(), node("stage", `读 outcomes 没有收，实读=${answer.status()}`)).toBe(200);
  const events = ((await answer.json()).events ?? []) as Array<Record<string, unknown>>;
  const deleted = events.filter((e) => e.event_type === "JOURNEY_DELETED");
  return { deleted, payload: (deleted.at(-1)?.payload ?? null) as Record<string, unknown> | null };
}

test("A1 屏上八项就是契约那八项，机器词面不上屏", async ({ page }) => {
  const jid = await createJourney(page, "A1");
  const panel = await openHub(page, jid, "A1");
  const opener = panel.getByTestId("abort-open");
  await expect(opener, node("A1", "没带上屏的触发钮")).toBeVisible();
  // The boxes live in the sheet, and the sheet only opens on a tap -- counting them before pressing
  // measured a closed screen, which is exactly what the first run of this arm reported (屏上=0).
  await opener.click();

  const api = readFileSync("src/generated/api.ts", "utf-8");
  const union = api.match(/JourneyAbortCode:\s*([^;]+);/);
  expect(union ? 1 : 0, node("A1", "生成的客户端里找不到 JourneyAbortCode 那行，对照无从做起")).toBe(1);
  const declared = [...union[1].matchAll(/"([A-Z_]+)"/g)].map((m) => m[1]);
  expect(declared.length, node("A1", `契约词表枚数不是 8，实读=${declared.length}`)).toBe(8);

  const boxes = panel.locator('[data-testid="abort-code"]');
  await expect(boxes, node("A1", `屏上方框数与契约枚数不等，屏上=${await boxes.count()}`)).toHaveCount(
    declared.length,
  );
  const shown = await boxes.evaluateAll((ns) => ns.map((n) => String(n.getAttribute("data-cnx-code") ?? "")));
  expect([...shown].sort(), node("A1", `屏上词表与契约词表不是同一批：屏=${shown.join(",")}`)).toEqual(
    [...declared].sort(),
  );

  const sheetText = clean(await panel.innerText());
  for (const token of declared) {
    expect(sheetText.includes(token), node("A1", `机器词面 ${token} 直接落在旅客那行上`)).toBe(false);
  }
  /* `clean` is a Node-side helper; inside evaluateAll this is the browser's realm, so the whitespace
     normaliser is written inline. The first run of this arm died on exactly that (`ReferenceError:
     clean is not defined`), which is an instrument bug, not a screen bug. */
  const labels = await panel.locator(".cn-abort-code label span").evaluateAll((ns) =>
    ns.map((n) => String(n.textContent ?? "").replace(/\s+/g, " ").trim()),
  );
  expect(labels.length, node("A1", `说明句数量不对，实读=${labels.length}`)).toBe(declared.length);
  for (let i = 0; i < declared.length; i += 1) {
    const wanted = say(ABORT_REASON_KEYS[declared[i] as keyof typeof ABORT_REASON_KEYS]);
    expect(labels[i], node("A1", `${declared[i]} 的说明句不是字典那句，实读=${labels[i]}`)).toBe(wanted);
  }
});

test("A2 勾了就走真门：一行记录、旅客的顺序、刷新后还说同样的话", async ({ page }) => {
  const jid = await createJourney(page, "A2");
  const panel = await openHub(page, jid, "A2");
  await panel.getByTestId("abort-open").click();
  const order = ["DATES_OR_PLACE_CHANGED", "BUDGET_DOES_NOT_FIT"];
  for (const code of order) {
    await panel.locator(`[data-cnx-code="${code}"]`).check();
  }
  const note = "住宿那一晚超了";
  await panel.getByTestId("abort-note").fill(note);
  await panel.getByTestId("abort-confirm").click();

  const done = panel.getByTestId("abort-done");
  await expect(done, node("A2", "丢掉之后屏上没有说出这条记录")).toBeVisible({ timeout: 20_000 });
  expect(await done.getAttribute("data-cnx-state"), node("A2", "屏上那格状态不是 DECLARED")).toBe("DECLARED");
  const text = clean(await done.innerText());
  const first = say(ABORT_REASON_KEYS.DATES_OR_PLACE_CHANGED);
  const second = say(ABORT_REASON_KEYS.BUDGET_DOES_NOT_FIT);
  expect(
    text.indexOf(first) >= 0 && text.indexOf(first) < text.indexOf(second),
    node("A2", `原因句没按旅客勾的顺序说，实读=${text}`),
  ).toBe(true);

  const { deleted, payload } = await serverRecord(page, jid);
  expect(deleted.length, node("A2", `一次丢弃在 journey_outcome_events 里不是恰好一枚，实读=${deleted.length}`)).toBe(1);
  expect(payload!.reason_state, node("A2", `服务器记的不是 DECLARED，实读=${payload!.reason_state}`)).toBe("DECLARED");
  expect(payload!.codes, node("A2", `服务器记的顺序被改了，实读=${JSON.stringify(payload!.codes)}`)).toEqual(order);
  expect(payload!.note, node("A2", `补充说明没落到行里，实读=${payload!.note}`)).toBe(note);

  await page.reload({ waitUntil: "load" });
  const again = page.getByTestId("abort-done");
  await expect(again, node("A2", "刷新之后这条记录在屏上没有了")).toBeVisible({ timeout: 20_000 });
  expect(clean(await again.innerText()), node("A2", "刷新后那句与刚才那句不是同一句")).toBe(text);
  await expect(page.getByTestId("abort-open"), node("A2", "刷新后还端出「把这趟丢进回收站」，等于说这事没发生")).toHaveCount(0);
});

test("A3 跳过是它自己那一格，不是「没原因」也不是「说了原因」", async ({ page }) => {
  const jid = await createJourney(page, "A3");
  const panel = await openHub(page, jid, "A3");
  await panel.getByTestId("abort-open").click();
  await panel.getByTestId("abort-skip").click();

  const done = panel.getByTestId("abort-done");
  await expect(done, node("A3", "跳过之后屏上没有落定那句")).toBeVisible({ timeout: 20_000 });
  expect(await done.getAttribute("data-cnx-state"), node("A3", "屏上那格状态不是 SKIPPED_BY_TRAVELER")).toBe(
    "SKIPPED_BY_TRAVELER",
  );
  const text = clean(await done.innerText());
  expect(text, node("A3", `跳过那句不是字典里那句实话，实读=${text}`)).toBe(say("abort.doneSkipped"));
  for (const code of Object.keys(ABORT_REASON_KEYS)) {
    expect(
      text.includes(say(ABORT_REASON_KEYS[code as keyof typeof ABORT_REASON_KEYS])),
      node("A3", `跳过却把 ${code} 的说明句端上了屏`),
    ).toBe(false);
  }

  const { deleted, payload } = await serverRecord(page, jid);
  expect(deleted.length, node("A3", `跳过这一趟留下的行数不是 1，实读=${deleted.length}`)).toBe(1);
  expect(payload!.reason_state, node("A3", `服务器把跳过记成了别的，实读=${payload!.reason_state}`)).toBe(
    "SKIPPED_BY_TRAVELER",
  );
  expect(payload!.codes, node("A3", `跳过却带了原因进来，实读=${JSON.stringify(payload!.codes)}`)).toEqual([]);
});

test("A4 输入框上限就是那扇门真的上限", async ({ page }) => {
  const probe = await createJourney(page, "A4-probe");
  const probePanel = await openHub(page, probe, "A4");
  await probePanel.getByTestId("abort-open").click();
  const limit = Number(await probePanel.getByTestId("abort-note").getAttribute("maxlength"));
  expect(Number.isInteger(limit) && limit > 0, node("A4", `输入框没有上限可读，实读=${limit}`)).toBe(true);

  const fits = await createJourney(page, "A4-accepts");
  const accepted = await page.request.delete(`/api/v1/journeys/${fits}`, {
    method: "DELETE",
    data: { answered: true, codes: ["OTHER"], note: "字".repeat(limit) },
  });
  expect(accepted.status(), node("A4", `刚好 ${limit} 字应当收，实读=${accepted.status()}`)).toBe(204);

  const over = await createJourney(page, "A4-refuses");
  const refused = await page.request.delete(`/api/v1/journeys/${over}`, {
    method: "DELETE",
    data: { answered: true, codes: ["OTHER"], note: "字".repeat(limit + 1) },
  });
  expect(refused.status(), node("A4", `${limit + 1} 字竟然被收了，上限是假的`)).toBe(422);
  const { deleted } = await serverRecord(page, over);
  expect(deleted.length, node("A4", "被拒的超长说明还是落了行")).toBe(0);
  const still = await page.request.get(`/api/v1/journeys/${over}`);
  expect(still.status(), node("A4", "被拒的那一 tap 把行程丢了")).toBe(200);
  expect((await still.json()).deleted_at ?? null, node("A4", "被拒的那一 tap 写了 deleted_at")).toBe(null);
});

test("A5 什么都没勾时，等待的那枚按钮自己说明为什么", async ({ page }) => {
  const jid = await createJourney(page, "A5");
  const panel = await openHub(page, jid, "A5");
  await panel.getByTestId("abort-open").click();
  const confirm = panel.getByTestId("abort-confirm");
  const skip = panel.getByTestId("abort-skip");
  expect(await confirm.isDisabled(), node("A5", "一枚没勾就能丢，那「愿意说明」就是假选项")).toBe(true);
  const hint = panel.getByTestId("abort-hint");
  await expect(hint, node("A5", "禁用了却没说为什么禁用")).toBeVisible();
  expect(clean(await hint.innerText()), node("A5", "禁用说明不是字典那句")).toBe(say("abort.pickOne"));
  expect(await skip.isEnabled(), node("A5", "跳过被连带禁掉了，旅客就只能硬说一个原因")).toBe(true);

  const first = panel.locator('[data-cnx-code="OTHER"]');
  await first.check();
  expect(await confirm.isDisabled(), node("A5", "勾了一枚之后仍然不能丢")).toBe(false);
  await first.uncheck();
  await expect(panel.getByTestId("abort-hint"), node("A5", "取消勾选后那句解释没有回来")).toBeVisible();
});

test("A6 服务器具名的拒绝上屏时说的是人话，带的是那张回执", async ({ page }) => {
  /* A renderer arm, and it is honest about it: the bytes below are not invented. They are this same
     server's real answer to a real malformed request (captured against a throwaway journey two lines
     down); only the delivery is intercepted, because the screen cannot produce the contradiction
     itself -- the ticked box is what makes it `answered: true` with no codes at the wire level here. */
  const probe = await createJourney(page, "A6-capture");
  const capture = await page.request.delete(`/api/v1/journeys/${probe}`, {
    method: "DELETE",
    data: { answered: true, codes: [] },
  });
  expect(capture.status(), node("A6", `这台服务器不再答那枚具名拒绝，实读=${capture.status()}`)).toBe(422);
  const body = await capture.text();
  expect(
    JSON.parse(body).error.details.errors[0].type,
    node("A6", "捕获到的不是 ABORT_ANSWER_WITHOUT_CODES 那格，反件无从 Replay"),
  ).toBe("abort_answer_without_codes");
  const receipt = String(JSON.parse(body).error.error_receipt_id ?? "");
  expect(receipt.length, node("A6", "捕获的答复里没有回执号")).toBeGreaterThan(4);

  const jid = await createJourney(page, "A6-screen");
  await page.route("**/api/v1/journeys/*", async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 422, contentType: "application/json", body });
      return;
    }
    await route.fallback();
  });
  const panel = await openHub(page, jid, "A6");
  await panel.getByTestId("abort-open").click();
  await panel.locator('[data-cnx-code="OTHER"]').check();
  await panel.getByTestId("abort-confirm").click();

  const refused = panel.getByTestId("abort-refused");
  await expect(refused, node("A6", "被拒之后屏上没有那格拒绝")).toBeVisible({ timeout: 20_000 });
  expect(await refused.getAttribute("data-cnx-refusal"), node("A6", "读到的不是那枚具名拒绝")).toBe(
    "abort_answer_without_codes",
  );
  const text = clean(await refused.innerText());
  expect(text.includes(say("abort.refuseWithoutCodes")), node("A6", `没说出那句人话，实读=${text}`)).toBe(true);
  expect(text.includes(receipt), node("A6", `没把服务器给的回执号带上，实读=${text}`)).toBe(true);
  expect(text.includes("abort_answer_without_codes"), node("A6", "机器词面直接上了旅客那行")).toBe(false);
  /* A named refusal keeps the sheet open on purpose: the ticks are still the traveller's and the next
     tap is theirs, so the assertion is "the question is still here and nothing was announced as
     binned" -- not "the trigger came back", which is a different design choice this panel does not make. */
  await expect(panel.getByTestId("abort-question"), node("A6", "被拒之后那层问卷没有留在屏上")).toBeVisible();
  await expect(panel.getByTestId("abort-confirm"), node("A6", "被拒之后勾选丢了")).toBeEnabled();
  await expect(panel.getByTestId("abort-done"), node("A6", "被拒的那一 tap 却落成了已丢弃")).toHaveCount(0);
});

test("A8 没人问过的丢弃，屏上说的是没问过，不是旅客答了「不答」", async ({ page }) => {
  /* The other direction of the order's prohibition, produced without a single stub: a client that
     deletes with no body at all -- which is exactly what every client on this tree did before
     ORD-0464 -- must land on NOT_ASKED, and the screen must say the question never arrived. Turning
     that into "you chose not to say" is the fabrication this order was cut to stop. */
  const jid = await createJourney(page, "A8");
  const silent = await page.request.delete(`/api/v1/journeys/${jid}`);
  expect(silent.status(), node("A8", `不带请求体的丢弃竟然被拒，实读=${silent.status()}`)).toBe(204);
  const { payload } = await serverRecord(page, jid);
  expect(payload!.reason_state, node("A8", `服务器把没问过记成了 ${payload!.reason_state}`)).toBe("NOT_ASKED");

  const panel = await openHub(page, jid, "A8");
  const done = panel.getByTestId("abort-done");
  await expect(done, node("A8", "屏上没有落定那格已丢弃")).toBeVisible({ timeout: 20_000 });
  expect(await done.getAttribute("data-cnx-state"), node("A8", "屏上状态不是 NOT_ASKED")).toBe("NOT_ASKED");
  const text = clean(await done.innerText());
  expect(text, node("A8", `那格说的不是「没有收到过这个问题」，实读=${text}`)).toBe(say("abort.doneNotAsked"));
  expect(
    text.includes(say("abort.doneSkipped").replace("，我们也不会替你编一个。", "")),
    node("A8", `没问过被说成了旅客自己选了不说明，实读=${text}`),
  ).toBe(false);
  expect(await done.getAttribute("data-cnx-state"), node("A8", "NOT_ASKED 与 SKIPPED 落成了同一格")).not.toBe(
    "SKIPPED_BY_TRAVELER",
  );
});

test("A7 手机上这一屏真的点得到：滚进视口、按中心命中", async ({ page }) => {
  const jid = await createJourney(page, "A7");
  const panel = await openHub(page, jid, "A7");
  await panel.getByTestId("abort-open").click();
  const confirm = panel.getByTestId("abort-confirm");
  await confirm.scrollIntoViewIfNeeded();
  const box = await confirm.boundingBox();
  expect(box ? box.width : 0, node("A7", `按钮没有尺寸，实读=${JSON.stringify(box)}`)).toBeGreaterThan(0);
  expect(box!.height, node("A7", `触达高度低于 44px，实读=${box!.height}`)).toBeGreaterThanOrEqual(44);
  const viewport = page.viewportSize();
  expect(
    box!.y >= 0 && box!.y + box!.height <= (viewport?.height ?? 0),
    node("A7", `滚完之后仍然没有整枚在视口里，实读 y=${box!.y} h=${box!.height} vh=${viewport?.height}`),
  ).toBe(true);
  const hit = await page.evaluate(
    ([x, y]) => {
      const el = document.elementFromPoint(x, y);
      return el ? `${el.tagName}|${el.getAttribute("data-testid") ?? ""}` : "NONE";
    },
    [box!.x + box!.width / 2, box!.y + box!.height / 2],
  );
  expect(hit.endsWith("|abort-confirm"), node("A7", `中心命中的不是这枚按钮，实读=${hit}`)).toBe(true);
});
