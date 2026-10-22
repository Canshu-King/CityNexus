// One writer for everything the screens say about facts that are still missing before departure.
// The departure to-do (DraftDepartureCard) and the saved-schedule screen (MobilePlanWorkbench) used
// to keep their own wording, and the workbench one asserted a missing transfer route for every
// reason the server could possibly have had - including the price reason that was actually in front
// of it.  Both screens now read these tables, and only the server decides which operation a line is
// allowed to name (goal_preparation.py writes a `resolution` code; a code appears here only when the
// button it points at exists on that card).

export type GapRow = { kind?: string; title?: string; resolution?: string; place_id?: string | null };

export const GAP_LABELS: Record<string, string> = {
  SOURCE_IDENTITY: "地点资料接入",
  PLACE_REQUIRED: "具体地点",
  OPENING_HOURS: "营业时间",
  ADMISSION_PRICE: "票价",
  TRANSFER_ROUTE: "转场路线",
};

const ASK_FOR_PLACE = "ASK_AGENT_TO_FIND_PLACE";
const ASK_FOR_FACT = "ASK_AGENT_FOR_PLACE_FACT";
const ASK_FOR_ROUTE = "ASK_AGENT_TO_MEASURE_HOP";
const PRICE_BY_TRAVELLER = "PRICE_HELD_BY_TRAVELLER";

// Every agent clause names the button that is on this very card, in its own words.
export const ASK_AGENT_BUTTON = "和 Agent 补齐出发资料";

const GAP_ACTION_LABELS: Record<string, string> = {
  [ASK_FOR_PLACE]: "让 Agent 找这一处",
  [ASK_FOR_FACT]: "让 Agent 向来源再要这一项",
  [ASK_FOR_ROUTE]: "让 Agent 量这一段路",
  [PRICE_BY_TRAVELLER]: "没有来源给出这一项的价格",
};

export function gapAction(row: GapRow): string {
  return GAP_ACTION_LABELS[String(row.resolution || "")] ?? "让 Agent 继续补这一项";
}

function labelsIn(rows: GapRow[]): string[] {
  const present = new Set(rows.map((row) => String(row.kind || "")));
  return Object.keys(GAP_LABELS).filter((kind) => present.has(kind)).map((kind) => {
    const needsAPlace = kind === "PLACE_REQUIRED" || kind === "SOURCE_IDENTITY";
    if (!needsAPlace) return GAP_LABELS[kind];
    const names = [...new Set(rows.filter((row) => String(row.kind || "") === kind)
      .map((row) => String(row.title || "").trim()).filter(Boolean))].slice(0, 2);
    return names.length ? `${GAP_LABELS[kind]}（${names.join("、")}）` : GAP_LABELS[kind];
  });
}

// Why a saved schedule cannot be chosen yet, from the reasons the server actually listed.
// A candidate with no frozen walking evidence says so too, and names the button that closes it: the
// draft door itself freezes nothing (backend/app/agent/goal_preparation.py:76), selection reads a
// snapshot id (backend/app/main.py:18120), and 「核实并冻结今天的转场」 on the departure card is the
// only thing on this screen that writes one.
export function missingFactsSentence(rows: GapRow[], hasMobilityEvidence = true): string {
  const labels = labelsIn(rows);
  const parts: string[] = [];
  if (labels.length) parts.push(`这版方案还缺：${labels.join("、")}。出发待办逐处写着找谁要。`);
  if (!hasMobilityEvidence) parts.push("这份候选里还没有冻结的步行时间，出发待办下方可以核实并冻结今天的转场。");
  if (!parts.length) return "这份方案现在还不能选用。";
  return parts.join("");
}

// Bands the traveller confirmed but nobody has placed. They stay on the day as a note and are not
// routed, so the schedule screen has to say which it is looking at rather than showing an empty slot.
export function bandSentence(count: number): string {
  return `另有 ${count} 段时间还没有确定地点，没有算进转场核实。`;
}

// The one door that turns "no source answered the price" into a decision the traveller made, in their
// own words. Nothing here may read as a booking, a bought ticket, or a budget that holds: the server
// keeps unknown_cost_included false and the plan's total does not gain these items.
export const PRICE_CONSENT_BUTTON = "票价没有来源，我接受先不计入预算";
export const PRICE_SWAP_BUTTON = "让 Agent 换成价格明确的地点";
export const PRICE_SWAP_PROMPT = "把票价没有来源的地方换成门票价格明确的地点，其他安排保持不变";

export function unknownPricePlaceIds(rows: GapRow[]): string[] {
  const ids = rows.filter((row) => String(row.kind || "") === "ADMISSION_PRICE" && row.place_id)
    .map((row) => String(row.place_id));
  return [...new Set(ids)];
}

export function priceUnknownSentence(knownMinor: number, unknownCount: number): string {
  const known = knownMinor > 0 ? `已知费用 ¥${(knownMinor / 100).toFixed(0)}` : "还没有来源给过确定的费用";
  return `${known}；另有 ${unknownCount} 处门票没有来源，预算里没有把它们算作 0 元，${budgetNote(unknownCount)}`;
}

function budgetNote(unknownCount: number): string {
  return unknownCount > 0 ? "实际花费可能超出预算。" : "费用已全部核实。";
}

export function priceAcceptedSentence(unknownCount: number, knownMinor: number): string {
  const known = knownMinor > 0 ? `已计入 ¥${(knownMinor / 100).toFixed(0)}` : "没有已核实的费用";
  return `按你的确认保存：这 ${unknownCount} 处门票仍未核实，${known}，出发前请自己留意现场票价。`;
}

// The walked hops, as the card reports them. An overnight link is measured for real but the traveller
// does not make it that afternoon, so it is named apart instead of inflating "today's" count.
export function routeSentence(verified: number, total: number, frozen: boolean, overnight: number): string {
  if (!total) return "这版方案里没有相邻两站之间的转场要核实。";
  const tail = overnight > 0 ? `（其中 ${overnight} 段是跨夜衔接）` : "";
  if (verified < total) return `转场已核实 ${verified}/${total}${tail}，还有 ${total - verified} 段没有来源回答。`;
  return frozen ? `转场已核实 ${verified}/${total}${tail} · 已冻结进这版方案`
    : `转场已核实 ${verified}/${total}${tail}，还没有冻结进这版方案。`;
}
