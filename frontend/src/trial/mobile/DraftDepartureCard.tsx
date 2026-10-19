import type { DraftGoalTask } from "../../api/citynexus";

/** Show the selected server draft in place; source candidate IDs are never Place UUIDs. */
export function DraftDepartureCard({ task, onDiscuss }: { task: DraftGoalTask; onDiscuss: (goal: string) => void }) {
  const days = task.draft_artifact?.days ?? [];
  const slots = days.flatMap(day => day.slots.filter(slot => slot.title.trim()));
  if (!slots.length) return null;
  const sources = new Map((task.candidate_places ?? []).map(place => [place.id, place]));
  const places = [...new Map(slots.filter(slot => slot.place_id).map(slot => [slot.place_id!, slot])).values()];
  return <section className="rev-v3-departure" aria-label="当前草案的出发准备">
    <h3>从这份安排继续</h3>
    <p>{days.length} 天 · {slots.length} 项安排，保留在当前旅行。</p>
    <ul>{places.map(slot => {
      const source = sources.get(slot.place_id!);
      return <li key={slot.place_id}><strong>{slot.title}</strong><span>{source?.opening_state === "KNOWN" ? "营业资料已读取" : "营业待核实"} · {source?.cost_evidence.status === "KNOWN" ? "费用资料已读取" : "费用待核实"}</span></li>;
    })}</ul>
    <p>正式出发还需要把这份安排接入正式计划。你可以先和 Agent 补齐地点与转场资料，草案会继续保留。</p>
    <button type="button" onClick={() => onDiscuss("继续讨论当前选好的草案，保留所有日期和地点。逐项告诉我出发前缺哪些营业、费用或转场资料，并给我处理选择，先不要改行程。")}>
      和 Agent 补齐出发资料
    </button>
  </section>;
}
