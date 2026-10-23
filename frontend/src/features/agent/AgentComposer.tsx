import { useEffect, useMemo, useState } from "react";
import type { V8Data } from "../../app/v8Types";
import { cityNexusApi, type CopilotResponse } from "../../api/citynexus";
import { useLocale, useT, type TripLocale } from "../../i18n/LocaleContext";
import { formatMinorMoney } from "../../lib/money";
import { formatWhen } from "../../lib/formatWhen";
import { NativeMissionTimeline } from "./CopilotDock";
import { classifyReadFailure, copyFor } from "../../lib/failureAttribution";
import type { Attribution } from "../../lib/failureAttribution";
import { dropLegacyDiskCopies, recallTranscript, rememberTranscript } from "../../lib/agentSessionCache";


type CopilotMessage = {
  role: "user" | "assistant";
  text: string;
  response?: CopilotResponse;
};

const intentLabel: Record<string, string> = {
  EXPLAIN_PLAN: "agent.intentExplain",
  WHAT_IF: "agent.intentWhatIf",
  DISCOVER: "agent.intentDiscover",
  PREFERENCE_CHANGE: "agent.intentPreference",
  DISRUPTION_REPORT: "agent.intentDisruption",
  REPLAN_REQUEST: "agent.intentReplan",
  VERIFY_FACT: "agent.intentVerifyFact",
  PERSONAL_ASSISTANCE: "agent.intentPersonalAssistance",
  UNKNOWN: "agent.intentUnknown",
};

// The what-if feasibility value is an internal enum; the traveller reads a
// plain sentence.
function feasibilityLabel(value: string | null | undefined, t: (key: string) => string): string {
  const key = String(value ?? "").toUpperCase();
  if (key === "FEASIBLE" || key === "PASS" || key === "PASSED") {
    return t("hub.feasible");
  }
  if (key === "INFEASIBLE" || key === "FAIL" || key === "FAILED") {
    return t("hub.infeasible");
  }
  if (key.includes("UNKNOWN") || key.includes("NEEDS") || key === "") {
    return t("hub.needsMoreInfo");
  }
  return t("hub.assessed");
}

export function AgentComposer({
  data,
  busy,
  onNavigate,
}: {
  data: V8Data;
  busy: boolean;
  onNavigate: (route: string) => void;
}) {
  const t = useT();
  const { locale } = useLocale();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<CopilotMessage[]>(() => {
    /* Issue #27：这一段以前从 `citynexus.copilot.history.<journeyId>` 播回来，
     * 而那把键只绑行程号 —— 行程是成员共用的，所以同一台手机上换个人就会先看到上一位
     * 的问答与 `agent_run`。现在只认本页内存（见 `lib/agentSessionCache.ts`），
     * 并把这台设备上那份旧副本抹掉。 */
    dropLegacyDiskCopies(data.journey.id);
    return (recallTranscript(data.journey.id) as CopilotMessage[] | null) ?? [];
  });
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /* ORD-0326: what the request actually answered, as the existing channel measured it. */
  const [failureFacts, setFailureFacts] = useState<string | null>(null);
  const localeCode = locale === "zh-CN" ? "zh" : "en";
  const latestNativeRun = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const run = messages[index].response?.agent_run;
      if (run) return run;
    }
    return null;
  }, [messages]);
  useEffect(() => {
    /* 只留内存：面板关掉、路由切走都还在（这本来就是那份缓存存在的理由），
     * 但刷新与换人都不会再把上一位的问答带回来。服务器时间线才是权威。 */
    rememberTranscript(data.journey.id, messages);
  }, [data.journey.id, messages]);
  const suggestions = useMemo(
    () => [t("agent.suggestionExplain"), t("agent.suggestionWhatIf"), t("agent.suggestionDiscover")],
    [t],
  );

  const send = async () => {
    const value = message.trim();
    if (value.length < 2 || sending) return;
    setSending(true);
    setError(null);
    setMessages((current) => [...current, { role: "user", text: value }]);
    setMessage("");
    try {
      const response = await cityNexusApi.sendCopilotMessage(
        data.journey.id,
        value,
        localeCode,
      );
      setMessages((current) => [
        ...current,
        { role: "assistant", text: response.message, response },
      ]);
    } catch (cause) {
      const attribution: Attribution = classifyReadFailure(cause);
      setFailureFacts(attribution.telemetry);
      setError(copyFor(attribution, locale.startsWith("zh")).body ?? t("agent.sendError"));
    } finally {
      setSending(false);
    }
  };

  const actionLabel = (action: string | null | undefined) => {
    if (action === "REQUEST_REPLAN") return t("agent.requestReplan");
    if (action === "REQUEST_PLACE_SEARCH") return t("agent.openDiscovery");
    if (action === "REQUEST_PREFERENCE_UPDATE") return t("agent.openPreferences");
    if (action === "REQUEST_PLAN_EXPLANATION") return t("agent.explainAgain");
    return null;
  };

  const continueAction = (action: string | null | undefined) => {
    if (action === "REQUEST_PLACE_SEARCH") onNavigate("discover");
    if (action === "REQUEST_REPLAN") onNavigate("authoritative");
    if (action === "REQUEST_PREFERENCE_UPDATE") onNavigate("me");
  };

  return (
    <section className="v8-page" data-testid="v15-copilot">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{t("agent.kicker")}</p>
          <h1>{t("agent.title")}</h1>
          <p className="v8-lede">{t("agent.lede")}</p>
        </div>
        <span className="v8-status-pill violet">
          {data.traveler_twin?.learned_soft_dimensions?.length
            ? t("agent.twinActive")
            : t("agent.twinReady")}
        </span>
      </div>

      <div className="v8-agent-composer-card">
        <div className="v8-agent-copy">
          <span className="v8-agent-mark">{t("agent.brand")}</span>
          <h2>{t("agent.whatChange")}</h2>
          <p>{t("agent.whatChangeSub")}</p>
          <p className="v8-agent-reassure">{t("agent.boundarySub")}</p>
        </div>
        <div className="v8-agent-input">
          <label htmlFor="v15-copilot-input">{t("agent.message")}</label>
          <textarea
            id="v15-copilot-input"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={t("agent.inputPlaceholder")}
            data-testid="v15-copilot-input"
            onKeyDown={(event) => {
              // Enter sends, Shift+Enter makes a new line — the behaviour a
              // traveller expects from a chat box.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (!busy && !sending && message.trim().length >= 2) void send();
              }
            }}
          />
          <div className="v8-agent-toolbar">
            <span>
              {data.journey.title}
            </span>
            <button
              className="v8-primary"
              data-testid="v15-copilot-submit"
              disabled={busy || sending || message.trim().length < 2}
              onClick={() => void send()}
            >
              {sending ? t("agent.working") : t("agent.send")}
            </button>
          </div>
          <div className="v15-copilot-suggestions" aria-label={t("agent.suggestions") }>
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                className="v8-outline-button"
                type="button"
                onClick={() => setMessage(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <p className="v8-message error" data-testid="agent-send-error" data-attribution={failureFacts ?? ""}>
          {error}
        </p>
      )}

      <div className="v15-copilot-history" aria-live="polite">
        {messages.map((item, index) => (
          <article
            key={`${item.role}-${index}`}
            className={item.role === "user" ? "v15-copilot-message user" : "v15-copilot-message"}
          >
            <span className="v8-kicker">
              {item.role === "user" ? t("agent.you") : t("agent.citynexus")}
            </span>
            <p>{item.text}</p>
            {item.response && (
              <div className="v15-copilot-evidence">
                <div className="v15-copilot-badges">
                  <span className="v8-status-pill violet" data-testid="v15-intent">
                    {t(intentLabel[item.response.intent.name] ?? "agent.intentUnknown")}
                  </span>
                  <span className="v8-evidence-label" data-testid="v15-mode">
                    {item.response.mode === "AI" ? t("agent.aiBadge") : t("agent.fallbackBadge")}
                  </span>
                </div>
                {item.response.what_if && (
                  <div className="v15-what-if" data-testid="v15-what-if">
                    <div className="v15-what-if-head">
                      <b>{t("agent.whatIfPreview")}</b>
                      <span data-testid="v15-simulation-only">{t("agent.simulationOnly")}</span>
                    </div>
                    <div className="v15-what-if-grid">
                      <div>
                        <span>{t("agent.before")}</span>
                        <b>{formatMetric(item.response.what_if.before, item.response.what_if.before.cost_minor, locale)}</b>
                      </div>
                      <div>
                        <span>{t("agent.after")}</span>
                        <b>{formatMetric(item.response.what_if.after, item.response.what_if.after.cost_minor, locale)}</b>
                      </div>
                      <div>
                        <span>{t("agent.feasibility")}</span>
                        <b>{feasibilityLabel(item.response.what_if.feasibility, t)}</b>
                      </div>
                    </div>
                    <small>
                      {t("agent.protectedCount", {
                        n: item.response.what_if.protected_commitments.count,
                      })}{" "}
                      · {item.response.what_if.protected_commitments.preserved ? t("agent.preserved") : t("agent.notPreserved")}
                    </small>
                  </div>
                )}
                <div className="v15-copilot-action">
                  <span>{item.response.intent.provider === "deepseek" ? t("agent.aiInterpreted") : t("agent.fallbackInterpreted")}</span>
                  {actionLabel(item.response.action?.type) && item.response.action?.type !== "REQUEST_PLAN_EXPLANATION" && (
                    <button
                      className="v8-secondary"
                      type="button"
                      onClick={() => continueAction(item.response?.action?.type)}
                    >
                      {actionLabel(item.response.action?.type)}
                    </button>
                  )}
                </div>
                {item.response.intent.semantic_envelope && (
                  <details className="v15-copilot-semantic" data-testid="v17-semantic-envelope">
                    <summary>{t("agent.advancedDetail")}</summary>
                    <span className="v8-sr-only">{t("agent.semanticBoundary")}</span>
                    <b>
                      {item.response.intent.semantic_envelope.assertion_status}
                      {" · "}
                      {formatWhen(item.response.intent.semantic_envelope.effective_time, {
                        zh: locale.startsWith("zh"),
                        pending: t("inbox.timePending"),
                      })}
                      {" · "}
                      {item.response.intent.semantic_envelope.event_type}
                    </b>
                    <small>{item.response.intent.semantic_envelope.requested_action}</small>
                  </details>
                )}
              </div>
            )}
          </article>
        ))}
      </div>

      {latestNativeRun && (
        <NativeMissionTimeline
          data={data}
          run={latestNativeRun}
          compact
          onNavigate={onNavigate}
        />
      )}

      <div className="v8-agent-progress">
        <span className="v8-kicker">{t("agent.recentUnderstanding")}</span>
        <div>
          <b>{t("agent.whatIfStudio")}</b>
          <span>{t("agent.whatIfStudioSub")}</span>
        </div>
        <div>
          <b>{t("agent.protected")}</b>
          <span>{t("agent.protectedSummary")}</span>
        </div>
      </div>
    </section>
  );
}

function formatMetric(
  record: Record<string, unknown>,
  cost: unknown,
  locale: TripLocale,
) {
  const currency = typeof record.currency === "string" ? record.currency : "CNY";
  const value = typeof cost === "number" ? formatMinorMoney(cost, currency, locale) : "—";
  const walking =
    typeof record.walking_min === "number" ? ` · ${record.walking_min} min walk` : "";
  return value + walking;
}
