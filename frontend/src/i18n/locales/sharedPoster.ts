// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const sharedPoster = {
  en: {
  /* ORD-0528: the guest's poster shape. Only the sentences that say what *this shape* are here --
     loading, no-token, refusal and empty-plan lines are the door's, and this screen quotes
     `shared.*` for them so one fact cannot grow two wordings. */
  "sharedPoster.kicker": "A shared trip poster",
  "sharedPoster.counted": "{city} · {days} {plural:day:days} · {stops} {plural:stop:stops}, counted from what this link sent",
  /* ORD-0542: the finding was that this page printed "trip length unknown" on one line and "2 days" on
     the next. Both facts are true -- the share door sends no length projection -- so one sentence now
     carries the number and the next one says what kind of number it is. */
  "sharedPoster.countedWhy": "That is a count of the days this link sent, not the trip's own length projection: the share door answers no projection.",
  "sharedPoster.formNote": "This link opens the trip's long picture: one block per day, and nothing here you can act on. The trip itself and its map open from the same link in its other shape.",
  "sharedPoster.download": "Save this picture",
  "sharedPoster.made": "Saved as a PNG.",
  "sharedPoster.failed": "The picture was not made: this device's drawing surface refused to draw.",
  },
  zh: {
  "sharedPoster.kicker": "别人分享给你的行程长图",
  "sharedPoster.counted": "{city} · 按这条链接读到的内容数出 {days} 天 · {stops} 站",
  "sharedPoster.countedWhy": "上面那个天数是数出来的，不是这趟旅行的长度投影：分享那一扇门不答投影，投影只在旅行者自己那扇门上。",
  "sharedPoster.formNote": "这一屏是这趟旅行的长图形状：一天一块，可以存成图片。它不是行程本身——行程和地图用同一条链接的另一种形状打开，这里没有任何能改动别人旅行的操作。",
  "sharedPoster.download": "存下这张图",
  "sharedPoster.made": "已存为 PNG。",
  "sharedPoster.failed": "图没有生成：这台设备的画布没有交出可用的绘制上下文。",
  },
};
