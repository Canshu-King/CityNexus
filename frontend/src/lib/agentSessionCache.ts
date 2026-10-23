/* Issue #27：Agent 轨迹与 Copilot 会话不再落在"跨人"的盘上。
 *
 * 改之前有两处 localStorage：
 *   `citynexus.copilot.history.<journeyId>` —— 里面连 `response.agent_run` 和它的
 *     `initial_events` 一起存（`features/agent/AgentComposer.tsx`）；
 *   `citynexus.native-hermes.timeline.<journeyId>.<runId>` —— 事件表（`features/agent/CopilotDock.tsx`）。
 * 两把键都只绑行程号，而行程是成员共用的。同一台手机上换一个人、回到同一个行程入口，
 * 上一位的工具行就先播出来了：`e2e/qoder27-timeline-identity-boundary.spec.ts` 里那行
 * `A-ONLY-…` 记号就是这件事的可复现证据。
 *
 * 这一份只活在本页内存里：路由卸载、面板关掉都不丢（那正是原注释要保的事），刷新即空。
 * 权威仍是服务器那条审计时间线；盘上没有可回放的副本，也就没有"跨人"这条路。
 *
 * 为什么不做"绑身份的本地缓存"：这台部署里没有任何接口告诉前端"当前签名查看者是谁"
 * （只有 `/members`、`/share-grants`、`/acl/roles`、`/member-role-limits` 这类"这一趟有谁"的门）。
 * 工单明确要求不许拿 self-reported traveler_id、单独的 journeyId 或 cookie 存在冒充签名权威，
 * 所以在有那一道权威之前，这里干脆不缓存可回放的历史。
 *
 * `dropLegacyDiskCopies` 负责把已经躺在老设备上的那两份抹掉 —— 留着它，下一个读盘的人就是我们。
 */

const transcripts = new Map<string, unknown[]>();
const timelines = new Map<string, unknown[]>();

function journeyTranscriptKey(journeyId: string): string {
  return `t|${journeyId}`;
}

function runTimelineKey(journeyId: string, runId: string): string {
  return `e|${journeyId}|${runId}`;
}

export const LEGACY_TRANSCRIPT_PREFIX = "citynexus.copilot.history.";
export const LEGACY_TIMELINE_PREFIX = "citynexus.native-hermes.timeline.";

export function recallTranscript(journeyId: string): unknown[] | null {
  return (transcripts.get(journeyTranscriptKey(journeyId)) as unknown[] | undefined) ?? null;
}

export function rememberTranscript(journeyId: string, messages: unknown[]): void {
  transcripts.set(journeyTranscriptKey(journeyId), messages.slice(-50));
}

export function recallTimeline(journeyId: string, runId: string): unknown[] | null {
  return (timelines.get(runTimelineKey(journeyId, runId)) as unknown[] | undefined) ?? null;
}

export function rememberTimeline(journeyId: string, runId: string, events: unknown[]): void {
  timelines.set(runTimelineKey(journeyId, runId), events.slice(-250));
}

/** 抹掉这台设备上属于这一趟（以及这一趟里这一跑）的旧副本。只在浏览器里做，失败不响。 */
export function dropLegacyDiskCopies(journeyId: string, runId?: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(`${LEGACY_TRANSCRIPT_PREFIX}${journeyId}`);
    if (runId) window.localStorage.removeItem(`${LEGACY_TIMELINE_PREFIX}${journeyId}.${runId}`);
  } catch {
    // 私密模式或配额问题下删不掉也不该影响这一屏：权威历史在服务器。
  }
}

/** 整页换人时（登出、切换签名会话）由调用方清空这一份内存。 */
export function clearAgentSessionCaches(): void {
  transcripts.clear();
  timelines.clear();
}

/**
 * 换人／退出／凭证失效那一刻的全量清扫：这台设备上属于**任何**行程的 Agent 旧副本都不再属于
 * 当前这个人，所以不能只擦"当前那一趟"。Issue #27 收住了新的写入，`dropLegacyDiskCopies`
 * 只按一枚行程号擦，改前它擦不到上一位留下的别的行程；`clearSignedSession` 现在两样都做，
 * 返回值只为让调用方能数清擦了几条，不改变判定。
 */
export function dropAllLegacyDiskCopies(): number {
  if (typeof window === "undefined") return 0;
  let removed = 0;
  try {
    for (const key of Object.keys(window.localStorage)) {
      if (key.startsWith(LEGACY_TRANSCRIPT_PREFIX) || key.startsWith(LEGACY_TIMELINE_PREFIX)) {
        window.localStorage.removeItem(key);
        removed += 1;
      }
    }
  } catch {
    /* 私密模式或配额问题下删不掉也不该影响这一屏：权威记录在服务器。 */
  }
  return removed;
}
