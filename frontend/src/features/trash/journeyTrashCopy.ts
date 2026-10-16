/**
 * ORD-0402 slice 2 -- copy for the recycle-bin screen.
 *
 * Deliberately NOT in `i18n/LocaleContext.tsx`: that file is the shared dictionary other lanes edit
 * on the same night (the ORD-0386 screen made the same choice for the same reason, see
 * `features/studio/planVersionHistoryCopy.ts`). Only `nav.trash` went into the shared dictionary,
 * because the nav strip builds its labels as `t("nav." + key)` and has no fallback hook.
 *
 * Three wording rules, all of them from the order:
 *  - the verb is 找回 / "bring it back". 恢复 and `recover*` are autonomous recovery in this product
 *    (`recovery.*` keys, `POST /journeys/{id}/recovery/acknowledge`), and 还原 is the plan-version
 *    screen's word (`planVersionHistoryCopy.ts:10`). The server picked the same pair
 *    (`backend/app/main.py` -- "The word is 找回 / undelete").
 *  - a refusal is *said*, not printed as a code. The 409 `JOURNEY_NOT_DELETED` gets the sentence
 *    "这条已经在你的行程列表里了。"; the machine token stays on the details face where a screen can
 *    quote it without the traveller having to read a code to know what happened.
 *  - nothing here offers a second action on a deleted trip. There is no permanent-delete route on
 *    this server, so no sentence may imply one (ORD-0385: copy may not exceed the mechanism).
 */
export const journeyTrashCopy = {
  en: {
    "trash.title": "Recycle bin",
    "trash.sub": "Deleted trips you can restore.",
    "trash.loading": "Reading the bin…",
    "trash.empty": "The bin is empty.",
    "trash.count": "{n} trips in the bin",
    "trash.rowState": "in the bin",
    "trash.rowStateMissing": "status unavailable",
    "trash.deletedAt": "put in the bin at {when}",
    "trash.deletedAtMissing": "time unavailable",
    "trash.action": "Bring it back",
    "trash.busy": "Bringing it back…",
    "trash.found": "Brought back: {title}. It is in your trip list again.",
    "trash.already": "This trip is already in your list.",
    "trash.gone": "This trip is no longer available.",
    "trash.refused": "Could not restore this trip. Refresh to check its status.",
    "trash.transport": "Recycle bin unavailable.",
    "trash.doorAbsent": "Could not load deleted trips.",
    "trash.refresh": "Read the bin again",
  },
  "zh-CN": {
    "trash.title": "回收站",
    "trash.sub": "已删除、可找回的行程。",
    "trash.loading": "正在读回收站…",
    "trash.empty": "回收站为空。",
    "trash.count": "回收站里有 {n} 条行程",
    "trash.rowState": "在回收站里",
    "trash.rowStateMissing": "状态暂不可用",
    "trash.deletedAt": "丢弃于 {when}",
    "trash.deletedAtMissing": "时间暂不可用",
    "trash.action": "找回",
    "trash.busy": "正在找回…",
    "trash.found": "已找回：{title}。它回到你的行程列表里了。",
    "trash.already": "这条行程已在列表中。",
    "trash.gone": "这条行程已不可用。",
    "trash.refused": "无法找回这条行程，请刷新确认状态。",
    "trash.transport": "回收站暂不可用。",
    "trash.doorAbsent": "无法读取已删除的行程。",
    "trash.refresh": "再读一次回收站",
  },
} as const;

export type JourneyTrashCopyKey = keyof (typeof journeyTrashCopy)["zh-CN"];

/** Same fallback rule as every other lane copy module: a key missing in one language must never
 *  reach the traveller as a raw key. */
export function trashCopy(locale: string, key: JourneyTrashCopyKey): string {
  const table = journeyTrashCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? journeyTrashCopy.en[key] ?? key;
}

/** `{n}` and `{title}` come from the read and the response, never from a number this file knows. */
export function fillTrash(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
