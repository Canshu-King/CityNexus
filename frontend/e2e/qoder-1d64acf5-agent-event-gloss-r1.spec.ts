import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { agentEventGloss, agentWorkCopy } from "../src/i18n/agentWorkFeedCopy";

/* 内联双语迁移的反控臂（车道 1d64acf5）。
 *
 * 这 11 句「服务器事件类型 → 人读的一句话」原先成对写死在 `AgentWorkFeedPanel.tsx` 里，
 * 是 `## ORDERS` 盘点里那 311 处可见汉字的一部分。本单把它们搬进本车道自己的字典
 * `src/i18n/agentWorkFeedCopy.ts`，字面量一个都不改。
 *
 * 为什么这枚臂会真的咬：
 *   1) 它**调用**字典函数，不是读字符串——把 `EVENT_GLOSS` 或两张表里任何一条删掉，那一行就红；
 *   2) 它同时回读组件源码，要求那 11 句中文不再内联出现在 `AgentWorkFeedPanel.tsx` 里——
 *      把改动 revert 掉（词表回到组件内），这一组就红；
 *   3) 分母不为空：表里少一枚，`EXPECTED.length` 这条先红，不会出现「零条断言也算过」。
 */

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const PANEL = join(FRONTEND, "src", "features", "agent", "AgentWorkFeedPanel.tsx");

/** 服务器写的事件类型 → 迁移前屏上就有的那两句，逐字抄，不许改。 */
const EXPECTED: Array<{ event: string; zh: string; en: string }> = [
  { event: "journey.created", zh: "行程已创建", en: "the trip was created" },
  { event: "traveler.created", zh: "旅行者已建立", en: "a traveller was created" },
  { event: "journey.updated", zh: "行程资料有更新", en: "the trip details changed" },
  { event: "journey.deleted", zh: "行程已删除", en: "the trip was deleted" },
  { event: "agent_tool_requested", zh: "AI 请求使用一个工具", en: "the AI asked to use a tool" },
  { event: "replan_requested", zh: "AI 请求重排行程", en: "the AI asked to re-plan" },
  { event: "impact_hypothesis_created", zh: "影响假设已记录", en: "an impact hypothesis was recorded" },
  { event: "impact_corroborated", zh: "影响已被佐证", en: "an impact was corroborated" },
  { event: "impact_validated", zh: "影响已核实", en: "an impact was validated" },
  { event: "proposal.created", zh: "方案已生成", en: "a proposal was created" },
  { event: "approval.required", zh: "等待你的确认", en: "your approval is needed" },
];

test("分母：这 11 枚事件标签是这一格的完整清单", () => {
  expect(EXPECTED.length).toBe(11);
});

test("字典两侧都答得出，且逐字等于迁移前屏上那两句", () => {
  for (const row of EXPECTED) {
    const zhKey = agentEventGloss("zh-CN", row.event);
    const enKey = agentEventGloss("en-GB", row.event);
    expect(zhKey, `中文侧没有这一枚事件类型的键：${row.event}`).toBeTruthy();
    expect(enKey, `英文侧没有这一枚事件类型的键：${row.event}`).toBeTruthy();
    expect(agentWorkCopy("zh-CN", zhKey!)).toBe(row.zh);
    expect(agentWorkCopy("en-GB", enKey!)).toBe(row.en);
  }
});

test("词表外的事件类型回 null，两侧都是（判不出就不猜一句）", () => {
  expect(agentEventGloss("zh-CN", "something.the.server.made.up")).toBeNull();
  expect(agentEventGloss("en-GB", "something.the.server.made.up")).toBeNull();
});

test("大小写不敏感：服务器把同一件事写成大写形状时也认得", () => {
  const key = agentEventGloss("zh-CN", "JOURNEY.CREATED");
  expect(key).toBeTruthy();
  expect(agentWorkCopy("zh-CN", key!)).toBe("行程已创建");
});

test("反控：这 11 句不再内联留在组件源码里", () => {
  const src = readFileSync(PANEL, "utf-8");
  for (const row of EXPECTED) {
    expect(src.includes(`"${row.zh}"`), `组件里还内联着中文那句：${row.zh}`).toBe(false);
    expect(src.includes(`"${row.en}"`), `组件里还内联着英文那句：${row.en}`).toBe(false);
  }
});

test("组件确实改成走字典通道（不是删掉了事）", () => {
  const src = readFileSync(PANEL, "utf-8");
  expect(src.includes("agentEventGloss")).toBe(true);
  expect(src.includes('from "../../i18n/agentWorkFeedCopy"')).toBe(true);
});
