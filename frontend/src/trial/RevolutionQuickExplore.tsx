import { useEffect, useRef, useState } from "react";
import {
  CityNexusApiError,
  cityNexusApi,
  type BootstrapCitySearchResult,
  type BootstrapDiscoveryCandidate,
  type BootstrapDiscoveryReadinessResponse,
  type BootstrapDiscoveryResponse,
  type BootstrapPocketWalkResponse,
  type BootstrapPocketWalkGoState,
} from "../api/citynexus";
import { parsePublicMapLink } from "../features/discovery/BootstrapDiscoveryPanel";
import { PublicCityAreaPicker, type PublicCityCenter } from "../features/discovery/PublicCityAreaPicker";
import { readTravelerBearer, subscribeTravelerBearer } from "../lib/travelerSession";
import { isOriginResponseUnusable } from "../lib/failureAttribution";
import { isReadDeadlineMissed } from "../lib/readDeadline";
import { isWriteDeadlineMissed } from "../lib/writeDeadline";

/**
 * A HUMAN-SIZED entry to the exact signed R107/R108 endpoints.
 *
 * The two external HTTP operations are sent only when the user clicks their
 * plainly-labelled release button. A public geocoder result is only an
 * APPROXIMATE city center. If a user explicitly selects it as a coarse
 * public search area, this creates a manual search choice, not a claim that
 * they tapped a map or physically arrived there. No GPS, silent external
 * requests, disguised fixture, PlanVersion, or AgentRun is invented here.
 */
type Stage = "area" | "category" | "results" | "walk";

const categories = [
  { value: "park/garden", name: "公园和绿地", subtitle: "轻松散步" },
  { value: "museum/gallery", name: "博物馆和艺术", subtitle: "看看文化和历史" },
  { value: "cafe", name: "咖啡馆", subtitle: "坐下来歇一会儿" },
  { value: "library", name: "图书馆", subtitle: "找个安静的地方" },
] as const;

const goCopy: Record<BootstrapPocketWalkGoState, string> = {
  NOT_STARTED: "路线已经保存。想出发时，点击下面的「开始散步」。",
  HEADING_TO_FIRST: "正前往第一站。到达后请自己确认，系统不会假装知道你的实时位置。",
  FIRST_STOP_DONE_SELF_REPORTED: "第一站完成（由你手动报告）。可以出发去第二站了。",
  HEADING_TO_SECOND: "正前往第二站。完成后你可以自己报告。",
  WALK_DONE_SELF_REPORTED: "散步完成。这个状态是你的报告，不是系统证明你真实到达。",
  PAUSED: "路线已暂停，稍后可以继续。",
};

type AlertKind = "neutral" | "error" | "good";
type QuickRecovery = { label: string; action: () => void };
type QuickAlert = { type: AlertKind; text: string; recovery?: QuickRecovery };
type ExplorePhase =
  | "请教 AI"
  | "查找地名"
  | "检查地图服务"
  | "搜索附近真实地点"
  | "选择正式路线地点"
  | "保存私人散步"
  | "更新散步进度"
  | "读取服务端路线";
type ErrorDiagnostics = {
  phase: ExplorePhase | "读取服务端路线";
  classification: string;
  method: string | null;
  path: string | null;
  status: number | null;
  reasonCode: string | null;
};

function candidateSource(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      !["www.openstreetmap.org", "openstreetmap.org"].includes(url.hostname) ||
      url.username || url.password ||
      !/^\/(node|way|relation)\/[1-9][0-9]*$/.test(url.pathname)
    ) return null;
    return url.toString();
  } catch {
    return null;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function safeReasonCode(error: unknown): string | null {
  if (!(error instanceof CityNexusApiError)) return null;
  const root = asRecord(error.body);
  const envelope = asRecord(root?.error);
  const detail = asRecord(root?.detail);
  const candidates = [
    envelope?.reason_code,
    envelope?.code,
    root?.reason_code,
    root?.code,
    detail?.reason_code,
    detail?.code,
  ];
  return candidates.find(
    (value): value is string => typeof value === "string" && /^[A-Z][A-Z0-9_]{1,63}$/.test(value),
  ) ?? null;
}

function safeRequestPath(value: unknown): string | null {
  if (typeof value !== "string" || !value) return null;
  let pathname = value;
  try {
    pathname = new URL(value, window.location.origin).pathname;
  } catch {
    pathname = value.split(/[?#]/, 1)[0];
  }
  pathname = pathname.replace(/^\/api\/v1(?=\/)/, "");
  return pathname.replace(
    /\/[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=\/|$)/gi,
    "/:id",
  );
}

function errorDiagnostics(phase: ExplorePhase, error: unknown): ErrorDiagnostics {
  const metadata = error instanceof Error
    ? error as Error & { requestMethod?: unknown; requestPath?: unknown; method?: unknown; path?: unknown; status?: unknown }
    : null;
  const methodValue = error instanceof CityNexusApiError
    ? error.requestMethod
    : metadata?.requestMethod ?? metadata?.method;
  const pathValue = error instanceof CityNexusApiError
    ? error.requestPath
    : metadata?.requestPath ?? metadata?.path;
  const statusValue = error instanceof CityNexusApiError
    ? error.status
    : isOriginResponseUnusable(error) ? error.status : null;
  const method = typeof methodValue === "string" && /^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$/i.test(methodValue)
    ? methodValue.toUpperCase()
    : null;
  let classification = "页面校验未通过";
  if (error instanceof CityNexusApiError) classification = "HTTP 应答";
  else if (isOriginResponseUnusable(error)) classification = "HTTP 成功，但响应格式不可用";
  else if (isReadDeadlineMissed(error) || isWriteDeadlineMissed(error)) classification = "本机等待期限已到";
  else if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) classification = "未收到 HTTP 应答";
  return {
    phase,
    classification,
    method,
    path: safeRequestPath(pathValue),
    status: typeof statusValue === "number" ? statusValue : null,
    reasonCode: safeReasonCode(error),
  };
}

function messageForError(phase: ExplorePhase, error: unknown): string {
  if (phase === "请教 AI") {
    return "AI 建议这一步没有完成；没有自动重试或额外模型调用。你仍可跳过 AI，继续手动选择地区和地点。";
  }
  if (error instanceof CityNexusApiError) {
    const status = error.status;
    if (status === 401) return phase + "需要有效的签名会话。回到 Revolution 重新进入后再试。";
    if (status === 403) return "当前会话没有执行「" + phase + "」的权限。请回到 Revolution 重新进入这趟行程。";
    if (status === 404) return "服务器找不到当前行程或对应资源，「" + phase + "」没有完成。回到 Revolution 重新开始。";
    if (status === 409) return "服务器上的行程状态已经变化；「" + phase + "」没有覆盖新状态。先重新读取路线状态。";
    if (status === 422) return "服务器拒绝了「" + phase + "」提交的数据。检查位置、类别或所选地点后再试。";
    if (status === 429) return "服务端对「" + phase + "」进行了限流。稍等片刻，再明确点一次恢复操作。";
    if (status >= 500) {
      const writes = ["保存私人散步", "更新散步进度", "选择正式路线地点"].includes(phase);
      return writes
        ? phase + "遇到服务端故障（HTTP " + status + "）。请求结果需要先从服务器读取核对。"
        : phase + "遇到服务端故障（HTTP " + status + "）。可以稍后再明确试一次。";
    }
    return "服务器拒绝了「" + phase + "」（HTTP " + status + "）。检查当前输入后再试。";
  }
  if (isOriginResponseUnusable(error)) {
    return "服务器已回答 HTTP " + error.status + "，但响应内容无法用于「" + phase + "」，本页没有采用这份响应。";
  }
  if (isReadDeadlineMissed(error) || isWriteDeadlineMissed(error)) {
    const writes = ["保存私人散步", "更新散步进度", "选择正式路线地点"].includes(phase);
    return writes
      ? "等待「" + phase + "」的答复超时，服务器可能已经处理这次请求。先读取服务器路线状态，再决定是否重试。"
      : "等待「" + phase + "」的答复超时，没有收到 HTTP 状态。你可以明确重试这一步。";
  }
  if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) {
    const writes = ["保存私人散步", "更新散步进度", "选择正式路线地点"].includes(phase);
    return writes
      ? "「" + phase + "」没有收到 HTTP 答复，服务器可能已经处理请求。先读取服务器路线状态，再决定是否重试。"
      : "「" + phase + "」没有收到 HTTP 答复。检查连接后可以明确重试这一步。";
  }
  return "「" + phase + "」返回的内容未通过本页校验，没有采用。先读取服务器状态或返回检查所选内容。";
}

function recoveryForError(
  error: unknown,
  fallback: QuickRecovery,
  invalidInputFallback?: QuickRecovery,
): QuickRecovery {
  if (error instanceof CityNexusApiError && [401, 403].includes(error.status)) {
    return { label: "回到 Revolution 重新进入", action: () => window.location.assign("/revolution") };
  }
  if (error instanceof CityNexusApiError && error.status === 404) {
    return { label: "回到 Revolution 重新开始", action: () => window.location.assign("/revolution") };
  }
  if (error instanceof CityNexusApiError && error.status === 422 && invalidInputFallback) {
    return invalidInputFallback;
  }
  return fallback;
}

export function RevolutionQuickExplore({
  journeyId,
  cityName,
  agentConfigured = false,
  onFormalCandidateSelected,
}: {
  journeyId: string;
  cityName: string;
  agentConfigured?: boolean;
  onFormalCandidateSelected?: (placeId: string) => void;
}) {
  const sampleProviderMode = import.meta.env.VITE_REV_TRIAL_MODE === "sample";
  const [stage, setStage] = useState<Stage>("area");
  const [query, setQuery] = useState(cityName);
  const [aiGoal, setAiGoal] = useState(`我在${cityName}，今天想轻松逛逛，别太累。有什么好玩的方向？`);
  const [aiAdvice, setAiAdvice] = useState<{ category: string | null; reason: string; verifiedTool: boolean; model: string | null } | null>(null);
  const [cityResults, setCityResults] = useState<BootstrapCitySearchResult[]>([]);
  const [cityFocus, setCityFocus] = useState<{ latitude: number; longitude: number } | null>(null);
  const [cityFocusLabel, setCityFocusLabel] = useState<string | null>(null);
  const [centerBasis, setCenterBasis] = useState<"EXPLICIT_GEOCODER_APPROX" | "MAP_TAP" | "OSM_MAP_LINK" | null>(null);
  const [tilesEnabled, setTilesEnabled] = useState(false);
  const [selectedPin, setSelectedPin] = useState<PublicCityCenter | null>(null);
  const [mapLink, setMapLink] = useState("");
  const [center, setCenter] = useState<{ latitude: number; longitude: number } | null>(null);
  const [category, setCategory] = useState<(typeof categories)[number]["value"]>("park/garden");
  const [readiness, setReadiness] = useState<BootstrapDiscoveryReadinessResponse | null>(null);
  const [readinessStatus, setReadinessStatus] = useState<"checking" | "ready" | "blocked" | "error">("checking");
  const [discovery, setDiscovery] = useState<BootstrapDiscoveryResponse | null>(null);
  const [first, setFirst] = useState<string | null>(null);
  const [second, setSecond] = useState<string | null>(null);
  const [walk, setWalk] = useState<BootstrapPocketWalkResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [alert, setAlert] = useState<QuickAlert | null>(null);
  const [errorDetails, setErrorDetails] = useState<ErrorDiagnostics | null>(null);
  const generation = useRef(0);
  const currentOperation = useRef(0);
  const mounted = useRef(true);
  const busyRef = useRef(false);
  const currentBearer = useRef(readTravelerBearer());

  useEffect(() => {
    mounted.current = true;
    const stop = subscribeTravelerBearer((bearer) => {
      // Never display signed member A's private route to member B.
      currentBearer.current = bearer;
      generation.current += 1;
      currentOperation.current += 1;
      busyRef.current = false;
      setBusy(false);
      setCityResults([]);
      setDiscovery(null);
      setWalk(null);
      setFirst(null);
      setSecond(null);
      setCenter(null);
      setSelectedPin(null);
      setCityFocus(null);
      setCityFocusLabel(null);
      setCenterBasis(null);
      setAiAdvice(null);
      setStage("area");
      setAlert({ type: "neutral", text: "账户已切换，请重新选择公开地图位置。" });
    });
    return () => {
      mounted.current = false;
      generation.current += 1;
      currentOperation.current += 1;
      stop();
    };
  }, []);

  useEffect(() => {
    const identity = readTravelerBearer();
    const generationAtStart = generation.current;
    if (!identity) {
      setAlert({ type: "error", text: "缺少登录会话，请重新进入 Revolution。" });
      return;
    }
    const valid = () => mounted.current && generation.current === generationAtStart && readTravelerBearer() === identity;
    void cityNexusApi.getBootstrapDiscoveryReadiness(journeyId)
      .then((next) => {
        if (!valid()) return;
        setReadiness(next);
        setReadinessStatus(next.status === "READY" ? "ready" : "blocked");
      })
      .catch(() => {
        if (!valid()) return;
        setReadiness(null);
        setReadinessStatus("error");
      });
    void cityNexusApi.getBootstrapShortlist(journeyId).then((state) => {
      if (!valid()) return;
      if (state.pocket_walk) {
        setWalk(state.pocket_walk);
        setStage("walk");
      }
    }).catch(() => {
      // No saved walk or an unavailable backend is not permission to display
      // fabricated state. First-time users can still start a fresh search.
    });
  }, [journeyId]);

  const enter = (state: Stage) => {
    setStage(state);
    // The active stage is near the top; don't strand people 5 screens lower.
    requestAnimationFrame(() => {
      document.querySelector(".rev-quick")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const run = async (
    phase: ExplorePhase,
    task: (stillCurrent: () => boolean) => Promise<void>,
    recovery: QuickRecovery | ((error: unknown) => QuickRecovery),
  ) => {
    if (busyRef.current) return;
    const identity = readTravelerBearer();
    if (!identity) {
      setAlert({
        type: "error",
        text: "没有有效登录会话，请重新进入 Revolution。",
        recovery: { label: "回到 Revolution 重新进入", action: () => window.location.assign("/revolution") },
      });
      return;
    }
    busyRef.current = true;
    const requestGeneration = generation.current;
    const runId = ++currentOperation.current;
    const stillCurrent = () =>
      mounted.current &&
      generation.current === requestGeneration &&
      currentOperation.current === runId &&
      readTravelerBearer() === identity;
    setBusy(true);
    setAlert(null);
    setErrorDetails(null);
    try {
      await task(stillCurrent);
    } catch (error) {
      if (stillCurrent()) {
        setAlert({
          type: "error",
          text: messageForError(phase, error),
          recovery: typeof recovery === "function" ? recovery(error) : recoveryForError(error, recovery),
        });
        setErrorDetails(errorDiagnostics(phase, error));
      }
    } finally {
      if (currentOperation.current === runId) {
        busyRef.current = false;
        if (stillCurrent()) setBusy(false);
      }
    }
  };

  const consultHermes = () => {
    const goal = aiGoal.trim();
    if (!agentConfigured) {
      setAlert({ type: "neutral", text: "当前 AI 尚未接入这个会话，直接查城市也能继续。需要先用 --agent 启动本地服务。" });
      return;
    }
    if (goal.length < 4 || goal.length > 360) {
      setAlert({ type: "error", text: "用一句话告诉 AI 你想玩什么（4 到 360 个字）。" });
      return;
    }
    void run("请教 AI", async (stillCurrent) => {
      const suggestion = await cityNexusApi.suggestTrialDiscovery(journeyId, goal);
      if (!stillCurrent()) return;
      const verified = suggestion.status === "MODEL_TOOL_SUGGESTION";
      const matched = verified ? categories.find((item) => item.value === suggestion.category) : null;
      if (matched) setCategory(matched.value);
      setAiAdvice({
        category: matched?.name ?? null,
        reason: suggestion.reason,
        verifiedTool: verified && !!matched,
        model: suggestion.model ?? null,
      });
      setAlert(verified && matched
        ? { type: "good", text: "AI 已根据你说的话建议了一个探索方向。地点仍要从真实公开地图查找。" }
        : { type: "neutral", text: "模型这次没有返回可验证的工具建议。你仍然可以手动选择地区和兴趣。" });
    }, { label: "继续手动探索", action: () => setAlert({ type: "neutral", text: "AI 建议未完成；可以直接查找公开地名并手动挑选两处地点。" }) });
  };

  const cityLookup = () => {
    const cityQuery = query.trim();
    if (cityQuery.length < 2 || cityQuery.length > 120) {
      setAlert({ type: "error", text: "请输入至少两个字的城市或地区，例如「连城县」。" });
      return;
    }
    void run("查找地名", async (stillCurrent) => {
      // The button explicitly announces that this ONE request sends the
      // entered public city label to Nominatim. No passive or typing request.
      const response = await cityNexusApi.bootstrapCitySearch(journeyId, {
        query: cityQuery, provider_consent: true, limit: 3,
      });
      if (!stillCurrent()) return;
      if (response.status !== "CITY_RESULTS" || !response.results.length) {
        setCityResults([]);
        setAlert({
          type: "neutral",
          text: response.status === "GEOCODER_RATE_LIMITED"
            ? "地图服务正在限流，稍等后重试；也可以粘贴公开 OpenStreetMap 地图链接。"
            : "没有找到足够可靠的地名结果。可以换更完整的地名，或粘贴公开地图链接。",
        });
        return;
      }
      setCityResults(response.results);
      setCityFocus(null);
      setSelectedPin(null);
      setTilesEnabled(false);
      setAlert({ type: "good", text: "已经找到公开地区。选一个结果后可以直接按“从这一带附近找”，地图是可选的。" });
    }, (error) => recoveryForError(
      error,
      { label: "再次查找地名", action: () => cityLookup() },
      { label: "检查并编辑地名", action: () => document.getElementById("rev-quick-search")?.focus() },
    ));
  };

  const useCenter = (point: { latitude: number; longitude: number }, basis: "EXPLICIT_GEOCODER_APPROX" | "MAP_TAP" | "OSM_MAP_LINK") => {
    if (!Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) return;
    setCenter(point);
    setCenterBasis(basis);
    setDiscovery(null);
    setFirst(null);
    setSecond(null);
    setCityResults([]);
    setAlert({ type: "good", text: "公开搜索区域已确认。接下来选一个你感兴趣的类别。" });
    enter("category");
  };

  const applyLink = () => {
    const point = parsePublicMapLink(mapLink);
    if (!point) {
      setAlert({
        type: "error",
        text: "请粘贴 OpenStreetMap 的公开地图链接（例如 https://www.openstreetmap.org/#map=13/25.7/116.75），不要粘贴私人地址。",
      });
      return;
    }
    useCenter(point, "OSM_MAP_LINK");
  };

  const retryReadiness = () => {
    void run("检查地图服务", async (stillCurrent) => {
      const next = await cityNexusApi.getBootstrapDiscoveryReadiness(journeyId);
      if (!stillCurrent()) return;
      setReadiness(next);
      setReadinessStatus(next.status === "READY" ? "ready" : "blocked");
      setAlert(next.status === "READY"
        ? { type: "good", text: "地图服务已准备好，可以发起一次明确授权的查询。" }
        : { type: "error", text: "地图服务仍不可用。你可以查看服务状态，但不会虚构地点。" });
    }, { label: "重新检查地图服务", action: () => retryReadiness() });
  };

  const discover = () => {
    if (!center) {
      enter("area");
      setAlert({ type: "neutral", text: "先选一个公开地图区域。" });
      return;
    }
    if (!readiness || readiness.status !== "READY") {
      setAlert({ type: "error", text: "地图服务暂时无法搜索。没有发送请求，也不会虚构结果。" });
      return;
    }
    const selection = center;
    const chosenCategory = category;
    void run("搜索附近真实地点", async (stillCurrent) => {
      // The explicitly labelled button is the ONE-use provider consent.
      const response = await cityNexusApi.bootstrapDiscovery(journeyId, {
        query: chosenCategory,
        radius_m: 2500,
        limit: 3,
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider_consent: true,
        latitude: selection.latitude,
        longitude: selection.longitude,
        coordinate_system: "WGS84",
        mode: "live",
      });
      if (!stillCurrent()) return;
      setDiscovery(response);
      setFirst(null);
      setSecond(null);
      enter("results");
      if (response.status !== "LIVE_RESULTS" || response.candidates.length === 0) {
        setAlert({ type: "neutral", text: "这次没有找到可用的公开地点。可以换类别或位置再试，不会偷偷用样本替换。" });
      } else {
        setAlert({
          type: "good",
          text: `找到 ${response.candidates.length} 个公开地点。现在可以查看并挑选两站。`,
        });
      }
    }, (error) => recoveryForError(
      error,
      { label: "再次搜索附近地点", action: () => discover() },
      { label: "返回修改搜索条件", action: () => enter("category") },
    ));
  };

  const choose = (id: string) => {
    if (!first) {
      setFirst(id);
      return;
    }
    if (first === id) {
      setFirst(second);
      setSecond(null);
      return;
    }
    if (second === id) {
      setSecond(null);
      return;
    }
    setSecond(id);
  };

  const chooseFormalJourney = (candidateId: string) => {
    if (!discovery?.receipt_id || !onFormalCandidateSelected) return;
    const selected = discovery.candidates.find((item) => item.candidate_id === candidateId);
    if (!selected || selected.selection_state !== "READY_FOR_NATIVE_PLAN") {
      setAlert({ type: "neutral", text: "这个地点暂时还没有足够的营业状态证据，不能用它启动正式 Journey。可以先保存私人散步。" });
      return;
    }
    const receiptId = discovery.receipt_id;
    void run("选择正式路线地点", async (stillCurrent) => {
      const response = await cityNexusApi.selectBootstrapCandidate(journeyId, receiptId, candidateId);
      if (!stillCurrent()) return;
      if (response.journey_id !== journeyId || !response.selected_place_id) {
        throw new Error("地点选择未绑定当前的签名 Journey。");
      }
      onFormalCandidateSelected(response.selected_place_id);
      setAlert({ type: "good", text: "地点已按服务器事实选定。现在由你确认正式计划，随后可使用真正的 Journey Operator。" });
    }, { label: "回到 Revolution 重新读取行程", action: () => window.location.assign("/revolution") });
  };

  const refreshSavedWalk = () => {
    void run("读取服务端路线", async (stillCurrent) => {
      const state = await cityNexusApi.getBootstrapShortlist(journeyId);
      if (!stillCurrent()) return;
      if (state.pocket_walk) {
        setWalk(state.pocket_walk);
        enter("walk");
        setAlert({ type: "good", text: "已从服务器重新读取路线状态；显示的是当前签名行程保存的事实。" });
      } else {
        setWalk(null);
        setAlert({ type: "neutral", text: "服务器当前没有已保存的私人散步。原路线没有被本页假定为已保存；可以回到结果页再决定是否保存。" });
      }
    }, { label: "重新读取路线状态", action: () => refreshSavedWalk() });
  };

  const saveWalk = () => {
    if (!discovery?.receipt_id || !first || !second || first === second) {
      setAlert({ type: "neutral", text: "先挑两个不同的真实地点。" });
      return;
    }
    const receipt = discovery.receipt_id;
    const firstId = first;
    const secondId = second;
    void run("保存私人散步", async (stillCurrent) => {
      const saved = await cityNexusApi.saveBootstrapDiscoveryPocketWalk(journeyId, {
        receipt_id: receipt,
        first_candidate_id: firstId,
        second_candidate_id: secondId,
        max_walk_minutes: null,
      });
      if (!stillCurrent()) return;
      if (saved.pocket_walk.journey_id !== journeyId ||
          saved.pocket_walk.plan_version_id !== null ||
          saved.pocket_walk.go_progress.physical_arrival_state !== "NOT_PHYSICAL_ARRIVAL_PROVEN") {
        throw new Error("服务端未返回符合当前 Journey 权限和事实等级的私人散步。");
      }
      setWalk(saved.pocket_walk);
      enter("walk");
      setAlert({ type: "good", text: "两站路线已保存到你的私人探索草稿。刷新页面也能恢复。" });
    }, (error) => recoveryForError(
      error,
      { label: "重新读取已保存路线", action: () => refreshSavedWalk() },
      { label: "返回检查所选地点", action: () => enter("results") },
    ));
  };

  const go = (action: "START" | "REPORT_FIRST_DONE" | "START_SECOND" | "REPORT_WALK_DONE" | "PAUSE" | "RESUME") => {
    if (!walk) return;
    const saved = walk;
    void run("更新散步进度", async (stillCurrent) => {
      const response = await cityNexusApi.transitionBootstrapPocketWalkGo(journeyId, {
        action,
        expected_revision: saved.go_progress.progress_revision,
        pocket_walk_revision: saved.revision,
        idempotency_key: crypto.randomUUID(),
      });
      if (!stillCurrent()) return;
      if (response.pocket_walk.pocket_walk_id !== saved.pocket_walk_id ||
          response.pocket_walk.revision !== saved.revision ||
          response.go_progress.physical_arrival_state !== "NOT_PHYSICAL_ARRIVAL_PROVEN" ||
          response.go_progress.progress_class !== "USER_REPORTED_PROGRESS") {
        throw new Error("收到不符合当前用户或路线版本的进度，未采用结果。");
      }
      setWalk(response.pocket_walk);
      setAlert({ type: "good", text: "状态已保存。到达与完成由你报告，不是手机 GPS 证明。" });
    }, { label: "重新读取路线进度", action: () => refreshSavedWalk() });
  };

  const stageNumber = { area: 1, category: 2, results: 3, walk: 4 }[stage];
  const sourceKind = discovery?.provider_provenance;
  const firstPlace = discovery?.candidates.find((item) => item.candidate_id === first);
  const secondPlace = discovery?.candidates.find((item) => item.candidate_id === second);
  const goState = walk?.go_progress.state;

  return (
    <section className="rev-quick" data-testid="rev-quick-explore">
      <header className="rev-quick-header">
        <div className="rev-quick-kicker">CITYNEXUS / EXPLORE</div>
        <h2>{stage === "walk" ? "你的私人散步路线" : "想去哪儿逛逛？"}</h2>
        <p>
          {stage === "area" && "你可以先告诉 AI 想怎么玩，再找地方。地图打不开也能继续。"}
          {stage === "category" && "位置已选好。挑一种兴趣，我们会查找附近的公开地点。"}
          {stage === "results" && "选两个真实返回的地点。没有可信结果就直接告诉你。"}
          {stage === "walk" && "保存了两个公开地点。你控制进度，我们不冒充 GPS 到场。"}
        </p>
        <div className="rev-quick-progress" aria-label="当前步骤">
          {["选地方", "选兴趣", "看结果", "去散步"].map((label, i) => (
            <span key={label} className={i + 1 === stageNumber ? "is-active" : i + 1 < stageNumber ? "is-done" : ""}>
              {i + 1}. {label}
            </span>
          ))}
        </div>
      </header>

      {alert && (
        <p className={"rev-quick-alert " + alert.type} role={alert.type === "error" ? "alert" : "status"}>
          {alert.text}
          {alert.recovery && (
            <>
              <br />
              <button type="button" className="rev-quick-secondary" onClick={alert.recovery.action} data-testid="rev-quick-error-recovery">
                {alert.recovery.label}
              </button>
            </>
          )}
        </p>
      )}
      {alert?.type === "error" && errorDetails && (
        <details className="rev-quick-internals" data-testid="rev-quick-error-details">
          <summary>技术详情（已隐藏原始响应和行程标识）</summary>
          <p>操作阶段：{errorDetails.phase}</p>
          <p>请求：{errorDetails.method ?? "未知"} {errorDetails.path ?? "未能确定路径"}</p>
          <p>HTTP 状态：{errorDetails.status ?? "未收到 HTTP 状态"}</p>
          <p>服务端原因码：{errorDetails.reasonCode ?? "响应未提供可安全显示的原因码"}</p>
          <p>归类：{errorDetails.classification}</p>
        </details>
      )}

      {stage === "area" && (
        <div className="rev-quick-pane" data-testid="rev-quick-area">
          <section className="rev-quick-ai" data-testid="rev-quick-ai-guide">
            <div className="rev-quick-ai-title">
              <strong>先跟 AI 说一句</strong>
              <small>{agentConfigured ? "Hermes 模型已配置，可请求真实建议" : "模型尚未接通，不影响手动探索"}</small>
            </div>
            <label htmlFor="rev-quick-ai-prompt">你想怎么玩？</label>
            <textarea
              id="rev-quick-ai-prompt"
              value={aiGoal}
              maxLength={360}
              rows={3}
              onChange={(event) => setAiGoal(event.target.value)}
              placeholder="例如：我在连城，今晚三个小时，想吃点当地特色，再轻松散散步。"
              disabled={busy}
            />
            <div className="rev-quick-ai-actions">
              <button
                type="button"
                onClick={consultHermes}
                disabled={busy || !agentConfigured}
                data-testid="rev-quick-consult-ai"
              >{busy ? "正在请教 AI…" : "让 AI 帮我想想 →"}</button>
              <span>点击后才会把上面这句话发给本机 wb2api 连接的外部模型，可能消耗积分；不会自动搜索地图或预订。</span>
            </div>
            {aiAdvice && (
              <div className="rev-quick-ai-response" role="status" data-testid="rev-quick-ai-response">
                <strong>{aiAdvice.verifiedTool ? "AI 给你的探索建议" : "模型这次未完成工具建议"}</strong>
                <p>{aiAdvice.reason}</p>
                {aiAdvice.category && <span>建议兴趣：{aiAdvice.category}（可以修改）</span>}
                <small>{aiAdvice.verifiedTool
                  ? "来自真实模型的只读工具建议，不是已规划路线，也没有发生 AgentRun。"
                  : "没有得到可校验的工具调用，不能当作 AI 规划已完成。"}{aiAdvice.model ? ` · ${aiAdvice.model}` : ""}</small>
              </div>
            )}
          </section>
          <label htmlFor="rev-quick-search">城市或地区</label>
          <div className="rev-quick-inline">
            <input
              id="rev-quick-search"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setCityResults([]); setCityFocus(null); setCityFocusLabel(null); setSelectedPin(null); }}
              placeholder="比如：连城县，福建龙岩"
              maxLength={120}
              disabled={busy}
            />
            <button type="button" onClick={cityLookup} disabled={busy} data-testid="rev-quick-find-city">
              {busy ? "查询中…" : "查找位置 →"}
            </button>
          </div>
          <p className="rev-quick-disclosure">
            {sampleProviderMode
              ? "点「查找位置」时只把地名发送给本机受控测试服务（TEST_PROVIDER），不会访问公开 Nominatim。不会读取手机 GPS。"
              : "点「查找位置」才会把这次输入的地名发送给公开 Nominatim 地图服务。不会读取手机 GPS。"}
          </p>
          {cityResults.length > 0 && (
            <div className="rev-quick-results" data-testid="rev-quick-city-results">
              <h3>是这些地方吗？</h3>
              {cityResults.map((item) => (
                <button
                  type="button"
                  className="rev-quick-city-option"
                  key={item.result_id}
                  onClick={() => {
                    // User chooses the geocoder's APPROXIMATE public area.
                    // This does NOT assert map tap, GPS, or physical arrival.
                    // Overpass is still only called on next explicit button.
                    setCityFocus({ latitude: item.latitude, longitude: item.longitude });
                    setCityFocusLabel(item.display_name || item.name);
                    setSelectedPin(null);
                    setTilesEnabled(false);
                    useCenter({
                      latitude: item.latitude,
                      longitude: item.longitude,
                    }, "EXPLICIT_GEOCODER_APPROX");
                  }}
                >
                  <strong>{item.display_name || item.name}</strong>
                  <small>{item.provider_provenance === "TEST_PROVIDER" ? "受控测试来源" : "公开地名搜索结果"} · 中心位置仅供参考</small>
                  <span>就从这个公开地区中心附近找（约2.5公里） →</span>
                </button>
              ))}
            </div>
          )}
          {cityFocus && (
            <div className="rev-quick-map-step">
              <h3>已找到：{cityFocusLabel || "当前地区"}</h3>
              <p className="rev-quick-disclosure">
                这个位置来自公开地名搜索，是城市或县城的<strong>大致中心</strong>，不是你的 GPS，
                不保证景点就在这里。你可以立即从附近 2.5 公里查找，或按需调整地图。
              </p>
              <button
                type="button"
                className="rev-quick-primary rev-quick-continue"
                data-testid="rev-quick-use-approx-center"
                onClick={() => {
                  // This explicit user selection makes a PUBLIC, approximate
                  // center the user-directed search area. It does NOT invent a
                  // MAP_TAP provenance or silently send provider requests.
                  useCenter({
                    latitude: cityFocus.latitude,
                    longitude: cityFocus.longitude,
                  }, "EXPLICIT_GEOCODER_APPROX");
                }}
              >直接从这片地区附近找 →</button>
              <details className="rev-quick-optional-map">
                <summary>想换具体位置？可以打开地图（可选）</summary>
                <p className="rev-quick-disclosure">加载地图瓦片需要单独点击“显示地图”，地图不显示也不影响上面的快捷入口。</p>
              {!tilesEnabled ? (
                <button
                  type="button"
                  className="rev-quick-secondary"
                  onClick={() => setTilesEnabled(true)}
                  data-testid="rev-quick-load-map"
                >
                  显示地图（仅此次向 OpenStreetMap 加载地图瓦片）
                </button>
              ) : (
                <>
                  <PublicCityAreaPicker
                    selectedCenter={selectedPin}
                    focusCenter={cityFocus}
                    onSelect={(point) => {
                      // A deliberate public map tap is already the user's manual
                      // center selection. Don't demand a second "confirm" click.
                      // No Overpass request occurs until the next explicit action.
                      setSelectedPin(point);
                      useCenter(point, "MAP_TAP");
                    }}
                  />
                </>
              )}
              </details>
            </div>
          )}
          <details className="rev-quick-internals">
            <summary>想用公开 OpenStreetMap 链接定位？（可选）</summary>
            <label htmlFor="rev-quick-map-link">公开地图链接</label>
            <input
              id="rev-quick-map-link"
              type="url"
              value={mapLink}
              onChange={(e) => setMapLink(e.target.value)}
              placeholder="https://www.openstreetmap.org/#map=13/25.7/116.75"
            />
            <button type="button" onClick={applyLink} data-testid="rev-quick-apply-map-link">使用这个公开地图位置</button>
          </details>
        </div>
      )}

      {stage === "category" && (
        <div className="rev-quick-pane" data-testid="rev-quick-category">
          <h3>这次想看些什么？</h3>
          <div className="rev-quick-categories">
            {categories.map((item) => (
              <button
                type="button"
                className={category === item.value ? "is-chosen" : ""}
                key={item.value}
                onClick={() => setCategory(item.value)}
                disabled={busy}
                aria-pressed={category === item.value}
              >
                <strong>{item.name}</strong><small>{item.subtitle}</small>
              </button>
            ))}
          </div>
          <p className="rev-quick-disclosure">
            {centerBasis === "EXPLICIT_GEOCODER_APPROX"
              ? "采用你刚才明确选定的公开县城/城市近似中心，查找半径约 2.5 公里。若不合适可返回改选，绝不是你的精确位置。"
              : "你已选择公开地图位置。"}
            {sampleProviderMode
              ? "点击下面的搜索按钮时，只向本机受控测试地点服务（TEST_PROVIDER）发送已选公开区域和类别。"
              : "点击下面的搜索按钮时，才会向 OpenStreetMap/Overpass 发送公开地图坐标和类别。"}
            不发送 GPS、身份令牌或私人行程。
          </p>
          {readinessStatus !== "ready" && (
            <p className="rev-quick-alert neutral" role="status">
              {readinessStatus === "checking"
                ? "正在检查地图服务是否可用（这一步不发起公开地点查询）…"
                : readinessStatus === "blocked"
                  ? "公开地点服务暂时不可用，不会擅自发送请求或假装找到地点。"
                  : "刚才无法检查地图服务。你可以重新检查，不需要重建旅程。"}
              {readinessStatus !== "checking" && (
                <button type="button" className="rev-quick-secondary" onClick={retryReadiness} disabled={busy}>
                  重新检查服务
                </button>
              )}
            </p>
          )}
          <div className="rev-quick-actions">
            <button
              type="button"
              className="rev-quick-primary"
              onClick={discover}
              disabled={busy || readiness?.status !== "READY"}
              data-testid="rev-quick-find-places"
            >
              {busy ? "正在寻找真实地点…" : "搜索附近地点 →"}
            </button>
            <button type="button" className="rev-quick-text-btn" onClick={() => enter("area")}>换一个位置</button>
          </div>
        </div>
      )}

      {stage === "results" && (
        <div className="rev-quick-pane" data-testid="rev-quick-results">
          <h3>这些地方怎么样？</h3>
          <p className="rev-quick-disclosure">
            {sourceKind === "TEST_PROVIDER"
              ? "以下全部是测试来源，不能当作实地开放的景点。"
              : sourceKind === "LIVE_PROVIDER"
                ? "地点名称和坐标来自实际公开服务。是否营业、门票和路线时间仍须自行核实。"
                : "数据来源未能验证，不要把这些地点当作已确认事实。"}
          </p>
          {discovery?.status !== "LIVE_RESULTS" || !discovery.candidates.length ? (
            <p>暂时没有找到符合条件的地点。可以换个类别，或重新选一个区域再试。</p>
          ) : (
            <>
              <p>点击卡片选择两站，先点的是第一站。</p>
              <div className="rev-quick-place-list">
                {discovery.candidates.map((candidate: BootstrapDiscoveryCandidate) => {
                  const chosenAs = first === candidate.candidate_id ? "第一站" : second === candidate.candidate_id ? "第二站" : null;
                  const source = candidateSource(candidate.source_url);
                  return (
                    <article className={chosenAs ? "is-picked" : ""} key={candidate.candidate_id}>
                      <button
                        type="button"
                        onClick={() => choose(candidate.candidate_id)}
                        data-testid={`rev-quick-select-${candidate.candidate_id}`}
                      >
                        <span className="rev-quick-pick">{chosenAs ?? "＋ 选择"}</span>
                        <strong>{candidate.name}</strong>
                        <small>{candidate.category} · {candidate.provider_provenance === "TEST_PROVIDER" ? "测试数据" : "OpenStreetMap 公开地点"}</small>
                      </button>
                      {source && (
                        <a href={source} rel="noopener noreferrer" target="_blank">
                          查看 OSM 原始来源（会打开外部网站） ↗
                        </a>
                      )}
                      {onFormalCandidateSelected && candidate.selection_state === "READY_FOR_NATIVE_PLAN" && (
                        <button
                          type="button"
                          className="rev-quick-formal"
                          disabled={busy}
                          onClick={() => chooseFormalJourney(candidate.candidate_id)}
                          data-testid={`rev-quick-formal-${candidate.candidate_id}`}
                        >想让 AI 继续照看正式行程？从这里开始（需要你确认计划）</button>
                      )}
                    </article>
                  );
                })}
              </div>
            </>
          )}
          {first && second && firstPlace && secondPlace && (
            <div className="rev-quick-save">
              <p>第一站：<strong>{firstPlace.name}</strong>　→　第二站：<strong>{secondPlace.name}</strong></p>
              <button type="button" className="rev-quick-primary" onClick={saveWalk} disabled={busy} data-testid="rev-quick-save">
                {busy ? "保存中…" : "保存这两个地点为我的私人散步 →"}
              </button>
            </div>
          )}
          <div className="rev-quick-actions">
            <button type="button" className="rev-quick-text-btn" onClick={() => enter("category")}>换个兴趣重找</button>
            <button type="button" className="rev-quick-text-btn" onClick={() => enter("area")}>换地图位置</button>
          </div>
        </div>
      )}

      {stage === "walk" && walk && (
        <div className="rev-quick-pane" data-testid="rev-quick-walk">
          <span className="rev-quick-success">✓ 已保存到你的私人行程</span>
          <div className="rev-quick-stop"><span>01</span><strong>{walk.first_stop.name}</strong></div>
          <div className="rev-quick-stop"><span>02</span><strong>{walk.second_stop.name}</strong></div>
          <h3>GO MODE · 出发</h3>
          <p>{goCopy[goState ?? "NOT_STARTED"]}</p>
          {goState === "NOT_STARTED" && <button type="button" className="rev-quick-primary" disabled={busy} onClick={() => go("START")}>开始散步 →</button>}
          {goState === "HEADING_TO_FIRST" && <button type="button" className="rev-quick-primary" disabled={busy} onClick={() => go("REPORT_FIRST_DONE")}>我完成了第一站 →</button>}
          {goState === "FIRST_STOP_DONE_SELF_REPORTED" && <button type="button" className="rev-quick-primary" disabled={busy} onClick={() => go("START_SECOND")}>前往第二站 →</button>}
          {goState === "HEADING_TO_SECOND" && <button type="button" className="rev-quick-primary" disabled={busy} onClick={() => go("REPORT_WALK_DONE")}>我完成了两站散步 ✓</button>}
          {goState === "PAUSED" && <button type="button" className="rev-quick-primary" disabled={busy} onClick={() => go("RESUME")}>继续散步 →</button>}
          {goState && !["NOT_STARTED", "WALK_DONE_SELF_REPORTED", "PAUSED"].includes(goState) && (
            <button type="button" className="rev-quick-secondary" disabled={busy} onClick={() => go("PAUSE")}>暂停散步</button>
          )}
          <p className="rev-quick-disclosure">进度由你本人报告并保存在服务器中，不等于 GPS 已证明到场。地图导航、支付和正式 AI Journey 是独立授权的功能。</p>
        </div>
      )}

      <details className="rev-quick-internals">
        <summary>技术信息（不影响正常使用）</summary>
        <p>城市结果提供公开地区的大致中心。点选结果即可继续；地图和 OSM 链接都是可选项。</p>
        <p>数据状态：{discovery?.status ?? "尚未搜索"} · {sourceKind ?? "来源未确定"}</p>
        <p>普通地点搜索不等于 Agent 自主推理。私人路线和进度由当前签名会话从服务器读取。</p>
      </details>
    </section>
  );
}
