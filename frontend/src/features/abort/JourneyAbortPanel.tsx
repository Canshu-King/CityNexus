/* ORD-0505: the 中止 panel -- a trip can be stopped, and the record says why.
 *
 * Two rules shape what is on screen:
 *
 * 1. the consequence is stated *before* the tap.  `after` says the trip leaves the live screen and
 *    stays in the list; `back` says this build has no un-abort door, so the step is confirmed as
 *    irreversible.  A traveller who learns either of those only after the write has not been told,
 *    they have been informed of a surprise.
 * 2. the reason a traveller reads afterwards is the one the server holds.  When the trip is already
 *    stopped this panel renders `journeys.cancelled_reason` and `cancelled_at` from the payload it was
 *    given and offers no second write -- so the second tap cannot overwrite the first reason, which
 *    is what the backend's own 409 exists to protect.
 */
import { useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { abortJourney, refusalReasonCode, type AbortRejection } from "./journeyAbort";
import { ABORT_REFUSAL_KEYS, abortCopy, fillAbortCopy } from "./journeyAbortCopy";

type Props = {
  journeyId: string;
  travellerId: string;
  status: string;
  cancelledAt?: string | null;
  cancelledReason?: string | null;
  onChanged?: () => void;
};

export function JourneyAbortPanel({
  journeyId,
  travellerId,
  status,
  cancelledAt,
  cancelledReason,
  onChanged,
}: Props) {
  const { locale } = useLocale();
  const arm = (locale.startsWith("zh") ? "zh" : "en") as "zh" | "en";
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  const stopped = status === "CANCELLED";

  const submit = async () => {
    setBusy(true);
    setOutcome(null);
    setRefused(null);
    try {
      await abortJourney(journeyId, { reason, requestedBy: travellerId });
      setOutcome(abortCopy(arm, "done"));
      onChanged?.();
    } catch (cause) {
      const code = refusalReasonCode(cause);
      const key = code ? ABORT_REFUSAL_KEYS[code] : undefined;
      setRefused(
        key
          ? abortCopy(arm, key)
          : fillAbortCopy(arm, "refusedOther", { code: code ?? "UNKNOWN" }),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="v8-page cn-abort" data-testid="journey-abort-panel">
      <span className="v8-kicker">{abortCopy(arm, "title")}</span>
      <p className="v8-lede" data-testid="journey-abort-after">{abortCopy(arm, "after")}</p>
      <p className="v8-lede" data-testid="journey-abort-back">{abortCopy(arm, "back")}</p>

      {stopped ? (
        <p className="v8-muted" data-testid="journey-abort-stored">
          {cancelledReason
            ? fillAbortCopy(arm, "storedReason", {
                reason: cancelledReason,
                moment: cancelledAt ?? "",
              })
            : abortCopy(arm, "noReasonYet")}
        </p>
      ) : (
        <label>
          {abortCopy(arm, "reasonLabel")}
          <input
            data-testid="journey-abort-reason"
            value={reason}
            placeholder={abortCopy(arm, "reasonHint")}
            onChange={(event) => setReason(event.target.value)}
          />
          <button
            type="button"
            data-testid="journey-abort-submit"
            disabled={busy || reason.trim().length < 3}
            onClick={() => void submit()}
          >
            {abortCopy(arm, "submit")}
          </button>
        </label>
      )}

      {outcome ? <p data-testid="journey-abort-outcome">{outcome}</p> : null}
      {refused ? (
        <p role="alert" data-testid="journey-abort-refused">
          {refused}
        </p>
      ) : null}
    </section>
  );
}

export type { AbortRejection };
