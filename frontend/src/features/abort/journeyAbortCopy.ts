/**
 * ORD-0464: copy for the reason survey that sits in front of binning a trip.
 *
 * Own file, not `i18n/LocaleContext.tsx`.  The eight reason sentences are the traveller-facing half
 * of the vocabulary declared in `contracts/openapi.yaml` (`JourneyAbortCode`); the machine token never
 * reaches the line -- the checkbox carries it in `data-cnx-code` for the gate, and the label is the
 * sentence below.
 *
 * The button wording follows the one thing the reference survey gets right (剖析件 §1.7): the control
 * that finishes the flow keeps naming the real action.  Nothing here says "提交" / "确认"; both exits
 * say 丢进回收站, because a traveller who pressed it and then found the trip in the bin was told the
 * truth on the button.
 */

export const ABORT_REASON_KEYS = {
  ITINERARY_NOT_USEFUL: "abort.code.itineraryNotUseful",
  BUDGET_DOES_NOT_FIT: "abort.code.budgetDoesNotFit",
  DATES_OR_PLACE_CHANGED: "abort.code.datesOrPlaceChanged",
  EVIDENCE_UNAVAILABLE: "abort.code.evidenceUnavailable",
  PROTECTED_ITEM_DROPPED: "abort.code.protectedItemDropped",
  ARRANGED_ELSEWHERE: "abort.code.arrangedElsewhere",
  TEST_OR_DEMO_DATA: "abort.code.testOrDemoData",
  OTHER: "abort.code.other",
} as const;

/** The refusal names this server answers with, mapped to a sentence.  `abort_answer_without_codes`
 *  and `abort_skip_with_codes` are this door's two contradictions; `literal_error`,
 *  `string_too_long` and `extra_forbidden` come from pydantic over the same shape.  Anything not in
 *  this table renders as the generic refusal with the receipt id, not as a guessed cause. */
export const ABORT_REFUSAL_KEYS = {
  abort_answer_without_codes: "abort.refuseWithoutCodes",
  abort_skip_with_codes: "abort.refuseSkipWithCodes",
  literal_error: "abort.refuseNotAnOption",
  string_too_long: "abort.refuseNoteTooLong",
  extra_forbidden: "abort.refuseUnknownField",
} as const;

const zh: Record<string, string> = {
  "abort.open": "把这趟丢进回收站",
  "abort.question": "方便说说为什么不需要这趟了吗？",
  "abort.help": "可以勾好几项，也可以一项都不勾直接跳过。这只帮我们改进，不影响这趟能不能找回。",
  "abort.code.itineraryNotUseful": "安排不合用（活动、顺序或节奏）",
  "abort.code.budgetDoesNotFit": "预算兜不住",
  "abort.code.datesOrPlaceChanged": "日期或目的地变了",
  "abort.code.evidenceUnavailable": "关键信息拿不到（路况、住宿没有可信答案）",
  "abort.code.protectedItemDropped": "被保护的安排被排掉了",
  "abort.code.arrangedElsewhere": "已经用别的方式安排好了",
  "abort.code.testOrDemoData": "这是测试或演示数据",
  "abort.code.other": "其他",
  "abort.noteLabel": "补充说明（可不填，最多 {n} 字）",
  "abort.confirm": "丢进回收站",
  "abort.pickOne": "至少勾一项才能这样丢，或者选下面的「暂不说明」。",
  "abort.skip": "暂不说明，直接丢进回收站",
  "abort.busy": "正在丢进回收站…",
  "abort.doneDeclared": "这趟已经在回收站里。服务器记下的原因是：{codes}。",
  "abort.doneSkipped": "这趟已经在回收站里。当时你选了不说明原因，我们也不会替你编一个。",
  "abort.doneNotAsked": "这趟已经在回收站里。这台服务器没有收到过这个问题，所以也没有原因可记。",
  "abort.doneNoState": "这趟已经在回收站里，但那一条记录没有带原因状态。",
  "abort.findAgain": "在回收站里可以找回。",
  "abort.goTrash": "去回收站",
  "abort.refuseWithoutCodes": "服务器说：选了「愿意说明」却没勾任何一项，所以这一次没有丢。",
  "abort.refuseSkipWithCodes": "服务器说：一边跳过一边给了原因，这两件事不能同时记，所以这一次没有丢。",
  "abort.refuseNotAnOption": "服务器说：勾选项里有一枚不在它认得的范围内，所以这一次没有丢。",
  "abort.refuseNoteTooLong": "服务器说：补充说明超过了它接受的长度，所以这一次没有丢。",
  "abort.refuseUnknownField": "服务器说：请求带了它不认识的内容，所以这一次没有丢。",
  "abort.refused": "这台服务器拒绝了这一次操作，没有给出我们能认的原因。",
  "abort.receipt": "回执 {receipt}",
  "abort.failed": "这台服务器没有收下这趟的丢弃请求，行程还在原来的地方。",
};

const en: Record<string, string> = {
  "abort.open": "Move this trip to the recycle bin",
  "abort.question": "Mind saying why this trip is not needed?",
  "abort.help":
    "Tick as many as apply, or skip it entirely. This only helps us improve it, and it does not affect whether you can bring the trip back.",
  "abort.code.itineraryNotUseful": "The plan did not suit (activities, order or pace)",
  "abort.code.budgetDoesNotFit": "It did not fit the budget",
  "abort.code.datesOrPlaceChanged": "The dates or the destination changed",
  "abort.code.evidenceUnavailable": "Key information was unavailable (no trustworthy transit or stay answers)",
  "abort.code.protectedItemDropped": "Something I protected got pushed out",
  "abort.code.arrangedElsewhere": "I arranged it another way",
  "abort.code.testOrDemoData": "This is test or demo data",
  "abort.code.other": "Something else",
  "abort.noteLabel": "Anything more? (optional, up to {n} characters)",
  "abort.confirm": "Move to recycle bin",
  "abort.pickOne": "Tick at least one reason, or use “skip” below.",
  "abort.skip": "Move it without saying why",
  "abort.busy": "Moving it to the recycle bin…",
  "abort.doneDeclared": "This trip is in the recycle bin. The server holds these reasons: {codes}.",
  "abort.doneSkipped":
    "This trip is in the recycle bin. You chose not to say why, and we will not invent a reason.",
  "abort.doneNotAsked":
    "This trip is in the recycle bin. This server was never asked for a reason, so it holds none.",
  "abort.doneNoState": "This trip is in the recycle bin, but that record carries no reason state.",
  "abort.findAgain": "You can bring it back from the recycle bin.",
  "abort.goTrash": "Open the recycle bin",
  "abort.refuseWithoutCodes":
    "The server said: you agreed to explain but ticked nothing, so this trip was not moved.",
  "abort.refuseSkipWithCodes":
    "The server said: skipping and naming reasons cannot both be recorded, so this trip was not moved.",
  "abort.refuseNotAnOption":
    "The server said: one of the ticks is outside the reasons it knows, so this trip was not moved.",
  "abort.refuseNoteTooLong":
    "The server said: the note is longer than it accepts, so this trip was not moved.",
  "abort.refuseUnknownField":
    "The server said: the request carried something it does not recognise, so this trip was not moved.",
  "abort.refused": "This server refused the request without a reason we can name.",
  "abort.receipt": "Receipt {receipt}",
  "abort.failed": "This server did not accept the request to move the trip; it is still where it was.",
};

export type JourneyAbortCopyKey =
  | keyof typeof ABORT_REASON_KEYS
  | keyof typeof ABORT_REFUSAL_KEYS
  | keyof typeof zh;

export function abortCopy(locale: string, key: JourneyAbortCopyKey): string {
  const table = locale.startsWith("zh") ? zh : en;
  return table[key] ?? en[key] ?? key;
}

export function fillAbort(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in params ? String(params[name]) : whole,
  );
}
