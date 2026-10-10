// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const poster = {
  en: {
  /* ORD-0472 — the trip poster. Its source line reuses `mapComp.attribution` directly above: the
     attribution obligation is one sentence in this product, not one per surface. */
  "poster.kicker": "Trip poster",
  "poster.barNote": "One long picture of this trip, made of the days already on this screen.",
  "poster.action": "Open the trip poster",
  "poster.close": "Close the poster",
  "poster.cityAndDays": "{city} · {days} {plural:day:days}",
  "poster.daysUnknown": "{city} · trip length unknown",
  "poster.dayStops": "{n} {plural:stop}",
  "poster.attributionLabel": "Source",
  "poster.paged": "This trip is too tall for one picture, so it is split by day: {pages} pages, each exported on its own.",
  "poster.page": "Page {page}",
  "poster.madePage": "That was page {page} of {pages}.",
  "poster.download": "Make the PNG and save it",
  "poster.working": "Drawing…",
  "poster.made": "Saved as a PNG: {bytes} bytes, {width} × {height} px.",
  "poster.failPrefix": "The poster was not made: ",
  "poster.fail.noCanvas": "this device gave the drawing surface no usable context.",
  "poster.fail.noWidth": "the poster sheet had no width on screen to draw into.",
  "poster.fail.missingTokens": "some of the product's own size and colour settings did not reach the drawing surface.",
  "poster.fail.blank": "the picture was read back pixel by pixel after drawing and nothing was on it.",
  "poster.fail.noBytes": "the drawing surface returned no PNG bytes.",
  "poster.fail.noDownload": "this browser gives us no way to hand you a file.",
  /* ORD-0528: "share this picture". One outlet, one door (the trip's own share grants), and the
     sentence below is only ever the server's list door agreeing that a row exists -- so each of the
     four ways that agreement can fail has its own words. None of them quote the response body: the
     only upstream value these lines carry is the HTTP status the door itself chose.
     ORD-0541: agreement can arrive two ways, and the two are different claims about this trip, so
     they are two lines. Both still open with the same confirmation word the landed X1 arm measures. */
  "poster.share": "Share this picture",
  "poster.sharing": "Asking the server…",
  "poster.shareDone": "Shared. This press wrote a new grant: the server's own grant list answers with {rows} {plural:row:rows} for this trip, and this link's row is {grant}.",
  "poster.shareErrRefused": "Not shared: the server refused this grant write (status {status}).",
  "poster.shareErrNoToken": "Not shared: the write came back without a token, so there is no link to hand over.",
  "poster.shareErrNotListed": "Not shared: the server's grant list does not carry the row this device just wrote.",
  "poster.shareErrRevoked": "Not shared: the row on the server's list carries a revocation, so the link is already withdrawn.",
  "poster.shareErrReadUnanswered": "Not shared: the grant list gave no answer (status {status}), so this device has nothing to confirm.",
  "poster.shareLinkLabel": "The link that opens this picture for somebody else",
  "poster.shareReused": "Shared. This press wrote nothing: the server's grant list for this trip already carried a standing link-readable row, {grant}, and that is the link handed over ({rows} {plural:row:rows} read).",
  },
  zh: {
  /* ORD-0472 — 行程长图（中英两侧同键，见 `poster.kicker` 一节） */
  "poster.kicker": "行程长图",
  "poster.barNote": "把这趟旅行收成一张长图；图上每一天，就是这块屏上已经排好的那些。",
  "poster.action": "展开行程长图",
  "poster.close": "收起长图",
  "poster.cityAndDays": "{city} · {days} 天",
  "poster.daysUnknown": "{city} · 天数未知",
  "poster.dayStops": "{n} 站",
  "poster.attributionLabel": "来源",
  "poster.paged": "图过长，已按天分页：共 {pages} 页，每页可单独导出。",
  "poster.page": "第 {page} 页",
  "poster.madePage": "刚导出的是第 {page} / 共 {pages} 页。",
  "poster.download": "成长图并保存",
  "poster.working": "正在画…",
  "poster.made": "已存为 PNG：{bytes} 字节，{width} × {height} 像素。",
  "poster.failPrefix": "长图没有生成：",
  "poster.fail.noCanvas": "这台设备的画布没有给出可用的绘制上下文。",
  "poster.fail.noWidth": "长图那一屏在屏上没有宽度，画布无处可铺。",
  "poster.fail.missingTokens": "产品自己的一组字号与颜色档位没有传到画布上。",
  "poster.fail.blank": "画完把像素逐块读回来，图上没有任何一笔。",
  "poster.fail.noBytes": "画布没有交出 PNG 字节。",
  "poster.fail.noDownload": "这台浏览器不给我们递文件的出口。",
  "poster.share": "分享这张长图",
  "poster.sharing": "正在向服务器登记…",
  "poster.shareDone": "已分享：这一次按下确实写入了一条授权。服务器自己的授权列表对这趟旅行答出 {rows} 条，这条链接对应的那一条是 {grant}。",
  "poster.shareErrRefused": "没有分享出去：服务器拒了这次授权写入（状态码 {status}）。",
  "poster.shareErrNoToken": "没有分享出去：写入答回来了，但没有交出暗号，所以没有链接可以给你。",
  "poster.shareErrNotListed": "没有分享出去：服务器回读的授权列表里没有这台设备刚写入的那一条。",
  "poster.shareErrRevoked": "没有分享出去：服务器列表上的那一条带着撤销记录，链接已经被收回。",
  "poster.shareErrReadUnanswered": "没有分享出去：授权列表没有给出答复（状态码 {status}），这台设备无从确认。",
  "poster.shareLinkLabel": "让别人打开这张长图的链接",
  "poster.shareReused": "已分享：这一次按下没有再写入。服务器对这趟旅行的授权列表里本来就带着一条仍然有效、档位为链接可读的记录 {grant}，交给你的长图地址就是它那一条（读出 {rows} 条）。",
  },
};
