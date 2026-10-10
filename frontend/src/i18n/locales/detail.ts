// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const detail = {
  en: {

  // ── Detail pages & status surfaces ──
  /* I18N_细节补齐: the detail pages and the status lines each kept their own inline
     `zh ? "..." : "..."` arm, so one fact could grow two wordings and neither half was reachable by a
     key lookup. Both halves move here so each fact carries one wording per locale. The values are the
     sentences these screens were already showing, not new copy. The call sites still read their local
     arm; rewiring them is a separate change, so nothing on screen moves in this one. */
  "detail.backToItinerary": "Back to itinerary",
  "detail.duration": "Duration",
  "detail.travelFromPrev": "Travel from previous stop",
  "detail.openingHours": "Opening hours",
  "detail.hoursProvided": "Provided",
  "detail.hoursProviderText": " · provider's own text",
  "detail.hoursNoData": "Not available",
  "detail.category": "Category",
  "detail.activityType": "Activity type",
  "detail.location": "Location",
  "detail.noCoordinates": "No coordinates",
  "detail.showOnMap": "Show on map",
  "detail.askCopilot": "Ask Copilot",
  "detail.nearbyStops": "Other stops nearby",
  "detail.otherTripStops": "Other stops on this trip",
  "detail.nearbyNoteClose": "All within about {n} m, ordered by straight-line distance.",
  "detail.nearbyNoteFar": "These are other stops on the same trip; they are not necessarily within walking distance.",
  "detail.metres": "{n} m",
  "detail.kilometres": "{n} km",
  "detail.confirmedProtected": "Confirmed · protected",
  "detail.viewDetails": "View details",
  "detail.detailsChevron": "Details ›",
  "detail.weekIndex": "Week {n}",
  "detail.dayStops": "{n} stops",
  "detail.progressDayTotal": "{n} days.",
  "detail.pretripAria": "Pre-trip checklist",
  "detail.pretripKicker": "Before you go",
  "detail.pretripHeading": "The two things the server reports as outstanding",
  /* ORD-0557 兜底行: the sentence this panel paints when the derivation returns nothing. It used to be
     typed inside `lib/pretripChecklist.ts`; the Chinese side is the words already on the glass. */
  "detail.pretripNeitherOpen": "Neither one is open on this generation.",
  "detail.basisPrefix": "Basis: ",
  "detail.anchorPrefix": "Anchor: ",
  "detail.measuredHttpLabel": "This device's reading: HTTP",
  "detail.measuredContentType": "Media type read back",
  "detail.measuredBytes": "Octets this device counted",
  "detail.measuredNoneSuffix": "{label}: this device measured none",
  "detail.receiptFoldSummary": "What this device read back, and the server's receipt",
  "detail.receiptHttpNone": "This device's reading: HTTP measured none",
  "detail.receiptLabel": "server receipt",
  "detail.receiptLabelAbsent": "no server receipt",
  "detail.rawFactsHeading": "Fields this device measured",
  },
  zh: {

  // ── 细节页与状态面 ──
  /* I18N_细节补齐: 这几块屏各自把中文写在 `zh ? "..." : "..."` 的分支里，一条事实会长出两种说法，
     而且两边都查不到键。两端都搬进字典，每条事实在每种语言下各留一种说法。值仍是这些屏本来就在
     显示的那句，不是新写的文案。调用点继续读它自己那半个分支，改调用点是另一件事，所以屏上文字不动。 */
  "detail.backToItinerary": "返回行程",
  "detail.duration": "停留时长",
  "detail.travelFromPrev": "从上一站出发",
  "detail.openingHours": "营业时间",
  "detail.hoursProvided": "已提供",
  "detail.hoursProviderText": " · 供应商原文",
  "detail.hoursNoData": "暂无数据",
  "detail.category": "类型",
  "detail.activityType": "活动类型",
  "detail.location": "位置",
  "detail.noCoordinates": "暂无坐标",
  "detail.showOnMap": "在地图上查看",
  "detail.askCopilot": "问问 Copilot",
  "detail.nearbyStops": "附近的其他停靠点",
  "detail.otherTripStops": "这趟行程的其他停靠点",
  "detail.nearbyNoteClose": "都在约 {n} 米范围内，按直线距离排列。",
  "detail.nearbyNoteFar": "这些是同一行程的其他停靠点，不一定是步行可达的邻近地点。",
  "detail.metres": "{n} 米",
  "detail.kilometres": "{n} 公里",
  "detail.confirmedProtected": "已确认 · 受保护",
  "detail.viewDetails": "查看详情",
  "detail.detailsChevron": "详情 ›",
  "detail.weekIndex": "第 {n} 周",
  "detail.dayStops": "{n} 项",
  "detail.progressDayTotal": "共 {n} 天。",
  "detail.pretripAria": "行前清单",
  "detail.pretripKicker": "行前清单",
  "detail.pretripHeading": "服务端报出的两类待办",
  /* ORD-0557 兜底行：这一面在两类检查都没有可列时念的那一句，原先写死在 `lib/pretripChecklist.ts`，
     这里就是屏上原本那几个字。 */
  "detail.pretripNeitherOpen": "这一代都没有报出。",
  "detail.basisPrefix": "依据：",
  "detail.anchorPrefix": "锚点：",
  "detail.measuredHttpLabel": "这台设备看到的回读：HTTP",
  "detail.measuredContentType": "回读的媒体类型",
  "detail.measuredBytes": "这台设备数到的字节",
  "detail.measuredNoneSuffix": "{label}：这台设备没量到",
  "detail.receiptFoldSummary": "这台设备量到的回读与服务器回执号",
  "detail.receiptHttpNone": "这台设备看到的回读：HTTP 没量到",
  "detail.receiptLabel": "服务器回执号",
  "detail.receiptLabelAbsent": "服务器未给回执号",
  "detail.rawFactsHeading": "这台设备自己量到的回读字段",
  },
};
