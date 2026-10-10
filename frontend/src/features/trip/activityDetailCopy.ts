/**
 * Copy for one activity's detail screen.
 *
 * Own file, not `i18n/LocaleContext.tsx` — the same call `planRankingCopy.ts` documents: that file
 * is the most contested mount tonight. Keys are prefixed `activity.` rather than the `detail.`
 * segment another lane named in the ledger, because that segment is not on the tip and two
 * families under one name is how a dictionary starts to disagree with itself.
 */
export const activityDetailCopy = {
  en: {
    "activity.backToItinerary": "Back to itinerary",
    "activity.stopConfirmed": "This is a confirmed booking and will not be moved by other changes.",
    "activity.stopOpen": "This is one stop on your itinerary.",
    "activity.factDuration": "Duration",
    "activity.factCost": "Cost",
    "activity.costFree": "Free",
    "activity.factHours": "Opening hours",
    "activity.factCategory": "Category",
    "activity.factKind": "Activity type",
    "activity.factLocation": "Location",
    "activity.noCoords": "No coordinates",
    "activity.factTravelFromPrev": "Travel from previous stop",
    "activity.showOnMap": "Show on map",
    "activity.askCopilot": "Ask Copilot",
    "activity.nearbyStops": "Other stops nearby",
    "activity.otherStops": "Other stops on this trip",
    "activity.otherStopsNote": "These are other stops on the same trip; they are not necessarily within walking distance.",
    "activity.noOtherStops": "This trip has no other stop beside this one, so there is nothing to place nearby or far away.",
  },
  "zh-CN": {
    "activity.backToItinerary": "返回行程",
    "activity.stopConfirmed": "这是已确认的安排，不会因为其他调整被移动。",
    "activity.stopOpen": "这是你行程中的一个停靠点。",
    "activity.factDuration": "停留时长",
    "activity.factCost": "费用",
    "activity.costFree": "免费",
    "activity.factHours": "营业时间",
    "activity.factCategory": "类型",
    "activity.factKind": "活动类型",
    "activity.factLocation": "位置",
    "activity.noCoords": "暂无坐标",
    "activity.factTravelFromPrev": "从上一站出发",
    "activity.showOnMap": "在地图上查看",
    "activity.askCopilot": "问问 Copilot",
    "activity.nearbyStops": "附近的其他停靠点",
    "activity.otherStops": "这趟行程的其他停靠点",
    "activity.otherStopsNote": "这些是同一行程的其他停靠点，不一定是步行可达的邻近地点。",
    "activity.noOtherStops": "这一程除了这一站没有别的停靠点，所以这里既没有邻近的站，也没有远处的站。",
  },
} as const;

export type ActivityDetailCopyKey = keyof (typeof activityDetailCopy)["zh-CN"];

export function activityDetailCopyLookup(locale: string, key: ActivityDetailCopyKey): string {
  const table = activityDetailCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? activityDetailCopy.en[key] ?? key;
}
