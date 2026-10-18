import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  BrainCircuit, CalendarDays, Clock3, Compass, MapPinned, Navigation2, RefreshCw,
  Route, ShieldCheck, Sparkles, Users,
} from "lucide-react";
import {
  cityNexusApi, type DraftGoalTask, type DraftGoalTaskEvent,
} from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import { WorkspaceMap, type WorkspaceMapPoint } from "./WorkspaceMap";
import { WorkspaceActions } from "./WorkspaceActions";
import { GoalDraftEditor } from "./GoalDraftEditor";
import "./MissionCockpit.css";

type Props = {
  journeyId: string;
  cityName: string;
  goal: string;
  journeyStatus: string;
  agentStatus: string;
  agentAvailable: boolean;
  onExplore: () => void;
  onTrip: () => void;
  executionAgent?: ReactNode;
  executionDecisions?: ReactNode;
};

type DataState = "loading" | "ready" | "partial" | "unavailable";
const TASK_POINTER = "citynexus.revolution.goal-task";
const statusCopy: Record<string, string> = {
  ACCEPTED: "已接收目标",
  WORKING: "Agent 正在推进",
  PARTIAL_READY: "已有阶段性成果",
  RESUMABLE: "可以继续研究",
  NEEDS_DECISION: "等待你的决定",
  FAILED_RECOVERABLE: "部分能力暂时不可用",
  CANCELLED: "本次任务已停止",
  COMPLETED: "本次任务已完成",
};
const toolCopy: Record<string, string> = {
  inspect_journey: "读取旅行目标",
  discover_places: "检索公开地点",
  discover_nearby_places: "检索附近地点",
  search_city_services: "查询城市服务",
  research_place_sources: "调查地点来源",
  acquire_place_facts: "核实地点事实",
  estimate_place_facts: "准备参考估算",
  compare_routes: "比较已保存路线",
  save_draft_itinerary: "整理多日草案",
};
const eventCopy: Record<string, string> = {
  RUN_STARTED: "Agent 已开始工作",
  MODEL_TURN_STARTED: "模型正在选择下一步",
  MODEL_TURN_COMPLETED: "模型完成一次处理",
  TOOL_STARTED: "开始调用工具",
  TOOL_COMPLETED: "工具已返回结果",
  TOOL_SUCCEEDED: "工具执行成功",
  TOOL_FAILED: "工具执行未成功",
  TASK_PARTIAL_READY: "已保存阶段成果",
  TASK_DRAFT_UPDATED: "草案已更新",
  TASK_RESUMABLE: "任务可以继续",
  TASK_CANCELLED: "任务已取消",
  MODEL_FAILED: "模型服务暂不可用",
  TASK_NEEDS_DECISION: "需要用户决定",
};

function openAgent(journeyId: string, goal: string) {
  window.dispatchEvent(new CustomEvent("citynexus:open-goal-task", {
    detail: { journeyId, goal: goal.trim().slice(0, 2000) },
  }));
}

function eventLabel(event: DraftGoalTaskEvent): string {
  const summary = eventCopy[event.event_type] ?? "任务事件";
  const tool = event.tool_name ? toolCopy[event.tool_name] ?? event.tool_name : null;
  const reason = event.reason_code && /^[A-Z0-9_]{2,80}$/.test(event.reason_code) ? event.reason_code : null;
  return [summary, tool, reason].filter(Boolean).join(" · ");
}

export function MissionCockpit({
  journeyId, cityName, goal, journeyStatus, agentStatus, agentAvailable, onExplore, onTrip, executionAgent, executionDecisions,
}: Props) {
  const [command, setCommand] = useState(goal);
  const [task, setTask] = useState<DraftGoalTask | null>(null);
  const [events, setEvents] = useState<DraftGoalTaskEvent[]>([]);
  const [places, setPlaces] = useState<WorkspaceMapPoint[]>([]);
  const [dataState, setDataState] = useState<DataState>("loading");
  const [refresh, setRefresh] = useState(0);
  const [mapAllowed, setMapAllowed] = useState(false);
  const [identityTick, setIdentityTick] = useState(0);
  const [commandRevision, setCommandRevision] = useState(0);
  const spatial = useRef<HTMLDivElement>(null);
  const [layer, setLayer] = useState<"map" | "timeline">("map");
  const selectLayer = (next: "map" | "timeline") => {
    setLayer(next);
    spatial.current?.querySelector<HTMLElement>(next === "map" ? ".cn-mission-map-pane" : ".cn-mission-timeline-pane")?.scrollIntoView({ block: "nearest", inline: "start", behavior: "smooth" });
  };
  const goalRequest = useMemo(() => commandRevision ? ({ journeyId, goal: command }) : null, [journeyId, command, commandRevision]);
  const receiveTask = useCallback((value: DraftGoalTask, items: DraftGoalTaskEvent[]) => {
    if (value.journey_id !== journeyId) return;
    setTask(value); setEvents(items); setDataState("ready");
  }, [journeyId]);
  const focusPlace = useCallback((id: string) => {
    const slot = document.querySelector<HTMLDetailsElement>(`.cn-mission-os .rev-goal-draft-slot[data-place-id="${CSS.escape(id)}"]`);
    if (slot) { slot.open = true; slot.scrollIntoView({ block: "nearest", inline: "start", behavior: "smooth" }); }
  }, []);
  useEffect(() => {
    const focus = (event: Event) => {
      const value = (event as CustomEvent).detail;
      if (value?.journeyId && value.journeyId !== journeyId) return;
      if (typeof value?.goal === "string" && value.goal.trim()) { setCommand(value.goal.slice(0, 2000)); setCommandRevision((v) => v + 1); }
      document.querySelector<HTMLTextAreaElement>(".cn-mission-os .rev-workspace-inline textarea")?.focus();
    };
    window.addEventListener("citynexus:mission-command", focus);
    return () => window.removeEventListener("citynexus:mission-command", focus);
  }, [journeyId]);

  useEffect(() => { setCommand(goal); setMapAllowed(false); }, [journeyId]);
  useEffect(() => {
    if (!command.trim() && goal) setCommand(goal);
  }, [goal]);
  useEffect(() => {
    const refreshWorkspace = () => setRefresh((value) => value + 1);
    window.addEventListener("citynexus:mission-refresh", refreshWorkspace);
    return () => window.removeEventListener("citynexus:mission-refresh", refreshWorkspace);
  }, []);
  useEffect(() => subscribeTravelerBearer(() => {
    setTask(null); setEvents([]); setPlaces([]); setMapAllowed(false);
    setIdentityTick((value) => value + 1);
  }), []);

  useEffect(() => {
    const bearer = readTravelerBearer();
    const owner = readTravelerIdentity()?.travelerId;
    if (!bearer || !owner) {
      setTask(null); setEvents([]); setPlaces([]); setDataState("unavailable");
      return;
    }
    let disposed = false;
    setDataState("loading");
    // This local pointer only locates a task. Both reads are authorized by the server.
    const pointer = localStorage.getItem(TASK_POINTER + "." + owner + "." + journeyId);
    const readTask = pointer ? cityNexusApi.getDraftGoalTask(journeyId, pointer).catch(() => null) : Promise.resolve(null);
    const readEvents = pointer ? cityNexusApi.getDraftGoalTaskEvents(journeyId, pointer).catch(() => null) : Promise.resolve(null);
    void Promise.all([
      cityNexusApi.getJourneyMapPlaces(journeyId).catch(() => null), readTask, readEvents,
    ]).then(([map, savedTask, eventPage]) => {
      if (disposed || bearer !== readTravelerBearer() || owner !== readTravelerIdentity()?.travelerId) return;
      const ownedTask = savedTask?.journey_id === journeyId ? savedTask : null;
      setTask(ownedTask);
      setEvents(ownedTask && eventPage?.task_id === ownedTask.task_id && Array.isArray(eventPage.events)
        ? eventPage.events : []);
      setPlaces(map?.journey_id === journeyId && Array.isArray(map.candidates) ? map.candidates : []);
      setDataState(map || ownedTask ? "ready" : "partial");
    }).catch(() => { if (!disposed) setDataState("unavailable"); });
    return () => { disposed = true; };
  }, [journeyId, refresh, identityTick]);

  const researchFingerprint = (task?.research_places ?? []).map((place) => [place.id, place.latitude, place.longitude, place.provider_provenance].join(":")).join("|");
  const mapPoints = useMemo<WorkspaceMapPoint[]>(() => {
    const results = new Map<string, WorkspaceMapPoint>();
    for (const point of places) results.set(point.candidate_id, point);
    for (const point of task?.research_places ?? []) {
      if (point.provider_provenance === "UNVERIFIED") continue;
      results.set(point.id, {
        candidate_id: point.id,
        name: point.name,
        latitude: point.latitude,
        longitude: point.longitude,
        coordinate_system: "WGS84",
        provider_provenance: point.provider_provenance,
        selection_state: "OPENING_UNVERIFIED",
        source_url: point.source_url,
        observation_expired: false,
      });
    }
    return [...results.values()];
  }, [places, researchFingerprint]);
  const draftDays = task?.draft_artifact?.days ?? [];
  const draftSlots = draftDays.flatMap((day) => day.slots.map((slot) => ({ date: day.date, ...slot })));
  const latestEvents = events.slice(-5).reverse();
  useEffect(() => {
    if (task?.status !== "WORKING") return;
    const timer = window.setInterval(() => setRefresh((value) => value + 1), 3000);
    return () => window.clearInterval(timer);
  }, [task?.status]);
  const status = journeyStatus === "ACTIVE" ? "行程执行中" : task ? statusCopy[task.status] ?? "任务已保存" : "等待第一个目标";

  return <section className="cn-mission-os" aria-label="CityNexus Mission 工作台" data-testid="rev-mission-cockpit">
    <header className="cn-mission-head">
      <div><div className="cn-mission-kicker"><Sparkles size={15} /> CITYNEXUS / MISSION OS</div>
        <h2>{cityName}，<span>边研究，边成行。</span></h2><p>地图、日程和 Agent 在同一个工作空间。</p></div>
      <span className="cn-mission-state" aria-live="polite">{status}</span>
    </header>
    <div className="cn-mission-layer-tabs" aria-label="切换工作台图层">
      <button type="button" aria-pressed={layer === "map"} onClick={() => selectLayer("map")} data-testid="rev-mission-layer-map"><MapPinned size={17} />地图</button>
      <button type="button" aria-pressed={layer === "timeline"} onClick={() => selectLayer("timeline")} data-testid="rev-mission-layer-timeline"><CalendarDays size={17} />{journeyStatus === "ACTIVE" ? "执行与待办" : "日程"}</button>
    </div>
    <div className="cn-mission-grid">
      <div className="cn-mission-agent-pane" data-testid="rev-mission-agent-pane">
        <div className="cn-mission-section-heading"><BrainCircuit size={18} /><strong>Agent 命令台</strong></div>
        {journeyStatus === "ACTIVE" ? executionAgent :
          <WorkspaceActions embedded panel="assistant" goalRequest={goalRequest} onClose={() => undefined} onTaskChange={receiveTask} />}
      </div>
      <div ref={spatial} className="cn-mission-spatial" aria-label="地图与日程画布" onScroll={(event) => setLayer(event.currentTarget.scrollLeft > event.currentTarget.clientWidth / 2 ? "timeline" : "map")}>
        <article className="cn-mission-card cn-mission-map cn-mission-map-pane" data-testid="rev-mission-map-pane">
          <div className="cn-mission-map-top"><div className="cn-mission-section-heading"><MapPinned size={18} /><strong>现实地图</strong></div><span>{mapPoints.length} 处地点</span></div>
          {mapPoints.length ? <WorkspaceMap candidates={mapPoints} allowed={mapAllowed} onAllow={() => setMapAllowed(true)} onSelect={focusPlace} />
            : <div className="cn-mission-map-empty"><Navigation2 size={30} /><strong>地点研究会在这里汇合</strong><span>找到有坐标的地点后，点击图钉查看来源。</span></div>}
          <div className="cn-mission-map-footer"><button type="button" onClick={onExplore}>手动探索地点 <Compass size={15} /></button></div>
          <section className="cn-mission-activity" aria-label="Agent 工作轨迹">
            <div className="cn-mission-activity-top"><strong>Agent 工作轨迹</strong><button type="button" aria-label="刷新 Agent 实际任务" onClick={() => setRefresh((v) => v + 1)}><RefreshCw size={16} /></button></div>
            {task && <p className="cn-mission-run-stats">模型 {task.usage.model_turns ?? 0} 轮 · 工具 {task.usage.tool_calls ?? 0} 次</p>}
            {latestEvents.length ? <ol>{latestEvents.map((event) => <li key={event.sequence}><Clock3 size={14} /><div><strong>{eventLabel(event)}</strong><small>#{event.sequence}</small></div></li>)}</ol>
              : <p>{dataState === "loading" ? "正在读取工作记录…" : "提交目标后，这里显示实际工作进度。"}</p>}
          </section>
        </article>
        <article className="cn-mission-card cn-mission-timeline-pane" data-testid="rev-mission-timeline-pane">
          <div className="cn-mission-section-heading"><CalendarDays size={18} /><strong>{journeyStatus === "ACTIVE" ? "执行与待办" : "按天调整行程"}</strong></div>
          {journeyStatus === "ACTIVE" ? executionDecisions : <>
          <p>{draftSlots.length} 项安排 · {draftDays.length} 天</p>
          {task?.draft_artifact ? <GoalDraftEditor key={task.task_id} artifact={task.draft_artifact} disabled={task.status === "WORKING"}
            onSave={async (artifact) => {
              const bearer = readTravelerBearer(); const owner = readTravelerIdentity()?.travelerId;
              if (!bearer || !owner) throw new Error("请先登录这趟旅行。");
              const value = await cityNexusApi.updateGoalDraft(journeyId, task.task_id, artifact);
              if (bearer !== readTravelerBearer() || owner !== readTravelerIdentity()?.travelerId) throw new Error("登录已切换，请重新打开行程。");
              setTask(value); window.dispatchEvent(new Event("citynexus:mission-refresh"));
            }} /> : <p>Agent 会把暂定安排和待查事项逐步保存到这里。</p>}</>}
          <div className="cn-mission-capability-grid">
            <button type="button" onClick={onTrip}><Route size={18} /><strong>候选方案与出发</strong></button>
            <button type="button" onClick={onTrip}><ShieldCheck size={18} /><strong>行程守护</strong></button>
            <button type="button" onClick={onTrip}><Users size={18} /><strong>同行决策</strong></button>
          </div>
        </article>
      </div>
    </div>
  </section>;
}
