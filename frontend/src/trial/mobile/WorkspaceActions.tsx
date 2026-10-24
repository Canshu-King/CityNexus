import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cityNexusApi, type TravelPlanningInput, type BootstrapDiscoveryCandidate, type DraftGoalTask, type DraftGoalTaskEvent, type GoalResearchRoute } from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import { WorkspaceMap } from "./WorkspaceMap";
import { TravelGoalPreferences } from "./MobileAiPrompt";
import { GoalDraftEditor } from "./GoalDraftEditor";
import { isAreaGoalResearchLead, splitGoalResearch } from "./goalResearch";
import { humanDistance, humanDuration, isSafeAmapNavigationUrl } from "./departureGaps";
import type { GoalResearchLead } from "../../api/citynexus";
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

// PARTIAL_READY means "this turn stopped and the next word is the traveller's", not "there are results".
// Measured on the screen walk-76 left open: two model turns completed, no source was ever queried, the
// draft still had zero schedule lines, and the panel header read 旅行研究 · 已有阶段成果
// (trial/results/20261022_v3_human_chrome/research-head-before.txt:1).  A traveller who believes that
// headline will wait instead of acting, which is how a stalled Agent looks like progress.  The two
// counts below are the same fields the panel already draws, so nothing here is inferred.
function researchHeadline(task: DraftGoalTask): string {
  const label = TASK_STATUS[task.status] ?? task.status;
  if (task.status !== "PARTIAL_READY") return label;
  const slots = (task.draft_artifact?.days ?? []).reduce((count, day) => count + day.slots.length, 0);
  return (task.research_places ?? []).length || slots ? label : "这一轮还没有查到来源";
}
const TOOL_NAME: Record<string, string> = {
  ask_traveler: "与你商量安排", research_place_media: "查找地点照片",
  inspect_journey: "读取行程", read_guardian_stream: "查看行程守护记录", save_draft_variants: "比较旅行备选", search_city_services: "搜索城市地点",
  research_place_sources: "查找地点资料",
  discover_places: "查找公开地点", discover_nearby_places: "查找周边地点", save_draft_itinerary: "整理旅行草案",
  acquire_place_facts: "核实地点资料", estimate_place_facts: "估算备选安排",
  replace_draft_slots: "更新指定时段",
  generate_plans: "生成候选方案", compare_routes: "比较已有路线", route_public_places: "查询步行路线",
};
const EVENT_NAME: Record<string, string> = {
  TASK_ACCEPTED: "研究任务已建立",
  USER_MESSAGE_ADDED: "收到了你的新要求",
  RUN_STARTED: "本轮研究开始",
  MODEL_TURN_STARTED: "AI 正在判断下一步",
  MODEL_TURN_COMPLETED: "AI 已完成这一轮分析",
  TOOL_STARTED: "开始调用工具",
  TOOL_SUCCEEDED: "工具返回结果",
  TOOL_COMPLETED: "工具返回结果",
  TOOL_FAILED: "工具未完成",
  TASK_DRAFT_UPDATED: "你的修改已保存",
  TASK_PARTIAL_READY: "已交付阶段成果",
  TASK_RESUMABLE: "这轮研究结束，可继续",
  TASK_NEEDS_DECISION: "等待你决定",
  MODEL_FAILED: "模型请求失败，可保留现有草案",
  RUN_INTERRUPTED: "运行已中断，可恢复",
};
function eventSummary(event: DraftGoalTaskEvent): string {
  const prefix = EVENT_NAME[event.event_type] ?? "任务状态已更新";
  const tool = event.tool_name ? ` · ${TOOL_NAME[event.tool_name] ?? event.tool_name}` : "";
  const turn = event.model_turn_no ? ` · 第${event.model_turn_no}轮` : "";
  const reason = event.reason_code === "MODEL_BUDGET_EXHAUSTED" ? " · 本次研究预算用完"
    : event.reason_code === "RESEARCH_INCOMPLETE" ? " · 继续核实资料"
    : event.reason_code === "NO_RESULTS" ? " · 暂无匹配地点，需换研究方法"
    : event.reason_code === "PHOTON_UNAVAILABLE" ? " · 公开地点服务暂不可用" : "";
  return prefix + tool + turn + reason;
}
async function loadGoalEvents(journeyId: string, taskId: string): Promise<{ task_id: string; events: DraftGoalTaskEvent[] }> {
  const events: DraftGoalTaskEvent[] = [];
  let cursor = 0;
  for (let page = 0; page < 12; page++) {
    const result = await cityNexusApi.getDraftGoalTaskEvents(journeyId, taskId, cursor);
    if (result.task_id !== taskId) throw new Error("Goal task event identity mismatch");
    events.push(...result.events);
    if (result.next_cursor === null || result.next_cursor <= cursor) break;
    cursor = result.next_cursor;
  }
  return { task_id: taskId, events: events.slice(-100) };
}
const TASK_POINTER = "citynexus.revolution.goal-task";


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
  const route = result.route && typeof result.route === "object" ? result.route as Record<string, unknown> : null;
  if (route && typeof route.distance_m === "number" && Number.isFinite(route.distance_m) && route.distance_m >= 0
    && typeof route.duration_seconds === "number" && Number.isFinite(route.duration_seconds) && route.duration_seconds >= 0) {
    // The row says which door answered it, so the panel says the same thing back.  Naming every route a
    // walk is how a 180-minute bus ride from 八达岭长城 appeared as footsteps.  The drawer below uses the
    // same two readers, so a segment never reads as "52185 米" in one place and "52.2 公里" in another.
    return `${route.mode === "TRANSIT" ? "公共交通路线" : "步行路线"} · ${humanDistance(route.distance_m)} · ${humanDuration(route.duration_seconds)}`;
  }
  if (result.status === "CACHED_ONLY") return Array.isArray(result.cached_references) && result.cached_references.length
    ? `已读取 ${result.cached_references.length} 条已有地点来源` : "已读取已有地点资料";
  const provider = result.provider === "nominatim" ? "Nominatim" : result.provider === "photon" ? "Photon" : "公开地点来源";
  if (result.status === "NO_RESULTS" || result.reason_code === "NO_RESULTS") return `${provider} 未找到匹配地点，Agent 可更换关键词或来源`;
  if (result.status === "PROVIDER_UNAVAILABLE" || result.reason_code === "PHOTON_UNAVAILABLE" || result.reason_code === "NOMINATIM_UNAVAILABLE") return `${provider} 暂不可用，已有成果已保留`;
  if (typeof result.draft_revision === "number") return "旅行草案已保存";
  if (typeof result.candidate_count === "number") return `${result.candidate_count} 份候选方案`;
  if (result.status === "NO_STORED_ROUTE_FACTS") return "这两站还没有路线资料";
  if (typeof result.option_count === "number") return `${result.option_count} 条已有路线`;
  if (result.status === "ESTIMATED_AGENT") return "已保存备选估算";
  if (typeof result.place_count === "number") return `${result.place_count} 处地点${typeof result.area_count === "number" && result.area_count > 0 ? ` · ${result.area_count} 处地区线索` : ""}`;
  if (Array.isArray(result.observation_ids)) return `${result.observation_ids.length} 条来源记录`;
  return result.status === "COMPLETED" ? "完成" : "这一步暂未完成";
}

const AMAP_MARKER_URL = /^https:\/\/uri\.amap\.com\/marker(?:\?.*)?$/;
const ADMIN_ADDRESS_KEYS = ["province", "city", "district", "county", "township", "town"] as const;

function shortAdministrativeAddress(address?: Record<string, string>): string {
  if (!address) return "";
  return [...new Set(ADMIN_ADDRESS_KEYS.map((key) => typeof address[key] === "string" ? address[key].trim() : "").filter(Boolean))]
    .slice(0, 3).join(" · ");
}

function isAmapLead(place: GoalResearchLead): boolean {
  return typeof place.provider === "string" && place.provider.toLowerCase() === "amap";
}

function frozenHopLine(route: GoalResearchRoute): string | null {
  // A hop the traveller's own walking limit moved onto a bus: the row stays what the walking door
  // measured, and this line says what this version of the plan froze instead.  Both halves are one
  // sentence each because the two outcomes are different -- transport answered, or it did not.
  const cap = typeof route.walking_cap_m === "number" && route.walking_cap_m > 0 ? route.walking_cap_m : null;
  if (cap === null) return null;
  const capText = `${(cap / 1000).toFixed(cap % 1000 ? 1 : 0)} 公里`;
  if (route.frozen_mode === "TRANSIT" && route.mode !== "TRANSIT") {
    const when = typeof route.frozen_minutes === "number" ? ` · ${humanDuration(route.frozen_minutes * 60)}` : "";
    const lines = (route.frozen_lines ?? []).slice(0, 2).join(" · ");
    return `超过你写的${capText}，这版按公共交通核实${typeof route.frozen_distance_m === "number"
      ? ` ${humanDistance(route.frozen_distance_m)}${when}` : ""}${lines ? `（${lines}）` : ""}`;
  }
  return route.frozen_mode === "WALK" ? `超过你写的${capText}，公共交通没有答案，这版仍按步行核实` : null;
}

function ResearchRoutes({ items }: { items: GoalResearchRoute[] }) {
  const routes = items.filter((route) => route.provider === "amap" && route.coordinate_system === "GCJ02"
    && typeof route.id === "string" && !!route.id && typeof route.from_place_id === "string" && !!route.from_place_id
    && typeof route.to_place_id === "string" && !!route.to_place_id
    && typeof route.from_name === "string" && !!route.from_name.trim()
    && typeof route.to_name === "string" && !!route.to_name.trim()
    && Number.isFinite(route.distance_m) && route.distance_m >= 0
    && Number.isFinite(route.duration_seconds) && route.duration_seconds >= 0
    && isSafeAmapNavigationUrl(route.source_url, route.mode));
  if (!routes.length) return null;
  return <details className="rev-agent-research-drawer"><summary>高德转场路线（{routes.length}）</summary>
    <ul className="rev-workspace-task-places">{routes.map((route) => <li key={route.id} data-testid="rev-amap-research-route">
      <strong>{route.from_name} → {route.to_name}</strong>
      <span title={`${route.distance_m} 米 · ${route.duration_seconds} 秒`}>{route.mode === "TRANSIT" ? "公共交通" : "步行"} · {humanDistance(route.distance_m)} · {humanDuration(route.duration_seconds)}</span>
      {route.mode === "TRANSIT" && (route.lines ?? []).length > 0
        && <small data-testid="rev-amap-research-lines">{route.lines!.slice(0, 3).join(" · ")}</small>}
      {frozenHopLine(route) && <small data-testid="rev-amap-research-frozen">{frozenHopLine(route)}</small>}
      <a href={route.source_url} target="_blank" rel="noopener noreferrer">在高德地图查看路线 ↗</a>
    </li>)}</ul>
  </details>;
}

function ResearchLeads({ items, area = false }: { items: GoalResearchLead[]; area?: boolean }) {
  return <ul className="rev-workspace-task-places">{items.map((place) => <li key={place.id}>
    <strong>{place.name}</strong><span>{area || isAreaGoalResearchLead(place) ? "地区／村落线索" : "营业、费用待查"}</span>
    {isAmapLead(place)
      ? shortAdministrativeAddress(place.public_address) && <small>{shortAdministrativeAddress(place.public_address)}</small>
      : place.public_address && <small>{[...new Set(Object.values(place.public_address))].join(" · ")}</small>}
    {place.region_status === "UNKNOWN" && <small>地区归属待核实</small>}
    {/^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/[0-9]+$/.test(place.source_url) &&
      <a href={place.source_url} target="_blank" rel="noreferrer">查看地点来源 ↗</a>}
    {isAmapLead(place) && AMAP_MARKER_URL.test(place.source_url) &&
      <a href={place.source_url} target="_blank" rel="noopener noreferrer">在高德地图打开 ↗</a>}
  </li>)}</ul>;
}

/**
 * The model writes its answer as markdown, and this screen has no markdown renderer: 「**待核查项**」
 * and 「- Day1 上午…」 used to land as literal asterisks and dashes inside one long paragraph. The
 * words are the Agent's and stay untouched — only the line structure is read.
 */
function AgentMessageBody({ text }: { text: string }) {
  const lines = text.split("\n").map((raw) => {
    const trimmed = raw.trim();
    return { item: /^[-*]\s+/.test(trimmed), text: trimmed.replace(/^[-*]\s+/, "").replace(/\*+/g, "").trim() };
  }).filter((line) => line.text.length > 0);
  return <div className="rev-agent-message-body">
    {lines.map((line, index) => <p className={line.item ? "is-item" : undefined} key={index}>{line.text}</p>)}
  </div>;
}

/**
 * Whether this reply actually moved the schedule, read off the two revisions the server stored with
 * it. A sentence can say anything; the version numbers come from the draft on disk, so "已改" that
 * did not write shows up as 没有改动日程 instead of being believed.
 */
function draftReceipt(item: { draft_revision_before?: number | null; draft_revision_after?: number | null }) {
  const before = item.draft_revision_before;
  const after = item.draft_revision_after;
  if (typeof after !== "number") return null;
  if (typeof before !== "number") return "这一轮保存了第一版日程（版本 " + after + "）";
  if (after === before) return "这条回复没有改动日程（版本 " + after + "）";
  return "日程：版本 " + before + " → " + after;
}

export function WorkspaceActions({ panel, goalRequest, onClose, embedded = false, chatDockVisible = false, dialogueActive = true, onBrowseFound, onTaskChange }: { panel: WorkspacePanel;
  goalRequest?: { journeyId: string; goal: string } | null; onClose: () => void;
  embedded?: boolean; chatDockVisible?: boolean; dialogueActive?: boolean; onBrowseFound?: () => void;
  onTaskChange?: (task: DraftGoalTask, events: DraftGoalTaskEvent[]) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const [revision, setRevision] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [goalTaskSnapshot, setGoalTaskSnapshot] = useState<GoalTaskSnapshot | null>(null);
  const [question, setQuestion] = useState("");
  const seededGoal = useRef("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [modelConsent, setModelConsent] = useState(false);
  const [onlineResearchConsent, setOnlineResearchConsent] = useState(false);
  const composer = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const node = composer.current; if (!node) return;
    node.style.height = "auto";
    node.style.height = Math.min(132, Math.max(48, node.scrollHeight)) + "px";
    node.style.overflowY = node.scrollHeight > 132 ? "auto" : "hidden";
  }, [question]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [aiReady, setAiReady] = useState(false);
  const [allowTiles, setAllowTiles] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsButton = useRef<HTMLButtonElement>(null);
  const previousContext = useRef<Context | null>(null);
  const generation = useRef(0);
  const writeBusy = useRef(false);
  const followupMessageId = useRef<string | null>(null);
  const postController = useRef<AbortController | null>(null);
  const context = readContext();
  const visible = snapshot && sameContext(snapshot.context, context) ? snapshot : null;
  const visibleTask = goalTaskSnapshot && sameContext(goalTaskSnapshot.context, context) ? goalTaskSnapshot.value : null;
  const visibleEvents = goalTaskSnapshot && sameContext(goalTaskSnapshot.context, context) ? goalTaskSnapshot.events : [];
  const resumableTask = Boolean(visibleTask && ["RESUMABLE", "FAILED_RECOVERABLE"].includes(visibleTask.status));
  const conversationAnchor = useRef<HTMLDivElement>(null);
  const lastMessageId = visibleTask?.conversation?.at(-1)?.message_id;
  useEffect(() => {
    if (!chatDockVisible || !dialogueActive || !lastMessageId) return;
    const frame = requestAnimationFrame(() => {
      const anchor = conversationAnchor.current;
      if (anchor?.getClientRects().length) anchor.scrollIntoView({ block: "end", behavior: "instant" });
    });
    return () => cancelAnimationFrame(frame);
  }, [chatDockVisible, dialogueActive, lastMessageId, visibleTask?.pending_question?.id]);
  const research = splitGoalResearch(visibleTask);
  useEffect(() => {
    if (embedded && goalTaskSnapshot && sameContext(goalTaskSnapshot.context, readContext())) {
      onTaskChange?.(goalTaskSnapshot.value, goalTaskSnapshot.events);
    }
  }, [embedded, goalTaskSnapshot, onTaskChange]);
  useEffect(() => {
    if (!embedded) return;
    const refresh = () => setRevision((value) => value + 1);
    window.addEventListener("citynexus:mission-refresh", refresh);
    return () => window.removeEventListener("citynexus:mission-refresh", refresh);
  }, [embedded]);

  useEffect(() => {
    const invalidate = () => {
      generation.current += 1;
      postController.current?.abort();
      postController.current = null;
      writeBusy.current = false;
      setSnapshot(null); setGoalTaskSnapshot(null); setQuestion(""); setRequestError(null); followupMessageId.current = null;
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
      setQuestion(""); seededGoal.current = ""; setGoalTaskSnapshot(null); setBusy(false); setRequestError(null);
      setModelConsent(false); setOnlineResearchConsent(false); setAllowTiles(false); setAiReady(false);
    }
    let cancelled = false;
    setLoading(true); setLoadError(null);
    const taskId = readTaskPointer(actor);
    const taskRequest = taskId
      ? Promise.all([
        cityNexusApi.getDraftGoalTask(actor.id, taskId),
        loadGoalEvents(actor.id, taskId),
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
        const incomingGoal = savedTask?.[0]?.journey_id === actor.id ? "" : (input.intent?.goal ?? "").slice(0, 2000);
        const previousSeed = seededGoal.current;
        seededGoal.current = incomingGoal;
        setQuestion((value) => goalRequest?.journeyId === actor.id ? goalRequest.goal
          : !value.trim() || value === previousSeed ? incomingGoal : value);
        if (savedTask && savedTask[0].journey_id === actor.id) {
          setQuestion((value) => goalRequest?.journeyId === actor.id ? goalRequest.goal : value);
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
  }, [Boolean(panel), context?.id, context?.owner, context?.token, revision, goalRequest]);

  const refreshGoalTask = async (actor: Context, taskId: string) => {
    const [value, eventPage] = await Promise.all([
      cityNexusApi.getDraftGoalTask(actor.id, taskId),
      loadGoalEvents(actor.id, taskId),
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

  const startNewTask = async (interaction: "DISCUSS" | "RESEARCH" = "DISCUSS") => {
    const actor = readContext();
    if (!actor || !visible || !sameContext(actor, visible.context) || !aiReady || visible.status !== "DRAFT" || !modelConsent || writeBusy.current || question.trim().length < 1) return;
    const serial = ++generation.current;
    const controller = new AbortController();
    postController.current = controller;
    writeBusy.current = true; setBusy(true); setRequestError(null);
    const timer = window.setTimeout(() => controller.abort(), 180000);
    try {
      const created = await cityNexusApi.createDraftGoalTask(actor.id, {
        goal: question.trim(), model_consent: modelConsent,
        online_research_consent: onlineResearchConsent,
        interaction_mode: interaction, unlimited_research: true,
      }, controller.signal);
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      saveTaskPointer(actor, created.task_id);
      setQuestion("");
      setGoalTaskSnapshot({ context: actor, value: created, events: [] });
      const result = await cityNexusApi.runDraftGoalTask(actor.id, created.task_id, {
        model_consent: modelConsent, online_research_consent: onlineResearchConsent,
        interaction_mode: interaction, unlimited_research: true,
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
    const timer = window.setTimeout(() => controller.abort(), 180000);
    try {
      const result = await cityNexusApi.runDraftGoalTask(actor.id, task.task_id, {
        model_consent: modelConsent, online_research_consent: onlineResearchConsent,
        interaction_mode: "RESEARCH", unlimited_research: true,
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

  const sendFollowup = async (reply?: string, interaction: "DISCUSS" | "RESEARCH" = "DISCUSS") => {
    const actor = readContext();
    const task = visibleTask;
    const message = (reply ?? question).trim();
    if (!actor || !task || !modelConsent || !aiReady || writeBusy.current || task.status === "WORKING"
        || task.status === "CANCELLED" || message.length < 1) return;
    const serial = ++generation.current;
    const controller = new AbortController();
    postController.current = controller;
    writeBusy.current = true; setBusy(true); setRequestError(null);
    const messageId = followupMessageId.current ?? crypto.randomUUID();
    followupMessageId.current = messageId;
    const timer = window.setTimeout(() => controller.abort(), 180000);
    try {
      const result = await cityNexusApi.runDraftGoalTask(actor.id, task.task_id, {
        model_consent: modelConsent, online_research_consent: onlineResearchConsent,
        interaction_mode: interaction, unlimited_research: true,
        user_message: message, message_id: messageId,
      }, true, controller.signal);
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      // Only clear after server acknowledgement. The same message ID is reused after an
      // unknown response so a retry cannot secretly start duplicate research.
      setQuestion(""); followupMessageId.current = null;
      setGoalTaskSnapshot({ context: actor, value: result, events: [] });
      await refreshGoalTask(actor, task.task_id);
    } catch (error) {
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      setRequestError(error instanceof Error && error.name === "AbortError"
        ? "消息还在确认中，刷新任务查看最新进度。"
        : error instanceof Error && error.message.includes("GOAL_TASK_ALREADY_RUNNING")
          ? "Agent 正在处理上一条指令，等这轮结束后可以继续发消息。"
          : error instanceof Error ? error.message : "当前消息没有确认成功，请检查任务状态。");
    } finally {
      window.clearTimeout(timer);
      if (serial === generation.current) { postController.current = null; writeBusy.current = false; setBusy(false); }
    }
  };

  const sendMessage = () => {
    window.dispatchEvent(new CustomEvent("citynexus:mission-panel", { detail: "assistant" }));
    if (visibleTask && visibleTask.status !== "CANCELLED") void sendFollowup();
    else void startNewTask();
  };

  // The two per-trip permissions decide whether 发送 can do anything, so until they are granted they
  // sit with the button they unlock: behind the ⚙ glyph a first-time traveller presses 发送, sees
  // nothing happen and has no way to know the screen is waiting for a tick. Once both are granted the
  // same rows move into 对话设置, where they stay revocable without crowding the composer.
  const bothGranted = modelConsent && onlineResearchConsent;
  const consentRows = (
    <div className="rev-mission-chat-consent" data-testid="rev-mission-consent-strip">
      <label className="rev-workspace-consent"><input type="checkbox" checked={modelConsent} disabled={busy} onChange={(event) => setModelConsent(event.target.checked)} />本次允许 AI 处理旅行目标（可能产生费用）</label>
      <label className="rev-workspace-consent"><input type="checkbox" checked={onlineResearchConsent} disabled={busy} onChange={(event) => setOnlineResearchConsent(event.target.checked)} />本次允许查询公开地图和地点来源</label>
    </div>
  );

  const permissionSettings = (
    <details className="rev-agent-research-settings" open={embedded || !visibleTask}>
            <summary>加上时间与偏好</summary>
            <div className="rev-agent-research-settings-body">
              {bothGranted ? consentRows : null}
              <TravelGoalPreferences value={question} busy={busy} onChange={(value) => { followupMessageId.current = null; setQuestion(value); }} />

            </div>
          </details>
  );

  const taskMapPoints = (visibleTask?.research_places ?? []).filter((place) => place.region_status !== "CONFLICT").map((place) => ({
    candidate_id: place.id, name: place.name, latitude: place.latitude, longitude: place.longitude,
    coordinate_system: place.coordinate_system ?? (isAmapLead(place) ? "GCJ02" as const : "WGS84" as const),
    provider: place.provider, provider_object_id: place.provider_object_id, adcode: place.adcode, public_address: place.public_address,
    provider_provenance: place.provider_provenance, region_status: place.region_status,
    selection_state: "OPENING_UNVERIFIED" as const, source_url: place.source_url, observation_expired: false,
  }));
  const conversation = visibleTask?.conversation?.length
    ? visibleTask.conversation
    : visibleTask ? [{ role: "user" as const, text: visibleTask.goal, message_id: "initial", at: visibleTask.created_at ?? "" }] : [];
  const activeTools = visibleEvents.filter((event) => event.event_type === "TOOL_STARTED" &&
    !(visibleTask?.tool_steps ?? []).some((step) => step.run_id === event.run_id && step.sequence_no === event.step_sequence_no));

  const content = <>
    {!embedded && <header className="rev-workspace-top"><h2 id="rev-workspace-heading">{panel === "map" ? COPY.map : COPY.assistant}</h2>
      <button type="button" onClick={onClose} aria-label={COPY.close}>×</button></header>}
    <div className="rev-workspace-body">
      {!context && <p>{COPY.none}</p>}
      {loading && !visible && <p role="status">{COPY.load}</p>}
      {loadError && <p role="alert">{loadError}</p>}
      {context && <button type="button" className="rev-workspace-secondary" disabled={loading} onClick={() => {
        const actor = readContext();
        if (actor && visibleTask) void refreshGoalTask(actor, visibleTask.task_id).catch(() => undefined);
        setRevision((value) => value + 1);
      }}>{COPY.reload}</button>}
      {visible && panel === "map" && <WorkspaceMap candidates={[...visible.mapCandidates.filter((candidate) =>
        candidate.region_status !== "CONFLICT" && candidate.selection_state !== "REGION_CONFLICT"), ...taskMapPoints]} allowed={allowTiles} onAllow={() => setAllowTiles(true)} />}
      {visible && panel === "assistant" && <>
        <p>{visible.input.trip.dates.length} 天 · {visible.input.trip.party_size} 人 · 旅行需求已从服务器读取</p>
        {!aiReady && <p role="status">AI 尚未连接。</p>}
        {visible.status !== "DRAFT" ? <p>行程已经开始，可以在今日行程里向执行助手提出调整。</p> : <>
          {conversation.length > 0 && <div className="rev-agent-conversation" role="log" aria-label="与 Agent 的真实对话">
            {conversation.map((item) => <div className={"rev-agent-message is-" + item.role} key={item.message_id}>
              <span>{item.role === "user" ? "你" : "CityNexus Agent"}</span>
              <AgentMessageBody text={item.text} />
              {item.role === "assistant" && draftReceipt(item) && <small className="rev-agent-message-receipt">{draftReceipt(item)}</small>}
            </div>)}
            {visibleTask && !conversation.some((item) => item.role === "assistant") &&
              (visibleTask.draft_artifact?.days ?? []).some((day) => day.slots.length > 0) &&
              <div className="rev-agent-message is-status">
                <span>已保存的研究成果 · 来自服务器，不是模型回复</span>
                <p>当前有 {visibleTask.draft_artifact?.days.length} 天暂定日程，
                  {(visibleTask.draft_artifact?.days ?? []).reduce((count, day) => count + day.slots.length, 0)} 项安排。
                  你可以在下方直接告诉 Agent 下一步想修改什么。</p>
              </div>}
          </div>}
          {visibleTask?.pending_question && <section className="rev-agent-choices" aria-label="Agent 请你选择">
            {!conversation.some(item => item.message_id === visibleTask.pending_question?.id) && <h3>{visibleTask.pending_question.question}</h3>}
            {visibleTask.pending_question.options.map(option => <button key={option.label} type="button" disabled={busy}
              onClick={() => { followupMessageId.current = null; void sendFollowup(option.label); }}>
              <strong>{option.label}</strong><span>{option.description}</span>
            </button>)}
            <small>也可以在下方直接说你的想法。</small>
          </section>}
          {visibleTask && visibleTask.status !== "WORKING" && visibleTask.status !== "CANCELLED" &&
            <button type="button" className="rev-agent-start-research" disabled={busy || !modelConsent || !aiReady}
              onClick={() => { followupMessageId.current = null; void sendFollowup(question.trim() || "按我们讨论的方向开始研究，遇到重要取舍先给我选择。", "RESEARCH"); }}>
              按讨论的方向开始研究
            </button>}
          <div ref={conversationAnchor} style={{ height: 1, scrollMarginBottom: 180 }} />
          {!embedded && !bothGranted && consentRows}
          {!embedded && permissionSettings}
          {!embedded && <form className="rev-agent-nonmodal-form" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
            <label htmlFor="rev-workspace-question">{visibleTask ? "继续和这位 Agent 说话" : COPY.question}</label>
            <textarea id="rev-workspace-question" rows={3} maxLength={2000} value={question}
              disabled={busy} onChange={(event) => { followupMessageId.current = null; setQuestion(event.target.value); }}
              placeholder={visibleTask ? "例如：把第二天下午换成轻松的自然景点，保留其他安排。" : "直接描述你的旅行目标。"} />
            <button type="submit" disabled={!aiReady || busy || !modelConsent || question.trim().length < 1 || visibleTask?.status === "WORKING"}>
              {busy ? COPY.sending : visibleTask && visibleTask.status !== "CANCELLED" ? "发送并继续这趟旅行" : "发送给 Agent"}
            </button>
          </form>}
        </>}
        {requestError && <p role="alert">{requestError}</p>}
        {visibleTask && <section aria-label="Agent 任务" className="rev-workspace-answer">
          <h3>旅行研究 · {researchHeadline(visibleTask)}</h3>

          {visibleTask.assistant_summary && <details><summary>本轮研究摘要</summary><p>{visibleTask.assistant_summary}</p></details>}
          {visibleTask.failure_code && !["TRAVELER_INPUT_REQUIRED", "MODEL_BUDGET_EXHAUSTED", "TOOL_BUDGET_EXHAUSTED"].includes(visibleTask.failure_code) && <p>这次有一部分还没完成，你可以继续告诉我想怎么调整。</p>}

          {activeTools.map((event) => <p role="status" key={event.sequence}>{TOOL_NAME[event.tool_name ?? ""] ?? "处理当前任务"}…</p>)}
          {visibleEvents.length > 0 && <details className="rev-workspace-timeline" open={!embedded}>
            <summary>Agent 真实工作过程 · 已记录 {visibleEvents.length} 条事件</summary>
            <p>按时间显示模型轮次、工具结果和恢复进度。</p>
            <ol aria-label="Agent 运行事件">
              {visibleEvents.slice(-24).map((event) => <li key={event.sequence}>
                <span className="rev-workspace-event-sequence">#{event.sequence}</span>
                <span>{eventSummary(event)}</span>
              </li>)}
            </ol>
            {visibleEvents.length > 24 && <p>这里只显示最新 24 条；完整事件仍在同一任务的服务端记录中。</p>}
          </details>}
          {(visibleTask.tool_steps ?? []).length > 0 && <details open={!embedded}><summary>工具结果 · {visibleTask.tool_steps?.length} 次</summary><ol className="rev-workspace-task-steps">
            {(visibleTask.tool_steps ?? []).map((step) => <li key={`${step.run_id}-${step.sequence_no}`}>
              <strong>{TOOL_NAME[step.tool_name] ?? step.tool_name}</strong>
              {typeof step.result.public_action === "string" && <span>{step.result.public_action}</span>}
              <span>{step.tool_name === "inspect_journey" && step.status === "COMPLETED" ? "行程已读取" : taskStepText(step.result)}</span>
              {typeof step.result.elapsed_ms === "number" && <small>{(step.result.elapsed_ms / 1000).toFixed(1)} 秒</small>}
            </li>)}
          </ol></details>}
          {visibleTask.research_routes?.length ? <ResearchRoutes items={visibleTask.research_routes} /> : null}
          {(visibleTask.candidate_places ?? []).length > 0 && <details className="rev-agent-research-drawer"><summary>已核对的正式地点（{visibleTask.candidate_places?.length}）</summary><ul className="rev-workspace-task-places">
            {visibleTask.candidate_places?.map((place) => <li key={place.id}>
              <strong>{place.name}</strong><span>{place.opening_state === "KNOWN" ? "营业资料已读取" : "营业待核实"}</span>
              <span>{place.cost_evidence.status === "KNOWN" ? "费用资料已读取" : "费用待核实"}</span>
            </li>)}
          </ul></details>}
          {research.places.length > 0 && <details className="rev-agent-research-drawer"><summary>公开来源发现的地点（{research.places.length}）</summary><ResearchLeads items={research.places} /></details>}
          {research.areas.length > 0 && <details><summary>地区／村落线索（{research.areas.length}）</summary><ResearchLeads items={research.areas} area /></details>}
          {research.unknown.length > 0 && <details><summary>待核实来源（{research.unknown.length}）</summary><ResearchLeads items={research.unknown} /></details>}
          {research.conflicts.length > 0 && <details><summary>其他地区候选（{research.conflicts.length}）</summary><ResearchLeads items={research.conflicts} /></details>}
          {!embedded && visibleTask.draft_artifact && <GoalDraftEditor key={visibleTask.task_id} artifact={visibleTask.draft_artifact}
            disabled={busy || visibleTask.status === "WORKING"} onSave={async (artifact) => {
              const actor = readContext();
              if (!actor) throw new Error("当前登录身份已失效，无法保存，请重新登录。");
              const value = await cityNexusApi.updateGoalDraft(actor.id, visibleTask.task_id, artifact);
              if (!sameContext(actor, readContext())) throw new Error("身份已切换，检查新的登录后再保存。");
              setGoalTaskSnapshot((previous) => previous && sameContext(previous.context, actor)
                ? { ...previous, value } : previous);
              // Saved response is authoritative; optional event refresh failure is not a failed save.
              void refreshGoalTask(actor, value.task_id).catch(() => undefined);
            }} />}
          {visibleTask.status === "WORKING" && <button type="button" className="rev-workspace-secondary" onClick={() => void cancelTask()}>取消任务</button>}
          {resumableTask &&
            <button type="button" disabled={!aiReady || busy || !modelConsent} onClick={() => void resumeTask()}>继续研究</button>}

        </section>}
      </>}
    </div>
  </>;
  if (embedded) return <>
    <section className="rev-workspace-dialog rev-workspace-inline" aria-label="Agent 命令台">{content}</section>
    {chatDockVisible && visible?.status === "DRAFT" && createPortal(
      <form className="rev-mission-chat-dock" aria-label="与当前旅行 Agent 对话"
        onSubmit={(event) => { event.preventDefault(); sendMessage(); }}
        onKeyDown={(event) => {
          if (event.key === "Escape" && settingsOpen) { setSettingsOpen(false); settingsButton.current?.focus(); }
        }}>
        <button ref={settingsButton} type="button" className="rev-mission-settings-toggle" aria-label="对话设置"
          aria-expanded={settingsOpen} aria-controls="rev-mission-settings" onClick={() => setSettingsOpen(value => !value)}>⚙</button>
        <label htmlFor="rev-mission-chat-input">{visibleTask ? "继续和当前 Agent 对话" : "告诉 CityNexus 你的旅行目标"}</label>
        {bothGranted ? null : consentRows}
        <div className="rev-mission-chat-row">
          <textarea ref={composer} id="rev-mission-chat-input" value={question} rows={Math.min(4, Math.max(1, question.split("\n").length))} maxLength={2000}
            disabled={busy} onChange={(event) => { followupMessageId.current = null; setQuestion(event.target.value); }}
            placeholder="想怎么安排？先聊聊"/>
          <button type="submit" disabled={!aiReady || busy || !modelConsent || question.trim().length < 1 || visibleTask?.status === "WORKING"}>
            {busy ? "回复中…" : "发送 ↑"}
          </button>
        </div>
        <section id="rev-mission-settings" className="rev-mission-settings-panel" hidden={!settingsOpen} aria-label="对话设置">
          <header><strong>加上时间与偏好</strong><button type="button" aria-label="关闭对话设置"
            onClick={() => { setSettingsOpen(false); settingsButton.current?.focus(); }}>×</button></header>
          {permissionSettings}
        </section>
        {(busy || visibleTask?.status === "WORKING" || visibleTask?.status === "FAILED_RECOVERABLE" || requestError) && <p role="status" data-testid="rev-dock-status">{busy || visibleTask?.status === "WORKING"
          ? "Agent 正在处理，请稍后继续发消息。已有地图与日程仍可查看。"
          : (requestError || "Agent 上一轮没有答完，这次的服务暂时不可用。你可以再说一次，或先继续调整日程，等它能答时再问。")}</p>}
        {resumableTask && <div className="rev-mission-dock-recovery" data-testid="rev-dock-recovery">
          {/* A stalled round used to be recoverable only from the panel below the fold, so the fixed dock
              left the traveller a sentence with nothing to press. */}
          <button type="button" data-testid="rev-dock-retry-round" disabled={!aiReady || busy || !modelConsent}
            onClick={() => void resumeTask()}>重试这一轮</button>
          {onBrowseFound && <button type="button" data-testid="rev-dock-browse-found"
            onClick={() => onBrowseFound()}>先浏览已找到的地点</button>}
        </div>}
      </form>, document.body)}
  </>;
  return createPortal(<dialog ref={dialog} className="rev-workspace-dialog" aria-labelledby="rev-workspace-heading"
    onCancel={(event) => { event.preventDefault(); closeRef.current(); }}>{content}</dialog>, document.body);
}
