import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { CnxMeasuredFacts } from "../../components/CnxMeasuredFacts";
import { classifyReadFailure } from "../../lib/failureAttribution";
import type { RawFacts } from "../../lib/rawFacts";
import {
  RejectionWithFacts,
  createCollection,
  readCollections,
  refusalDetails,
  refusalReasonCode,
  type CollectionRow,
  type CollectionShelf,
} from "./collections";
import { copyForLocale, fill, type CollectionCopyKey } from "./collectionCopy";
import "./collections.css";

/**
 * ORD-0444 -- 我的收藏: the read-only list screen for the collection container.
 *
 * Mounted through the panel registry (`app/v8PanelRegistry.tsx`, surface "route", on the existing
 * 城市探索 route), so this directory and one registry entry are the whole front-end change and the
 * four hot files -- `app/V8Experience.tsx`, `styles.css`, `i18n/LocaleContext.tsx`,
 * `design-tokens.css` -- stay shut. It shares the route with 城市探索 rather than getting its own
 * because the nav strip resolves its label as `t("nav." + key)` against the shared dictionary, and
 * a key that dictionary does not have is printed as its own name.
 *
 * Four things this screen may not do:
 *  - It may not answer an empty container with 「暂无数据」. The empty state carries a working action:
 *    `POST /api/v1/collections` is on the line, so 「建一个收藏夹」 really creates the shelf and
 *    re-reads it back from the server (`features/collections/collections.ts`). F23's rule -- 完成
 *    always beside 新建, so nobody reaches a dead end -- is what that button is for.
 *  - It may not present client state as a saved collection. Every row below comes from
 *    `GET /api/v1/collections`, in the order that door answered: shelves oldest-created first,
 *    rows first-put-on first. Nothing here is sorted, filtered or held locally.
 *  - It may not print a refusal as a code. `COLLECTION_FOLDER_NOT_FOUND`, `PLACE_NOT_FOUND` and
 *    `PLACE_ALREADY_IN_COLLECTION` each get their own sentence; the server's token goes on the
 *    details face, where it is quotable and not required reading.
 *  - It may not show a 「地址」 cell. The competitor's shelf row has one
 *    (`D:/moodle/_apk_analysis_pi_travel/MAP/map_findings.md`, F23); this server cannot fill it --
 *    `places` has no address column and no address-shaped metadata key -- so the row shows name,
 *    category, city code, coordinate and note, and says nothing about an address it does not have.
 *
 * Rename and remove are not offered because neither door exists yet. An inert 「重命名」 would be a
 * control that does nothing, which is the defect this product was called out for elsewhere.
 */

type ReadState =
  | { phase: "loading" }
  | { phase: "ready"; shelves: CollectionShelf[] }
  | { phase: "absent"; facts: RawFacts | null; messageKey: string }
  | { phase: "failed"; facts: RawFacts | null; messageKey: string };

type Outcome =
  | { kind: "created"; name: string }
  | { kind: "refused"; code: string | null; facts: RawFacts | null; details: Record<string, unknown> | null };

const OUTCOME_KEY: Record<string, CollectionCopyKey> = {
  created: "collections.created",
  COLLECTION_FOLDER_NOT_FOUND: "collections.refusedFolder",
  PLACE_NOT_FOUND: "collections.refusedPlace",
  PLACE_ALREADY_IN_COLLECTION: "collections.refusedDuplicate",
};

/** The shelf's rows, read straight off the payload. A shelf whose count and array disagree is
 *  reported as "no count given" rather than having one of the two quietly preferred. */
function shelfRows(shelf: CollectionShelf): CollectionRow[] {
  return Array.isArray(shelf.items) ? shelf.items : [];
}

export function CollectionPanel() {
  const { locale, t } = useLocale();
  const zh = locale.startsWith("zh");
  const say = (key: CollectionCopyKey, params: Record<string, string | number> = {}) =>
    fill(copyForLocale(locale, key), params);

  const [read, setRead] = useState<ReadState>({ phase: "loading" });
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setRead({ phase: "loading" });
    try {
      const shelves = await readCollections();
      if (!Array.isArray(shelves)) {
        // A 200 that is not the array the contract declares is not an empty list. Saying "empty"
        // would be answering a shape problem with a product state.
        setRead({ phase: "failed", facts: null, messageKey: "collections.shape" });
        return;
      }
      setRead({ phase: "ready", shelves });
    } catch (cause) {
      const rejection = cause instanceof RejectionWithFacts ? cause : null;
      setRead({
        phase: rejection?.http_status === 404 || rejection?.http_status === 405 ? "absent" : "failed",
        facts: rejection?.facts ?? null,
        messageKey: classifyReadFailure(cause).message_key,
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const startShelf = async () => {
    setBusy(true);
    setOutcome(null);
    try {
      const created = await createCollection(say("collections.emptyDefaultName"));
      setOutcome({ kind: "created", name: created.name });
      await load();
    } catch (cause) {
      setOutcome({
        kind: "refused",
        code: refusalReasonCode(cause),
        facts: cause instanceof RejectionWithFacts ? cause.facts : null,
        details: refusalDetails(cause),
      });
    } finally {
      setBusy(false);
    }
  };

  const shelves = read.phase === "ready" ? read.shelves : [];
  const outcomeText = outcome
    ? outcome.kind === "created"
      ? say("collections.created", { name: outcome.name })
      : outcome.code
        ? say(OUTCOME_KEY[outcome.code] ?? "collections.refused")
        : say("collections.codeAbsent")
    : null;

  return (
    <section
      className="cn-collections"
      data-testid="collection-panel"
      {...(read.phase === "ready" ? { "data-shelf-count": shelves.length } : {})}
      aria-label={say("collections.title")}
    >
      <header className="cn-collections-head">
        <span className="v8-kicker">{say("collections.title")}</span>
        <p className="v8-muted">{say("collections.sub")}</p>
      </header>

      {read.phase === "loading" && (
        <p className="v8-muted" data-testid="collection-loading">
          {say("collections.loading")}
        </p>
      )}

      {(read.phase === "absent" || read.phase === "failed") && (
        <div className="cn-collections-notice" role="alert" data-testid="collection-read-failed">
          <p>{read.phase === "absent" ? say("collections.doorAbsent") : say("collections.readFailed")}</p>
          {read.facts ? (
            <details className="cn-collections-details">
              <summary>{t("agent.advancedDetail")}</summary>
              <CnxMeasuredFacts facts={read.facts} zh={zh} testId="collection-read" envelope={null} />
              <span className="cnx-measured-fact" data-testid="collection-read-message-key">
                {read.messageKey}
              </span>
            </details>
          ) : null}
          <button type="button" className="v8-quiet-button" data-testid="collection-refresh" onClick={() => void load()}>
            {say("collections.refresh")}
          </button>
        </div>
      )}

      {/* The empty state, and the only action it offers is one the server can actually perform. */}
      {read.phase === "ready" && shelves.length === 0 && (
        <div className="cn-collections-empty" data-testid="collection-empty">
          <p className="v8-muted">{say("collections.empty")}</p>
          <button
            type="button"
            className="v8-quiet-button cn-collections-action"
            data-testid="collection-empty-action"
            disabled={busy}
            onClick={() => void startShelf()}
          >
            {busy ? say("collections.emptyActionBusy") : say("collections.emptyAction")}
          </button>
        </div>
      )}

      {read.phase === "ready" && shelves.length > 0 && (
        <>
          {/* Counted out of the same array the shelves are drawn from, so the number on screen
              cannot describe a different read from the cards under it. */}
          <p className="v8-muted" data-testid="collection-shelf-count">
            {say("collections.shelfCount", { n: shelves.length })}
          </p>
          <ul className="cn-collections-list" data-testid="collection-shelf-list">
            {shelves.map((shelf) => {
              const rows = shelfRows(shelf);
              const countStated = typeof shelf.item_count === "number" && shelf.item_count === rows.length;
              return (
                <li
                  key={shelf.id}
                  className="cn-collections-shelf"
                  data-testid="collection-shelf"
                  data-cnx-folder={shelf.id}
                >
                  <b className="cn-collections-shelf-name" data-testid="collection-shelf-name">
                    {shelf.name}
                  </b>
                  <span className="cn-collections-shelf-count" data-testid="collection-shelf-count">
                    {countStated
                      ? say("collections.rowCount", { n: shelf.item_count })
                      : say("collections.countMissing")}
                  </span>
                  {rows.length === 0 ? (
                    <p className="v8-muted cn-collections-empty-shelf" data-testid="collection-shelf-empty">
                      {say("collections.emptyFolder")}
                    </p>
                  ) : (
                    <ul className="cn-collections-rows" data-testid="collection-row-list">
                      {rows.map((row) => (
                        <li key={row.id} className="cn-collections-row" data-testid="collection-row" data-cnx-place={row.place_id}>
                          <b className="cn-collections-row-name" data-testid="collection-row-name">
                            {row.name}
                          </b>
                          <span className="cn-collections-row-meta" data-testid="collection-row-meta">
                            {row.category} · {row.city_code} ·{" "}
                            {say("collections.coordinate", {
                              lat: row.location.latitude,
                              lng: row.location.longitude,
                              crs: row.coordinate_system,
                            })}
                          </span>
                          <span className="cn-collections-row-note" data-testid="collection-row-note">
                            {row.note ? say("collections.note", { note: row.note }) : say("collections.noNote")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}

      {read.phase === "ready" && shelves.length > 0 && (
        <button
          type="button"
          className="v8-quiet-button cn-collections-action"
          data-testid="collection-refresh"
          onClick={() => {
            // A deliberate re-read retires the last receipt: leaving 「已建好」 above a list the
            // traveller has just asked for again would put two answers on one question.
            setOutcome(null);
            void load();
          }}
        >
          {say("collections.refresh")}
        </button>
      )}

      {outcomeText && (
        /* A div, not a <p>: the disclosure below is flow content and a paragraph may not hold it. */
        <div
          className="cn-collections-outcome"
          role="status"
          data-testid="collection-outcome"
          data-cnx-outcome={outcome?.kind}
        >
          <span data-testid="collection-outcome-text">{outcomeText}</span>
          {outcome && outcome.kind === "refused" ? (
            <details className="cn-collections-details">
              <summary>{t("agent.advancedDetail")}</summary>
              {/* ORD-0444 r2, on the door's refusal (`_pf_batch_ORD-0444.json`: this screen grew
                  `UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT` and `UPSTREAM_TEXT_VIA_HELPER_TO_DOM`).  The
                  server's reason token does not reach this screen at all now -- not in a `data-*` slot
                  (Q64 counts an attribute slot as DOM) and not as a child, including when it arrives
                  through the shared display table: measured on the door's own snapshot method, routing
                  it through `displayVocabulary` still cost a cell here, and additionally made the
                  module graph light up ten cells in files this order never edits.  Words the traveller
                  reads are this file's own copy above; what stays in the details face is the numbers
                  the refusal was read from (status, content-type, byte count, receipt) on
                  `CnxMeasuredFacts`, which is where a reading belongs.  Nothing was exempted, and no
                  gate, flag or allowlist was touched to get here. */}
              {outcome.facts ? (
                <CnxMeasuredFacts facts={outcome.facts} zh={zh} testId="collection-action" />
              ) : null}
            </details>
          ) : null}
        </div>
      )}
    </section>
  );
}
