/* ORD-0476 slice 2 -- the footprint screen.

What is on this screen and where each part comes from:
  - every row is a row the server answered at `GET /api/v1/journeys/{id}/checkins`. Nothing is
    assembled locally: no stamp appears because a tap happened, only because the read returned it;
  - `stamped_at` is the instant the server recorded (the doors take no caller-supplied time --
    `backend/app/main.py:3301`), rendered through `Intl` for the traveller's locale;
  - the target's words are resolved by the server from the row it still holds, and a stamp whose
    activity has left the plan reads back `activity_title: null` -- which is shown as 那一站已不在计划
    rather than as a blank or a substituted name;
  - every sentence is a dictionary key (`t("checkin.…")`). No reason code, status number or server
    message reaches the DOM. The duplicate case in particular is answered with *this* screen's own
    sentence plus a re-read, so the traveller sees the stamp the server kept instead of an overwrite.
*/

import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { readCheckins, stampLabel, type CheckinStamp } from "./checkins";
import "./footprint.css";

type Props = { journeyId: string | null };

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "read"; stamps: CheckinStamp[] }
  | { kind: "failed" };

export function FootprintPanel({ journeyId }: Props) {
  const { locale, t } = useLocale();
  const [state, setState] = useState<State>({ kind: "idle" });
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(async () => {
    if (!journeyId) return;
    setState({ kind: "loading" });
    const answer = await readCheckins(journeyId);
    setState(answer.kind === "read" ? { kind: "read", stamps: answer.stamps } : { kind: "failed" });
  }, [journeyId]);

  useEffect(() => {
    void load();
  }, [load, attempt]);

  const moment = (iso: string) =>
    new Intl.DateTimeFormat(locale, {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));

  const stamps = state.kind === "read" ? state.stamps : [];

  return (
    <section className="cn-footprints" data-testid="footprint-panel">
      <header className="cn-footprints__head">
        <div>
          <p className="cnx-eyebrow">{t("checkin.title")}</p>
          <h2>{t("checkin.scope")}</h2>
        </div>
        <button
          type="button"
          className="cn-footprints__retry"
          onClick={() => setAttempt((n) => n + 1)}
          disabled={!journeyId}
          data-testid="footprint-retry"
        >
          {t("checkin.retry")}
        </button>
      </header>

      {!journeyId ? (
        <p className="cn-footprints__state" data-testid="footprint-no-journey">
          {t("checkin.noJourney")}
        </p>
      ) : state.kind === "loading" || state.kind === "idle" ? (
        <p className="cn-footprints__state">{t("checkin.loading")}</p>
      ) : state.kind === "failed" ? (
        <p className="cn-footprints__state" data-testid="footprint-failed">
          {t("checkin.readFailed")}
        </p>
      ) : stamps.length === 0 ? (
        <p className="cn-footprints__state" data-testid="footprint-empty">
          {t("checkin.empty")}
        </p>
      ) : (
        <ul className="cn-footprints__list">
          {stamps.map((stamp) => (
            <li key={stamp.id} className="cn-footprints__row" data-testid="footprint-row">
              <span className="cn-footprints__when">{moment(stamp.stamped_at)}</span>
              <span className="cn-footprints__what">
                {stampLabel(stamp) ?? t("checkin.targetGone")}
              </span>
              {stamp.note ? (
                <span className="cn-footprints__note">{stamp.note}</span>
              ) : (
                <span className="cn-footprints__note cn-footprints__note--absent">
                  {t("checkin.noteAbsent")}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      <p className="cn-footprints__tally" data-testid="footprint-tally">
        {t("checkin.count", { count: stamps.length })}
      </p>
    </section>
  );
}
