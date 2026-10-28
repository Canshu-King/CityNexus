// One place that turns a refused request into a sentence a traveler can act on.
// Measured on the clean generation (report §85/§86): the client's own error string is
// "CityNexus API 409: /journeys/<uuid>/agent/goal-tasks/<uuid>/resume" -- route plus two ids --
// so no screen may print it. An unknown reason gets the caller's fallback, never the raw string.

const REASONS: [string, string][] = [
  ["GOAL_TASK_ALREADY_RUNNING", "这一轮还在进行中，先等它结束再发新的消息。"],
  ["GOAL_TASK_NOT_RESUMABLE", "这一轮已经结束了，直接说下一步想怎么调整就行。"],
  ["MESSAGE_ID_REUSED_WITH_DIFFERENT_TEXT", "这条消息已经记下别的文字，请把这条重新发一次。"],
  ["GOAL_TASK_REQUIRES_DRAFT", "这趟已经有排好的方案，这一轮不再改草案；到「我的旅程」查看方案。"],
  ["GOAL_TASK_STATE_INVALID", "这一轮的状态已经变了，刷新一下再继续。"],
  ["STALE_RECOMPOSE_REQUIRED", "地点信息有更新，重新准备一次方案就好。"],
  ["PLAN_INFEASIBLE", "这几段之间赶路时间不够，请先调整时间再试。"],
];

export function travelerErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.name === "AbortError") {
    return "本次响应等待超时；刷新可查看最新进度。";
  }
  const body = (error as { body?: { error?: { message?: string }; detail?: string } } | undefined)?.body;
  const reason = `${body?.error?.message ?? ""} ${body?.detail ?? ""}`;
  for (const [needle, sentence] of REASONS) if (reason.includes(needle)) return sentence;
  return fallback;
}
