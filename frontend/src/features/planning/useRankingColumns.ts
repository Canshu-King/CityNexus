/* Column sizing for the comparison table: measure the painted words, then let the traveller override
   a column by dragging its boundary, double-clicking it back, or using the keyboard on the grip. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  RANK_COLS,
  clampWidth,
  measureColumnWidths,
  readStoredWidths,
  writeStoredWidths,
  type RankCol,
} from "./planRankingColumns";

const FALLBACK_WIDTH = 140;

/** Size the flexible columns to the words they carry, then let them share whatever the fixed
    (dragged) columns leave over. Doing this here rather than with `width: 100%` keeps a dragged
    boundary answering the pointer one-for-one instead of through a browser's scaling factor. */
function distribute(
  auto: Partial<Record<RankCol, number>>,
  manual: Partial<Record<RankCol, number>>,
  container: number,
): Record<RankCol, number> {
  const out = {} as Record<RankCol, number>;
  const flex: RankCol[] = [];
  let wanted = 0;
  let used = 0;
  for (const col of RANK_COLS) {
    const width = clampWidth(manual[col] ?? auto[col] ?? FALLBACK_WIDTH);
    if (manual[col] != null) {
      out[col] = width;
      used += width;
    } else {
      flex.push(col);
      wanted += width;
    }
  }
  const room = Math.max(0, container - used);
  for (const col of flex) {
    const base = clampWidth(auto[col] ?? FALLBACK_WIDTH);
    out[col] = wanted > 0 && room > wanted ? clampWidth((base * room) / wanted) : base;
  }
  return out;
}

export type RankingColumns = {
  widths: Record<RankCol, number>;
  isCustom: boolean;
  dragging: RankCol | null;
  beginDrag: (col: RankCol, event: React.PointerEvent) => void;
  nudge: (col: RankCol, delta: number) => void;
  releaseColumn: (col: RankCol) => void;
  resetAll: () => void;
  remeasure: () => void;
};

export function useRankingColumns(
  tableRef: React.RefObject<HTMLTableElement | null>,
  wrapperRef: React.RefObject<HTMLElement | null>,
  signature: string,
): RankingColumns {
  const [auto, setAuto] = useState<Partial<Record<RankCol, number>>>({});
  const [manual, setManual] = useState<Partial<Record<RankCol, number>>>(() => readStoredWidths());
  const [dragging, setDragging] = useState<RankCol | null>(null);
  const [container, setContainer] = useState(0);
  const drag = useRef<{ col: RankCol; x: number; width: number } | null>(null);

  const remeasure = useCallback(() => {
    const table = tableRef.current;
    if (!table) return;
    const headers = [...table.querySelectorAll<HTMLElement>("thead th")];
    const bodyRows = [...table.querySelectorAll<HTMLElement>("tbody tr")].map((row) => [
      ...row.querySelectorAll<HTMLElement>("th, td"),
    ]);
    if (headers.length === 0) return;
    setAuto(measureColumnWidths(headers, bodyRows, FALLBACK_WIDTH));
  }, [tableRef]);

  /* Re-measured whenever the words change, so a plan set with longer labels widens the column and a
     set with shorter ones narrows it again — unless the traveller has taken that column over. */
  useEffect(() => {
    remeasure();
  }, [remeasure, signature]);

  /* Re-observed with the data, not only once on mount: the first paint of this panel is the loading
     sentence, so the wrapper — and its width — does not exist yet. */
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper || typeof ResizeObserver === "undefined") return;
    const read = () => setContainer(wrapper.clientWidth);
    read();
    const observer = new ResizeObserver(read);
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, [wrapperRef, signature]);

  const widths = useMemo(
    () => distribute(auto, manual, container),
    [auto, manual, container],
  );

  const commit = useCallback((next: Partial<Record<RankCol, number>>) => {
    setManual(next);
    writeStoredWidths({ ...next } as Record<RankCol, number>);
  }, []);

  const endDrag = useCallback(() => {
    setDragging(null);
    drag.current = null;
    document.body.classList.remove("plan-ranking-resizing");
  }, []);

  const beginDrag = useCallback(
    (col: RankCol, event: React.PointerEvent) => {
      event.preventDefault();
      drag.current = { col, x: event.clientX, width: widths[col] };
      setDragging(col);
      document.body.classList.add("plan-ranking-resizing");
    },
    [widths],
  );

  useEffect(() => {
    if (!dragging) return;
    const onMove = (event: PointerEvent) => {
      const active = drag.current;
      if (!active) return;
      setManual((current) => {
        const next = {
          ...current,
          [active.col]: clampWidth(active.width + (event.clientX - active.x)),
        };
        writeStoredWidths(next as Record<RankCol, number>);
        return next;
      });
    };
    const onUp = () => endDrag();
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [dragging, endDrag]);

  const nudge = useCallback(
    (col: RankCol, delta: number) => {
      setManual((current) => {
        /* Start from the width on screen, not the measured content width: a flexible column is
           wider than its words because it absorbed the leftover, and nudging from the ungrown
           number made one arrow key visibly shrink the column. */
        const from = current[col] ?? widths[col];
        const next = { ...current, [col]: clampWidth(from + delta) };
        writeStoredWidths(next as Record<RankCol, number>);
        return next;
      });
    },
    [widths],
  );

  const releaseColumn = useCallback(
    (col: RankCol) => {
      const next = { ...manual };
      delete next[col];
      commit(next);
      remeasure();
    },
    [commit, manual, remeasure],
  );

  const resetAll = useCallback(() => {
    commit({});
    remeasure();
  }, [commit, remeasure]);

  return {
    widths,
    isCustom: RANK_COLS.some((col) => manual[col] != null),
    dragging,
    beginDrag,
    nudge,
    releaseColumn,
    resetAll,
    remeasure,
  };
}
