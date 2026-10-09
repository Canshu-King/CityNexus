/**
 * The comparison table must not lie when it degrades.
 *
 * ORD-0439's screen ranks plans on numbers this product computes. Three of its behaviours fail
 * silently rather than loudly: an unanswered dimension rendered as zero reads as "cheapest", a
 * filter that keeps unanswered rows reads as a comparison, and a missing dictionary key in one
 * language falls back to the other arm without any visible break. None of those would show up as a
 * console error, so they are pinned here as behaviour, not as source text.
 *
 * Pure-node spec, no page and no backend: it exercises the same functions the panel calls.
 */

import { test, expect } from "@playwright/test";
import {
  clampWidth,
  cellText,
  filterRankedRows,
  MAX_COL_WIDTH,
  MIN_COL_WIDTH,
  nextSort,
  sortRankedRows,
  type Say,
} from "../src/features/planning/planRankingColumns";
import { rankPlans } from "../src/features/planning/planRanking";
import { planRankingCopy } from "../src/features/planning/planRankingCopy";
import type { Cell, RankDim, RankedPlan } from "../src/features/planning/planRanking";

const DIMS: RankDim[] = ["cost", "walk", "evidence", "protected"];

function plan(versionNo: number, cells: Partial<Record<RankDim, Cell>>, totalFacts = 2): RankedPlan {
  const filled = {} as Record<RankDim, Cell>;
  for (const dim of DIMS) {
    filled[dim] = cells[dim] ?? { kind: "absent", reason: "noFacts" };
  }
  return {
    id: `p${versionNo}`,
    versionNo,
    cells: filled,
    evidence: { hard: 1, total: totalFacts, worstQuality: null },
  };
}

const order = (rows: RankedPlan[]) => rows.map((row) => row.versionNo);

const say: Say = (key, params = {}) =>
  String(key).replace(/^rank\./, "") + (params.dims ? `:${params.dims}` : "");

test("a dimension nobody answered is never ranked as if it were zero", () => {
  const rows = [
    plan(1, { cost: { kind: "value", number: 0 } }),
    plan(2, { cost: { kind: "absent", reason: "priceUnknown" } }),
    plan(3, { cost: { kind: "value", number: 5000 } }),
  ];

  const ascending = sortRankedRows(rows, { col: "cost", dir: "asc" });
  expect(order(ascending)).toEqual([1, 3, 2]);

  const descending = sortRankedRows(rows, { col: "cost", dir: "desc" });
  expect(order(descending)).toEqual([3, 1, 2]);

  expect(ascending[ascending.length - 1].cells.cost.kind).toBe("absent");
  expect(descending[descending.length - 1].cells.cost.kind).toBe("absent");
});

test("the unanswered rows keep their own order instead of being scattered", () => {
  const rows = [
    plan(7, { walk: { kind: "absent", reason: "walkNotMeasured" } }),
    plan(4, { walk: { kind: "value", number: 90 } }),
    plan(2, { walk: { kind: "absent", reason: "noFacts" } }),
    plan(9, { walk: { kind: "value", number: 10 } }),
  ];

  expect(order(sortRankedRows(rows, { col: "walk", dir: "asc" }))).toEqual([9, 4, 2, 7]);
  expect(order(sortRankedRows(rows, { col: "walk", dir: "desc" }))).toEqual([4, 9, 2, 7]);
});

test("sorting does not mutate the ranked order the product computed", () => {
  const rows = [
    plan(1, { cost: { kind: "value", number: 30 } }),
    plan(2, { cost: { kind: "value", number: 10 } }),
  ];
  const before = order(rows);
  sortRankedRows(rows, { col: "cost", dir: "desc" });
  expect(order(rows)).toEqual(before);
});

test("a header click walks unsorted to ascending to descending and back to unsorted", () => {
  expect(nextSort(null, "cost")).toEqual({ col: "cost", dir: "asc" });
  expect(nextSort({ col: "cost", dir: "asc" }, "cost")).toEqual({ col: "cost", dir: "desc" });
  expect(nextSort({ col: "cost", dir: "desc" }, "cost")).toBeNull();
  expect(nextSort({ col: "walk", dir: "asc" }, "cost")).toEqual({ col: "cost", dir: "asc" });
});

test("filtering on a missing dimension cannot leave a row that answers it", () => {
  const rows = [
    plan(1, { cost: { kind: "value", number: 10 }, walk: { kind: "value", number: 20 } }),
    plan(2, { cost: { kind: "value", number: 10 }, walk: { kind: "absent", reason: "walkNotMeasured" } }),
    plan(3, { cost: { kind: "absent", reason: "priceUnknown" }, walk: { kind: "value", number: 5 } }),
  ];

  const onlyMeasuredWalk = filterRankedRows(rows, ["walkNotMeasured"]);
  expect(order(onlyMeasuredWalk)).toEqual([1, 3]);
  for (const row of onlyMeasuredWalk) {
    expect(row.cells.walk.kind).toBe("value");
  }

  expect(order(filterRankedRows(rows, ["priceUnknown"]))).toEqual([1, 2]);
  expect(order(filterRankedRows(rows, []))).toEqual([1, 2, 3]);
});

test("an unanswered cell is never printed as a number", () => {
  const absent = plan(5, { cost: { kind: "absent", reason: "priceUnknown" } });
  const text = cellText(absent, "cost", say, "CNY");
  expect(text).toBe("priceUnknown");
  expect(text).not.toMatch(/0/);

  const zero = plan(6, { cost: { kind: "value", number: 0 } });
  expect(cellText(zero, "cost", say, "CNY")).toBe("CNY 0.00");
});

test("a measured walk sum says so when only some legs were measured", () => {
  const partial = plan(8, { walk: { kind: "value", number: 40, partial: true } });
  expect(cellText(partial, "walk", say, "CNY")).toContain("walkPartial");
});

test("column widths stay inside the band that keeps words readable", () => {
  expect(clampWidth(1)).toBe(MIN_COL_WIDTH);
  expect(clampWidth(99_999)).toBe(MAX_COL_WIDTH);
  expect(clampWidth(240)).toBe(240);
  expect(MIN_COL_WIDTH).toBeLessThan(MAX_COL_WIDTH);
});

test("the ranking still refuses to invent a dimension every plan shares", () => {
  const asPayload = (versionNo: number, costMinor: number, walkMin: number) => ({
    id: `p${versionNo}`,
    version_no: versionNo,
    total_cost: { amount_minor: costMinor },
    mobility_evidence: { facts: [{ walking_min: walkMin }, { walking_min: walkMin }] },
    activities: [{ protected: true }],
  });
  const ranked = rankPlans([asPayload(1, 10, 5), asPayload(2, 20, 5)]);
  expect(ranked.comparable.walk).toBe(false);
  expect(ranked.comparable.cost).toBe(true);
  expect(ranked.usedDims).toEqual(["cost"]);
});

test("both language arms carry exactly the same keys", () => {
  const en = Object.keys(planRankingCopy.en).sort();
  const zh = Object.keys(planRankingCopy["zh-CN"]).sort();
  expect(zh).toEqual(en);
  expect(en.length).toBeGreaterThan(0);
});
