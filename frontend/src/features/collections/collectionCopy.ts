/**
 * ORD-0444 -- copy for the collection shelf.
 *
 * Deliberately NOT in `i18n/LocaleContext.tsx`: that file is the shared dictionary other lanes edit
 * on the same night, and this order may not open it. The precedent is the two neighbours this
 * screen sits beside -- `features/trash/journeyTrashCopy.ts` and
 * `features/studio/planVersionHistoryCopy.ts`, each of which carries its own zh and en arms.
 *
 * One consequence is worth stating because it decides where the panel mounts: the nav strip builds
 * its labels as `t("nav." + item.key)` (`frontend/src/app/V8Experience.tsx:1731`) and `t()` falls
 * back to the **key itself** when a dictionary has no entry
 * (`frontend/src/i18n/LocaleContext.tsx:1825` -- `dictionaries.en[key] ?? key`). So adding a route
 * key to `routes/v8Routes.ts` would put the literal text `nav.collections` in the sidebar. The
 * shelf therefore mounts on the existing 城市探索 route through `app/v8PanelRegistry.tsx`, and no
 * new nav label is invented here.
 *
 * Four wording rules this file holds itself to:
 *  - 「我的收藏」 is the name of this *screen*, not a claim about whose shelf a row is. The container
 *    has no owner column (`backend/db/schema.sql:1054`), and `GET /api/v1/collections` is
 *    unscoped, so no sentence here may say 我的私有 / "only you can see these".
 *  - the empty state carries an action. 「暂无数据」 is not shipped: a traveller who is told a
 *    container is empty and given nothing to press is at a dead end, which is the failure mode
 *    F23's 「完成」-beside-「新建」 pairing exists to prevent.
 *  - a refusal is said, not printed as a code. `COLLECTION_FOLDER_NOT_FOUND`, `PLACE_NOT_FOUND` and
 *    `PLACE_ALREADY_IN_COLLECTION` each get a sentence; the token stays on the details face.
 *  - the shelf row shows name, city code and coordinate, and shows no 「地址」 label. The competitor's
 *    row has one (F23: 封面 + 名称 + 地址 + 备注), and this server cannot fill that cell: `places`
 *    has no address column among its 14, and its `metadata_json` carries `cost_minor`,
 *    `duration_min` and `accessibility_evidence` and nothing address-shaped. A label over nothing
 *    is a lie with better typography.
 */
export const collectionCopy = {
  en: {
    "collections.title": "My collections",
    "collections.sub":
      "Shelves this server reports, each with the places it says are on it. Nothing here is saved on this device.",
    "collections.loading": "Reading the shelves…",
    "collections.empty":
      "Nothing is collected yet. Pick a place in City Discovery above, or start a shelf here and add to it later.",
    "collections.emptyAction": "Start a shelf",
    "collections.emptyActionBusy": "Starting a shelf…",
    "collections.emptyDefaultName": "Default list",
    "collections.emptyFolder": "This shelf holds no place yet.",
    "collections.created": "Started: {name}. The server read it back with no places on it.",
    "collections.shelfCount": "{n} shelves on this server",
    "collections.folderCount": "{name} · {n} places",
    "collections.rowCount": "{n} places on this shelf",
    "collections.countMissing": "this server gave no count for this shelf",
    "collections.note": "Note: {note}",
    "collections.noNote": "No note was written for this place",
    "collections.coordinate": "{lat}, {lng} ({crs})",
    "collections.addressAbsent": "no address on this server for this place",
    "collections.provider": "from {provider}",
    "collections.readFailed":
      "The shelves could not be read from this server. Nothing about your collections changed because of this screen.",
    "collections.doorAbsent":
      "This server did not answer the shelf list, so no row can be shown yet. Nothing was changed.",
    "collections.refused": "The server refused this attempt. Your shelves are unchanged.",
    "collections.refusedDuplicate": "That place is already on this shelf, so nothing was added.",
    "collections.refusedFolder": "This server does not hold that shelf, so nothing was added to it.",
    "collections.refusedPlace":
      "This server does not hold that place any more, so it cannot be put on a shelf.",
    "collections.codeAbsent": "this server gave no name for the refusal",
    "collections.refresh": "Read the shelves again",
    "collections.busy": "Starting…",
  },
  "zh-CN": {
    "collections.title": "我的收藏",
    "collections.sub": "这台服务器报出的收藏夹，以及它说每个夹里放着哪些地点。这一屏没有在设备上存任何东西。",
    "collections.loading": "正在读收藏夹…",
    "collections.empty": "还没有收藏。可以在上面的「城市探索」里挑一枚地点，或者先在这儿建一个收藏夹，之后再往里放。",
    "collections.emptyAction": "建一个收藏夹",
    "collections.emptyActionBusy": "正在建收藏夹…",
    "collections.emptyDefaultName": "默认收藏夹",
    "collections.emptyFolder": "这个夹里还没有地点。",
    "collections.created": "已建好：{name}。这台服务器把它读回来了，里面还没有地点。",
    "collections.shelfCount": "这台服务器上有 {n} 个收藏夹",
    "collections.folderCount": "{name} · {n} 个地点",
    "collections.rowCount": "这一夹里有 {n} 个地点",
    "collections.countMissing": "服务器没有给出这一夹的条目数",
    "collections.note": "备注：{note}",
    "collections.noNote": "这个地点没有写备注",
    "collections.coordinate": "{lat}, {lng}（{crs}）",
    "collections.addressAbsent": "这台服务器没有这个地点的地址",
    "collections.provider": "来自 {provider}",
    "collections.readFailed": "收藏夹没有从这台服务器读到。这一屏没有改动你的任何收藏。",
    "collections.doorAbsent": "这台服务器没有答出收藏夹列表，所以现在一行都显示不出来。没有任何东西被改动。",
    "collections.refused": "服务器拒绝了这次操作。你的收藏夹没有变化。",
    "collections.refusedDuplicate": "这个地点已经在这个收藏夹里了，没有重复加入。",
    "collections.refusedFolder": "这台服务器上没有这个收藏夹，所以没有往它里面加东西。",
    "collections.refusedPlace": "这台服务器已经没有这个地点了，所以它加不进收藏夹。",
    "collections.codeAbsent": "服务器没有给出拒绝的原因名",
    "collections.refresh": "再读一次收藏夹",
    "collections.busy": "正在建…",
  },
} as const;

export type CollectionCopyKey = keyof (typeof collectionCopy)["zh-CN"];

/** Same fallback rule as every other lane copy module: a key missing in one language must never
 *  reach the traveller as a raw key. */
export function copyForLocale(locale: string, key: CollectionCopyKey): string {
  const table = collectionCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? collectionCopy.en[key] ?? key;
}

/** `{n}`, `{name}`, `{note}` and the rest come from the read and the response, never from a number
 *  or a title this file knows. */
export function fill(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
