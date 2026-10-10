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
- 三元式余面这一格我只引「同一枚文件、同一把尺、改前与改后」这一条，并且先交代两件事：
  - 他的尺（`_bilingual_count_r1.py`）跑在他自己的集成仓里，我这枝那枚对象不在那棵树，我没有往别人的树里写东西（一次 `git ls-tree CODE_FAIL` 就是它报的错），所以那把尺的数留给落地门去跑。
  - 我另写了一把同判据的本地副本（本目录 `ternary_count_local_r1.py:1`），先做校准：同一枚现尖上他的尺印 `files=156 hits=318`，我的副本印 `files=17 hits=169` —— 不同值，所以我的副本任何全局数一律不引。
  - 副本只用于单文件两侧对照（`one_file_ternary_count_r1.py:1`）：改前那枚尖在该文件命中 1 处，逐字是第 407 行 `{locale.startsWith("zh") ? "技术详情" : "Technical detail"}`；改后我这枝命中 0 处，两臂都真出了读数（`both_arms_produced_readings: True`）。

## 没做的那一格（具名，不糊）

- 屏上读数没取。原因：那个折叠层只在 `failureFacts` 非空时才渲染（条件在 `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx:404`），要真取屏读得跑起一次真会失败并带测量事实的发现请求；`frontend/e2e/` 全树对该折叠层的 testid `v13-discovery-technical-toggle` 现读 0 份命中（一次 grep 计数），所以没有现成夹具可借。我不拿假数据凑一张屏读，也不拿字典读数冒充屏读——上面那节明写它们是字典读数。
- 这一格若要补，给我一句：允许我在真后端上造一次「该城无封印回放、live 提供者失败」的发现请求（需要起后端与前端两枚服务，端口由你点，避免撞在工车道）。

## 枝与回验
- 推枝命令原样 `git push origin HEAD:refs/heads/review/路牌工甲-0557-r1`，回验命令原样 `git ls-remote origin refs/heads/review/路牌工甲-0557-r1` 回 `783406a9d75b7a51dc0a2e689d1a2d469b7483ad`，与提交那笔代码时的 `git rev-parse HEAD` 逐字相同（一枚可 cat-file 回 commit）；本件自身入账后枝尖会再前进一笔（读数件那一笔），所以枝尖一律以 `ls-remote` 现读为准，不引本件里写过的数。
- 相对起点那枚尖，本枝逐字 numstat：`frontend/src/features/discovery/RealCityDiscoveryPanel.tsx` 1 行增 1 行删、`frontend/src/i18n/LocaleContext.tsx` 2 行增 0 行删、读数目录若干件；产品面改动共两枚文件。
