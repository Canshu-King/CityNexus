import { useEffect, useRef, useState } from "react";
import { BootstrapDiscoveryPanel } from "../features/discovery/BootstrapDiscoveryPanel";
import { RevolutionQuickExplore } from "./RevolutionQuickExplore";
import { MobilePlanWorkbench } from "./mobile/MobilePlanWorkbench";
import { LiveRecovery } from "../features/execution/LiveRecovery";
import { cityNexusApi, type AgentRuntimeStatus, type BootstrapPocketWalkResponse, type SessionDraftJourney } from "../api/citynexus";
import { RevolutionMobileNav, type RevolutionMobileTab } from "./RevolutionMobileNav";
import { MissionCockpit } from "./mobile/MissionCockpit";
import { AgentWorkStatus } from "./mobile/AgentWorkStatus";
import { MobileHermesRun } from "./mobile/MobileHermesRun";
import { MobileCompatAgentActivity } from "./mobile/MobileCompatAgentActivity";
import { fetchWithReadDeadline, READ_DEADLINE_MS, ReadDeadlineMissed } from "../lib/readDeadline";
import {
  CLIENT_WRITE_DEADLINE_MS,
  CLIENT_WRITE_DEADLINE_SECONDS,
  fetchWithWriteDeadline,
  WriteDeadlineMissed,
} from "../lib/writeDeadline";
import {
  clearTravelerBearer,
  readTravelerBearer,
  readTravelerIdentity,
  storeTravelerIdentity,
  subscribeTravelerBearer,
} from "../lib/travelerSession";
import "./RevolutionFirstLook.css";
import "./RevolutionUsability.css";
import "./RevolutionQuickExplore.css";
import "./RevolutionMobileV1.css";
import "./mobile/RevolutionV3.css";

const STORAGE_KEY = "citynexus.revolution.firstlook.journey";
const RECENT_JOURNEYS_KEY = "citynexus.revolution.firstlook.recent-journeys";
const START_WRITE_STATUS_KEY = "citynexus.revolution.firstlook.start-write";

type TripPlanningMode = "balanced" | "budget" | "explore" | "strict_schedule";
type TripEnergy = "easy" | "steady" | "full";

const TRIP_INTERESTS = [
  { value: "local_food", label: "当地美食" },
  { value: "night_market", label: "夜市小吃" },
  { value: "old_town", label: "古城老街" },
  { value: "heritage", label: "人文古迹" },
  { value: "nature", label: "山野自然" },
  { value: "coast", label: "海边水岸" },
  { value: "architecture", label: "建筑文化" },
  { value: "nightlife", label: "夜间活动" },
  { value: "photography", label: "摄影打卡" },
  { value: "family", label: "亲子活动" },
  { value: "shopping", label: "逛街购物" },
  { value: "park/garden", label: "公园绿地" },
  { value: "cafe", label: "咖啡馆" },
  { value: "museum/gallery", label: "博物馆艺术" },
  { value: "library", label: "图书馆" },
] as const;

const TRIP_ENERGY_LABELS: Record<TripEnergy, string> = {
  easy: "轻松少走",
  steady: "适中节奏",
  full: "充实安排",
};

function localDateAfter(days: number): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDaysToDateInput(value: string, days: number): string {
  const [year, month, day] = value.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1, day + days));
  return `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, "0")}-${String(next.getUTCDate()).padStart(2, "0")}`;
}

function tripBriefGoal(goal: string, interests: string[], energy: TripEnergy): string {
  if (!goal.trim() && interests.length === 0) return "";
  const interestLabels = TRIP_INTERESTS
    .filter((item) => interests.includes(item.value))
    .map((item) => item.label);
  return [
    goal.trim(),
    interestLabels.length ? `兴趣：${interestLabels.join("、")}` : "",
    `节奏：${TRIP_ENERGY_LABELS[energy]}`,
  ].filter(Boolean).join("\n").slice(0, 360);
}

type StartWritePhase = "traveler" | "journey";
type StartWriteState = {
  phase: StartWritePhase;
  state: "pending" | "unknown" | "partial";
  reason?: "client-deadline" | "traveler-created" | "journey-created";
  receiptKey?: string;
  cityName: string;
  cityCode?: string;
};

function readStartWriteState(): StartWriteState | null {
  let raw: string | null;
  try {
    raw = localStorage.getItem(START_WRITE_STATUS_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<StartWriteState>;
    const phase: StartWritePhase = value.phase === "traveler" ? "traveler" : "journey";
    const cityName = typeof value.cityName === "string" && value.cityName.length <= 60
      ? value.cityName
      : "连城";
    const cityCode = typeof value.cityCode === "string" ? value.cityCode : undefined;
    const receiptKey = typeof value.receiptKey === "string" && /^[0-9a-f]{64}$/.test(value.receiptKey)
      ? value.receiptKey
      : undefined;
    const common = { cityName, ...(cityCode ? { cityCode } : {}), ...(receiptKey ? { receiptKey } : {}) };
    if (value.state === "partial" &&
        (value.reason === "traveler-created" || value.reason === "journey-created")) {
      return { phase, state: "partial", reason: value.reason, ...common };
    }
    // A pending marker left by reload or tab close has no confirmed outcome.
    return {
      phase,
      state: "unknown",
      ...(value.reason === "client-deadline" ? { reason: "client-deadline" as const } : {}),
      ...common,
    };
  } catch {
    // A malformed marker still means one of the writes may have been sent.
    return { phase: "journey", state: "unknown", cityName: "连城" };
  }
}

function persistStartWriteState(state: StartWriteState): boolean {
  try {
    localStorage.setItem(START_WRITE_STATUS_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

function clearStartWriteState(): void {
  try {
    localStorage.removeItem(START_WRITE_STATUS_KEY);
  } catch {
    // The in-memory lock still protects the current page.
  }
}

function createStartWriteReceiptKey(): string {
  const bytes = new Uint8Array(32);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function startWriteMessage(status: StartWriteState): string {
  if (status.state === "pending") {
    return status.phase === "traveler"
      ? "仍在创建登录会话，结果尚未确认。请勿重复提交。"
      : "仍在创建行程草稿，结果尚未确认。请勿重复提交。";
  }
  if (status.state === "partial" && status.reason === "traveler-created") {
    return "登录会话已创建，但行程未完成。原身份和输入已保留；请勿重新提交。";
  }
  if (status.state === "partial" && status.reason === "journey-created") {
    return "行程已创建，但页面未完成保存。原身份和输入已保留；请勿重新提交。";
  }
  if (status.reason === "client-deadline") {
    const write = status.phase === "traveler" ? "登录会话" : "行程草稿";
    return `${write}等待 ${CLIENT_WRITE_DEADLINE_SECONDS} 秒后停止，服务器结果未知。请勿重复提交。`;
  }
  return "这次写入结果未知。原身份和输入已保留；请勿重复提交。";
}

class StartWriteHttpError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`HTTP ${status}：服务器未能完成请求`);
    this.name = "StartWriteHttpError";
    this.status = status;
  }
}

function hasConfirmedWriteRejection(error: unknown): boolean {
  return error instanceof StartWriteHttpError && error.status >= 400 && error.status < 500 &&
    ![408, 409, 425, 429].includes(error.status);
}

async function readJsonBeforeWriteDeadline<T>(response: Response, path: string, deadlineAt: number): Promise<T> {
  const remainingMs = deadlineAt - performance.now();
  if (remainingMs <= 0) throw new WriteDeadlineMissed("POST", path, CLIENT_WRITE_DEADLINE_MS);
  let timer: number | undefined;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = window.setTimeout(
      () => reject(new WriteDeadlineMissed("POST", path, CLIENT_WRITE_DEADLINE_MS)),
      remainingMs,
    );
  });
  try {
    return await Promise.race([response.json() as Promise<T>, deadline]);
  } finally {
    if (timer !== undefined) window.clearTimeout(timer);
  }
}

async function readJsonBeforeReadDeadline<T>(response: Response, deadlineAt: number): Promise<T> {
  const remainingMs = deadlineAt - performance.now();
  if (remainingMs <= 0) throw new ReadDeadlineMissed(READ_DEADLINE_MS);
  let timer: number | undefined;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = window.setTimeout(() => reject(new ReadDeadlineMissed(READ_DEADLINE_MS)), remainingMs);
  });
  try {
    return await Promise.race([response.json() as Promise<T>, deadline]);
  } finally {
    if (timer !== undefined) window.clearTimeout(timer);
  }
}

type TrialJourney = {
  id: string;
  cityCode: string;
  cityName: string;
  status: "DRAFT" | "ACTIVE";
  ownerTravelerId: string;
};

type LocalJourneyPointer = Omit<TrialJourney, "ownerTravelerId"> & { ownerTravelerId?: string };

function readLegacyJourneyPointer(): LocalJourneyPointer | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const value = raw ? JSON.parse(raw) as unknown : null;
    if (!value || typeof value !== "object") return null;
    const record = value as Partial<LocalJourneyPointer>;
    if (typeof record.id !== "string" || typeof record.cityCode !== "string" ||
        typeof record.cityName !== "string") return null;
    return {
      id: record.id,
      cityCode: record.cityCode,
      cityName: record.cityName,
      status: record.status === "ACTIVE" ? "ACTIVE" : "DRAFT",
      ...(typeof record.ownerTravelerId === "string" ? { ownerTravelerId: record.ownerTravelerId } : {}),
    };
  } catch {
    return null;
  }
}

function parseJourneyPointer(value: unknown, travelerId: string): TrialJourney | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Partial<TrialJourney>;
  if (typeof record.id !== "string" || typeof record.cityCode !== "string" ||
      typeof record.cityName !== "string" || record.ownerTravelerId !== travelerId) return null;
  return {
    id: record.id,
    cityCode: record.cityCode,
    cityName: record.cityName,
    status: record.status === "ACTIVE" ? "ACTIVE" : "DRAFT",
    ownerTravelerId: travelerId,
  };
}

function loadRecentJourney(): TrialJourney | null {
  // A local pointer is shown only for the same signed session id. The server
  // still authorizes all private Journey reads from the bearer.
  const identity = readTravelerIdentity();
  if (!identity) return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return parseJourneyPointer(raw ? JSON.parse(raw) as unknown : null, identity.travelerId);
  } catch {
    return null;
  }
}

function loadRecentJourneys(): TrialJourney[] {
  const identity = readTravelerIdentity();
  if (!identity) return [];
  try {
    const raw = localStorage.getItem(RECENT_JOURNEYS_KEY);
    const values = raw ? JSON.parse(raw) as unknown : [];
    if (!Array.isArray(values)) return [];
    const current = loadRecentJourney();
    const parsed = values
      .map((value) => parseJourneyPointer(value, identity.travelerId))
      .filter((value): value is TrialJourney => value !== null);
    const combined = current ? [current, ...parsed] : parsed;
    return combined.filter((value, index) => combined.findIndex((item) => item.id === value.id) === index).slice(0, 8);
  } catch {
    return [];
  }
}

function rememberJourney(journey: TrialJourney): TrialJourney[] {
  const recent = [journey, ...loadRecentJourneys().filter((item) => item.id !== journey.id)].slice(0, 8);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(journey));
  localStorage.setItem(RECENT_JOURNEYS_KEY, JSON.stringify(recent));
  return recent;
}

async function postJson<T>(
  path: string,
  payload: object,
  bearerOverride: string | undefined,
  receiptKey: string,
): Promise<T> {
  // Use the fresh token for the new Journey without replacing the existing
  // browser session until the entire create flow has succeeded.
  const bearer = bearerOverride === undefined ? readTravelerBearer() : bearerOverride;
  const requestPath = "/api/v1" + path;
  const deadlineAt = performance.now() + CLIENT_WRITE_DEADLINE_MS;
  const response = await fetchWithWriteDeadline(requestPath, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": receiptKey,
      ...(bearer ? { Authorization: `Bearer ${bearer}` } : {}),
    },
    body: JSON.stringify(payload),
  }, CLIENT_WRITE_DEADLINE_MS);
  if (!response.ok) {
    throw new StartWriteHttpError(response.status);
  }
  return readJsonBeforeWriteDeadline<T>(response, requestPath, deadlineAt);
}

function freshCityCode(): string {
  // DRAFT codes are private application keys; the catalog resolver supplies canonical city identity.
  return "CN-RV-" + crypto.randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase();
}

function DraftAgentActivity({
  status,
  hasSelectedPlace,
  hasSavedPocketWalk,
}: {
  status: string;
  hasSelectedPlace: boolean;
  hasSavedPocketWalk: boolean;
}) {
  return (
    <section className="rev-mobile-panel" data-testid="rev-draft-agent-activity">
      <span className="rev-firstlook-eyebrow">AI 助手</span>
      <h2>AI 工作动态</h2>
      <div className="rev-mobile-account-line">
        <span>AI 服务</span><strong>{status}</strong>
      </div>
      <div className="rev-mobile-account-line">
        <span>本次行程</span><strong>暂无运行记录</strong>
      </div>
      <p>
        {hasSelectedPlace
          ? "已选地点。下一步：在上方确认正式行程。"
          : hasSavedPocketWalk
            ? "散步路线已保存。选定正式行程地点后，在上方确认行程。"
            : "选定真实地点后，在上方确认正式行程。"}
      </p>
      <p>正式行程开始且 AI 可用时，实际工作记录会显示在这里。</p>
    </section>
  );
}

const GOAL_CN_NUM: Record<string, number> = {
  一: 1,
  二: 2,
  两: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  七: 7,
  八: 8,
  九: 9,
  十: 10,
};

function readPartyFromGoal(text: string): number | null {
  const match = text.match(/([一二两三四五六七八九十\d]+)\s*(?:个)?人/);
  if (!match) return null;
  const raw = match[1];
  const value = /^\d+$/.test(raw) ? Number(raw) : GOAL_CN_NUM[raw];
  if (!value) return null;
  return Math.min(20, Math.max(1, value));
}

function readPerPersonBudgetFromGoal(text: string): number | null {
  const match = text.match(/(?:人均|每人|平均每人)[^\d]{0,4}(\d{2,6})/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

export function RevolutionFirstLook() {
  const [cityName, setCityName] = useState(() => readStartWriteState()?.cityName ?? "");
  const [startDate, setStartDate] = useState(() => localDateAfter(1));
  const [durationDays, setDurationDays] = useState(2);
  const [partySize, setPartySize] = useState(1);
  const [budgetYuan, setBudgetYuan] = useState("1000");
  const [planningMode, setPlanningMode] = useState<TripPlanningMode>("balanced");
  const [tripGoal, setTripGoal] = useState("");
  const partyEdited = useRef(false);
  const budgetEdited = useRef(false);
  const applyNumbersFromGoal = (text: string) => {
    const party = readPartyFromGoal(text);
    const perPerson = readPerPersonBudgetFromGoal(text);
    if (party !== null && !partyEdited.current) setPartySize(party);
    if (perPerson !== null && !budgetEdited.current) {
      const people = party ?? partySize;
      setBudgetYuan(String(perPerson * Math.max(1, people)));
    }
  };
  const [tripInterests, setTripInterests] = useState<string[]>([]);
  const [tripEnergy, setTripEnergy] = useState<TripEnergy>("easy");
  const [journey, setJourney] = useState<TrialJourney | null>(loadRecentJourney);
  // The trips the server says this traveller has, for the cases a locally kept pointer cannot
  // cover: a new device, a cleared browser, or the same person coming back a week later.  Until
  // this existed, 我的旅程 could only ever show a journey this very browser had opened, and a
  // traveller with a real saved trip was told to go and explore again.
  const [savedTrips, setSavedTrips] = useState<SessionDraftJourney[]>([]);
  const tripLookup = useRef(0);
  const [recentJourneys, setRecentJourneys] = useState<TrialJourney[]>(loadRecentJourneys);
  const [explorationTitle, setExplorationTitle] = useState<{ journeyId: string; label: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [startWriteStatus, setStartWriteStatus] = useState<StartWriteState | null>(readStartWriteState);
  const [startRecoveryIdentity, setStartRecoveryIdentity] = useState<{ bearer: string; travelerId: string } | null>(null);
  const [startRecoveryBusy, setStartRecoveryBusy] = useState(false);
  const [startRecoveryMessage, setStartRecoveryMessage] = useState<string | null>(null);
  const [receiptBusy, setReceiptBusy] = useState(false);
  const [receiptMessage, setReceiptMessage] = useState<string | null>(null);
  const startRequestInFlightRef = useRef(false);
  const startWriteBlockedRef = useRef(startWriteStatus !== null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [legacyRestoreFailed, setLegacyRestoreFailed] = useState(false);
  const [candidateForJourney, setCandidateForJourney] = useState<string | null>(null);
  const [briefBearer, setBriefBearer] = useState(readTravelerBearer);
  const [serverBrief, setServerBrief] = useState<{ journeyId: string; bearer: string; goal: string } | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<RevolutionMobileTab>(() => { try { const saved = sessionStorage.getItem("citynexus.revolution.v3.space"); return saved === "trips" || saved === "me" ? saved : "explore"; } catch { return "explore"; } });
  useEffect(() => { try { sessionStorage.setItem("citynexus.revolution.v3.space", activeTab); } catch { /* Navigation still works in memory. */ } }, [activeTab]);
  const [pocketWalk, setPocketWalk] = useState<BootstrapPocketWalkResponse | null>(null);
  const [agentRuntime, setAgentRuntime] = useState<AgentRuntimeStatus | null>(null);
  const [agentCheckError, setAgentCheckError] = useState<string | null>(null);
  const sample = import.meta.env.VITE_REV_TRIAL_MODE === "sample";
  const startWriteBlocked = startWriteStatus !== null;
  const canCheckCurrentStartDrafts = startWriteStatus?.phase === "journey" &&
    Boolean(startWriteStatus.cityCode && (startRecoveryIdentity?.bearer || readTravelerBearer()));

  // A local pointer is not proof that this session owns the Journey, so it never navigates and never
  // claims progress.  It only stops the trips panel from saying "you have nothing" while the device
  // still names a trip: measured 2026-10-22, localStorage held 北京's pointer, sessionStorage held no
  // bearer, and the panel told the traveller to go and start exploring.
  const deviceJourneyHint = briefBearer ? null : (readLegacyJourneyPointer()?.cityName ?? null);

  useEffect(() => subscribeTravelerBearer((token) => { setServerBrief(null); setBriefBearer(token); }), []);
  useEffect(() => {
    let cancelled = false;
    setServerBrief(null);
    if (journey && briefBearer) {
      void cityNexusApi.getTravelPlanningInput(journey.id).then((result) => {
        if (!cancelled && briefBearer === readTravelerBearer() && result.journey_id === journey.id && result.intent) {
          setServerBrief({ journeyId: journey.id, bearer: briefBearer,
            goal: tripBriefGoal(result.intent.goal, result.intent.interests, result.intent.energy) });
        }
      }).catch(() => { /* Existing services can still explore without a saved trip brief. */ });
    }
    return () => { cancelled = true; };
  }, [journey?.id, briefBearer]);

  useEffect(() => {
    let cancelled = false;
    void cityNexusApi.getAgentRuntimeStatus().then((state) => {
      if (!cancelled) setAgentRuntime(state);
    }).catch(() => {
      if (!cancelled) setAgentCheckError("无法读取后端 Agent 状态。");
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (readStartWriteState()) return;
    const bearer = readTravelerBearer();
    const pairedIdentity = readTravelerIdentity();
    const pointer = readLegacyJourneyPointer();
    if (!bearer || !pointer) return;
    if (pairedIdentity && pointer.ownerTravelerId === pairedIdentity.travelerId) return;

    let cancelled = false;
    void (async () => {
      try {
        const session = await cityNexusApi.getTravelerSession();
        if (!session.traveler_id || (pointer.ownerTravelerId && pointer.ownerTravelerId !== session.traveler_id)) {
          throw new Error("Journey owner does not match the signed traveler");
        }
        // A pointer is only a local navigation hint. The authenticated server
        // read proves the current signed traveler is a member before restoring it.
        await cityNexusApi.getBootstrapShortlist(pointer.id);
        if (cancelled || readTravelerBearer() !== bearer) return;
        const restored: TrialJourney = { ...pointer, ownerTravelerId: session.traveler_id };
        storeTravelerIdentity(bearer, session.traveler_id);
        setRecentJourneys(rememberJourney(restored));
        setJourney(restored);
        setCityName(restored.cityName);
        setLegacyRestoreFailed(false);
        setError(null);
      } catch {
        if (cancelled) return;
        setCityName(pointer.cityName);
        setLegacyRestoreFailed(true);
        setError("旧行程无法恢复，原记录仍保存在服务器。");
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const nativeHermesConfigured = agentRuntime?.runtime_identity === "HERMES_NATIVE_MCP"
    && agentRuntime.hermes_native_gateway?.configured === true;
  const nativeHermesReady = nativeHermesConfigured
    && agentRuntime?.hermes_native_gateway?.ready === true
    && agentRuntime.hermes_native_gateway.runs
    && agentRuntime.hermes_native_gateway.events;
  const agentConfigured = nativeHermesConfigured || (
    agentRuntime?.runtime_identity === "HERMES_COMPAT_ENDPOINT"
    && agentRuntime.hermes_compat_configured
  );
  const agentStatusChecking = !agentRuntime && !agentCheckError;
  const runtimeAiState = agentRuntime?.ai_state?.toUpperCase();
  const aiDisabled = runtimeAiState === "DISABLED" || runtimeAiState === "DISABLED_BY_OPS";
  const aiNotConfigured = runtimeAiState === "NOT_CONFIGURED";
  const agentCanRequestSuggestion = agentConfigured && !aiDisabled && !aiNotConfigured;
  const agentStatusTitle = agentStatusChecking
    ? "AI 正在连接"
    : agentCheckError
      ? "AI 暂时不可用"
      : aiDisabled
        ? "AI 暂未开启"
        : nativeHermesReady
          ? "AI 可用"
          : nativeHermesConfigured
            ? "AI 暂时没连上"
            : aiNotConfigured || !agentConfigured
              ? "AI 尚未连接"
              : runtimeAiState === "PROVIDER_REFUSED"
                ? "AI 暂时没响应"
                : "AI 建议可试";
  const agentStatusDetail = agentStatusChecking
    ? "正在准备 AI。"
    : agentCheckError
      ? "先继续挑地点。"
      : aiDisabled
        ? "先选好地点，再继续安排行程。"
        : nativeHermesReady
          ? "出发行程后可查看 AI 工作动态。"
          : nativeHermesConfigured
            ? "先继续挑地点。"
            : runtimeAiState === "PROVIDER_REFUSED"
              ? "先继续挑地点。"
              : agentCanRequestSuggestion
                ? "在底部告诉 Agent 你想怎么玩。"
                : "先开始探索。";

  const markStartWriteUnknown = (marker: StartWriteState, reason?: "client-deadline") => {
    const unknown: StartWriteState = {
      ...marker,
      state: "unknown",
      ...(reason ? { reason } : {}),
    };
    persistStartWriteState(unknown);
    startWriteBlockedRef.current = true;
    setStartWriteStatus(unknown);
    return unknown;
  };

  const clearStartWriteMarker = (receiptKey: string) => {
    const current = readStartWriteState();
    if (current?.receiptKey && current.receiptKey !== receiptKey) return;
    clearStartWriteState();
    setStartWriteStatus(null);
    startWriteBlockedRef.current = false;
  };

  const postStartWrite = async <T,>(
    phase: StartWritePhase,
    path: string,
    payload: object,
    bearerOverride: string | undefined,
    label: string,
    cityCode?: string,
  ): Promise<{ value: T; marker: StartWriteState }> => {
    const marker: StartWriteState = {
      phase,
      state: "pending",
      receiptKey: createStartWriteReceiptKey(),
      cityName: label,
      ...(cityCode ? { cityCode } : {}),
    };
    setReceiptMessage(null);
    setStartRecoveryMessage(null);
    if (!persistStartWriteState(marker) || readStartWriteState()?.receiptKey !== marker.receiptKey) {
      clearStartWriteState();
      setStartWriteStatus(null);
      startWriteBlockedRef.current = false;
      throw new Error("无法保存本次写入核验凭据，因此未发送请求。");
    }
    startWriteBlockedRef.current = true;
    setStartWriteStatus(marker);
    try {
      const value = await postJson<T>(path, payload, bearerOverride, marker.receiptKey!);
      return { value, marker };
    } catch (caught) {
      if (hasConfirmedWriteRejection(caught)) {
        clearStartWriteMarker(marker.receiptKey!);
      } else {
        markStartWriteUnknown(
          marker,
          caught instanceof WriteDeadlineMissed ? "client-deadline" : undefined,
        );
      }
      throw caught;
    }
  };

  const start = async (cityNameOverride?: string, options: { freshSession?: boolean } = {}) => {
    const savedWrite = readStartWriteState();
    if (startRequestInFlightRef.current || startWriteBlockedRef.current || savedWrite) {
      if (savedWrite) {
        startWriteBlockedRef.current = true;
        setStartWriteStatus(savedWrite);
      }
      return;
    }
    const label = (cityNameOverride ?? cityName).trim();
    if (label.length < 2 || label.length > 60) {
      setError("请输入 2 至 60 个字符的城市或地区名称，例如连城、厦门或杭州。");
      return;
    }
    const parsedBudget = Number(budgetYuan);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate) || startDate < localDateAfter(0)) {
      setError("请选择今天或之后的出发日期。");
      return;
    }
    if (!Number.isInteger(durationDays) || durationDays < 1 || durationDays > 14) {
      setError("游玩天数请选 1 至 14 天。");
      return;
    }
    if (!Number.isInteger(partySize) || partySize < 1 || partySize > 20) {
      setError("同行人数请填 1 至 20 人。");
      return;
    }
    if (!budgetYuan.trim() || !Number.isFinite(parsedBudget) || parsedBudget < 0 || parsedBudget > 10000000) {
      setError("预算请填 0 至 1000 万元之间的数字。");
      return;
    }
    const budgetMinor = Math.round(parsedBudget * 100);
    const initialGoal = tripBriefGoal(tripGoal, tripInterests, tripEnergy);
    startRequestInFlightRef.current = true;
    setBusy(true);
    setError(null);
    setNotice(null);
    setLegacyRestoreFailed(false);
    setStartRecoveryMessage(null);
    let writePostDispatched = false;
    let travelerCreatedThisAttempt = false;
    let travelerReceiptKey: string | undefined;
    let journeyCreatedThisAttempt = false;
    let journeyReceiptKey: string | undefined;
    let journeyCityCode: string | undefined;
    try {
      // Keep one signed traveler while the person starts Journeys in other
      // cities. A new traveler is issued only when this browser has no paired
      // signed session; both session fields commit after Journey creation.
      const existingBearer = options.freshSession ? null : readTravelerBearer();
      const existingIdentity = options.freshSession ? null : readTravelerIdentity();
      let traveler: { id: string; access_token?: string };
      if (existingBearer) {
        traveler = { id: (await cityNexusApi.getTravelerSession()).traveler_id, access_token: existingBearer };
      } else {
        writePostDispatched = true;
        const travelerResult = await postStartWrite<{ id: string; access_token?: string }>("traveler", "/travelers", {
          display_name: "Revolution Lab explorer",
          locale: "zh-CN",
          timezone: "Asia/Shanghai",
        }, "", label);
        traveler = travelerResult.value;
        travelerReceiptKey = travelerResult.marker.receiptKey;
        if (typeof traveler.id !== "string" || !traveler.id || typeof traveler.access_token !== "string" || !traveler.access_token) {
          markStartWriteUnknown(travelerResult.marker);
          throw new Error("服务器未能确认登录会话信息，请勿重复提交。");
        }
        travelerCreatedThisAttempt = true;
        clearStartWriteMarker(travelerResult.marker.receiptKey!);
      }
      if (!traveler.access_token) {
        throw new Error("服务器没有发放可用于私人探索的签名会话，请检查本地鉴权配置。");
      }
      setStartRecoveryIdentity({ bearer: traveler.access_token, travelerId: traveler.id });
      const startAt = `${startDate}T09:00:00+08:00`;
      const endDate = addDaysToDateInput(startDate, durationDays - 1);
      const endAt = `${endDate}T21:00:00+08:00`;
      journeyCityCode = freshCityCode();
      writePostDispatched = true;
      const journeyResult = await postStartWrite<{ id: string }>("journey", "/journeys", {
        traveler_id: traveler.id,
        title: label + ` · ${durationDays}日行程`,
        city_code: journeyCityCode,
        timezone: "Asia/Shanghai",
        start_at: startAt,
        end_at: endAt,
        budget: { amount_minor: budgetMinor, currency: "CNY" },
        planning_mode: planningMode,
        party_size: partySize,
        planning_intent: { goal: tripGoal.trim(), public_region_label: label, interests: tripInterests, energy: tripEnergy },
      }, traveler.access_token, label, journeyCityCode);
      journeyReceiptKey = journeyResult.marker.receiptKey;
      const created = journeyResult.value;
      if (typeof created.id !== "string" || !created.id) {
        markStartWriteUnknown(journeyResult.marker);
        throw new Error("服务器未能确认行程编号，请勿重复提交。");
      }
      journeyCreatedThisAttempt = true;
      if (!existingIdentity || existingIdentity.travelerId !== traveler.id) {
        storeTravelerIdentity(traveler.access_token, traveler.id);
      }
      const next: TrialJourney = {
        id: created.id,
        cityCode: journeyCityCode!,
        cityName: label,
        status: "DRAFT",
        ownerTravelerId: traveler.id,
      };
      setServerBrief({ journeyId: created.id, bearer: traveler.access_token, goal: initialGoal });
      setRecentJourneys(rememberJourney(next));
      setExplorationTitle(null);
      setJourney(next);
      setActiveTab("explore");
      setPocketWalk(null);
      setNotice("旅行目标已建立。Agent 可以接手研究，地图与日程会随着成果逐步更新。");
      clearStartWriteMarker(journeyResult.marker.receiptKey!);
      startWriteBlockedRef.current = false;
      setStartRecoveryIdentity(null);
    } catch (caught) {
      if (journeyCreatedThisAttempt || (!startWriteBlockedRef.current && travelerCreatedThisAttempt)) {
        const partial: StartWriteState = {
          phase: journeyCreatedThisAttempt ? "journey" : "traveler",
          state: "partial",
          reason: journeyCreatedThisAttempt ? "journey-created" : "traveler-created",
          receiptKey: journeyCreatedThisAttempt ? journeyReceiptKey : travelerReceiptKey,
          cityName: label,
          ...(journeyCityCode ? { cityCode: journeyCityCode } : {}),
        };
        persistStartWriteState(partial);
        startWriteBlockedRef.current = true;
        setStartWriteStatus(partial);
        setError(null);
      } else if (startWriteBlockedRef.current) {
        setError(null);
      } else {
        setError(caught instanceof Error ? caught.message : "创建探索草稿失败。");
        if (!writePostDispatched && readTravelerBearer()) setLegacyRestoreFailed(true);
      }
    } finally {
      setBusy(false);
      startRequestInFlightRef.current = false;
    }
  };

  const checkStartWriteReceipt = async () => {
    const marker = readStartWriteState();
    if (!marker?.receiptKey || !startWriteBlocked || receiptBusy) return;
    setReceiptBusy(true);
    setReceiptMessage(null);
    try {
      const deadlineAt = performance.now() + READ_DEADLINE_MS;
      const response = await fetchWithReadDeadline(
        `/api/v1/start-write-receipts/${marker.phase}`,
        {
          headers: {
            Accept: "application/json",
            "X-CityNexus-Write-Receipt-Key": marker.receiptKey,
          },
          cache: "no-store",
        },
        READ_DEADLINE_MS,
      );
      if (!response.ok) {
        setReceiptMessage("暂时无法读取这次写入回执。结果仍未知；原启动标记保留，请勿重复提交。");
        return;
      }
      const value: unknown = await readJsonBeforeReadDeadline(response, deadlineAt);
      const receipt = value && typeof value === "object" ? value as Record<string, unknown> : null;
      if (!receipt || receipt.operation !== marker.phase ||
          !["pending", "committed", "unknown"].includes(String(receipt.state))) {
        setReceiptMessage("回执内容无法核验。结果仍未知；原启动标记保留，请勿重复提交。");
      } else if (receipt.state === "pending") {
        setReceiptMessage("服务器仍将这次写入标记为处理中。结果尚未确认；请勿重复提交。");
      } else if (receipt.state === "committed" && marker.phase === "traveler") {
        setReceiptMessage("服务器回执确认登录会话已创建；当前页面没有收到会话凭据。请勿重新提交。");
      } else if (receipt.state === "committed") {
        setReceiptMessage("服务器回执确认行程草稿已创建；页面尚未恢复该行程。请勿重新提交。");
      } else {
        setReceiptMessage("服务器当前没有可核验的这次写入回执。结果仍未知；请勿重复提交。");
      }
    } catch {
      setReceiptMessage("暂时无法读取这次写入回执。结果仍未知；原启动标记保留，请勿重复提交。");
    } finally {
      setReceiptBusy(false);
    }
  };

  const checkCurrentTravelerDrafts = async () => {
    const marker = readStartWriteState();
    const recovery = startRecoveryIdentity;
    const bearer = recovery?.bearer ?? readTravelerBearer();
    if (!marker?.cityCode || marker.phase !== "journey" || !startWriteBlocked || !bearer || startRecoveryBusy) return;
    const storedBearerAtStart = readTravelerBearer();
    const storedTravelerIdAtStart = readTravelerIdentity()?.travelerId ?? null;
    setStartRecoveryBusy(true);
    setStartRecoveryMessage(null);
    try {
      const deadlineAt = performance.now() + READ_DEADLINE_MS;
      const response = await fetchWithReadDeadline("/api/v1/journeys/session/recent-drafts", {
        headers: { Authorization: `Bearer ${bearer}`, Accept: "application/json" },
        cache: "no-store",
      }, READ_DEADLINE_MS);
      if (!response.ok) {
        setStartRecoveryMessage("当前签名身份暂时无法读取草稿。结果仍未知；未重发写入。");
        return;
      }
      const value: unknown = await readJsonBeforeReadDeadline(response, deadlineAt);
      if (!Array.isArray(value)) {
        setStartRecoveryMessage("服务器草稿列表无法核验。结果仍未知；未重发写入。");
        return;
      }
      if (readTravelerBearer() !== storedBearerAtStart ||
          (readTravelerIdentity()?.travelerId ?? null) !== storedTravelerIdAtStart ||
          (recovery && startRecoveryIdentity?.bearer !== recovery.bearer)) {
        setStartRecoveryMessage("核验期间签名身份已变化。结果仍未知；未重发写入。");
        return;
      }
      const matchingDraft = value.some((item) => {
        if (!item || typeof item !== "object") return false;
        const record = item as Record<string, unknown>;
        return record.status === "DRAFT" && record.city_code === marker.cityCode &&
          typeof record.id === "string" && record.id.length > 0;
      });
      setStartRecoveryMessage(matchingDraft
        ? "当前签名身份下已找到与本次地区对应的草稿。结果已确认；原身份和行程保留，未重发写入。"
        : "当前签名身份下未找到与本次地区匹配的草稿。结果仍未知；原启动标记保留，未重发写入。");
    } catch {
      setStartRecoveryMessage("暂时无法读取当前签名身份的草稿。结果仍未知；未重发写入。");
    } finally {
      setStartRecoveryBusy(false);
    }
  };

  const restartWithNewSession = () => {
    if (startRequestInFlightRef.current || startWriteBlockedRef.current) return;
    const pointer = readLegacyJourneyPointer();
    setJourney(null);
    setPocketWalk(null);
    setRecentJourneys([]);
    setLegacyRestoreFailed(false);
    setError(null);
    void start(pointer?.cityName, { freshSession: true });
  };

  const resumeRecentJourney = (saved: TrialJourney) => {
    if (startWriteBlockedRef.current) return;
    const identity = readTravelerIdentity();
    if (!identity || identity.travelerId !== saved.ownerTravelerId) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    setJourney(saved);
    setCityName(saved.cityName);
    setExplorationTitle(null);
    setCandidateForJourney(null);
    setPocketWalk(null);
    setError(null);
    setNotice(null);
    setActiveTab("explore");
  };

  const recoverDeniedJourney = () => {
    // A stale local pointer is NOT proof that the current bearer owns a
    // Journey. Clear only the navigation pointer after an explicit user tap.
    // The database Journey is untouched; no permission bypass or silent
    // reassignment takes place.
    if (!journey || startWriteBlockedRef.current) return;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const stored = saved ? JSON.parse(saved) as Partial<TrialJourney> : null;
      if (stored?.id === journey.id) localStorage.removeItem(STORAGE_KEY);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
    clearTravelerBearer();
    setCityName(journey.cityName);
    setJourney(null);
    setExplorationTitle(null);
    setCandidateForJourney(null);
    setPocketWalk(null);
    setActiveTab("explore");
    setNotice(null);
    setError("这次登录无法访问之前的行程。你可以重新开始探索，原行程不会因此被删除。");
    setRecentJourneys([]);
  };

  const switchCity = (nextCityName?: string) => {
    if (startWriteBlockedRef.current) return;
    if (journey) setRecentJourneys(rememberJourney(journey));
    // Keep the signed traveler and the previous Journey in the recent list.
    localStorage.removeItem(STORAGE_KEY);
    if (nextCityName?.trim()) setCityName(nextCityName.trim());
    setExplorationTitle(null);
    setJourney(null);
    setError(null);
    setNotice(null);
    setCandidateForJourney(null);
    setPocketWalk(null);
    setActiveTab("explore");
  };

  const finishStartingJourney = async () => {
    if (!journey) return;
    const next: TrialJourney = { ...journey, status: "ACTIVE" };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    localStorage.setItem("citynexus.v8.journey_id", next.id);
    setCandidateForJourney(null);
    setJourney(next);
    setActiveTab("trips");
    setNotice("行程已开始，可以在「我的旅程」继续调整。");
  };

  useEffect(() => {
    const bearer = readTravelerBearer();
    if (activeTab !== "trips" || journey || !bearer) { setSavedTrips([]); return; }
    const serial = ++tripLookup.current;
    cityNexusApi.listSessionDraftJourneys()
      .then((rows) => {
        if (serial !== tripLookup.current || readTravelerBearer() !== bearer) return;
        setSavedTrips(Array.isArray(rows) ? rows.filter((row) => row && typeof row.id === "string") : []);
      })
      .catch(() => { if (serial === tripLookup.current) setSavedTrips([]); });
  }, [activeTab, journey]);

  const resumeSavedTrip = async (tripId: string) => {
    const bearer = readTravelerBearer(), identity = readTravelerIdentity();
    if (!bearer || !identity || startWriteBlockedRef.current) return;
    const serial = ++tripLookup.current;
    try {
      const saved = await cityNexusApi.getJourney(tripId);
      if (serial !== tripLookup.current || readTravelerBearer() !== bearer) return;
      // The server already authorizes this read for the bearer; the check here keeps a list that
      // went stale between two taps from opening somebody else's trip under this traveller's nose.
      if (saved.id !== tripId || saved.traveler_id !== identity.travelerId) return;
      const next: TrialJourney = {
        id: saved.id, cityCode: saved.city_code, cityName: saved.title,
        status: saved.status === "ACTIVE" ? "ACTIVE" : "DRAFT", ownerTravelerId: identity.travelerId,
      };
      setRecentJourneys(rememberJourney(next));
      localStorage.setItem("citynexus.v8.journey_id", next.id);
      setCandidateForJourney(null);
      setError(null);
      setJourney(next);
    } catch {
      if (serial === tripLookup.current && readTravelerBearer() === bearer) setError("这趟行程暂时打不开，稍后再试一次。");
    }
  };

  const goSummary = (state: string) => {
    switch (state) {
      case "NOT_STARTED": return "已保存，等待你出发";
      case "HEADING_TO_FIRST": return "正在前往第一站";
      case "FIRST_STOP_DONE_SELF_REPORTED": return "第一站已由你确认完成";
      case "HEADING_TO_SECOND": return "正在前往第二站";
      case "WALK_DONE_SELF_REPORTED": return "两站完成（自行报告）";
      case "PAUSED": return "已暂停，可以继续";
      default: return "由服务器保存的私人路线";
    }
  };

  useEffect(() => {
    const revealAgent = () => { if (activeTab === "me") setActiveTab("explore"); };
    window.addEventListener("citynexus:mission-panel", revealAgent);
    return () => window.removeEventListener("citynexus:mission-panel", revealAgent);
  }, [activeTab]);

  const navigateMobile = (tab: RevolutionMobileTab) => {
    setActiveTab(tab);
    if (tab !== "me") requestAnimationFrame(() => window.dispatchEvent(new CustomEvent("citynexus:mission-panel", { detail: tab === "trips" ? "timeline" : "map" })));
    try { sessionStorage.setItem("citynexus.revolution.v3.space", tab); } catch { /* In-memory navigation remains usable. */ }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="rev-firstlook rev-mobile-v1 rev-v3" data-testid="revolution-first-look">
      <header className="rev-firstlook-header">
        <div className="rev-firstlook-brand">
          <span className="rev-firstlook-mark" aria-hidden="true">C</span>
          <div>
            <strong>CityNexus</strong>
            <small>你的智能旅行伙伴</small>
          </div>
        </div>
        <details className="rev-firstlook-agent" data-testid="revolution-agent-runtime">
          <summary>
            {agentStatusTitle}
          </summary>
          <p>
            {agentCheckError ?? agentStatusDetail}
          </p>
        </details>
      </header>

      <main className="rev-firstlook-content">
        {startWriteStatus && (
          <section
            className="rev-firstlook-notice"
            role="status"
            aria-live="polite"
            data-testid="rev-start-write-status"
          >
            <p>{startWriteMessage(startWriteStatus)}</p>
            {startWriteBlocked && startWriteStatus.state !== "pending" && (
              <div className="rev-firstlook-recovery" data-testid="rev-start-write-checks">
                {startWriteStatus.receiptKey && (
                  <button
                    type="button"
                    className="rev-mobile-secondary"
                    disabled={receiptBusy}
                    onClick={() => void checkStartWriteReceipt()}
                    data-testid="rev-firstlook-query-write-receipt"
                  >
                    {receiptBusy ? "正在查询写入回执…" : "手动查询本次写入回执"}
                  </button>
                )}
                {canCheckCurrentStartDrafts && (
                  <button
                    type="button"
                    className="rev-mobile-secondary"
                    disabled={startRecoveryBusy}
                    onClick={() => void checkCurrentTravelerDrafts()}
                    data-testid="rev-firstlook-check-start-draft"
                  >
                    {startRecoveryBusy ? "正在查询当前身份的草稿…" : "手动查找本次行程草稿"}
                  </button>
                )}
                {receiptMessage && <p data-testid="rev-start-write-receipt-result">{receiptMessage}</p>}
                {startRecoveryMessage && <p data-testid="rev-start-write-draft-result">{startRecoveryMessage}</p>}
              </div>
            )}
          </section>
        )}
        {!journey ? (
          activeTab === "explore" ? (
            <section className="rev-firstlook-hero" data-testid="rev-mobile-welcome">
              <span className="rev-firstlook-eyebrow">CITYNEXUS / YOUR TRIP</span>
              <h1>你的下一趟旅行，<br />从一句话开始。</h1>
              <p>说说想去哪儿、和谁一起、想怎样度过。我们一起把想法变成行程。</p>
              <form className="rev-trip-request-form" onSubmit={(event) => { event.preventDefault(); void start(); }}>
                    <label className="rev-trip-goal-label" htmlFor="rev-trip-goal">想怎么玩？</label>
                    <textarea
                      id="rev-trip-goal"
                      value={tripGoal}
                      maxLength={240}
                      rows={3}
                      disabled={busy || startWriteBlocked}
                      onChange={(event) => {
                        const value = event.target.value;
                        setTripGoal(value);
                        applyNumbersFromGoal(value);
                      }}
                      placeholder="例如：带爸妈轻松逛两天，少走路，晚上想吃当地特色。"
                      data-testid="rev-trip-goal"
                    />
                <label className="rev-trip-destination-label" htmlFor="rev-firstlook-city">目的地</label>
                <div className="rev-firstlook-form-row">
                  <input
                    id="rev-firstlook-city"
                    autoComplete="off"
                    value={cityName}
                    maxLength={60}
                      required
                    disabled={busy || startWriteBlocked}
                    placeholder="例如：连城、厦门、杭州"
                    onChange={(event) => setCityName(event.target.value)}
                    data-testid="rev-firstlook-city"
                  />
                </div>
                <details className="rev-v3-trip-dates"><summary>日期与天数</summary><div className="rev-trip-request-grid">
                  <label>
                    出发日期
                    <input
                      type="date"
                      min={localDateAfter(0)}
                      value={startDate}
                      required
                      disabled={busy || startWriteBlocked}
                      onChange={(event) => setStartDate(event.target.value)}
                      data-testid="rev-trip-start-date"
                    />
                  </label>
                  <label>
                    游玩天数
                    <input
                      type="number"
                      min={1}
                      max={14}
                      value={durationDays}
                      required
                      disabled={busy || startWriteBlocked}
                      onChange={(event) => setDurationDays(Number(event.target.value))}
                      data-testid="rev-trip-duration"
                    />
                  </label>
                </div>
                </details>
                <details className="rev-trip-preferences">
                  <summary>
                    <span>更多偏好</span>
                    <small>同行 {partySize} 人 · 预算 ¥{Number(budgetYuan || 0).toLocaleString("zh-CN")}</small>
                  </summary>
                  <div className="rev-trip-preferences-content">
                    <div className="rev-trip-request-grid">
                      <label>
                        同行人数
                        <input
                          type="number"
                          min={1}
                          max={20}
                          value={partySize}
                          required
                          disabled={busy || startWriteBlocked}
                          onChange={(event) => {
                            partyEdited.current = true;
                            setPartySize(Number(event.target.value));
                          }}
                          data-testid="rev-trip-party-size"
                        />
                      </label>
                      <label>
                        总预算（元）
                        <input
                          type="number"
                          min={0}
                          max={10000000}
                          step="1"
                          value={budgetYuan}
                          required
                          disabled={busy || startWriteBlocked}
                          onChange={(event) => {
                            budgetEdited.current = true;
                            setBudgetYuan(event.target.value);
                          }}
                          data-testid="rev-trip-budget"
                        />
                      </label>
                    </div>
                    <div className="rev-trip-request-grid rev-trip-request-options">
                      <label>
                        行程节奏
                        <select
                          value={planningMode}
                          disabled={busy || startWriteBlocked}
                          onChange={(event) => setPlanningMode(event.target.value as TripPlanningMode)}
                          data-testid="rev-trip-planning-mode"
                        >
                          <option value="balanced">松紧适中</option>
                          <option value="budget">优先省钱</option>
                          <option value="explore">多看看新地方</option>
                          <option value="strict_schedule">按时间安排</option>
                        </select>
                      </label>
                      <label>
                        活动强度
                        <select
                          value={tripEnergy}
                          disabled={busy || startWriteBlocked}
                          onChange={(event) => setTripEnergy(event.target.value as TripEnergy)}
                          data-testid="rev-trip-energy"
                        >
                          <option value="easy">轻松少走</option>
                          <option value="steady">适中节奏</option>
                          <option value="full">充实安排</option>
                        </select>
                      </label>
                    </div>
                    <fieldset className="rev-trip-interest-set" disabled={busy || startWriteBlocked}>
                      <legend>感兴趣的内容</legend>
                      <div className="rev-trip-interest-options">
                        {TRIP_INTERESTS.map((interest) => (
                          <label key={interest.value}>
                            <input
                              type="checkbox"
                              checked={tripInterests.includes(interest.value)}
                              onChange={(event) => setTripInterests((current) => event.target.checked
                                ? [...current, interest.value]
                                : current.filter((item) => item !== interest.value))}
                              data-testid={`rev-trip-interest-${interest.value}`}
                            />
                            <span>{interest.label}</span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <p className="rev-trip-ai-line">保存后，这段想法会带到 Agent 输入栏，可以继续聊着修改。</p>
                  </div>
                </details>
                <button className="rev-trip-submit" disabled={busy || startWriteBlocked} type="submit" data-testid="rev-firstlook-start">
                  {busy ? "正在保存旅行需求…" : startWriteBlocked ? "结果待确认" : "继续规划 →"}
                </button>
              </form>
              {recentJourneys.length > 0 && (
                <div className="rev-firstlook-recent-journeys" data-testid="rev-recent-journeys">
                  <h2>最近的行程</h2>
                  {recentJourneys.map((saved) => (
                    <button
                      key={saved.id}
                      type="button"
                      className="rev-mobile-secondary"
                      disabled={busy || startWriteBlocked}
                      aria-label={`打开${saved.cityName}行程`}
                      onClick={() => resumeRecentJourney(saved)}
                    >
                      <span>{saved.cityName}</span>
                      <span>继续行程 →</span>
                    </button>
                  ))}
                </div>
              )}
              {error && <p className="rev-firstlook-error" role="alert">{error}</p>}
              {legacyRestoreFailed && !startWriteBlocked && (
                <button
                  type="button"
                  className="rev-mobile-secondary"
                  disabled={busy || startWriteBlocked}
                  onClick={restartWithNewSession}
                  data-testid="rev-firstlook-new-session"
                >
                  用新行程继续
                </button>
              )}
            </section>
          ) : activeTab === "trips" ? (
            <section className="rev-mobile-panel" data-testid="rev-mobile-empty-trips">
              <span className="rev-firstlook-eyebrow">TRIPS</span>
              <h2>行程</h2>
              {savedTrips.length > 0 && (
                <ul className="rev-saved-trips" data-testid="rev-saved-trips">
                  {savedTrips.map((item) => (
                    <li key={item.id}>
                      <span>{item.status === "ACTIVE" ? "在路上" : "还没出发"}</span>
                      <button type="button" data-testid="rev-trip-resume"
                        onClick={() => void resumeSavedTrip(item.id)}>继续这趟</button>
                    </li>
                  ))}
                </ul>
              )}
              <p>{deviceJourneyHint
                ? `这台设备上还留着「${deviceJourneyHint}」这趟行程，这次打开没有登录到它，所以读不到进度。`
                : "开始探索一个地区后，你保存的路线和出发进度会显示在这里。"}</p>
              <button type="button" data-testid="rev-mobile-empty-start" onClick={() => navigateMobile("explore")}>
                开始探索 →
              </button>
              <div className="rev-mobile-account-line">
                <span>AI 服务</span><strong>{agentStatusTitle}</strong>
              </div>
              <p>选好地点并确认行程后，Agent 就会开始工作。</p>
            </section>
          ) : (
            <section className="rev-mobile-panel" data-testid="rev-mobile-empty-me">
              <span className="rev-firstlook-eyebrow">CITYNEXUS</span>
              <h2>我的</h2>
              <p>开始探索后，这里会显示你的地区和助手状态。</p>
              <div className="rev-mobile-account-line">
                <span>AI 助手</span><strong>{agentStatusTitle}</strong>
              </div>
            </section>
          )
        ) : (
          <>
            <div hidden={activeTab === "me"}>
              <MissionCockpit
                key={journey.id}
                journeyId={journey.id}
                cityName={journey.cityName}
                onChangeCity={() => switchCity()}
                goal={serverBrief?.journeyId === journey.id && serverBrief.bearer === readTravelerBearer()
                  ? serverBrief.goal : tripGoal}
                journeyStatus={journey.status}
                visible={activeTab !== "me"}
                space={activeTab === "trips" ? "journey" : "explore"}
                preparation={(fromAgentDraft) => <MobilePlanWorkbench fromAgentDraft={fromAgentDraft} key={journey.id} journeyId={journey.id} placeId={candidateForJourney}
                  visible={activeTab === "trips"} onStarted={finishStartingJourney} onExplore={() => navigateMobile("explore")}
                  onBriefSaved={(brief) => { const bearer = readTravelerBearer(); if (bearer) setServerBrief({ journeyId: journey.id, bearer, goal: tripBriefGoal(brief.goal, brief.interests, brief.energy) }); window.dispatchEvent(new Event("citynexus:mission-refresh")); }} />}
                agentStatus={agentStatusTitle}
                agentAvailable={Boolean(agentCanRequestSuggestion)}
                executionAgent={journey.status === "ACTIVE" ? <section aria-label="真正的 Journey Operator" data-testid="revolution-real-operator">
                  <AgentWorkStatus journeyId={journey.id} visible={activeTab !== "me"} />
                  <MobileCompatAgentActivity journeyId={journey.id} visible={activeTab !== "me"} aiDisabled={aiDisabled} />
                  <MobileHermesRun globalComposer journeyId={journey.id} visible={activeTab !== "me"} />
                </section> : null}
                executionDecisions={journey.status === "ACTIVE"
                  ? <LiveRecovery journeyId={journey.id} journeyStatus="ACTIVE" /> : null}
                onExplore={() => {
                  if (journey.status === "ACTIVE") { navigateMobile("trips"); return; }
                  document.querySelector(".rev-firstlook-real-ui")?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
                onTrip={() => navigateMobile("trips")}
              />
            </div>
            <section className="rev-mobile-tabpanel" hidden={activeTab !== "explore" && !(journey.status === "ACTIVE" && activeTab === "trips")} data-testid="rev-mobile-screen-explore">
              <section className="rev-firstlook-journey">
                <div>
                  <span className="rev-firstlook-eyebrow">{journey.status === "ACTIVE" ? "正在旅行" : "正在探索"}</span>
                  <h1>{explorationTitle?.journeyId === journey.id ? explorationTitle.label : journey.cityName}</h1>
                  <p>想怎么走？先聊一句，再从真实地点中选择。</p>
                </div>
                <button type="button" onClick={() => switchCity()} className="rev-firstlook-reset">
                  换地区
                </button>
              </section>

              {journey.status === "DRAFT" && (
                <button
                  type="button"
                  className="rev-firstlook-agent-entry"
                  data-testid="rev-quick-open-agent-activity"
                  aria-label={`AI 工作动态，${agentStatusTitle}`}
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent("citynexus:mission-panel", { detail: "assistant" }));
                    const composer = document.getElementById("rev-mission-chat-input");
                    if (composer) { composer.focus(); return; }
                    document.querySelector(".cn-mission-activity")?.scrollIntoView({ behavior: "smooth", block: "start" });
                  }}
                >
                  <span>AI 工作动态</span>
                  <small>{agentStatusTitle}</small>
                  <span aria-hidden="true">查看 →</span>
                </button>
              )}
              {notice && <p className="rev-firstlook-notice" role="status">{notice}</p>}
              {journey.status === "DRAFT" ? (
                <section className="rev-firstlook-real-ui" aria-label="地点探索与私人散步">
                  <RevolutionQuickExplore
                    missionMode
                    key={journey.id}
                    journeyId={journey.id}
                    cityName={journey.cityName}
                    initialGoal={serverBrief?.journeyId === journey.id && serverBrief.bearer === readTravelerBearer() ? serverBrief.goal : undefined}
                    onExplorationCenterLabelChange={(label) => {
                      setExplorationTitle({ journeyId: journey.id, label });
                    }}
                    agentConfigured={Boolean(agentCanRequestSuggestion)}
                    agentChecking={agentStatusChecking}
                    onPocketWalkChange={setPocketWalk}
                    onMemberAccessDenied={recoverDeniedJourney}
                    onFormalCandidateSelected={(placeId) => {
                      setCandidateForJourney(placeId);
                      setNotice("已选中有来源的地点。请在行程页面确认正式计划。");
                      navigateMobile("trips");
                    }}
                  />
                  <details
                    className="rev-discovery-details"
                    open={advancedOpen}
                    onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}
                  >
                    <summary>高级功能：地图坐标、分享与技术详情</summary>
                    {advancedOpen && (
                      <BootstrapDiscoveryPanel
                        key={journey.id + "-advanced"}
                        journeyId={journey.id}
                        cityCode={journey.cityCode}
                        cityName={journey.cityName}
                        onCompleted={async (placeId) => {
                          setCandidateForJourney(placeId);
                          setNotice("已选择有来源的地点。请在行程页面确认正式计划。");
                          navigateMobile("trips");
                        }}
                      />
                    )}
                  </details>
                </section>
              ) : (
                <section className="rev-mobile-panel">
                  <h2>行程已经启动</h2>
                  <p>实时进度、变更建议和 Agent 审批现在都在「行程」里。</p>
                  <button type="button" onClick={() => navigateMobile("trips")}>查看当前行程 →</button>
                </section>
              )}
            </section>

            <section className="rev-mobile-tabpanel" hidden={activeTab !== "trips"} data-testid="rev-mobile-screen-trips">

              {journey.status === "ACTIVE" ? (
                <section className="rev-mobile-panel">
                  <section className="rev-mobile-panel">
                    <h2>当前行程</h2>
                    <p>这里显示行程监测、助手运行记录和待确认操作。</p>
                  </section>
                  <button type="button" onClick={() => navigateMobile("explore")}>回到行程工作台</button>
                </section>
              ) : (
                <>
                  <section className="rev-mobile-panel">
                    <span className="rev-firstlook-eyebrow">YOUR TRIP</span>
                    <h2>我的行程</h2>
                    {pocketWalk ? (
                      <>
                        <p>以下两站来自当前签名成员保存在服务器的私人路线。</p>
                        <div className="rev-mobile-stop"><b>01</b><span>{pocketWalk.first_stop.name}</span></div>
                        <div className="rev-mobile-stop"><b>02</b><span>{pocketWalk.second_stop.name}</span></div>
                        <p>当前进度：<strong>{goSummary(pocketWalk.go_progress.state)}</strong></p>
                        <small className="rev-mobile-truth">到达状态由你确认。</small>
                        <button type="button" onClick={() => navigateMobile("explore")}>
                          查看路线并继续 GO →
                        </button>
                      </>
                    ) : (
                      <>
                        <p>还没有保存的私人路线。探索时挑选两个真实地点，就会在这里看到它们。</p>
                        <button type="button" onClick={() => navigateMobile("explore")}>去发现地点 →</button>
                      </>
                    )}
                  </section>
                  <DraftAgentActivity
                    status={agentStatusTitle}
                    hasSelectedPlace={Boolean(candidateForJourney)}
                    hasSavedPocketWalk={Boolean(pocketWalk)}
                  />
                </>
              )}
            </section>

            <section className="rev-mobile-tabpanel" hidden={activeTab !== "me"} data-testid="rev-mobile-screen-me">
              <section className="rev-mobile-panel">
                <span className="rev-firstlook-eyebrow">CITYNEXUS</span>
                <h2>我的</h2>
                <div className="rev-mobile-account-line">
                  <span>探索地区</span><strong>{journey.cityName}</strong>
                </div>
                <div className="rev-mobile-account-line">
                  <span>公开地点</span><strong>{sample ? "受控样本模式" : "真实公开地图接口"}</strong>
                </div>
                <div className="rev-mobile-account-line">
                  <span>AI 助手</span><strong>{agentStatusTitle}</strong>
                </div>
                <div className="rev-mobile-account-line">
                  <span>行程状态</span><strong>{journey.status === "ACTIVE" ? "已正式启动" : "私人探索草稿"}</strong>
                </div>
                <button type="button" className="rev-mobile-secondary" onClick={() => switchCity()}>探索其他地区</button>
                <details className="rev-discovery-details">
                  <summary>关于技术来源与旧版界面</summary>
                  <p>AI 推理、公开地图查询和路线进度有独立的数据来源与授权。</p>
                  <a className="rev-firstlook-quiet" href="/v8/hub">查看旧版 V8 界面 ↗</a>
                </details>
              </section>
            </section>
          </>
        )}
      </main>
      <RevolutionMobileNav
        active={activeTab}
        onSelect={navigateMobile}
        hasSavedWalk={Boolean(pocketWalk)}
      />
      <footer className="rev-firstlook-footer">
        CityNexus · 地点来源见卡片，到达状态由你确认
      </footer>
    </div>
  );
}
