/* 门牌号 ORD-0558 的两语读数探针：同一枚 pendingSetCopy.ts 两代字节，esbuild 打包后 node 真跑。
   入参照产品调用点给：frontend/src/features/pending/PendingSetPanel.tsx:315 传 {n}、:456 传 {planned,picked}，
   计数取 1 与 2 与 3 三档；未改的 pending.receipt 那枚一起打，作为「本批没碰的面逐字节未变」的对照。 */
import { pendingCopy, fillPending } from "../../frontend/src/features/pending/pendingSetCopy";

const KEYS: string[] = [
  "pending.count",
  "pending.batchLine",
  "pending.blocked.SET_TOO_LARGE",
  "pending.receipt",
];

for (const locale of ["zh-CN", "en"]) {
  for (const n of [1, 2, 3]) {
    const params: Record<string, string | number> = {
      n,
      planned: n,
      picked: n,
      max: n,
      days: n,
      stops: n,
      version: "v7",
    };
    for (const key of KEYS) {
      const line = fillPending(pendingCopy(locale, key as never), params);
      console.log(`${locale} | n=${n} | ${key} | ${line}`);
    }
  }
}
