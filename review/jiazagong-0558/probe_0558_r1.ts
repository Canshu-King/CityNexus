// ORD-0558 加闸工 两语读数探针：把现尖那一代与改后那一代的同一枚函数各 bundle 一次、node 真跑。
// 用法（cwd frontend，node_modules 用 junction 接现有那份）：
//   cp <现尖字节> src/features/progress/_journeyProgress_before_r1.ts
//   node_modules/.bin/esbuild _probe_0558_r1.ts --bundle --platform=node --format=cjs --outfile=../probe_out.cjs
//   node ../probe_out.cjs
// 跑完把两枚临时文件删掉，src 下 .ts/.tsx 清单要回到与现尖逐字相同（156 行清单 diff 回空）。
import { progressContractCopy as after } from "./src/features/progress/journeyProgress";
import { progressContractCopy as before } from "./src/features/progress/_journeyProgress_before_r1";

function mk(o: any) {
  return {
    day_total_source: "server_temporal_shape",
    day_of_basis: "cursor_unreadable",
    day_total: null,
    day_of: null,
    completed_count: 0,
    settled_count: 0,
    planned_total: 0,
    ...o,
  };
}

const cases: Array<[string, any]> = [
  ["days=1", mk({ day_total: 1, completed_count: 0, planned_total: 3 })],
  ["days=2", mk({ day_total: 2, completed_count: 0, planned_total: 3 })],
  ["noneWalked planned=1", mk({ day_total: 3, day_of: 1, completed_count: 0, planned_total: 1 })],
  ["noneWalked planned=2", mk({ day_total: 3, day_of: 1, completed_count: 0, planned_total: 2 })],
  ["done 1/1", mk({ day_total: 3, day_of: 1, completed_count: 1, settled_count: 1, planned_total: 1 })],
  ["done 1/2", mk({ day_total: 3, day_of: 1, completed_count: 1, settled_count: 1, planned_total: 2 })],
  ["done 1/3 with 2 skipped", mk({ day_total: 3, day_of: 1, completed_count: 1, settled_count: 3, planned_total: 3 })],
];

for (const [label, p] of cases) {
  for (const zh of [true, false]) {
    const lang = zh ? "zh" : "en";
    console.log("CASE " + label + " | " + lang);
    console.log("  BEFORE: " + before(p as any, zh));
    console.log("  AFTER : " + after(p as any, zh));
    console.log("  SAME_AS_BEFORE: " + String(before(p as any, zh) === after(p as any, zh)));
  }
}
