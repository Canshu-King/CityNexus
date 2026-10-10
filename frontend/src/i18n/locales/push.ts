// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const push = {
  en: {

  // ── Push Capability ──
  "push.checking": "Checking delivery path…",
  "push.unavailable": "Push capability unavailable · in-app records remain active.",
  "push.noKey": "No VAPID key is configured · notifications are recorded in the Journey.",
  "push.saved": "Web Push subscription saved; policy-bound delivery remains auditable.",
  "push.notEnabled": "Web Push was not enabled · the server will keep a notification record.",
  "push.kicker": "NOTIFICATIONS",
  "push.checkingState": "Checking",
  "push.enable": "Enable Web Push",
  /* ORD-0251: the server's own labels (RECORD_ONLY / DEPENDENCY_MISSING / WEB_PUSH_CONFIGURED) are not
     prose, and an unknown one is reported as unknown rather than echoed back. */
  "push.capRecordOnly": "Recorded, not pushed",
  "push.capRecordOnlyHelp": "The server has no push key, so notifications stay in the journey and never reach this device.",
  "push.capDependencyMissing": "Push component missing on the server",
  "push.capDependencyMissingHelp": "A push component is missing on the server, so records stay in the journey. That is the server's to install, not yours to fix.",
  "push.capWebPushConfigured": "Push is configured",
  "push.capWebPushConfiguredHelp": "The server can send push. The button below asks the browser to subscribe this device.",
  "push.capUnknown": "Push availability unclear",
  "push.capUnknownHelp": "The server answered with a status this screen does not know, so we do not guess whether it can push.",
  "push.capUnread": "Push status unreadable",
  },
  zh: {

  // ── 推送能力 ──
  "push.checking": "正在检查推送通道…",
  "push.unavailable": "推送能力不可用 · 应用内记录保持活跃。",
  "push.noKey": "未配置 VAPID 密钥 · 通知记录在行程中。",
  "push.saved": "Web Push 订阅已保存；策略绑定的推送仍可审计。",
  "push.notEnabled": "Web Push 未启用 · 服务端将保留通知记录。",
  "push.kicker": "通知",
  "push.checkingState": "检查中",
  "push.enable": "启用 Web Push",
  /* ORD-0251：服务器那几个标签（RECORD_ONLY / DEPENDENCY_MISSING / WEB_PUSH_CONFIGURED）不是给人看的话，
     不认识的那个只说"不认识"，不原样回显。 */
  "push.capRecordOnly": "只记录，不发推送",
  "push.capRecordOnlyHelp": "服务器没有配置推送密钥，所以通知只会记在行程里，不会弹到这台设备上。",
  "push.capDependencyMissing": "服务器缺推送组件",
  "push.capDependencyMissingHelp": "服务器少了一个推送组件，目前只能记在行程里；这一格要服务器装上才会变，不是你这边的问题。",
  "push.capWebPushConfigured": "推送已配置",
  "push.capWebPushConfiguredHelp": "服务器已经能发推送；下面的按钮是让浏览器把这台设备加进订阅。",
  "push.capUnknown": "说不准推送能不能用",
  "push.capUnknownHelp": "服务器回了一个本界面不认识的状态，所以我们不猜它能不能推送。",
  "push.capUnread": "读不到推送状态",
  },
};
