import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cityNexusApi, type TravelPlanningInput, type BootstrapDiscoveryCandidate } from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import { WorkspaceMap } from "./WorkspaceMap";
import "./WorkspaceActions.css";

export type WorkspacePanel = "assistant" | "map" | null;
type Context = { id: string; token: string; owner: string };
type Snapshot = { context: Context; input: TravelPlanningInput; status: string; mapCandidates: BootstrapDiscoveryCandidate[] };
const COPY = {
  assistant: "AI助手", map: "地图", close: "关闭工作台",
  load: "正在读取当前行程…",
  none: "先在探索页建立一趟行程，随后在任何页面都能打开地图和 AI。",
  failed: "暂时无法读取行程，可以重新读取。",
  question: "告诉 AI 你想怎么玩", send: "发送给 AI",
  sending: "正在请求 AI…", reload: "重新读取",
};

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

export function WorkspaceActions({ panel, onClose }: { panel: WorkspacePanel; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const [revision, setRevision] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{ context: Context; text: string } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [aiReady, setAiReady] = useState(false);
  const [allowTiles, setAllowTiles] = useState(false);
  const previousContext = useRef<Context | null>(null);
  const generation = useRef(0);
  const writeBusy = useRef(false);
  const postController = useRef<AbortController | null>(null);
  const context = readContext();
  const visible = snapshot && sameContext(snapshot.context, context) ? snapshot : null;
  const visibleAnswer = answer && sameContext(answer.context, context) ? answer.text : null;

  useEffect(() => {
    const invalidate = () => {
      generation.current += 1;
      postController.current?.abort();
      postController.current = null;
      writeBusy.current = false;
      setSnapshot(null); setAnswer(null); setQuestion(""); setRequestError(null);
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
      setQuestion(""); setAnswer(null); setBusy(false); setRequestError(null); setAllowTiles(false); setAiReady(false);
    }
    let cancelled = false;
    setLoading(true); setLoadError(null);
    Promise.all([cityNexusApi.getTravelPlanningInput(actor.id), cityNexusApi.getJourney(actor.id),
      cityNexusApi.getJourneyMapPlaces(actor.id).catch(() => null)])
      .then(([input, journey, mapPlaces]) => {
        if (cancelled || !sameContext(actor, readContext())) return;
        if (input.journey_id !== actor.id || journey.id !== actor.id || !Array.isArray(input.candidates)) throw new Error("Context mismatch");
        if (mapPlaces?.journey_id && mapPlaces.journey_id !== actor.id) throw new Error("Map context mismatch");
        setSnapshot({ context: actor, input, status: journey.status,
          mapCandidates: mapPlaces?.journey_id === actor.id && Array.isArray(mapPlaces.candidates) ? mapPlaces.candidates : input.candidates });
        setQuestion((value) => value || (input.intent?.goal ?? "").slice(0, 360));
      }).catch(() => { if (!cancelled && sameContext(actor, readContext())) { setSnapshot(null); setLoadError(COPY.failed); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    void cityNexusApi.getAgentRuntimeStatus().then((runtime) => {
      if (cancelled || !sameContext(actor, readContext())) return;
      const state = String(runtime.ai_state ?? "").toUpperCase();
      setAiReady(runtime.hermes_compat_configured === true && !["DISABLED", "DISABLED_BY_OPS", "NOT_CONFIGURED"].includes(state));
    }).catch(() => { if (!cancelled && sameContext(actor, readContext())) setAiReady(false); });
    return () => { cancelled = true; };
  }, [Boolean(panel), context?.id, context?.owner, context?.token, revision]);

  const send = async () => {
    const actor = readContext();
    if (!actor || !visible || !sameContext(actor, visible.context) || !aiReady || visible.status !== "DRAFT" || writeBusy.current || question.trim().length < 4) return;
    const serial = ++generation.current;
    const controller = new AbortController();
    postController.current = controller;
    writeBusy.current = true; setBusy(true); setRequestError(null); setAnswer(null);
    const timer = window.setTimeout(() => controller.abort(), 65000);
    try {
      const response = await fetch(`/api/v1/journeys/${encodeURIComponent(actor.id)}/trial-ai-discovery`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${actor.token}` },
        body: JSON.stringify({ goal: question.trim() }), signal: controller.signal, cache: "no-store",
      });
      if (!response.ok) {
        const message = response.status === 401 || response.status === 403
          ? "登录已变化，请重新进入行程。"
          : response.status === 409 ? "这个建议入口适用于旅行草稿，已出发的行程请使用行程页的执行助手。"
          : "AI 服务暂未完成请求。地点列表和地图仍可使用。";
        throw new Error(message);
      }
      const result = await response.json() as { status?: unknown; evidence?: unknown; reason?: unknown };
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      if (result.status !== "MODEL_TOOL_SUGGESTION" || result.evidence !== "HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE" || typeof result.reason !== "string") {
        throw new Error("AI 没有返回可使用的建议，你的行程仍然保留。");
      }
      setAnswer({ context: actor, text: result.reason.slice(0, 1000) });
    } catch (error) {
      if (serial !== generation.current || !sameContext(actor, readContext())) return;
      setRequestError(error instanceof Error && error.name === "AbortError"
        ? "等待已停止，服务可能仍在处理；没有自动重发模型请求。"
        : error instanceof Error ? error.message : "AI 请求暂未完成。");
    } finally {
      window.clearTimeout(timer);
      if (serial === generation.current) { postController.current = null; writeBusy.current = false; setBusy(false); }
    }
  };

  return createPortal(<dialog ref={dialog} className="rev-workspace-dialog" aria-labelledby="rev-workspace-heading"
    onCancel={(event) => { event.preventDefault(); closeRef.current(); }}>
    <header className="rev-workspace-top"><h2 id="rev-workspace-heading">{panel === "map" ? COPY.map : COPY.assistant}</h2>
      <button type="button" onClick={onClose} aria-label={COPY.close}>×</button></header>
    <div className="rev-workspace-body">
      {!context && <p>{COPY.none}</p>}
      {loading && !visible && <p role="status">{COPY.load}</p>}
      {loadError && <p role="alert">{loadError}</p>}
      {context && <button type="button" className="rev-workspace-secondary" disabled={loading} onClick={() => setRevision((value) => value + 1)}>{COPY.reload}</button>}
      {visible && panel === "map" && <WorkspaceMap candidates={visible.mapCandidates} allowed={allowTiles} onAllow={() => setAllowTiles(true)} />}
      {visible && panel === "assistant" && <>
        <p>{visible.input.trip.dates.length} 天 · {visible.input.trip.party_size} 人 · 旅行需求已从服务器读取</p>
        {!aiReady && <p role="status">AI 暂未连接。本机可通过 OPEN_REVOLUTION_AI.cmd 开启，地图与地点仍可以使用。</p>}
        {visible.status !== "DRAFT" ? <p>这趟行程已进入确认或执行阶段，关闭面板后在行程页查看执行助手。</p> :
          <form onSubmit={(event) => { event.preventDefault(); void send(); }}>
            <label htmlFor="rev-workspace-question">{COPY.question}</label>
            <textarea id="rev-workspace-question" rows={5} maxLength={360} value={question} disabled={busy} onChange={(event) => setQuestion(event.target.value)} />
            <p className="rev-workspace-caption">点击发送后，本次问题会发送给已连接的 AI 服务，可能计费。</p>
            <button type="submit" disabled={!aiReady || busy || question.trim().length < 4}>{busy ? COPY.sending : COPY.send}</button>
          </form>}
        {busy && <p role="status">正在等待模型响应；收起面板不会重复发送。</p>}
        {requestError && <p role="alert">{requestError}</p>}
        {visibleAnswer && <section aria-label="AI 返回的建议" className="rev-workspace-answer"><h3>AI 探索建议</h3><p>{visibleAnswer}</p>
          <small>这是现有只读建议接口的返回，还不是自主执行记录。</small></section>}
      </>}
    </div>
  </dialog>, document.body);
}
