// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const itinerary = {
  en: {

  // ── Itinerary list: empty state & status headers ──
  /* I18N_细节补齐 (slice 2): the itinerary screen's empty state and its day-strip status headers each
     carried their own inline `zh ? "..." : "..."` arm, so neither half was reachable by a key lookup.
     Both halves move here. The interpolated arms (week index, per-day stop count) already live under
     `detail.weekIndex` / `detail.dayStops`; this section is only the sentence arms. Values are the
     strings the screen was already showing, not new copy. */
  "itinerary.importPrompt": "Import places for this trip",
  "itinerary.planWithAiNeedsPlaces": "Plan my trip with AI (needs places first)",
  "itinerary.planWithAi": "Plan my trip with AI",
  "itinerary.emptyTitle": "No itinerary yet",
  // The stop's own "this is where you are" marker. Not reusing `today.now`: that key
  // reads 现在 on the Chinese side, and this label says 当前 on screen today.
  "itinerary.stopNow": "Now",
  "itinerary.emptyPlanNoDays": "No stop in this plan sits on a day yet. Add stops and this screen lists them day by day.",
  "itinerary.emptyNoPlan": "This trip has no chosen plan yet. Ask the AI to plan it, then pick a plan and the day-by-day itinerary appears here.",
  "itinerary.emptyReadingPlaces": "Reading back from the server how many places this city holds…",
  "itinerary.lengthUnknown": "length unknown",
  "itinerary.dayByDay": "Day by day. Confirmed bookings are marked as protected.",
  },
  zh: {

  // ── 行程列表：空态与状态头 ──
  /* I18N_细节补齐（第二片）：行程屏的空态和它那些逐日状态头，各自把中文写在 `zh ? "..." : "..."` 的分支
     里，两边都查不到键。两端都搬进字典。插值的分支（周序号、每天站点数）已经在 `detail.weekIndex` /
     `detail.dayStops`，这一段只收句子分支。值仍是这些屏本来就在显示的那句，不是新写的文案。 */
  "itinerary.importPrompt": "去导入这趟的地点",
  "itinerary.planWithAiNeedsPlaces": "AI 帮我规划（要先有地点）",
  "itinerary.planWithAi": "AI 帮我规划",
  "itinerary.emptyTitle": "还没有可看的行程",
  "itinerary.stopNow": "当前",
  "itinerary.emptyPlanNoDays": "这一版方案里还没有站点被排在某一天上。补上站点，这一屏就按天把它们列出来。",
  "itinerary.emptyNoPlan": "这个行程还没有选定的方案。先让 AI 帮你规划，选定方案后这里会显示逐日安排。",
  "itinerary.emptyReadingPlaces": "正在向服务器回读这座城有多少地点…",
  "itinerary.lengthUnknown": "天数未知",
  "itinerary.dayByDay": "逐日安排。已确认的预订会被标记为受保护。",
  },
};
