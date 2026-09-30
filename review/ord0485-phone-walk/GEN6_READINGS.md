# ORD-0485 r4/r5 -- 现尖 0989713aa687b97f4cd40bae009a6ce493425a4b 读数单

生成 `2026-10-01T02:43:23.819654+08:00`。本代全部重量，无跨代折算。

## 一、两面的产物身份

| 面 | 入口资产 | 打包字节数 | 打包本机字节 sha256 前缀 | 服务字节=磁盘字节 | tsc check | tsc all | build |
|---|---|---|---|---|---|---|---|
| TIP_0989713a | index-DaHdgt6W.js | 1547460 | 5311bae9cf7a4075 | True | 0 | 0 | 0 |
| O0485_R5 | index-C3-5f0ll.js | 1547615 | 81bfda0ff8b14b97 | True | 0 | 0 | 0 |

本机字节 sha256，不是 git 物件，不可 cat-file。第三证（访问日志）`NOT_AVAILABLE_BY_CMDR`：`vite preview` 不往本车道控制的日志里写请求行；两面各实测一次，件 `gen6_walk_r1.json`。

## 二、词汇清点（本代两枚各一件）

| 代 | en 枚 | zhCN 枚 | 引用键 枚 | 两表都缺 枚 | 缺的键 | 字典本机字节 sha256 前缀 |
|---|---|---|---|---|---|---|
| TIP_0989713a | 934 | 934 | 730 | 2 | exec.state.notStarted, poiImport.channelLocal | 188fc4a04383e0c8 |
| O0485_R5 | 936 | 936 | 730 | 0 | 无 | 8ca451653ea3395a |

两本字典字节不同：True。

## 三、25 面走查与词汇臂（本代）

- TIP_0989713a：屏 25 面，pageerror 0，机词命中 0 枚；词汇臂退出 1，1 passed (2.6s)，红臂 ord0485-1-the-import-pill-says-a-word-not-a-key
    判语：Error: e2e/qoder-ord0485-phone-words.spec.ts :: ord0485-1 — the pill fell back to the dictionary key: poiImport.channelLocal
- O0485_R5：屏 25 面，pageerror 0，机词命中 0 枚；词汇臂退出 0，2 passed (2.2s)，红臂 无
    判语：e2e/qoder-ord0485-phone-words.spec.ts :: ord0485-2 — settled after 1000 ms of waiting for the plan read

## 四、重切状态（逐枚比字节，不按血缘）

- 我这枚候选提交 `0989713aa687b97f4cd40bae009a6ce493425a4b`（`git rev-parse lane/ord0485-r5` 现读）里 `frontend/src/i18n/LocaleContext.tsx` 的 blob 是 `83df88df16771ada15e7cb36fa0745b72163ed0e`。
- 我切它时那枚基座 `0989713aa687b97f4cd40bae009a6ce493425a4b` 上同一文件是 `83df88df16771ada15e7cb36fa0745b72163ed0e`；号令者下一次落地时读到的现尖 `7862c6de5565c02c20ec2dccaa9da18960603e06` 上仍是 `83df88df16771ada15e7cb36fa0745b72163ed0e`——两枚同一 blob，所以逐枚比字节的结果是合得上、不需要再重切。
- 只读预测 `git merge-tree --write-tree 7862c6de5565c02c20ec2dccaa9da18960603e06 0989713aa687b97f4cd40bae009a6ce493425a4b` 的预测树是 `a0d9cbecfff67edc75e2ba2e8853d6f65881e48e`，从那枚树里把同一文件取回来再数是 `83df88df16771ada15e7cb36fa0745b72163ed0e`，与我候选那枚逐字节同一枚：True。
- 产品写集只有 4 行：`git diff --numstat 0989713aa687b97f4cd40bae009a6ce493425a4b 0989713aa687b97f4cd40bae009a6ce493425a4b -- frontend/src/i18n/LocaleContext.tsx` = 0。

