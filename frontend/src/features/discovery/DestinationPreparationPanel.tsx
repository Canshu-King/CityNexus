/**
 * ORD-0193 -- preparing a destination, as a flow the traveller can see on a phone.
 *
 * Every number and every word here comes from the server's own projections:
 *   `GET /destinations/capability` -> { capability, reason_code, recommended_action, coverage,
 *                                       missing_categories, candidates, provider_status? }
 *   `POST/GET /catalog-hydrations` -> { status, phase, outcome, terminal, elapsed_ms, retryable,
 *                                       error{code,message_key,reason_code,message} }
 *
 * Three things this screen is forbidden to do, all measured elsewhere in this project:
 *
 *  1. **Invent a denominator.**  The job record has no `progress` field on purpose (the backend's
 *     docstring says a percentage would be a claim about a queue this process cannot see), so this
 *     screen shows `phase` + `elapsed_ms` and never a bar.  An invented progress step was a defect
 *     here once already.
 *  2. **Say "network unavailable" about a structural state.**  `NO_MATCH`, `AMBIGUOUS` and an
 *     unavailable provider are server-known facts, not connectivity (R14-P, reverse face).  The
 *     copy for those comes from `reason_code`, never from a fetch failure.
 *  3. **Close silently or do nothing.**  Every terminal state ends in a real action -- prepare,
 *     choose another destination, retry, or go and plan -- and the action comes from the server's
 *     `recommended_action` where it exists.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocale, useT } from "../../i18n/LocaleContext";
import { deviceReadout } from "../../lib/failureAttribution";
import { PrepAbandonSurvey } from "./PrepAbandonSurvey";
import { failureSentence, nameTheFailure } from "./prepFailureCopy";
import { STOP_ACTION_KEY, SURVEY_COPY, appendSurveyLog } from "./prepAbandonSurveyCopy";
import {
  cityNexusApi,
  type CatalogHydrationOperation,
  type DestinationCapability,
} from "../../api/citynexus";

type Props = {
  journeyId?: string | null;
  /** Hand the traveller on to planning once the destination is ready. */
  onOpenPlan?: () => void;
  /** ORD-0566: `PREPARE_PLACES` says the place rows themselves need work, so the advice is a door. */
  onOpenPreparePlaces?: () => void;
  initialQuery?: string;
};

/** The server's structural verdicts.  Anything unrecognised is shown as itself, not guessed at. */
const CAPABILITY_READY = "READY";

export function DestinationPreparationPanel({
  journeyId,
  onOpenPlan,
  onOpenPreparePlaces,
  initialQuery = "",
}: Props) {
  const t = useT();
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");

  const queryRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState(initialQuery);
  const [capability, setCapability] = useState<DestinationCapability | null>(null);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [job, setJob] = useState<CatalogHydrationOperation | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [surveyOpen, setSurveyOpen] = useState(false);

  /* A survey belongs to the job it was opened for, so a *new* operation closes it. It does not close
     when the job terminalises underneath: the probe measured the server answering 云和县 ~4 s after
     the sheet opened, and dropping the sheet there would throw away an answer half-written. The stop
     request is idempotent (`POST /catalog-hydrations/{id}/abandon`), so finishing the answer is safe. */
  useEffect(() => {
    setSurveyOpen(false);
  }, [job?.operation_id]);
  const pollTimer = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current !== null) {
      window.clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  /* The job's own record is the only source while it runs.  Polling stops the moment the server
     says `terminal`, so a finished job is never "still working" on screen. */
  const watch = useCallback(
    (operationId: string) => {
      stopPolling();
      const tick = async () => {
        try {
          const row = await cityNexusApi.getCatalogHydration(operationId);
          setJob(row);
          if (!row.terminal) {
            const wait = Math.max(500, Number(row.retry_after_ms || 0) || 1500);
            pollTimer.current = window.setTimeout(() => void tick(), wait);
          }
        } catch (error) {
          /* A read that failed is not a job that failed: name it and keep the last real reading. */
          setActionError(failureSentence("read", nameTheFailure(error), zh));
        }
      };
      void tick();
    },
    [stopPolling, zh],
  );

  useEffect(() => stopPolling, [stopPolling]);

  const check = async () => {
    const wanted = query.trim();
    if (!wanted) return;
    setChecking(true);
    setCapabilityError(null);
    setJob(null);
    setActionError(null);
    stopPolling();
    try {
      setCapability(await cityNexusApi.getDestinationCapability(wanted));
    } catch (error) {
      setCapability(null);
      setCapabilityError(failureSentence("check", nameTheFailure(error), zh));
    } finally {
      setChecking(false);
    }
  };

  const prepare = async () => {
    const wanted = (capability?.query ?? query).trim();
    if (!wanted) return;
    setBusy(true);
    setActionError(null);
    try {
      const started = await cityNexusApi.startCatalogHydration(wanted, { journeyId: journeyId ?? null });
      setJob(started);
      /* `reused` means an identical job already covers this request -- the server says so rather
         than answering 409, so the screen says "already preparing" instead of pretending to start. */
      if (!started.terminal) watch(started.operation_id);
    } catch (error) {
      setActionError(failureSentence("start", nameTheFailure(error), zh));
    } finally {
      setBusy(false);
    }
  };

  const abandon = async (): Promise<boolean> => {
    if (!job) return false;
    setBusy(true);
    setActionError(null);
    try {
      const stopped = await cityNexusApi.abandonCatalogHydration(job.operation_id);
      stopPolling();
      setJob(stopped);
      return true;
    } catch (error) {
      setActionError(failureSentence("stop", nameTheFailure(error), zh));
      return false;
    } finally {
      setBusy(false);
    }
  };

  /* ORD-0440: the survey sits in front of the stop, and the stop is still the stop. The record is
     written after the server answered, because an answer recorded against a stop that never landed
     would be a report about our own widget. */
  const stopAfterSurvey = async (reasons: string[], note: string) => {
    const operationId = job?.operation_id ?? "";
    const stopped = await abandon();
    setSurveyOpen(false);
    if (!operationId) return;
    appendSurveyLog({
      at: new Date().toISOString(),
      operation_id: operationId,
      reasons,
      note,
      note_chars: note.length,
      skipped: reasons.length === 0 && note.trim() === "",
      stopped,
    });
  };

  const reasonCode = capability?.reason_code ?? "";
  const verdict = capability?.capability ?? "";
  const missing = capability?.missing_categories ?? [];
  const candidates = capability?.candidates ?? [];

  /** The verdict in the traveller's words, keyed by the server's own reason code. */
  const verdictCopy = (): { title: string; body: string } => {
    if (!capability) return { title: "", body: "" };
    switch (reasonCode) {
      case "CATALOG_CURRENT":
        return {
          title: t("discovery.thisDestinationIsReady"),
          body: t("prep.current"),
        };
      case "COVERAGE_INCOMPLETE":
        return {
          title: t("discovery.thisDestinationHasNotBeenPrepared"),
          body: t("prep.missing", {
            n: missing.length,
            list: missing.join(zh ? "、" : ", "),
          }),
        };
      case "CATALOG_STALE":
        return {
          title: t("discovery.thisDestinationSFactsHaveAged"),
          body: t("prep.stale"),
        };
      case "DESTINATION_AMBIGUOUS":
        return {
          title: t("discovery.thatNameDoesNotNameOnePlace"),
          body: t("prep.ambiguous", { query: capability.query }),
        };
      case "NO_CANONICAL_IDENTITY":
        return {
          title: t("discovery.thisDestinationCannotBeNamedFromATraceableSource"),
          body: t("prep.unnamed", {
            label: capability.pending_destination_label ?? capability.query,
          }),
        };
      case "PROVIDER_RATE_LIMITED":
      case "PROVIDER_TIMEOUT":
      case "PROVIDER_NETWORK_FAILURE":
      case "PROVIDER_SERVER_ERROR":
      case "CATALOG_PREPARING":
        return {
          title: t("discovery.aProviderCouldNotAnswerThisTime"),
          body: t("prep.providerTransient", { reason: reasonCode }),
        };
      case "DESTINATION_RESOLVER_UNAVAILABLE":
        /* ORD-0203: the fourth cell.  Measured live (resolver on, Photon unreachable):
           capability=NOT_ANSWERED, reason=DESTINATION_RESOLVER_UNAVAILABLE, action=RETRY_LATER,
           retryable=true, provider_status=[{status:"UNREACHABLE", answered:false}].
           R11 froze 「可规划性 ≠ 覆盖完整度」, so this says nobody answered -- NOT that the city
           needs data poured in (that would be a claim about the place) and NOT that it cannot be
           planned (that is the UNAVAILABLE cell's claim, which the server did not make). */
        return {
          title: t("discovery.nobodyAnsweredUs"),
          body: t("prep.notAnswered", { reason: reasonCode }),
        };
      default:
        return {
          title: t("prep.verdictTitle", { verdict }),
          body: t("prep.verdictBody", { reason: reasonCode }),
        };
    }
  };

  /** The job, in the server's vocabulary.  `phase` and `elapsed_ms` -- never a percentage. */
  const jobCopy = (): { title: string; body: string } => {
    if (!job) return { title: "", body: "" };
    if (!job.terminal) {
      const elapsedCell = deviceReadout({ elapsed_ms: job.elapsed_ms }, ["elapsed_ms"]);
      return {
        title: job.reused ? t("prep.reusedTitle") : t("prep.runningTitle"),
        body: t("prep.runningBody", {
          phase: job.phase,
          seconds: Math.round(job.elapsed_ms / 1000),
          elapsed: elapsedCell,
        }),
      };
    }
    switch (String(job.outcome ?? "")) {
      case "CATALOG_PREPARED":
        return {
          title: t("discovery.preparedYouCanGoAndPlan"),
          body: t("prep.prepared"),
        };
      case "ALREADY_CURRENT":
        return {
          title: t("discovery.alreadyCurrentNothingWasChanged"),
          body: t("prep.alreadyCurrent"),
        };
      case "NO_REGISTERED_SOURCE":
        return {
          title: t("discovery.noTraceableSourceForThisDestination"),
          body: t("prep.noSource"),
        };
      case "ABANDONED_BY_TRAVELLER":
        return {
          title: t("discovery.youStoppedThisPreparation"),
          body: t("discovery.theServerRecordedTheStopAndWillNotUseThisRunSResult"),
        };
      case "RESOLVER_RUNTIME_FAILURE":
        return {
          title: t("discovery.theResolverFailedAtRuntime"),
          body: t("prep.runtimeFailure"),
        };
      case "WORKER_LOST":
        return {
          title: t("discovery.thisPreparationWasLostMidRun"),
          body: t("discovery.theServerSaysTheWorkerRunningItDisappearedSoThisAttemptDoesNotCountStartingAgainIsTheRoute"),
        };
      default:
        return {
          title: t("prep.endedTitle", { status: String(job.status) }),
          body: t("prep.endedBody", { outcome: String(job.outcome ?? "—") }),
        };
    }
  };

  /* ORD-0566: the server's own advice for a destination it cannot name.  The cell below this one has
     always offered the reset; what was missing is that when the server *recommends* it, the screen
     treated that advice as having no action at all.  Focusing the field is the part that makes the
     click a route rather than a repaint: the traveller lands on an empty query with the cursor in it. */
  const chooseAnotherDestination = () => {
    stopPolling();
    setCapability(null);
    setJob(null);
    setQuery("");
    setActionError(null);
    queryRef.current?.focus();
  };

  /* ORD-0440 second half: this cell used to print `job.error.message`, i.e. whatever sentence the
     server happened to answer with. The refusal is still said - by the token the server owns
     (`code` / `reason_code` / `message_key`), which chooses a sentence written here. The prose itself
     is dropped, and it does not ride into a `data-*` either: `error_receipt_id` and friends are not
     among the six fields a slot may name. */
  const serverError = job?.error ?? null;
  const serverSentence = serverError
    ? failureSentence("read", nameTheFailure(serverError), zh)
    : "";
  /* The action comes from the server.  `retryable` is the pair the fourth cell is obliged to keep
     (`NOT_ANSWERED => retryable is true and a provider_status exists`), so the retry action reads it
     rather than deciding for itself that retrying is reasonable. */
  const action = capability?.recommended_action ?? "";
  const retryable = Boolean(capability?.retryable);

  /* ORD-0440: once the traveller has asked to stop, the sheet is the screen. With the page intro and
     the verdict still stacked above it, the walk measured the exit at centre y=1145 in a 390x844
     viewport - past the 768 first-screen line and past the viewport itself, which a tap that auto-
     scrolls would never have shown. `review/n3_0440_evidence_r1/walk/walk_zh.json` carries that
     reading; this branch is the fix it asked for.
     The poll is held while the sheet is open: the shell re-measures by ~10 px on every tick
     (`review/ord0440/_shift_source_probe.cjs`, kicker top 93 <-> 103 with a stable 66 px topbar), so a
     row under the finger moved each time the server answered. Stopping the read for the length of one
     answer is ours to do; the header's own re-measure is named in the delivery for its owner. */
  const openSurvey = () => {
    stopPolling();
    setSurveyOpen(true);
  };

  const closeSurvey = () => {
    setSurveyOpen(false);
    if (job && !job.terminal) watch(job.operation_id);
  };

  if (surveyOpen && job) {
    return (
      <section
        className="v8-page"
        data-testid="prep-panel"
        data-job-id={job.operation_id}
        data-focus="stop-survey"
      >
        <p className="v8-kicker" data-testid="prep-survey-context">
          {t("discovery.preparation")} · {job.status}
        </p>
        <PrepAbandonSurvey
          zh={zh}
          operationId={job.operation_id}
          busy={busy}
          onExit={(reasons, note) => void stopAfterSurvey(reasons, note)}
          onBack={closeSurvey}
        />
      </section>
    );
  }

  return (
    <section
      className="v8-page"
      data-testid="prep-panel"
      data-verdict={verdict}
      data-reason={reasonCode}
      data-action={action}
      data-retryable={String(retryable)}
      data-job-id={job?.operation_id ?? ""}
    >
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{t("discovery.prepareADestination")}</p>
          <h1>{t("discovery.firstWhetherThisCityCanBePlanned")}</h1>
          <p className="v8-lede">
            {zh
              ? "输入一个目的地，服务器会告诉我们它现在能规划到什么程度；不能的话，缺什么、下一步是什么，都由服务器说了算。"
              : "Type a destination and the server says how far it can plan it right now; if it cannot, what is missing and what to do next come from the server."}
          </p>
        </div>
      </div>

      <div className="prep-form">
        <label>
          <span>{t("discovery.destination")}</span>
          <input
            ref={queryRef}
            data-testid="prep-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("discovery.eGTianjin")}
          />
        </label>
        <button
          type="button"
          className="v8-primary-button"
          data-testid="prep-check"
          disabled={checking || busy || query.trim().length === 0}
          onClick={() => void check()}
        >
          {checking ? (t("discovery.askingTheServer")) : zh ? "看看能不能规划" : "Check this destination"}
        </button>
      </div>

      {capabilityError && (
        <p className="role-alert" role="alert" data-testid="prep-check-error">
          {capabilityError}
        </p>
      )}

      {capability && (
        <div className="prep-verdict" data-testid="prep-verdict" data-capability={verdict}>
          <span className="v8-kicker">
            {t("discovery.serverVerdict")} · {verdict}
          </span>
          <h2 data-testid="prep-verdict-title">{verdictCopy().title}</h2>
          <p data-testid="prep-verdict-body">{verdictCopy().body}</p>

          {/* What is missing, category by category, from the server's coverage map. */}
          {missing.length > 0 && (
            <ul className="prep-coverage" data-testid="prep-missing">
              {missing.map((key) => (
                <li key={key}>
                  {key} · {String(capability.coverage[key] ?? "")}
                </li>
              ))}
            </ul>
          )}

          {/* An observation exists only if something looked; absence is left absent. */}
          {capability.provider_status && capability.provider_status.length > 0 && (
            <ul className="prep-providers" data-testid="prep-providers">
              {capability.provider_status.map((item, index) => (
                <li key={`${item.provider ?? index}`}>
                  {item.provider ?? t("discovery.providerUnnamed")} · {item.status ?? ""}
                  {item.message ? ` · ${item.message}` : ""}
                </li>
              ))}
            </ul>
          )}

          {candidates.length > 0 && (
            <div className="prep-candidates" data-testid="prep-candidates">
              <b>{t("discovery.theServerSaysTheseAllMatchPickOne")}</b>
              <ul>
                {candidates.map((candidate, index) => (
                  <li key={String(candidate.id ?? index)}>
                    {String(candidate.label ?? candidate.name ?? candidate.id ?? index)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Every verdict ends in a real action.  No silent close, no no-op.  The action is the
              server's `recommended_action`, not a local rule: measured on the fourth cell, the
              server answers RETRY_LATER and the old "anything not READY may prepare" branch offered
              开始准备 for a destination nobody had named -- the exact defect `anywhere_capability.py`
              names in its own comment. */}
          <div className="prep-actions">
            {action === "ACCEPT_PARTIAL_PLAN" ? (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-go-plan"
                onClick={() => onOpenPlan?.()}
                disabled={!onOpenPlan}
              >
                {t("discovery.goAndPlan")}
              </button>
            ) : action === "RETRY_LATER" ? (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-retry-later"
                disabled={checking || !retryable}
                onClick={() => void check()}
              >
                {checking ? (t("discovery.tryingAgain")) : zh ? "稍后重试" : "Try again later"}
              </button>
            ) : action === "START_HYDRATION" ? (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-start"
                disabled={busy || Boolean(job && !job.terminal)}
                onClick={() => void prepare()}
              >
                {busy ? (t("discovery.starting")) : zh ? "开始准备" : "Prepare this destination"}
              </button>
            ) : action === "CHOOSE_ANOTHER_DESTINATION" ? (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-choose-another-primary"
                onClick={chooseAnotherDestination}
              >
                {t("discovery.pickAnotherDestination")}
              </button>
            ) : action === "PREPARE_PLACES" ? (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-prepare-places"
                onClick={() => onOpenPreparePlaces?.()}
                disabled={!onOpenPreparePlaces}
              >
                {t("discovery.preparePlaces")}
              </button>
            ) : null}
            {/* The outline exit below stays for every verdict, including CHOOSE_ANOTHER_DESTINATION:
                the server's advice for a destination it cannot name now has its own arm (ORD-0566),
                and this row remains the always-available way out.  Named so no future action string
                silently inherits "prepare this". */}
            <button
              type="button"
              className="v8-outline-button"
              data-testid="prep-choose-another"
              onClick={() => {
                stopPolling();
                setCapability(null);
                setJob(null);
                setQuery("");
                setActionError(null);
              }}
            >
              {t("discovery.chooseAnotherDestination")}
            </button>
          </div>
        </div>
      )}

      {job && (
        <div
          className={`prep-job ${job.terminal ? "terminal" : "running"}`}
          data-testid="prep-job"
          data-status={job.status}
          data-phase={job.phase}
          data-terminal={job.terminal ? "true" : "false"}
          data-outcome={String(job.outcome ?? "")}
          data-elapsed-ms={Math.round(job.elapsed_ms)}
          role="status"
        >
          <span className="v8-kicker">{t("discovery.preparation2")} · {job.status}</span>
          <h3 data-testid="prep-job-title">{jobCopy().title}</h3>
          <p data-testid="prep-job-body">{jobCopy().body}</p>
          {serverSentence && (
            <p className="prep-server" data-testid="prep-server-message">
              {serverSentence}
            </p>
          )}
          <div className="prep-actions">
            {!job.terminal && !surveyOpen && (
              <button
                type="button"
                className="v8-outline-button"
                data-testid="prep-abandon"
                disabled={busy}
                onClick={openSurvey}
              >
                {zh ? SURVEY_COPY.zh[STOP_ACTION_KEY] : SURVEY_COPY.en[STOP_ACTION_KEY]}
              </button>
            )}
            {job.terminal && job.retryable && (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-retry"
                disabled={busy}
                onClick={() => void prepare()}
              >
                {t("offline.retry")}
              </button>
            )}
            {job.terminal && String(job.outcome ?? "") === "CATALOG_PREPARED" && onOpenPlan && (
              <button
                type="button"
                className="v8-primary-button"
                data-testid="prep-go-plan"
                onClick={() => onOpenPlan()}
              >
                {t("discovery.goAndPlan2")}
              </button>
            )}
            {job.terminal && (
              <button
                type="button"
                className="v8-outline-button"
                data-testid="prep-recheck"
                disabled={busy || checking}
                onClick={() => void check()}
              >
                {t("discovery.checkAgain")}
              </button>
            )}
          </div>
        </div>
      )}

      {actionError && (
        <p className="role-alert" role="alert" data-testid="prep-action-error">
          {actionError}
        </p>
      )}
    </section>
  );
}
