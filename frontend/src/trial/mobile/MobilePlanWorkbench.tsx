import { useCallback, useEffect, useRef, useState } from "react";
import { CalendarDays, Check, Clock3, MapPin } from "lucide-react";
import { CityNexusApiError, cityNexusApi, type Activity, type JourneyRecord, type PlanVersion, type TravelPlanningInput, type TravelBrief } from "../../api/citynexus";
import { TravelBriefPreview } from "./TravelBriefPreview";
import { formatMinorMoney } from "../../lib/money";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import "./MobilePlanWorkbench.css";

type PlanSnapshot = { bearer: string; journey: JourneyRecord; plans: PlanVersion[]; input: TravelPlanningInput | null };
type WriteAction = "generate" | "select" | "start" | "brief" | "facts";

function failureText(error: unknown): string {
  if (error instanceof CityNexusApiError) {
    const body = error.body as { reason_code?: string; error?: { reason_code?: string }; detail?: { reason_code?: string } } | null;
    const reason = body?.reason_code ?? body?.error?.reason_code ?? body?.detail?.reason_code;
    if (reason === "UNRESOLVED_ACTIVITY_FACTS") return "地点的营业时间还没核实。回到探索，查看来源或换一个地点。";
    if (reason === "PLACE_COST_UNVERIFIED") return "地点费用还没核实。回到探索查看来源后继续。";
    if (reason === "PLACES_NOT_IN_CATALOG") return "地点列表有更新，请重新选择地点。";
    if (error.status === 401 || error.status === 403) return "当前账号无法读取这份行程，请重新进入行程。";
    if (error.status === 409) return "行程已有变化，刷新方案后继续。";
    if (error.status === 422) return "这些地点暂时排不成可用方案。回到探索补充或更换地点。";
  }
  return "暂时没能读取最新结果，点击刷新方案再继续。";
}

function dateKey(value: string | undefined, timeZone: string): string | null {
  if (!value || !Number.isFinite(Date.parse(value))) return null;
  try {
    const parts = new Intl.DateTimeFormat("en", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(value));
    const part = (name: string) => parts.find((item) => item.type === name)?.value;
    return `${part("year")}-${part("month")}-${part("day")}`;
  } catch { return null; }
}

function timeText(value: string, timeZone: string): string {
  if (!Number.isFinite(Date.parse(value))) return "时间待确认";
  try { return new Intl.DateTimeFormat("zh-CN", { timeZone, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value)); }
  catch { return "时间待确认"; }
}

function activityCost(activity: Activity): string {
  if (activity.cost_status === "KNOWN_FREE") return "免费";
  if (activity.cost_status === "KNOWN_PAID" && Number.isFinite(activity.estimated_cost?.amount_minor)) {
    return formatMinorMoney(activity.estimated_cost.amount_minor, activity.estimated_cost.currency, "zh-CN");
  }
  return "费用待确认";
}

function sourceLinks(activity: Activity): string[] {
  const meta = activity.metadata;
  const opening = meta?.opening_hours as { source_urls?: unknown } | undefined;
  const urls = meta?.source_urls ?? opening?.source_urls;
  if (!Array.isArray(urls)) return [];
  return urls.filter((value): value is string => {
    if (typeof value !== "string") return false;
    try { const url = new URL(value); return /^https?:$/.test(url.protocol) && !url.username && !url.password; }
    catch { return false; }
  }).slice(0, 2);
}

function PlanSchedule({ plan, journey }: { plan: PlanVersion; journey: JourneyRecord }) {
  const timeZone = journey.timezone;
  const days = new Map<string, Activity[]>();
  for (const activity of [...plan.activities].sort((a, b) => a.sequence_no - b.sequence_no)) {
    const key = dateKey(activity.start_at, timeZone) ?? "日期待确认";
    days.set(key, [...(days.get(key) ?? []), activity]);
  }
  const start = dateKey(journey.start_at, timeZone);
  const end = dateKey(journey.end_at, timeZone);
  const requestedDays = start && end ? Math.round((Date.parse(end) - Date.parse(start)) / 86_400_000) + 1 : null;
  const scheduledDays = [...days.keys()].filter((day) => day !== "日期待确认").length;
  const missingDays = requestedDays && requestedDays > scheduledDays ? requestedDays - scheduledDays : 0;
  const unknownCosts = plan.activities.filter((item) => !["KNOWN_FREE", "KNOWN_PAID"].includes(item.cost_status ?? "")).length;
  const knownTotal = plan.total_cost_status === "KNOWN" && unknownCosts === 0;
  const total = plan.total_cost && Number.isFinite(plan.total_cost.amount_minor)
    ? formatMinorMoney(plan.total_cost.amount_minor, plan.total_cost.currency, "zh-CN") : null;

  return <>
    <div className="rev-plan-summary">
      <span><CalendarDays size={16} aria-hidden="true" />{scheduledDays} 天 · {plan.activities.length} 项安排</span>
      <strong>{unknownCosts > 0 && unknownCosts === plan.activities.length ? "费用待确认" : total ? `${knownTotal ? "计划费用" : "已知费用"} ${total}` : "费用汇总待确认"}</strong>
    </div>
    {unknownCosts > 0 && <p className="rev-plan-gap">{unknownCosts} 项费用待确认，尚未计入完整预算。</p>}
    {missingDays > 0 && <p className="rev-plan-gap" data-testid="rev-plan-day-gap">还有 {missingDays} 天未安排，可返回探索补充地点。</p>}
    {[...days].map(([day, activities]) => <section className="rev-plan-day" key={day}>
      <h4>{day === "日期待确认" ? day : `${day.slice(5).replace("-", "月")}日`}</h4>
      <ol>
        {activities.map((activity) => <li key={activity.id}>
          <div className="rev-plan-time"><Clock3 size={14} aria-hidden="true" />{timeText(activity.start_at, timeZone)}—{timeText(activity.end_at, timeZone)}</div>
          <strong><MapPin size={15} aria-hidden="true" />{activity.title}</strong>
          <div className="rev-plan-activity-facts"><span>{activityCost(activity)}</span>{activity.travel_from_prev_min > 0 && <span>转场预留 {activity.travel_from_prev_min} 分钟</span>}</div>
          {sourceLinks(activity).map((url, index) => <a key={url} href={url} target="_blank" rel="noreferrer">查看地点来源{index ? ` ${index + 1}` : ""} ↗</a>)}
        </li>)}
      </ol>
    </section>)}
    {plan.activities.length === 0 && <p>这份方案还没有活动安排。</p>}
  </>;
}

export function MobilePlanWorkbench({ journeyId, placeId, visible, onStarted, onExplore, onBriefSaved }: {
  journeyId: string;
  placeId: string | null;
  visible: boolean;
  onStarted: () => Promise<void>;
  onExplore: () => void;
  onBriefSaved?: (brief: TravelBrief) => void;
}) {
  const [bearer, setBearer] = useState(readTravelerBearer);
  const [snapshot, setSnapshot] = useState<PlanSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<WriteAction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [costAck, setCostAck] = useState(false);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const [candidateIds, setCandidateIds] = useState<string[]>([]);
  const epoch = useRef(0);
  const writeLock = useRef(false);
  const current = snapshot?.bearer === readTravelerBearer() && snapshot?.journey.id === journeyId ? snapshot : null;

  const refresh = useCallback(async () => {
    const serial = ++epoch.current;
    const token = readTravelerBearer();
    if (!token) { setSnapshot(null); return; }
    setLoading(true);
    try {
      const [journey, plans, input] = await Promise.all([cityNexusApi.getJourney(journeyId), cityNexusApi.listJourneyPlans(journeyId), cityNexusApi.getTravelPlanningInput(journeyId).catch(() => null)]);
      if (serial !== epoch.current || token !== readTravelerBearer()) return;
      if (journey.id !== journeyId || !Array.isArray(plans) || plans.some((plan) => plan.journey_id !== journeyId || !Array.isArray(plan.activities))) throw new Error("Plan response mismatch");
      if (input && input.journey_id !== journeyId) throw new Error("Trip intent response mismatch");
      setSnapshot({ bearer: token, journey, plans, input });
      setNeedsRefresh(false);
      setMessage(null);
    } catch (error) {
      if (serial !== epoch.current || token !== readTravelerBearer()) return;
      setSnapshot(null);
      setMessage(failureText(error));
    } finally { if (serial === epoch.current) setLoading(false); }
  }, [journeyId]);

  useEffect(() => subscribeTravelerBearer((token) => {
    epoch.current += 1;
    setSnapshot(null);
    setMessage(null);
    setCostAck(false);
    setCandidateIds([]);
    setBearer(token);
  }), []);
  useEffect(() => {
    if (visible && bearer) void refresh();
    return () => { epoch.current += 1; };
  }, [bearer, visible, refresh]);
  useEffect(() => { setCostAck(false); }, [placeId]);

  const write = async (action: WriteAction, plan?: PlanVersion) => {
    const token = readTravelerBearer();
    if (!token || !current || writeLock.current || needsRefresh || loading) return;
    if (action === "generate" && (current.input ? !readyForMulti : (!costAck || !placeId))) return;
    const serial = epoch.current;
    const stillCurrent = () => token === readTravelerBearer() && serial === epoch.current;
    writeLock.current = true;
    setBusy(action);
    setMessage(null);
    try {
      if (action === "generate") {
        if (current.input) await cityNexusApi.generateFromDiscovery(journeyId, candidateIds, crypto.randomUUID());
        else await cityNexusApi.generatePlans(journeyId, 1, { placeIds: [placeId!], allowSinglePlace: true, allowUnknownCost: true, idempotencyKey: crypto.randomUUID() });
      } else if (action === "select" && plan) {
        await cityNexusApi.selectPlan(journeyId, plan.id);
      } else if (action === "start") {
        const started = await cityNexusApi.startJourney(journeyId);
        if (!stillCurrent()) return;
        if (started.journey_id !== journeyId || started.context?.journey_status !== "ACTIVE") throw new Error("Journey not active");
        await onStarted();
      }
      if (stillCurrent()) await refresh();
    } catch (error) {
      if (!stillCurrent()) return;
      setNeedsRefresh(true);
      setMessage(failureText(error));
    } finally {
      writeLock.current = false;
      setBusy(null);
    }
  };

  if (!visible) return null;
  const plans = current?.plans.filter((plan) => ["CANDIDATE", "SELECTED", "ACTIVE"].includes(plan.status) && plan.lifecycle !== "STANDBY") ?? [];
  const selected = plans.find((plan) => plan.is_current === true);
  const canStart = current?.journey.status === "PLANNED" && selected?.status === "SELECTED" && !selected.stale;
  const locked = Boolean(busy || loading || needsRefresh);
  const picked = current?.input?.candidates.filter((item) => candidateIds.includes(item.candidate_id)) ?? [];
  const readyForMulti = picked.length >= 2 && picked.length === candidateIds.length && picked.every((item) => item.selection_state === "READY_FOR_NATIVE_PLAN");
  const saveBrief = async (brief: TravelBrief) => {
    const token = readTravelerBearer();
    if (!current || !token || writeLock.current) return;
    const serial = epoch.current;
    writeLock.current = true; setBusy("brief"); setMessage(null);
    try {
      const saved = await cityNexusApi.saveTravelBrief(journeyId, brief);
      if (serial === epoch.current && token === readTravelerBearer()) {
        if (saved.intent) onBriefSaved?.(saved.intent);
        await refresh();
      }
    } catch (error) { if (serial === epoch.current && token === readTravelerBearer()) setMessage(failureText(error)); }
    finally { writeLock.current = false; setBusy(null); }
  };
  const refreshPlaceFacts = async (place: TravelPlanningInput["candidates"][number]) => {
    const token = readTravelerBearer();
    const currentPlace = current?.input?.candidates.find((item) => item.candidate_id === place.candidate_id);
    if (!current || !token || !currentPlace || currentPlace.receipt_id !== place.receipt_id ||
      currentPlace.facts_status != null || writeLock.current || needsRefresh || loading) return;

    const serial = epoch.current;
    const stillCurrent = () => token === readTravelerBearer() && serial === epoch.current;
    writeLock.current = true;
    setBusy("facts");
    setMessage(null);
    try {
      const refreshed = await cityNexusApi.refreshBootstrapPlaceFacts(
        journeyId, currentPlace.receipt_id, currentPlace.candidate_id,
      );
      if (!stillCurrent()) return;
      if (refreshed.journey_id !== journeyId || refreshed.candidate?.candidate_id !== currentPlace.candidate_id) {
        throw new Error("Place facts response mismatch");
      }

      const input = await cityNexusApi.getTravelPlanningInput(journeyId);
      if (!stillCurrent()) return;
      if (input.journey_id !== journeyId || !input.candidates.some((item) => item.candidate_id === currentPlace.candidate_id)) {
        throw new Error("Place facts planning intent mismatch");
      }
      setSnapshot((previous) => previous?.bearer === token && previous.journey.id === journeyId
        ? { ...previous, input }
        : previous);
    } catch (error) {
      if (!stillCurrent()) return;
      setMessage(error instanceof Error && error.message.includes("mismatch")
        ? "地点详情与当前行程不匹配，未更新显示。请刷新方案后继续。"
        : failureText(error));
    } finally {
      writeLock.current = false;
      setBusy(null);
    }
  };

  return <section className="rev-plan-workbench" data-testid="rev-plan-workbench" aria-busy={Boolean(busy || loading)}>
    <header><div><span className="rev-firstlook-eyebrow">TRAVEL PLAN</span><h2>你的行程方案</h2></div><button type="button" className="rev-plan-refresh" disabled={Boolean(busy || loading)} onClick={() => void refresh()}>刷新方案</button></header>
    {message && <p role="alert" className="rev-plan-message">{message}</p>}
    {loading && !current && <p role="status">正在读取你的行程方案…</p>}
    {current?.input && current.journey.status === "DRAFT" && <TravelBriefPreview key={`${journeyId}:${bearer}`} input={current.input} selected={candidateIds} onSelect={setCandidateIds} onSave={saveBrief} onRefreshFacts={refreshPlaceFacts} disabled={locked} />}
    {current && plans.length === 0 && <p>{current.input ? "从想去清单里挑选地点，再生成日程。" : "先选一个已核实的地点，再把它排进日程。"}</p>}
    {current?.journey.status !== "ACTIVE" && current && <div className="rev-plan-generate">
      {current.input ? <>
        {candidateIds.length > 0 && !readyForMulti && <p className="rev-plan-gap">先选至少两处；资料未齐的地点可展开卡片查询 OpenStreetMap 详情，或改选。</p>}
        <button type="button" disabled={locked || !readyForMulti} onClick={() => void write("generate")} data-testid="rev-plan-generate">{busy === "generate" ? "正在安排行程…" : "用所选地点生成正式方案"}</button>
        <button type="button" onClick={onExplore}>继续探索、补资料 →</button>
      </> : placeId ? <>
        <label><input type="checkbox" checked={costAck} disabled={Boolean(busy)} onChange={(event) => setCostAck(event.target.checked)} />未核实的门票费用，稍后确认</label>
        <button type="button" disabled={locked || !costAck} onClick={() => void write("generate")} data-testid="rev-plan-generate">{busy === "generate" ? "正在安排行程…" : "生成行程方案"}</button>
      </> : <button type="button" onClick={onExplore}>去选地点 →</button>}
    </div>}
    {plans.map((plan) => <article key={plan.id} className="rev-plan-option" data-testid="rev-plan-option" data-current={plan.is_current === true}>
      <div className="rev-plan-option-heading"><h3>方案 {plan.version_no}</h3>{plan.is_current && <span><Check size={15} aria-hidden="true" />{current?.journey.status === "ACTIVE" ? "正在使用" : "已选用"}</span>}</div>
      {current && <PlanSchedule plan={plan} journey={current.journey} />}
      {plan.stale ? <p className="rev-plan-gap">地点信息有更新，请重新生成方案。</p> : plan.selectable !== false && plan.status === "CANDIDATE" && current?.journey.status !== "ACTIVE" && <button type="button" disabled={locked} onClick={() => void write("select", plan)} data-testid="rev-plan-select">{busy === "select" ? "正在选用…" : "选用这份方案"}</button>}
    </article>)}
    {canStart && <div className="rev-plan-start"><p>已选好方案。确认后开始正式行程。</p><button type="button" disabled={locked} onClick={() => void write("start")} data-testid="rev-plan-start">{busy === "start" ? "正在启动…" : "确认方案，开始行程"}</button></div>}
  </section>;
}
