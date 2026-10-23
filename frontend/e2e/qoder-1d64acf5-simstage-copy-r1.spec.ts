import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { simulationStageCopy, simulationStagePair } from "../src/i18n/simulationStageCopy";
import type { SimulationStageCopyKey } from "../src/i18n/simulationStageCopy";

/* 模拟舞台内联双语迁移的反控臂（车道 1d64acf5）。
 *
 * 这 25 句「按钮名 / 这一步为什么按不动」原先成对写死在 `SimulationPanel.tsx` 里，屏上按
 * `locale.startsWith("zh")` 挑一臂。本单把字面量搬进本车道自己的字典
 * `src/i18n/simulationStageCopy.ts`，一个字母都没改，选择逻辑也仍留在组件里。
 *
 * 为什么这枚臂会真的咬：
 *   1) 它**调用**字典函数取词，不是比对字符串是否存在——表里任何一条被删或被改，那一行就红；
 *   2) 它同时回读组件源码，要求这 25 句不再以 `zh: "…",` 成对内联形状出现在
 *      `SimulationPanel.tsx` 里——把改动 revert（词表回到组件内），第 4、5、6 条就红；
 *   3) 分母写死在表里：少一枚 `EXPECTED.length` 先红，不会出现「零条断言也算过」。
 *
 * 第 4 条为什么只钉「成对内联形状」而不是「文件里不许出现这句话」：本臂第一次真跑就抓到
 * rowReplan 那句「请求重规划」仍以被引用的形式嵌在两句带插值的长文案里（同文件 :334 与 :374，
 * 形如 请用下面「请求重规划」）。那两枚是**带 ${} 插值的另一族**，不在本格 25 枚的分母里；
 * 它们把按钮名硬写在散文里，名字一改就会说假话——这一格不扩半径，只把这个耦合点名记下来。
 */

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const PANEL = join(FRONTEND, "src", "features", "simulation", "SimulationPanel.tsx");

/** 键名 -> 迁移前屏上就有的那两句，逐字抄自父提的组件源码，不许改。 */
const EXPECTED: Array<{ key: SimulationStageCopyKey; zh: string; en: string }> = [
  { key: "noScenarioOnStage", zh: "台上没有场景：服务器回的是 NO_SCENARIO。先在产品里建一趟行程，或按下面的重置播一个演示场景。", en: "There is no scenario on stage (the server answered NO_SCENARIO). Create a trip in the product, or re-seed one below." },
  { key: "cursorStillReading", zh: "服务器游标还在读，读完才知道有没有可推进的活动。", en: "The server cursor is still being read." },
  { key: "executingButCursorEmpty", zh: "服务器说这趟在执行中，但游标是空的（没有任何活动在进行），所以这一步没有可推进的位置。", en: "The server says the journey is executing but the cursor is empty (no activity is in progress), so there is no position to advance from." },
  { key: "noActivePlanForReplan", zh: "这趟还没有 ACTIVE 计划（服务器没返回计划版本），重规划需要它。", en: "No ACTIVE plan on this journey (the server returned no plan version), and a replan needs one." },
  { key: "activityStatusStillReading", zh: "还在读这份计划里当前活动的状态。", en: "The current activity's status is still being read." },
  { key: "cursorOffPlanList", zh: "服务器给的当前活动不在这份计划的清单里，所以没有可执行的下一步。", en: "The cursor points at an activity that is not on this plan, so there is no next step to offer." },
  { key: "cityStillReading", zh: "还在读这趟行程属于哪座城。", en: "The journey's city is still being read." },
  { key: "serviceCatalogueStillReading", zh: "还在读这座城的服务目录（哪些地点挂着可下单的服务）。", en: "The city's service catalogue is still being read." },
  { key: "serviceWindowsBeingAsked", zh: "目录里有带着可下单服务的活动，正在逐个按它自己的时间问服务器那一段有没有时段。", en: "Some activities carry an orderable service; their windows are being asked of the server." },
  { key: "rowReset", zh: "重置到场景起点", en: "Re-seed the scenario" },
  { key: "resetNeedsServerSideToken", zh: "这一步会删掉整库（52 张表），现在还要服务器自己的环境变量里的令牌；浏览器拿不到它，也不该拿到。所以这里不给按——要重播种行程，请由运行服务器的人来做。", en: "This step deletes the whole library (52 tables) and now needs a token that lives in the server's own environment. A browser cannot hold that value and should not, so this is refused on every deployment -- re-seeding is done by whoever runs the server." },
  { key: "rowPrepare", zh: "准备舞台（生成并选定计划）", en: "Put a plan on the stage" },
  { key: "prepareAlreadyExecuting", zh: "服务器说这趟已经在执行中，不需要再准备一次。", en: "The server says this journey is already executing; preparing again is not the step." },
  { key: "bookNothingOrderable", zh: "服务器给的这份计划里没有可下单的活动，所以这里没有可建承诺的东西。", en: "The plan the server gave carries no activity that can be ordered, so there is nothing here to book." },
  { key: "rowStart", zh: "开始执行（真实 /start）", en: "Put the journey into execution" },
  { key: "startAlreadyExecuting", zh: "服务器说这趟已经在执行中，不需要再开始一次。", en: "The server says this journey is already executing." },
  { key: "startNoPlanOnStage", zh: "舞台上还没有计划（服务器回的 plan_version_id 是空的）。先按上面「准备舞台」，才有可开始的东西。", en: "No plan on the stage yet (the server's plan_version_id is empty). Put a plan on it first; that is what there is to start." },
  { key: "rowEvent", zh: "触发一次中断", en: "Raise a disruption" },
  { key: "rowReplan", zh: "请求重规划", en: "Ask for a replan" },
  { key: "replanNeedsDisruption", zh: "重规划要由一个中断触发（服务器要求 trigger_event_id）。先按上面「触发一次中断」。", en: "A replan needs a triggering event (the server requires trigger_event_id). Raise a disruption above first." },
  { key: "acceptNoProposal", zh: "服务器还没有给出方案（它回的列表是空的），所以这里没有可接受的东西。", en: "The server has not offered a proposal (its list is empty), so there is nothing to accept." },
  { key: "rejectNoProposal", zh: "服务器还没有给出方案（它回的列表是空的），所以这里没有可拒绝的东西。", en: "The server has not offered a proposal (its list is empty), so there is nothing to reject." },
  { key: "rowDegrade", zh: "提供方降级", en: "Degrade the provider" },
  { key: "rowRestore", zh: "提供方恢复", en: "Restore the provider" },
  { key: "previousActionStillRunning", zh: "上一个动作还没回来。", en: "The previous action is still running." },
];

const panel = readFileSync(PANEL, "utf-8");test("分母：这 25 枚是这一格的完整清单，且两臂都非空", () => {
  expect(EXPECTED.length).toBe(25);
  expect(new Set(EXPECTED.map((x) => x.key)).size).toBe(25);
  for (const x of EXPECTED) {
    const arms = simulationStagePair(x.key);
    expect(arms.zh.length).toBeGreaterThan(0);
    expect(arms.en.length).toBeGreaterThan(0);
  }
});

test("字典两侧都答得出，且逐字等于迁移前屏上那两句", () => {
  for (const x of EXPECTED) {
    expect(simulationStageCopy("zh-Hans", x.key)).toBe(x.zh);
    expect(simulationStageCopy("en", x.key)).toBe(x.en);
  }
});

test("选臂规则没动：zh 前缀取中文，其余一律取英文", () => {
  for (const x of EXPECTED) {
    expect(simulationStageCopy("zh", x.key)).toBe(x.zh);
    expect(simulationStageCopy("zh-TW", x.key)).toBe(x.zh);
    expect(simulationStageCopy("fr", x.key)).toBe(x.en);
    expect(simulationStageCopy("", x.key)).toBe(x.en);
  }
});

test("反控：这 25 句不再以内联成对的形状留在组件源码里", () => {
  for (const x of EXPECTED) {
    expect(panel.includes(`zh: "${x.zh}",`)).toBe(false);
    expect(panel.includes(`en: "${x.en}",`)).toBe(false);
  }
});

test("反控：组件里已经没有静态中英对内形状", () => {
  expect(panel.match(/^\s*zh: "/gm)).toBeNull();
});

test("组件确实改成走字典通道（不是删掉了事）", () => {
  expect(panel.includes('import { simulationStagePair } from "../../i18n/simulationStageCopy";')).toBe(true);
  const calls = panel.match(/\.\.\.simulationStagePair\("([A-Za-z0-9_]+)"\)/g) ?? [];
  expect(calls.length).toBe(25);
  for (const x of EXPECTED) {
    expect(calls.filter((c) => c.includes(`"${x.key}"`)).length).toBe(1);
  }
});
