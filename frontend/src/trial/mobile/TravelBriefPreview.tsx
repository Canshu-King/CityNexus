import { useEffect, useState } from "react";
import type { TravelBrief, TravelPlanningInput } from "../../api/citynexus";
import { formatMinorMoney } from "../../lib/money";
import { formatCost, formatOpeningHours } from "./DiscoveryPlaceCard";

const interests = [ ["park/garden", "公园绿地"], ["cafe", "美食咖啡"],
  ["museum/gallery", "博物馆艺术"], ["library", "安静阅读"] ] as const;
const labels: Record<string, string> = { outdoor: "户外兴趣", food: "美食兴趣", cultural: "文化兴趣",
  library: "阅读兴趣", low_walking: "少走路偏好", day_rhythm: "作息时间" };
const blockers: Record<string, string> = {OPENING_UNVERIFIED:"营业时间",COST_UNKNOWN:"费用",ACCESS_RESTRICTED:"开放权限"};

export function TravelBriefPreview({ input, selected, onSelect, onSave, disabled }: {
  input: TravelPlanningInput; selected: string[]; onSelect: (ids: string[]) => void;
  onSave: (brief: TravelBrief) => Promise<void>; disabled: boolean;
}) {
  const [goal, setGoal] = useState(input.intent?.goal ?? "");
  const [chosen, setChosen] = useState<TravelBrief["interests"]>(input.intent?.interests ?? []);
  const [energy, setEnergy] = useState<TravelBrief["energy"]>(input.intent?.energy ?? "steady");
  useEffect(() => {
    setGoal(input.intent?.goal ?? ""); setChosen(input.intent?.interests ?? []); setEnergy(input.intent?.energy ?? "steady");
  }, [input.intent?.id, input.intent?.updated_at]);
  const candidates = input.candidates.filter((item) => selected.includes(item.candidate_id));
  const slots = input.trip.dates.map((date) => ({ date, places: [] as typeof candidates }));
  candidates.forEach((candidate, index) => slots[index % Math.max(1, slots.length)]?.places.push(candidate));
  return <section className="rev-travel-input" data-testid="rev-travel-input">
    <h3>这次想怎么玩</h3>
    <p>{input.trip.dates.length} 天 · {input.trip.party_size} 人 · 预算 {formatMinorMoney(input.trip.budget.amount_minor, input.trip.budget.currency, "zh-CN")}</p>
    {input.intent && <>
      <p className="rev-plan-gap">已保存到这份行程，重新登录后可恢复。</p>
      <p>{input.intent.goal}</p>
      <p>规划器已接收：{[...new Set(input.intent.mapped_preferences.map((item) => labels[item.preference] ?? item.preference))].join("、") || "日期、人数和预算"}</p>
      {input.intent.goal && <p className="rev-plan-gap">原文已保留；未列出的开放式要求还需你确认，暂不作为硬性排程条件。</p>}
    </>}
    <details><summary>修改旅行需求</summary>
      <form onSubmit={(event) => { event.preventDefault(); if (!disabled) void onSave({ goal, interests: chosen, energy }); }}>
        <label>想做什么<textarea value={goal} maxLength={1000} disabled={disabled} onChange={(event) => setGoal(event.target.value)} /></label>
        <fieldset disabled={disabled}><legend>兴趣</legend>{interests.map(([value, label]) => <label key={value}>
          <input type="checkbox" checked={chosen.includes(value)} onChange={(event) => setChosen(event.target.checked ? [...chosen, value] : chosen.filter((item) => item !== value))} />{label}
        </label>)}</fieldset>
        <label>旅行节奏<select disabled={disabled} value={energy} onChange={(event) => setEnergy(event.target.value as TravelBrief["energy"])}>
          <option value="easy">轻松少走</option><option value="steady">适中</option><option value="full">充实</option>
        </select></label>
        <button disabled={disabled} type="submit">保存旅行需求</button>
      </form>
    </details>
    <h3>把想去的地点放在一起</h3>
    <p>选择 2–6 处。先看想去清单，资料齐全后再生成正式方案。</p>
    {input.candidates.length === 0 && <p>还没有地点，去探索添加。</p>}
    {input.candidates.map((place) => <div className="rev-travel-place" key={place.candidate_id}>
      <label><input type="checkbox" disabled={disabled || place.public_access_state === "RESTRICTED" || (!selected.includes(place.candidate_id) && selected.length >= 6)}
        checked={selected.includes(place.candidate_id)} onChange={(event) => onSelect(event.target.checked ? [...selected, place.candidate_id] : selected.filter((id) => id !== place.candidate_id))} />{place.name}</label>
      <p>营业时间：{formatOpeningHours(place.opening_hours) ?? "未知"} · {formatCost(place)}</p>
      <p>{place.provider_provenance === "LIVE_PROVIDER" ? "公开地图来源" : place.provider_provenance === "TEST_PROVIDER" ? "测试地点" : "来源待确认"}</p>
      <p>{place.selection_state === "READY_FOR_NATIVE_PLAN" ? "营业与费用资料可用于排程" : `待补：${place.selection_blockers?.map((key) => blockers[key] ?? "地点资料").join("、") || "营业与费用"}`}</p>
      {place.source_url && /^https:\/\/(www\.)?openstreetmap\.org\/(node|way|relation)\/[0-9]+$/.test(place.source_url) && <a href={place.source_url} target="_blank" rel="noreferrer">查看地点来源 ↗</a>}
    </div>)}
    <h3>多日想去清单 · 未排定</h3>
    <p className="rev-plan-gap">地点先按天分组供你挑选。营业时间、票价及转场尚需核实。</p>
    {slots.map(({date, places}) => <div className="rev-travel-day" key={date}>
      <strong>{date}</strong>{places.length ? <ul>{places.map((place) => <li key={place.candidate_id}>{place.name} · 转场时间待确认</li>)}</ul> : <p>这一天还没有选地点。</p>}
    </div>)}
  </section>;
}
