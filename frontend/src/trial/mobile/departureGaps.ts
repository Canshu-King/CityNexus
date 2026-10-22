// One writer for everything the screens say about facts that are still missing before departure.
// The departure to-do (DraftDepartureCard) and the saved-schedule screen (MobilePlanWorkbench) used
// to keep their own wording, and the workbench one asserted a missing transfer route for every
// reason the server could possibly have had - including the price reason that was actually in front
// of it.  Both screens now read these tables, and only the server decides which operation a line is
// allowed to name (goal_preparation.py writes a `resolution` code; a code appears here only when the
// button it points at exists on that card).

export type GapRow = { kind?: string; title?: string; resolution?: string };

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
export function missingFactsSentence(rows: GapRow[]): string {
  const labels = labelsIn(rows);
  if (!labels.length) return "这份方案现在还不能选用。";
  return `这版方案还缺：${labels.join("、")}。出发待办逐处写着找谁要。`;
}
