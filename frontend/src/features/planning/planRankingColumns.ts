/* Table column mechanics for the comparison screen: one place produces a cell's text, so the width
   a column is measured with is the width of the words it actually paints. */

import { RANK_DIMS, type AbsentReason, type RankDim, type RankedPlan } from "./planRanking";
import type { PlanRankCopyKey } from "./planRankingCopy";

export type RankCol = "version" | RankDim;

/* Derived from RANK_DIMS, never restated: the header row and the column boxes have to agree on
   order, and a second literal list is how they would start to disagree. */
export const RANK_COLS: RankCol[] = ["version", ...RANK_DIMS];

export const DIM_KEYS: Record<RankDim, PlanRankCopyKey> = {
  cost: "rank.dim.cost",
  walk: "rank.dim.walk",
  protected: "rank.dim.protected",
  evidence: "rank.dim.evidence",
};

export const ABSENT_KEYS: Record<string, PlanRankCopyKey> = {
  priceUnknown: "rank.priceUnknown",
  walkNotMeasured: "rank.walkNotMeasured",
  protectedNotMarked: "rank.protectedNotMarked",
  noFacts: "rank.noFacts",
};

export const COL_KEYS: Record<RankCol, PlanRankCopyKey> = {
  version: "rank.version",
  ...DIM_KEYS,
};

export type Say = (key: PlanRankCopyKey, params?: Record<string, string | number>) => string;

export function moneyOf(minor: number, currency: string): string {
  return `${currency} ${(minor / 100).toFixed(2)}`;
}

/** The single source of a cell's words. `absent` keeps its own sentence rather than a zero, because
 *  "price unknown" rendered as 0.00 would read as the cheapest plan on the screen. */
export function cellText(row: RankedPlan, col: RankCol, say: Say, currency: string): string {
  if (col === "version") return `${say("rank.version")} ${row.versionNo}`;
  const cell = row.cells[col];
  if (cell.kind === "absent") return say(ABSENT_KEYS[cell.reason]);
  if (col === "cost") return moneyOf(cell.number, currency);
  if (col === "evidence") return `${cell.number}/${row.evidence.total}`;
  return `${cell.number}${cell.partial ? ` (${say("rank.walkPartial")})` : ""}`;
}

/** The number a column sorts on, or null when the plan does not answer that dimension. */
export function sortValue(row: RankedPlan, col: RankCol): number | null {
  if (col === "version") return row.versionNo;
  const cell = row.cells[col];
  return cell.kind === "value" ? cell.number : null;
}

export type SortState = { col: RankCol; dir: "asc" | "desc" };

/** Clicking a header walks it: unsorted -> ascending -> descending -> back to the product's order. */
export function nextSort(current: SortState | null, col: RankCol): SortState | null {
  if (!current || current.col !== col) return { col, dir: "asc" };
  if (current.dir === "asc") return { col, dir: "desc" };
  return null;
}

export function sortRankedRows(rows: RankedPlan[], sort: SortState | null): RankedPlan[] {
  if (!sort) return rows;
  const direction = sort.dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = sortValue(a, sort.col);
    const y = sortValue(b, sort.col);
    /* An unanswered dimension is not the lowest value it could have had, so it is parked below every
       number in both directions instead of being multiplied by the direction. */
    if (x === null && y === null) return a.versionNo - b.versionNo;
    if (x === null) return 1;
    if (y === null) return -1;
    if (x === y) return a.versionNo - b.versionNo;
    return (x - y) * direction;
  });
}

/** Which dimensions a plan leaves unanswered — the rows a traveller can filter on. */
export function absentReasonsOf(row: RankedPlan): AbsentReason[] {
  const reasons: AbsentReason[] = [];
  for (const dim of RANK_DIMS) {
    const cell = row.cells[dim];
    if (cell.kind === "absent") reasons.push(cell.reason);
  }
  return reasons;
}

export const FILTER_REASONS: AbsentReason[] = [
  "priceUnknown",
  "walkNotMeasured",
  "protectedNotMarked",
  "noFacts",
];

export const FILTER_KEYS: Record<AbsentReason, PlanRankCopyKey> = {
  priceUnknown: "rank.priceUnknown",
  walkNotMeasured: "rank.walkNotMeasured",
  protectedNotMarked: "rank.protectedNotMarked",
  noFacts: "rank.noFacts",
};

export function filterRankedRows(rows: RankedPlan[], hidden: AbsentReason[]): RankedPlan[] {
  if (hidden.length === 0) return rows;
  return rows.filter((row) => {
    const reasons = absentReasonsOf(row);
    return !hidden.some((reason) => reasons.includes(reason));
  });
}

export const MIN_COL_WIDTH = 96;
export const MAX_COL_WIDTH = 460;
/* 6px 8px padding either side of a cell, plus the resize grip that sits on the boundary. */
const CELL_INSET = 16 + 12;

export function clampWidth(width: number): number {
  return Math.round(Math.min(MAX_COL_WIDTH, Math.max(MIN_COL_WIDTH, width)));
}

let measureContext: CanvasRenderingContext2D | null | undefined;

function fontOf(element: Element): string {
  const style = element ? getComputedStyle(element) : null;
  if (!style) return "12px sans-serif";
  return `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
}

/** Auto layout gives the widest header the most room, which is the wrong trade on this table: a
 *  four-character cell under a long heading inherits the heading's width. So measure the words that
 *  are actually painted and size the column to the larger of heading and body. */
export function measureColumnWidths(
  headers: Element[],
  bodyRows: Element[][],
  fallback: number,
): Record<RankCol, number> {
  const widths = {} as Record<RankCol, number>;
  if (typeof document === "undefined") return widths;
  if (measureContext === undefined) {
    const canvas = document.createElement("canvas");
    measureContext = canvas.getContext("2d");
  }
  const ctx = measureContext;
  if (!ctx) {
    for (let i = 0; i < RANK_COLS.length; i += 1) widths[RANK_COLS[i]] = clampWidth(fallback);
    return widths;
  }
  headers.forEach((header, index) => {
    const col = RANK_COLS[index];
    if (!col) return;
    ctx.font = fontOf(header);
    let widest = ctx.measureText(header.textContent?.trim() ?? "").width;
    for (const row of bodyRows) {
      const cell = row[index];
      if (!cell) continue;
      ctx.font = fontOf(cell);
      widest = Math.max(widest, ctx.measureText(cell.textContent?.trim() ?? "").width);
    }
    widths[col] = clampWidth(Math.ceil(widest) + CELL_INSET);
  });
  return widths;
}

export const COLUMN_WIDTH_KEY = "citynexus.plan-ranking.column-widths.v1";

export function readStoredWidths(): Partial<Record<RankCol, number>> {
  try {
    const raw = localStorage.getItem(COLUMN_WIDTH_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const out = {} as Partial<Record<RankCol, number>>;
    for (const col of RANK_COLS) {
      const value = Number(parsed?.[col]);
      if (Number.isFinite(value) && value > 0) out[col] = clampWidth(value);
    }
    return out;
  } catch {
    return {};
  }
}

export function writeStoredWidths(widths: Record<RankCol, number>): void {
  try {
    localStorage.setItem(COLUMN_WIDTH_KEY, JSON.stringify(widths));
  } catch {
    /* A blocked storage is a lost preference, not a broken table. */
  }
}
