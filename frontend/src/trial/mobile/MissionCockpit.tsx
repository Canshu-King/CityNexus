import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  BrainCircuit, CalendarDays, Clock3, Compass, MapPinned, Navigation2, RefreshCw,
  Route, ShieldCheck, Sparkles, Users,
} from "lucide-react";
import {
  cityNexusApi, CityNexusApiError, type DraftGoalTask, type DraftGoalTaskEvent, type GoalDraftArtifact,
} from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import { WorkspaceMap, type WorkspaceMapPoint } from "./WorkspaceMap";
import { WorkspaceActions } from "./WorkspaceActions";
import { GoalDraftEditor } from "./GoalDraftEditor";
import { DraftDepartureCard } from "./DraftDepartureCard";
import { GoalDraftVariants } from "./GoalDraftVariants";
import { GuardianRealityPanel } from "./GuardianRealityPanel";
import { DestinationMedia } from "./DestinationMedia";
import { PlacePhotoGallery } from "./PlacePhotoGallery";
import { useSourcePlaceMedia } from "./useSourcePlaceMedia";
import { isAreaGoalResearchLead, splitGoalResearch } from "./goalResearch";
import "./MissionCockpit.css";

type Props = {
  journeyId: string;
  cityName: string;
  goal: string;
  journeyStatus: string;
  visible?: boolean;
  agentStatus: string;
  agentAvailable: boolean;
  onExplore: () => void;
  onTrip: () => void;
  onChangeCity?: () => void;
  space?: "explore" | "journey";
  preparation?: (fromAgentDraft: boolean) => ReactNode;
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
  read_guardian_stream: "查看行程守护记录",
  discover_places: "检索公开地点",
  discover_nearby_places: "检索附近地点",
  search_city_services: "查询城市服务",
  research_place_sources: "调查地点来源",
  research_place_media: "查找地点照片",
  acquire_place_facts: "核实地点事实",
  estimate_place_facts: "准备参考估算",
  compare_routes: "比较已保存路线",
  route_public_places: "查询步行路线",
  save_draft_itinerary: "整理多日草案",
  replace_draft_slots: "更新指定时段",
};
const eventCopy: Record<string, string> = {
  RUN_STARTED: "Agent 已开始工作",
  USER_MESSAGE_ADDED: "已收到用户的新要求",
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
  journeyId, cityName, goal, journeyStatus, visible = true, space = "explore", preparation, agentStatus, agentAvailable, onExplore, onTrip, onChangeCity, executionAgent, executionDecisions,
}: Props) {
  const [command, setCommand] = useState(goal);
  const [task, setTask] = useState<DraftGoalTask | null>(null);
  const [events, setEvents] = useState<DraftGoalTaskEvent[]>([]);
  const [places, setPlaces] = useState<WorkspaceMapPoint[]>([]);
  const [dataState, setDataState] = useState<DataState>("loading");
  const [accessLost, setAccessLost] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [mapAllowed, setMapAllowed] = useState(false);
  const [identityTick, setIdentityTick] = useState(0);
  const [commandRevision, setCommandRevision] = useState(0);
  const [showAllResearch, setShowAllResearch] = useState(false);
  const [guardianOpen, setGuardianOpen] = useState(false);
  const [focusedPlaceId, setFocusedPlaceId] = useState<string | null>(null);
  const [chosenDraftRevision, setChosenDraftRevision] = useState(0);
  const spatial = useRef<HTMLDivElement>(null);
  const [layer, setLayer] = useState<"map" | "timeline" | "agent">(journeyStatus === "ACTIVE" ? "agent" : "map");
  useEffect(() => { setLayer(space === "journey" || journeyStatus === "ACTIVE" ? "timeline" : "map"); }, [space, journeyStatus]);
  const selectLayer = (next: "map" | "timeline" | "agent") => {
    setLayer(next);
    // Phone panels remain mounted so switching never discards draft edits.
    requestAnimationFrame(() => {
      document.querySelector(".cn-mission-layer-tabs")?.scrollIntoView({ block: "start", behavior: "auto" });
    });
  };
  const goalRequest = useMemo(() => commandRevision ? ({ journeyId, goal: command }) : null, [journeyId, command, commandRevision]);
  const receiveTask = useCallback((value: DraftGoalTask, items: DraftGoalTaskEvent[]) => {
    if (value.journey_id !== journeyId) return;
    setTask(value); setEvents(items); setDataState("ready");
  }, [journeyId]);
  const focusPlace = useCallback((id: string, preferMap = false) => {
    setFocusedPlaceId(id);
    const slot = document.querySelector<HTMLDetailsElement>(`.cn-mission-os .rev-goal-draft-slot[data-place-id="${CSS.escape(id)}"]`);
    if (slot && !preferMap) {
      slot.open = true;
      window.dispatchEvent(new CustomEvent("citynexus:draft-focus", { detail: id }));
      setLayer("timeline");
      requestAnimationFrame(() => slot.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" }));
    } else {
      setLayer("map");
      requestAnimationFrame(() => document.querySelector('.cn-mission-map-pane [aria-label="当前行程地图"]')?.scrollIntoView({ block: "center", behavior: "auto" }));
    }
  }, []);
  useEffect(() => {
    const focus = (event: Event) => {
      const value = (event as CustomEvent).detail;
      if (value?.journeyId && value.journeyId !== journeyId) return;
      if (typeof value?.goal === "string" && value.goal.trim()) { setCommand(value.goal.slice(0, 2000)); setCommandRevision((v) => v + 1); }
      (document.getElementById("rev-mission-chat-input") as HTMLTextAreaElement | null)?.focus();
    };
    const openPanel = (event: Event) => {

      const kind = (event as CustomEvent).detail;
      if (kind === "map" || kind === "assistant" || kind === "timeline") setLayer(kind === "assistant" ? "agent" : kind);
    };
    window.addEventListener("citynexus:mission-command", focus);
    window.addEventListener("citynexus:mission-panel", openPanel);
    return () => { window.removeEventListener("citynexus:mission-command", focus); window.removeEventListener("citynexus:mission-panel", openPanel); };
  }, [journeyId]);

  useEffect(() => { setCommand(goal); setMapAllowed(false); setGuardianOpen(false); setFocusedPlaceId(null); }, [journeyId]);
  useEffect(() => {
    if (goal && goal !== command) { setCommand(goal); setCommandRevision(value => value + 1); }
  }, [goal]);
  useEffect(() => {
    const refreshWorkspace = () => setRefresh((value) => value + 1);
    window.addEventListener("citynexus:mission-refresh", refreshWorkspace);
    return () => window.removeEventListener("citynexus:mission-refresh", refreshWorkspace);
  }, []);
  useEffect(() => subscribeTravelerBearer(() => {
    setTask(null); setEvents([]); setPlaces([]); setMapAllowed(false); setFocusedPlaceId(null);
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
    // A credential that has run out is not the same fact as "this traveller has no places yet", and
    // the screen used to show them identically: measured 2026-10-22, an expired bearer made both reads
    // answer http_status=401 while the cockpit still said 「地点研究会在这里汇合」 and 「提交目标后，这里显示
    // 实际工作进度」 -- an empty app to a person who had a full trip minutes earlier.
    let refused = false;
    const noteRefused = (error: unknown) => {
      if (error instanceof CityNexusApiError && (error.status === 401 || error.status === 403)) refused = true;
      return null;
    };
    setAccessLost(false);
    // This local pointer only locates a task. Both reads are authorized by the server.
    const pointer = localStorage.getItem(TASK_POINTER + "." + owner + "." + journeyId);
    const readTask = pointer ? cityNexusApi.getDraftGoalTask(journeyId, pointer).catch(noteRefused) : Promise.resolve(null);
    const readEvents = pointer ? cityNexusApi.getDraftGoalTaskEvents(journeyId, pointer).catch(noteRefused) : Promise.resolve(null);
    void Promise.all([
      cityNexusApi.getJourneyMapPlaces(journeyId).catch(noteRefused), readTask, readEvents,
    ]).then(([map, savedTask, eventPage]) => {
      if (disposed || bearer !== readTravelerBearer() || owner !== readTravelerIdentity()?.travelerId) return;
      setAccessLost(refused);
      const ownedTask = savedTask?.journey_id === journeyId ? savedTask : null;
      setTask(ownedTask);
      setEvents(ownedTask && eventPage?.task_id === ownedTask.task_id && Array.isArray(eventPage.events)
        ? eventPage.events : []);
      setPlaces(map?.journey_id === journeyId && Array.isArray(map.candidates) ? map.candidates : []);
      setDataState(map || ownedTask ? "ready" : "partial");
    }).catch(() => { if (!disposed) setDataState("unavailable"); });
    return () => { disposed = true; };
  }, [journeyId, refresh, identityTick]);

  const research = splitGoalResearch(task);
  const researchFingerprint = JSON.stringify([research.places, research.areas, research.unknown, research.conflicts]);
  const allMapPoints = useMemo<WorkspaceMapPoint[]>(() => {
    const results = new Map<string, WorkspaceMapPoint>();
    for (const point of places) if (point.region_status !== "CONFLICT" && point.selection_state !== "REGION_CONFLICT") results.set(point.candidate_id, point);
    for (const point of [...research.places, ...research.areas, ...research.unknown]) {
      if (point.region_status === "CONFLICT") continue;
      if (point.provider_provenance === "UNVERIFIED") continue;
      results.set(point.id, {
        candidate_id: point.id,
        name: point.name,
        latitude: point.latitude,
        longitude: point.longitude,
        coordinate_system: point.coordinate_system ?? (typeof point.provider === "string" && point.provider.toLowerCase() === "amap" ? "GCJ02" : "WGS84"),
        provider: point.provider,
        provider_object_id: point.provider_object_id,
        adcode: point.adcode,
        public_address: point.public_address,
        provider_provenance: point.provider_provenance,
        selection_state: "OPENING_UNVERIFIED",
        source_url: point.source_url,
        observation_expired: false,
        region_status: point.region_status,
        kind: isAreaGoalResearchLead(point) ? "area" : "place",
      });
    }
    return [...results.values()];
  }, [places, researchFingerprint]);
  const draftDays = task?.draft_artifact?.days ?? [];
  const draftSlots = draftDays.flatMap((day) => day.slots.map((slot) => ({ date: day.date, ...slot })));
  const draftPlaceIds = new Set(draftSlots.map((slot) => slot.place_id).filter(Boolean));
  const draftPlaceFingerprint = [...draftPlaceIds].sort().join("|");
  const itineraryMapPoints = useMemo(() => allMapPoints.filter((point) => draftPlaceIds.has(point.candidate_id)
    && point.region_status !== "CONFLICT" && point.selection_state !== "REGION_CONFLICT"), [allMapPoints, draftPlaceFingerprint]);
  const defaultMapIds = new Set([...places.map((point) => point.candidate_id), ...research.places.map((point) => point.id),
    ...research.areas.map((point) => point.id), ...[...research.places, ...research.areas, ...research.unknown]
      .filter((point) => draftPlaceIds.has(point.id)).map((point) => point.id)]);
  const defaultMapPoints = allMapPoints.filter((point) => defaultMapIds.has(point.candidate_id));
  const focusedMapCount = itineraryMapPoints.length || defaultMapPoints.length;
  const visibleMapPoints = showAllResearch ? allMapPoints : itineraryMapPoints.length ? itineraryMapPoints : defaultMapPoints;
  const selectedResearch = allMapPoints.find(point => point.candidate_id === focusedPlaceId);
  const mapPoints = selectedResearch && !visibleMapPoints.some(point => point.candidate_id === focusedPlaceId)
    ? [...visibleMapPoints, selectedResearch] : visibleMapPoints;
  const photoPriorityIds = new Set([...draftPlaceIds, ...(task?.draft_variants ?? []).flatMap(variant => variant.source_place_ids)] as string[]);
  const mediaById = useSourcePlaceMedia(journeyId, task?.task_id, Boolean(task?.consent.online_research),
    allMapPoints, new Set([...(task?.research_places ?? []), ...(task?.research_areas ?? [])].map(place => place.id)), photoPriorityIds, focusedPlaceId);
  const coverPoint = allMapPoints.find(point => photoPriorityIds.has(point.candidate_id)
    && mediaById[point.candidate_id]?.media?.can_show);
  const coverMedia = coverPoint ? mediaById[coverPoint.candidate_id].media : undefined;
  const latestEvents = events.slice(-5).reverse();
  useEffect(() => {
    if (task?.status !== "WORKING") return;
    const timer = window.setInterval(() => setRefresh((value) => value + 1), 3000);
    return () => window.clearInterval(timer);
  }, [task?.status]);
  const status = journeyStatus === "ACTIVE" ? "行程执行中" : task ? statusCopy[task.status] ?? "任务已保存" : accessLost ? "登录已过期" : "等待第一个目标";

  const chooseDraft = async (artifact: GoalDraftArtifact) => {
    const bearer = readTravelerBearer(); const owner = readTravelerIdentity()?.travelerId;
    if (!bearer || !owner || !task) throw new Error("请先登录这趟旅行。");
    const value = await cityNexusApi.updateGoalDraft(journeyId, task.task_id,
      { ...artifact, revision: task.draft_artifact?.revision ?? 0 });
    if (bearer !== readTravelerBearer() || owner !== readTravelerIdentity()?.travelerId) throw new Error("登录已切换。");
    setTask(value); setChosenDraftRevision((revision) => revision + 1);
    window.dispatchEvent(new Event("citynexus:mission-refresh"));
  };

  return <section className="cn-mission-os" aria-label="CityNexus Mission 工作台" data-testid="rev-mission-cockpit" data-layer={layer} data-space={space}>
    <header className="cn-mission-head">
      <div><div className="cn-mission-kicker"><Sparkles size={15} /> YOUR NEXT JOURNEY</div>
        <h2 aria-label={cityName}>{cityName}<span>{journeyStatus === "ACTIVE" ? "旅途正在继续。" : "把想去变成出发。"}</span></h2><p>{journeyStatus === "ACTIVE" ? "下一站、行程变化和同行决定，都在这里。" : draftSlots.length ? `已有 ${draftDays.length} 天安排，随时可以和 Agent 一起调整。` : "先聊聊你想怎样旅行，再一起找值得去的地方。"}</p>
        {onChangeCity && <button type="button" className="cn-mission-change-city" onClick={onChangeCity}>换地区 ›</button>}</div>
      <DestinationMedia key={cityName + (coverMedia?.image_url || "")} cityName={cityName} media={coverMedia} placeName={coverPoint?.name} />
      <span className="cn-mission-state" aria-live="polite">{status}</span>
    </header>
    <div className="cn-mission-layer-tabs" aria-label="切换工作台图层">
      <button type="button" aria-pressed={layer === "map"} onClick={() => selectLayer("map")} data-testid="rev-mission-layer-map"><MapPinned size={17} />地图</button>
      <button type="button" aria-pressed={layer === "timeline"} onClick={() => selectLayer("timeline")} data-testid="rev-mission-layer-timeline"><CalendarDays size={17} />{journeyStatus === "ACTIVE" ? "执行与待办" : "日程"}</button>
      {journeyStatus !== "ACTIVE" && <button type="button" aria-pressed={layer === "agent"} onClick={() => selectLayer("agent")} data-testid="rev-mission-layer-agent"><BrainCircuit size={17} />对话</button>}
    </div>
    <div className="cn-mission-grid">
      <div className="cn-mission-agent-pane" data-testid="rev-mission-agent-pane">
        <div className="cn-mission-section-heading"><BrainCircuit size={18} /><strong>你的旅行搭档</strong></div>
        <div className="cn-mission-agent-glance" aria-live="polite">
          <span>{status}</span>
          <strong>{draftSlots.length
            ? `已整理 ${draftDays.length} 天 · ${draftSlots.length} 项安排`
            : journeyStatus === "ACTIVE" ? "你的行程正在执行" : "告诉我想去哪儿，其余交给 Agent"}</strong>
          <p>{task ? "地点、地图、日程都会随研究更新。用屏幕底部的输入框继续调整。" : "无需填写复杂表单，直接说出目的地、兴趣和偏好。"}</p>
        </div>
        {journeyStatus === "ACTIVE" ? <p>当前行程的助手动态在「执行与待办」里。</p> :
          <div className="cn-mission-agent-disclosure">
            <h3>一起商量安排</h3>
            <WorkspaceActions embedded chatDockVisible={true} dialogueActive={layer === "agent"} panel="assistant" goalRequest={goalRequest} onClose={() => undefined} onBrowseFound={() => selectLayer("map")} onTaskChange={receiveTask} />
          </div>}
      </div>
      <div ref={spatial} className="cn-mission-spatial" aria-label="地图与日程画布">
        <article className="cn-mission-card cn-mission-map cn-mission-map-pane" data-testid="rev-mission-map-pane">
          <div className="cn-mission-map-top"><div className="cn-mission-section-heading"><MapPinned size={18} /><strong>现实地图</strong></div><span>{mapPoints.length} 处地点</span></div>
          {allMapPoints.length > focusedMapCount && <button type="button" className="cn-mission-map-scope" onClick={() => setShowAllResearch((value) => !value)}>
            {showAllResearch ? "收起其他研究" : `查看其他研究（${allMapPoints.length - mapPoints.length}）`}
          </button>}
          <PlacePhotoGallery cityName={cityName} places={allMapPoints} mediaById={mediaById} priorityIds={photoPriorityIds} selectedId={focusedPlaceId} scheduledIds={draftPlaceIds} onSelect={focusPlace} />
          {selectedResearch && <p role="status">正在查看：{selectedResearch.name}{draftPlaceIds.has(selectedResearch.candidate_id) ? " · 已排入日程" : " · 尚未排入日程"}</p>}
          {mapPoints.length ? <WorkspaceMap candidates={mapPoints} allowed={mapAllowed} onAllow={() => setMapAllowed(true)} onSelect={focusPlace} selectedId={focusedPlaceId} />
            : <div className="cn-mission-map-empty"><Navigation2 size={30} /><strong>{accessLost ? "这次登录已经过期" : "地点研究会在这里汇合"}</strong><span>{accessLost ? "这趟行程还在，只是这台设备当前读不到它。" : "找到有坐标的地点后，点击图钉查看来源。"}</span></div>}
          <div className="cn-mission-map-footer"><button type="button" onClick={onExplore}>手动探索地点 <Compass size={15} /></button></div>
          <details className="cn-mission-activity" aria-label="Agent 工作轨迹"><summary>查看 Agent 工作过程</summary>
            <div className="cn-mission-activity-top"><strong>Agent 工作轨迹</strong><button type="button" aria-label="刷新 Agent 实际任务" onClick={() => setRefresh((v) => v + 1)}><RefreshCw size={16} /></button></div>
            {task && <p className="cn-mission-run-stats">模型 {task.usage.model_turns ?? 0} 轮 · 工具 {task.usage.tool_calls ?? 0} 次</p>}
            {latestEvents.length ? <ol>{latestEvents.map((event) => <li key={event.sequence}><Clock3 size={14} /><div><strong>{eventLabel(event)}</strong><small>#{event.sequence}</small></div></li>)}</ol>
              : <p>{accessLost ? "这次登录已经过期，读不到工作记录。" : dataState === "loading" ? "正在读取工作记录…" : "提交目标后，这里显示实际工作进度。"}</p>}
          </details>
        </article>
        <article className="cn-mission-card cn-mission-timeline-pane" data-testid="rev-mission-timeline-pane">
          <div className="cn-mission-section-heading"><CalendarDays size={18} /><strong>{journeyStatus === "ACTIVE" ? "执行与待办" : "按天调整行程"}</strong></div>
          {journeyStatus === "ACTIVE" ? <>{executionAgent}{executionDecisions}</> : <>
          <p>{draftSlots.length} 项安排 · {draftDays.length} 天</p>
          <GoalDraftVariants key={task?.task_id ?? journeyId} variants={task?.draft_variants ?? []} current={task?.draft_artifact}
            disabled={task?.status === "WORKING"} onChoose={chooseDraft} />
          {task?.draft_artifact ? <GoalDraftEditor key={task.task_id + ":" + chosenDraftRevision} artifact={task.draft_artifact} disabled={task.status === "WORKING"}
            mediaById={mediaById} onPlaceSelect={id => focusPlace(id, true)}
            onSave={async (artifact) => {
              const bearer = readTravelerBearer(); const owner = readTravelerIdentity()?.travelerId;
              if (!bearer || !owner) throw new Error("请先登录这趟旅行。");
              const value = await cityNexusApi.updateGoalDraft(journeyId, task.task_id, artifact);
              if (bearer !== readTravelerBearer() || owner !== readTravelerIdentity()?.travelerId) throw new Error("登录已切换，请重新打开行程。");
              setTask(value); window.dispatchEvent(new Event("citynexus:mission-refresh"));
            }} /> : <p>Agent 会把暂定安排和待查事项逐步保存到这里。</p>}</>}
          {space === "journey" && <details open className="cn-v3-preparation" data-testid="rev-v3-preparation"><summary>准备出发 · 正式计划与待办</summary>{task && <DraftDepartureCard task={task} onDiscuss={(value) => openAgent(journeyId, value)} />}{preparation?.(draftSlots.length > 0)}</details>}
          <div className="cn-mission-capability-grid">
            <button type="button" onClick={onTrip}><Route size={18} /><strong>准备出发</strong></button>
            <button type="button" aria-expanded={guardianOpen} onClick={() => setGuardianOpen((value) => !value)}><ShieldCheck size={18} /><strong>行程守护</strong></button>
            <button type="button" onClick={onTrip}><Users size={18} /><strong>同行决策</strong></button>
          </div>
          <GuardianRealityPanel journeyId={journeyId} visible={visible && guardianOpen} active={journeyStatus === "ACTIVE"} />
        </article>
      </div>
    </div>
  </section>;
}
