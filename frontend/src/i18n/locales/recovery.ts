// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const recovery = {
  en: {
  /* ORD-0370 tier 1: the recovery panels' own placeholder lines. Each English value
     is the exact word the panel printed before the key existed, so an English screen
     cannot move; only the Chinese screen stops reading English. */
  "recovery.statusUnavailable": "unavailable",
  "recovery.guardianEnvelope": "guardian envelope",
  "recovery.noDominantMode": "no dominant mode",
  "recovery.noneOnThisJourney": "none on this journey",
  "recovery.changedFromActivity": "Current activity",
  "recovery.changedToActivity": "recovered activity",

  // ── Recovery / stale-evidence card ──
  /* ORD-0369: this card is what a traveller hits first when a chosen plan can no longer be
     verified, and every sentence in it used to be a hardcoded English literal inside the component
     -- an unreadable gate in front of the only way out of a stale plan. */
  "recovery.staleTitle": "Trip evidence needs re-syncing",
  "recovery.staleDetail": "The route evidence this plan was built on has expired, so a change to it cannot be checked yet. Nothing about your trip has been altered.",
  "recovery.noAltTitle": "No safe alternative is available",
  "recovery.noAltDetail": "A replan was attempted for {code} and produced no feasible alternative. The current plan stays unverified.",
  "recovery.decisionTitle": "Your trip needs a decision",
  "recovery.decisionDetail": "A new hard requirement ({code}) means the current plan can no longer be confirmed as safe. Your existing plan has not been changed.",
  "recovery.generate": "Generate new options",
  "recovery.generating": "Generating…",
  "recovery.generated": "Fresh options generated. Select one to clear this warning - it stays until then.",
  "recovery.generateRefused": "The server refused to generate new options (HTTP {status}, named {code}). No plan was changed.",
  "recovery.acknowledge": "Acknowledge warning",
  "recovery.acknowledged": "Warning acknowledged",
  "recovery.ackRefused": "The server did not accept the acknowledgement (HTTP {status}, named {code}). The warning is still showing because the plan is still unverified.",
  "recovery.noOpenRecovery": "There is no recovery decision open on this journey to acknowledge: what is stale here is the plan's evidence, and the server says so. This warning clears when a verified plan is selected.",
  "recovery.failureCount": "The server listed {n} {plural:refusal} against this plan; its own words are in the technical detail.",
  "recovery.technicalDetail": "Technical detail",
  "recovery.serverReason": "Reason the server gave",
  "recovery.deviceReason": "This device's own reading (the server sent no sentence)",
  "recovery.diffRemoved": "Removed",
  "recovery.diffAdded": "Replaced with",
  "recovery.diffMoved": "Moved",
  "recovery.affectedPrefix": " · Affected: ",
  "recovery.suggestedChange": "Suggested change",
  },
  zh: {
  "recovery.statusUnavailable": "暂无状态",
  "recovery.guardianEnvelope": "守护授权",
  // ORD-0557 transport, not a rewrite: V14PreventivePanel prints these two
  // fallbacks as English literals in both locales, so the zh value is the exact
  // word already on screen. Wording is a separate order.
  "recovery.noDominantMode": "no dominant mode",
  "recovery.noneOnThisJourney": "none on this journey",
  "recovery.changedFromActivity": "当前活动",
  "recovery.changedToActivity": "恢复的活动",

  // ── 恢复与证据过期卡片 ──
  "recovery.staleTitle": "这趟行程的出行证据需要重新同步",
  "recovery.staleDetail": "这套方案当初依据的路线证据已经过期，所以现在对它的改动还没法校验。你行程上的任何东西都没有被改动。",
  "recovery.noAltTitle": "没有安全的替代方案",
  "recovery.noAltDetail": "针对 {code} 试过一次重规划，没有产出可行的替代方案。当前方案仍未通过校验。",
  "recovery.decisionTitle": "你的行程需要你做一个决定",
  "recovery.decisionDetail": "新增加的一条硬性要求（{code}）让当前方案无法再被确认为安全。你原有的方案没有被改动。",
  "recovery.generate": "重新生成可选方案",
  "recovery.generating": "正在生成…",
  "recovery.generated": "已经生成新的可选方案。选定其中一份之后这条提醒才会消失——在那之前它会一直显示。",
  "recovery.generateRefused": "服务器拒绝了这次生成（HTTP {status}，具名 {code}）。没有任何方案被改动。",
  "recovery.acknowledge": "我知道了这条提醒",
  "recovery.acknowledged": "已确认收到提醒",
  "recovery.ackRefused": "服务器没有接受这次确认（HTTP {status}，具名 {code}）。提醒仍在显示，因为方案仍未通过校验。",
  "recovery.noOpenRecovery": "这趟行程现在没有等待确认的恢复决定：这里过期的是方案的证据，服务器就是这么答的。选定一份通过校验的方案后这条提醒才会消失。",
  "recovery.failureCount": "服务器针对这一版列出了 {n} 条拒绝，原文在技术详情里。",
  "recovery.technicalDetail": "技术详情",
  "recovery.serverReason": "服务器给出的原因",
  "recovery.deviceReason": "这台设备自己的读数（服务器没给句子）",
  "recovery.diffRemoved": "移出",
  "recovery.diffAdded": "换成",
  "recovery.diffMoved": "调整时间",
  "recovery.affectedPrefix": " · 受影响：",
  "recovery.suggestedChange": "推荐怎么改",
  },
};
