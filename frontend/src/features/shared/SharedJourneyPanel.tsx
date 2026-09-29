import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { CnxMeasuredFacts } from "../../components/CnxMeasuredFacts";
import { copyFor } from "../../lib/failureAttribution";
import { MapPanel, type MapPanelInput } from "../../components/v8/MapPanel";
import { planSourceLabel } from "../../lib/displayVocabulary";
import { bookingStatusLabel, stopRoleLabel } from "../../i18n/travelerLabels";
import { formatV8Date } from "../../lib/v8Formatting";
import { clock, dayLabel, localDateKey } from "../trip/TripItinerary";
import {
  askSharedJourney,
  sharedStopsOf,
  type SharedScreenRead,
  type SharedStop,
} from "./sharedJourneyDoors";
import "./sharedJourney.css";

/**
 * ORD-0465 -- the screen a person lands on after somebody sends them a share link.
 *
 * Until this file, the link could be sent and had nowhere to open: `GET /api/v1/shared/journeys/{token}`
 * was already on the line and the generated client already carried its shape
 * (`frontend/src/generated/api.ts:488`), but no route read that door, so `/v8/shared/...` bounced to
 * Today and the token was a string with no destination.
 *
 * Four rules this screen is built under, each of which has a defect behind it:
 *
 *  1. Opening it sends one GET. It does not create a traveller, a journey, or a demo scenario. The
 *     shell's own boot read is `GET /journeys/<stored id>/experience`, which writes while it answers
 *     and is the reason this project has a 500 for opening a page; the person arriving here is not the
 *     traveller whose journey that is, and `app/V8Experience.tsx`'s boot now says so before it asks.
 *  2. Every refusal is named by the server's `error.reason_code`, never by something this device
 *     worked out. `sharedJourneyDoors.ts` holds the whole vocabulary and a body that carries no name
 *     lands in `unnamed`, which says "no name was read" rather than picking the nearest sentence.
 *  3. There is no arm that reads "loaded, and here is your empty rectangle". The two ways a
 *     successful read can still have nothing to list are different facts -- no plan was ever selected,
 *     and a plan is selected with no stops in it -- and each gets its own sentence below.
 *  4. Nothing on this screen is a raw store value pretending to be a heading. A stop is the place's
 *     own name, falling back to the plan's title only when the store has no name; the plan's `source`
 *     and `status` go through the shared display tables; and the only instants shown are formatted in
 *     the trip's own timezone. The token itself is never painted -- it is the thing that grants access,
 *     and a screenshot of this page should not hand the trip to whoever receives the screenshot.
 */

/** The arms that name themselves with one dictionary key, and the key each one uses. */
const REFUSAL_KEY: Record<string, string> = {
  token_unknown: "shared.refusedTokenUnknown",
  revoked: "shared.refusedRevoked",
  expired: "shared.refusedExpired",
  expiry_unreadable: "shared.refusedExpiryUnreadable",
  not_link_readable: "shared.refusedNotLinkReadable",
  membership_required: "shared.refusedMembershipRequired",
  not_a_member: "shared.refusedNotAMember",
  journey_gone: "shared.refusedJourneyGone",
  in_recycle_bin: "shared.refusedInRecycleBin",
  unnamed: "shared.refusedUnnamed",
};

/**
 * The map's input, built from what this door actually answered.
 *
 * `legs`, `user_location` and `disruptions` are empty or null because the door sends none of them, and
 * that is a fact about the answer rather than a placeholder: a leg's geometry would need a routing
 * provider this deployment does not have, and the traveller's live position is the one field on this
 * trip that belongs to them and not to whoever holds a link.
 */
function toMapInput(stops: SharedStop[]): MapPanelInput {
  return {
    active_plan: {
      current_activity_id: null,
      activities: stops.map((stop) => ({
        id: stop.id,
        title: stop.place_name || stop.title,
        metadata: {},
        location: {
          state: stop.coordinate.state,
          reason: stop.coordinate.reason ?? null,
          latitude: stop.coordinate.latitude,
          longitude: stop.coordinate.longitude,
          coordinate_system: stop.coordinate.coordinate_system,
          source_coordinate_system: stop.coordinate.source_coordinate_system ?? null,
        },
      })),
      legs: [],
      disruptions: [],
      user_location: null,
    },
    offers: [],
    mobility_facts: [],
  };
}

export function SharedJourneyScreen({ token }: { token: string }) {
  const { locale, t, switchLocale } = useLocale();
  const zh = locale.startsWith("zh");
  const trimmed = token.trim();
  const [read, setRead] = useState<SharedScreenRead>(
    trimmed ? { state: "loading" } : { state: "no_token_in_address" },
  );
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!trimmed) {
      setRead({ state: "no_token_in_address" });
      return;
    }
    let retired = false;
    setRead({ state: "loading" });
    void askSharedJourney(trimmed).then((next) => {
      if (!retired) setRead(next);
    });
    return () => {
      retired = true;
    };
  }, [trimmed, attempt]);

  const readAgain = useCallback(() => setAttempt((n) => n + 1), []);

  const answer = read.state === "ready" ? read.answer : null;
  const stops = answer ? sharedStopsOf(answer) : [];
  const timeZone = answer?.timezone || "UTC";

  /** Grouped by the trip's own calendar day, with the two helpers the traveller's own itinerary uses,
   *  so the same stop falls on the same day on both screens. */
  const days = (() => {
    const buckets = new Map<string, SharedStop[]>();
    for (const stop of [...stops].sort((a, b) => a.start_at.localeCompare(b.start_at))) {
      const key = localDateKey(stop.start_at, timeZone);
      buckets.set(key, [...(buckets.get(key) ?? []), stop]);
    }
    return [...buckets.entries()].map(([key, items], index) => ({
      key,
      label: dayLabel(key, index, locale),
      stops: items,
    }));
  })();

  const refusalKey =
    read.state === "refused" ? REFUSAL_KEY[read.refusal] ?? REFUSAL_KEY.unnamed : null;

  return (
    <div className="cn-shared" data-testid="shared-screen" data-shared-state={read.state}>
      <header className="cn-shared-head">
        <span className="v8-kicker">{t("shared.openedByLink")}</span>
        <button
          type="button"
          className="v8-quiet-button cn-shared-language"
          data-testid="shared-language"
          onClick={switchLocale}
        >
          {t("nav.language")}
        </button>
      </header>

      {read.state === "loading" && (
        <p className="v8-muted" role="status" data-testid="shared-loading">
          {t("shared.loading")}
        </p>
      )}

      {read.state === "no_token_in_address" && (
        <div className="cn-shared-notice" role="alert" data-testid="shared-no-token">
          <b>{t("shared.noTokenTitle")}</b>
          <p>{t("shared.noTokenInAddress")}</p>
          <p className="v8-muted">{t("shared.noTokenWhy")}</p>
        </div>
      )}

      {read.state === "read_failed" && (
        <div className="cn-shared-notice" role="alert" data-testid="shared-read-failed">
          <p>{copyFor(read.attribution, zh).body}</p>
          {read.facts ? (
            <details className="cn-shared-details">
              <summary>{t("agent.advancedDetail")}</summary>
              <CnxMeasuredFacts
                facts={read.facts}
                zh={zh}
                testId="shared-read-failed"
                envelope={null}
              />
            </details>
          ) : null}
          <button
            type="button"
            className="v8-quiet-button"
            data-testid="shared-refresh"
            onClick={readAgain}
          >
            {t("shared.refresh")}
          </button>
        </div>
      )}

      {read.state === "refused" && refusalKey && (
        <div className="cn-shared-notice" role="alert" data-testid="shared-refused"
             data-shared-code={read.reason_code ?? undefined}>
          <b data-testid="shared-refusal-title">{t(refusalKey)}</b>
          {/* The server's own name for what it refused goes here and nowhere else on the face of the
              screen: quotable, and not required reading. */}
          <details className="cn-shared-details">
            <summary>{t("agent.advancedDetail")}</summary>
            <p className="cn-shared-code-label">{t("shared.refusalCodeLabel")}</p>
            <code data-testid="shared-refusal-code">
              {read.reason_code ?? t("shared.refusalCodeNone")}
            </code>
            {read.facts ? (
              <CnxMeasuredFacts facts={read.facts} zh={zh} testId="shared-refused" envelope={null} />
            ) : null}
          </details>
          <button
            type="button"
            className="v8-quiet-button"
            data-testid="shared-refresh"
            onClick={readAgain}
          >
            {t("shared.refresh")}
          </button>
        </div>
      )}

      {answer && (
        <>
          <h1 className="cn-shared-title" data-testid="shared-title">
            {answer.title}
          </h1>
          <p className="v8-muted" data-testid="shared-window">
            {t("shared.window", {
              from: formatV8Date(answer.start_at, locale),
              to: formatV8Date(answer.end_at, locale),
            })}
          </p>

          {answer.plan_state === "NO_ACTIVE_PLAN" && (
            <p className="v8-muted" data-testid="shared-no-plan">
              {t("shared.noPlan")}
            </p>
          )}
          {answer.plan_state === "ACTIVE_PLAN_ROW_MISSING" && (
            <p className="v8-muted" data-testid="shared-plan-row-missing">
              {t("shared.planRowMissing")}
            </p>
          )}

          {answer.plan_state === "ACTIVE_PLAN_PRESENT" && answer.active_plan && (
            <p className="v8-muted" data-testid="shared-plan-line">
              {t("shared.planLine", {
                version: answer.active_plan.version_no,
                source: planSourceLabel(answer.active_plan.source, zh),
                status: bookingStatusLabel(answer.active_plan.status, zh),
              })}
            </p>
          )}

          {answer.plan_state === "ACTIVE_PLAN_PRESENT" && stops.length === 0 && (
            /* Rule 3. This is the arm a screen falls into by accident: the read answered, the plan is
               there, and there is not one stop in it. Saying nothing here would put a heading above an
               empty page. */
            <div className="cn-shared-notice" role="status" data-testid="shared-plan-empty">
              <b>{t("shared.planEmptyTitle")}</b>
              <p>{t("shared.planEmptyBody")}</p>
            </div>
          )}

          {days.length > 0 && (
            <>
              <p className="v8-muted" data-testid="shared-day-count">
                {t("shared.dayCount", { n: days.length })}
              </p>
              {days.map((day) => (
                <section className="cn-shared-day" key={day.key} data-testid="shared-day">
                  <h2 className="cn-shared-day-head">
                    {t("shared.dayHeading", { label: day.label })}
                  </h2>
                  <ul className="cn-shared-stops">
                    {day.stops.map((stop) => (
                      <li className="cn-shared-stop" key={stop.id} data-testid="shared-stop">
                        <b className="cn-shared-stop-name" data-testid="shared-stop-name">
                          {stop.place_name || stop.title || t("shared.stopUnnamed")}
                        </b>
                        <span className="cn-shared-stop-meta" data-testid="shared-stop-meta">
                          {clock(stop.start_at, timeZone)} ·{" "}
                          {stopRoleLabel({ type: stop.activity_type }, zh)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
              <section className="cn-shared-map" data-testid="shared-map">
                <h2 className="cn-shared-map-head">{t("shared.mapHeading")}</h2>
                <MapPanel data={toMapInput(stops)} option={null} />
              </section>
            </>
          )}

          <button
            type="button"
            className="v8-quiet-button"
            data-testid="shared-refresh"
            onClick={readAgain}
          >
            {t("shared.refresh")}
          </button>
        </>
      )}
    </div>
  );
}
