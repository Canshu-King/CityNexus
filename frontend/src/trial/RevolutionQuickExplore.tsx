import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  CityNexusApiError,
  cityNexusApi,
  type BootstrapCitySearchResponse,
  type BootstrapCitySearchResult,
  type BootstrapDiscoveryCandidate,
  type BootstrapDiscoveryReadinessResponse,
  type BootstrapDiscoveryResponse,
  type BootstrapPocketWalkResponse,
  type BootstrapPocketWalkGoState,
} from "../api/citynexus";
import { parsePublicMapLink } from "../features/discovery/BootstrapDiscoveryPanel";
import { type PublicCityCenter } from "../features/discovery/PublicCityAreaPicker";
import { readTravelerBearer, subscribeTravelerBearer } from "../lib/travelerSession";
import { isOriginResponseUnusable } from "../lib/failureAttribution";
import { isReadDeadlineMissed } from "../lib/readDeadline";
import { isWriteDeadlineMissed } from "../lib/writeDeadline";
import { CityPicker } from "./mobile/CityPicker";
import { DiscoveryPlaceCard } from "./mobile/DiscoveryPlaceCard";
import { InterestPicker } from "./mobile/InterestPicker";
import { NamedPlaceSearch } from "./mobile/NamedPlaceSearch";
import type { MobileAiAdvice } from "./mobile/MobileAiPrompt";

/**
 * A HUMAN-SIZED entry to the exact signed R107/R108 endpoints.
 *
 * The labeled buttons send the two external HTTP operations. Geocoder results
 * provide approximate city centers; selecting one sets a manual coarse public
 * search area for the discovery request.
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
  HEADING_TO_FIRST: "正前往第一站。到达后请确认进度。",
  FIRST_STOP_DONE_SELF_REPORTED: "第一站完成（由你手动报告）。可以出发去第二站了。",
  HEADING_TO_SECOND: "正前往第二站。完成后你可以自己报告。",
  WALK_DONE_SELF_REPORTED: "两站散步已完成。",
  PAUSED: "路线已暂停，稍后可以继续。",
};

type AlertKind = "neutral" | "error" | "good";
type QuickRecovery = { label: string; action: () => void; disclosure?: string };
type QuickAlert = { type: AlertKind; text: string; recovery?: QuickRecovery };
type ExplorePhase =
  | "请教 AI"
  | "查找地名"
  | "检查地图服务"
  | "搜索附近真实地点"
  | "选择正式路线地点"
  | "查询地点详情"
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
    if (error instanceof CityNexusApiError) {
      if (error.status === 401) return "登录已过期，请重新进入行程。";
      if (error.status === 403) return "当前账号无权使用 AI 引导。";
      if (error.status === 404) return "AI 引导暂不可用。";
      if (error.status === 422) return "AI 没能理解这句话，换个说法试试。";
      if (error.status === 429) return "AI 当前繁忙。";
      if (error.status >= 500) return "AI 服务暂不可用。";
      return "AI 引导失败（HTTP " + error.status + "）。";
    }
    if (isReadDeadlineMissed(error)) return "等待 AI 超时。";
    if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) {
      return "AI 连接中断。";
    }
    return "AI 建议暂未生成。";
  }
  if (error instanceof CityNexusApiError) {
    const status = error.status;
    if (status === 401) return "登录已过期，请重新进入行程。";
    if (status === 403 && phase === "查找地名") return "无法用当前登录信息操作这条行程。";
    if (status === 403) return "当前账号无权执行「" + phase + "」。";
    if (status === 404) return "找不到当前行程，请重新进入。";
    if (status === 409) return "行程状态已更新，请刷新后继续。";
    if (status === 422) return "检查位置、类别或所选地点后重试。";
    if (status === 429) return "操作太频繁，请稍后重试。";
    if (status >= 500) {
      const writes = ["保存私人散步", "更新散步进度", "选择正式路线地点"].includes(phase);
      return writes
        ? phase + "暂时失败，请刷新行程确认状态。"
        : phase + "暂时失败，请稍后重试。";
    }
    return "「" + phase + "」失败（HTTP " + status + "），检查输入后重试。";
  }
  if (isOriginResponseUnusable(error)) {
    return "服务器返回内容异常，请刷新后重试「" + phase + "」。";
  }
  if (isReadDeadlineMissed(error) || isWriteDeadlineMissed(error)) {
    const writes = ["保存私人散步", "更新散步进度", "选择正式路线地点"].includes(phase);
    return writes
      ? "「" + phase + "」请求超时，请刷新行程确认结果。"
      : "「" + phase + "」请求超时，请稍后重试。";
  }
  if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) {
    const writes = ["保存私人散步", "更新散步进度", "选择正式路线地点"].includes(phase);
    return writes
      ? "「" + phase + "」连接中断，请刷新行程确认结果。"
      : "「" + phase + "」连接中断，请检查网络后重试。";
  }
  return "「" + phase + "」暂时无法完成，请检查所选内容后重试。";
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
  initialGoal,
  agentConfigured = false,
  agentChecking = false,
  onFormalCandidateSelected,
  onPocketWalkChange,
  onExplorationCenterLabelChange,
  onMemberAccessDenied,
}: {
  journeyId: string;
  cityName: string;
  initialGoal?: string;
  agentConfigured?: boolean;
  agentChecking?: boolean;
  onFormalCandidateSelected?: (placeId: string) => void;
  onPocketWalkChange?: (walk: BootstrapPocketWalkResponse | null) => void;
  onExplorationCenterLabelChange?: (label: string) => void;
  onMemberAccessDenied?: () => void;
}) {
  const sampleProviderMode = import.meta.env.VITE_REV_TRIAL_MODE === "sample";
  const [stage, setStage] = useState<Stage>("area");
  const [query, setQuery] = useState(cityName);
  const [aiGoal, setAiGoal] = useState(() => initialGoal?.trim() || `我在${cityName}，今天想轻松逛逛，别太累。有什么好玩的方向？`);
  const [aiAdvice, setAiAdvice] = useState<MobileAiAdvice | null>(null);
  const quickExploreRef = useRef<HTMLElement>(null);
  const pendingAiAdviceReveal = useRef(false);
  const [cityResults, setCityResults] = useState<BootstrapCitySearchResult[]>([]);
  const [cityProviderKey, setCityProviderKey] = useState<BootstrapCitySearchResponse["provider_key"] | undefined>(undefined);
  const [photonFallbackAvailable, setPhotonFallbackAvailable] = useState(false);
  const [cityFocus, setCityFocus] = useState<{ latitude: number; longitude: number } | null>(null);
  const [cityFocusLabel, setCityFocusLabel] = useState<string | null>(null);
  const [mapFallbackOpen, setMapFallbackOpen] = useState(false);
  const [centerBasis, setCenterBasis] = useState<"EXPLICIT_GEOCODER_APPROX" | "MAP_TAP" | "OSM_MAP_LINK" | null>(null);
  const [explorationCenterLabel, setExplorationCenterLabel] = useState<string | null>(null);
  const [tilesEnabled, setTilesEnabled] = useState(false);
  const [selectedPin, setSelectedPin] = useState<PublicCityCenter | null>(null);
  const [mapLink, setMapLink] = useState("");
  const [center, setCenter] = useState<{ latitude: number; longitude: number } | null>(null);
  const [category, setCategory] = useState<(typeof categories)[number]["value"]>("park/garden");
  const [placeName, setPlaceName] = useState("");
  const [readiness, setReadiness] = useState<BootstrapDiscoveryReadinessResponse | null>(null);
  const [readinessStatus, setReadinessStatus] = useState<"checking" | "ready" | "blocked" | "error">("checking");
  const [discovery, setDiscovery] = useState<BootstrapDiscoveryResponse | null>(null);
  const [first, setFirst] = useState<string | null>(null);
  const [second, setSecond] = useState<string | null>(null);
  const [walk, setWalk] = useState<BootstrapPocketWalkResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [alert, setAlert] = useState<QuickAlert | null>(null);
  const [errorDetails, setErrorDetails] = useState<ErrorDiagnostics | null>(null);

  // Reveal each accepted reply once; scrolling never moves keyboard focus.
  useLayoutEffect(() => {
    if (!aiAdvice || !pendingAiAdviceReveal.current) return;
    pendingAiAdviceReveal.current = false;
    const resultCard = quickExploreRef.current?.querySelector<HTMLElement>(".rev-quick-ai-response");
    if (!resultCard) return;

    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    resultCard.scrollIntoView({
      behavior: reducedMotion ? "instant" : "smooth",
      block: "nearest",
      inline: "nearest",
    });
  }, [aiAdvice]);
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
      pendingAiAdviceReveal.current = false;
      setCityResults([]);
      setDiscovery(null);
      setPlaceName("");
      setWalk(null);
      onPocketWalkChange?.(null);
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
      .catch((error: unknown) => {
        if (!valid()) return;
        setReadiness(null);
        setReadinessStatus("error");
        if (error instanceof CityNexusApiError && [401, 403].includes(error.status)) {
          setAlert({
            type: "error",
            text: "当前登录无法访问这段行程，请重新建立探索。原来的行程记录不会因此被删除。",
            recovery: onMemberAccessDenied
              ? { label: "重新开始探索", action: onMemberAccessDenied }
              : undefined,
          });
        }
      });
    const operationAtLoad = currentOperation.current;
    void cityNexusApi.getBootstrapShortlist(journeyId).then(async (state) => {
      if (!valid()) return;
      onPocketWalkChange?.(state.pocket_walk ?? null);
      if (state.pocket_walk) {
        setWalk(state.pocket_walk);
        setStage("walk");
      } else {
        const previous = await cityNexusApi.getCurrentBootstrapDiscovery(journeyId);
        if (!valid() || currentOperation.current !== operationAtLoad || !previous?.candidates.length || previous.journey_id !== journeyId) return;
        setDiscovery(previous);
        setStage("results");
        setAlert({ type: "neutral", text: "已恢复上次找到的地点，可以继续挑选。" });
      }
    }).catch((error: unknown) => {
      // A denied member can never re-authorize itself by reloading the same
      // URL; offer a human action instead of an endless 403 / reload loop.
      if (!valid()) return;
      if (error instanceof CityNexusApiError && [401, 403].includes(error.status)) {
        setAlert({
          type: "error",
          text: "这次登录没有权限读取旧行程。你可以重新开始，服务器原记录不会被清除。",
          recovery: onMemberAccessDenied
            ? { label: "重新开始探索", action: onMemberAccessDenied }
            : undefined,
        });
      }
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
    recovery: QuickRecovery | ((error: unknown) => QuickRecovery | null),
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
        const sessionDenied = error instanceof CityNexusApiError && [401, 403].includes(error.status);
        const errorRecovery = typeof recovery === "function" ? recovery(error) : recoveryForError(error, recovery);
        const nextRecovery = sessionDenied && onMemberAccessDenied
          ? { label: "重新开始探索", action: onMemberAccessDenied }
          : errorRecovery;
        setAlert({
          type: "error",
          text: sessionDenied
            ? "当前登录无法继续访问这段行程；重新开始不会删除服务器上的旧记录。"
            : messageForError(phase, error),
          ...(nextRecovery ? { recovery: nextRecovery } : {}),
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
    if (agentChecking) {
      setAlert({ type: "neutral", text: "AI 正在连接，稍等一下再提交。" });
      return;
    }
    if (!agentConfigured) {
      setAlert({ type: "neutral", text: "AI 建议暂不可用，可直接搜索地点。" });
      return;
    }
    if (goal.length < 4 || goal.length > 360) {
      setAlert({ type: "error", text: "用一句话告诉 AI 你想玩什么（4 到 360 个字）。" });
      return;
    }
    void run("请教 AI", async (stillCurrent) => {
      pendingAiAdviceReveal.current = false;
      setAiAdvice(null);
      const suggestion = await cityNexusApi.suggestTrialDiscovery(journeyId, goal);
      if (!stillCurrent()) return;
      const verified = suggestion.status === "MODEL_TOOL_SUGGESTION";
      const matched = verified ? categories.find((item) => item.value === suggestion.category) : null;
      if (matched) setCategory(matched.value);
      pendingAiAdviceReveal.current = true;
      setAiAdvice({
        category: matched?.name ?? null,
        reason: suggestion.reason,
        verifiedTool: verified && !!matched,
        model: suggestion.model ?? null,
      });
      setAlert(verified && matched
        ? { type: "good", text: "AI 建议已生成 · 下一步从公开地图选地点。" }
        : { type: "neutral", text: "已切换到手动选地点。" });
    }, () => ({
      label: "继续手动探索",
      action: () => {
        setErrorDetails(null);
        setAlert({ type: "neutral", text: "可以直接查找公开地名，或在地图上手选区域。" });
        document.getElementById("rev-quick-search")?.focus();
      },
    }));
  };

  const openMapFallback = () => {
    setMapFallbackOpen(true);
    setTilesEnabled(true);
    setSelectedPin(null);
    setErrorDetails(null);
    setAlert({
      type: "neutral",
      text: "地图底图来自 OpenStreetMap。轻触地图确定公开搜索区域；不会读取设备定位。",
    });
  };

  const mapFallbackRecovery: QuickRecovery = {
    label: "打开 OpenStreetMap 地图手选 →",
    disclosure: "点击后会加载 OpenStreetMap 地图底图；不会使用设备定位。",
    action: openMapFallback,
  };

  const cityLookup = (provider?: "nominatim" | "photon") => {
    const cityQuery = query.trim();
    if (cityQuery.length < 2 || cityQuery.length > 120) {
      setAlert({ type: "error", text: "请输入至少两个字的城市或地区，例如「连城县」。" });
      return;
    }
    setCityProviderKey(undefined);
    void run("查找地名", async (stillCurrent) => {
      // One explicit action sends the entered public city label to the
      // server-selected geocoder. There is no passive or typing request.
      const response = await cityNexusApi.bootstrapCitySearch(journeyId, {
        query: cityQuery,
        provider_consent: true,
        limit: 3,
        ...(provider === "photon" ? { provider } : {}),
      });
      if (!stillCurrent()) return;
      setCityProviderKey(response.provider_key);
      if (response.status !== "CITY_RESULTS" || !response.results.length) {
        setCityResults([]);
        const attemptedProvider = provider ?? response.provider_key;
        setPhotonFallbackAvailable(
          !sampleProviderMode && attemptedProvider !== "photon" && (
            response.status === "GEOCODER_UNAVAILABLE" ||
            response.status === "GEOCODER_RATE_LIMITED" ||
            response.status === "CITY_NO_RESULTS"
          ),
        );
        const message = response.status === "GEOCODER_RATE_LIMITED"
          ? "地名查找正在限流。你可以在地图上手选区域，或稍后再查。"
          : response.status === "GEOCODER_UNAVAILABLE"
            ? "地名查找暂时连不上。你可以在地图上手选区域。"
            : response.status === "GEOCODER_DISABLED"
              ? "当前环境未开启地名查找。你可以在地图上手选区域。"
              : "没找到这个地区。试试更完整的名称，或在地图上手选区域。";
        setAlert({
          type: "neutral",
          text: message,
          recovery: mapFallbackRecovery,
        });
        return;
      }
      setCityResults(response.results);
      setPhotonFallbackAvailable(false);
      setCityFocus(null);
      setSelectedPin(null);
      setMapFallbackOpen(false);
      setTilesEnabled(false);
      setAlert({
        type: "good",
        text: provider === "photon"
          ? "Photon 已找到公开地区。选一个结果后就能继续搜索附近地点。"
          : "已经找到公开地区。选一个结果后可以直接按“从这一带附近找”，地图是可选的。",
      });
    }, (error) => {
      if (error instanceof CityNexusApiError && error.status === 429) {
        return mapFallbackRecovery;
      }
      return recoveryForError(
        error,
        mapFallbackRecovery,
        { label: "检查并编辑地名", action: () => document.getElementById("rev-quick-search")?.focus() },
      );
    });
  };

  const useCenter = (point: { latitude: number; longitude: number }, basis: "EXPLICIT_GEOCODER_APPROX" | "MAP_TAP" | "OSM_MAP_LINK") => {
    if (!Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) return;
    setCenter(point);
    setCenterBasis(basis);
    const nextCenterLabel = basis === "EXPLICIT_GEOCODER_APPROX"
      ? cityFocusLabel || "已选地区中心"
      : basis === "OSM_MAP_LINK"
        ? `地图中心已选 · ${point.latitude.toFixed(3)}, ${point.longitude.toFixed(3)}`
        : "地图中心已选";
    setExplorationCenterLabel(nextCenterLabel);
    onExplorationCenterLabelChange?.(nextCenterLabel);
    setDiscovery(null);
    setFirst(null);
    setSecond(null);
    setCityResults([]);
    setAlert({ type: "good", text: "公开搜索区域已确认。接下来选一个你感兴趣的类别。" });
    setMapFallbackOpen(false);
    enter("category");
  };

  const applyLink = () => {
    const point = parsePublicMapLink(mapLink);
    if (!point) {
      setAlert({
        type: "error",
        text: "请粘贴公开 OpenStreetMap 地图链接，勿填私人地址。",
      });
      return;
    }
    setQuery("");
    setCityFocus(null);
    setCityFocusLabel(null);
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
        : { type: "error", text: "地图服务暂不可用，请检查服务状态或稍后重试。" });
    }, { label: "重新检查地图服务", action: () => retryReadiness() });
  };

  const discover = (namedQuery?: string) => {
    if (!center) {
      enter("area");
      setAlert({ type: "neutral", text: "先选一个公开地图区域。" });
      return;
    }
    if (!readiness || readiness.status !== "READY") {
      setAlert({ type: "error", text: "地图服务暂不可用，请稍后重试。" });
      return;
    }
    const name = namedQuery?.trim();
    if (name !== undefined && (readiness.provider !== "photon" || name.length < 2 || name.length > 120)) return;
    const selection = center;
    const chosenQuery = name ?? category;
    const consentedProvider = readiness.provider;
    void run("搜索附近真实地点", async (stillCurrent) => {
      // The explicitly labelled button is the ONE-use provider consent.
      const response = await cityNexusApi.bootstrapDiscovery(journeyId, {
        query: chosenQuery,
        ...(name !== undefined ? { query_mode: "name" as const } : {}),
        radius_m: 2500,
        limit: 3,
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider_consent: true,
        consented_provider: consentedProvider,
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
      if (response.status === "PROVIDER_UNAVAILABLE") {
        setAlert({
          type: "error",
          text: "地点服务未响应，本次没有找到地点。稍后再试。",
          recovery: { label: "修改搜索条件", action: () => enter("category") },
        });
        return;
      }
      if (response.status === "PROVIDER_DISABLED") {
        setAlert({
          type: "error",
          text: "公开地点搜索尚未开启。",
          recovery: {
            label: "重新检查地图服务",
            action: () => {
              enter("category");
              retryReadiness();
            },
          },
        });
        return;
      }
      if (response.status === "RATE_LIMITED") {
        setAlert({
          type: "error",
          text: "地点查询次数已达限制，请稍后重试。",
          recovery: { label: "修改搜索条件", action: () => enter("category") },
        });
        return;
      }
      if (response.status !== "LIVE_RESULTS" || response.candidates.length === 0) {
        setAlert({ type: "neutral", text: "没找到地点，调整类别或位置后再试。" });
      } else if (response.candidates.length === 1) {
        setAlert(null);
      } else {
        setAlert({
          type: "good",
          text: `找到 ${response.candidates.length} 个公开地点。现在可以查看并挑选两站。`,
        });
      }
    }, (error) => recoveryForError(
      error,
      { label: "返回搜索条件", action: () => enter("category") },
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

  const refreshPlaceFacts = (candidateId: string) => {
    const receiptId = discovery?.receipt_id;
    if (!receiptId) return;
    void run("查询地点详情", async (stillCurrent) => {
      const result = await cityNexusApi.refreshBootstrapPlaceFacts(journeyId, receiptId, candidateId);
      if (!stillCurrent()) return;
      if (result.journey_id !== journeyId || result.candidate.candidate_id !== candidateId) {
        throw new Error("地点详情与当前选择不一致");
      }
      setDiscovery((current) => current?.receipt_id === receiptId ? {
        ...current,
        candidates: current.candidates.map((place) => place.candidate_id === candidateId ? result.candidate : place),
      } : current);
    }, { label: "回到地点列表", action: () => enter("results") });
  };

  const chooseFormalJourney = (candidateId: string) => {
    if (!discovery?.receipt_id || !onFormalCandidateSelected) return;
    const selected = discovery.candidates.find((item) => item.candidate_id === candidateId);
    if (!selected || selected.selection_state !== "READY_FOR_NATIVE_PLAN") {
      setAlert({ type: "neutral", text: "营业信息不足，暂不能启动行程；可先保存私人散步。" });
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
        onPocketWalkChange?.(state.pocket_walk);
        enter("walk");
        setAlert({ type: "good", text: "已从服务器重新读取路线状态；显示的是当前签名行程保存的事实。" });
      } else {
        setWalk(null);
        onPocketWalkChange?.(null);
        setAlert({ type: "neutral", text: "暂无已保存的私人散步。返回结果页保存路线。" });
      }
    }, { label: "重新读取路线状态", action: () => refreshSavedWalk() });
  };

  const saveWalk = () => {
    if (!discovery?.receipt_id || !first || !second || first === second) {
      setAlert({ type: "neutral", text: "请选择两个不同地点。" });
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
      onPocketWalkChange?.(saved.pocket_walk);
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
      onPocketWalkChange?.(response.pocket_walk);
      setAlert({ type: "good", text: "进度已保存。" });
    }, { label: "重新读取路线进度", action: () => refreshSavedWalk() });
  };

  const stageNumber = { area: 1, category: 2, results: 3, walk: 4 }[stage];
  const sourceKind = discovery?.provider_provenance;
  const isPartialLiveResult = discovery?.status === "LIVE_RESULTS" && discovery.candidates.length === 1;
  const filterSummary = discovery?.filter_summary;
  const safeFilterSummary = filterSummary &&
    Number.isSafeInteger(filterSummary.raw_count) &&
    filterSummary.raw_count >= 0 &&
    Number.isSafeInteger(filterSummary.accepted_count) &&
    filterSummary.accepted_count >= 0 &&
    filterSummary.accepted_count <= filterSummary.raw_count
    ? filterSummary
    : null;
  const firstPlace = discovery?.candidates.find((item) => item.candidate_id === first);
  const secondPlace = discovery?.candidates.find((item) => item.candidate_id === second);
  const goState = walk?.go_progress.state;

  const focusAiPrompt = () => {
    const prompt = quickExploreRef.current?.querySelector<HTMLTextAreaElement>("#rev-quick-ai-prompt");
    if (!prompt) return;
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    prompt.scrollIntoView({
      behavior: reducedMotion ? "instant" : "smooth",
      block: "center",
      inline: "nearest",
    });
    prompt.focus({ preventScroll: true });
  };

  return (
    <section ref={quickExploreRef} className="rev-quick" data-testid="rev-quick-explore">
      <header className="rev-quick-header">
        <div className="rev-quick-kicker">CITYNEXUS / EXPLORE</div>
        <h2>
          {stage === "walk"
            ? "你的私人散步路线"
            : center && explorationCenterLabel
              ? `本次探索位置：${explorationCenterLabel}`
              : "想去哪儿逛逛？"}
        </h2>
        <p>
          {stage === "area" && "先选地区，再挑兴趣和地点。AI 只在你点击后参与；地图打不开也能继续。"}
          {stage === "category" && "位置已选好。挑一种兴趣，我们会查找附近的公开地点。"}
          {stage === "results" && !isPartialLiveResult && "选两个真实返回的地点。没有可信结果就直接告诉你。"}
          {stage === "walk" && "保存了两个公开地点。你可以在行程中手动更新到访进度。"}
        </p>
        {stage === "area" && agentConfigured && (
          <button
            type="button"
            className="rev-quick-text-btn"
            data-testid="rev-quick-ask-ai-shortcut"
            onClick={focusAiPrompt}
          >
            问 AI
          </button>
        )}
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
              {alert.recovery.disclosure && (
                <small className="rev-quick-recovery-disclosure">{alert.recovery.disclosure}</small>
              )}
              <button type="button" className="rev-quick-secondary" onClick={alert.recovery.action} data-testid="rev-quick-error-recovery">
                {alert.recovery.label}
              </button>
            </>
          )}
        </p>
      )}
      {alert?.type === "error" && errorDetails && (
        <details className="rev-quick-internals" data-testid="rev-quick-error-details">
          <summary>技术详情</summary>
          <p>操作阶段：{errorDetails.phase}</p>
          <p>请求：{errorDetails.method ?? "未知"} {errorDetails.path ?? "未能确定路径"}</p>
          <p>HTTP 状态：{errorDetails.status ?? "未收到 HTTP 状态"}</p>
          <p>服务端原因码：{errorDetails.reasonCode ?? "未知"}</p>
          <p>归类：{errorDetails.classification}</p>
        </details>
      )}

      {stage === "area" && (
        <>
          <CityPicker
            query={query}
            cityResults={cityResults}
            cityFocus={cityFocus}
            cityFocusLabel={cityFocusLabel}
            mapFallbackOpen={mapFallbackOpen}
            photonFallbackAvailable={photonFallbackAvailable}
            selectedPin={selectedPin}
            busy={busy}
            cityProviderKey={cityProviderKey}
            sampleProviderMode={sampleProviderMode}
            tilesEnabled={tilesEnabled}
            mapLink={mapLink}
            aiGoal={aiGoal}
            agentConfigured={agentConfigured}
            agentChecking={agentChecking}
            aiAdvice={aiAdvice}
            onQueryChange={(value) => {
              setQuery(value);
              setCityResults([]);
              setCityProviderKey(undefined);
              setPhotonFallbackAvailable(false);
              setCityFocus(null);
              setCityFocusLabel(null);
              setSelectedPin(null);
              setMapFallbackOpen(false);
              setTilesEnabled(false);
            }}
            onCityLookup={cityLookup}
            onPhotonCityLookup={() => cityLookup("photon")}
            onCityResultSelect={(item) => {
              // Keep the geocoder's approximate-area source distinct from
              // map taps, GPS, and arrival; Overpass starts on the next button.
              setCityFocus({ latitude: item.latitude, longitude: item.longitude });
              setCityFocusLabel(item.display_name || item.name);
              setSelectedPin(null);
              setTilesEnabled(false);
              setAlert({
                type: "good",
                text: "已选中公开地区的大致中心。你可以直接从附近查找，也可以先打开地图微调。",
              });
            }}
            onUseCenter={useCenter}
            onEnableTiles={() => setTilesEnabled(true)}
            onMapSelect={(point) => {
              // A deliberate public map tap is already the user's manual
              // center selection. Don't demand a second "confirm" click.
              // No public POI request occurs until the next explicit action.
              setSelectedPin(point);
              useCenter(point, "MAP_TAP");
            }}
            onMapLinkChange={setMapLink}
            onApplyMapLink={applyLink}
            onAiGoalChange={setAiGoal}
            onAskAi={() => { void consultHermes(); }}
          />
        </>
      )}

      {stage === "category" && (
        <>
        <InterestPicker
          categories={categories}
          category={category}
          centerBasis={centerBasis}
          sampleProviderMode={sampleProviderMode}
          expectedRecipient={readiness?.expected_recipient ?? null}
          readinessStatus={readinessStatus}
          readinessReady={readiness?.status === "READY"}
          busy={busy}
          onCategoryChange={setCategory}
          onRetryReadiness={retryReadiness}
          onDiscover={() => discover()}
          onChangeArea={() => enter("area")}
        />
        {readiness?.provider === "photon" && (
          <NamedPlaceSearch
            value={placeName}
            onChange={setPlaceName}
            onSearch={() => discover(placeName)}
            disabled={busy || readiness.status !== "READY"}
            recipient={readiness.expected_recipient}
          />
        )}
        </>
      )}

      {stage === "results" && (
        <div className="rev-quick-pane" data-testid="rev-quick-results">
          <h3>这些地方怎么样？</h3>
          <p className="rev-quick-disclosure">
            {sourceKind === "TEST_PROVIDER"
              ? "示例地点（测试来源）。"
              : sourceKind === "LIVE_PROVIDER"
                ? "来源：公开地名服务 · 营业、票价和路线信息待补充。"
                : "地点来源待确认。"}
          </p>
          {discovery?.status === "PROVIDER_UNAVAILABLE" ? (
            <p>地点服务暂未返回结果。</p>
          ) : discovery?.status === "PROVIDER_DISABLED" ? (
            <p>当前试玩环境尚未启用公开地点搜索。</p>
          ) : discovery?.status === "RATE_LIMITED" ? (
            <p>地图服务限制了这次请求，暂时不能判断附近地点。</p>
          ) : discovery?.status !== "LIVE_RESULTS" || !discovery.candidates.length ? (
            safeFilterSummary && discovery?.status === "LIVE_ZERO_RESULTS" && safeFilterSummary.accepted_count === 0 ? (
              <p role="status" data-testid="rev-quick-filter-result">
                地图返回 {safeFilterSummary.raw_count} 条，符合条件 {safeFilterSummary.accepted_count} 处。
              </p>
            ) : (
              <p>没有匹配地点。换个类别或搜索区域。</p>
            )
          ) : (
            <>
              {isPartialLiveResult ? (
                <p role="status" data-testid="rev-quick-partial-result">
                  {first
                    ? "第 1 站已选；换类别或地图位置找第 2 站。"
                    : "已找到 1 处；点卡片加入第 1 站，换类别或地图位置找第 2 站。"}
                </p>
              ) : (
                <p role="status" aria-live="polite">
                  {!first
                    ? "尚未选地点。点选一处加入第 1 站，再点另一处加入第 2 站。"
                    : !second
                      ? "第 1 站已选；点另一处加入第 2 站。"
                      : "第 1 站和第 2 站已选；点选卡片可调整选择。"}
                </p>
              )}
              <div className="rev-quick-place-list">
                {discovery.candidates.map((candidate: BootstrapDiscoveryCandidate) => {
                  const chosenAs = first === candidate.candidate_id ? "第一站" : second === candidate.candidate_id ? "第二站" : null;
                  return (
                    <DiscoveryPlaceCard
                      key={candidate.candidate_id}
                      candidate={candidate}
                      chosenAs={chosenAs}
                      busy={busy}
                      canStartJourney={Boolean(onFormalCandidateSelected)}
                      onChoose={choose}
                      onStartJourney={chooseFormalJourney}
                      onRefreshFacts={refreshPlaceFacts}
                    />
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
          <p className="rev-quick-disclosure">到访进度由你确认；导航和支付需单独授权。</p>
        </div>
      )}

      <details className="rev-quick-internals">
        <summary>技术信息</summary>
        <p>城市结果提供公开地区的大致中心。点选结果即可继续；地图和 OSM 链接都是可选项。</p>
        <p>数据状态：{discovery?.status ?? "尚未搜索"} · {sourceKind ?? "来源未确定"}</p>
        {safeFilterSummary && (
          <p data-testid="rev-quick-filter-summary">
            原始候选：{safeFilterSummary.raw_count} 条 · 可用地点：{safeFilterSummary.accepted_count} 处
          </p>
        )}
        <p>地点来源：{sourceKind ?? "待确定"}。私人路线与进度来自当前行程。</p>
      </details>
    </section>
  );
}
