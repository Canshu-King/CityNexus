/* 门牌号 ORD-0558 r3 两语读数探针：同一枚 catalogueCountSentence 两代字节，esbuild 打包后 node 真跑。
   入参照真出口形状：frontend/src/features/planning/catalogueReadback.ts:63 那枚函数收 readback 与 zh 两参，
   placeCount 由服务器回读那一格给；计数取零与一与二与三，另加一格 null（读不到那一臂）做反控。 */
import { catalogueCountSentence } from "../../frontend/src/features/planning/catalogueReadback";

const CASES: Array<[string, number | null]> = [
  ["null（门没答）", null],
  ["0", 0],
  ["1", 1],
  ["2", 2],
  ["3", 3],
];

for (const [label, count] of CASES) {
  for (const zh of [false, true]) {
    const line = catalogueCountSentence({ source: "server", placeCount: count } as never, zh);
    console.log(`${zh ? "zh-CN" : "en"} | placeCount=${label} | ${line}`);
  }
}
