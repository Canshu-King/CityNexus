// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const nav = {
  en: {
  // ── Navigation labels ──
  "nav.hub": "Today",
  "nav.studio": "Trip Studio",
  "nav.stay": "Stay Explorer",
  "nav.discover": "City Discovery",
  "nav.live": "Live Journey",
  "nav.bookings": "Travel Wallet",
  "nav.intelligence": "Intelligence",
  "nav.twin": "Traveler Twin",
  "nav.agent": "Copilot",
  "nav.authoritative": "Recovery",
  "nav.map": "Map",
  "nav.import": "Import places",
  "nav.me": "Me",
  "nav.language": "中文",
  "nav.trips": "Trips",
  /* ORD-0402 slice 2: the recycle bin nav label. The screen owns its own copy in
     `features/trash/journeyTrashCopy.ts`; this pair has to live in the shared dictionary only
     because the nav strip looks labels up as t("nav." + key) with no fallback
     (app/V8Experience.tsx). */
  "nav.trash": "Recycle bin",
  "nav.access": "Members and access",
  /* ORD-0476 slice 2 -- the footprint screen, in one contiguous run so this hot file takes a single
     block from this order instead of scattered lines. Every word the screen and the per-stop 打卡
     control shows is here; nothing is written in a component. */
  "nav.footprints": "Footprints",
  // Drawer group headings; the en values are the words already on screen, so the English arm cannot move.
  "nav.groupToday": "TODAY",
  "nav.groupPlan": "PLAN",
  "nav.groupTravel": "TRAVEL",
  "nav.groupSystem": "SYSTEM",
  "nav.groupOther": "MORE",
  },
  zh: {
  // ── 导航标签 ──
  "nav.hub": "今天",
  "nav.studio": "行程工作台",
  "nav.stay": "住宿选择",
  "nav.discover": "城市探索",
  "nav.live": "实时行程",
  "nav.bookings": "旅行票夹",
  "nav.intelligence": "智能守护",
  "nav.twin": "旅行者画像",
  "nav.agent": "Copilot",
  "nav.authoritative": "恢复与执行",
  "nav.map": "地图",
  "nav.import": "导入地点",
  "nav.me": "我的",
  "nav.language": "EN",
  "nav.trips": "行程",
  "nav.trash": "回收站",
  "nav.access": "成员与权限",
  /* ORD-0476 第二切片 —— 足迹屏的中文臂，同样集中成一段连续插入。 */
  "nav.footprints": "足迹",
  "nav.groupToday": "今日",
  "nav.groupPlan": "规划",
  "nav.groupTravel": "出行",
  "nav.groupSystem": "系统",
  "nav.groupOther": "更多",
  },
};
