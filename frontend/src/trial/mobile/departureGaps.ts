// One writer for everything the screens say about facts that are still missing before departure.
// The departure to-do (DraftDepartureCard) and the saved-schedule screen (MobilePlanWorkbench) used
// to keep their own wording, and the workbench one asserted a missing transfer route for every
// reason the server could possibly have had - including the price reason that was actually in front
// of it.  Both screens now read these tables, and only the server decides which operation a line is
// allowed to name (goal_preparation.py writes a `resolution` code; a code appears here only when the
// button it points at exists on that card).

export type GapRow = { kind?: string; title?: string; resolution?: string; place_id?: string | null;
  detail?: { verdict?: string; reason_code?: string; source_text?: string } | null };

// What the venue's own source sentence says about the day in the plan.  Four answers, and the one that
// is not "open" quotes the sentence it came from, because a bare 当天不开放 is exactly the kind of claim
// a traveller cannot check for themselves.
export const OPENING_LABELS: Record<string, string> = {
  OPEN_ON_DATE: "来源写这天开放",
  CLOSED_ON_DATE: "来源说这天闭馆",
  TIME_OUTSIDE_WINDOW: "到达时间在来源写的开门时间之外",
  DATE_SPECIFIC_UNKNOWN: "那天来源没给可靠答案",
};

export type OpeningCheck = { sequence_no: number; title: string; verdict: string; reason_code?: string | null;
  window?: number[] | null; defers_to_notice?: boolean; source_text?: string | null };

const clockText = (minutes: number | undefined | null): string | null => {
  if (typeof minutes !== "number" || !Number.isFinite(minutes) || minutes < 0) return null;
  const hour = Math.floor(minutes / 60);
  // 24:00 is a closing bound the provider really writes (「周一至周日 00:00-24:00」 for an open street);
  // dropping it here would leave the card saying "来源写这天开放" with no hours, next to a source
  // sentence on the same screen that states them.
  if (hour > 24) return null;
  return `${String(hour).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
};

// Which half of "we don't know" it is, said differently, because the server read the difference out of
// the source sentence and the traveller can act on one and not the other.
const REASON_LABELS: Record<string, string> = {
  SOURCE_SEASON_NOT_STATED_FOR_THIS_DAY: "来源只写了其他时段的营业时间",
  SOURCE_DEFERS_TO_NOTICE_FOR_A_HOLIDAY: "这天是节假日，来源说以官方通知为准",
  NO_WINDOW_STATED: "来源没写具体时间",
};

export function openingSentence(row: OpeningCheck): string {
  const byReason = REASON_LABELS[String(row.reason_code ?? "")];
  const label = byReason ?? OPENING_LABELS[String(row.verdict)] ?? "这一处当天的开放情况没有读出来";
  const low = Array.isArray(row.window) ? clockText(row.window[0]) : null;
  const high = Array.isArray(row.window) ? clockText(row.window[1]) : null;
  const hours = low && high ? `（来源写的时段 ${low}—${high}）` : "";
  const hedge = row.defers_to_notice && !String(label).includes("官方通知") ? "；来源另写「以官方通知为准」" : "";
  return `${label}${hours}${hedge}`;
}


export const GAP_LABELS: Record<string, string> = {
  SOURCE_IDENTITY: "地点资料接入",
  PLACE_REQUIRED: "具体地点",
  OPENING_HOURS: "营业时间",
  ADMISSION_PRICE: "票价",
  TRANSFER_ROUTE: "转场路线",
  DATE_SPECIFIC_OPENING: "当天是否开放",
};

const ASK_FOR_PLACE = "ASK_AGENT_TO_FIND_PLACE";
const ASK_TO_MOVE_HOUR = "ASK_AGENT_TO_MOVE_HOUR";
const ASK_TO_REPLAN_DAY = "ASK_AGENT_TO_REPLAN_THE_DAY";
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
  [ASK_TO_MOVE_HOUR]: "让 Agent 把这一处挪到开门时间内",
  [ASK_TO_REPLAN_DAY]: "让 Agent 换一天或换一处",
};

export function gapAction(row: GapRow): string {
  return GAP_ACTION_LABELS[String(row.resolution || "")] ?? "让 Agent 继续补这一项";
}

// What the traveller actually says when they press 「和 Agent 补齐出发资料」.  This is the second
// writer over the same server resolutions, in the traveller's own imperative rather than the card's
// third-person label, and it is deliberately not one generic sentence: the button used to send
// 「逐项告诉我出发前缺哪些…先不要改行程」, which asked the Agent for a report of what the screen
// already shows and forbade the one thing the label promises.  The ask now names each open item the
// server listed, keeps everything else untouched, and re-prepares afterwards.
const ASK_VERBS: Record<string, (title: string) => string> = {
  [ASK_FOR_PLACE]: (title) => `「${title}」还没有确定地点，请在正式地点表里找一处定下来`,
  [ASK_FOR_ROUTE]: (title) => `「${title}」前面那一段路还没核实过，请量一次并告诉我几分钟`,
  [ASK_TO_MOVE_HOUR]: (title) => `「${title}」的到达时间不在来源写的时段里，请把这一处挪进去`,
  [ASK_TO_REPLAN_DAY]: (title) => `「${title}」来源说那天闭馆，请换一天或换一处`,
  [ASK_FOR_FACT]: (title) => `「${title}」的来源没给可靠答案，请再向来源要一次`,
};

export function agentAskPrompt(rows: GapRow[], priceAccepted: boolean): string {
  const asks = rows.map((row) => {
    const verb = ASK_VERBS[String(row.resolution || "")];
    return verb ? verb(String(row.title || "").trim() || "这一处") : null;
  }).filter((line): line is string => Boolean(line));
  const unique = [...new Set(asks)];
  const keepQuiet = priceAccepted
    ? "票价这一项我已经确认先不计入预算，不用再问。" : "";
  if (!unique.length) {
    return `屏上出发待办已经没有可问的了，${priceAccepted ? "票价也确认过了，" : ""}这份方案可以直接选用。`;
  }
  return `出发前还缺这几项，请逐项去来源补齐：${unique.join("；")}。${keepQuiet}`
    + "只改上面点名的这几处安排，其它日期和其它安排都保持不变。"
    // The traveller, not the Agent, saves the plan: the draft door is POST .../prepare-plan behind this
    // card's own checkbox and idempotency key, so asking the Agent to "重新准备一份方案" would invite it
    // to claim a write it cannot make.  Ask for the findings; keep the save on this screen.
    + "补完把查到的告诉我，我在这张卡片上再保存一次方案；"
    + "哪项来源还是没有答案，就直接说哪项没有，不要把没答的当成确定的。";
}

// Why the ask needs a second press, said before the press instead of after.  The chat dock sends only
// once the traveller's own model consent stands, so a button claiming to have asked already would report
// an agreement that has not been given; and a line rendered only after the press is not trustworthy
// either -- the press itself remounts this card (the cockpit refetches the task), which walk-66 and
// walk-69 both measured as the note never appearing.  So it stands next to the button permanently.
export const ASK_HOW_IT_WORKS = "按这一个按钮会把上面这些项写进底部的对话框，再按「发送 ↑」才交给 Agent 去查。";

// The count the card shows right above that button, so the traveller knows whether pressing it can
// still move anything.
export function pendingCountSentence(count: number): string {
  if (count <= 0) return "屏上的出发待办都齐了，可以直接选用这份方案。";
  return `还有 ${count} 项要主动向来源要，按下面这一个按钮逐项去补。`;
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
// does not make it that afternoon, so it is named apart instead of inflating "today's" count.  A hop the
// walking door could not answer is now measured as public transport, and that too is named apart: a bus
// minute shown as footsteps would send a traveller walking somewhere they were never told to walk.
export function routeSentence(verified: number, total: number, frozen: boolean, overnight: number,
  transit = 0): string {
  if (!total) return "这版方案里没有相邻两站之间的转场要核实。";
  const parts = [overnight > 0 ? `${overnight} 段是跨夜衔接` : "",
    transit > 0 ? `${transit} 段按公共交通核实` : ""].filter(Boolean);
  const tail = parts.length ? `（其中 ${parts.join("，")}）` : "";
  if (verified < total) return `转场已核实 ${verified}/${total}${tail}，还有 ${total - verified} 段没有来源回答。`;
  return frozen ? `转场已核实 ${verified}/${total}${tail} · 已冻结进这版方案`
    : `转场已核实 ${verified}/${total}${tail}，还没有冻结进这版方案。`;
}

// After a reload this card holds only the stored answer: `routes` is null again, while the plan itself
// still carries the frozen facts and the stored answer still says mobility_frozen=true
// (backend/app/agent/goal_route_freeze.py:372).  Telling a traveller then that nothing was ever verified
// sends them to redo work the plan already holds -- which is what the screen actually did after the
// reload measured in walk-74.  No count is claimed here, because the stored answer keeps the flag and
// not the verified/total pair; the numbers come back as soon as the door is pressed again.
export const FROZEN_ROUTE_SENTENCE = "转场已经核实并冻结进这版方案。";

// One hop the map would not answer, in the traveller's words.
//
// Why this exists: the band above says 「还有 N 段没有来源回答」 and stops, and the freeze answer already
// carries a `reason_code` per hop that no screen read (grep of src/ for PROVIDER_ROUTE_UNAVAILABLE and
// AMAP_NOT_CONFIGURED returns zero lines).  Two very different situations were therefore printed as the
// same sentence: the provider answered "I have no route for this pair" (measured for 八达岭长城 → 故宫 and
// 雁栖湖 → 故宫, trial/results/20261022_v3_human_chrome/amap-transit-within-city-1.txt:3 and :5), and the
// provider refused to talk at all -- a spent quota, a rejected key, no key on the server.  The first is
// the traveller's planning problem; the second is theirs to fix, and the traveller should be told to come
// back later rather than to change the plan.
export type RouteHopRow = {
  from_name?: string | null; to_name?: string | null;
  status?: string | null; reason_code?: string | null;
};

const HOP_REFUSAL_SENTENCES: Record<string, string> = {
  AMAP_QUOTA_EXCEEDED: "地图服务今天的查询次数已经用完，稍后再核实这一段。",
  AMAP_HTTP_ERROR: "地图服务没有响应，稍后再核实这一段。",
  AMAP_INVALID_KEY: "这台服务的高德查询凭证不可用，需要运维处理。",
  AMAP_SERVICE_PERMISSION_DENIED: "这台服务的高德凭证没有开通路线查询，需要运维处理。",
  AMAP_NOT_CONFIGURED: "这台服务还没有配置高德查询。",
  AMAP_NO_ROUTE: "高德说这一段没有步行路线，公共交通也没答上来。",
  AMAP_PROVIDER_REJECTED: "高德说这一段没有步行路线，公共交通也没答上来。",
};

const HOP_REFUSAL_FALLBACK = "地图服务没有回答这一段。";

export function unansweredHopSentences(edges: RouteHopRow[], limit = 3): string[] {
  const unanswered = (edges || []).filter((row) => row && row.status === "ROUTE_UNAVAILABLE");
  const named = unanswered.slice(0, limit).map((row) => {
    const reason = HOP_REFUSAL_SENTENCES[String(row.reason_code || "")] || HOP_REFUSAL_FALLBACK;
    const from = String(row.from_name || "").trim();
    const to = String(row.to_name || "").trim();
    return from && to ? `${from} → ${to}：${reason}` : reason;
  });
  const rest = unanswered.length - named.length;
  if (rest > 0) named.push(`另有 ${rest} 段同样没有回答。`);
  return named;
}
