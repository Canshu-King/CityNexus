/**
 * ORD-0445 -- copy for the 待规划 screen.
 *
 * Its own file for the same reason ORD-0386 and ORD-0402 wrote theirs: `i18n/LocaleContext.tsx` is
 * the shared dictionary several lanes edit on one night, and a new screen must not become a merge
 * conflict there. `useLocale()` is still what decides the language -- only the strings live here.
 *
 * Four rules this file keeps:
 *  - 待规划 is a *state of the data*, named as one: 这台服务器说这些地点属于这一程，但没有排在任何一天.
 *    It is not "暂无数据", and it never asks the traveller to guess whether something was lost.
 *  - The verb pair stays the one already pinned: 找回 / 还原. 恢复 is not used anywhere -- it already
 *    means autonomous recovery here (`recovery.*`, `POST /journeys/{id}/recovery/acknowledge`), and
 *    还原 belongs to the plan-version screen (`features/studio/planVersionHistoryCopy.ts:10`).
 *  - No sentence promises a door this build does not have. There is no write that puts a place on a
 *    day (`backend/app/main.py:6798`, `:6803`, `:6808` only move an activity through execution), so
 *    the screen says that plainly instead of showing a button for it (ORD-0385).
 *  - Chinese is the shorter arm on purpose: no filler like 哦/哟, and one clause per fact.
 */
export const pendingSetCopy = {
  en: {
    "pending.title": "Not on a day yet",
    "pending.sub": "Captured places not yet assigned to a day.",
    "pending.loading": "Reading the pending set…",
    "pending.count": "{n} places not on a day",
    "pending.shown": "{m} of {n} shown",
    "pending.noDay": "no day of this trip holds it",
    "pending.capturedOn": "captured on {day}",
    "pending.deleteDayRule": "Places removed from a day remain here.",
    "pending.noPlaceDoor": "Day assignment is not available from this screen.",
    "pending.filter": "Filter",
    "pending.filter.all": "All",
    "pending.filter.allSub": "every pending place",
    "pending.filter.reset": "Reset",
    "pending.filter.done": "Done",
    "pending.filter.sheetTitle": "Filter the pending places",
    "pending.rowCategoryMissing": "this server gave no category for this row",
    "pending.noPlan": "Choose a plan to see places without a day.",
    "pending.empty": "No place is waiting for a day on this trip.",
    "pending.filterEmpty": "No place in this filter. There are still {n} in All.",
    "pending.empty.next": "To add one, capture places for this trip.",
    "pending.empty.action": "Open City Discovery",
    "pending.reread": "Read it again",
    "pending.candidatesAbsent": "The server returned no pending places.",
    "pending.setUnknown": "Pending place count unavailable.",
    "pending.placesAbsent": "Categories unavailable; all places remain under All.",
    "pending.details": "Technical details",
    "pending.reads": "What this device read",
    "pending.activities": "activities read",
    "pending.candidates": "captured places read",
    "pending.placesRows": "places read",
    "pending.notAnswered": "not answered",
    "pending.placed": "places a day already holds",
    "pending.candidatesPlaced": "captures a day already holds",
    "pending.stateMissing": "this server gave no state for this row",
  },
  "zh-CN": {
    "pending.title": "待规划",
    "pending.sub": "已捕获、尚未排入日期的地点。",
    "pending.loading": "正在读待规划集合…",
    "pending.count": "{n} 个地点没有排在某一天",
    "pending.shown": "筛出 {m} / 共 {n}",
    "pending.noDay": "这一程没有任何一天排它",
    "pending.capturedOn": "捕获于 {day}",
    "pending.deleteDayRule": "从日期移除的地点会留在这里。",
    "pending.noPlaceDoor": "日期安排请前往行程计划。",
    "pending.filter": "筛选",
    "pending.filter.all": "全部",
    "pending.filter.allSub": "全部待规划地点",
    "pending.filter.reset": "重置",
    "pending.filter.done": "完成",
    "pending.filter.sheetTitle": "筛选待规划地点",
    "pending.rowCategoryMissing": "服务器没给这一行的类别",
    "pending.noPlan": "选择方案后可查看未排日期的地点。",
    "pending.empty": "这一程没有待规划的地点。",
    "pending.filterEmpty": "这个筛选里现在没有地点，「全部」下还有 {n} 个。",
    "pending.empty.next": "想收进新的地点，去城市探索捕获这一程的地点。",
    "pending.empty.action": "去城市探索",
    "pending.reread": "再读一次",
    "pending.candidatesAbsent": "服务器没有返回待规划地点。",
    "pending.setUnknown": "待规划地点数量暂不可用。",
    "pending.placesAbsent": "地点类别暂不可用，全部地点仍列在「全部」下。",
    "pending.details": "技术详情",
    "pending.reads": "这台设备读到的",
    "pending.activities": "已读活动",
    "pending.candidates": "已读捕获地点",
    "pending.placesRows": "已读地点",
    "pending.notAnswered": "未答出",
    "pending.placed": "已有某天猫住",
    "pending.candidatesPlaced": "已被某天排上的捕获",
    "pending.stateMissing": "服务器没给这一行的状态",
  },
} as const;

export type PendingSetCopyKey = keyof (typeof pendingSetCopy)["zh-CN"];

/** Same fallback rule as the other lane copy modules: a key missing in one language must never
 *  reach the traveller as a raw key. */
export function pendingCopy(locale: string, key: PendingSetCopyKey): string {
  const table = pendingSetCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? pendingSetCopy.en[key] ?? key;
}

/** `{n}` and `{day}` come from a read, never from a number this file knows. */
export function fillPending(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
