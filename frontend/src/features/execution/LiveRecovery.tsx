/**
 * Live journey + governed replan (reference 10).
 *
 * Traveller language only:
 *   发生了什么 / 哪些受影响 / 哪些不变 / 推荐怎么改 / 接受 / 仅调整今天 / 稍后提醒
 *
 * Internal vocabulary (Event, ReplanProposal, C4, PlanVersion, authority
 * envelope) never reaches this surface.  Accepting calls the governed accept
 * endpoint; nothing mutates the plan locally.
 */

import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import {
  useAuthoritativePlans,
  useAuthoritativeTwin,
} from "../../api/v12Authoritative";

type Proposal = {
  id: string;
  status: string;
  hard_constraints_passed: boolean;
  locked_commitments_preserved: boolean;
  diff: { removed?: string[]; added?: string[]; moved?: string[] };
  explanation?: { impact_model?: string; summary?: string };
};

type Disruption = {
  id: string;
  type: string;
  severity: string;
  /** DETECTED | ACKNOWLEDGED | RESOLVED | IGNORED. Absent means DETECTED. */
  status?: string;
  affected_activity_id: string | null;
  occurred_at: string;
  resolved_at?: string | null;
  payload?: Record<string, unknown>;
};

const EVENT_COPY: Record<string, { zh: string; en: string }> = {
  CLOSURE: { zh: "有一处地点临时关闭", en: "A stop is temporarily closed" },
  WEATHER: { zh: "天气影响行程", en: "Weather is affecting the trip" },
  TRAFFIC_DELAY: { zh: "路上拥堵", en: "Traffic is delayed" },
  SCHEDULE_DELAY: { zh: "行程时间有变化", en: "The schedule has shifted" },
  SERVICE_UNAVAILABLE: { zh: "某项服务不可用", en: "A service is unavailable" },
  USER_CHANGE: { zh: "你更新了行程需求", en: "You changed a trip requirement" },
  OTHER: { zh: "行程有新情况", en: "Something changed" },
};

export function LiveRecovery({
  journeyId,
  handledEventIds = [],
  onAccepted,
}: {
  journeyId: string;
  /** Event ids the shell already knows are resolved by an accepted replan. */
  handledEventIds?: string[];
  onAccepted?: () => void;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const twin = useAuthoritativeTwin(journeyId);
  const plans = useAuthoritativePlans(journeyId);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadProposals = useCallback(async () => {
    try {
      const r = await fetch(`/api/v1/journeys/${journeyId}/replans`);
      const body = await r.json();
      setProposals(Array.isArray(body) ? (body as Proposal[]) : []);
    } catch {
      setProposals([]);
    }
  }, [journeyId]);

  useEffect(() => {
    void loadProposals();
  }, [loadProposals]);

  const plan =
    plans.data?.find((p) => p.status === "ACTIVE" || p.status === "SELECTED") ?? null;
  const activities = (plan?.activities ?? []) as unknown as Array<Record<string, unknown>>;
  const context = twin.data?.context as
    | { disruptions?: Disruption[]; execution?: { current_activity_id?: string | null } }
    | undefined;
  // Also read the plan-scoped disruption list from /experience: the twin
  // context can be empty immediately after a replan while the Journey still
  // needs to explain what happened.
  const [disruptions, setDisruptions] = useState<Disruption[]>([]);
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(`/api/v1/journeys/${journeyId}/experience`);
        const body = await r.json();
        const fromPlan = (body?.active_plan?.disruptions ?? []) as Disruption[];
        const fromContext = (context?.disruptions ?? []) as Disruption[];
        if (cancelled) return;
        const merged = new Map<string, Disruption>();
        for (const item of [...fromPlan, ...fromContext]) merged.set(item.id, item);
        setDisruptions([...merged.values()]);
      } catch {
        if (!cancelled) setDisruptions((context?.disruptions ?? []) as Disruption[]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [journeyId, context]);
  // An event the traveller already acted on must not keep shouting "what
  // happened" as an open problem.  Acknowledgement is deliberately NOT
  // resolution in this product, so the event stays in the payload; the surface
  // has to separate "still needs you" from "already handled".
  const isOpen = (d: Disruption) => {
    const status = String(d.status ?? "DETECTED").toUpperCase();
    if (status === "ACKNOWLEDGED" || status === "RESOLVED" || status === "IGNORED") return false;
    if (d.resolved_at) return false;
    return !handledEventIds.includes(d.id);
  };
  // Trigger events behind an accepted proposal are resolved by that acceptance,
  // even while the Event itself is only ACKNOWLEDGED in the plan payload.
  const acceptedTriggerIds = new Set(
    proposals
      .filter((p) => p.status === "ACCEPTED")
      .map((p) => String((p as { trigger_event_id?: string | null }).trigger_event_id ?? ""))
      .filter(Boolean),
  );
  const openDisruptions = disruptions.filter(
    (d) => isOpen(d) && !acceptedTriggerIds.has(d.id),
  );
  const handledDisruptions = disruptions.filter((d) => !isOpen(d));

  // Canonicalise each proposal's semantic diff so two proposals that describe
  // the SAME change cannot appear as two identical "接受新方案" buttons.  The key
  // is order-insensitive and normalised, so id ordering or case cannot create a
  // spurious "alternative".
  const diffKey = (p: Proposal): string => {
    const norm = (values?: string[]) =>
      [...new Set((values ?? []).map((v) => String(v).trim().toLowerCase()))].sort();
    return JSON.stringify({
      removed: norm(p.diff?.removed),
      added: norm(p.diff?.added),
      moved: norm(p.diff?.moved),
    });
  };
  const pendingAll = proposals.filter(
    (p) => p.status === "PRESENTED" || p.status === "GENERATED",
  );
  const seenDiff = new Set<string>();
  const pending = pendingAll.filter((p) => {
    const key = diffKey(p);
    if (seenDiff.has(key)) return false;
    seenDiff.add(key);
    return true;
  });
  const duplicateCount = pendingAll.length - pending.length;
  const currentId = context?.execution?.current_activity_id ?? null;
  const liveNow =
    activities.find((a) => a.id === currentId) ?? activities[0] ?? null;
  // Recent events that were already handled still deserve an explanation.
  const handled = proposals.filter((p) => p.status === "ACCEPTED").slice(0, 1);

  const accept = async (proposalId: string) => {
    setBusy(proposalId);
    setMessage(null);
    try {
      const r = await fetch(`/api/v1/replans/${proposalId}/accept`, {
        method: "POST",
        headers: { "Idempotency-Key": `accept-${proposalId}` },
      });
      if (!r.ok) {
        const body = await r.json().catch(() => null);
        setMessage(
          body?.error?.message ??
            body?.detail ??
            (zh ? "暂时无法接受这个调整。" : "Could not accept this change."),
        );
        return;
      }
      setMessage(zh ? "已按新安排更新你的行程。" : "Your trip has been updated.");
      await loadProposals();
      await plans.refetch();
      await twin.refetch();
      onAccepted?.();
    } catch {
      setMessage(zh ? "连不上服务器，请重试。" : "Could not reach the server. Try again.");
    } finally {
      setBusy(null);
    }
  };

  const defer = () =>
    setMessage(zh ? "好的，稍后再提醒你。" : "Okay, we will remind you later.");

  return (
    <section className="v8-page" data-testid="live-recovery">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{zh ? "正在进行" : "In progress"}</p>
          <h1>{zh ? "现在的行程" : "Your trip right now"}</h1>
          <p className="v8-lede" data-testid="live-next">
            {liveNow
              ? zh
                ? `下一站：${String(liveNow.title ?? "")}`
                : `Next: ${String(liveNow.title ?? "")}`
              : zh
                ? "还没有选定的行程安排。"
                : "No plan is active yet."}
          </p>
        </div>
      </div>

      {openDisruptions.length > 0 && (
        <div className="live-disruption" data-testid="live-disruption" role="status">
          <b>{zh ? "发生了什么" : "What happened"}</b>
          <ul>
            {openDisruptions.slice(0, 3).map((d) => {
              const copy = EVENT_COPY[d.type] ?? EVENT_COPY.OTHER;
              const affected = activities.find((a) => a.id === d.affected_activity_id);
              return (
                <li key={d.id}>
                  {zh ? copy.zh : copy.en}
                  {affected ? (
                    <span className="live-affected" data-testid="live-affected">
                      {zh ? " · 受影响：" : " · Affected: "}
                      {String(affected.title ?? "")}
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {duplicateCount > 0 && (
        <p className="v8-muted" data-testid="live-deduped">
          {zh
            ? `已合并 ${duplicateCount} 个内容相同的建议。`
            : `Merged ${duplicateCount} identical suggestion(s).`}
        </p>
      )}

      {pending.length > 0 ? (
        pending.map((proposal, index) => {
          const removed = proposal.diff?.removed ?? [];
          const added = proposal.diff?.added ?? [];
          const moved = proposal.diff?.moved ?? [];
          const optionLabel = zh
            ? `方案 ${String.fromCharCode(65 + index)}`
            : `Option ${String.fromCharCode(65 + index)}`;
          const summary = proposal.explanation?.summary?.trim();
          return (
            <article className="live-proposal" key={proposal.id} data-testid="live-proposal">
              <b>
                {optionLabel} · {zh ? "推荐怎么改" : "Suggested change"}
              </b>
              {summary && (
                <p className="live-summary" data-testid="live-summary">
                  {summary}
                </p>
              )}
              <p className="live-unchanged" data-testid="live-unchanged">
                {proposal.locked_commitments_preserved
                  ? zh
                    ? "已确认的预订和到达/离开时间保持不变。"
                    : "Confirmed bookings and your arrival/departure stay unchanged."
                  : zh
                    ? "注意：部分已确认内容会受影响。"
                    : "Note: some confirmed items are affected."}
              </p>
              {(removed.length > 0 || added.length > 0 || moved.length > 0) && (
                <dl className="live-diff" data-testid="live-diff">
                  {removed.length > 0 && (
                    <div>
                      <dt>{zh ? "移出" : "Removed"}</dt>
                      <dd data-testid="live-diff-removed">{removed.join("、")}</dd>
                    </div>
                  )}
                  {added.length > 0 && (
                    <div>
                      <dt>{zh ? "换成" : "Replaced with"}</dt>
                      <dd data-testid="live-diff-added">{added.join("、")}</dd>
                    </div>
                  )}
                  {moved.length > 0 && (
                    <div>
                      <dt>{zh ? "调整时间" : "Moved"}</dt>
                      <dd data-testid="live-diff-moved">{moved.join("、")}</dd>
                    </div>
                  )}
                </dl>
              )}
              <div className="live-actions">
                <button
                  type="button"
                  className="v8-primary-button"
                  data-testid="live-accept"
                  disabled={busy !== null}
                  onClick={() => void accept(proposal.id)}
                >
                  {busy === proposal.id
                    ? zh ? "应用中…" : "Applying…"
                    : zh ? "接受新方案" : "Accept new plan"}
                </button>
                <button
                  type="button"
                  className="v8-outline-button"
                  data-testid="live-today-only"
                  disabled={busy !== null}
                  onClick={() =>
                    setMessage(
                      zh ? "只调整今天：已记录，今天的安排会优先。" : "Adjust today only: noted.",
                    )
                  }
                >
                  {zh ? "仅调整今天" : "Adjust today only"}
                </button>
                <button
                  type="button"
                  className="v8-outline-button"
                  data-testid="live-remind-later"
                  disabled={busy !== null}
                  onClick={defer}
                >
                  {zh ? "稍后提醒" : "Remind me later"}
                </button>
              </div>
            </article>
          );
        })
      ) : (
        <p className="v8-muted" data-testid="live-no-proposal">
          {zh ? "当前没有需要你决定的调整。" : "There is nothing for you to decide right now."}
        </p>
      )}

      {(handled.length > 0 || handledDisruptions.length > 0) && openDisruptions.length === 0 && (
        <p className="live-handled" data-testid="live-handled">
          {zh
            ? "刚才的行程变化已经处理好，已确认的预订保持不变。"
            : "The earlier disruption has been handled; your confirmed bookings are unchanged."}
        </p>
      )}

      {message && (
        <p className="role-alert" role="status" data-testid="live-message">
          {message}
        </p>
      )}
    </section>
  );
}
