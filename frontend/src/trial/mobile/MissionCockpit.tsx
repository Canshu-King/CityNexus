import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowRight, ArrowUpRight, BrainCircuit, CalendarDays, CheckCircle2, Clock3,
  Compass, Layers3, MapPinned, MessageSquareText, Navigation2, RefreshCw,
  Route, ShieldCheck, Sparkles, Users, Wrench,
} from "lucide-react";
import {
  cityNexusApi, type DraftGoalTask, type DraftGoalTaskEvent,
} from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import { WorkspaceMap, type WorkspaceMapPoint } from "./WorkspaceMap";
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
  journeyId, cityName, goal, journeyStatus, agentStatus, agentAvailable, onExplore, onTrip,
}: Props) {
  const [command, setCommand] = useState(goal);
  const [task, setTask] = useState<DraftGoalTask | null>(null);
  const [events, setEvents] = useState<DraftGoalTaskEvent[]>([]);
  const [places, setPlaces] = useState<WorkspaceMapPoint[]>([]);
  const [dataState, setDataState] = useState<DataState>("loading");
  const [refresh, setRefresh] = useState(0);
  const [mapAllowed, setMapAllowed] = useState(false);
  const [identityTick, setIdentityTick] = useState(0);

  useEffect(() => { setCommand(goal); setMapAllowed(false); }, [journeyId]);
  useEffect(() => {
    if (!command.trim() && goal) setCommand(goal);
  }, [goal]);
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
  }, [places, task]);
  const draftDays = task?.draft_artifact?.days ?? [];
  const draftSlots = draftDays.flatMap((day) => day.slots.map((slot) => ({ date: day.date, ...slot })));
  const latestEvents = events.slice(-5).reverse();
  useEffect(() => {
    if (task?.status !== "WORKING") return;
    const timer = window.setInterval(() => setRefresh((value) => value + 1), 3000);
    return () => window.clearInterval(timer);
  }, [task?.status]);
  const status = journeyStatus === "ACTIVE" ? "行程执行中" : task ? statusCopy[task.status] ?? "任务已保存" : "等待第一个目标";

  const submitGoal = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (command.trim().length >= 4) openAgent(journeyId, command);
  };

  return (
    <section className="cn-mission-os" aria-label="CityNexus Mission 工作台" data-testid="rev-mission-cockpit">
      <div className="cn-mission-head">
        <div>
          <div className="cn-mission-kicker"><Sparkles size={15} aria-hidden="true" /> CITYNEXUS / MISSION OS</div>
          <h2>你的旅行，<span>交给 Agent 推进。</span></h2>
          <p>一个目标，统一调度研究、地图、日程与实际行程。不需要先完成一串准备页面。</p>
        </div>
        <div className="cn-mission-state" aria-live="polite">
          <span className="cn-mission-state-dot" aria-hidden="true" />
          {status}
        </div>
      </div>

      <div className="cn-mission-grid">
        <div className="cn-mission-left">
          <form className="cn-mission-composer" onSubmit={submitGoal}>
            <div className="cn-mission-section-heading"><BrainCircuit size={18} aria-hidden="true" /><strong>交给 CityNexus</strong></div>
            <label htmlFor="cn-mission-command">想去哪里，或者想改变什么？</label>
            <textarea id="cn-mission-command" value={command} onChange={(event) => setCommand(event.target.value)}
              maxLength={2000} rows={4}
              placeholder="例如：帮我找到福建的古村落和当地小吃，做两天轻松的行程。找不到就继续换办法。" />
            <div className="cn-mission-composer-actions">
              <span>{agentStatus}</span>
              <button type="submit" disabled={command.trim().length < 4}>
                <Sparkles size={16} aria-hidden="true" /> {agentAvailable ? "交给 Agent" : "打开任务助手"}
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            </div>
            <small>打开当前受签名的任务助手。开始模型和公开研究前，在助手内确认本次授权。</small>
          </form>

          <article className="cn-mission-card cn-mission-plan">
            <div className="cn-mission-section-heading"><CalendarDays size={18} aria-hidden="true" /><strong>正在形成的行程</strong></div>
            <div className="cn-mission-plan-metric">
              <strong>{draftSlots.length}</strong><span>项已保存安排</span>
              <span className="cn-mission-mini-dot" aria-hidden="true" /><strong>{draftDays.length}</strong><span>天草案</span>
            </div>
            {draftSlots.length ? (
              <ol>
                {draftSlots.slice(0, 3).map((slot, index) => <li key={slot.date + ":" + index}>
                  <span className="cn-mission-stop-dot">{String(index + 1).padStart(2, "0")}</span>
                  <span><strong>{slot.title}</strong><small>{slot.date} · {slot.place_id ? "待确认来源与执行条件" : "暂定建议 / 待调查"}</small></span>
                </li>)}
              </ol>
            ) : <p>Agent 尚未保存日程。它可以先提交暂定安排，再逐项补全资料，不必等全部地点 READY。</p>}
            <button type="button" className="cn-mission-text-action" onClick={() => openAgent(journeyId, command.trim() || goal || cityName)}>
              进入草案与研究记录 <ArrowUpRight size={16} aria-hidden="true" />
            </button>
          </article>

          <div className="cn-mission-capability">
            <div className="cn-mission-section-heading"><Layers3 size={18} aria-hidden="true" /><strong>可调度的现实能力</strong></div>
            <div className="cn-mission-capability-grid">
              <button type="button" onClick={onExplore}><Compass size={20} aria-hidden="true" /><strong>地点与发现</strong><small>探索真实地点</small></button>
              <button type="button" onClick={onTrip}><Route size={20} aria-hidden="true" /><strong>日程与路线</strong><small>比较和调整方案</small></button>
              <button type="button" onClick={onTrip}><ShieldCheck size={20} aria-hidden="true" /><strong>Guardian</strong><small>行程守护与变化</small></button>
              <button type="button" onClick={onTrip}><Users size={20} aria-hidden="true" /><strong>多人协作</strong><small>成员决策与同行</small></button>
            </div>
            <p>这些是能力入口，不代表每个子 Agent 当前都在运行。实际工作以服务器事件为准。</p>
          </div>
        </div>

        <div className="cn-mission-right">
          <article className="cn-mission-card cn-mission-map">
            <div className="cn-mission-map-top">
              <div className="cn-mission-section-heading"><MapPinned size={18} aria-hidden="true" /><strong>现实地图</strong></div>
              <span>{mapPoints.length} 处有坐标的地点</span>
            </div>
            {mapPoints.length ? (
              <WorkspaceMap candidates={mapPoints} allowed={mapAllowed} onAllow={() => setMapAllowed(true)} />
            ) : (
              <div className="cn-mission-map-empty">
                <Navigation2 size={30} aria-hidden="true" />
                <strong>地图等待真实地点</strong>
                <span>Agent 找到带坐标的公开地点后，这里直接出现图钉。不会编造位置。</span>
              </div>
            )}
            <div className="cn-mission-map-footer">
              <span>公开地理资料和私人行程分别按原权限读取</span>
              <button type="button" onClick={() => window.dispatchEvent(new Event("citynexus:open-map-workspace"))}>
                展开地图 <ArrowUpRight size={15} aria-hidden="true" />
              </button>
            </div>
          </article>

          <article className="cn-mission-card cn-mission-activity">
            <div className="cn-mission-activity-top">
              <div className="cn-mission-section-heading"><Wrench size={18} aria-hidden="true" /><strong>Agent 工作轨迹</strong></div>
              <button type="button" aria-label="刷新 Agent 实际任务" onClick={() => setRefresh((value) => value + 1)}>
                <RefreshCw size={17} aria-hidden="true" />
              </button>
            </div>
            {task && <div className="cn-mission-run-stats">
              <span><BrainCircuit size={14} aria-hidden="true" /> 模型 {task.usage.model_turns ?? 0} 轮</span>
              <span><Wrench size={14} aria-hidden="true" /> 工具 {task.usage.tool_calls ?? 0} 次</span>
              <span><CheckCircle2 size={14} aria-hidden="true" /> 事件 {events.length} 条</span>
            </div>}
            {latestEvents.length ? (
              <ol>
                {latestEvents.map((event) => <li key={event.sequence}>
                  <span className="cn-mission-event-mark"><Clock3 size={13} aria-hidden="true" /></span>
                  <div><strong>{eventLabel(event)}</strong><small>事件 #{event.sequence} · 当前任务的真实服务器记录</small></div>
                </li>)}
              </ol>
            ) : <div className="cn-mission-activity-empty">
              <MessageSquareText size={21} aria-hidden="true" />
              <span>{dataState === "loading" ? "正在读取实际工作记录…" : dataState === "unavailable" ? "登录状态不可用，无法读取任务。" : "还没有当前任务的工作事件。提交目标后会显示工具调用与结果。"}</span>
            </div>}
            <button type="button" className="cn-mission-text-action" onClick={() => openAgent(journeyId, command.trim() || goal || cityName)}>
              查看完整过程及继续研究 <ArrowRight size={16} aria-hidden="true" />
            </button>
          </article>
        </div>
      </div>
    </section>
  );
}
