import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cityNexusApi, type TravelPlanningInput, type BootstrapDiscoveryCandidate, type DraftGoalTask, type DraftGoalTaskEvent } from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import { WorkspaceMap } from "./WorkspaceMap";
import "./WorkspaceActions.css";

export type WorkspacePanel = "assistant" | "map" | null;
type Context = { id: string; token: string; owner: string };
type Snapshot = { context: Context; input: TravelPlanningInput; status: string; mapCandidates: BootstrapDiscoveryCandidate[] };
type GoalTaskSnapshot = { context: Context; value: DraftGoalTask; events: DraftGoalTaskEvent[] };
const COPY = {
  assistant: "AI助手", map: "地图", close: "关闭工作台",
  load: "正在读取当前行程…",
  none: "先在探索页建立一趟行程，随后在任何页面都能打开地图和 AI。",
  failed: "暂时无法读取行程，可以重新读取。",
  question: "告诉 Agent 你的旅行计划", send: "开始研究",
  sending: "研究进行中…", reload: "刷新任务",
};

const TASK_STATUS: Record<string, string> = {
  ACCEPTED: "已接收", WORKING: "正在研究", PARTIAL_READY: "已有阶段成果",
  NEEDS_DECISION: "等你决定", RESUMABLE: "可以继续", FAILED_RECOVERABLE: "可以重试",
  CANCELLED: "已取消", COMPLETED: "已完成",
};
const TOOL_NAME: Record<string, string> = {
  inspect_journey: "读取行程", search_city_services: "搜索城市地点",
  research_place_sources: "查找地点资料",
};
const TASK_POINTER = "citynexus.revolution.goal-task";
const MODEL_TURNS = 4;
const TOOL_CALLS = 8;

// This pointer is only a candidate. Every read and model request is authorized by the server.
function readContext(): Context | null {
  try {
    const identity = readTravelerIdentity();
    const token = readTravelerBearer();
    const raw = localStorage.getItem("citynexus.revolution.firstlook.journey");
    if (!identity || !token || !raw) return null;
    const value = JSON.parse(raw) as { id?: unknown; ownerTravelerId?: unknown };
    if (typeof value.id !== "string" || !/^[0-9a-f-]{36}$/i.test(value.id) || value.ownerTravelerId !== identity.travelerId) return null;
    return { id: value.id, token, owner: identity.travelerId };
  } catch { return null; }
}
function sameContext(a: Context | null, b: Context | null): boolean {
  return !!a && !!b && a.id === b.id && a.owner === b.owner && a.token === b.token;
}
function pointerKey(actor: Context): string { return `${TASK_POINTER}.${actor.owner}.${actor.id}`; }
function readTaskPointer(actor: Context): string | null {
  try {
    const value = localStorage.getItem(pointerKey(actor));
    return value && /^[0-9a-f-]{36}$/i.test(value) ? value : null;
  } catch { return null; }
}
function saveTaskPointer(actor: Context, taskId: string): void {
  try { localStorage.setItem(pointerKey(actor), taskId); } catch { /* server remains the task record */ }
}
function taskStepText(result: Record<string, unknown>): string {
  const reason = typeof result.reason_code === "string" ? result.reason_code : null;
  if (reason) return reason;
  if (typeof result.place_count === "number") return `${result.place_count} 处地点`;
  if (Array.isArray(result.observation_ids)) return `${result.observation_ids.length} 条来源记录`;
  return result.status === "COMPLETED" ? "完成" : String(result.status ?? "已记录");
}

export function WorkspaceActions({ panel, onClose }: { panel: WorkspacePanel; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const [revision, setRevision] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [goalTaskSnapshot, setGoalTaskSnapshot] = useState<GoalTaskSnapshot | null>(null);
  const [question, setQuestion] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [modelConsent, setModelConsent] = useState(false);
  const [onlineResearchConsent, setOnlineResearchConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [aiReady, setAiReady] = useState(false);
  const [allowTiles, setAllowTiles] = useState(false);
  const previousContext = useRef<Context | null>(null);
  const generation = useRef(0);
  const writeBusy = useRef(false);
  const postController = useRef<AbortController | null>(null);
  const context = readContext();
  const visible = snapshot && sameContext(snapshot.context, context) ? snapshot : null;
  const visibleTask = goalTaskSnapshot && sameContext(goalTaskSnapshot.context, context) ? goalTaskSnapshot.value : null;
  const visibleEvents = goalTaskSnapshot && sameContext(goalTaskSnapshot.context, context) ? goalTaskSnapshot.events : [];

  useEffect(() => {
    const invalidate = () => {
      generation.current += 1;
      postController.current?.abort();
      postController.current = null;
      writeBusy.current = false;
      setSnapshot(null); setGoalTaskSnapshot(null); setQuestion(""); setRequestError(null);
      setModelConsent(false); setOnlineResearchConsent(false);
      setLoadError(null); setBusy(false); setAllowTiles(false); setAiReady(false);
      setRevision((value) => value + 1);
    };
    const unsubscribe = subscribeTravelerBearer(invalidate);
    window.addEventListener("storage", invalidate);
    return () => { unsubscribe(); window.removeEventListener("storage", invalidate); generation.current += 1; postController.current?.abort(); };
  }, []);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (panel && !node.open) node.showModal();
    else if (!panel && node.open) node.close();
  }, [panel]);

  // Panel navigation is local. Opening it performs signed reads only, never a model call.
  useEffect(() => {
    if (!panel) return;
    const actor = readContext();
    if (!actor) { setSnapshot(null); setLoading(false); return; }
    if (!sameContext(actor, previousContext.current)) {
      generation.current += 1;
      postController.current?.abort();
      postController.current = null;
      writeBusy.current = false;
      previousContext.current = actor;
      setQuestion(""); setGoalTaskSnapshot(null); setBusy(false); setRequestError(null);
      setModelConsent(false); setOnlineResearchConsent(false); setAllowTiles(false); setAiReady(false);
    }
    let cancelled = false;
    setLoading(true); setLoadError(null);
    const taskId = readTaskPointer(actor);
    const taskRequest = taskId
      ? Promise.all([
        cityNexusApi.getDraftGoalTask(actor.id, taskId),
        cityNexusApi.getDraftGoalTaskEvents(actor.id, taskId, 0),
      ]).catch(() => null)
      : Promise.resolve(null);
    Promise.all([cityNexusApi.getTravelPlanningInput(actor.id), cityNexusApi.getJourney(actor.id),
      cityNexusApi.getJourneyMapPlaces(actor.id).catch(() => null), taskRequest])
      .then(([input, journey, mapPlaces, savedTask]) => {
        if (cancelled || !sameContext(actor, readContext())) return;
        if (input.journey_id !== actor.id || journey.id !== actor.id || !Array.isArray(input.candidates)) throw new Error("Context mismatch");
        if (mapPlaces?.journey_id && mapPlaces.journey_id !== actor.id) throw new Error("Map context mismatch");
        setSnapshot({ context: actor, input, status: journey.status,
          mapCandidates: mapPlaces?.journey_id === actor.id && Array.isArray(mapPlaces.candidates) ? mapPlaces.candidates : input.candidates });
        setQuestion((value) => value || (input.intent?.goal ?? "").slice(0, 360));
        if (savedTask && savedTask[0].journey_id === actor.id) {
          setGoalTaskSnapshot({ context: actor, value: savedTask[0], events: savedTask[1].events });
          setModelConsent(savedTask[0].consent.model === true);
          setOnlineResearchConsent(savedTask[0].consent.online_research === true);
        } else if (taskId) {
          try { localStorage.removeItem(pointerKey(actor)); } catch { /* no local task content is retained */ }
        }
      }).catch(() => { if (!cancelled && sameContext(actor, readContext())) { setSnapshot(null); setLoadError(COPY.failed); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    void cityNexusApi.getAgentRuntimeStatus().then((runtime) => {
      if (cancelled || !sameContext(actor, readContext())) return;
      const state = String(runtime.ai_state ?? "").toUpperCase();
      setAiReady(runtime.hermes_compat_configured === true && !["DISABLED", "DISABLED_BY_OPS", "NOT_CONFIGURED"].includes(state));
    }).catch(() => { if (!cancelled && sameContext(actor, readContext())) setAiReady(false); });
    return () => { cancelled = true; };
  }, [Boolean(panel), context?.id, context?.owner, context?.token, revision]);

  const refreshGoalTask = async (actor: Context, taskId: string) => {
    const [value, eventPage] = await Promise.all([
      cityNexusApi.getDraftGoalTask(actor.id, taskId),
      cityNexusApi.getDraftGoalTaskEvents(actor.id, taskId, 0),
    ]);
    if (value.journey_id !== actor.id || eventPage.task_id !== taskId || !sameContext(actor, readContext())) return;
    setGoalTaskSnapshot({ context: actor, value, events: eventPage.events });
  };

  useEffect(() => {
    const actor = readContext();
    const taskId = visibleTask?.task_id;
    const isActive = visibleTask?.status === "WORKING" || busy;
    if (!panel || panel !== "assistant" || !actor || !taskId || !isActive) return;
    let stopped = false;
    const timer = window.setInterval(() => {
      if (!stopped) void refreshGoalTask(actor, taskId).catch(() => undefined);
    }, 1400);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [panel, visibleTask?.task_id, visibleTask?.status, busy, context?.id, context?.owner, context?.token]);

  const startNewTask = async () => {
    const actor = readContext();
    if (!actor || !visible || !sameContext(actor, visible.context) || !aiReady || visible.status !== "DRAFT" || !modelConsent || writeBusy.current || question.trim().length < 4) return;
    const serial = ++generation.current;
    const controller = new AbortController();
    postController.current = controller;
    writeBusy.current = true; setBusy(true); setRequestError(null);
    const timer = window.setTimeout(() => controller.abort(), 180000);
    try {
      const created = await cityNexusApi.createDraftGoalTask(actor.id, {
        goal: question.trim(), model_consent: modelConsent,
        online_research_consent: onlineResearchConsent,
        max_model_turns: MODEL_TURNS, max_tool_calls: TOOL_CALLS,
      }, controller.signal);
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      saveTaskPointer(actor, created.task_id);
      setGoalTaskSnapshot({ context: actor, value: created, events: [] });
      const result = await cityNexusApi.runDraftGoalTask(actor.id, created.task_id, {
        model_consent: modelConsent, online_research_consent: onlineResearchConsent,
        max_model_turns: MODEL_TURNS, max_tool_calls: TOOL_CALLS,
      }, false, controller.signal);
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      setGoalTaskSnapshot({ context: actor, value: result, events: [] });
      await refreshGoalTask(actor, created.task_id);
    } catch (error) {
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      setRequestError(error instanceof Error && error.name === "AbortError"
        ? "本次响应等待超时；刷新可查看服务端任务进度。"
        : error instanceof Error ? error.message : "任务未能启动。");
    } finally {
      window.clearTimeout(timer);
      if (serial === generation.current) { postController.current = null; writeBusy.current = false; setBusy(false); }
    }
  };

  const resumeTask = async () => {
    const actor = readContext();
    const task = visibleTask;
    if (!actor || !task || !modelConsent || writeBusy.current) return;
    const serial = ++generation.current;
    const controller = new AbortController();
    postController.current = controller;
    writeBusy.current = true; setBusy(true); setRequestError(null);
    const nextTurns = Math.min(8, Math.max(task.budget.max_model_turns ?? MODEL_TURNS, task.usage.model_turns ?? 0) + 2);
    const nextTools = Math.min(16, (task.budget.max_tool_calls ?? TOOL_CALLS) + 4);
    const timer = window.setTimeout(() => controller.abort(), 180000);
    try {
      const result = await cityNexusApi.runDraftGoalTask(actor.id, task.task_id, {
        model_consent: modelConsent, online_research_consent: onlineResearchConsent,
        max_model_turns: nextTurns, max_tool_calls: nextTools,
      }, true, controller.signal);
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      setGoalTaskSnapshot({ context: actor, value: result, events: [] });
      await refreshGoalTask(actor, task.task_id);
    } catch (error) {
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      setRequestError(error instanceof Error && error.name === "AbortError"
        ? "本次响应等待超时；刷新可查看服务端任务进度。"
        : error instanceof Error ? error.message : "任务未能继续。");
    } finally {
      window.clearTimeout(timer);
      if (serial === generation.current) { postController.current = null; writeBusy.current = false; setBusy(false); }
    }
  };

  const cancelTask = async () => {
    const actor = readContext();
    const task = visibleTask;
    if (!actor || !task) return;
    try {
      const value = await cityNexusApi.cancelDraftGoalTask(actor.id, task.task_id);
      if (sameContext(actor, readContext())) await refreshGoalTask(actor, value.task_id);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "任务取消失败。");
    }
  };

  const nextModelBudget = visibleTask
    ? Math.min(8, Math.max(
        visibleTask.budget.max_model_turns ?? MODEL_TURNS,
        visibleTask.usage.model_turns ?? 0,
      ) + 2)
    : MODEL_TURNS;
  const nextToolBudget = visibleTask
    ? Math.min(16, (visibleTask.budget.max_tool_calls ?? TOOL_CALLS) + 4)
    : TOOL_CALLS;

  return createPortal(<dialog ref={dialog} className="rev-workspace-dialog" aria-labelledby="rev-workspace-heading"
    onCancel={(event) => { event.preventDefault(); closeRef.current(); }}>
    <header className="rev-workspace-top"><h2 id="rev-workspace-heading">{panel === "map" ? COPY.map : COPY.assistant}</h2>
      <button type="button" onClick={onClose} aria-label={COPY.close}>×</button></header>
    <div className="rev-workspace-body">
      {!context && <p>{COPY.none}</p>}
      {loading && !visible && <p role="status">{COPY.load}</p>}
      {loadError && <p role="alert">{loadError}</p>}
      {context && <button type="button" className="rev-workspace-secondary" disabled={loading} onClick={() => {
        const actor = readContext();
        if (actor && visibleTask) void refreshGoalTask(actor, visibleTask.task_id).catch(() => undefined);
        setRevision((value) => value + 1);
      }}>{COPY.reload}</button>}
      {visible && panel === "map" && <WorkspaceMap candidates={visible.mapCandidates} allowed={allowTiles} onAllow={() => setAllowTiles(true)} />}
      {visible && panel === "assistant" && <>
        <p>{visible.input.trip.dates.length} 天 · {visible.input.trip.party_size} 人 · 旅行需求已从服务器读取</p>
        {!aiReady && <p role="status">AI 尚未连接。</p>}
        {visible.status !== "DRAFT" ? <p>这趟行程已进入确认或执行阶段，关闭面板后在行程页查看执行助手。</p> :
          <form onSubmit={(event) => { event.preventDefault(); void startNewTask(); }}>
            <label htmlFor="rev-workspace-question">{COPY.question}</label>
            <textarea id="rev-workspace-question" rows={5} maxLength={2000} value={question} disabled={busy} onChange={(event) => setQuestion(event.target.value)} />
            <label className="rev-workspace-consent"><input type="checkbox" checked={modelConsent} disabled={busy} onChange={(event) => setModelConsent(event.target.checked)} />将目标和行程信息发送给 AI，最多 {MODEL_TURNS} 轮</label>
            <label className="rev-workspace-consent"><input type="checkbox" checked={onlineResearchConsent} disabled={busy} onChange={(event) => setOnlineResearchConsent(event.target.checked)} />允许查询公开地点与来源，最多 {TOOL_CALLS} 次</label>
            <button type="submit" disabled={!aiReady || busy || !modelConsent || question.trim().length < 4}>{busy ? COPY.sending : COPY.send}</button>
          </form>}
        {requestError && <p role="alert">{requestError}</p>}
        {visibleTask && <section aria-label="Agent 任务" className="rev-workspace-answer">
          <h3>旅行研究 · {TASK_STATUS[visibleTask.status] ?? visibleTask.status}</h3>
          <p>{visibleTask.usage.model_turns ?? 0}/{visibleTask.budget.max_model_turns ?? MODEL_TURNS} 轮模型 · {visibleTask.usage.tool_calls ?? 0}/{visibleTask.budget.max_tool_calls ?? TOOL_CALLS} 次工具</p>
          {visibleTask.assistant_summary && <p>{visibleTask.assistant_summary}</p>}
          {visibleTask.failure_code && <p>当前结果：{visibleTask.failure_code}</p>}
          {(visibleTask.tool_steps ?? []).length > 0 && <ol className="rev-workspace-task-steps">
            {(visibleTask.tool_steps ?? []).map((step) => <li key={`${step.run_id}-${step.sequence_no}`}>
              <strong>{TOOL_NAME[step.tool_name] ?? step.tool_name}</strong>
              <span>{taskStepText(step.result)}</span>
            </li>)}
          </ol>}
          {(visibleTask.candidate_places ?? []).length > 0 && <ul className="rev-workspace-task-places">
            {visibleTask.candidate_places?.map((place) => <li key={place.id}>
              <strong>{place.name}</strong><span>{place.opening_state === "KNOWN" ? "营业资料已读取" : "营业待核实"}</span>
              <span>{place.cost_evidence.status === "KNOWN" ? "费用资料已读取" : "费用待核实"}</span>
            </li>)}
          </ul>}
          {visibleEvents.filter((event) => event.event_type.startsWith("TOOL_") || event.event_type === "RUN_STARTED" || event.event_type.startsWith("TASK_")).length > 0 &&
            <ol className="rev-workspace-task-events" aria-label="任务记录">
              {visibleEvents.filter((event) => event.event_type.startsWith("TOOL_") || event.event_type === "RUN_STARTED" || event.event_type.startsWith("TASK_")).map((event) =>
                <li key={event.sequence}>{event.event_type}{event.tool_name ? ` · ${TOOL_NAME[event.tool_name] ?? event.tool_name}` : ""}{event.reason_code ? ` · ${event.reason_code}` : ""}</li>)}
            </ol>}
          {visibleTask.status === "WORKING" && <button type="button" className="rev-workspace-secondary" onClick={() => void cancelTask()}>取消任务</button>}
          {["RESUMABLE", "FAILED_RECOVERABLE", "PARTIAL_READY", "NEEDS_DECISION"].includes(visibleTask.status) &&
            <button type="button" disabled={!aiReady || busy || !modelConsent} onClick={() => void resumeTask()}>
              {busy ? COPY.sending : `继续研究（上限 ${nextModelBudget} 轮 / ${nextToolBudget} 次工具）`}
            </button>}
        </section>}
      </>}
    </div>
  </dialog>, document.body);
}
