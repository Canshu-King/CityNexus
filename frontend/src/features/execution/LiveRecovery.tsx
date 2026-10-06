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
import { cityNexusApi, type JourneyOperatorProjection } from "../../api/citynexus";
import { travelerAuthHeaders } from "../../lib/travelerSession";
import { useLocale, useT } from "../../i18n/LocaleContext";
import {
  isDisruptionAcknowledgedOnly,
  isDisruptionOpen,
} from "../../lib/disruptionState";
import {
  fetchWithWriteDeadline,
  isWriteDeadlineMissed,
  writeDeadlineCopy,
} from "../../lib/writeDeadline";
import {
  useAuthoritativePlans,
  useAuthoritativeTwin,
} from "../../api/v12Authoritative";

type Proposal = {
  id: string;
  status: string;
  recovery_epoch_id?: string | null;
  source_agent_run_id?: string | null;
  hard_constraints_passed: boolean;
  locked_commitments_preserved: boolean;
  diff: { removed?: string[]; added?: string[]; moved?: string[] };
  explanation?: { impact_model?: string; summary?: string };
};

type GuardianPulse = {
  status?: string;
  completed_at?: string | null;
  result?: {
    signals?: { degraded?: boolean };
    context_watch?: { status?: string } | null;
  };
};

type GuardianWatch = {
  enabled?: boolean;
  next_move?: { copy?: string; presence?: { state?: string } } | null;
};

type DepartureReadiness = {
  state?: string;
  target_title?: string | null;
  target_activity_id?: string | null;
  starts_at?: string | null;
  minutes_until_start?: number | null;
  must_leave_by?: string | null;
  launch_origin?: { source?: string | null; name?: string | null } | null;
  recommended_action?: string;
  departure_activation?: {
    state?: string;
    activity_id?: string | null;
    target_title?: string | null;
    must_leave_by?: string | null;
    minutes_to_leave?: number | null;
    readiness_state?: string;
    can_confirm_departure?: boolean;
    recommended_action?: string;
  } | null;
};

type LaunchSetup = {
  status?: string;
  current_origin?: { name?: string | null } | null;
  candidates?: Array<{ kind?: string; display_name?: string; eligible?: boolean }>;
  actions?: string[];
  contract?: { display_name?: string | null } | null;
};

type RouteOperation = {
  operation_id?: string;
  status?: string;
  outcome?: string | null;
  terminal?: boolean;
  result?: { duration_min?: number | null; mobility_fact_id?: string | null } | null;
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

/**
 * Translate an internal replan refusal into traveller language.
 *
 * `MOBILITY_DATA_UNAVAILABLE` means the engine could not establish how long a
 * new leg takes.  That is not the same finding as "no replacement place
 * exists", so it must not be shown as such (T2 /
 * docs/MOBILITY_TRUTH_CONTRACT.md).  Raw internal codes never reach the
 * traveller; only the Advanced details may retain them.
 */
export function humanReplanReason(raw: string, zh: boolean): string {
  const code = String(raw ?? "");
  if (code.includes("MOBILITY_DATA_UNAVAILABLE")) {
    return zh
      ? "暂时无法获取这段路线的可靠通行时间，因此没有自动修改你的行程。你可以稍后重试，或手动选择替代地点。"
      : "We could not get a reliable travel time for this leg, so your trip was not changed automatically. You can retry later or pick a replacement place yourself.";
  }
  if (code.includes("REPLAN_NO_ALTERNATIVE")) {
    return zh
      ? "附近没有可以替换这处行程的合适地点。"
      : "No suitable replacement place was found for this stop.";
  }
  if (code.includes("REPLAN_TARGET_UNRESOLVED")) {
    return zh
      ? "没能确定这次变化影响的是哪一段行程。"
      : "We could not tell which stop this change affects.";
  }
  if (code.includes("REPLAN_PROTECTED_CONFLICT")) {
    return zh
      ? "这一段属于你已确认不能动的安排，需要你手动处理。"
      : "This stop is part of a protected commitment, so it needs your decision.";
  }
  // Unknown / unmapped reason: never surface the raw internal string.
  return zh
    ? "暂时无法自动调整这段行程，请稍后重试或手动处理。"
    : "We couldn't adjust this part of your trip automatically. Please retry later or handle it manually.";
}

export function LiveRecovery({
  journeyId,
  journeyStatus,
  handledEventIds = [],
  onAccepted,
}: {
  journeyId: string;
  journeyStatus?: string | null;
  /** Event ids the shell already knows are resolved by an accepted replan. */
  handledEventIds?: string[];
  onAccepted?: () => void;
}) {
  const { locale } = useLocale();
  const t = useT();
  const zh = locale.startsWith("zh");
  const twin = useAuthoritativeTwin(journeyId);
  const plans = useAuthoritativePlans(journeyId);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [guardianPulse, setGuardianPulse] = useState<GuardianPulse | null>(null);
  const [guardianWatch, setGuardianWatch] = useState<GuardianWatch | null>(null);
  const [departureReadiness, setDepartureReadiness] = useState<DepartureReadiness | null>(null);
  const [launchSetup, setLaunchSetup] = useState<LaunchSetup | null>(null);
  const [routeOperation, setRouteOperation] = useState<RouteOperation | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [operator, setOperator] = useState<JourneyOperatorProjection | null>(null);

  const loadOperator = useCallback(async () => {
    try {
      setOperator(await cityNexusApi.getJourneyOperator(journeyId));
    } catch {
      setOperator(null);
    }
  }, [journeyId]);

  useEffect(() => {
    void loadOperator();
  }, [loadOperator]);

  const startOperator = useCallback(async () => {
    setBusy("operator-start");
    setMessage(null);
    try {
      const next = await cityNexusApi.startJourneyOperator(journeyId);
      setOperator(next);
      setMessage(zh ? "CityNexus 会照看这趟行程。" : "CityNexus is now taking care of this trip.");
    } catch {
      setMessage(zh ? "暂时无法开启行程托管。" : "We couldn't start trip care yet.");
    } finally {
      setBusy(null);
    }
  }, [journeyId, zh]);

  const approveOperatorChange = useCallback(async () => {
    const approvalId = operator?.approval?.approval_id;
    if (!approvalId) return;
    setBusy("operator-approve");
    setMessage(null);
    try {
      await cityNexusApi.approveJourneyOperatorChange(journeyId, approvalId);
      await loadOperator();
      await plans.refetch();
      await twin.refetch();
      setMessage(zh ? "变更已应用，CityNexus 会继续照看行程。" : "Change applied. CityNexus is watching your trip again.");
      onAccepted?.();
    } catch {
      setMessage(zh ? "这项变更暂时无法批准。" : "We couldn't approve that change yet.");
    } finally {
      setBusy(null);
    }
  }, [journeyId, loadOperator, onAccepted, operator, plans, twin, zh]);

  const rejectOperatorChange = useCallback(async () => {
    const approvalId = operator?.approval?.approval_id;
    if (!approvalId) return;
    setBusy("operator-reject");
    setMessage(null);
    try {
      await cityNexusApi.rejectJourneyOperatorChange(journeyId, approvalId);
      await loadOperator();
      setMessage(zh ? "保留当前行程，CityNexus 会继续照看。" : "Keeping the current plan. CityNexus will keep watching.");
    } catch {
      setMessage(zh ? "暂时无法保留当前行程。" : "We couldn't keep the current plan yet.");
    } finally {
      setBusy(null);
    }
  }, [journeyId, loadOperator, operator, zh]);

  const answerCollectiveOption = useCallback(async (proposalId: string | null) => {
    const collective = operator?.collective;
    if (!collective?.mission_id || !collective.clarification_id || !collective.viewer_member_id || !proposalId) return;
    setBusy("collective-answer");
    setMessage(null);
    try {
      await cityNexusApi.answerCollectiveClarification(
        journeyId,
        collective.mission_id,
        collective.viewer_member_id,
        collective.clarification_id,
        proposalId,
      );
      await loadOperator();
      setMessage(zh ? "已记录你的选择，正在等待其他成员。" : "Your choice is recorded. Waiting for the other travellers.");
    } catch {
      setMessage(zh ? "这次选择已过期或暂时无法提交。" : "That choice is stale or could not be submitted yet.");
    } finally {
      setBusy(null);
    }
  }, [journeyId, loadOperator, operator, zh]);

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

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch(`/api/v1/journeys/${journeyId}/guardian/pulse/latest`);
        if (!response.ok) return;
        const body = await response.json();
        if (!cancelled) setGuardianPulse((body?.pulse ?? null) as GuardianPulse | null);
      } catch {
        if (!cancelled) setGuardianPulse(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [journeyId]);

  const loadLaunchSetup = useCallback(async () => {
    try {
      const response = await fetch(`/api/v1/journeys/${journeyId}/launch-setup`);
      if (!response.ok) return;
      setLaunchSetup((await response.json()) as LaunchSetup);
    } catch {
      setLaunchSetup(null);
    }
  }, [journeyId]);

  useEffect(() => {
    void loadLaunchSetup();
  }, [loadLaunchSetup]);

  const confirmLaunchSource = useCallback(async (sourceKind: "SELECTED_STAY" | "ARRIVAL_ANCHOR") => {
    setBusy(`launch:${sourceKind}`);
    try {
      const response = await fetch(`/api/v1/journeys/${journeyId}/launch-origin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_kind: sourceKind }),
      });
      if (!response.ok) throw new Error("launch origin unavailable");
      await loadLaunchSetup();
      const readiness = await fetch(`/api/v1/journeys/${journeyId}/guardian/readiness`);
      if (readiness.ok) setDepartureReadiness((await readiness.json()) as DepartureReadiness);
    } catch {
      setMessage(zh ? "暂时无法保存出发点。" : "We couldn't save that starting point yet.");
    } finally {
      setBusy(null);
    }
  }, [journeyId, loadLaunchSetup, zh]);

  const checkRoute = useCallback(async () => {
    setBusy("route");
    try {
      const response = await fetch(`/api/v1/journeys/${journeyId}/routes/acquire`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requested_mode: "WALK" }),
      });
      if (!response.ok) throw new Error("route unavailable");
      const body = (await response.json()) as RouteOperation;
      setRouteOperation(body);
      const readiness = await fetch(`/api/v1/journeys/${journeyId}/guardian/readiness`);
      if (readiness.ok) setDepartureReadiness((await readiness.json()) as DepartureReadiness);
    } catch {
      setMessage(zh ? "暂时无法检查这段路线。" : "We couldn't check that route yet.");
    } finally {
      setBusy(null);
    }
  }, [journeyId, zh]);

  const confirmDeparture = useCallback(async () => {
    const activation = departureReadiness?.departure_activation;
    const activityId = activation?.activity_id ?? departureReadiness?.target_activity_id;
    if (!activityId || activation?.can_confirm_departure !== true || activation.state === "BLOCKED") {
      setMessage(zh ? "现在还不能确认出发，请先检查行程提示。" : "You cannot confirm departure yet. Check the trip guidance first.");
      return;
    }
    setBusy("departure");
    setMessage(null);
    try {
      const response = await fetchWithWriteDeadline(
        `/api/v1/journeys/${journeyId}/activities/${activityId}/depart`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...travelerAuthHeaders() },
          body: JSON.stringify({
            truth_kind: "OPERATOR_CONFIRMED_EXECUTION",
            operator_confirmed: true,
          }),
        },
      );
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          setMessage(zh ? "请先登录后确认出发。" : "Please sign in before confirming departure.");
        } else {
          setMessage(zh ? "暂时无法确认出发。" : "We couldn't confirm departure yet.");
        }
        return;
      }
      setMessage(zh ? "已记录，你正在前往下一站。" : "Got it — you’re on the way to the next stop.");
      const readiness = await fetch(`/api/v1/journeys/${journeyId}/guardian/readiness`);
      if (readiness.ok) setDepartureReadiness((await readiness.json()) as DepartureReadiness);
      await twin.refetch();
      await plans.refetch();
    } catch (error) {
      setMessage(isWriteDeadlineMissed(error) ? writeDeadlineCopy(zh).body : (zh ? "暂时无法确认出发。" : "We couldn't confirm departure yet."));
    } finally {
      setBusy(null);
    }
  }, [departureReadiness, journeyId, plans, twin, zh]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch(`/api/v1/journeys/${journeyId}/guardian/autopilot/status`);
        if (!response.ok) return;
        const body = await response.json();
        if (!cancelled) {
          setGuardianWatch(
            body?.enrollment?.enabled
              ? ({ enabled: true, next_move: body?.watch?.next_move ?? null } as GuardianWatch)
              : null,
          );
          setDepartureReadiness(body?.readiness ?? null);
        }
      } catch {
        if (!cancelled) setGuardianWatch(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [journeyId]);

  const plan =
    plans.data?.find((p) => p.status === "ACTIVE" || p.status === "SELECTED") ?? null;
  const journeyCompleted =
    String(journeyStatus ?? twin.data?.context?.journey_status ?? "").toUpperCase() ===
    "COMPLETED";
  const activities = (plan?.activities ?? []) as unknown as Array<Record<string, unknown>>;
  // The projection this card reads is the shared execution truth, whose keys are
  // now_activity_id / next_activity_id / cursor_status / persisted_cursor.  It used to
  // reach for `current_activity_id`, a key that dict does not contain (the *twin* has
  // one at its top level; `execution` does not), so `currentId` was permanently null and
  // the `?? activities[0]` below made the first stop the traveller's Now no matter how
  // far the journey had advanced — CX-SOL-001's failure class in a second consumer.
  const context = twin.data?.context as
    | {
        disruptions?: Disruption[];
        execution?: {
          now_activity_id?: string | null;
          cursor_status?: string | null;
          persisted_cursor?: string | null;
        };
      }
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
  // resolution in this product: `ACKNOWLEDGED` means the traveller has seen
  // the disruption, not that a recovery was chosen.  Only RESOLVED, IGNORED,
  // or an ACCEPTED replan explicitly linked to this event closes it
  // (T3 / docs/ACK_RESOLUTION_CONTRACT.md).  The rule lives in one shared
  // module so Today and Live cannot disagree about the same event.
  const acceptedTriggerIds: Set<string> = new Set(
    proposals
      .filter((p) => p.status === "ACCEPTED")
      .map((p) => String((p as { trigger_event_id?: string | null }).trigger_event_id ?? ""))
      .filter(Boolean),
  );
  const leaveByDisplay = departureReadiness?.must_leave_by
    ? new Date(departureReadiness.must_leave_by).toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;
  const openDisruptions = disruptions.filter((d) => isDisruptionOpen(d, acceptedTriggerIds));
  const handledDisruptions = disruptions.filter((d) => !isDisruptionOpen(d, acceptedTriggerIds));
  // Acknowledged-but-unresolved events get their own copy: the traveller has
  // seen them, but they still need a decision.
  const acknowledgedOnly = disruptions.filter((d) =>
    isDisruptionAcknowledgedOnly(d, acceptedTriggerIds),
  );

  const contextStatus = String(guardianPulse?.result?.context_watch?.status ?? "");
  const pulseDegraded = Boolean(guardianPulse?.result?.signals?.degraded);
  const guardianSurfaceState = guardianPulse
    ? contextStatus === "MATERIAL_CONFLICT" || openDisruptions.length > 0
      ? "recovery"
      : pulseDegraded || ["UNKNOWN", "PROVIDER_DEGRADED"].includes(contextStatus) || guardianPulse.status !== "COMPLETED"
        ? "incomplete"
        : "clear"
    : null;

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
  // A completed Journey has no executable cursor.  Older databases can still
  // contain PRESENTED rows from before the server retired them at completion;
  // keep those rows available to history APIs, but never render them as an
  // actionable or advisory recovery card on the completed surface.
  const pendingAll = journeyCompleted
    ? []
    : proposals.filter((p) => p.status === "PRESENTED" || p.status === "GENERATED");
  const seenDiff = new Set<string>();
  const pending = pendingAll.filter((p) => {
    const key = diffKey(p);
    if (seenDiff.has(key)) return false;
    seenDiff.add(key);
    return true;
  });
  const duplicateCount = pendingAll.length - pending.length;
  const cursorStatus = context?.execution?.cursor_status ?? null;
  const nowId = context?.execution?.now_activity_id ?? null;
  // No list position is ever a substitute for a resolved Now: an id that the plan
  // cannot honour yields null, and the render below says so instead of pointing at
  // whatever happens to be first.
  const liveNow = nowId ? (activities.find((a) => a.id === nowId) ?? null) : null;
  // Recent events that were already handled still deserve an explanation.
  const handled = proposals.filter((p) => p.status === "ACCEPTED").slice(0, 1);

  const accept = async (proposalId: string) => {
    setBusy(proposalId);
    setMessage(null);
    try {
      const r = await fetchWithWriteDeadline(`/api/v1/replans/${proposalId}/accept`, {
        method: "POST",
        headers: { "Idempotency-Key": `accept-${proposalId}` },
      });
      if (!r.ok) {
        const body = await r.json().catch(() => null);
        const raw =
          body?.error?.message ??
          body?.detail ??
          t("live.acceptFailed");
        setMessage(humanReplanReason(raw, zh));
        return;
      }
      setMessage(zh ? "已按新安排更新你的行程。" : "Your trip has been updated.");
      await loadProposals();
      await plans.refetch();
      await twin.refetch();
      onAccepted?.();
    } catch (error) {
      /* ORD-0281 T-b: this device's bound expiring is its own fact.  It used to be reported as
         「连不上服务器」, which blamed the network for a request the server may still be finishing --
         the same attribution mistake ORD-0280 closed for the label, in another panel. */
      if (isWriteDeadlineMissed(error)) {
        const copy = writeDeadlineCopy(zh);
        setMessage(`${copy.title}｜${copy.body}`);
      } else {
        setMessage(zh ? "连不上服务器，请重试。" : "Could not reach the server. Try again.");
      }
    } finally {
      setBusy(null);
    }
  };

  const defer = () =>
    setMessage(zh ? "好的，稍后再提醒你。" : "Okay, we will remind you later.");

  const flow = operator?.flow ?? null;
  const advanceFlow = async (transition: "depart" | "arrive" | "begin" | "complete") => {
    const activityId = flow?.current?.id;
    if (!activityId || !flow?.can_confirm || busy !== null) return;
    setBusy(`flow:${transition}`);
    setMessage(null);
    try {
      await cityNexusApi.transitionActivity(journeyId, activityId, transition);
      await Promise.all([loadOperator(), twin.refetch(), plans.refetch()]);
      setMessage(zh ? "已更新行程进度。" : "Trip progress updated.");
    } catch {
      setMessage(zh ? "请先登录后确认这一步。" : "Please sign in before confirming this step.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="v8-page" data-testid="live-recovery">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">
            {journeyCompleted
              ? zh
                ? "已完成"
                : "Completed"
              : zh
                ? "正在进行"
                : "In progress"}
          </p>
          <h1>
            {journeyCompleted
              ? t("live.completedTitle")
              : zh
                ? "现在的行程"
                : "Your trip right now"}
          </h1>
          <p
            className="v8-lede"
            data-testid="live-next"
            data-cursor-status={cursorStatus ?? "UNKNOWN"}
            data-now-activity-id={String(liveNow?.id ?? "")}
          >
            {journeyCompleted
              ? t("live.completedAdvisory")
              : liveNow
                  ? zh
                    ? `下一站：${String(liveNow.title ?? "")}`
                    : `Next: ${String(liveNow.title ?? "")}`
                  : !plan
                    ? t("live.awaitingPlan")
                    : cursorStatus === "STALE"
                      ? t("live.unresolvedStep")
                      : t("live.nothingDue")}
          </p>
        </div>
      </div>

      <section className="journey-operator-card" data-testid="journey-operator" aria-live="polite">
        <div className="journey-operator-heading">
          <p className="v8-kicker">Journey Operator</p>
          <strong>{operator?.headline ?? (zh ? "把这趟行程交给 CityNexus" : "Let CityNexus take care of this trip")}</strong>
        </div>
        {flow && (
          <div className={`journey-continuous-flow journey-flow-${flow.state.toLowerCase()}`} data-testid="journey-continuous-flow">
            <span className="v8-kicker">{zh ? "今天的行程" : "Today’s journey"}</span>
            <strong data-testid="journey-flow-state">
              {flow.state === "DAY_COMPLETE" ? (zh ? "今天的行程完成了。" : "Your journey is complete.")
                : flow.state === "NEEDS_ATTENTION" ? (zh ? "下一步需要你的注意。" : "The next step needs your attention.")
                : flow.current ? (zh ? `现在：${flow.current.title}` : `Now: ${flow.current.title}`)
                : (zh ? "正在准备下一步。" : "Preparing the next step.")}
            </strong>
            {flow.next && flow.state !== "DAY_COMPLETE" && (
              <span>{zh ? `接下来：${flow.next.title}` : `Next: ${flow.next.title}`}</span>
            )}
            {flow.route?.exact && flow.route.duration_min != null ? (
              <small>{zh ? `已找到准确路线 · 约 ${flow.route.duration_min} 分钟` : `Exact route found · about ${flow.route.duration_min} min`}</small>
            ) : flow.current && ["PREPARING_TO_LEAVE", "NEXT_STOP_PREPARING", "BETWEEN_STOPS"].includes(flow.state) ? (
              <>
                <small>{zh ? "路线还需要检查。" : "The route still needs checking."}</small>
                <button type="button" disabled={busy !== null} onClick={() => void checkRoute()}>{zh ? "检查路线" : "Check route"}</button>
              </>
            ) : null}
            {flow.state === "DAY_COMPLETE" ? null : flow.state === "ARRIVAL_READY" ? (
              <button type="button" disabled={busy !== null} onClick={() => void advanceFlow("arrive")}>{zh ? "我到了" : "I’m here"}</button>
            ) : flow.state === "READY_TO_BEGIN" ? (
              <button type="button" disabled={busy !== null} onClick={() => void advanceFlow("begin")}>{zh ? "开始" : "Start"}</button>
            ) : flow.state === "READY_TO_COMPLETE" || flow.state === "IN_ACTIVITY" ? (
              <button type="button" disabled={busy !== null} onClick={() => void advanceFlow("complete")}>{zh ? "完成这站" : "Done"}</button>
            ) : flow.state === "LEAVE_NOW" || flow.state === "PREPARING_TO_LEAVE" ? (
              <button type="button" disabled={busy !== null} onClick={() => void advanceFlow("depart")}>{zh ? "我出发了" : "I’m leaving"}</button>
            ) : null}
          </div>
        )}
        {operator?.ahead && (
          <div className={`journey-ahead journey-ahead-${operator.ahead.state.toLowerCase()}`} data-testid="journey-ahead" aria-live="polite">
            <span className="v8-kicker">{zh ? "同时看着后面的行程" : "Looking ahead"}</span>
            <strong>{operator.ahead.headline}</strong>
            <small>
              {zh
                ? `未来 ${operator.ahead.horizon.remaining_activity_count} 个行程点 · 看到 ${new Date(operator.ahead.horizon.lookahead_until).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}`
                : `${operator.ahead.horizon.remaining_activity_count} future stops · looking through ${new Date(operator.ahead.horizon.lookahead_until).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}`}
            </small>
            {operator.ahead.top_risk && (
              <span data-testid="journey-ahead-risk">
                {zh
                  ? `${operator.ahead.top_risk.title ?? "后续行程"} · ${operator.ahead.top_risk.lead_time_minutes ?? ""} 分钟后${operator.ahead.top_risk.grounded ? " · 有依据的预测" : " · 继续观察"}`
                  : `${operator.ahead.top_risk.title ?? "Later stop"} · in ${operator.ahead.top_risk.lead_time_minutes ?? ""} min${operator.ahead.top_risk.grounded ? " · grounded forecast" : " · watching"}`}
              </span>
            )}
          </div>
        )}
        {operator?.overnight && operator.overnight.state !== "INACTIVE" && (
          <div className={`journey-overnight journey-overnight-${operator.overnight.state.toLowerCase()}`} data-testid="journey-overnight">
            <span className="v8-kicker">{zh ? "今晚我继续照看行程" : "I’ll keep looking after your trip overnight"}</span>
            <strong>
              {operator.overnight.state === "MORNING_READY"
                ? (zh ? "早上好，你今天的行程已准备好。" : "Good morning — today’s trip is prepared.")
                : operator.overnight.state === "MORNING_NEEDS_ATTENTION"
                  ? (zh ? "明天的第一站已准备好，出发路线还需要确认。" : "Your first stop is ready, but I still need a reliable route before I can tell you when to leave.")
                  : (zh ? "我会继续照看明天的安排。" : "I’m watching tomorrow’s plan while you rest.")}
            </strong>
            {operator.overnight.learning_summary?.summary && (
              <small data-testid="journey-overnight-learning">{operator.overnight.learning_summary.summary}</small>
            )}
            {operator.overnight.briefing?.first_activities?.slice(0, 3).map((item, index) => (
              <span key={item.id}>{index === 0 ? (zh ? `第一站：${item.title}` : `First stop: ${item.title}`) : (zh ? `之后：${item.title}` : `Then: ${item.title}`)}</span>
            ))}
            {operator.overnight.briefing?.route?.exact && operator.overnight.briefing.route.must_leave_by && (
              <small>{zh ? `建议 ${new Date(operator.overnight.briefing.route.must_leave_by).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })} 出发 · ${operator.overnight.briefing.route.duration_min} 分钟路线` : `Leave around ${new Date(operator.overnight.briefing.route.must_leave_by).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })} · ${operator.overnight.briefing.route.duration_min} min route`}</small>
            )}
            {operator.overnight.briefing?.future_risk && (
              <small>{zh ? `留意后续行程：${operator.overnight.briefing.future_risk.title ?? "有依据的风险"}` : `One thing to watch: ${operator.overnight.briefing.future_risk.title ?? "a grounded future risk"}`}</small>
            )}
          </div>
        )}
        {operator?.brain && (
          <div className="journey-operator-brain" data-testid="journey-operator-brain">
            <span className="v8-kicker">Planning brain</span>
            <strong>{operator.brain.headline}</strong>
            {operator.brain.recovery_resume.pending && (
              <span>
                {operator.brain.recovery_resume.safe_to_resume
                  ? (zh ? "问题已记住，规划 AI 恢复后会继续处理。" : "I remembered the problem and will continue when planning is available.")
                  : (zh ? "这次恢复已保留，需要安全地回到原来的处理链。" : "I kept this recovery safe and will not switch brains blindly.")}
              </span>
            )}
          </div>
        )}
        {operator?.collective && operator.collective.state !== "SINGLE_TRAVELLER" && (
          <div className="journey-operator-collective" data-testid="journey-operator-collective">
            <span className="v8-kicker">Shared trip</span>
            <strong>
              {operator.collective.state === "MEDIATING"
                ? (zh ? "大家的选择不同，CityNexus 正在寻找兼顾彼此的方案。" : "Your choices differ. CityNexus is looking for a compromise that protects everyone.")
                : operator.collective.state === "COLLECTIVE_AUTHORIZED"
                  ? (zh ? "大家已同意，正在继续执行共享行程。" : "Everyone agreed. The shared trip is continuing.")
                  : operator.collective.state === "COLLECTIVE_STALE"
                    ? (zh ? "行程情况已变化，需要重新确认。" : "The trip changed, so this group decision needs to be renewed.")
                    : (zh
                      ? `这次变化影响 ${operator.collective.required_count} 位同行者，已回答 ${operator.collective.response_count} 位。`
                      : `This change affects ${operator.collective.required_count} travellers; ${operator.collective.response_count} have responded.`)}
            </strong>
            <div className="journey-operator-members">
              {operator.collective.members.map((member) => (
                <span key={member.member_id ?? member.display_name} data-responded={member.responded}>
                  {member.display_name}{member.responded ? (zh ? " · 已回答" : " · answered") : (zh ? " · 等待中" : " · waiting")}
                </span>
              ))}
            </div>
            {operator.collective.viewer_can_respond && operator.collective.options.length > 0 && (
              <div className="journey-operator-collective-options">
                <span>{zh ? "你更愿意哪种处理？" : "Which recovery fits you?"}</span>
                {operator.collective.options.map((option) => (
                  <button
                    key={option.proposal_id}
                    type="button"
                    disabled={busy !== null}
                    onClick={() => void answerCollectiveOption(option.proposal_id)}
                  >
                    {option.label}
                    {option.schedule_delta_min != null ? ` · ${option.schedule_delta_min} min` : ""}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {operator?.discovery && operator.discovery.state !== "IDLE" && (
          <div className="journey-operator-discovery" data-testid="journey-operator-discovery">
            <span className="v8-kicker">Open-world recovery</span>
            <strong>
              {operator.discovery.state === "DISCOVERY_IN_PROGRESS"
                ? (zh ? "已知选择不够，我正在附近寻找新的可能性。" : "The known choices are too narrow, so I’m looking nearby for new possibilities.")
                : operator.discovery.state === "DISCOVERY_DEGRADED"
                  ? (zh ? "暂时无法连接城市发现服务，已有行程选项保持不变。" : "City discovery is temporarily unavailable; your existing recovery options are unchanged.")
                  : (zh ? "我已经找过附近的替代方案，但还没有更多可靠选择。" : "I looked nearby, but I still don’t have another grounded recovery.")}
            </strong>
          </div>
        )}
        {operator?.operations && (
          <div className="journey-operator-operations" data-testid="journey-operator-operations">
            <span className="v8-kicker">{zh ? "外部事务" : "Trip operations"}</span>
            <strong>
              {operator.operations.status === "WAITING_FOR_APPROVAL"
                ? (zh ? "这次调整还需要处理预订。" : "This recovery still needs reservation work.")
                : operator.operations.status === "EXECUTING"
                  ? (zh ? "正在更新行程并处理预订……" : "Updating the trip and handling the reservation…")
                  : operator.operations.status === "COMPLETED"
                    ? (zh ? "Sandbox 预订已确认，继续照看行程。" : "Sandbox booking confirmed. I’m watching the trip again.")
                    : operator.operations.status === "PARTIALLY_APPLIED"
                      ? (zh ? "部分预订操作已完成，剩余事项需要你的注意。" : "Part of the reservation work completed; the remaining work needs your attention.")
                      : (zh ? "预订操作需要你的注意。" : "Reservation work needs your attention.")}
            </strong>
            <span>
              {zh
                ? `${operator.operations.completed_action_count} / ${operator.operations.planned_action_count} 项已完成 · ${operator.operations.provider_label ?? "LAB_SANDBOX_PROVIDER"}`
                : `${operator.operations.completed_action_count} of ${operator.operations.planned_action_count} actions complete · ${operator.operations.provider_label ?? "LAB_SANDBOX_PROVIDER"}`}
            </span>
          </div>
        )}
        {!operator?.enabled && (
          <button
            type="button"
            data-testid="journey-operator-start"
            disabled={busy !== null}
            onClick={() => void startOperator()}
          >
            {zh ? "照看这趟行程" : "Take care of this trip"}
          </button>
        )}
        {operator?.enabled && <span data-testid="journey-operator-state">
          {operator.state === "WATCHING"
            ? (zh ? "正在照看" : "Watching")
            : operator.state === "INVESTIGATING"
              ? (zh ? "正在了解情况" : "Working on a recovery")
              : operator.state === "WAITING_FOR_APPROVAL"
                ? (zh ? "等待你的批准" : "Waiting for your approval")
                : operator.state === "RECOVERED"
                  ? (zh ? "调整已应用，继续照看" : "Change applied · watching again")
                  : operator.state === "NEEDS_ATTENTION"
                    ? (zh ? "需要你的注意" : "Needs your attention")
                    : operator.state === "DEGRADED"
                      ? (zh ? "暂时无法完整照看" : "Needs attention")
                      : (zh ? "正在处理" : "Working")}
        </span>}
        {operator?.approval?.required && operator.decision && (
          <div className="journey-operator-approval" data-testid="journey-operator-approval">
            <b>{zh ? "CityNexus 找到一个更稳妥的调整" : "CityNexus recommends this change"}</b>
            <span>{operator.decision.summary ?? (zh ? "这项调整可以减少行程影响。" : "This change should reduce the impact on your trip.")}</span>
            {operator.decision.schedule_delta_min != null && (
              <span>{zh ? `时间影响：${operator.decision.schedule_delta_min} 分钟` : `Schedule impact: ${operator.decision.schedule_delta_min} min`}</span>
            )}
            <button
              type="button"
              data-testid="journey-operator-approve"
              disabled={busy !== null}
              onClick={() => void approveOperatorChange()}
            >
              {zh ? "批准变更" : "Approve change"}
            </button>
            <button
              type="button"
              data-testid="journey-operator-reject"
              disabled={busy !== null}
              onClick={() => void rejectOperatorChange()}
            >
              {zh ? "保留当前行程" : "Keep current plan"}
            </button>
          </div>
        )}
        {operator?.timeline?.length ? (
          <ol data-testid="journey-operator-timeline">
            {operator.timeline.slice(-5).map((item) => <li key={`${item.at}-${item.kind}`}>{item.label}</li>)}
          </ol>
        ) : null}
      </section>

      {guardianSurfaceState && (
        <div
          className={`live-guardian-check live-guardian-check-${guardianSurfaceState}`}
          data-testid="live-guardian-check"
          data-state={guardianSurfaceState}
          role="status"
        >
          <b>
            {guardianSurfaceState === "clear"
              ? zh
                ? "刚刚检查过"
                : "Just checked"
              : guardianSurfaceState === "incomplete"
                ? zh
                  ? "部分信息待确认"
                  : "Some information needs checking"
                : zh
                  ? "正在处理行程变化"
                  : "Trip change is being handled"}
          </b>
          <span>
            {guardianSurfaceState === "clear"
              ? t("live.guardianCheckedClear")
              : guardianSurfaceState === "incomplete"
                ? t("live.guardianVerificationIncomplete")
                : t("live.guardianRecoveryActive")}
          </span>
          {guardianPulse?.completed_at && (
            <time dateTime={guardianPulse.completed_at}>
              {new Date(guardianPulse.completed_at).toLocaleTimeString(locale, {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </time>
          )}
        </div>
      )}

      {guardianWatch?.enabled && guardianWatch.next_move?.copy && (
        <div className="live-next-move" data-testid="live-next-move" role="status">
          <b>{zh ? "下一步" : "Next move"}</b>
          <span>{guardianWatch.next_move.copy}</span>
        </div>
      )}

      {launchSetup?.status === "NEEDS_ORIGIN" && (
        <div className="live-readiness live-launch-setup" data-testid="live-launch-setup" role="status">
          <b>{zh ? "你将从哪里出发？" : "Where will you start from?"}</b>
          <span>
            {zh
              ? "CityNexus 需要一个明确的起点，才能估算何时出发。"
              : "CityNexus needs a starting point before it can estimate when to leave."}
          </span>
          {(launchSetup.candidates ?? []).filter((candidate) => candidate.eligible && candidate.display_name).map((candidate) => (
            <button
              key={candidate.kind}
              type="button"
              disabled={busy !== null}
              onClick={() => {
                if (candidate.kind === "SELECTED_STAY") {
                  void confirmLaunchSource("SELECTED_STAY");
                } else if (candidate.kind === "ARRIVAL_ANCHOR") {
                  void confirmLaunchSource("ARRIVAL_ANCHOR");
                }
              }}
            >
              {zh ? `从 ${candidate.display_name} 出发` : `Start from ${candidate.display_name}`}
            </button>
          ))}
          {(launchSetup.actions ?? []).includes("CHOOSE_PLACE") && (
            <small>{zh ? "也可以选择一个已验证的地点作为计划起点。" : "You can also choose another verified place as your planned starting point."}</small>
          )}
        </div>
      )}

      {launchSetup?.contract?.display_name && (
        <div className="live-next-move" data-testid="live-launch-confirmed" role="status">
          {zh
            ? `首段路线将从 ${launchSetup.contract.display_name} 规划。`
            : `Planning your first route from ${launchSetup.contract.display_name}.`}
          {!routeOperation || routeOperation.status === "UNAVAILABLE" || routeOperation.status === "FAILED" ? (
            <button type="button" disabled={busy !== null} onClick={() => void checkRoute()}>
              {zh ? "检查路线" : "Check route"}
            </button>
          ) : null}
          {routeOperation?.status === "RUNNING" && (
            <small>{zh ? "正在检查从起点到下一站的路线……" : "Checking the route to your first stop…"}</small>
          )}
          {routeOperation?.status === "COMPLETED" && routeOperation.result?.duration_min != null && (
            <small>
              {zh
                ? `约 ${routeOperation.result.duration_min} 分钟${leaveByDisplay ? ` · 建议 ${leaveByDisplay} 前出发` : ""}`
                : `About ${routeOperation.result.duration_min} min${leaveByDisplay ? ` · leave around ${leaveByDisplay}` : ""}`}
            </small>
          )}
          {routeOperation?.status === "UNAVAILABLE" && (
            <small>{zh ? "CityNexus 暂时无法获取这段路线的可靠结果。" : "CityNexus could not get a reliable route for this leg."}</small>
          )}
          {routeOperation?.status === "FAILED" && (
            <small>{zh ? "路线服务暂时不可用。" : "The route provider is unavailable right now."}</small>
          )}
        </div>
      )}

      {departureReadiness && (
        <div
          className={`live-readiness live-readiness-${String(departureReadiness.state ?? "unknown").toLowerCase()}`}
          data-testid="live-departure-readiness"
          role="status"
        >
          <b>{zh ? "下一站准备情况" : "Ready for next?"}</b>
          {departureReadiness.target_title && <strong>{departureReadiness.target_title}</strong>}
          <span>
            {departureReadiness.state === "READY"
              ? zh ? "可以出发 · 下一站按计划开放。" : "Ready to go · next stop opens as planned."
              : departureReadiness.state === "BLOCKED"
                ? zh ? "先不要出发 · 下一站目前无法前往。" : "Do not leave yet · the next stop is currently unavailable."
                : departureReadiness.state === "ACTION_NEEDED"
                  ? zh ? "出发前检查 · 下一站或路线仍需确认。" : "Check before leaving · the next stop or route still needs checking."
                  : departureReadiness.state === "NOT_DUE"
                    ? zh ? "还没到出发时间 · 按计划准备即可。" : "Not time to leave yet · stay with the plan."
                    : zh ? "基本准备好了 · 仍有实时信息未确认。" : "Mostly ready · some live information is unavailable."}
          </span>
          {departureReadiness.must_leave_by && (
            <small>
              {zh ? "建议在 " : "Leave by "}
              {new Date(departureReadiness.must_leave_by).toLocaleTimeString(locale, {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </small>
          )}
          {departureReadiness.launch_origin?.name && (
            <small>
              {zh ? `出发点：${departureReadiness.launch_origin.name}` : `Starting from ${departureReadiness.launch_origin.name}`}
            </small>
          )}
          {(() => {
            const activation = departureReadiness.departure_activation;
            if (!activation) return null;
            if (activation.state === "ALREADY_EN_ROUTE") {
              return <strong>{zh ? "正在前往下一站。" : "On the way to the next stop."}</strong>;
            }
            if (activation.state === "BLOCKED") {
              return <strong>{zh ? "先暂停出发，请先检查行程提示。" : "Hold before leaving — check the issue first."}</strong>;
            }
            if (activation.state === "NO_ROUTE") {
              return <small>{zh ? "路线尚未准备好。" : "The route is not ready yet."}</small>;
            }
            if (activation.state === "NOT_DUE") return null;
            return (
              <>
                <strong>
                  {activation.state === "LEAVE_SOON"
                    ? zh ? "快到出发时间了。" : "You’ll need to leave soon."
                    : activation.state === "OVERDUE"
                      ? zh ? "已超过建议出发时间；确认你已在路上。" : "You’re past the planned leave time; confirm when you’re on the way."
                      : zh ? `该出发前往 ${activation.target_title ?? departureReadiness.target_title ?? "下一站"} 了。` : `It’s time to leave for ${activation.target_title ?? departureReadiness.target_title ?? "your next stop"}.`}
                </strong>
                {activation.can_confirm_departure === true && (
                  <button type="button" disabled={busy !== null} onClick={() => void confirmDeparture()}>
                    {zh ? "我出发了" : "I’m leaving"}
                  </button>
                )}
              </>
            );
          })()}
        </div>
      )}

      {journeyCompleted && (openDisruptions.length > 0 || pending.length > 0) && (
        <p className="v8-muted" data-testid="live-completed">
          {t("live.completedProposalIntro")}
        </p>
      )}

      {openDisruptions.length > 0 && (
        <div className="live-disruption" data-testid="live-disruption" role="status">
          <b>
            {journeyCompleted
              ? t("live.completedDisruption")
              : zh
                ? "发生了什么"
                : "What happened"}
          </b>
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

      {/* acknowledged-only events are a subset of openDisruptions (an
          acknowledged event is still open), so this must key off their own
          count — the earlier `openDisruptions.length === 0` guard made this
          branch unreachable (V2-T3). */}
      {acknowledgedOnly.length > 0 && (
        <p className="v8-muted" data-testid="live-acknowledged">
          {zh
            ? "已知晓，仍待处理：你已经看过这些变化，但还没有选定新的安排。"
            : "Seen, still open: you have seen these changes but have not chosen a new arrangement yet."}
        </p>
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
            <article
              className="live-proposal"
              key={proposal.id}
              data-testid="live-proposal"
              data-authority={journeyCompleted ? "advisory-after-completion" : "actionable"}
              data-state={busy === proposal.id ? "accepting" : "idle"}
            >
              <b data-testid="live-proposal-heading">
                {journeyCompleted
                  ? t("live.completedProposalTitle")
                  : `${optionLabel} · ${zh ? "推荐怎么改" : "Suggested change"}`}
              </b>
              {summary && (
                <p className="live-summary" data-testid="live-summary">
                  {summary}
                </p>
              )}
              {proposal.source_agent_run_id && (
                <p
                  className="v8-muted"
                  data-testid="live-agent-origin"
                  data-agent-run-id={proposal.source_agent_run_id}
                  data-recovery-epoch-id={proposal.recovery_epoch_id ?? ""}
                >
                  {zh
                    ? "这次调整由旅行 Agent 根据最新事实自主提出；最终执行仍受当前行程权限约束。"
                    : "Your travel Agent proposed this change from the latest facts; execution still follows the Journey's current authority."}
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
              {journeyCompleted ? (
                <p className="v8-muted" data-testid="live-advisory-only">
                  {t("live.advisoryOnly")}
                </p>
              ) : (
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
              )}
            </article>
          );
        })
      ) : (
        /* ORD-0407 ③: this cell deliberately carries no action, and that is a decision, not a leftover.
           It says nothing is waiting for a decision, so any button here would offer work the server did
           not report -- the exact overreach ORD-0384 was narrowed for refusing. The screen already
           carries the one action that could change this reading (`live-update-location`, and
           `live-report-rain` beside it), measured above the 768 px line, so "no action in this cell" is
           not "no way forward on this screen". e2e/qoder-ord0407-empty-state-actions.spec.ts judges
           both halves; if this sentence ever gains a button, that cell goes red on purpose. */
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
