import { useEffect, useState } from "react";
import { BootstrapDiscoveryPanel } from "../features/discovery/BootstrapDiscoveryPanel";
import { RevolutionQuickExplore } from "./RevolutionQuickExplore";
import { BootstrapJourneyStartPanel } from "../features/discovery/BootstrapJourneyStartPanel";
import { LiveRecovery } from "../features/execution/LiveRecovery";
import { cityNexusApi, type AgentRuntimeStatus, type BootstrapPocketWalkResponse } from "../api/citynexus";
import { RevolutionMobileNav, type RevolutionMobileTab } from "./RevolutionMobileNav";
import { AgentWorkStatus } from "./mobile/AgentWorkStatus";
import { MobileHermesRun } from "./mobile/MobileHermesRun";
import { MobileCompatAgentActivity } from "./mobile/MobileCompatAgentActivity";
import {
  clearTravelerBearer,
  readTravelerBearer,
  readTravelerIdentity,
  storeTravelerIdentity,
} from "../lib/travelerSession";
import "./RevolutionFirstLook.css";
import "./RevolutionUsability.css";
import "./RevolutionQuickExplore.css";
import "./RevolutionMobileV1.css";

const STORAGE_KEY = "citynexus.revolution.firstlook.journey";
const RECENT_JOURNEYS_KEY = "citynexus.revolution.firstlook.recent-journeys";

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

async function postJson<T>(path: string, payload: object, bearerOverride?: string): Promise<T> {
  // Use the fresh token for the new Journey without replacing the existing
  // browser session until the entire create flow has succeeded.
  const bearer = bearerOverride === undefined ? readTravelerBearer() : bearerOverride;
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(bearer ? { Authorization: `Bearer ${bearer}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    // Do not surface hidden tokens or the entire server response as UI copy.
    let reason = "服务器未能完成请求";
    try {
      const json: unknown = await response.json();
      if (json && typeof json === "object" && "detail" in json) {
        const detail = (json as { detail?: unknown }).detail;
        if (typeof detail === "string") reason = detail.slice(0, 240);
      }
    } catch {
      // The status still names the failure when upstream returns non-JSON.
    }
    throw new Error("HTTP " + response.status + "：" + reason);
  }
  return response.json() as Promise<T>;
}

function freshCityCode(): string {
  // DRAFT codes are private application keys; the catalog resolver supplies canonical city identity.
  return "CN-RV-" + crypto.randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase();
}

export function RevolutionFirstLook() {
  const [cityName, setCityName] = useState("连城");
  const [journey, setJourney] = useState<TrialJourney | null>(loadRecentJourney);
  const [recentJourneys, setRecentJourneys] = useState<TrialJourney[]>(loadRecentJourneys);
  const [explorationTitle, setExplorationTitle] = useState<{ journeyId: string; label: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [legacyRestoreFailed, setLegacyRestoreFailed] = useState(false);
  const [candidateForJourney, setCandidateForJourney] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<RevolutionMobileTab>("explore");
  const [pocketWalk, setPocketWalk] = useState<BootstrapPocketWalkResponse | null>(null);
  const [agentRuntime, setAgentRuntime] = useState<AgentRuntimeStatus | null>(null);
  const [agentCheckError, setAgentCheckError] = useState<string | null>(null);
  const sample = import.meta.env.VITE_REV_TRIAL_MODE === "sample";

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
  const agentStatusTitle = agentStatusChecking
    ? "正在连接 AI…"
    : nativeHermesReady
    ? "Hermes 工具已就绪"
    : agentCheckError
      ? "AI 状态未知"
      : nativeHermesConfigured
        ? "Hermes 暂不可用"
        : agentConfigured
          ? "AI 网关已配置"
          : "AI 未启用";
  const agentStatusDetail = agentStatusChecking
    ? "正在读取本机 AI 服务状态。"
    : nativeHermesReady
    ? "可以提交行程需求并查看助手记录。"
    : nativeHermesConfigured
      ? "助手工具暂不可用，可先浏览行程。"
      : agentConfigured
        ? "AI 网关已配置，可在行程页提交需求。"
        : "AI 未启用，可先探索公开地点。";

  const start = async (cityNameOverride?: string, options: { freshSession?: boolean } = {}) => {
    const label = (cityNameOverride ?? cityName).trim();
    if (label.length < 2 || label.length > 60) {
      setError("请输入 2 至 60 个字符的城市或地区名称，例如连城、厦门或杭州。");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      // Keep one signed traveler while the person starts Journeys in other
      // cities. A new traveler is issued only when this browser has no paired
      // signed session; both session fields commit after Journey creation.
      const existingBearer = options.freshSession ? null : readTravelerBearer();
      const existingIdentity = options.freshSession ? null : readTravelerIdentity();
      const traveler = existingBearer
        ? { id: (await cityNexusApi.getTravelerSession()).traveler_id, access_token: existingBearer }
        : await postJson<{ id: string; access_token?: string }>("/travelers", {
          display_name: "Revolution Lab explorer",
          locale: "zh-CN",
          timezone: "Asia/Shanghai",
        }, "");
      if (!traveler.access_token) {
        throw new Error("服务器没有发放可用于私人探索的签名会话，请检查本地鉴权配置。");
      }
      const startAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
      const endAt = new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString();
      const cityCode = freshCityCode();
      const created = await postJson<{ id: string }>("/journeys", {
        traveler_id: traveler.id,
        title: label + " · Revolution Explore",
        city_code: cityCode,
        timezone: "Asia/Shanghai",
        start_at: startAt,
        end_at: endAt,
        // Open-ended discovery starts from user intent; arrival/departure
        // anchors belong to a later confirmed plan.
        budget: { amount_minor: 100000, currency: "CNY" },
        party_size: 1,
      }, traveler.access_token);
      if (!created.id) throw new Error("服务器未返回 Journey ID。");
      if (!existingIdentity || existingIdentity.travelerId !== traveler.id) {
        storeTravelerIdentity(traveler.access_token, traveler.id);
      }
      const next: TrialJourney = {
        id: created.id,
        cityCode,
        cityName: label,
        status: "DRAFT",
        ownerTravelerId: traveler.id,
      };
      setRecentJourneys(rememberJourney(next));
      setExplorationTitle(null);
      setJourney(next);
      setActiveTab("explore");
      setPocketWalk(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建探索草稿失败。");
      if (readTravelerBearer()) setLegacyRestoreFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const restartWithNewSession = () => {
    const pointer = readLegacyJourneyPointer();
    setJourney(null);
    setPocketWalk(null);
    setRecentJourneys([]);
    setLegacyRestoreFailed(false);
    setError(null);
    void start(pointer?.cityName, { freshSession: true });
  };

  const resumeRecentJourney = (saved: TrialJourney) => {
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
    if (!journey) return;
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
    setNotice("Journey 已启动。前往「行程」提交需求或查看动态。");
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

  const navigateMobile = (tab: RevolutionMobileTab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="rev-firstlook rev-mobile-v1" data-testid="revolution-first-look">
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
          {agentRuntime && <small>{agentRuntime.runtime_identity} · {agentRuntime.ai_state ?? "UNKNOWN"}</small>}
        </details>
      </header>

      <main className="rev-firstlook-content">
        {!journey ? (
          activeTab === "explore" ? (
            <section className="rev-firstlook-hero" data-testid="rev-mobile-welcome">
              <span className="rev-firstlook-eyebrow">CITYNEXUS / DISCOVER</span>
              <h1>想去哪儿，<br />就从那里开始。</h1>
              <p>输入一个城市或地区，接下来可以用自然语言告诉 AI 你想怎么玩。</p>
              <form onSubmit={(event) => { event.preventDefault(); void start(); }}>
                <label htmlFor="rev-firstlook-city">目的地</label>
                <div className="rev-firstlook-form-row">
                  <input
                    id="rev-firstlook-city"
                    autoComplete="off"
                    value={cityName}
                    maxLength={60}
                    disabled={busy}
                    placeholder="例如：连城、厦门、杭州"
                    onChange={(event) => setCityName(event.target.value)}
                    data-testid="rev-firstlook-city"
                  />
                  <button disabled={busy} type="submit" data-testid="rev-firstlook-start">
                    {busy ? "正在准备…" : "开始探索 →"}
                  </button>
                </div>
              </form>
              {recentJourneys.length > 0 && (
                <div className="rev-firstlook-recent-journeys" data-testid="rev-recent-journeys">
                  <h2>最近的行程</h2>
                  {recentJourneys.map((saved) => (
                    <button
                      key={saved.id}
                      type="button"
                      className="rev-mobile-secondary"
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
              {legacyRestoreFailed && (
                <button
                  type="button"
                  className="rev-mobile-secondary"
                  disabled={busy}
                  onClick={restartWithNewSession}
                  data-testid="rev-firstlook-new-session"
                >
                  用新行程继续
                </button>
              )}
              <p className="rev-mobile-truth">点击后先创建行程草稿。</p>
            </section>
          ) : activeTab === "trips" ? (
            <section className="rev-mobile-panel" data-testid="rev-mobile-empty-trips">
              <span className="rev-firstlook-eyebrow">TRIPS</span>
              <h2>行程</h2>
              <p>开始探索一个地区后，你保存的路线和出发进度会显示在这里。</p>
              <button type="button" data-testid="rev-mobile-empty-start" onClick={() => navigateMobile("explore")}>
                开始探索 →
              </button>
            </section>
          ) : (
            <section className="rev-mobile-panel" data-testid="rev-mobile-empty-me">
              <span className="rev-firstlook-eyebrow">CITYNEXUS</span>
              <h2>我的</h2>
              <p>开始探索后，这里会显示你的地区和助手状态。</p>
              <div className="rev-mobile-account-line">
                <span>AI 助手</span><strong>{agentStatusChecking ? "正在连接" : nativeHermesReady ? "Hermes 工具已就绪" : agentConfigured ? "网关已配置" : "当前未配置"}</strong>
              </div>
            </section>
          )
        ) : (
          <>
            <section className="rev-mobile-tabpanel" hidden={activeTab !== "explore"} data-testid="rev-mobile-screen-explore">
              <section className="rev-firstlook-journey">
                <div>
                  <span className="rev-firstlook-eyebrow">正在探索</span>
                  <h1>{explorationTitle?.journeyId === journey.id ? explorationTitle.label : journey.cityName}</h1>
                  <p>想怎么走？先聊一句，再从真实地点中选择。</p>
                </div>
                <button type="button" onClick={() => switchCity()} className="rev-firstlook-reset">
                  换地区
                </button>
              </section>
              {notice && <p className="rev-firstlook-notice" role="status">{notice}</p>}
              {journey.status === "DRAFT" ? (
                <section className="rev-firstlook-real-ui" aria-label="地点探索与私人散步">
                  <RevolutionQuickExplore
                    key={journey.id}
                    journeyId={journey.id}
                    cityName={journey.cityName}
                    onExplorationCenterLabelChange={(label) => {
                      setExplorationTitle({ journeyId: journey.id, label });
                    }}
                    agentConfigured={Boolean(agentConfigured)}
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
              {journey.status === "DRAFT" && candidateForJourney && (
                <section className="rev-firstlook-start-plan" data-testid="revolution-agent-start-journey">
                  <h2>确认正式行程</h2>
                  <p>费用信息未知；预订和付款需另行确认。</p>
                  <BootstrapJourneyStartPanel
                    journeyId={journey.id}
                    placeId={candidateForJourney}
                    onStarted={finishStartingJourney}
                    onCancel={() => setCandidateForJourney(null)}
                  />
                </section>
              )}
              {journey.status === "ACTIVE" ? (
                <section className="rev-firstlook-real-ui" aria-label="真正的 Journey Operator" data-testid="revolution-real-operator">
                  <section className="rev-mobile-panel">
                    <h2>当前行程</h2>
                    <p>这里显示行程监测、助手运行记录和待确认操作。</p>
                  </section>
                  <AgentWorkStatus journeyId={journey.id} visible={activeTab === "trips"} />
                  <MobileCompatAgentActivity journeyId={journey.id} visible={activeTab === "trips"} />
                  <MobileHermesRun journeyId={journey.id} visible={activeTab === "trips"} />
                  <LiveRecovery journeyId={journey.id} journeyStatus="ACTIVE" />
                </section>
              ) : (
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
                  <span>AI 助手</span><strong>{agentStatusChecking ? "正在连接" : nativeHermesReady ? "Hermes 工具已就绪" : agentConfigured ? "网关已配置" : "当前未配置"}</strong>
                </div>
                <div className="rev-mobile-account-line">
                  <span>行程状态</span><strong>{journey.status === "ACTIVE" ? "已正式启动" : "私人探索草稿"}</strong>
                </div>
                <p>进度属于当前行程；地点来源见卡片，到达由你确认。</p>
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
