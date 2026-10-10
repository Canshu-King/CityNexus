# ORD-0513 · 第三枚语言档 `de`：具名不可得（`NOT_AVAILABLE`），不是漏翻

裁语（CMDR 01:48 块第 5 段 / 02:35 块第 3 条）：`zh` 与 `en` 两枚成对交，第三枚 `de` 具名记
`NOT_AVAILABLE`，理由「第三档语言位不在本单范围」；`LocaleContext.tsx:4`、`LocaleContext.tsx:2133`
两行不开。本件把那一句理由写成可核对的形式。

## 为什么是「不可得」而不是「未翻译」

产品根本没有第三个语言位可填。现尖 `5a4cdbd26d4a58d6ed6b277480e766ac08b15ded` 上逐字查得（两处行号都是从那一枚 blob 里搜出来的，不是记的）：

- `frontend/src/i18n/LocaleContext.tsx:4` → `export type TripLocale = "en" | "zh-CN";`
- `frontend/src/i18n/LocaleContext.tsx:2212` → `const dictionaries: Record<TripLocale, Dict> = { en, "zh-CN": zhCN };`

第三枚臂的声明在全文件里搜两遍，两遍的计数都留在这里：宽松子串匹配（引号里的 `de`，或 `de:` 这两个字符）命中 4 行，逐行摊开各是被哪个词的尾巴碰上的 —— `frontend/src/i18n/LocaleContext.tsx:970` 撞上 `made:`；`frontend/src/i18n/LocaleContext.tsx:1050` 撞上 `code:`；`frontend/src/i18n/LocaleContext.tsx:1096` 撞上 `mode:`；`frontend/src/i18n/LocaleContext.tsx:1146` 撞上 `made:`。四行没有一行是词典臂。换成整词匹配（键位上的 `de`，或独立词 `de` 紧跟冒号）命中 0 行。只贴后一个数就是把结论当证据，所以两个都写。
真正承重的是上面那两行结构化事实：联合类型只有 `"en" | "zh-CN"`，注册表只有 `{ en, "zh-CN": zhCN }`。

所以本件的口径是：**zh+en 成对已交并实测；`de` = `NOT_AVAILABLE`**，理由与可核对的两行在此。
