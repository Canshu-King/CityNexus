/**
 * ORD-0702 甲 · a stopped clock is not a cancelled run, and an empty book is not an empty city.
 *
 * TWO DEFECTS, ONE SCREEN, MEASURED ON THE PHONE FIRST (`_cmdr_fe_rev_1016/cmdr_ord0702a_*`).
 *
 * (1) The keyless-write deadline ended the WHOLE submission. `fetchWithKeylessWriteDeadline` wrapped
 *     the `agent/commands` leg, and its throw was caught by the run's outer `catch`, so the device's
 *     own 60 s bound acted like a cancellation: the deterministic composer below it was never asked.
 *     A traveller whose model answered in 81 s read 「这一笔的结果未知」 and got neither plans nor a
 *     count. Measured with the mission leg held for 70 s: before this commit the run issued no
 *     further request after the deadline; after it, `/plans/generate` went out at 72 s and answered
 *     201, and the candidates were on the screen under the unknown sentence.
 *
 * (2) The fallback then asked the WRONG question. It fetched `/api/v1/places` with no parameters and
 *     called a zero-row answer `CATALOG_EMPTY` -- but that default view is the city-exploration book:
 *     `backend/app/main.py:7640` excludes `_SERVER_OWNED_PLACE_PROVIDERS` and the structural
 *     categories unless `include_structural=true`, and those excluded rows are exactly what this
 *     journey's composer places. Measured on the live preview library, one city, one request each:
 *     the default view returned 0 rows, the planner's view returned 12, and the compose leg that
 *     followed them put 3 candidates on the stage. So the screen told a traveller "this city has no
 *     place data" about a city holding twelve of its own places, and that sentence is unretractable
 *     once it has been read.
 *
 * Arms (each reads rendered text plus the request ledger, never a source string):
 *   M1  deadline arm, the shipped shape: the mission leg never answers, the device's bound fires,
 *       and the run must STILL ask the catalogue -- in the planner's terms -- and the composer
 *       afterwards. `UNKNOWN_KEYLESS_WRITE_DEADLINE` stays exactly as ORD-0310 pinned it (this arm
 *       goes red if the unknown is traded away for a green), and the plans this device can prove are
 *       carried beside that sentence instead of forfeited by it.
 *   M2  catalogue arm, no clock pressure: the model answers in time and produces nothing, and the
 *       city holds only server-owned/structural rows. It must land on real composed candidates and
 *       must not emit the 「没有任何地点数据」 sentence.
 *   M3  negative control: a city that is empty in the planner's OWN terms must still be allowed to
 *       say `CATALOG_EMPTY`, and must not knock on the composer. Without this arm, "always pass the
 *       flag" would look like a fix while silencing a true emptiness.
 *
 * The flag is a strict superset (`main.py:7640` only ever REMOVES two exclusion filters), so M3's
 * zero on the planner's view is also a zero on the explorer's view -- the empty claim stays honest.
 *
 * WHAT DID NOT IMPROVE, stated instead of quietly asserted away. On the UNKNOWN card the count this
 * device did prove (`data-plan-count`, `data-new-plan-ids`) is carried as attributes, while the
 * traveller-readable units row (`plan-ai-units`) is emitted only for `COMPLETED` /
 * `PLANS_WITHOUT_AI` (`aiGenerationRun.ts`, the `unitsFromRows` ternary). Making that row speak on a
 * Q54=① card adds a sentence to a surface an arbitration pinned, so it is a ruling to ask for, not a
 * midnight edit. M1 therefore records `units_line` as an observation and asserts nothing about it; if
 * the ruling comes back "speak it", this file needs one line, not a rewrite.
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";
import { KEYLESS_WRITE_DEADLINE_MS } from "../src/lib/keylessWriteDeadline";

const FILE = "e2e/qoder-ord0702a-keyless-deadline-still-asks-compose.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "norunid";

const USER_SENTENCE = "傍晚到得正好，先去吃碗面，再沿着河边慢慢走一段。";
/** The refusal this slice removes for cities that do hold placeable rows (PlanWithAiSheet BLOCKED_BY_CODE). */
const EMPTY_CLAIM = "这座城我们还没有任何地点数据";
/** The ORD-0310 half of the same card, which has to survive untouched. */
const UNKNOWN_TITLE = "结果未知";
/** Attribution this screen is forbidden to make about its own clock (Q54=①). */
const FORBIDDEN = ["已取消", "没有发生", "再点一次就行"];

/** Rows the planner's view returns and the city-explorer's view hides on purpose. */
const SERVER_OWNED_ROWS = [
  { id: "cmdr-0702a-place-arrival", name: "到达锚点", category: "arrival", provider_key: "citynexus-v12-authoritative" },
  { id: "cmdr-0702a-place-stay", name: "住的地方", category: "stay", provider_key: "citynexus-v12-authoritative" },
  { id: "cmdr-0702a-place-riverside", name: "河边散步", category: "sightseeing", provider_key: "citynexus-v9-domain" },
];

/** Two candidates with the shape `planStamp` reads, so the units line is earned rather than stubbed in. */
const COMPOSED_ROWS = [
  {
    id: "cmdr-0702a-plan-a", is_current: true, status: "CANDIDATE", version_no: 7,
    activities: [
      { id: "act-a1", start_at: "2026-10-09T18:30:00+08:00" },
      { id: "act-a2", start_at: "2026-10-09T19:40:00+08:00" },
    ],
  },
  {
    id: "cmdr-0702a-plan-b", is_current: false, status: "CANDIDATE", version_no: 8,
    activities: [{ id: "act-b1", start_at: "2026-10-10T09:00:00+08:00" }],
  },
];

type ArmId = "M1" | "M2" | "M3";
type Ledger = {
  t0: number;
  places: { at_ms: number; with_planner_flag: boolean }[];
  generate_posts: number;
  generate_at_ms: number | null;
  mission_posts: number;
};

const readings: Record<string, unknown> = {};

/**
 * Interception over exactly the legs this run owns. The shell, the journey read and everything else
 * keep going to the real backend: a stub that swallowed the whole app would prove nothing about the
 * ORDER of operations, which is the thing under test.
 */
async function stubLegs(page: Page, ledger: Ledger, opts: {
  /** `hold` never answers the mission leg; `answered` replies with a mission that produced nothing. */
  mission: "hold" | "answered";
  /** Whether the planner's view holds rows. The explorer's view is empty in every arm -- that is the defect. */
  plannerRows: boolean;
}): Promise<void> {
  await page.route(() => true, async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    const at = () => Math.max(0, Date.now() - ledger.t0);

    if (/\/api\/v1\/journeys\/[^/]+\/agent\/commands$/.test(path) && method === "POST") {
      ledger.mission_posts += 1;
      if (opts.mission === "hold") {
        // The measured shape of "the server may still be working": no answer at all, not a failure.
        return new Promise<never>(() => {});
      }
      return route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({
          accepted: true,
          mission: { id: `cmdr-0702a-${opts.mission}-mission`, status: "COMPLETED",
            failure_reason: null, reasoning_summary: null },
        }),
      });
    }

    if (path === "/api/v1/places" && method === "GET") {
      const flagged = url.searchParams.get("include_structural") === "true";
      ledger.places.push({ at_ms: at(), with_planner_flag: flagged });
      const rows = flagged && opts.plannerRows ? SERVER_OWNED_ROWS : [];
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(rows) });
    }

    if (/\/api\/v1\/journeys\/[^/]+\/plans\/generate$/.test(path) && method === "POST") {
      ledger.generate_posts += 1;
      ledger.generate_at_ms = at();
      return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(COMPOSED_ROWS) });
    }

    /* The baseline read -- and the verification re-count -- are this run's own arithmetic, so the
       stage starts empty in every arm. The `$` keeps `/plans/generate` out of this branch. */
    if (/\/api\/v1\/journeys\/[^/]+\/plans$/.test(path) && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }

    return route.fallback();
  });
}

async function openSheetAndSubmit(page: Page, arm: ArmId, ledger: Ledger): Promise<void> {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId.length > 0, node(arm, "舞台没点出旅程")).toBe(true);
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node(arm, "首页没渲染")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("hub-plan-with-ai").click();
  await page.getByTestId("plan-ai-input").fill(USER_SENTENCE);
  /* The clock starts at the press, because everything this file claims is an offset from it. */
  ledger.t0 = Date.now();
  await page.getByTestId("plan-ai-submit").click();
}

async function readCard(page: Page) {
  const result = page.getByTestId("plan-ai-result");
  const units = page.getByTestId("plan-ai-units");
  return {
    status: (await result.getAttribute("data-result-status")) ?? "",
    plan_count: (await result.getAttribute("data-plan-count")) ?? "",
    new_plan_ids: (await result.getAttribute("data-new-plan-ids")) ?? "",
    units_line: (await units.count()) > 0 ? clean(await units.innerText()) : "",
    text: clean(await result.innerText()),
  };
}

function decide(arm: ArmId, read: Awaited<ReturnType<typeof readCard>>, ledger: Ledger) {
  const rows: { claim: string; ok: boolean; got: unknown }[] = [];
  const add = (claim: string, ok: boolean, got: unknown) => rows.push({ claim, ok, got });
  const flagged = ledger.places.filter((p) => p.with_planner_flag);
  const plain = ledger.places.length - flagged.length;

  if (arm === "M3") {
    add("这座城在排程器自己的口径下也确实空，所以拒答照旧", read.status === "BLOCKED:CATALOG_EMPTY", read.status);
    add("屏上仍说得出那句「没有任何地点数据」（修口径不等于噤声）", read.text.includes(EMPTY_CLAIM), read.text.slice(0, 90));
    add("目录确实空的时候不去敲方案口", ledger.generate_posts === 0,
      { generate_posts: ledger.generate_posts, places: ledger.places.length });
    add("那句「空」也是在排程器的口径上读的（不是只问过探索目录就下结论）", flagged.length > 0,
      { flagged: flagged.length, plain });
  } else {
    add("这一趟仍然去问了目录", ledger.places.length > 0, ledger.places.length);
    add("问目录用的是排程器那一份口径（带 include_structural）", flagged.length > 0,
      { flagged: flagged.length, plain });
    add("那句「没有任何地点数据」不再出现", !read.text.includes(EMPTY_CLAIM), read.text.slice(0, 120));
    add("没有落成 CATALOG_* 的拒答", !read.status.startsWith("BLOCKED:CATALOG"), read.status);
    add("方案口被真敲了一次", ledger.generate_posts === 1, ledger.generate_posts);
    add("排出来的两枚候选落在这张卡上",
      read.plan_count === "2" && read.new_plan_ids === "cmdr-0702a-plan-a,cmdr-0702a-plan-b",
      { plan_count: read.plan_count, new_plan_ids: read.new_plan_ids });
    if (arm === "M2") {
      add("可核对的单位行渲染出来了", read.units_line.length > 0, read.units_line);
    }
  }

  if (arm === "M1") {
    add("ORD-0310 的那句仍在：这一笔结果未知", read.status === "UNKNOWN_KEYLESS_WRITE_DEADLINE", read.status);
    add("「结果未知」与「不是没发生」都还在屏上",
      read.text.includes(UNKNOWN_TITLE) && read.text.includes("不是没发生"), read.text.slice(0, 120));
    add("期限到点之后才去问的目录（排程器口径那一问落在期限之后）",
      flagged.some((p) => p.at_ms >= KEYLESS_WRITE_DEADLINE_MS),
      { flagged_offsets_ms: flagged.map((p) => p.at_ms), deadline_ms: KEYLESS_WRITE_DEADLINE_MS });
    add("这台设备的期限确实先到了：方案口在期限之后才发出",
      ledger.generate_at_ms !== null && ledger.generate_at_ms >= KEYLESS_WRITE_DEADLINE_MS,
      { generate_at_ms: ledger.generate_at_ms, deadline_ms: KEYLESS_WRITE_DEADLINE_MS });
    add("任务口没有被这台设备自己补发第二发", ledger.mission_posts === 1, ledger.mission_posts);
    add("禁句一个都没有", FORBIDDEN.every((s) => !read.text.includes(s)),
      FORBIDDEN.filter((s) => read.text.includes(s)));
  }
  if (arm === "M2") {
    add("模型按时答完、自己又没排出东西时，这一趟以候选收尾", read.status === "COMPLETED", read.status);
    add("屏上出现「个可选方案」这类计数句", read.text.includes("个可选方案"), read.text.slice(0, 120));
    add("两枚候选都挂在卡上", read.plan_count === "2", read.plan_count);
  }

  const bad = rows.filter((r) => !r.ok);
  readings[arm] = {
    read,
    places_asked: ledger.places.length,
    places_asked_with_planner_flag: flagged.length,
    places_asked_plain: plain,
    place_offsets: ledger.places,
    generate_posts: ledger.generate_posts,
    generate_at_ms: ledger.generate_at_ms,
    mission_posts: ledger.mission_posts,
    deadline_ms: KEYLESS_WRITE_DEADLINE_MS,
    verdict: bad.length === 0 ? "MET" : "NOT_MET",
    rows,
    ...(bad.length ? { failed: bad.map((b) => b.claim) } : {}),
  };
  expect(bad.map((b) => b.claim), node(arm, JSON.stringify({ status: read.status, plan_count: read.plan_count })))
    .toEqual([]);
}

test("M1 期限到点后仍要问目录与方案口：未知的归未知，数得出来的归数得出来", async ({ page }) => {
  test.setTimeout(KEYLESS_WRITE_DEADLINE_MS + 150_000);
  const ledger: Ledger = { t0: Date.now(), places: [], generate_posts: 0, generate_at_ms: null,
    mission_posts: 0 };
  await stubLegs(page, ledger, { mission: "hold", plannerRows: true });
  await openSheetAndSubmit(page, "M1", ledger);
  await expect(page.getByTestId("plan-ai-result"), node("M1", "期限到了也没有结局卡"))
    .toBeVisible({ timeout: KEYLESS_WRITE_DEADLINE_MS + 90_000 });
  await expect(page.getByTestId("plan-ai-result"), node("M1", "结局卡上没有两枚候选"))
    .toHaveAttribute("data-plan-count", "2", { timeout: 30_000 });
  await decide("M1", await readCard(page), ledger);
});

test("M2 只有服务器自有地点的城：不许说「没有任何地点数据」，要落到真候选", async ({ page }) => {
  const ledger: Ledger = { t0: Date.now(), places: [], generate_posts: 0, generate_at_ms: null,
    mission_posts: 0 };
  await stubLegs(page, ledger, { mission: "answered", plannerRows: true });
  await openSheetAndSubmit(page, "M2", ledger);
  await expect(page.getByTestId("plan-ai-result"), node("M2", "没有结局卡"))
    .toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("plan-ai-result"), node("M2", "结局卡上没有两枚候选"))
    .toHaveAttribute("data-plan-count", "2", { timeout: 30_000 });
  await decide("M2", await readCard(page), ledger);
});

test("M3 负控制：排程器口径下也空的城，仍要如实说空，并且不去敲方案口", async ({ page }) => {
  const ledger: Ledger = { t0: Date.now(), places: [], generate_posts: 0, generate_at_ms: null,
    mission_posts: 0 };
  await stubLegs(page, ledger, { mission: "answered", plannerRows: false });
  await openSheetAndSubmit(page, "M3", ledger);
  await expect(page.getByTestId("plan-ai-result"), node("M3", "没有结局卡"))
    .toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("plan-ai-result"), node("M3", "状态没落成 CATALOG_EMPTY"))
    .toHaveAttribute("data-result-status", "BLOCKED:CATALOG_EMPTY", { timeout: 30_000 });
  await decide("M3", await readCard(page), ledger);
});

test.afterAll(() => {
  writeFileSync(evidencePath("ord0702a", `deadline_still_asks_compose_arms-${RUN}.json`),
    JSON.stringify({ file: FILE, runId: RUN, deadline_ms: KEYLESS_WRITE_DEADLINE_MS, arms: readings }, null, 1));
});
