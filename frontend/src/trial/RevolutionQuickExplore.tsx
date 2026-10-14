import { useEffect, useRef, useState } from "react";
import {
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

/**
 * A HUMAN-SIZED entry to the exact signed R107/R108 endpoints.
 *
 * The two external HTTP operations are sent only when the user clicks their
 * plainly-labelled release button. City results are CAMERA ONLY, never a
 * confirmed search center: a user must tap the map or provide an exact OSM
 * link to set a manual public center. No GPS, automatic provider calls,
 * disguised fixture, PlanVersion, or AgentRun is invented here.
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

function messageForError(error: unknown): string {
  // Error text can contain server internals. Keep it only in an optional
  // developer detail, never silently substitute sample locations as LIVE.
  if (error instanceof Error) {
    if (/401|403|AUTH|UNAUTHORIZED/i.test(error.message)) {
      return "登录会话可能已失效。请重新进入 Revolution，再试一次。";
    }
    if (/429|RATE_LIMIT/i.test(error.message)) {
      return "公开地图服务请求太频繁。稍等一会儿再试。";
    }
  }
  return "这一步没有完成。请检查网络后重试，已保存的行程不会因此消失。";
}

export function RevolutionQuickExplore({
  journeyId,
  cityName,
}: {
  journeyId: string;
  cityName: string;
}) {
  const [stage, setStage] = useState<Stage>("area");
  const [query, setQuery] = useState(cityName);
  const [cityResults, setCityResults] = useState<BootstrapCitySearchResult[]>([]);
  const [cityFocus, setCityFocus] = useState<{ latitude: number; longitude: number } | null>(null);
  const [tilesEnabled, setTilesEnabled] = useState(false);
  const [selectedPin, setSelectedPin] = useState<PublicCityCenter | null>(null);
  const [mapLink, setMapLink] = useState("");
  const [center, setCenter] = useState<PublicCityCenter | null>(null);
  const [category, setCategory] = useState<(typeof categories)[number]["value"]>("park/garden");
  const [readiness, setReadiness] = useState<BootstrapDiscoveryReadinessResponse | null>(null);
  const [readinessStatus, setReadinessStatus] = useState<"checking" | "ready" | "blocked" | "error">("checking");
  const [discovery, setDiscovery] = useState<BootstrapDiscoveryResponse | null>(null);
  const [first, setFirst] = useState<string | null>(null);
  const [second, setSecond] = useState<string | null>(null);
  const [walk, setWalk] = useState<BootstrapPocketWalkResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [alert, setAlert] = useState<{ type: AlertKind; text: string } | null>(null);
  const [rawError, setRawError] = useState<string | null>(null);
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

  const run = async (task: (stillCurrent: () => boolean) => Promise<void>) => {
    if (busyRef.current) return;
    const identity = readTravelerBearer();
    if (!identity) {
      setAlert({ type: "error", text: "没有有效登录会话，请重新进入 Revolution。" });
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
    setRawError(null);
    try {
      await task(stillCurrent);
    } catch (error) {
      if (stillCurrent()) {
        setAlert({ type: "error", text: messageForError(error) });
        setRawError(error instanceof Error ? error.message.slice(0, 350) : "UNKNOWN");
      }
    } finally {
      if (currentOperation.current === runId) {
        busyRef.current = false;
        if (stillCurrent()) setBusy(false);
      }
    }
  };

  const cityLookup = () => {
    const cityQuery = query.trim();
    if (cityQuery.length < 2 || cityQuery.length > 120) {
      setAlert({ type: "error", text: "请输入至少两个字的城市或地区，例如「连城县」。" });
      return;
    }
    void run(async (stillCurrent) => {
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
      setAlert({ type: "good", text: "找到位置了。选一个结果，然后在地图上点选具体想逛的区域。" });
    });
  };

  const useCenter = (point: PublicCityCenter) => {
    if (!Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) return;
    setCenter(point);
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
    useCenter(point);
  };

  const retryReadiness = () => {
    void run(async (stillCurrent) => {
      const next = await cityNexusApi.getBootstrapDiscoveryReadiness(journeyId);
      if (!stillCurrent()) return;
      setReadiness(next);
      setReadinessStatus(next.status === "READY" ? "ready" : "blocked");
      setAlert(next.status === "READY"
        ? { type: "good", text: "地图服务已准备好，可以发起一次明确授权的查询。" }
        : { type: "error", text: "地图服务仍不可用。你可以查看服务状态，但不会虚构地点。" });
    });
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
    void run(async (stillCurrent) => {
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
    });
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

  const saveWalk = () => {
    if (!discovery?.receipt_id || !first || !second || first === second) {
      setAlert({ type: "neutral", text: "先挑两个不同的真实地点。" });
      return;
    }
    const receipt = discovery.receipt_id;
    const firstId = first;
    const secondId = second;
    void run(async (stillCurrent) => {
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
    });
  };

  const go = (action: "START" | "REPORT_FIRST_DONE" | "START_SECOND" | "REPORT_WALK_DONE" | "PAUSE" | "RESUME") => {
    if (!walk) return;
    const saved = walk;
    void run(async (stillCurrent) => {
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
    });
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
          {stage === "area" && "输入地区名称，找到它，然后在地图上选一个想探索的位置。"}
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

      {alert && <p className={`rev-quick-alert ${alert.type}`} role="status">{alert.text}</p>}
      {rawError && <details className="rev-quick-internals"><summary>查看这次错误的技术详情</summary><code>{rawError}</code></details>}

      {stage === "area" && (
        <div className="rev-quick-pane" data-testid="rev-quick-area">
          <label htmlFor="rev-quick-search">城市或地区</label>
          <div className="rev-quick-inline">
            <input
              id="rev-quick-search"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setCityResults([]); setCityFocus(null); setSelectedPin(null); }}
              placeholder="比如：连城县，福建龙岩"
              maxLength={120}
              disabled={busy}
            />
            <button type="button" onClick={cityLookup} disabled={busy} data-testid="rev-quick-find-city">
              {busy ? "查询中…" : "查找位置 →"}
            </button>
          </div>
          <p className="rev-quick-disclosure">点「查找位置」才会把这次输入的地名发送给公开 Nominatim 地图服务。不会读取手机 GPS。</p>
          {cityResults.length > 0 && (
            <div className="rev-quick-results" data-testid="rev-quick-city-results">
              <h3>是这些地方吗？</h3>
              {cityResults.map((item) => (
                <button
                  type="button"
                  className="rev-quick-city-option"
                  key={item.result_id}
                  onClick={() => {
                    setCityFocus({ latitude: item.latitude, longitude: item.longitude });
                    setSelectedPin(null);
                    setTilesEnabled(false);
                    setAlert({ type: "neutral", text: "地图会定位到这个大致区域。你还需要亲自在地图上点选具体搜索范围。" });
                  }}
                >
                  <strong>{item.display_name || item.name}</strong>
                  <small>{item.provider_provenance === "TEST_PROVIDER" ? "受控测试地点" : "公开地名搜索结果"} · 城市中心可能不精确</small>
                  <span>查看这个地区 →</span>
                </button>
              ))}
            </div>
          )}
          {cityFocus && (
            <div className="rev-quick-map-step">
              <h3>在地图上点一下你想探索的位置</h3>
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
                    onSelect={setSelectedPin}
                  />
                  {selectedPin && (
                    <button
                      type="button"
                      className="rev-quick-primary"
                      onClick={() => useCenter(selectedPin)}
                      data-testid="rev-quick-confirm-center"
                    >
                      就在这里找附近的地方 →
                    </button>
                  )}
                </>
              )}
            </div>
          )}
          <details className="rev-quick-internals">
            <summary>地图打不开？用公开 OpenStreetMap 链接定位</summary>
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
            点下面的按钮，会向 OpenStreetMap/Overpass 发送这片公开地图中心的坐标、你选择的类别，
            以及有限范围的一次查询。不会共享 GPS、身份证明或私人行程。
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
        <p>城市结果仅用于移动公开地图视角，必须由用户在地图上点选或粘贴明确的 OSM 位置链接。</p>
        <p>数据状态：{discovery?.status ?? "尚未搜索"} · {sourceKind ?? "来源未确定"}</p>
        <p>AI 模型可在另一个正式 Journey Operator 流程中使用。这里不会把普通地点搜索说成 Agent 自主推理。</p>
        <p>当前 Journey: {journeyId}</p>
      </details>
    </section>
  );
}
