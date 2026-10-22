import { useRef, useState } from "react";
import { Check, ChevronDown, Compass, Route, Sparkles } from "lucide-react";
import type { GoalDraftArtifact, GoalDraftVariant } from "../../api/citynexus";
import "./GoalDraftVariants.css";

const PERIOD: Record<string, string> = {
  morning: "上午",
  afternoon: "下午",
  evening: "晚上",
  flexible: "时间灵活",
};

// What a version actually is: which day, which half-day, which place. Everything else on a saved
// draft (notes, provenance fields the server fills in) is not part of the choice.
const draftSignature = (artifact: GoalDraftArtifact) => JSON.stringify(
  artifact.days.map((day) => [day.date, day.slots.map((slot) => [slot.time_of_day, slot.title.trim(), slot.place_id || ""])]),
);

type Props = {
  variants: GoalDraftVariant[];
  current?: GoalDraftArtifact | null;
  disabled?: boolean;
  onChoose: (artifact: GoalDraftArtifact) => Promise<void>;
};

export function GoalDraftVariants({ variants, current, disabled = false, onChoose }: Props) {
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [choosingId, setChoosingId] = useState<string | null>(null);
  const [failedId, setFailedId] = useState<string | null>(null);
  const choosing = useRef(false);

  if (variants.length === 0) return null;

  const choose = async (variant: GoalDraftVariant) => {
    if (disabled || choosing.current) return;
    choosing.current = true;
    setChoosingId(variant.id);
    setFailedId(null);
    try {
      await onChoose(variant.artifact);
    } catch {
      setFailedId(variant.id);
    } finally {
      choosing.current = false;
      setChoosingId(null);
    }
  };

  return (
    <section className="rev-goal-variants" aria-label="旅行方案对比">
      <div className="rev-goal-variants-heading">
        <div className="rev-goal-variants-heading-icon" aria-hidden="true"><Sparkles size={17} /></div>
        <div>
          <h3>挑一份更合适的安排</h3>
          <p>选用后可以继续调整每天的安排。</p>
        </div>
      </div>

      <div className="rev-v3-variant-tabs" role="tablist" aria-label="比较旅行方案">{variants.map((variant, index) => <button key={variant.id} type="button" role="tab" id={`rev-v3-variant-tab-${index}`} aria-controls={`rev-v3-variant-${index}`} aria-selected={(previewId ?? variants[0].id) === variant.id} onClick={() => { setPreviewId(variant.id); setExpandedId(variant.id); }}>{String.fromCharCode(65 + index)} · {variant.title}</button>)}</div>
      <div className="rev-goal-variants-list">
        {variants.map((variant, index) => {
          const expanded = expandedId === variant.id;
          // The saved draft comes back through the server's own normaliser, which fills in fields the
          // version card never carried. Comparing the two documents verbatim made every card keep
          // 「选用这份安排」 after one was chosen, so the traveller could not see which version the
          // schedule is on. The plan itself is the per-day list of period, place and title.
          const chosen = Boolean(current && draftSignature(current) === draftSignature(variant.artifact));
          const choosingThis = choosingId === variant.id;
          const unknowns = variant.unknown_summary.map((item) => item.trim().slice(0, 180)).filter(Boolean);
          const detailId = `rev-goal-variant-details-${index}`;
          return (
            <article className="rev-goal-variant-card" role="tabpanel" id={`rev-v3-variant-${index}`} aria-labelledby={`rev-v3-variant-tab-${index}`} hidden={(previewId ?? variants[0].id) !== variant.id} key={variant.id} data-plan-style={variant.id} data-expanded={expanded ? "true" : "false"}>
              <div className="rev-goal-variant-card-head">
                <span className="rev-goal-variant-number">{String.fromCharCode(65 + index)}</span>
                <div className="rev-goal-variant-title">
                  <h4>{variant.title}</h4>
                  <p>{variant.comparison}</p>
                </div>
              </div>

              <div className="rev-goal-variant-sources" aria-label="方案引用">
                <span><Compass size={14} aria-hidden="true" />地点 {variant.source_place_ids.length}</span>
                <span><Route size={14} aria-hidden="true" />路线 {variant.route_ids.length}</span>
                <span>{variant.artifact.days.length} 天</span>
              </div>

              <button
                type="button"
                className="rev-goal-variant-expand"
                aria-expanded={expanded}
                aria-controls={detailId}
                onClick={() => setExpandedId(expanded ? null : variant.id)}
              >
                {expanded ? "收起每天安排" : "查看每天安排与待查事项"}
                <ChevronDown size={16} aria-hidden="true" />
              </button>

              <div className="rev-goal-variant-details" id={detailId} hidden={!expanded}>
                <div className="rev-goal-variant-days">
                  {variant.artifact.days.map((day) => (
                    <section className="rev-goal-variant-day" key={day.date}>
                      <h5>{day.date}</h5>
                      {day.slots.length ? (
                        <ol>
                          {day.slots.map((slot, slotIndex) => (
                            <li key={`${day.date}-${slotIndex}`}>
                              <span>{PERIOD[slot.time_of_day] ?? "待定"}</span>
                              <strong>{slot.title.trim() || slot.notes.trim() || "待确认安排"}</strong>
                            </li>
                          ))}
                        </ol>
                      ) : <p>当天还没有安排。</p>}
                    </section>
                  ))}
                </div>
                <div className="rev-goal-variant-unknowns">
                  <strong>还需要确认</strong>
                  {unknowns.length ? (
                    <ul>{unknowns.map((item, itemIndex) => <li key={`${variant.id}-unknown-${itemIndex}`}>{item}</li>)}</ul>
                  ) : <p>暂无待查事项。</p>}
                </div>
              </div>

              <button
                type="button"
                className="rev-goal-variant-choose"
                disabled={disabled || choosingId !== null || chosen}
                onClick={() => void choose(variant)}
              >
                {chosen ? "已选为当前行程" : choosingThis ? "正在选用…" : choosingId !== null ? "请稍候…" : <><Check size={16} aria-hidden="true" />选用这份安排</>}
              </button>
              {failedId === variant.id && <p className="rev-goal-variant-error" role="alert">这份安排没能选用，请重试。</p>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
