# ORD-0439 · 多方案一屏对比 · 读数与没做到的部分

分支 `review/Q-ord0439-plan-ranking`；本文件与规格同一笔提交（那笔的 40 位在账本块里，写这里时还不存在）。
父尖（命令者点名的现尖）`8d038b21f09477b933cff3b1c7b09845c542373b`。

## 屏上读到的原话（无头 Chrome，zh-CN，页面是本车道自己的 `vite preview :4192`，不是 `npm run dev`）

取自本目录的 `RANK_READ_R1.json`（同一趟原始读数的副本，`panel` 段），那一趟有 21 份候选：

- 标题：把这趟能选的方案摆在一屏上比
- 副句：排序只用这个产品自己为每一版算得出的数。所有方案都一样的那一维照实列出来，但不用它分高下。
- 排序依据那句：**按这些维度排：预算。**（其余三维照实列在表头上、`data-comparable=false`，没被用来分高下）
- 四个表头与其 `data-comparable`：预算=true、步行时长=false、硬可用证据段数=false、受保护锚点=false
- 第一行四格：`方案 2` / `CNY 320.00`(value) / `没量到`(absent) / `9/56`(value) / `没标受保护项`(absent)
- 说明句：这一版 56 段里有 9 段的证据是闸门认可能当硬依据的，其余是 SYNTHETIC_DEFAULT。
- 屏上可点的按钮数：0（这一屏没有任何写操作）

## 四条臂各判什么，以及它被什么杀死

| 臂 | 判的是 | 反件（改的是产品源码，不是断言） | 结果 |
|---|---|---|---|
| P1 | 屏上维度集合 = 声明的四个；「按哪些维度排」只提名真分得开的 | `usedDims` → `RANK_DIMS`（把分不开的也宣布成依据） | killed，报错：分不开的「步行时长」被当成排序依据 |
| P2 | 载荷没有的那一维不许写成 0 | `walkCell` 的 absent 分支改成 `{kind:"value",number:0}` | killed，报错：rank-cell-walk 载荷里没有，屏上却当有值渲染：0 |
| P3 | 合成默认值不得被说成供应商结果 | 说明句改成「其余是供应商给的结果（{quality}）」 | killed，报错：把合成默认值说成了供应商结果 |
| P4 | 没有可比方案时只说空态，不摆排序家具 | `rows.length === 0` 守卫改成 `rows.length < 0` | killed，报错：没有可比方案时屏上没有那句实话 |

四枚反件全部 `restored_byte_identical=true`，最后再干净重建一次（rc=0）并把 4/4 重跑绿：
`stats: {'expected': 4, 'unexpected': 0, 'skipped': 0, 'flaky': 0, 'duration': 7737.964}`。

## 词表：四个维度都是我们自己算的，没有一个借来

- **预算** `cost` ← `plan_versions.total_cost_minor` + `currency`，住宿单价未知时走 `priceUnknown`，不补 0。
- **步行时长** `walk` ← 该版 `mobility_evidence_json` 里 `walking_min` 是数字的那些段之和；只加到部分段时格子里
  带 `partial` 标注，一段都没有则 `walkNotMeasured`。
- **硬可用证据段数** `evidence` ← 同一份 `mobility_evidence_json` 里 `fact_quality` 落在
  `backend/app/replanning/provider_snapshots.py:18` 的 `HARD_FEASIBLE_QUALITIES`（`EXPLICIT_FROZEN_FIXTURE` /
  `LIVE_PROVIDER_CAPTURE`）的段数 / 总段数。
- **受保护锚点** `protected` ← `activities[].protected` 是布尔的那些计一。

命令者转来的 mobility-facts 匹配结果里没有新的维度名进来；`score_breakdown` 的九个维度**故意没用**，
因为 `backend/app/services.py:682` 对旧行是拿一个聚合值（`aggregate = max(0.0, min(1.0, float(item.utility_score …`）
摊到九个维度上的，摊出来的数不能当分高下的依据。

## 没改善的部分（照实说）

1. **雨天替代这一维没上屏**：不是不想做，是没有任何 per-plan 字段可算。全仓能找到的只有
   `backend/app/replanning/mock_replan_engine.py:473` 的 `INDOOR_ALTERNATIVE`（一次 replan 的动作，不是一版方案的属性）、
   `V8Experience.tsx` 里的 `onRain`（UI 触发）和 per-leg 的 `weather_exposure`。为了有对比而 mock 一版，
   命令者已经禁止，所以这一维缺席。
2. **受保护锚点现在永远分不开**：真实载荷里 `activities[].protected` 全是 null，所以它只能以
   `没标受保护项`(absent) 出现，`data-comparable=false`。格子在，判定诚实，但它还不是一把尺。
3. **步行时长同样分不开**：`walking_min` 在 CNX-DEMO 的 mobility facts 里没被量到，屏上是 `没量到`。
   这一维有算法、没数据。
4. **证据那一维也分不开**：那一趟 21 份候选共用同一枚 mobility snapshot，`9/56` 每行都一样，
   所以 `硬可用证据段数=false`。目前只有「预算」真在分高下。
5. **这一屏没有对比之外的动作**：不能选中、不能接受、不能还原；`pressable=0` 是读数不是设计遗漏。
6. **P4 依赖封存演示那趟当下没有 CANDIDATE**：现在成立（`[('ACTIVE', 1), ('SUPERSEDED', 8)]`），一旦别的车道在那趟上生成候选，
   这条臂会 `test.skip` 并把份数写进原因里——它不会假装绿。
7. **没跑过的**：`playwright.config.ts` 只测了收集（456 tests in 108 files，四条臂具名在内），没有执行；
   后端整套 `--collect-only` 本回合没重跑，因为交付里 `backend/` 一个字节都没动。
