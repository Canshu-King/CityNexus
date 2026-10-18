import { useEffect, useState } from "react";
import type { TravelBrief, TravelPlanningInput } from "../../api/citynexus";
import { formatMinorMoney } from "../../lib/money";
import { formatCost, formatOpeningHours } from "./DiscoveryPlaceCard";

const interests = [
  ["local_food", "当地美食"], ["night_market", "夜市小吃"], ["old_town", "古城老街"],
  ["heritage", "人文古迹"], ["nature", "山野自然"], ["coast", "海边水岸"],
  ["architecture", "建筑文化"], ["nightlife", "夜间活动"], ["photography", "摄影打卡"],
  ["family", "亲子活动"], ["shopping", "逛街购物"], ["park/garden", "公园绿地"],
  ["cafe", "咖啡馆"], ["museum/gallery", "博物馆艺术"], ["library", "图书馆"],
] as const;
const labels: Record<string, string> = { outdoor: "户外兴趣", food: "美食兴趣", cultural: "文化兴趣",
  library: "阅读兴趣", low_walking: "少走路偏好", day_rhythm: "作息时间" };
const blockers: Record<string, string> = {OPENING_UNVERIFIED:"营业时间",COST_UNKNOWN:"费用",ACCESS_RESTRICTED:"开放权限"};

type PlaceCandidate = TravelPlanningInput["candidates"][number];

function missingPlaceFacts(place: PlaceCandidate): string[] {
  const missing: string[] = [];
  if (!formatOpeningHours(place.opening_hours)) missing.push("营业时间");
  if (formatCost(place) === "费用未知") missing.push("费用");
  return missing;
}

function canRefreshPlaceFacts(place: PlaceCandidate): boolean {
  return place.provider_provenance === "LIVE_PROVIDER" && ["overpass", "photon"].includes(place.provider_key) &&
    /^(node|way|relation)$/.test(place.osm_type) && /^[1-9][0-9]*$/.test(place.osm_id) &&
    (place.source_url === `https://www.openstreetmap.org/${place.osm_type}/${place.osm_id}` ||
      place.source_url === `https://openstreetmap.org/${place.osm_type}/${place.osm_id}`) &&
    place.public_access_state !== "RESTRICTED";
}

function TravelPlaceCard({ place, selected, selectedCount, disabled, onSelect, onRefreshFacts }: {
  place: PlaceCandidate;
  selected: boolean;
  selectedCount: number;
  disabled: boolean;
  onSelect: (checked: boolean) => void;
  onRefreshFacts: (place: PlaceCandidate) => Promise<void>;
}) {
  const [consented, setConsented] = useState(false);
  const missing = missingPlaceFacts(place);
  const refreshable = missing.length > 0 && place.facts_status == null && canRefreshPlaceFacts(place);
  useEffect(() => { setConsented(false); }, [place.receipt_id, place.facts_status, place.opening_hours, place.cost_evidence]);

  return <div className="rev-travel-place" data-testid={`rev-travel-place-${place.candidate_id}`}>
    <label><input type="checkbox" disabled={disabled || place.public_access_state === "RESTRICTED" || (!selected && selectedCount >= 6)}
      checked={selected} onChange={(event) => { setConsented(false); onSelect(event.target.checked); }} />{place.name}</label>
    <p>营业时间：{formatOpeningHours(place.opening_hours) ?? "未知"} · {formatCost(place)}</p>
    <p>{place.provider_provenance === "LIVE_PROVIDER" ? "公开地图来源" : place.provider_provenance === "TEST_PROVIDER" ? "测试地点" : "来源待确认"}</p>
    {missing.length > 0
      ? <p>待补：{missing.join("、")}</p>
      : place.selection_state === "READY_FOR_NATIVE_PLAN"
        ? <p>营业与费用资料可用于排程</p>
        : <p>待补：{place.selection_blockers?.map((key) => blockers[key] ?? "地点资料").join("、") || "地点资料"}</p>}
    {place.facts_status === "UNAVAILABLE" && missing.length > 0 &&
      <p className="rev-plan-gap">此前查询未能补齐以上资料；可以改选其他地点。</p>}
    {place.facts_status === "SUCCESS" && missing.length > 0 &&
      <p className="rev-plan-gap">已查询 OpenStreetMap；以上字段仍未知，可以改选其他地点。</p>}
    {place.source_url && /^https:\/\/(www\.)?openstreetmap\.org\/(node|way|relation)\/[0-9]+$/.test(place.source_url) && <a href={place.source_url} target="_blank" rel="noreferrer">查看地点来源 ↗</a>}
    {refreshable && <details data-testid={`rev-plan-facts-detail-${place.candidate_id}`} onToggle={(event) => {
      if (!event.currentTarget.open) setConsented(false);
    }}>
      <summary>补齐营业和费用资料</summary>
      <p>提交后，服务器会将 OpenStreetMap 地点标识 {place.osm_type}/{place.osm_id} 发送给 OpenStreetMap，查询营业时间和费用。每次提交只发起一次查询，不会自动重试。</p>
      <form onSubmit={(event) => {
        event.preventDefault();
        if (consented && !disabled) {
          setConsented(false);
          void onRefreshFacts(place);
        }
      }}>
        <label><input type="checkbox" checked={consented} disabled={disabled}
          data-testid={`rev-plan-facts-consent-${place.candidate_id}`}
          onChange={(event) => setConsented(event.target.checked)} />我同意本次将此 OpenStreetMap 地点标识发送给 OpenStreetMap 查询</label>
        <button type="submit" disabled={disabled || !consented}
          data-testid={`rev-plan-facts-refresh-${place.candidate_id}`}>查询地点详情一次</button>
      </form>
    </details>}
  </div>;
}

export function TravelBriefPreview({ input, selected, onSelect, onSave, onRefreshFacts, disabled }: {
  input: TravelPlanningInput; selected: string[]; onSelect: (ids: string[]) => void;
  onSave: (brief: TravelBrief) => Promise<void>;
  onRefreshFacts: (place: PlaceCandidate) => Promise<void>;
  disabled: boolean;
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
      {input.intent.unmapped_interests?.length ? <p className="rev-plan-gap">还未转成正式规划约束的兴趣：{input.intent.unmapped_interests.join("、")}。已为你保存在旅行需求中，后续由 AI 研究，不会被静默删除。</p> : null}
      {input.intent.goal && <p className="rev-plan-gap">开放式需求原文已保留，当前规则规划器仍不能完整执行这些要求。</p>}
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
    {input.candidates.map((place) => <TravelPlaceCard key={place.candidate_id} place={place}
      selected={selected.includes(place.candidate_id)} selectedCount={selected.length} disabled={disabled}
      onSelect={(checked) => onSelect(checked ? [...selected, place.candidate_id] : selected.filter((id) => id !== place.candidate_id))}
      onRefreshFacts={onRefreshFacts} />)}
    <h3>多日想去清单 · 未排定</h3>
    <p className="rev-plan-gap">地点先按天分组供你挑选。营业时间、票价及转场尚需核实。</p>
    {slots.map(({date, places}) => <div className="rev-travel-day" key={date}>
      <strong>{date}</strong>{places.length ? <ul>{places.map((place) => <li key={place.candidate_id}>{place.name} · 转场时间待确认</li>)}</ul> : <p>这一天还没有选地点。</p>}
    </div>)}
  </section>;
}
