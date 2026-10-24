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
  transit = 0, reasonCode?: string | null, replaced = 0, overCap = 0, capMeters?: number | null): string {
  // An empty edge list has two very different causes, and only one of them is "this plan has no hops".
  if (!total) return reasonCode === "NO_PLACED_STOPS"
    ? "这几处还没有被认成正式地点，所以没有可以量转场的两站。先在对话里让我把地点补认出来。"
    : "这版方案里没有相邻两站之间的转场要核实。";
  // A hop the traveller said they would not walk is not quietly counted as a walk: the limit they wrote,
  // how many hops it moved, and how many stayed over it are each named, because the difference between
  // those two is whether the day is on a bus or on foot.
  const capText = capMeters ? `${(capMeters / 1000).toFixed(capMeters % 1000 ? 1 : 0)} 公里` : "你写的上限";
  const parts = [overnight > 0 ? `${overnight} 段是跨夜衔接` : "",
    transit > 0 ? `${transit} 段按公共交通核实` : "",
    replaced > 0 ? `其中 ${replaced} 段超过${capText}，已换成公共交通核实` : "",
    overCap > 0 ? `另有 ${overCap} 段公共交通没有答案，仍按步行核实，超过${capText}` : ""].filter(Boolean);
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
  // Asked too often at once: nothing is spent, and a moment is enough.  Measured with eight back-to-back
  // calls, three refused and the next one OK four seconds later
  // (trial/results/20261022_v3_human_chrome/amap-burst-infocode-1.txt:2 against :3).
  AMAP_RATE_LIMITED: "地图服务一次被问得太急，过几秒再核实这一段。",
  AMAP_HTTP_ERROR: "地图服务没有响应，稍后再核实这一段。",
  AMAP_INVALID_KEY: "这台服务的高德查询凭证不可用，需要运维处理。",
  AMAP_SERVICE_PERMISSION_DENIED: "这台服务的高德凭证没有开通路线查询，需要运维处理。",
  AMAP_NOT_CONFIGURED: "这台服务还没有配置高德查询。",
  AMAP_NO_ROUTE: "高德说这一段没有步行路线，公共交通也没答上来。",
  AMAP_PROVIDER_REJECTED: "高德说这一段没有步行路线，公共交通也没答上来。",
  // The provider has its own words for a pair it will not route at all -- infocode 20803
  // OVER_DIRECTION_RANGE, measured on 什刹海/王府井 one side of 八达岭 while the same door answered an
  // 800 m hop in the city at the same minute
  // (trial/results/20261022_v3_human_chrome/amap-quota-vs-qps-1.txt:2 against :3).  A hop that far is a
  // planning fact the traveller can act on -- they can move the stop or take the bus -- so it is not
  // folded into the generic "no walking route" sentence.
  AMAP_OUT_OF_PROVIDER_RANGE: "这一段超出地图服务能规划的范围，公共交通也没给出路线；把这一站挪近一点或换成坐车，就能核实。",
};

const HOP_REFUSAL_FALLBACK = "地图服务没有回答这一段。";

export function hopSentences(unanswered: RouteHopRow[], limit = 3): string[] {
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

export function unansweredHopSentences(edges: RouteHopRow[], limit = 3): string[] {
  return hopSentences((edges || []).filter((row) => row && row.status === "ROUTE_UNAVAILABLE"), limit);
}

// Why a plan that saved fine still cannot be chosen, said in the traveller's words, with the door that
// actually fixes it.
//
// The departure gate answers with codes and internal place ids -- it appends
// `INSUFFICIENT_TRAVEL_GAP:<origin>|<destination>` (backend/app/replanning/feasibility.py:1013) -- and the
// plan screen translated any 422 into 「这些地点暂时排不成可用方案。回到探索补充或更换地点。」 That sentence
// sends a person to the exploration list when the thing to change is the gap between two of their own
// rows: measured on walk-84, the refusal was 赶路时间不够 (:73) and the screen said 换地点 (:74), and the
// traveller had nothing left to press.
const INFEASIBLE_SENTENCES: Record<string, string> = {
  INSUFFICIENT_TRAVEL_GAP: "两段安排之间留的赶路时间不够",
  MOBILITY_DATA_UNAVAILABLE: "有一段路还没有可用的实测资料",
  MOBILITY_DATA_INVALID: "有一段路的实测资料对不上",
};

// The gate writes a place id after the colon (`PLACE_CLOSED:<place_id>`,
// backend/app/replanning/feasibility.py:872), and PLACE_CLOSED means this row's own time falls outside the
// hours that place answers with -- not that the place is gone.  Showing the traveller the code named nothing
// they could act on (measured on walk-94, where the screen read 「这版方案排不下（PLACE_CLOSED）。」 while the
// refusal was about 八达岭长城), so the id is joined to the title already on this same screen.
const PLACE_ROW_REASONS: Record<string, { said: string; unnamed: string; fix: string }> = {
  PLACE_CLOSED: {
    said: "在你排的这段时间不开放",
    unnamed: "有一处安排在你排的这段时间不开放",
    fix: "把这一项挪到它的开放时间，或在探索里换一个地点，再按一次「选用这份方案」。",
  },
};

export function infeasibleAtDepartureSentence(failures: unknown, titleOf?: (placeId: string) => string | null): string {
  const rows = Array.isArray(failures) ? failures.map((row) => String(row)) : [];
  // No rows means the envelope did not carry the gate's list, and this screen will not guess at a cause
  // it was not given: an empty answer tells the caller to keep its own generic sentence.
  if (!rows.length) return "";
  const counts = new Map<string, number>();
  const placeLabels = new Map<string, string[]>();
  const others: string[] = [];
  for (const row of rows) {
    const [code, id] = row.split(":");
    if (INFEASIBLE_SENTENCES[code]) counts.set(code, (counts.get(code) ?? 0) + 1);
    else if (PLACE_ROW_REASONS[code]) {
      const title = (id && titleOf?.(id)) || "";
      const label = title ? `${title}${PLACE_ROW_REASONS[code].said}` : PLACE_ROW_REASONS[code].unnamed;
      const list = placeLabels.get(code) ?? [];
      if (!list.includes(label)) list.push(label);
      placeLabels.set(code, list);
    }
    else if (!others.includes(code)) others.push(code);
  }
  const named = [...counts].map(([code, count]) => `${INFEASIBLE_SENTENCES[code]}（${count} 段）`);
  for (const [code, labels] of placeLabels) {
    named.push(labels.slice(0, 3).join("；") + (labels.length > 3 ? `；另有 ${labels.length - 3} 处同样` : ""));
    void code;
  }
  const head = named.length
    ? `这版方案排不下：${named.join("；")}。`
    : `这版方案排不下（${others.join("、")}）。`;
  // Both doors can be refused in one answer, and each is fixed at a different place; naming two causes and
  // then pointing at one of them leaves the traveller to guess which half the sentence was about.
  const fixes: string[] = [];
  if (counts.has("INSUFFICIENT_TRAVEL_GAP")) {
    fixes.push("在出发待办里把后一项的开始时间挪晚，或把前一项的结束时间挪早，再按一次「选用这份方案」。");
  }
  if (placeLabels.get("PLACE_CLOSED")) {
    fixes.push(PLACE_ROW_REASONS.PLACE_CLOSED.fix);
  }
  const tail = named.length && others.length ? `另有 ${others.length} 类原因：${others.join("、")}。` : "";
  return head + fixes.join("") + tail;
}

// Facts the traveller has already decided themselves are not things a plan still 还缺.
//
// Why this exists: the traveller can press 「票价没有来源，我接受先不计入预算」 on the departure card, the
// server records it on the plan (backend/app/agent/goal_price_consent.py:143) and its own selection rule
// honours it (backend/app/services.py:771), yet the plan screen went on listing 票价 among
// 「这版方案还缺：…」 -- measured on walk-80, walk-82 and walk-83, where the workbench line still read
// 「费用待确认 … 这版方案还缺：票价」 while the card above it had already said 按你的确认保存.  The screen was
// asking the traveller to undo a decision they had just made.
//
// Nothing here decides whether the plan can be chosen.  The list loses only the kind the traveller
// settled; every other gap stays, and the button remains the server's to give.
export function priceConsentGiven(explanation?: Record<string, unknown> | null): boolean {
  return String((explanation ?? {}).authority_state || "") === "COST_UNKNOWN_ACCEPTED";
}

export function unsettledFactRows(rows: GapRow[], explanation?: Record<string, unknown> | null): GapRow[] {
  if (!priceConsentGiven(explanation)) return rows;
  return rows.filter((row) => String(row.kind || "") !== "ADMISSION_PRICE");
}

export function priceConsentNote(explanation?: Record<string, unknown> | null): string {
  if (!priceConsentGiven(explanation)) return "";
  const summary = (explanation ?? {}).cost_summary;
  const count = summary && typeof summary === "object"
    ? Number((summary as Record<string, unknown>).unknown_item_count) : Number.NaN;
  return Number.isFinite(count) && count > 0
    ? `票价这一项你已经确认先不计入预算（${count} 处没有来源）。`
    : "票价这一项你已经确认先不计入预算。";
}

// Which of the four time rules refused this save, in the traveller's words, with the row named.
//
// Why this exists: the door checked four conditions and answered with one code
// (backend/app/agent/goal_preparation.py:194 attaches the rule and the row now), and the card's own
// branch for that code looked at `error.message`, which the client fills with "CityNexus API 422:
// /journeys/…" (frontend/src/api/citynexus.ts:2838) -- so the branch could never fire and every
// refusal came out as 「这次未能保存，时间仍留在这里，可以重试。」 Measured on walk-77, where the row that
// actually broke was the seventh: trial/results/20261022_v3_human_chrome/walk-77-log.txt:33 against
// trial/results/20261022_v3_human_chrome/walk-77-window-readback-1.txt:11.
export type ScheduleRefusalRow = {
  rule?: string; sequence_no?: number; title?: string; date?: string;
  start_time?: string; end_time?: string; previous_end_time?: string | null;
};

const SCHEDULE_RULE_SENTENCES: Record<string, string> = {
  end_not_after_start: "结束时间不晚于开始时间",
  overlaps_previous_item: "开始时间排在上一项结束之前",
  before_journey_start: "开始时间早于这趟旅行的开始",
  after_journey_end: "结束时间超出了这趟旅行的结束",
};

export function scheduleRefusalSentence(row: ScheduleRefusalRow | null | undefined): string {
  if (!row || typeof row.sequence_no !== "number") return "";
  const title = String(row.title || "").trim();
  const what = SCHEDULE_RULE_SENTENCES[String(row.rule || "")] || "这一项的时间对不上这趟行程";
  const span = row.start_time && row.end_time ? ` ${row.start_time}–${row.end_time}` : "";
  // Only the overlap rule is about the row before this one.  walk-85 measured the other kind
  // (details.rule="after_journey_end", trial/results/20261022_v3_human_chrome/walk-85-log.txt:36) coming
  // out with 「上一项到 20:00 才结束」 attached, which pointed at a row that had done nothing wrong.
  const after = row.rule === "overlaps_previous_item" && row.previous_end_time
    ? `（上一项到 ${row.previous_end_time} 才结束）` : "";
  return `第 ${row.sequence_no} 项${title ? `「${title}」` : ""}${span}：${what}${after}。改这一项的时间再保存，其余不用动。`;
}

// Reading one verified transfer the way a traveller reads it.
//
// Why this exists: the drawer on walk-80 listed 「八达岭长城 → 颐和园 · 步行 · 52185 米 · 41748 秒」
// (trial/results/20261022_v3_human_chrome/walk-80-log.txt:61).  Both numbers are what the provider
// returned, and neither is usable: nobody pictures 41748 seconds, and a 52 km hop printed under the
// word 步行 is the sentence that makes a first-time user close the app.  The raw values stay in the
// row (and in the title attribute, so the reading can still be checked against them); only the
// wording a person sees changes here.
export function humanDistance(meters: number | undefined | null): string {
  if (typeof meters !== "number" || !Number.isFinite(meters) || meters < 0) return "";
  if (meters < 1000) return `${Math.round(meters)} 米`;
  return `${(meters / 1000).toFixed(1)} 公里`;
}

export function humanDuration(seconds: number | undefined | null): string {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "";
  const minutes = Math.round(seconds / 60);
  if (minutes < 1) return "不到 1 分钟";
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `约 ${minutes} 分钟`;
  return rest ? `约 ${hours} 小时 ${rest} 分` : `约 ${hours} 小时`;
}

// Which AMap deep link a row is allowed to carry.
//
// Why the mode is part of the check: the freeze door writes the transport it actually measured into
// the link (backend/app/agent/goal_route_freeze.py:309 builds mode=walk for a walking row and mode=bus
// for a transit one), while the drawer used to require mode=walk for every row
// (WorkspaceActions.tsx:161 as committed in 4dedfb2f, before this change).  So a transit answer was
// dropped from the list as an unsafe link: walk-80 read 「1 段按公共交通核实」 in the band and
// TRANSIT_LABELED=0 in the drawer it opens right after (trial/results/20261022_v3_human_chrome/walk-80-log.txt:39
// against :62).  The traveller was told a segment was verified by bus and then shown five walks.
const AMAP_NAVIGATION_PREFIX = "https://uri.amap.com/navigation?";
const AMAP_LINK_MODES: Record<string, string> = { WALK: "walk", TRANSIT: "bus" };

export function isSafeAmapNavigationUrl(value: string | undefined | null, mode?: string | null): boolean {
  if (typeof value !== "string" || !value.startsWith(AMAP_NAVIGATION_PREFIX)) return false;
  // A row written before the freeze door recorded a mode is a walking row -- the same reading the
  // panel uses (goal_route_freeze.py puts WALK on the row when the walking door answered).
  const expected = AMAP_LINK_MODES[String(mode || "WALK")];
  if (!expected) return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "uri.amap.com" && url.pathname === "/navigation"
      && !url.username && !url.password && url.searchParams.get("mode") === expected
      && url.searchParams.get("coordinate") === "gaode";
  } catch { return false; }
}

// The hop the measured minutes do not fit, and the one action that follows from saying so.
//
// The departure gate already refuses 「两段安排之间留的赶路时间不够」 (app/replanning/feasibility.py:1013)
// and left the traveller a sentence with nothing to press.  These rows come from the plan's own frozen
// facts read through backend/app/agent/goal_travel_gaps.py, so the minutes quoted here are the same
// minutes the gate will hold the plan to -- not an estimate made in the browser.
export type GapHopRow = {
  origin_title: string; destination_title: string;
  planned_gap_minutes: number | null; required_minutes: number | null;
  short_by_minutes: number; spans_night: boolean; reason_code?: string | null;
};

export type GapPlanRow = {
  title: string; planned_start: string; planned_end: string;
  proposed_start: string; proposed_end: string; extra_minutes: number; direct_cause: boolean;
};

export const REPLAN_BUTTON = "根据路线重新安排";
export const REPLAN_APPLY_BUTTON = "按这一版安排";

export function gapShortfallSentence(hop: GapHopRow): string {
  const from = hop.origin_title || "上一处";
  const to = hop.destination_title || "下一处";
  if (hop.planned_gap_minutes === null || hop.required_minutes === null) {
    return `${from} → ${to}：这一转量到了时间，但那两处的钟点读不出来。`;
  }
  return `${from} → ${to}：这一段路上要 ${hop.required_minutes} 分钟，中间只留了 ${hop.planned_gap_minutes} 分钟。`;
}

export function replanDiffSentence(row: GapPlanRow): string {
  const cause = row.direct_cause ? "因为上一转" : "跟着顺移";
  return `${row.title}：${row.planned_start}–${row.planned_end} 改成 ${row.proposed_start}–${row.proposed_end}，`
    + `往后 ${row.extra_minutes} 分钟（${cause}）。`;
}

const REPLAN_REFUSAL_SENTENCES: Record<string, string> = {
  "DAY_WOULD_RUN_PAST_22:00": "往后挪就要排到晚上十点之后，这一天放不下更多时间；要改的是这天排几处，不是钟点。",
  OVERNIGHT_HOP_NEEDS_DECISION: "跨夜的这一转，把晚上推后也接不上；要先定这一晚在哪结束。",
  SCHEDULE_ALIGNMENT_UNVERIFIED: "这一版的行序和保存的时间对不上，先刷新任务再试。",
};

export function replanRefusalSentence(reason: string | null | undefined): string | null {
  return REPLAN_REFUSAL_SENTENCES[String(reason || "")] ?? null;
}

export function replanAppliedSentence(count: number): string {
  return `已按路线把 ${count} 处往后排，这是一份新的候选方案；生效的那一份没有变。`;
}

export const REPLAN_NEEDS_FREEZE_SENTENCE = "新的一版还没有核实转场；先选用这一版，再核实并冻结转场。";
