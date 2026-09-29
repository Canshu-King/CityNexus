import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import {
  ABORT_NOTE_MAX_LENGTH,
  abortJourney,
  abortReceipt,
  abortRefusalType,
  readAbortRecord,
  type AbortRecord,
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
 * `SKIPPED_BY_TRAVELER` -- a real answer the traveller gave. Neither is what a client that never shows
 * this panel produces, and nothing here can produce that third state on purpose.
 *
 * Both buttons name the action that happens. The reference survey this order was pointed at keeps its
 * final control saying "Continue to delete account" rather than "Submit" (剖析件 §1.7), and that is the
 * one habit worth taking: a traveller who pressed 丢进回收站 and then found the trip in the bin was
 * told the truth by the button.
 *
 * The "it is in the bin now" sentence is read back from `GET .../outcomes`, not remembered from the
 * press. That is what makes the fourth acceptance cell -- still there after a refresh -- the same code
 * path as the first one, and it is why a row written before this order existed says "no reason was
 * recorded" instead of borrowing the traveller's silence for a question nobody asked.
 */

type Read =
  | { phase: "loading" }
  | { phase: "failed" }
  | { phase: "ready"; record: AbortRecord | null };

type Sheet = { kind: "closed" } | { kind: "open" } | { kind: "sending" } | { kind: "failed" };

/** The order the boxes render in. `contracts/openapi.yaml` owns the vocabulary, and gate arm A1 fails
 *  if this list, the generated client's `JourneyAbortCode` union and the boxes on screen drift apart. */
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
  const [read, setRead] = useState<Read>({ phase: "loading" });
  const [sheet, setSheet] = useState<Sheet>({ kind: "closed" });
  const [picked, setPicked] = useState<JourneyAbortCode[]>([]);
  const [note, setNote] = useState("");
  const [refusal, setRefusal] = useState<{ type: string | null; receipt: string | null } | null>(
    null,
  );

  const say = useCallback(
    (key: JourneyAbortCopyKey, params: Record<string, string | number> = {}) =>
      fillAbort(abortCopy(locale, key), params),
    [locale],
  );

  const load = useCallback(async () => {
    setRead({ phase: "loading" });
    try {
      setRead({ phase: "ready", record: await readAbortRecord(journeyId) });
    } catch {
      /* A read that did not answer is not a trip that was never binned; the two need different
         sentences, and a failed read must never fall through to the trigger. */
      setRead({ phase: "failed" });
    }
  }, [journeyId]);

  useEffect(() => {
    void load();
  }, [load]);

  const send = useCallback(
    async (declared: boolean) => {
      setSheet({ kind: "sending" });
      setRefusal(null);
      const codes = picked.filter((code) => code);
      const trimmed = note.trim();
      try {
        await abortJourney(
          journeyId,
          declared ? { answered: true, codes, note: trimmed ? trimmed : null } : { answered: false },
        );
        setSheet({ kind: "closed" });
        await load();
      } catch (cause) {
        const type = abortRefusalType(cause);
        if (type) {
          /* A named refusal keeps the sheet open: the ticks are still the traveller's, and the next
             tap is theirs to make. Nothing was binned, so nothing here may look binned. */
          setSheet({ kind: "open" });
          setRefusal({ type, receipt: abortReceipt(cause) });
        } else {
          setSheet({ kind: "failed" });
          setRefusal(null);
        }
      }
    },
    [journeyId, load, note, picked],
  );

  if (read.phase === "loading") {
    return (
      <section className="journey-abort" data-testid="journey-abort">
        <p className="v8-muted" data-testid="abort-loading">
          {say("abort.busy")}
        </p>
      </section>
    );
  }

  if (read.phase === "failed") {
    return (
      <section className="journey-abort" data-testid="journey-abort">
        <p className="v8-message" role="alert" data-testid="abort-read-failed">
          {say("abort.failed")}
        </p>
      </section>
    );
  }

  const record = read.record;
  if (record) {
    /** One sentence per state the server actually holds. Written as a switch rather than a ternary
     *  chain because the four arms are four different facts, and the `absent` arm is the one that must
     *  never be folded into "the traveller declined". */
    const binnedLine = (held: AbortRecord): string => {
      switch (held.state) {
        case "DECLARED":
          return say("abort.doneDeclared", {
            codes: held.codes.map((code) => say(ABORT_REASON_KEYS[code])).join(zh ? "、" : ", "),
          });
        case "SKIPPED_BY_TRAVELER":
          return say("abort.doneSkipped");
        case "NOT_ASKED":
          return say("abort.doneNotAsked");
        default:
          return say("abort.doneNoState");
      }
    };
    const text = binnedLine(record);
    return (
      <section className="journey-abort" data-testid="journey-abort">
        <p className="cn-abort-done" data-testid="abort-done" data-cnx-state={record.state} role="status">
          {text}
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
      </section>
    );
  }

  return (
    <section className="journey-abort" data-testid="journey-abort">
      {sheet.kind === "closed" && (
        <button
          type="button"
          className="v8-quiet-button"
          data-testid="abort-open"
          onClick={() => setSheet({ kind: "open" })}
        >
          {say("abort.open")}
        </button>
      )}

      {(sheet.kind === "open" || sheet.kind === "sending") && (
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
                    disabled={sheet.kind === "sending"}
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
              disabled={sheet.kind === "sending"}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <p className="cn-abort-actions">
            <button
              type="button"
              className="v8-primary-button"
              data-testid="abort-confirm"
              disabled={sheet.kind === "sending" || picked.length === 0}
              onClick={() => void send(true)}
            >
              {say("abort.confirm")}
            </button>
            <button
              type="button"
              className="v8-quiet-button"
              data-testid="abort-skip"
              disabled={sheet.kind === "sending"}
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

      {sheet.kind === "failed" && (
        <p className="v8-message" role="alert" data-testid="abort-failed">
          {say("abort.failed")}
        </p>
      )}

      {refusal && (
        <p
          className="v8-message"
          role="alert"
          data-testid="abort-refused"
          data-cnx-refusal={refusal.type ?? "unnamed"}
        >
          {refusal.type && ABORT_REFUSAL_KEYS[refusal.type as keyof typeof ABORT_REFUSAL_KEYS]
            ? say(ABORT_REFUSAL_KEYS[refusal.type as keyof typeof ABORT_REFUSAL_KEYS])
            : say("abort.refused")}
          {refusal.receipt ? ` ${say("abort.receipt", { receipt: refusal.receipt })}` : ""}
        </p>
      )}
    </section>
  );
}
