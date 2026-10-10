// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const calendar = {
  en: {
  // ORD-0525: the itinerary's calendar export.  These keys have to exist in BOTH dictionaries, because
  // `t()` falls back to the key itself -- a `calendar.refused.bin` on screen would be the machine-word
  // exposure this order's own acceptance forbids.
  "calendar.export": "Export calendar",
  "calendar.busy": "Exporting…",
  "calendar.done": "{events} events downloaded — open the file in your calendar app.",
  "calendar.refused.bin": "This trip is in the recycle bin, so there is no calendar to export. Bring it back first.",
  "calendar.refused.not_found": "This trip is not on the server, so there is no calendar to export.",
  "calendar.refused.unreadable": "This trip has no active plan yet, so there is nothing to export.",
  "calendar.refused.not_calendar": "The server answered, but not with a calendar file, so nothing was downloaded.",
  "calendar.refused.unknown": "The calendar could not be exported, so nothing was downloaded.",
  "calendar.unreachable": "The server could not be reached, so nothing was downloaded.",
  },
  zh: {
  // ORD-0525：行程屏的日历导出。中文这一本缺任何一条，屏上就会出现键名本身。
  "calendar.export": "导出日历",
  "calendar.busy": "正在导出…",
  "calendar.done": "已下载 {events} 个日程，可在日历 App 里打开那个文件。",
  "calendar.refused.bin": "这个行程在回收站里，所以现在没有可导出的日历。先把它找回来。",
  "calendar.refused.not_found": "服务器上找不到这个行程，所以现在没有可导出的日历。",
  "calendar.refused.unreadable": "这个行程还没有生效的方案，所以没有可导出的内容。",
  "calendar.refused.not_calendar": "服务器有回应，但回的不是日历文件，所以没有下载任何东西。",
  "calendar.refused.unknown": "日历没能导出，所以没有下载任何东西。",
  "calendar.unreachable": "连不上服务器，所以没有下载任何东西。",
  },
};
