import { useEffect, useRef, useState } from "react";
import { cityNexusApi, CityNexusApiError, type DraftGoalTask, type GoalPreparationSchedule, type GoalPreparationResult, type GoalRouteFreezeResult, type GoalTravelGapAnswer, type GoalPriceConsentResult } from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import { ASK_AGENT_BUTTON, agentAskPrompt, ASK_HOW_IT_WORKS, FROZEN_ROUTE_SENTENCE, GAP_LABELS, bandSentence, gapAction, hopSentences, openingSentence, pendingCountSentence, priceAcceptedSentence, PRICE_CONSENT_BUTTON, priceUnknownSentence, PRICE_SWAP_BUTTON, PRICE_SWAP_PROMPT, REPLAN_APPLY_BUTTON, REPLAN_BUTTON, REPLAN_NEEDS_FREEZE_SENTENCE, gapShortfallSentence, replanAppliedSentence, replanDiffSentence, replanRefusalSentence, routeSentence, scheduleRefusalSentence, type ScheduleRefusalRow, unknownPricePlaceIds, unansweredHopSentences } from "./departureGaps";

type PriceState = { count: number; knownMinor: number; confirmedAt: string; selectable: boolean | null; blocker: string | null };

// Before anything is saved there is no server gap list to name, so the ask asks for the one thing that
// is true at that moment: make the plan first, then say what is missing.
const UNSAVED_ASK = "还没保存候选方案。请先按上面确认的时间准备一份正式候选方案，再逐项告诉我出发前还缺哪些资料。";

function storedPriceState(result: GoalPreparationResult | null | undefined): PriceState | null {
  const stored = result?.price_unknown_accepted;
  if (!stored || !result) return null;
  return { count: stored.unknown_place_ids.length, knownMinor: stored.known_subtotal_minor,
    confirmedAt: stored.accepted_at, selectable: null, blocker: null };
}

function refusalRow(error: unknown): ScheduleRefusalRow | null {
  // The client's Error message is "CityNexus API 422: /journeys/..." (frontend/src/api/citynexus.ts:2838),
  // so matching on it could never see which rule refused -- that is why every failed save read as
  // "可以重试".  The server's own envelope is on the error object, and the row it names lives there.
  if (!(error instanceof CityNexusApiError)) return null;
  const envelope = (error.body ?? {}) as { error?: { details?: unknown } };
  const details = envelope.error?.details;
  return details && typeof details === "object" ? details as ScheduleRefusalRow : null;
}

function scheduleFor(task: DraftGoalTask): GoalPreparationSchedule[] {
  if (task.prepared_plan && task.prepared_plan.result.draft_revision === task.draft_artifact?.revision) return task.prepared_plan.schedule;
  return (task.draft_artifact?.days ?? []).flatMap((day, di) => {
    const used = new Map<string, number>();
    // The door refuses a row that starts before the row above it ends
    // (backend/app/agent/goal_preparation.py:194), and these seeded hours are what the traveller is shown
    // and what gets sent.  Per-bucket hours alone went backwards -- 八达岭 morning 09:00, 颐和园 afternoon
    // 14:00, 天坛 flexible 11:00 -- so the card was handing the save a contradiction of its own making
    // (trial/results/20261022_v3_human_chrome/walk-77-window-readback-1.txt:11).  A seeded hour now never
    // starts before the previous row finishes.
    let previousEnd = 0;
    return day.slots.flatMap((slot, si) => {
      if (!slot.title.trim()) return [];
      const start = { morning: 9, afternoon: 14, evening: 19, flexible: 11 }[slot.time_of_day];
      const offset = used.get(slot.time_of_day) ?? 0;
      used.set(slot.time_of_day, offset + 1);
      // A bucket the table does not know would make the hour NaN, and NaN:00 is not a time -- guard the
      // arithmetic so a row we cannot place still gets a usable, non-backwards hour instead of poisoning
      // every row after it.
      const wanted = Number.isFinite(start) ? start + offset * 2 : previousEnd;
      const hour = Math.min(22, Math.max(previousEnd, wanted));
      previousEnd = hour + 1;
      return [{ day_index: di, slot_index: si, start_time: `${String(hour).padStart(2, "0")}:00`, end_time: `${String(hour + 1).padStart(2, "0")}:00` }];
    });
  });
}

export function DraftDepartureCard({ task, onDiscuss }: { task: DraftGoalTask; onDiscuss: (goal: string) => void }) {
  const [schedule, setSchedule] = useState(() => scheduleFor(task));
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<GoalPreparationResult | null>(() => task.prepared_plan?.result.draft_revision === task.draft_artifact?.revision ? task.prepared_plan?.result ?? null : null);
  const [routes, setRoutes] = useState<GoalRouteFreezeResult | null>(null);
  const [routesBusy, setRoutesBusy] = useState(false);
  const [gaps, setGaps] = useState<GoalTravelGapAnswer | null>(null);
  const [planShown, setPlanShown] = useState(false);
  const [price, setPrice] = useState<PriceState | null>(() => storedPriceState(task.prepared_plan?.result));
  const [priceBusy, setPriceBusy] = useState(false);
  const routeKey = useRef<string | null>(null);
  const priceKey = useRef<string | null>(null);
  const requestKey = useRef<string | null>(null);
  const inFlight = useRef(false);
  const proposal = useRef<HTMLButtonElement | null>(null);
  const replan = useRef<HTMLButtonElement | null>(null);
  const scope = useRef(0);
  useEffect(() => { const stored = task.prepared_plan?.result.draft_revision === task.draft_artifact?.revision ? task.prepared_plan?.result ?? null : null; scope.current += 1; setSchedule(scheduleFor(task)); setConfirmed(false); setResult(stored); setPrice(storedPriceState(stored)); setMessage(""); requestKey.current = null; routeKey.current = null; setRoutes(null); setGaps(null); setPlanShown(false); priceKey.current = null; }, [task.task_id, task.draft_artifact?.revision]);
  useEffect(() => subscribeTravelerBearer(() => { scope.current += 1; setResult(null); setRoutes(null); setGaps(null); setPlanShown(false); setPrice(null); setMessage(""); setConfirmed(false); }), []);
  // A reload that lands on a plan whose hops are already measured still owes the traveller the answer
  // they paid for: which of their own hours those minutes do not fit.
  const frozenPlanId = result?.mobility_frozen ? result.plan_version_id : null;
  useEffect(() => {
    if (!frozenPlanId || !result || !readTravelerBearer()) return;
    const epoch = scope.current, journeyId = result.journey_id, taskId = result.task_id;
    void cityNexusApi.travelGaps(journeyId, taskId, frozenPlanId)
      .then((answer) => { if (epoch === scope.current && answer.plan_version_id === frozenPlanId) setGaps(answer); })
      .catch(() => { /* the freeze receipt above stands on its own; this is the reading of it */ });
  }, [frozenPlanId, result]);
  // The chat dock is fixed over the bottom of the screen, so the confirm button this card reveals can
  // land underneath it: measured 2026-10-24 at 390x844, the composer's textarea covered the centre of
  // 「按这一版安排」 and the traveller's first press opened the keyboard instead of saving (replan-probe-4
  // log: covers_it=true topmost=TEXTAREA, and no second prepare-plan went on the wire).  Revealing the
  // button is what the traveller's own press asked for, so the reveal has to clear the dock.
  useEffect(() => { if (planShown) proposal.current?.scrollIntoView({ block: "center" }); }, [planShown]);
  const days = task.draft_artifact?.days ?? [];
  if (!schedule.length) return null;
  type GapRow = GoalPreparationResult["gaps"][number];
  const pending = new Map<number, { title: string; rows: GapRow[] }>();
  for (const gap of result?.gaps ?? []) {
    const group = pending.get(gap.sequence_no) ?? { title: gap.title, rows: [] };
    if (!group.rows.some((item) => item.kind === gap.kind)) group.rows.push(gap);
    pending.set(gap.sequence_no, group);
  }
  // The traveller is asked to accept exactly the places the server lists as unanswered, and no others.
  const priceIds = unknownPricePlaceIds(result?.gaps ?? []);
  // What the ask button can still ask for: the server's own gap list, minus the price rows this
  // traveller already confirmed to keep out of the budget.  A row nobody can answer is not a reason to
  // hide the button -- it is the sentence the button sends.
  const askable = (result?.gaps ?? []).filter((gap) => !(price && String(gap.kind) === "ADMISSION_PRICE"));
  // Which hops the map refused, and what it said when it refused.  A freeze answer this session holds
  // carries the per-hop rows; after a refresh the same rows come back from the task's stored attempt,
  // because the work the traveller paid for is still in the record.
  const hopRefusals = routes ? unansweredHopSentences(routes.edges)
    : hopSentences(result?.route_attempt?.unanswered ?? []);
  const change = (index: number, field: "start_time" | "end_time", value: string) => {
    setSchedule(items => items.map((item, i) => i === index ? { ...item, [field]: value } : item));
    setConfirmed(false); setResult(null); requestKey.current = null; setRoutes(null); routeKey.current = null;
    // A saved candidate the traveller has not made again cannot keep their earlier word about prices.
    setPrice(null); priceKey.current = null;
  };
  const prepare = async () => {
    if (!confirmed || inFlight.current || task.status === "WORKING" || !task.draft_artifact) return;
    const token = readTravelerBearer(), epoch = scope.current;
    if (!token) return;
    inFlight.current = true; setBusy(true); setMessage("");
    requestKey.current ??= crypto.randomUUID();
    try {
      const answer = await cityNexusApi.prepareGoalDraft(task.journey_id, task.task_id, task.draft_artifact.revision, schedule, requestKey.current);
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      if (answer.journey_id !== task.journey_id || answer.task_id !== task.task_id || answer.draft_revision !== task.draft_artifact.revision || answer.selected !== false || answer.activated !== false) throw new Error("IDENTITY_MISMATCH");
      setResult(answer);
      setMessage(`已保存 ${answer.slots_count} 项正式安排。下方可以查看日程和出发待办。`);
      window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: task.journey_id }));
    } catch (error) {
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      const named = scheduleRefusalSentence(refusalRow(error));
      const detail = `${(error instanceof CityNexusApiError && typeof (error.body as { error?: { message?: string } } | undefined)?.error?.message === "string"
        ? (error.body as { error: { message: string } }).error.message : "")} `
        + `${error instanceof Error ? error.message : ""}`;
      // With the row named, "可以重试" would be the wrong instruction: the same numbers refuse again.
      setMessage(named || (detail.includes("DRAFT_CHANGED") ? "草案已更新，请刷新任务后再确认时间。"
        : detail.includes("SCHEDULE") ? "请调整时间：各项安排按顺序衔接，并放在这趟旅行的日期内。"
          : "这次未能保存，时间仍留在这里，可以重试。"));
    } finally { inFlight.current = false; setBusy(false); }
  };

  // The saved arrangements are not a PlanVersion. Formal candidates only exist after
  // plans/generate; this button is that door, and it says so before the traveller presses it.
  const generateCandidates = async () => {
    if (!result || generating) return;
    setGenerating(true);
    setMessage("");
    try {
      const generated = await cityNexusApi.generatePlans(task.journey_id, 3);
      setMessage(`已生成 ${generated.length} 份正式候选方案；在上方「你的行程方案」里查看并选用。`);
      window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: task.journey_id }));
    } catch (error) {
      const failure = error instanceof CityNexusApiError
        ? (error.body as { error?: { message?: string; reason_code?: string; details?: { places_in_catalog?: number } } } | undefined)?.error
        : undefined;
      const detail = `${typeof failure?.message === "string" ? failure.message : ""} ${error instanceof Error ? error.message : ""}`;
      const catalogSize = failure?.details?.places_in_catalog;
      // CATALOG_INSUFFICIENT is not "try again": this city's real rows are missing the facts a
      // strict candidate needs, so the door cannot open no matter how many times it is pressed.
      // The traveller can still continue with the draft candidate above, and that is what the
      // sentence has to say (measured on the live Beijing catalog: 54 places, 0 with verified
      // admission cost, 422 CATALOG_INSUFFICIENT).
      const catalogSentence = typeof catalogSize === "number" && catalogSize > 0
        ? `这版安排用的是 ${catalogSize} 个真实地点，但还没有一处同时具备正式候选要的开放时间与票价来源，所以严格候选排不出来。继续用上面这份草案候选就可以：先确认费用、核实转场，再选用。`
        : "这个城市还没有可用的真实地点，先在对话里补一处，再生成正式候选。";
      setMessage(failure?.reason_code === "CATALOG_EMPTY" ? catalogSentence
        : failure?.reason_code === "CATALOG_INSUFFICIENT" ? catalogSentence
          : detail.includes("NO_PLACED_STOPS") ? "这版方案还没有被认成正式地点的两站，先在对话里补认地点。"
            : detail.includes("PLACE_CLOSED") ? "这版方案里有地点在当天不开放，先换一处再生成。"
              : "这次没能生成正式候选，安排仍留在这里，可以重试。");
    } finally {
      setGenerating(false);
    }
  };
  const applyReplan = async () => {
    if (!result || !gaps?.rows.length || inFlight.current || task.status === "WORKING" || !task.draft_artifact) return;
    const token = readTravelerBearer(), epoch = scope.current;
    if (!token) return;
    const merged = schedule.map((stamp) => {
      const moved = gaps.rows.find((row) => row.day_index === stamp.day_index && row.slot_index === stamp.slot_index);
      return moved ? { ...stamp, start_time: moved.proposed_start, end_time: moved.proposed_end } : stamp;
    });
    inFlight.current = true; setBusy(true); setMessage("");
    // A different body must not replay the key the previous save used, or the door answers 409 and
    // says nothing about why.
    const key = crypto.randomUUID();
    try {
      const answer = await cityNexusApi.prepareGoalDraft(task.journey_id, task.task_id,
        task.draft_artifact.revision, merged, key);
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      if (answer.journey_id !== task.journey_id || answer.task_id !== task.task_id
          || answer.draft_revision !== task.draft_artifact.revision
          || answer.selected !== false || answer.activated !== false) throw new Error("IDENTITY_MISMATCH");
      setSchedule(merged); setConfirmed(true); setResult(answer); setRoutes(null); setGaps(null);
      setPlanShown(false); setPrice(null); priceKey.current = null; routeKey.current = null; requestKey.current = key;
      setMessage(replanAppliedSentence(gaps.rows.length) + REPLAN_NEEDS_FREEZE_SENTENCE);
      window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: task.journey_id }));
    } catch (error) {
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      const named = scheduleRefusalSentence(refusalRow(error));
      setMessage(named || "这一版没能保存，原来的时间还在这里。");
    } finally { inFlight.current = false; setBusy(false); }
  };

  const verifyRoutes = async () => {
    if (!result || inFlight.current || task.status === "WORKING") return;
    const token = readTravelerBearer(), epoch = scope.current;
    if (!token) return;
    inFlight.current = true; setRoutesBusy(true); setMessage("");
    routeKey.current ??= crypto.randomUUID();
    try {
      const answer = await cityNexusApi.freezeGoalRoutes(result.journey_id, result.task_id, result.plan_version_id, routeKey.current);
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      if (answer.journey_id !== result.journey_id || answer.task_id !== result.task_id || answer.plan_version_id !== result.plan_version_id) {
        throw new Error("这份转场结果不属于当前方案。");
      }
      setRoutes(answer);
      // The measured minutes only become usable once they are read back against the hours the
      // traveller chose; this door writes nothing, so a failure here must not look like a failed
      // freeze -- the freeze receipt above is already on the screen and stands on its own.
      try {
        setGaps(await cityNexusApi.travelGaps(result.journey_id, result.task_id, result.plan_version_id));
        // The answer to this press carries the next press, and the chat dock sits over the bottom of the
        // screen (its band measured 199px of an 844px viewport).  Left where it is, 根据路线重新安排 can
        // land under the dock and the traveller's next tap opens the keyboard instead -- measured twice
        // on 2026-10-24 (replan-probe-5-log.txt / replan-probe-6-log.txt: centre [189,718],
        // topmost TEXTAREA, no diff rendered).  Bringing the answer to the person who asked for it is
        // this card's job, not theirs.
        window.requestAnimationFrame(() => replan.current?.scrollIntoView({ block: "center" }));
      } catch { setGaps(null); }
      // A frozen hop makes the 转场路线 line for it a lie, and the server already knows that: on a
      // successful freeze it drops every TRANSFER_ROUTE row from the stored answer
      // (backend/app/agent/goal_route_freeze.py:369), so a refresh is correct.  This card holds its own
      // copy of that same answer, and without the same drop it keeps asking the Agent to measure
      // segments it just measured -- read on one and the same open card at walk-72-log.txt:33 ("5/5")
      // against :39 ("还有 5 项") and :45 (the five segments named again).  Only TRANSFER_ROUTE rows go;
      // identity, opening and price rows stay, because a frozen walk proves none of those, and a partly
      // verified day (frozen=false) keeps every row it had.
      if (answer.frozen) {
        setResult((current) => current
          ? { ...current, gaps: current.gaps.filter((gap) => String(gap.kind) !== "TRANSFER_ROUTE") }
          : current);
      }
      window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: result.journey_id }));
    } catch (error) {
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      setMessage(error instanceof Error && error.message ? error.message : "转场没能核实，时间仍留在这里，可以重试。");
    } finally { inFlight.current = false; setRoutesBusy(false); }
  };
  const acceptPrice = async () => {
    if (!result || inFlight.current || task.status === "WORKING") return;
    const ids = unknownPricePlaceIds(result.gaps);
    if (!ids.length) return;
    const token = readTravelerBearer(), epoch = scope.current;
    if (!token) return;
    inFlight.current = true; setPriceBusy(true); setMessage("");
    priceKey.current ??= crypto.randomUUID();
    try {
      const answer: GoalPriceConsentResult = await cityNexusApi.acceptUnknownPrice(
        result.journey_id, result.task_id, result.plan_version_id, ids, priceKey.current);
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      if (answer.plan_version_id !== result.plan_version_id || answer.task_id !== result.task_id
          || answer.journey_id !== result.journey_id || answer.accepted !== true
          || answer.unknown_cost_included !== false) {
        throw new Error("这份费用确认不属于当前方案。");
      }
      setPrice({ count: answer.unknown_count, knownMinor: answer.known_subtotal_minor,
        confirmedAt: answer.confirmed_at, selectable: answer.selectable_after, blocker: answer.blocker_after });
      window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: result.journey_id }));
    } catch (error) {
      if (epoch !== scope.current || token !== readTravelerBearer()) return;
      setMessage(error instanceof Error && error.message ? error.message : "这次没能记下你的确认，可以重试。");
    } finally { inFlight.current = false; setPriceBusy(false); }
  };

  return <section className="rev-v3-departure" aria-label="当前草案的出发准备">
    <h3>从这份安排继续</h3>
    <p>{result ? `${result.slots_count} 项安排已保存，刷新也能找回。` : "保留已选地点和日期；时间可以稍后调整。"}</p>
    <details><summary>{result ? "已确认时间 · 查看或调整" : "编辑行程时间（可选）"}</summary>
    <fieldset disabled={busy || task.status === "WORKING"}>
      {schedule.map((stamp, index) => {
        const day = days[stamp.day_index], slot = day?.slots[stamp.slot_index];
        if (!slot) return null;
        return <div className="rev-v3-slot-time" key={`${stamp.day_index}:${stamp.slot_index}`}>
          <strong>{day.date.slice(5)} · {slot.title}</strong>
          <div><label>开始<input type="time" aria-label={`${slot.title}开始时间`} value={stamp.start_time} onChange={event => change(index, "start_time", event.target.value)} /></label>
          <label>结束<input type="time" aria-label={`${slot.title}结束时间`} value={stamp.end_time} onChange={event => change(index, "end_time", event.target.value)} /></label></div>
        </div>;
      })}
    </fieldset>
    </details>
    <fieldset disabled={busy || task.status === "WORKING"}>
      <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />按以上时间准备方案</label>
      <button type="button" disabled={!confirmed || busy || Boolean(result)} onClick={() => void prepare()}>{busy ? "正在保存安排…" : result ? "安排已保存" : "保存为正式候选方案"}</button>
    </fieldset>
    {result && <div className="rev-v3-generate-plans">
      <button type="button" data-testid="rev-v3-generate-plans" disabled={generating} onClick={() => void generateCandidates()}>{generating ? "正在生成正式候选…" : "生成正式候选方案"}</button>
    </div>}
    {message && <p role="status">{message}</p>}
    {result && <p className="rev-v3-route-state" data-testid="rev-v3-route-state">
      {routes ? routeSentence(routes.verified, routes.total, routes.frozen, routes.overnight ?? 0, routes.transit ?? 0,
        routes.reason_code, routes.replaced_long_walks ?? 0, routes.over_cap_walks ?? 0, routes.walking_cap_m ?? null)
        : result.route_attempt && !result.route_attempt.frozen
          ? routeSentence(result.route_attempt.verified, result.route_attempt.total, false,
            result.route_attempt.overnight ?? 0, result.route_attempt.transit ?? 0, result.route_attempt.reason_code ?? null,
            result.route_attempt.replaced_long_walks ?? 0, result.route_attempt.over_cap_walks ?? 0,
            result.route_attempt.walking_cap_m ?? null)
          : result.mobility_frozen ? FROZEN_ROUTE_SENTENCE : "当天的转场还没有向高德核实过。"}
      <button type="button" disabled={routesBusy} onClick={() => void verifyRoutes()} data-testid="rev-v3-freeze-routes">
        {routesBusy ? "正在核实转场…"
          : (routes ? routes.frozen : result.route_attempt ? result.route_attempt.frozen : result.mobility_frozen)
            ? "重新核实转场" : "核实并冻结今天的转场"}
      </button>
    </p>}
    {hopRefusals.length > 0 && <ul className="rev-v3-hop-refusals" data-testid="rev-v3-hop-refusals" aria-label="哪几段没有回答">
      {hopRefusals.map((line) => <li key={line} data-testid="rev-v3-hop-refusal">{line}</li>)}
    </ul>}
    {gaps && (gaps.rows.length > 0 || gaps.hops.some((hop) => hop.short_by_minutes > 0)
      || Boolean(replanRefusalSentence(gaps.reason_code))) && <div className="rev-v3-travel-gaps" data-testid="rev-v3-travel-gaps">
      <h4>量回来的路上时间</h4>
      <ul data-testid="rev-v3-gap-shortfalls">{gaps.hops.filter((hop) => hop.short_by_minutes > 0)
        .map((hop) => <li key={`${hop.origin_title}->${hop.destination_title}`} data-testid="rev-v3-gap-shortfall">{gapShortfallSentence(hop)}</li>)}</ul>
      {gaps.reason_code && replanRefusalSentence(gaps.reason_code) && <p data-testid="rev-v3-replan-refusal">{replanRefusalSentence(gaps.reason_code)}</p>}
      {gaps.rows.length > 0 && !planShown && <button type="button" ref={replan} data-testid="rev-v3-replan" onClick={() => setPlanShown(true)}>{REPLAN_BUTTON}</button>}
      {planShown && <ul data-testid="rev-v3-replan-diff">{gaps.rows.map((row) => <li key={`${row.day_index}:${row.slot_index}`}>{replanDiffSentence(row)}</li>)}</ul>}
      {planShown && <button type="button" ref={proposal} data-testid="rev-v3-replan-apply" disabled={busy || task.status === "WORKING"} onClick={() => void applyReplan()}>{busy ? "正在保存这一版…" : REPLAN_APPLY_BUTTON}</button>}
    </div>}
    {result && (result.unrouted_count ?? 0) > 0 && <p className="rev-v3-band-note" data-testid="rev-v3-band-note">{bandSentence(result.unrouted_count ?? 0)}</p>}
    {(result?.opening_checks ?? []).length > 0 && <ul className="rev-v3-opening" data-testid="rev-v3-opening" aria-label="每一处当天的开放核实">
      {(result?.opening_checks ?? []).map((row) => <li key={row.sequence_no}>
        <strong>{row.title}</strong><span data-testid="rev-v3-opening-verdict">{openingSentence(row)}</span>
        {row.verdict !== "OPEN_ON_DATE" && row.source_text && <small>来源原文：{row.source_text}</small>}
      </li>)}
    </ul>}
    {result && priceIds.length > 0 && <div className="rev-v3-price-state" data-testid="rev-v3-price-state">
      {price ? <p>{priceAcceptedSentence(price.count, price.knownMinor)}{price.selectable === false ? "这一版还需要把待办逐项补完才能选用。" : ""}</p>
        : <>
          <p>{priceUnknownSentence(result.known_subtotal_minor ?? 0, priceIds.length)}</p>
          <button type="button" disabled={priceBusy || task.status === "WORKING"} onClick={() => void acceptPrice()} data-testid="rev-v3-accept-price">{priceBusy ? "正在记下你的确认…" : PRICE_CONSENT_BUTTON}</button>
          <button type="button" onClick={() => onDiscuss(PRICE_SWAP_PROMPT)} data-testid="rev-v3-swap-price">{PRICE_SWAP_BUTTON}</button>
        </>}
    </div>}
    {pending.size > 0 && <><h4>出发待办</h4><ul>{[...pending].map(([sequence, group]) => <li key={sequence}><strong>{group.title}</strong>{group.rows.map(gap => <span key={String(gap.kind)}>{GAP_LABELS[String(gap.kind)] ?? "资料"}：{gapAction(gap)}</span>)}</li>)}</ul></>}
    {result && <p className="rev-v3-band-note" data-testid="rev-v3-ask-count">{pendingCountSentence(askable.length)}</p>}
    {(result ? askable.length > 0 : true) && <p className="rev-v3-band-note" data-testid="rev-v3-ask-how">{ASK_HOW_IT_WORKS}</p>}
    {!result && <button type="button" data-testid="rev-v3-ask-agent" onClick={() => onDiscuss(UNSAVED_ASK)}>{ASK_AGENT_BUTTON}</button>}
    {result && askable.length > 0 && <button type="button" data-testid="rev-v3-ask-agent" onClick={() => onDiscuss(agentAskPrompt(askable, Boolean(price)))}>{ASK_AGENT_BUTTON}</button>}
  </section>;
}
