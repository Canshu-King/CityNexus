/* ORD-0439 · the comparison screen's gate. Four arms, each aimed at the way a ranking screen lies.
 *
 * The candidates are REAL: the arm creates a traveller and a journey and calls
 * `POST /api/v1/journeys/{id}/plans/generate`, the same door the product uses.  The city and window that
 * can actually generate on the frozen fixture are pinned at `CITY`/`WINDOW` below; the fixture itself is
 * `backend/app/services.py:766` (`_templates()` is a fixture of `CNX-DEMO` place ids).  Nothing here
 * patches a response, because a comparison built from a stub compares the stub -- and the arms therefore
 * write rows into whichever database the run's backend owns.  They never touch another journey's rows.
 *
 * P1 the dimension set on screen is the set this order declared, and the sentence that says what the
 *    ranking used names only dimensions that actually differ between the plans;
 * P2 a field the payload does not carry is reported as absent, never as 0 -- "price unknown" and
 *    "not measured" must not become "cheapest" and "no walking";
 * P3 evidence quality is said in our own named state: a `SYNTHETIC_DEFAULT` leg is never presented as
 *    a provider result on this screen;
 * P4 with nothing to compare the screen says so and ranks nothing -- it does not manufacture a plan.
 *
 * How it was actually run (so the green means what it says): a lane config that points Playwright at this
 * lane's own uvicorn and its own `vite preview` over the freshly built bundle -- not `npm run dev`, and not
 * the shared backend.  The exact command, ports, ports-ownership proof and stats are recorded in
 * `review/ord0439-plan-ranking/GATE_R1.txt`.  `playwright.config.ts` does discover these four arms too
 * (`--list` counts them); a run through it would describe whatever backend that config starts, so no
 * reading quoted here comes from it.
 */
import { test, expect, type Page } from "@playwright/test";
import { RANK_DIMS, rankPlans } from "../src/features/planning/planRanking";
import { fillRank, rankCopy } from "../src/features/planning/planRankingCopy";

const FILE = "e2e/qoder-ord0439-plan-ranking.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();
const LOCALE = "zh-CN";
const say = (key: string, params: Record<string, string | number> = {}) =>
  fillRank(rankCopy(LOCALE, key as never), params);

const CITY = "CNX-DEMO";
const WINDOW = { start: "2026-09-21T02:00:00+00:00", end: "2026-09-22T10:00:00+00:00" };

/** Real generation through the product's own door. Returns the journey id, or null when the door
 *  refuses -- and the arm then says which refusal it got instead of passing quietly. */
async function generateCandidates(page: Page, count: number, arm: string) {
  const traveler = await page.request.post("/api/v1/travelers", {
    data: { display_name: `ORD-0439 ${arm}`, locale: "zh-CN", timezone: "Asia/Shanghai" },
  });
  expect(traveler.status(), node("stage", `建旅行者没有收，实读=${traveler.status()}`)).toBe(201);
  const journey = await page.request.post("/api/v1/journeys", {
    data: {
      traveler_id: (await traveler.json()).id,
      title: `ORD-0439 ${arm}`,
      city_code: CITY,
      timezone: "Asia/Shanghai",
      start_at: WINDOW.start,
      end_at: WINDOW.end,
      budget: { currency: "CNY", amount_minor: 500000 },
      planning_mode: "balanced",
    },
  });
  expect(journey.status(), node("stage", `建行程没有收，实读=${journey.status()}`)).toBe(201);
  const id = String((await journey.json()).id);
  const generated = await page.request.post(`/api/v1/journeys/${id}/plans/generate`, {
    data: { candidate_count: count },
  });
  expect(
    generated.status(),
    node("stage", `真生成被拒（HTTP ${generated.status()}）：${clean(await generated.text()).slice(0, 200)}`),
  ).toBe(201);
  const created = (await generated.json()) as unknown[];
  expect(created.length, node("stage", `生成收了但没返回候选，实读=${created.length}`)).toBeGreaterThanOrEqual(2);
  return id;
}

async function openHub(page: Page, journeyId: string) {
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
  const panel = page.getByTestId("plan-ranking");
  await expect(panel, node("stage", "对比屏没有挂在今天屏上")).toBeVisible({ timeout: 30_000 });
  return panel;
}

async function readTable(panel: ReturnType<Page["getByTestId"]>) {
  const dims = await panel.locator('[data-testid="rank-dim"]').evaluateAll((ns) =>
    ns.map((n) => ({ name: String(n.innerText).replace(/\s+/g, " ").trim(), comparable: n.getAttribute("data-comparable") })),
  );
  const rows = await panel.locator('[data-testid="rank-row"]').evaluateAll((trs) =>
    trs.map((tr) =>
      Array.from(tr.querySelectorAll("td")).map((td) => ({
        text: String(td.innerText).replace(/\s+/g, " ").trim(),
        state: td.getAttribute("data-state"),
        dim: td.getAttribute("data-testid") ?? "",
      })),
    ),
  );
  const notes = await panel
    .locator('[data-testid="rank-note"]')
    .evaluateAll((ls) => ls.map((l) => String(l.innerText).replace(/\s+/g, " ").trim()));
  return {
    dims,
    rows,
    notes,
    rankedBy: clean(await panel.locator('[data-testid="rank-ranked-by"]').innerText()),
    pressable: await panel.locator("button, a, [role=button], input, select, summary").count(),
  };
}

test("P1 屏上的维度集合就是表里声明的那四个，排序只念真分得开的那几维", async ({ page }) => {
  const jid = await generateCandidates(page, 3, "P1");
  const panel = await openHub(page, jid);
  await expect(panel.locator('[data-testid="rank-row"]').first()).toBeVisible({ timeout: 20_000 });
  const t = await readTable(panel);

  expect(t.dims.map((d) => d.name).join("、"), node("P1", `维度名不是这四个：${t.dims.map((d) => d.name).join("、")}`)).toBe(
    RANK_DIMS.map((d) => say(`rank.dim.${d}`)).join("、"),
  );
  const used = t.dims.filter((d) => d.comparable === "true").map((d) => d.name);
  expect(used.length, node("P1", `一维都分不开却说按维度排了：${t.rankedBy}`)).toBeGreaterThan(0);
  for (const name of used) {
    expect(t.rankedBy.includes(name), node("P1", `分得开的「${name}」没被念出来：${t.rankedBy}`)).toBe(true);
  }
  for (const d of t.dims.filter((x) => x.comparable === "false")) {
    expect(t.rankedBy.includes(d.name), node("P1", `分不开的「${d.name}」被当成排序依据：${t.rankedBy}`)).toBe(false);
  }
  expect(t.pressable, node("P1", `只读对比屏长出了 ${t.pressable} 个可交互元素`)).toBe(0);
});

test("P2 载荷里没有的那一维不许被写成 0：价格与步行各自要说出自己缺什么", async ({ page }) => {
  const jid = await generateCandidates(page, 2, "P2");
  const panel = await openHub(page, jid);
  await expect(panel.locator('[data-testid="rank-row"]').first()).toBeVisible({ timeout: 20_000 });
  const t = await readTable(panel);

  const sent = (await (await page.request.get(`/api/v1/journeys/${jid}/plans`)).json()) as Array<{
    status: string; stale?: boolean; total_cost?: { amount_minor?: number | null };
    mobility_evidence?: { facts?: Array<{ walking_min?: number | null }> };
  }>;
  const candidates = sent.filter((p) => p.status === "CANDIDATE" && !p.stale);
  expect(candidates.length, node("P2", `服务器返回的候选不够两版，实读=${candidates.length}`)).toBeGreaterThanOrEqual(2);

  for (const row of t.rows) {
    for (const cell of row) {
      const absentExpected =
        cell.dim === "rank-cell-walk"
          ? candidates.every((p) => (p.mobility_evidence?.facts ?? []).every((f) => typeof f.walking_min !== "number"))
          : cell.dim === "rank-cell-cost"
            ? candidates.every((p) => typeof p.total_cost?.amount_minor !== "number")
            : false;
      if (absentExpected) {
        expect(cell.state, node("P2", `${cell.dim} 载荷里没有，屏上却当有值渲染：${cell.text}`)).toBe("absent");
        expect(["0", "0 ", "0.00", "CNY 0.00"].includes(cell.text), node("P2", `缺的字段被写成了 0：${cell.text}`)).toBe(false);
      }
    }
  }
  const walkCells = t.rows.map((r) => r.find((c) => c.dim === "rank-cell-walk")).filter(Boolean);
  expect(walkCells.length, node("P2", "没有步行列可读的行，这一格就是空转")).toBeGreaterThan(0);
});

test("P3 合成默认值的路段不会被说成供应商结果", async ({ page }) => {
  const jid = await generateCandidates(page, 2, "P3");
  const panel = await openHub(page, jid);
  await expect(panel.locator('[data-testid="rank-row"]').first()).toBeVisible({ timeout: 20_000 });
  const t = await readTable(panel);
  const joined = t.notes.join(" ");
  expect(t.notes.length, node("P3", "没有一条证据说明，这一格就是空转")).toBeGreaterThan(0);
  expect(joined.includes("闸门认可"), node("P3", `没说清哪几段是闸门认可的硬依据：${joined.slice(0, 160)}`)).toBe(true);
  if (joined.includes("SYNTHETIC_DEFAULT")) {
    expect(joined.includes("供应商"), node("P3", `把合成默认值说成了供应商结果：${joined.slice(0, 200)}`)).toBe(false);
  }
  for (const cell of t.rows.map((r) => r.find((c) => c.dim === "rank-cell-evidence")).filter((c) => c)) {
    expect(/^\d+\/\d+$/.test(cell!.text), node("P3", `硬证据那一格不是「几/共几」的形状：${cell!.text}`)).toBe(true);
  }
});

test("P4 没有可比方案时说实话，不为屏上有东西造一版", async ({ page }) => {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const jid = String(scene.journey_id ?? "");
  expect(jid.length, node("P4", "舞台没有已点名的旅程")).toBeGreaterThan(0);
  const panel = await openHub(page, jid);
  const rows = await panel.locator('[data-testid="rank-row"]').count();
  if (rows > 0) {
    test.skip(true, `封存演示那趟现在有 ${rows} 份可比候选，P4 需要一趟没有候选的行程才判空态`);
  }
  const none = panel.locator('[data-testid="rank-none"]');
  await expect(none, node("P4", "没有可比方案时屏上没有那句实话")).toBeVisible({ timeout: 20_000 });
  expect(clean(await none.innerText()), node("P4", `空态那句不是那句人话：${clean(await none.innerText())}`)).toBe(
    say("rank.none"),
  );
  await expect(panel.locator('[data-testid="rank-ranked-by"]'), node("P4", "空态下还在宣布排序依据")).toHaveCount(0);
});
