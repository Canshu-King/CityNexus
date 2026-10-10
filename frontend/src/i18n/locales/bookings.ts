// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const bookings = {
  en: {

  // ── Bookings ──
  "bookings.kicker": "Journey Inbox · Travel Wallet",
  "bookings.realtimeOnTime": "On time",
  "bookings.realtimeDelayed": "Delayed",
  "bookings.realtimeCancelled": "Cancelled",
  "bookings.realtimeNoStatus": "No live status",
  "bookings.realtimeStatusUnknown": "Status unknown",
  "bookings.title": "Your real reservations, protected.",
  "bookings.lede": "Paste structured reservation JSON, review it, then bind confirmed facts to the Journey as a durable commitment.",
  "bookings.stayEvidence": "Stay evidence",
  "bookings.noStay": "No stay selected",
  "bookings.freeCancel": "Free cancellation",
  "bookings.nonRefundable": "Non-refundable",
  "bookings.total": "total",
  "bookings.stayPreview": "STAY PREVIEW",
  "bookings.notChosen": "Not chosen",
  "bookings.noStaySub": "No stay option is available for this trip yet.",
  /* ORD-0407 ②: the sentence above named a state with no handle on it. The action opens the screen
     that owns stays (`nav.stay` = "Stay Explorer"), which is the only door this build has. It does not
     promise a room: the stay screen answers for itself, including when it has no offers. */
  "bookings.noStayAction": "Open Stay Explorer to look for one",
  "bookings.notBooked": "Not booked",
  "bookings.priceUnknown": "Price unknown",
  /* ORD-0517: a card may not borrow an identifier for a title. These are the named empty states for
     the two payload kinds that carry no name of their own. `Dict` is keyed by TripLocale, so a key
     that lands on one side only is a type error -- that is what keeps every tier paired. */
  "bookings.reservationUnnamed": "The server gave no name for this booking",
  "bookings.commitmentUnnamed": "The server gave no name for this commitment",
  "bookings.commitmentSimulated": "simulated commitment",
  "bookings.orderRef": "Reference",
  "bookings.protectedC4": "Protected C4",
  "bookings.importKicker": "IMPORT CONFIRMATION",
  "bookings.importBooking": "Import a booking",
  "bookings.advancedStructuredData": "Advanced: structured data",
  "bookings.reservationJson": "Reservation JSON",
  "bookings.reviewProtect": "Review and protect",
  "bookings.neverInvented": "Critical origin, destination, time, provider and reference facts are never invented.",
  "bookings.authorityExplicit": "Authority remains explicit",
  "bookings.authoritySub": "Importing a confirmed reservation protects it. Any payment, cancellation or irreversible change still passes the Delegation Policy.",
  },
  zh: {

  // ── Bookings ──
  "bookings.kicker": "行程收件箱 · 旅行票夹",
  "bookings.realtimeOnTime": "准点",
  "bookings.realtimeDelayed": "延误",
  "bookings.realtimeCancelled": "已取消",
  "bookings.realtimeNoStatus": "暂无实时状态",
  "bookings.realtimeStatusUnknown": "状态未知",
  "bookings.title": "你的真实预订，受保护。",
  "bookings.lede": "粘贴结构化预订 JSON，审核后，将确认的事实绑定为行程的持久承诺。",
  "bookings.stayEvidence": "住宿证据",
  "bookings.noStay": "未选择住宿",
  "bookings.freeCancel": "免费取消",
  "bookings.nonRefundable": "不可退款",
  "bookings.total": "合计",
  "bookings.stayPreview": "住宿预览",
  "bookings.notChosen": "尚未选择",
  "bookings.noStaySub": "这趟行程目前还没有可选的住宿。",
  "bookings.noStayAction": "到「住宿选择」里找一间可订的房",
  "bookings.notBooked": "未预订",
  "bookings.priceUnknown": "价格未知",
  "bookings.reservationUnnamed": "服务器没有给这单预订的名字",
  "bookings.commitmentUnnamed": "服务器没有给这项承诺的名字",
  "bookings.commitmentSimulated": "模拟承诺",
  "bookings.orderRef": "订单号",
  "bookings.protectedC4": "受保护 C4",
  "bookings.importKicker": "导入确认",
  "bookings.importBooking": "导入预订",
  "bookings.advancedStructuredData": "高级：结构化数据",
  "bookings.reservationJson": "预订 JSON",
  "bookings.reviewProtect": "审核并保护",
  "bookings.neverInvented": "关键的出发地、目的地、时间、供应商和参考事实绝不会被编造。",
  "bookings.authorityExplicit": "权限始终明确",
  "bookings.authoritySub": "导入已确认的预订即受保护。任何支付、取消或不可逆变更仍需通过委托策略。",
  },
};
