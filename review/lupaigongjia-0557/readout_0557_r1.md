# ORD-0557 路牌工甲 · RealCityDiscoveryPanel 那一枚内联双语搬进字典 · 读数件
# 枝 review/路牌工甲-0557-r1；起点 ee8b9c6bb299aac76d8ab969b84f7dfa5c3a173a（现取一次 ls-remote）

## 改了什么（三处，逐字）

1. `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx:407`
   - 改前：`{locale.startsWith("zh") ? "技术详情" : "Technical detail"}`
   - 改后：`{t("discovery.technicalDetail")}`
2. `frontend/src/i18n/LocaleContext.tsx:654`（英文半区，紧接 `discovery.defaultGoal` 之后）
   - 新增：`"discovery.technicalDetail": "Technical detail",`
3. `frontend/src/i18n/LocaleContext.tsx:1961`（中文半区，紧接同一枚兄弟键之后，两侧同序同位）
   - 新增：`"discovery.technicalDetail": "技术详情",`

键名与英文文案逐字取自草稿那一条：`_cn10_bldraft_1155.txt:210`（键 `discovery.technicalDetail`，英文 `Technical detail`）。中文文案取自该行代码里原有那句，不另写。

## 两语读数（搬动前后逐字对照，一次 python 现读）

- 改前那两句来自组件字面量：zh=`技术详情` en=`Technical detail`
- 改后那两句来自字典：en=`Technical detail`（行 654）、zh=`技术详情`（行 1961）
- 逐字相同：en=True zh=True —— 也就是说这次搬动不改屏上文案，只把文案的归属从组件里换到字典里。

## 闸与尺（命令原样、退出码）

- 全量类型闸：`node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit` → 退出码 0，错误 0 条（按 ORD-0560 那句只报这把）。
- 构建：`npm run build` → 退出码 0，built in 6.87s。
- 字典两侧对齐：他的尺 `_cmdr_dict_parity_tip_r1.py`（钉权威线，改不得）跑现尖回 TIP ee8b9c6bb2 / DICT_LINES 2681 / BOUNDS 2 en:8,zh:1356 / KEYS_TOTAL 1140 / KEYS_BOTH 1140 / KEYS_ONE_SIDED 0 / KEYS_MULTI 0。
- 同一判据的我方本地尺（本目录 `dict_parity_local_r1.py:1`）：
  - 跑现尖那枚文件 → 1140 / 1140 / 0 / 0，BOUNDS 与上面逐字相同 —— 先证明我这把尺与他的在同一枚字节上同值；
  - 跑我这枝 → KEYS_TOTAL 1141、KEYS_BOTH 1141、KEYS_ONE_SIDED 0、KEYS_MULTI 0，探针 `discovery.technicalDetail` 回 en=[654] zh=[1961]。
- 三元式余面：我这枝上该文件「两支各一条字面量、恰好一支含汉字」的命中行 0 行（一次 python 现读，改前是 1 行，即账上那一处）。

## 没做的那一格（具名，不糊）

- 屏上读数没取。原因：那个折叠层只在 `failureFacts` 非空时才渲染（条件在 `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx:404`），要真取屏读得跑起一次真会失败并带测量事实的发现请求；`frontend/e2e/` 全树对该折叠层的 testid `v13-discovery-technical-toggle` 现读 0 份命中（一次 grep 计数），所以没有现成夹具可借。我不拿假数据凑一张屏读，也不拿字典读数冒充屏读——上面那节明写它们是字典读数。
- 这一格若要补，给我一句：允许我在真后端上造一次「该城无封印回放、live 提供者失败」的发现请求（需要起后端与前端两枚服务，端口由你点，避免撞在工车道）。
