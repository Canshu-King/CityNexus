/**
 * ORD-0529: the catalog-hydration job's own vocabulary, in exactly one place.
 *
 * The destination-preparation screen has always said these outcomes in its own words.  The trip
 * screen's empty cell now runs the same job for its own journey's city, and a second table of the
 * same server facts would be a second answer -- the two would agree until a new outcome landed, and
 * only one of them would be wrong.  So the panel reads this module too; nothing here rewrites a
 * sentence that was already on the line.
 */

import { deviceReadout } from "../../lib/failureAttribution";

export type HydrationCopy = { title: string; body: string };

/** While the job runs: the server's `phase` and `elapsed_ms`, and never a percentage. */
export function hydrationRunningCopy(
  job: { phase: string; elapsed_ms: number; reused: boolean },
  zh: boolean,
): HydrationCopy {
  const elapsedCell = deviceReadout({ elapsed_ms: job.elapsed_ms }, ["elapsed_ms"]);
  return {
    title: job.reused
      ? zh
        ? "这件事已经在准备了"
        : "This is already being prepared"
      : zh
        ? "正在准备这个目的地"
        : "Preparing this destination",
    body: zh
      ? `服务器说现在在「${job.phase}」这一步，已经跑了 ${Math.round(job.elapsed_ms / 1000)} 秒（${elapsedCell}）。进度不按百分比报——服务器不给这个数，因为队列它自己看不到。`
      : `The server reports it is inside "${job.phase}", running ${Math.round(job.elapsed_ms / 1000)}s (${elapsedCell}). No percentage is shown because the server does not publish one -- it cannot see the queue.`,
  };
}

/** A finished job, keyed by the outcome token the server owns. */
export function hydrationOutcomeCopy(outcome: string, status: string, zh: boolean): HydrationCopy {
  switch (outcome) {
    case "CATALOG_PREPARED":
      return {
        title: zh ? "准备好了，可以去规划" : "Prepared -- you can go and plan",
        body: zh
          ? "服务器说这座城需要的事实已经落库。现在规划会用到它们。"
          : "The server says the facts this city needs are now stored, so planning will use them.",
      };
    case "ALREADY_CURRENT":
      return {
        title: zh ? "本来就是新的，没有改动" : "Already current -- nothing was changed",
        body: zh
          ? "服务器说这份资料已经是新的，所以这次准备什么也没做。这不是失败。"
          : "The server says this material was already current, so this run changed nothing. That is not a failure.",
      };
    case "NO_REGISTERED_SOURCE":
      return {
        title: zh ? "这个目的地没有可追溯的来源" : "No traceable source for this destination",
        body: zh
          ? "服务器说这个目的地它找不到任何可追溯的数据来源，所以准备不了。这是关于这个地方的事实，不是网络或服务器故障。换个目的地吧。"
          : "The server says it has no traceable source for this destination, so it cannot prepare it. That is a fact about the place, not a network or server fault. Choose another destination.",
      };
    case "ABANDONED_BY_TRAVELLER":
      return {
        title: zh ? "你已经停止这次准备" : "You stopped this preparation",
        body: zh
          ? "服务器记下了你的停止，它不再用这次的结果。"
          : "The server recorded the stop and will not use this run's result.",
      };
    case "RESOLVER_RUNTIME_FAILURE":
      return {
        title: zh ? "解析这次运行失败了" : "The resolver failed at runtime",
        body: zh
          ? "服务器说这是它那边的一次运行性失败（可以重试），不是「这个地方不存在」。"
          : "The server reports a runtime failure on its side (retryable), not that the place does not exist.",
      };
    case "WORKER_LOST":
      return {
        title: zh ? "这次准备中途丢了" : "This preparation was lost mid-run",
        body: zh
          ? "服务器说执行它的工作进程没了，这次不算数。可以再来一次。"
          : "The server says the worker running it disappeared, so this attempt does not count. Starting again is the route.",
      };
    default:
      return {
        title: zh ? `准备结束：${status}` : `Preparation ended: ${status}`,
        body: zh
          ? `服务器给出的结局是 ${outcome || "—"}，本地没有对应文案，照它说的给。`
          : `The server's outcome is ${outcome || "—"}; there is no local copy for it, so it is shown as-is.`,
      };
  }
}
