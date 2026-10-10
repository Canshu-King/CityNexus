import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { useAuthoritativePlans } from "../../api/v12Authoritative";
import { rankPlans, RANK_DIMS, type ComparablePlan, type AbsentReason } from "./planRanking";
import { fillRank, rankCopy, type PlanRankCopyKey } from "./planRankingCopy";
import { mobilityFactQualityLabel } from "../../lib/displayVocabulary";
import {
  COL_KEYS,
  DIM_KEYS,
  FILTER_KEYS,
  FILTER_REASONS,
  RANK_COLS,
  cellText,
  filterRankedRows,
  nextSort,
  sortRankedRows,
  type RankCol,
  type SortState,
} from "./planRankingColumns";
import { useRankingColumns } from "./useRankingColumns";
import "./planRanking.css";

/* ORD-0439: the comparison screen. It ranks the candidates the server already holds -- it never
   manufactures one, and it never shows a number the payload did not send. */

/* `stale` and `selectable` are answered by the route but are not in the committed generated types
   (the same gap `PlanComparison.tsx` documents), so the view type declares them here instead of
   widening a contract claim. */
type Row = ComparablePlan & {
  id: string;
  version_no: number;
  status: string;
  stale?: boolean;
  selectable?: boolean;
};

/** The shell already knows which journey it is on; the panel reads it the way the version list does,
 *  so mounting a new screen never needs another prop threaded through `V8Experience.tsx`. */
function useStoredJourneyId(): string | null {
  const [id, setId] = useState<string | null>(() => localStorage.getItem("citynexus.v8.journey_id"));
  useEffect(() => {
    const onStorage = () => setId(localStorage.getItem("citynexus.v8.journey_id"));
    window.addEventListener("storage", onStorage);
    const timer = window.setInterval(onStorage, 2000);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.clearInterval(timer);
    };
  }, []);
  return id;
}

export function PlanRankingPanel({ budgetMinor, currency }: { budgetMinor: number; currency: string }) {
  const { locale } = useLocale();
  const journeyId = useStoredJourneyId();
  const plans = useAuthoritativePlans(journeyId);
  const say = (key: PlanRankCopyKey, params: Record<string, string | number> = {}) =>
    fillRank(rankCopy(locale, key), params);

  const tableRef = useRef<HTMLTableElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [sort, setSort] = useState<SortState | null>(null);
  const [hidden, setHidden] = useState<AbsentReason[]>([]);

  const candidates = ((plans.data ?? []) as unknown as Row[]).filter(
    (plan) => plan.status === "CANDIDATE" && !plan.stale && plan.selectable !== false,
  );
  const { rows, comparable, usedDims } = rankPlans(candidates);
  const visible = useMemo(
    () => sortRankedRows(filterRankedRows(rows, hidden), sort),
    [rows, hidden, sort],
  );
  const columns = useRankingColumns(
    tableRef,
    scrollRef,
    `${visible.length}|${locale}|${currency}|${rows.map((row) => row.id).join(",")}`,
  );

  const toggleReason = (reason: AbsentReason) =>
    setHidden((current) =>
      current.includes(reason) ? current.filter((item) => item !== reason) : [...current, reason],
    );

  if (plans.isPending && !plans.isError) {
    return (
      <section className="plan-ranking" data-testid="plan-ranking">
        <p className="v8-muted" data-testid="rank-loading">{say("rank.loading")}</p>
      </section>
    );
  }
  if (plans.isError) {
    return (
      <section className="plan-ranking" data-testid="plan-ranking">
        <p className="v8-message" role="alert" data-testid="rank-failed">{say("rank.failed")}</p>
        <button
          type="button"
          className="v8-outline-button"
          data-testid="rank-retry"
          onClick={() => void plans.refetch()}
        >
          {say("rank.retry")}
        </button>
      </section>
    );
  }
  if (rows.length === 0) {
    return (
      <section className="plan-ranking" data-testid="plan-ranking">
        <p className="v8-muted" data-testid="rank-none">{say("rank.none")}</p>
        <p className="v8-muted plan-ranking-hint" data-testid="rank-none-hint">{say("rank.noneHint")}</p>
        <button
          type="button"
          className="v8-outline-button"
          data-testid="rank-none-retry"
          onClick={() => void plans.refetch()}
        >
          {say("rank.retry")}
        </button>
      </section>
    );
  }

  const sortedDimLabel = sort ? say(COL_KEYS[sort.col]) : "";
  const tableWidth = RANK_COLS.reduce((sum, col) => sum + columns.widths[col as RankCol], 0);

  return (
    <section className="plan-ranking" data-testid="plan-ranking">
      <header className="v12-panel-header">
        <div>
          <span className="v8-kicker">{say("rank.title")}</span>
          <p className="v8-muted">{say("rank.sub")}</p>
        </div>
      </header>
      <p className="plan-ranking-by" data-testid="rank-ranked-by">
        {usedDims.length > 0
          ? say("rank.rankedBy", { dims: usedDims.map((d) => say(DIM_KEYS[d])).join("、") })
          : say("rank.tie", { dims: RANK_DIMS.map((d) => say(DIM_KEYS[d])).join("、") })}
      </p>
      {rows.length === 1 && <p className="v8-muted" data-testid="rank-only-one">{say("rank.onlyOne")}</p>}

      <div className="plan-ranking-controls" data-testid="rank-controls">
        <span className="v8-muted plan-ranking-hint" data-testid="rank-sort-hint">
          {sort
            ? say("rank.sortActive", { dim: sortedDimLabel, direction: say(sort.dir === "asc" ? "rank.sortAsc" : "rank.sortDesc") })
            : say("rank.sortHint")}
        </span>
        {sort && (
          <button
            type="button"
            className="v8-text-button"
            data-testid="rank-sort-return"
            onClick={() => setSort(null)}
          >
            {say("rank.sortReturn")}
          </button>
        )}
        {columns.isCustom && (
          <button
            type="button"
            className="v8-text-button"
            data-testid="rank-columns-reset"
            onClick={columns.resetAll}
          >
            {say("rank.columnsReset")}
          </button>
        )}
      </div>

      {rows.length > 1 && (
        <div className="plan-ranking-filters" data-testid="rank-filters">
          <span className="plan-ranking-filter-title">{say("rank.filterTitle")}</span>
          {FILTER_REASONS.map((reason) => (
            <button
              key={reason}
              type="button"
              className="plan-ranking-chip"
              data-testid={`rank-filter-${reason}`}
              aria-pressed={hidden.includes(reason) ? "true" : "false"}
              onClick={() => toggleReason(reason)}
            >
              {say(FILTER_KEYS[reason])}
            </button>
          ))}
          <span className="v8-muted" data-testid="rank-filter-result">
            {say("rank.filterResult", { shown: visible.length, total: rows.length })}
          </span>
          {hidden.length > 0 && (
            <button
              type="button"
              className="v8-text-button"
              data-testid="rank-filter-clear"
              onClick={() => setHidden([])}
            >
              {say("rank.filterClear")}
            </button>
          )}
        </div>
      )}

      {visible.length === 0 ? (
        <p className="v8-muted" data-testid="rank-filtered-none">
          {say("rank.filteredNone")}
          <button
            type="button"
            className="v8-text-button"
            data-testid="rank-filtered-none-clear"
            onClick={() => setHidden([])}
          >
            {say("rank.filterClear")}
          </button>
        </p>
      ) : (
        <div className="plan-ranking-scroll" ref={scrollRef}>
          <table
            ref={tableRef}
            className="plan-ranking-table"
            data-testid="plan-ranking-table"
            data-custom={columns.isCustom ? "true" : "false"}
            style={{ width: `${tableWidth}px`, minWidth: `${tableWidth}px` }}
          >
            <colgroup>
              {RANK_COLS.map((col) => (
                <col key={col} style={{ width: `${columns.widths[col as RankCol]}px` }} />
              ))}
            </colgroup>
            <thead>
              <tr>
                {RANK_COLS.map((col) => {
                  const isDim = col !== "version";
                  const active = sort?.col === col;
                  return (
                    <th
                      key={col}
                      scope="col"
                      className="plan-ranking-head"
                      data-testid={isDim ? "rank-dim" : undefined}
                      data-comparable={isDim ? (comparable[col] ? "true" : "false") : undefined}
                      aria-sort={active ? (sort?.dir === "asc" ? "ascending" : "descending") : "none"}
                    >
                      <button
                        type="button"
                        className="plan-ranking-sort"
                        data-testid={`rank-sort-${col}`}
                        aria-label={say("rank.sortAria", { dim: say(COL_KEYS[col]) })}
                        onClick={() => setSort(nextSort(sort, col))}
                      >
                        {say(COL_KEYS[col])}
                        <span className="plan-ranking-arrow" aria-hidden="true">
                          {active ? (sort?.dir === "asc" ? "▲" : "▼") : "↕"}
                        </span>
                      </button>
                      <span
                        role="separator"
                        aria-orientation="vertical"
                        tabIndex={0}
                        className="plan-ranking-grip"
                        data-testid={`rank-grip-${col}`}
                        data-dragging={columns.dragging === col ? "true" : "false"}
                        aria-label={say("rank.gripAria", { dim: say(COL_KEYS[col]) })}
                        title={say("rank.gripHint")}
                        onPointerDown={(event) => columns.beginDrag(col, event)}
                        onDoubleClick={() => columns.releaseColumn(col)}
                        onKeyDown={(event) => {
                          if (event.key === "ArrowRight") {
                            event.preventDefault();
                            columns.nudge(col, 16);
                          } else if (event.key === "ArrowLeft") {
                            event.preventDefault();
                            columns.nudge(col, -16);
                          } else if (event.key === "Home") {
                            event.preventDefault();
                            columns.releaseColumn(col);
                          }
                        }}
                      />
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {visible.map((row, index) => (
                <tr key={row.id} data-testid="rank-row" data-place={index + 1}>
                  <th scope="row" data-testid="rank-version" title={cellText(row, "version", say, currency)}>
                    {cellText(row, "version", say, currency)}
                  </th>
                  {RANK_DIMS.map((d) => (
                    <td
                      key={d}
                      data-testid={`rank-cell-${d}`}
                      data-state={row.cells[d].kind}
                      title={cellText(row, d, say, currency)}
                    >
                      {cellText(row, d, say, currency)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {visible.length > 0 && (
        <ul className="plan-ranking-notes">
          {visible.map((row) => (
            <li key={row.id} data-testid="rank-note">
              {say("rank.evidenceNote", {
                hard: row.evidence.hard,
                total: row.evidence.total,
                quality:
                  row.evidence.worstQuality === null
                    ? "—"
                    : mobilityFactQualityLabel(row.evidence.worstQuality, locale),
              })}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
