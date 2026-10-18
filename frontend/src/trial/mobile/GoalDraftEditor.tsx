import { useEffect, useState } from "react";
import type { GoalDraftArtifact, GoalDraftSlot } from "../../api/citynexus";

export function GoalDraftEditor({ artifact, disabled, onSave }: {
  artifact: GoalDraftArtifact; disabled: boolean; onSave: (draft: GoalDraftArtifact) => Promise<void>;
}) {
  const [draft, setDraft] = useState(artifact);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => { setDraft(artifact); }, [artifact.revision]);
  const change = (day: number, slot: number, values: Partial<GoalDraftSlot>) => {
    setMessage("");
    setDraft((current) => ({ ...current, days: current.days.map((value, i) => i !== day ? value : {
      ...value, slots: value.slots.map((item, j) => j === slot ? { ...item, ...values } : item),
    }) }));
  };
  return <section className="rev-goal-draft" aria-label="可编辑旅行草案">
    <h3>你的旅行草案</h3><p>先安排想做的事，营业、费用和交通时间可以继续查。</p>
    {draft.days.map((day, dayIndex) => <fieldset key={day.date} disabled={disabled || saving}>
      <legend>{day.date}</legend>
      {day.slots.map((slot, slotIndex) => <div className="rev-goal-draft-slot" key={slotIndex}>
        <label>时段<select value={slot.time_of_day} onChange={(e) => change(dayIndex, slotIndex, { time_of_day: e.target.value as GoalDraftSlot["time_of_day"] })}>
          <option value="morning">上午</option><option value="afternoon">下午</option><option value="evening">晚上</option><option value="flexible">时间灵活</option>
        </select></label>
        <label>安排<input maxLength={160} value={slot.title} onChange={(e) => change(dayIndex, slotIndex, { title: e.target.value })} /></label>
        <label>备注<textarea rows={2} maxLength={500} value={slot.notes} onChange={(e) => change(dayIndex, slotIndex, { notes: e.target.value })} /></label>
      </div>)}
      {day.slots.length < 6 && <button type="button" className="rev-workspace-secondary" onClick={() => setDraft((current) => ({
        ...current, days: current.days.map((value, i) => i !== dayIndex ? value : { ...value, slots: [...value.slots, { title: "", time_of_day: "flexible", notes: "" }] }),
      }))}>添加安排</button>}
    </fieldset>)}
    <button type="button" disabled={disabled || saving || draft.days.some((day) => day.slots.some((slot) => !slot.title.trim()))}
      onClick={async () => { setSaving(true); setMessage(""); try { await onSave(draft); setMessage("草案已保存"); }
        catch { setMessage("保存未完成，请刷新任务后再试。"); } finally { setSaving(false); } }}>{saving ? "保存中…" : "保存草案"}</button>
    {message && <p role="status">{message}</p>}
  </section>;
}
