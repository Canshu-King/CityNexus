import { useEffect, useState } from "react";
import { CityNexusApiError } from "../../api/citynexus";
import { travelerErrorMessage } from "./travelerError";
import type { GoalDraftArtifact, GoalDraftSlot, GoalPlaceMediaResult } from "../../api/citynexus";

const PERIOD: Record<GoalDraftSlot["time_of_day"], string> = {
  morning: "上午", afternoon: "下午", evening: "晚上", flexible: "时间灵活",
};

/** What to tell the traveller after a refused save, chosen from the reason the server named. */
function saveFailureMessage(error: unknown): string {
  const retry = "没有保存成功，请稍后重试。";
  if (!(error instanceof CityNexusApiError)) {
    return travelerErrorMessage(error, retry);
  }
  const reason = (error.body as { error?: { reason_code?: unknown } } | undefined)?.error?.reason_code;
  if (reason === "DRAFT_RESEARCH_RUNNING") return "Agent 正在跑这一轮，等它结束再保存。你的改动还在这个页面。";
  if (reason === "DRAFT_CHANGED_RELOAD") return "服务器的草案版本发生了变化。你的编辑仍在当前页面，请先确认新内容，再点上方「刷新任务」。";
  if (error.status === 401 || error.status === 403) return "当前登录没有保存权限，请重新登录原来的旅行者。";
  return retry;
}

export function GoalDraftEditor({ artifact, disabled, onSave, mediaById = {}, onPlaceSelect }: {
  artifact: GoalDraftArtifact; disabled: boolean; mediaById?: Record<string, GoalPlaceMediaResult>;
  onPlaceSelect?: (id: string) => void; onSave: (draft: GoalDraftArtifact) => Promise<void>;
}) {
  const [draft, setDraft] = useState(artifact);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState("");
  const [saveFailed, setSaveFailed] = useState(false);

  // Do not erase a human's unsaved edits when an Agent event refreshes the component.
  useEffect(() => {
    if (!dirty && !saving) setDraft(artifact);
  }, [artifact.revision, dirty, saving]);

  useEffect(() => {
    const focus = (event: Event) => { const id = (event as CustomEvent).detail; const day = draft.days.find(value => value.slots.some(slot => slot.place_id === id)); if (day) setSelectedDate(day.date); };
    window.addEventListener("citynexus:draft-focus", focus);
    return () => window.removeEventListener("citynexus:draft-focus", focus);
  }, [draft]);

  const edit = (producer: (value: GoalDraftArtifact) => GoalDraftArtifact) => {
    setMessage("");
    setSaveFailed(false);
    setDirty(true);
    setDraft(producer);
  };
  const change = (day: number, slot: number, values: Partial<GoalDraftSlot>) => {
    edit((current) => ({ ...current, days: current.days.map((value, i) => i !== day ? value : {
      ...value, slots: value.slots.map((item, j) => j === slot ? { ...item, ...values } : item),
    }) }));
  };
  const add = (day: number) => edit((current) => ({ ...current, days: current.days.map((value, i) =>
    i !== day ? value : { ...value, slots: [...value.slots,
      { title: "", time_of_day: "flexible", notes: "" }] },
  ) }));
  const remove = (day: number, slot: number) => edit((current) => ({ ...current, days: current.days.map((value, i) =>
    i !== day ? value : { ...value, slots: value.slots.filter((_, j) => j !== slot) },
  ) }));

  const save = async () => {
    if (disabled || saving) {
      setMessage("Agent 正在运行或草案正在保存，请等待本轮结束。");
      return;
    }
    if (!dirty) {
      setMessage("这份草案已在服务器保存；修改一项安排后才需要重新保存。");
      setSaveFailed(false);
      return;
    }
    const incomplete = draft.days.flatMap((day) =>
      day.slots.filter((slot) => !slot.title.trim() && slot.notes.trim()).map(() => day.date));
    if (incomplete.length > 0) {
      setMessage(`${incomplete[0]} 有未填写标题但写了备注的安排。请补一个标题，或移除该安排。`);
      setSaveFailed(true);
      return;
    }
    // A bare click on "add" should not silently disable saving the whole trip.
    const prepared: GoalDraftArtifact = { ...draft, days: draft.days.map((day) => ({
      ...day, slots: day.slots.filter((slot) => slot.title.trim()).map((slot) => ({
        ...slot, title: slot.title.trim(),
      })),
    })) };
    setSaving(true);
    setMessage("正在保存到服务器…");
    setSaveFailed(false);
    try {
      await onSave(prepared);
      setDraft(prepared);
      setDirty(false);
      setMessage("草案已保存到这趟旅行，刷新页面也可以找回。");
    } catch (error) {
      setSaveFailed(true);
      setMessage(saveFailureMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return <section className="rev-goal-draft" aria-label="可编辑旅行草案">
    <h3>你的旅行草案</h3>
    <p>草案允许信息未知。点击某条安排展开修改；不需要一项一项补完营业时间、票价才能保存。</p>
    <div className="rev-v3-day-tabs" role="tablist" aria-label="选择行程日期">{draft.days.map((day, index) => <button key={day.date} type="button" role="tab" id={`rev-v3-day-tab-${index}`} aria-controls={`rev-v3-day-${index}`} aria-selected={(selectedDate ?? draft.days[0]?.date) === day.date} onClick={() => setSelectedDate(day.date)}>Day {index + 1}<small>{day.date.slice(5)}</small></button>)}</div>
    {draft.days.map((day, dayIndex) => <fieldset role="tabpanel" id={`rev-v3-day-${dayIndex}`} aria-labelledby={`rev-v3-day-tab-${dayIndex}`} hidden={(selectedDate && draft.days.some(item => item.date === selectedDate) ? selectedDate : draft.days[0]?.date) !== day.date} key={day.date} disabled={disabled || saving}>
      <legend>{day.date} · {day.slots.filter((slot) => slot.title.trim()).length} 项安排</legend>
      <div className="rev-draft-day-photos">{[...new Set(day.slots.map(slot => slot.place_id).filter((id): id is string => Boolean(id)))].slice(0, 3).map(id => {
        const media = mediaById[id]?.media;
        if (!media?.can_show || media.place_id !== id) return null;
        const title = day.slots.find(slot => slot.place_id === id)?.title || "行程地点";
        return <figure key={id} data-place-id={id}>
          <button type="button" onClick={() => onPlaceSelect?.(id)} aria-label={"在地图中查看 " + title}>
            <img src={media.thumb_url || media.image_url} loading="lazy" alt={title} onError={event => { event.currentTarget.hidden = true; }} />
          </button>
          <figcaption><strong>{title}</strong><a href={media.source_url} target="_blank" rel="noopener noreferrer">{media.author} · {media.license}</a></figcaption>
        </figure>;
      })}</div>
      {day.slots.length === 0 && <p>还没有安排，可以添加一项想去的地方或待核实事项。</p>}
      {day.slots.map((slot, slotIndex) => <details className="rev-goal-draft-slot" key={slotIndex} data-place-id={slot.place_id || undefined}>
        <summary><strong>{PERIOD[slot.time_of_day] ?? "待定"}</strong> · {slot.title.trim() || "新安排（待填写）"}
          <span>点击编辑</span></summary>
        <div className="rev-goal-draft-slot-fields">
          <label>时段<select value={slot.time_of_day} onChange={(e) => change(dayIndex, slotIndex, { time_of_day: e.target.value as GoalDraftSlot["time_of_day"] })}>
            <option value="morning">上午</option><option value="afternoon">下午</option><option value="evening">晚上</option><option value="flexible">时间灵活</option>
          </select></label>
          <label>安排<input maxLength={160} value={slot.title} onChange={(e) => change(dayIndex, slotIndex, { title: e.target.value })} /></label>
          <label>备注<textarea rows={2} maxLength={500} value={slot.notes} onChange={(e) => change(dayIndex, slotIndex, { notes: e.target.value })} /></label>
          <button type="button" className="rev-workspace-secondary" onClick={() => remove(dayIndex, slotIndex)}>移除这项安排</button>
        </div>
      </details>)}
      {day.slots.length < 6 && <button type="button" className="rev-workspace-secondary"
        onClick={() => add(dayIndex)}>＋ 添加安排</button>}
    </fieldset>)}
    <div className="rev-goal-draft-actions">
      <button type="button" disabled={disabled || saving} onClick={() => void save()}>
        {saving ? "保存中…" : dirty ? "保存草案" : "检查草案保存状态"}
      </button>
      <p role={saveFailed ? "alert" : "status"} aria-live="polite">
        {message || (disabled ? "Agent 正在研究，等这一轮结束即可编辑保存。"
          : dirty ? "修改还没有保存到服务器。" : "当前展示的是已保存版本。")}
      </p>
    </div>
  </section>;
}
