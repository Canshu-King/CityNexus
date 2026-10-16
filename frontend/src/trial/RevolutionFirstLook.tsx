import { useEffect, useState } from "react";
import { BootstrapDiscoveryPanel } from "../features/discovery/BootstrapDiscoveryPanel";
import { RevolutionQuickExplore } from "./RevolutionQuickExplore";
import { BootstrapJourneyStartPanel } from "../features/discovery/BootstrapJourneyStartPanel";
import { LiveRecovery } from "../features/execution/LiveRecovery";
import { cityNexusApi, type AgentRuntimeStatus, type BootstrapPocketWalkResponse } from "../api/citynexus";
import { RevolutionMobileNav, type RevolutionMobileTab } from "./RevolutionMobileNav";
import { AgentWorkStatus } from "./mobile/AgentWorkStatus";
import { MobileHermesRun } from "./mobile/MobileHermesRun";
import {
  clearTravelerBearer,
  readTravelerBearer,
  storeTravelerBearer,
} from "../lib/travelerSession";
import "./RevolutionFirstLook.css";
import "./RevolutionUsability.css";
import "./RevolutionQuickExplore.css";
import "./RevolutionMobileV1.css";

const STORAGE_KEY = "citynexus.revolution.firstlook.journey";

type TrialJourney = {
  id: string;
  cityCode: string;
  cityName: string;
  status: "DRAFT" | "ACTIVE";
};

function loadRecentJourney(): TrialJourney | null {
  // A local record is only a navigation pointer. The signed bearer remains the
  // server's sole member authority and is never copied to localStorage.
  if (!readTravelerBearer()) return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const value = raw ? JSON.parse(raw) as Partial<TrialJourney> : null;
    if (!value || typeof value.id !== "string" || typeof value.cityCode !== "string" ||
        typeof value.cityName !== "string") return null;
    return { id: value.id, cityCode: value.cityCode, cityName: value.cityName,
             status: value.status === "ACTIVE" ? "ACTIVE" : "DRAFT" };
  } catch {
    return null;
  }
}

async function postJson<T>(path: string, payload: object): Promise<T> {
  const bearer = readTravelerBearer();
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
  // The arbitrary DRAFT code is a private application namespace, NOT a claim
  // that the supplied place has a canonical city identity or verified catalog.
  return "CN-RV-" + crypto.randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase();
}

export function RevolutionFirstLook() {
  const [cityName, setCityName] = useState("连城");
  const [journey, setJourney] = useState<TrialJourney | null>(loadRecentJourney);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
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
      if (!cancelled) setAgentCheckError("无法读取后端 Agent 状态，尚未证明模型连接可用。");
    });
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
  const agentStatusTitle = nativeHermesReady
    ? "Hermes 工具已就绪"
    : agentCheckError
      ? "AI 状态未知"
      : nativeHermesConfigured
        ? "Hermes 暂不可用"
        : agentConfigured
          ? "AI 网关已配置"
          : "AI 未启用";
  const agentStatusDetail = nativeHermesReady
    ? "原生 Hermes 工具网关已就绪；这只代表连接准备好，不代表已经发生运行。"
    : nativeHermesConfigured
      ? "已发现原生 Hermes 工具网关，但当前未确认可用；页面只会显示服务器实际返回的运行记录。"
      : agentConfigured
        ? "模型网关已配置，但尚不代表真正执行过 AgentRun。公开地点搜索也不是 AI 自主规划。"
        : "你可以先探索真实公开地点，不需要先配置 AI。";

  const start = async () => {
    const label = cityName.trim();
    if (label.length < 2 || label.length > 60) {
      setError("请输入 2 至 60 个字符的城市或地区名称，例如连城、厦门或杭州。");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      // Create through the real product API with a signed member token. Do not
      // insert test rows, localStorage identities, or forged Journey objects.
      const traveler = await postJson<{ id: string; access_token?: string }>("/travelers", {
        display_name: "Revolution Lab explorer",
        locale: "zh-CN",
        timezone: "Asia/Shanghai",
      });
      if (!traveler.access_token) {
        throw new Error("服务器没有发放可用于私人探索的签名会话，请检查本地鉴权配置。");
      }
      storeTravelerBearer(traveler.access_token);
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
        // This DRAFT is for open-ended discovery. Don't manufacture a
        // physical arrival/departure anchor just to satisfy the old wizard.
        budget: { amount_minor: 100000, currency: "CNY" },
        party_size: 1,
      });
      if (!created.id) throw new Error("服务器未返回 Journey ID。");
      const next: TrialJourney = { id: created.id, cityCode, cityName: label, status: "DRAFT" };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setJourney(next);
      setActiveTab("explore");
      setPocketWalk(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建探索草稿失败。");
    } finally {
      setBusy(false);
    }
  };

  const switchCity = () => {
    // Only remove this isolated trial's pointer; never delete a Journey or
    // alter any production data. Server-side privacy still gates old boards.
    localStorage.removeItem(STORAGE_KEY);
    clearTravelerBearer();
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
    setNotice("正式 Journey 已启动。这里是原生 Journey Operator；点击照看行程后，再由你提交需求或处理事件。模型配置不代表已经发生 AgentRun。");
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
            {error && <p className="rev-firstlook-error" role="alert">{error}</p>}
            <p className="rev-mobile-truth">
              地名只是你输入的探索方向，系统不会因此断言你的实际位置。公开数据与 AI 请求仅在你主动操作后发生。
            </p>
          </section>
        ) : (
          <>
            <section className="rev-mobile-tabpanel" hidden={activeTab !== "explore"} data-testid="rev-mobile-screen-explore">
              <section className="rev-firstlook-journey">
                <div>
                  <span className="rev-firstlook-eyebrow">正在探索</span>
                  <h1>{journey.cityName}</h1>
                  <p>想怎么走？先聊一句，再从真实地点中选择。</p>
                </div>
                <button type="button" onClick={switchCity} className="rev-firstlook-reset">
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
                    agentConfigured={Boolean(agentConfigured)}
                    onPocketWalkChange={setPocketWalk}
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
                  <p>这会经过原有的计划与授权流程；未知费用仍然是未知，不会自动预订或付款。</p>
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
                    <p>这里连接原生 Journey Operator。只有真实产生的 AgentRun 和审批记录，才能算 AI 已执行。</p>
                  </section>
                  <AgentWorkStatus journeyId={journey.id} visible={activeTab === "trips"} />
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
                      <small className="rev-mobile-truth">完成进度由你手动报告，不等于 GPS 到场证明。</small>
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
                  <span>AI 助手</span><strong>{nativeHermesReady ? "Hermes 工具已就绪，运行待验证" : agentConfigured ? "网关已配置，运行待验证" : "当前未配置"}</strong>
                </div>
                <div className="rev-mobile-account-line">
                  <span>行程状态</span><strong>{journey.status === "ACTIVE" ? "已正式启动" : "私人探索草稿"}</strong>
                </div>
                <p>你的私人进度以服务器签名身份为准。本页面不会把样本地点、模型配置或自报到达说成现实证明。</p>
                <button type="button" className="rev-mobile-secondary" onClick={switchCity}>探索其他地区</button>
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
      {journey && (
        <RevolutionMobileNav
          active={activeTab}
          onSelect={navigateMobile}
          hasSavedWalk={Boolean(pocketWalk)}
        />
      )}
      <footer className="rev-firstlook-footer">
        CityNexus · 真实数据以提供方回复为准，探索进度不代表实地到场
      </footer>
    </div>
  );
}
