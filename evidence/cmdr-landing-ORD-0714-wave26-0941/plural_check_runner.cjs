// 第廿六波那三行的单复数对账：用产品里那一枚真的 expandPluralMarkers（esbuild 从 src/lib/plural.ts
// 转出来的同一份代码），把字典里我刚写进去的三行原文喂给它，看 n=1/2/3 各渲染成什么。
// 字典原文不是手抄的——从工作树那枚 .tsx 里正则抠出来，抠不到就报错退出，绝不拿记忆里的句子测。
const fs = require("fs");
const path = require("path");

const plural = require(path.resolve("D:/moodle/_cmdr_fe_rev_1016/_plural.cjs"));
const LOC = "D:/moodle/_cmdr_ord0705_wt_1022/frontend/src/i18n/LocaleContext.tsx";
const src = fs.readFileSync(LOC, "utf8");

function dictValue(blockMarker, key) {
  const start = src.indexOf(blockMarker);
  if (start < 0) throw new Error("BLOCK_NOT_FOUND " + blockMarker);
  const end = src.indexOf("\n};", start);
  const block = src.slice(start, end);
  const re = new RegExp('^\\s*"' + key + '": "((?:[^"\\\\]|\\\\.)*)",?$', "m");
  const m = block.match(re);
  if (!m) throw new Error("KEY_NOT_FOUND " + key + " in " + blockMarker);
  return m[1].replace(/\\"/g, '"');
}

const enBlock = "const en: Dict = {";
const zhBlock = 'const zhCN: Dict = {';
const keys = ["today.stopsToday", "today.stopsAfterThis", "today.tripEndsNextStop"];
let out = [];
for (const k of keys) {
  const en = dictValue(enBlock, k);
  const zh = dictValue(zhBlock, k);
  for (const n of [1, 2, 3]) {
    const counted = plural.expandPluralMarkers(en, { n });
    const rendered = counted.replace(/\{(\w+)\}/g, (_, name) => String(n));
    const zhRendered = zh.replace(/\{(\w+)\}/g, (_, name) => String(n));
    out.push({ k, n, en: rendered, zh: zhRendered });
    console.log("%s n=%d | en: %s | zh: %s", k, n, rendered, zhRendered);
  }
}
const wrong = out.filter(r => r.k === "today.stopsToday" && r.n === 1 && r.en !== "1 stop today");
if (wrong.length) {
  console.log("CHECK: 单数那一支没有变成 1 stop today");
  process.exit(1);
}
if (out.some(r => r.en.includes("{plural:"))) {
  console.log("CHECK: 字典里留下了没展开的标记");
  process.exit(1);
}
console.log("VERDICT 三行都展开干净，英文单数走 1 stop、复数走 N stops，中文三档只差数字");
