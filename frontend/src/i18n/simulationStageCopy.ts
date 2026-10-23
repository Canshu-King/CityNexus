/* 模拟舞台（SimulationPanel）这块屏自己的词表。
 *
 * 为什么单开一份（而不是往 LocaleContext.tsx 里塞）：那张字典正被别的车道同时改，
 * 号令者的收块规则是按文件摘取（同一条理由见 src/i18n/mapPanelCopy.ts 与
 * src/i18n/agentWorkFeedCopy.ts 的开头）。
 *
 * 这里每一句都是从 SimulationPanel.tsx 逐字搬来的：屏幕上的字一个也没改变。
 * 它们说的都是服务器给出的事实（或「服务器还没给」那种说法），不允许出现编出来的进度。
 * 组件仍然按 locale.startsWith("zh") 自己选臂，所以选择逻辑也没动。
 */

export type SimulationStageCopyKey =
  | "cursorStillReading"
  | "executingButCursorEmpty"
  | "activityStatusStillReading"
  | "cursorOffPlanList"
  | "cityStillReading"
  | "serviceCatalogueStillReading"
  | "serviceWindowsBeingAsked"
  | "rowReset"
  | "resetNeedsServerSideToken"
  | "rowPrepare"
  | "prepareAlreadyExecuting"
  | "bookNothingOrderable"
  | "rowStart"
  | "startAlreadyExecuting"
  | "startNoPlanOnStage"
  | "rowEvent"
  | "rowReplan"
  | "replanNeedsDisruption"
  | "acceptNoProposal"
  | "rejectNoProposal"
  | "rowDegrade"
  | "rowRestore"
  | "previousActionStillRunning";

const COPY: Record<SimulationStageCopyKey, { zh: string; en: string }> = {
  cursorStillReading: { zh: "服务器游标还在读，读完才知道有没有可推进的活动。", en: "The server cursor is still being read." },
  executingButCursorEmpty: { zh: "服务器说这趟在执行中，但游标是空的（没有任何活动在进行），所以这一步没有可推进的位置。", en: "The server says the journey is executing but the cursor is empty (no activity is in progress), so there is no position to advance from." },
  activityStatusStillReading: { zh: "还在读这份计划里当前活动的状态。", en: "The current activity's status is still being read." },
  cursorOffPlanList: { zh: "服务器给的当前活动不在这份计划的清单里，所以没有可执行的下一步。", en: "The cursor points at an activity that is not on this plan, so there is no next step to offer." },
  cityStillReading: { zh: "还在读这趟行程属于哪座城。", en: "The journey's city is still being read." },
  serviceCatalogueStillReading: { zh: "还在读这座城的服务目录（哪些地点挂着可下单的服务）。", en: "The city's service catalogue is still being read." },
  serviceWindowsBeingAsked: { zh: "目录里有带着可下单服务的活动，正在逐个按它自己的时间问服务器那一段有没有时段。", en: "Some activities carry an orderable service; their windows are being asked of the server." },
  rowReset: { zh: "重置到场景起点", en: "Re-seed the scenario" },
  resetNeedsServerSideToken: { zh: "这一步会删掉整库（52 张表），现在还要服务器自己的环境变量里的令牌；浏览器拿不到它，也不该拿到。所以这里不给按——要重播种行程，请由运行服务器的人来做。", en: "This step deletes the whole library (52 tables) and now needs a token that lives in the server's own environment. A browser cannot hold that value and should not, so this is refused on every deployment -- re-seeding is done by whoever runs the server." },
  rowPrepare: { zh: "准备舞台（生成并选定计划）", en: "Put a plan on the stage" },
  prepareAlreadyExecuting: { zh: "服务器说这趟已经在执行中，不需要再准备一次。", en: "The server says this journey is already executing; preparing again is not the step." },
  bookNothingOrderable: { zh: "服务器给的这份计划里没有可下单的活动，所以这里没有可建承诺的东西。", en: "The plan the server gave carries no activity that can be ordered, so there is nothing here to book." },
  rowStart: { zh: "开始执行（真实 /start）", en: "Put the journey into execution" },
  startAlreadyExecuting: { zh: "服务器说这趟已经在执行中，不需要再开始一次。", en: "The server says this journey is already executing." },
  startNoPlanOnStage: { zh: "舞台上还没有计划（服务器回的 plan_version_id 是空的）。先按上面「准备舞台」，才有可开始的东西。", en: "No plan on the stage yet (the server's plan_version_id is empty). Put a plan on it first; that is what there is to start." },
  rowEvent: { zh: "触发一次中断", en: "Raise a disruption" },
  rowReplan: { zh: "请求重规划", en: "Ask for a replan" },
  replanNeedsDisruption: { zh: "重规划要由一个中断触发（服务器要求 trigger_event_id）。先按上面「触发一次中断」。", en: "A replan needs a triggering event (the server requires trigger_event_id). Raise a disruption above first." },
  acceptNoProposal: { zh: "服务器还没有给出方案（它回的列表是空的），所以这里没有可接受的东西。", en: "The server has not offered a proposal (its list is empty), so there is nothing to accept." },
  rejectNoProposal: { zh: "服务器还没有给出方案（它回的列表是空的），所以这里没有可拒绝的东西。", en: "The server has not offered a proposal (its list is empty), so there is nothing to reject." },
  rowDegrade: { zh: "提供方降级", en: "Degrade the provider" },
  rowRestore: { zh: "提供方恢复", en: "Restore the provider" },
  previousActionStillRunning: { zh: "上一个动作还没回来。", en: "The previous action is still running." },
};

/** The two arms as one object: the stage builds blockers and rows that carry both, then the
    render picks the arm by locale -- same selection the component did with its inline literals. */
export function simulationStagePair(key: SimulationStageCopyKey): { zh: string; en: string } {
  return COPY[key];
}

/** Same locale rule the component uses inline: anything starting with zh takes the Chinese arm. */
export function simulationStageCopy(locale: string, key: SimulationStageCopyKey): string {
  const arms = COPY[key];
  return locale.startsWith("zh") ? arms.zh : arms.en;
}

/* Two of the 25 static bilingual pairs measured in SimulationPanel.tsx stayed inline: the sentences
 * that name the server's own enums NO_SCENARIO and ACTIVE.  codes_on_screen_gate_r4 refuses a
 * *newly written* rendered line carrying a raw server enum, and rewording those two would change
 * what a traveller reads -- a copy ruling this lane does not take on its own.  The gate's verdict
 * and both sentences are recorded in the ledger block for this cell (lane 1d64acf5).
 */
