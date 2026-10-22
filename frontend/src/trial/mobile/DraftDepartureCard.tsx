import { useEffect, useRef, useState } from "react";
import { cityNexusApi, type DraftGoalTask, type GoalPreparationSchedule, type GoalPreparationResult } from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import { ASK_AGENT_BUTTON, GAP_LABELS, gapAction } from "./departureGaps";

function scheduleFor(task: DraftGoalTask): GoalPreparationSchedule[] {
  if (task.prepared_plan && task.prepared_plan.result.draft_revision === task.draft_artifact?.revision) return task.prepared_plan.schedule;
  return (task.draft_artifact?.days ?? []).flatMap((day, di) => {
    const used = new Map<string, number>();
    return day.slots.flatMap((slot, si) => {
      if (!slot.title.trim()) return [];
      const start = { morning: 9, afternoon: 14, evening: 19, flexible: 11 }[slot.time_of_day];
      const offset = used.get(slot.time_of_day) ?? 0;
      used.set(slot.time_of_day, offset + 1);
      const hour = Math.min(22, start + offset * 2);
      return [{ day_index: di, slot_index: si, start_time: `${String(hour).padStart(2, "0")}:00`, end_time: `${String(hour + 1).padStart(2, "0")}:00` }];
    });
  });
}

export function DraftDepartureCard({ task, onDiscuss }: { task: DraftGoalTask; onDiscuss: (goal: string) => void }) {
  const [schedule, setSchedule] = useState(() => scheduleFor(task));
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<GoalPreparationResult | null>(() => task.prepared_plan?.result.draft_revision === task.draft_artifact?.revision ? task.prepared_plan?.result ?? null : null);
  const requestKey = useRef<string | null>(null);
  const inFlight = useRef(false);
  const scope = useRef(0);
  useEffect(() => { scope.current += 1; setSchedule(scheduleFor(task)); setConfirmed(false); setResult(task.prepared_plan?.result.draft_revision === task.draft_artifact?.revision ? task.prepared_plan?.result ?? null : null); setMessage(""); requestKey.current = null; }, [task.task_id, task.draft_artifact?.revision]);
  useEffect(() => subscribeTravelerBearer(() => { scope.current += 1; setResult(null); setMessage(""); setConfirmed(false); }), []);
  const days = task.draft_artifact?.days ?? [];
  if (!schedule.length) return null;
  type GapRow = GoalPreparationResult["gaps"][number];
  const pending = new Map<number, { title: string; rows: GapRow[] }>();
  for (const gap of result?.gaps ?? []) {
    const group = pending.get(gap.sequence_no) ?? { title: gap.title, rows: [] };
    if (!group.rows.some((item) => item.kind === gap.kind)) group.rows.push(gap);
    pending.set(gap.sequence_no, group);
  }
  const change = (index: number, field: "start_time" | "end_time", value: string) => {
    setSchedule(items => items.map((item, i) => i === index ? { ...item, [field]: value } : item));
    setConfirmed(false); setResult(null); requestKey.current = null;
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
      const detail = error instanceof Error ? error.message : "";
      setMessage(detail.includes("DRAFT_CHANGED") ? "草案已更新，请刷新任务后再确认时间。" : detail.includes("SCHEDULE") ? "请调整时间：各项安排按顺序衔接，并放在这趟旅行的日期内。" : "这次未能保存，时间仍留在这里，可以重试。");
    } finally { inFlight.current = false; setBusy(false); }
  };
  return <section className="rev-v3-departure" aria-label="当前草案的出发准备">
    <h3>从这份安排继续</h3>
    <p>{result ? `${result.slots_count} 项安排已保存，刷新也能找回。` : "保留已选地点和日期，先确认每天的时间。"}</p>
    <details open={!result}><summary>{result ? "已确认时间 · 查看或调整" : "确认每天的时间"}</summary>
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
      <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />按以上时间准备方案</label>
      <button type="button" disabled={!confirmed || busy || Boolean(result)} onClick={() => void prepare()}>{busy ? "正在保存安排…" : result ? "安排已保存" : "保存为正式候选方案"}</button>
    </fieldset>
    </details>
    {message && <p role="status">{message}</p>}
    {pending.size > 0 && <><h4>出发待办</h4><ul>{[...pending].map(([sequence, group]) => <li key={sequence}><strong>{group.title}</strong>{group.rows.map(gap => <span key={String(gap.kind)}>{GAP_LABELS[String(gap.kind)] ?? "资料"}：{gapAction(gap)}</span>)}</li>)}</ul></>}
    <button type="button" onClick={() => onDiscuss("继续讨论当前选好的草案，保留所有日期和地点。逐项告诉我出发前缺哪些营业、费用或转场资料，并给我处理选择，先不要改行程。")}>{ASK_AGENT_BUTTON}</button>
  </section>;
}
