import { pendingCopy, fillPending } from "../../frontend/src/features/pending/pendingSetCopy";

/* ORD-0558 单复数那一档 · 量名词的取数件。
   跑的是真模块、真字典、真 resolver：屏上的调用形制照抄 PendingSetPanel.tsx:97
   （fillPending(pendingCopy(locale, key), params)），参数名照面板自己传的取（:315 的 n、
   :456 的 planned 与 picked、:467 的 max），不是我这里另造的。

   用法（两代各跑一次，输出逐行落 count_read_r1.txt）：
     改后：npx esbuild --bundle --platform=node --format=cjs --outfile=out_after.cjs \
             review/liangmingci/p56_readouts/count_read_harness_r1.ts
           node out_after.cjs
     改前：把现尖那一代的该文件与 lib/plural.ts 按同样的目录层级另放一棵（字节逐字未改，
           用 git hash-object 与 git rev-parse 对拍过），再对那一棵跑同样两条命令。 */
const probes: Array<readonly [string, string, Record<string, string | number>]> = [
  ["en", "pending.count", { n: 1 }],
  ["en", "pending.count", { n: 2 }],
  ["en", "pending.batchLine", { planned: 1, picked: 3 }],
  ["en", "pending.batchLine", { planned: 2, picked: 3 }],
  ["en", "pending.blocked.SET_TOO_LARGE", { max: 1 }],
  ["en", "pending.blocked.SET_TOO_LARGE", { max: 20 }],
  ["zh-CN", "pending.count", { n: 1 }],
  ["zh-CN", "pending.count", { n: 2 }],
  ["zh-CN", "pending.batchLine", { planned: 1, picked: 3 }],
  ["zh-CN", "pending.blocked.SET_TOO_LARGE", { max: 20 }],
] as const;

for (const [locale, key, params] of probes) {
  const out = fillPending(pendingCopy(locale, key as never), params);
  console.log(`${locale} | ${key} | ${JSON.stringify(params)} | ${out}`);
}
