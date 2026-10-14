import { useState } from "react";
import { BootstrapDiscoveryPanel } from "../features/discovery/BootstrapDiscoveryPanel";
import {
  clearTravelerBearer,
  readTravelerBearer,
  storeTravelerBearer,
} from "../lib/travelerSession";
import "./RevolutionFirstLook.css";

const STORAGE_KEY = "citynexus.revolution.firstlook.journey";

type TrialJourney = {
  id: string;
  cityCode: string;
  cityName: string;
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
    return { id: value.id, cityCode: value.cityCode, cityName: value.cityName };
  } catch {
    return null;
  }
}

async function postJson<T>(path: string, payload: object): Promise<T> {
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const sample = import.meta.env.VITE_REV_TRIAL_MODE === "sample";

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
      const next = { id: created.id, cityCode, cityName: label };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setJourney(next);
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
  };

  return (
    <div className="rev-firstlook" data-testid="revolution-first-look">
      <header className="rev-firstlook-header">
        <div className="rev-firstlook-brand">
          <span className="rev-firstlook-mark">R</span>
          <div>
            <strong>CityNexus Revolution Lab</strong>
            <small>独立体验 · 真实产品 API</small>
          </div>
        </div>
        <a className="rev-firstlook-quiet" href="/v8/hub" title="旧产品界面，仅用于比较">
          原有 V8 界面 ↗
        </a>
      </header>

      <main className="rev-firstlook-content">
        <div className="rev-firstlook-mode">
          <span className={"rev-firstlook-pulse " + (sample ? "is-sample" : "is-live")} />
          {sample
            ? "受控样本模式：此模式不访问真实地点提供方"
            : "真实公开地图模式：仅在你主动授权后请求外部提供方"}
        </div>
        {!journey ? (
          <section className="rev-firstlook-hero">
            <span className="rev-firstlook-eyebrow">YOUR CITY. YOUR JOURNEY.</span>
            <h1>别选演示城市。<br />告诉我，你想去哪儿。</h1>
            <p>
              这是 Revolution 已实现的城市探索入口。可以输入连城、厦门或任何你关心的地区，
              无须先通过旧版「支持的目的地」目录。地名只是你的探索意图，
              具体位置要由你在下一步确认，不能冒充已验证的城市身份。
            </p>
            <form onSubmit={(event) => { event.preventDefault(); void start(); }}>
              <label htmlFor="rev-firstlook-city">我想探索</label>
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
                  {busy ? "正在创建…" : "开始真实探索 →"}
                </button>
              </div>
            </form>
            {error && <p className="rev-firstlook-error" role="alert">{error}</p>}
            <div className="rev-firstlook-cards">
              <article><span>01</span><b>自己选一个地区</b><small>无需内部城市目录</small></article>
              <article><span>02</span><b>发现公开地点</b><small>检查来源与不确定性</small></article>
              <article><span>03</span><b>保存 Pocket Walk</b><small>GO MODE、导航与状态恢复</small></article>
            </div>
            <p className="rev-firstlook-limit">
              此独立入口只解决首次进入 Revolution 的问题。外部 AI Agent 当前未启用，
              不能把 Pocket Walk 等同于完整自主 Agent。地点开放情况、费用和行走时长如无证据均为未知。
            </p>
          </section>
        ) : (
          <>
            <section className="rev-firstlook-journey">
              <div>
                <span className="rev-firstlook-eyebrow">EXPLORE · DRAFT JOURNEY</span>
                <h1>{journey.cityName}，从这里开始。</h1>
                <p>
                  已创建你自己的签名探索草稿。现在通过公开城市搜索或手动地图中心选择位置，
                  再选择类别寻找地点。探索不会自动创建付费预订，也不会确认你到达过任何地方。
                </p>
              </div>
              <button type="button" onClick={switchCity} className="rev-firstlook-reset">
                换一个地区
              </button>
            </section>
            {notice && <p className="rev-firstlook-notice" role="status">{notice}</p>}
            <section className="rev-firstlook-real-ui" aria-label="Revolution 真实城市探索与 GO MODE">
              <BootstrapDiscoveryPanel
                key={journey.id}
                journeyId={journey.id}
                cityCode={journey.cityCode}
                cityName={journey.cityName}
                onCompleted={async () => {
                  setNotice("已选择公开地点。Pocket Walk 仍是独立的私人草稿，不会在这里冒充已启动的正式行程。");
                }}
              />
            </section>
          </>
        )}
      </main>
      <footer className="rev-firstlook-footer">
        Revolution Lab 独立首体验 · 真实业务代码 · 不代表实地到达或 AI 自动完成
      </footer>
    </div>
  );
}
