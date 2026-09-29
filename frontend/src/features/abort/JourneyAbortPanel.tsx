import { useCallback, useMemo, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import {
  ABORT_NOTE_MAX_LENGTH,
  abortJourney,
  abortReceipt,
  abortRefusalType,
  type JourneyAbortCode,
} from "./journeyAbort";
import {
  ABORT_REASON_KEYS,
  ABORT_REFUSAL_KEYS,
  abortCopy,
  fillAbort,
  type JourneyAbortCopyKey,
} from "./journeyAbortCopy";
import "./journeyAbort.css";

/**
 * ORD-0464: the question that stands in front of binning a trip.
 *
 * Two exits, and the difference between them is the whole order. `丢进回收站` sends the ticks
 * (`DECLARED`); `暂不说明，直接丢进回收站` sends `{ answered: false }`, which the server records as
 * `SKIPPED_BY_TRAVELER` -- a real answer the traveller gave. Neither one is what a client that never
 * shows this panel produces, and nothing here can produce that third state on purpose.
 *
 * Both buttons name the action that happens. The reference survey this order was pointed at keeps its
 * final control saying "Continue to delete account" rather than "Submit" (剖析件 §1.7), and that is the
 * one habit worth taking: a traveller who pressed 丢进回收站 and finds the trip in the bin was told the
 * truth by the button.
 */

type Phase =
  | { kind: "idle" }
  | { kind: "sheet" }
  | { kind: "sending" }
  | { kind: "done"; declared: boolean; codes: JourneyAbortCode[] }
  | { kind: "refused"; type: string | null; receipt: string | null }
  | { kind: "failed" };

/** The order the boxes are rendered in. `contracts/openapi.yaml` owns the vocabulary; the gate arm
 *  reads that file and fails if this list and its `JourneyAbortCode` enum stop being the same set. */
const REASON_ORDER = Object.keys(ABORT_REASON_KEYS) as JourneyAbortCode[];

export function JourneyAbortPanel({
  journeyId,
  onNavigate,
}: {
  journeyId: string;
  onNavigate: (route: string) => void;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [picked, setPicked] = useState<JourneyAbortCode[]>([]);
  const [note, setNote] = useState("");

  const say = useCallback(
    (key: JourneyAbortCopyKey, params: Record<string, string | number> = {}) =>
      fillAbort(abortCopy(locale, key), params),
    [locale],
  );

  const send = useCallback(
    async (declared: boolean) => {
      setPhase({ kind: "sending" });
      const codes = picked.filter((code) => code);
      try {
        await abortJourney(
          journeyId,
          declared ? { answered: true, codes, note: note.trim() ? note.trim() : null } : { answered: false },
        );
        setPhase({ kind: "done", declared, codes });
      } catch (cause) {
        const type = abortRefusalType(cause);
        setPhase(
          type ? { kind: "refused", type, receipt: abortReceipt(cause) } : { kind: "failed" },
        );
      }
    },
    [journeyId, note, picked],
  );

  const doneText = useMemo(() => {
    if (phase.kind !== "done") return null;
    if (!phase.declared) return say("abort.doneSkipped");
    return say("abort.doneDeclared", {
      codes: phase.codes.map((code) => say(ABORT_REASON_KEYS[code])).join(zh ? "、" : ", "),
    });
  }, [phase, say, zh]);

  return (
    <section className="journey-abort" data-testid="journey-abort">
      {phase.kind === "idle" && (
        <button
          type="button"
          className="v8-quiet-button"
          data-testid="abort-open"
          onClick={() => setPhase({ kind: "sheet" })}
        >
          {say("abort.open")}
        </button>
      )}

      {(phase.kind === "sheet" || phase.kind === "sending") && (
        <div className="cn-abort-sheet">
          <p className="cn-abort-question" data-testid="abort-question">
            {say("abort.question")}
          </p>
          <p className="v8-muted" data-testid="abort-help">
            {say("abort.help")}
          </p>
          <ul className="cn-abort-codes">
            {REASON_ORDER.map((code) => (
              <li key={code} className="cn-abort-code">
                <label>
                  <input
                    type="checkbox"
                    data-testid="abort-code"
                    data-cnx-code={code}
                    checked={picked.includes(code)}
                    disabled={phase.kind === "sending"}
                    onChange={(event) =>
                      setPicked((current) => {
                        const without = current.filter((item) => item !== code);
                        return event.target.checked ? [...without, code] : without;
                      })
                    }
                  />
                  <span>{say(ABORT_REASON_KEYS[code])}</span>
                </label>
              </li>
            ))}
          </ul>
          <label className="cn-abort-note">
            <span className="v8-muted">{say("abort.noteLabel", { n: ABORT_NOTE_MAX_LENGTH })}</span>
            <textarea
              data-testid="abort-note"
              value={note}
              rows={2}
              maxLength={ABORT_NOTE_MAX_LENGTH}
              disabled={phase.kind === "sending"}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <p className="cn-abort-actions">
            <button
              type="button"
              className="v8-primary-button"
              data-testid="abort-confirm"
              disabled={phase.kind === "sending" || picked.length === 0}
              onClick={() => void send(true)}
            >
              {phase.kind === "sending" ? say("abort.busy") : say("abort.confirm")}
            </button>
            <button
              type="button"
              className="v8-quiet-button"
              data-testid="abort-skip"
              disabled={phase.kind === "sending"}
              onClick={() => void send(false)}
            >
              {say("abort.skip")}
            </button>
          </p>
          {picked.length === 0 && (
            <p className="v8-muted" data-testid="abort-hint">
              {say("abort.pickOne")}
            </p>
          )}
        </div>
      )}

      {phase.kind === "done" && (
        <>
          <p className="cn-abort-done" data-testid="abort-done" role="status">
            {doneText}
          </p>
          <p className="v8-muted" data-testid="abort-find-again">
            {say("abort.findAgain")}{" "}
            <button
              type="button"
              className="v8-quiet-button"
              data-testid="abort-go-trash"
              onClick={() => onNavigate("trash")}
            >
              {say("abort.goTrash")}
            </button>
          </p>
        </>
      )}

      {phase.kind === "refused" && (
        <p className="v8-message" role="alert" data-testid="abort-refused" data-cnx-refusal={phase.type ?? "unnamed"}>
          {phase.type && ABORT_REFUSAL_KEYS[phase.type as keyof typeof ABORT_REFUSAL_KEYS]
            ? say(ABORT_REFUSAL_KEYS[phase.type as keyof typeof ABORT_REFUSAL_KEYS])
            : say("abort.refused")}
          {phase.receipt ? ` ${say("abort.receipt", { receipt: phase.receipt })}` : ""}
        </p>
      )}

      {phase.kind === "failed" && (
        <p className="v8-message" role="alert" data-testid="abort-failed">
          {say("abort.failed")}
        </p>
      )}
    </section>
  );
}
