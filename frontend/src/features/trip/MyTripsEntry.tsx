import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { isCredentialRefusal } from "../../i18n/travelerLabels";
import { refusalReasonCode, RejectionWithFacts } from "../../lib/rejectionFacts";
import {
  renewSignedSessionIfShort,
  signedTravelerId,
} from "../../lib/travelerSession";
import { formatV8Date } from "../../lib/v8Formatting";
import { readJourneys, type JourneySummary } from "../access/accessDoors";
import { fillMyTrips, myTripsCopyFor, type MyTripsCopyKey } from "./myTripsCopy";
import "./myTrips.css";

/**
 * Issue #33 Q1 -- the trips this credential already owns.
 *
 * Why it exists: ORD-0687 made the pointer wipe on a refused credential correct, and the shell's
 * own recovery button is labelled 「选一趟行程」/ "Choose a trip" (`failureAttribution.ts`,
 * `choose-journey`) -- but the only thing behind that label was the create wizard.  A person whose
 * session was renewed, or whose pointer was cleared, still had to create a trip to get at the trips
 * they already had.  This entry is the list that makes that label true.
 *
 * What it may claim is bounded by two doors and nothing else:
 *  - `POST /api/v1/travelers/session/refresh` slides a live credential forward.  It takes no
 *    identity parameter, so there is nothing here that can trade a uuid for a session.
 *  - `GET /api/v1/journeys` with that credential answers the trips it speaks for
 *    (`backend/app/main.py`, `list_journeys`).  The rows on screen are that door's answer; a count
 *    is computed from the same array the rows are drawn from.
 *
 * It renders nothing without a signed-in traveller.  On a fresh tab there is no credential to ask
 * with, and a disabled list next to the create form would be a control that cannot work -- the
 * wizard is the honest door in that state.
 */

type Phase =
  | { kind: "reading" }
  | { kind: "ready"; rows: JourneySummary[] }
  | { kind: "ended" }
  | { kind: "failed" };

export function MyTripsEntry({
  onOpen,
  askRefresh,
}: {
  onOpen: (journeyId: string) => void;
  /** The renewal door, injected the way `verifySignedSession` takes its read: this component owns
   *  no fetch wrapper, and a test can drive the renewal branch without a network. */
  askRefresh: (headers: Record<string, string>) => Promise<{ status: number; body: unknown }>;
}) {
  const { locale } = useLocale();
  const say = (key: MyTripsCopyKey, params: Record<string, string | number> = {}) =>
    fillMyTrips(myTripsCopyFor(locale, key), params);

  const [phase, setPhase] = useState<Phase>({ kind: "reading" });
  const [opening, setOpening] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!signedTravelerId()) return;
    setPhase({ kind: "reading" });
    /* Slide the window first: a list read on a credential that dies mid-flight would answer with
       a refusal this screen would have to call a network failure. */
    await renewSignedSessionIfShort(askRefresh);
    try {
      setPhase({ kind: "ready", rows: await readJourneys(null) });
    } catch (cause) {
      const code = refusalReasonCode(cause);
      /* A refusal that names the credential is its own state -- "these are not your trips to list
         any more", not "the list is empty".  Anything else (transport, a 5xx, an unreadable answer)
         says only that the door did not answer. */
      const ended =
        isCredentialRefusal(code) ||
        (cause instanceof RejectionWithFacts && cause.http_status === 401);
      setPhase({ kind: ended ? "ended" : "failed" });
    }
  }, [askRefresh]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!signedTravelerId()) return null;
  const rows = phase.kind === "ready" ? phase.rows : [];

  return (
    <section className="cn-mytrips" data-testid="my-trips" aria-label={say("my.title")}>
      <span className="v8-kicker">{say("my.title")}</span>

      {phase.kind === "reading" && (
        <p className="v8-muted" data-testid="my-trips-loading" role="status">
          {say("my.loading")}
        </p>
      )}
      {phase.kind === "ended" && (
        <p className="v8-muted" data-testid="my-trips-ended" role="status">
          {say("my.expired")}
        </p>
      )}
      {phase.kind === "failed" && (
        <p className="v8-muted" data-testid="my-trips-failed" role="status">
          {say("my.failed")}
        </p>
      )}
      {phase.kind === "ready" && rows.length === 0 && (
        <p className="v8-muted" data-testid="my-trips-empty">
          {say("my.empty")}
        </p>
      )}
      {phase.kind === "ready" && rows.length > 0 && (
        <>
          <p className="v8-muted" data-testid="my-trips-count">
            {say("my.count", { n: rows.length })}
          </p>
          <ul className="cn-mytrips-list" data-testid="my-trips-list">
            {rows.map((row) => (
              <li key={row.id} className="cn-mytrips-row" data-cnx-journey={row.id}>
                <span className="cn-mytrips-name">
                  <b className="cn-mytrips-title">{row.title}</b>
                  {/* 同名是常态（两趟都叫北京之旅），能把它们分开的是服务器自己给的那条时间。
                      屏上写的是这一趟开始的那一刻，不是"出发"——向导那一格问的是抵达。 */}
                  {row.start_at ? (
                    <span className="cn-mytrips-when" data-testid="my-trips-when">
                      {say("my.when", { from: formatV8Date(row.start_at, locale) })}
                    </span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className="v8-quiet-button"
                  data-testid="my-trips-open"
                  disabled={opening === row.id}
                  onClick={() => {
                    setOpening(row.id);
                    onOpen(row.id);
                  }}
                >
                  {opening === row.id ? say("my.opening") : say("my.open")}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {(phase.kind === "failed" || phase.kind === "ended" || phase.kind === "ready") && (
        <button type="button" className="v8-quiet-button" data-testid="my-trips-refresh" onClick={() => void load()}>
          {say("my.refresh")}
        </button>
      )}
    </section>
  );
}
