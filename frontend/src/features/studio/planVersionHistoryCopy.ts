/**
 * ORD-0386: copy for the plan-version history screen.
 *
 * Deliberately NOT in `i18n/LocaleContext.tsx`: two other lanes are editing that file tonight and
 * the commander ruled the shared dictionary off-limits for this order, so a same-key collision
 * cannot silently take the last value. This file is therefore read directly, per locale, through
 * `historyCopy()` below -- `useT()` cannot reach these keys, because `LocaleContext.tsx:1635`
 * looks keys up in its own two dictionaries only and has no fallback-dictionary parameter.
 *
 * Wording rule from the order: this screen says 「历史版本 / 还原」. The word 恢复 already means
 * autonomous recovery in this product (`recovery.*` keys), and a third meaning for it on a list of
 * old plans is exactly how "who decided to change my trip" gets re-litigated.
 */
/**
 * Each label names only what the source code actually proves. The server writes exactly three
 * values (`backend/app/schemas.py:495`) from six places, and `MANUAL` is the one that is easy to
 * over-claim: `main.py:5721` writes it when a traveller re-orders activities in the trip studio
 * (`product_path = V12_TRIP_STUDIO_ACCEPT`), and `operations/v9.py:580` writes it for a stay-driven
 * rewrite. So it says 人工改动 and names both, rather than claiming one of them.
 */
export const planVersionHistoryCopy = {
  en: {
    "history.title": "Plan versions on this trip",
    "history.sub": "Plan versions, ordered by creation time.",
    "history.version": "Version",
    "history.sourceInitial": "first generation",
    "history.sourceReplan": "from a replan",
    "history.sourceManual": "from a manual change (activity order or stay)",
    "history.sourceUnknown": "source as this server wrote it: {code}",
    "history.current": "the trip runs this one",
    "history.parent": "from version",
    "history.noParent": "no parent version",
    "history.createdMissing": "no write time recorded",
    "history.retention": "{n} versions listed",
    "history.count": "{n} versions listed",
    "history.noRestore": "Restore is unavailable here.",
    "history.empty": "This trip has no plan version yet.",
    "history.loading": "Reading the version list…",
    "history.failed": "Could not load plan versions.",
  },
  "zh-CN": {
    "history.title": "这趟行程的方案版本",
    "history.sub": "按创建时间排列的方案版本。",
    "history.version": "版本",
    "history.sourceInitial": "首次生成",
    "history.sourceReplan": "来自一次重规划",
    "history.sourceManual": "来自一次人工改动（调整活动顺序或换住宿）",
    "history.sourceUnknown": "这台服务器写的来源：{code}",
    "history.current": "行程正在跑这一份",
    "history.parent": "源自版本",
    "history.noParent": "没有父版本",
    "history.createdMissing": "没有记录写入时间",
    /* "no cap" is a structural reading, not an extrapolation: nothing in the backend prunes a kept
       version (`grep -riE 'retention|prune|max_versions' backend/app` -> no hits), and the only
       DELETEs that touch plan versions remove a *proposal the hard gate refused before it was ever
       returned* (`backend/app/main.py:9787`, `backend/app/operations/v9.py:733`). Measured against
       real writes: 7 generate rounds left 21 rows, version_no 1..21 with no hole
       (backend/tests/test_qoder_ord0386_plan_version_history.py, test_3). */
    "history.retention": "共列出 {n} 份版本。",
    "history.count": "共列出 {n} 份版本",
    "history.noRestore": "版本还原入口暂不可用。",
    "history.empty": "这趟行程还没有方案版本。",
    "history.loading": "正在读版本列表…",
    "history.failed": "无法读取方案版本。",
  },
} as const;

export type PlanVersionCopyKey = keyof (typeof planVersionHistoryCopy)["zh-CN"];

/** Pick this screen's wording for the traveller's locale, falling back to English the same way
 *  LocaleContext does -- so a key that exists in one language can never render as a raw key. */
export function historyCopy(locale: string, key: PlanVersionCopyKey): string {
  const table = planVersionHistoryCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? planVersionHistoryCopy.en[key] ?? key;
}

/** `{n}` is the only placeholder these strings carry, and the count always comes from the same
 *  read that produced the list -- never from a number this file knows. */
export function fillHistory(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
