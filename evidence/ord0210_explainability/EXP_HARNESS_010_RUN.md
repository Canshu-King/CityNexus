# EXP-HARNESS-010（实跑）· HARD 能力让一个候选消失了，而**没有任何一道门说明为什么**

这是我在账本 03:5x 那块里说"下一格不再等令"的那件。**条件成立**才跑：`4d9ceae` 上演示地点带无障碍证据
`3/16`（不再是我 00:58 记的 `0/16` ⇒ 当时跑必然空转）。

## 0 · 坐标与方法

| 项 | 值 |
| --- | --- |
| 树 | `4d9ceaee785e78fd25482f91d80e3f832aa3f684`，我的导出 `lab/snap_4d9ceae/backend`（`git archive` 单向；权威树 0 改动） |
| 解释器 | `D:\moodle\CityNexus\.venv\Scripts\python.exe` 3.12.14 |
| 调用面 | **全黑盒 HTTP 语义**，但**进程内 `TestClient`**：0 监听端口、0 对外请求、**不为探针改产品**、不做 DB 行手术 |
| 库 | 每次运行自己新建的一次性 SQLite（`hard_cap_probe_<pid>.db` / `doors_<pid>.db`），跑完删；**从未 `POST demo/reset`** |
| 四步 | `GET journeys/{id}/plans` → `POST …/plans/generate`（**控制臂**）→ `PUT travelers/{id}/capabilities`（一枚 HARD）→ `POST …/plans/generate`（**处理臂**） |
| 收据 | `hard_cap_probe_4d9ceae_0350.json`(v1) · `…_v2.json` · `…_luggage.json` · `…_luggage_v3.json` · **`…_luggage_v4.json`** · `hard_cap_luggage_repeat{1,2,3}.json` · `hard_cap_stepfree_repeat{1,2}.json` · `hard_cap_doors_full.json` |

## 1 · 结论（两臂各自的答案，5 个独立进程）

### 臂 1：`LARGE_LUGGAGE` = HARD（**只与 1 个地点冲突，不会掏空目录**——这才是能藏"静默丢失"的形状）

```
控制臂  HTTP 201  候选 3
处理臂  HTTP 201  候选 2          ← 少了一个
消失的那一枚（按内容具名，不是按 id）：
  planning_mode=balanced，活动序列含 `Design Library @ place-design-library`
  （`place-design-library` 正是演示数据里唯一 `luggage_accessible=false` 的地点）
处理臂响应里【控制臂没有】的归因信号：  []      ← 空
verdict = SILENT_CANDIDATE_LOSS   4/4 个独立进程（v4 + 3 次重复，每进程新库）
```

产品这一刀的**取舍是对的**：HARD 能力与地点证据冲突 ⇒ 含该地点的方案不可行 ⇒ 该被去掉。
**缺的不是判定，是解释**：客户端只看到"少了一枚候选"，看不到"因为 `place-design-library` 的
`luggage_accessible=false` 与你的 LARGE_LUGGAGE 硬要求冲突"。

### 臂 2：`STEP_FREE_REQUIRED` = HARD（掏空形状）

```
控制臂 201 / 3 候选 → 处理臂 HTTP 422，body.error.reason_code = CATALOG_INSUFFICIENT   3/3
verdict = REFUSED_WITH_NAMED_REASON（有具名机器码，不是静默）
但口径要正：那个码把成因写成"目录不足"，而真成因是这条 HARD 能力把可用候选掏空了 ——
     一次请求内用户看不到"是你的能力导致的"。这半条我不算缺陷，交给你判要不要提。
```

## 2 · 判据改过四轮，每一轮的洞都是我自己踩出来的（逐轮留收据，不覆盖）

| 轮 | 我原来的判法 | 为什么不能用 |
| --- | --- | --- |
| v1 | "候选数下降且无具名阻塞 ⇒ SILENT_CANDIDATE_LOSS"，比较 `int` 计数字段 | 这个端点回的是 **JSON 数组**，`int` 计数字段根本不存在 ⇒ `dropped` 恒 False，**任何未覆盖形状都会印成 `NO_EFFECT`**（我第一份收据就是这么个假绿） |
| v2 | 数 `n_items`；判"响应里出现 `blocker/reason/…` 词" | 词表在**控制臂也命中**（两边都有 `reason` 这个字），一个两臂同响的判据**分不出"有解释"和"没解释"** ⇒ 那一轮的 `HONEST_BLOCKER` 是判据太松造出来的 |
| v3 | 换成具名信号（`LUGGAGE_ACCESS_UNAVAILABLE` 等 + 被排除的地点 id） | 仍然只问"处理臂里有没有"——`place-design-library` 在**控制臂里也有**（同一地点在别的候选里也出现）⇒ 还是松 |
| **v4** | **差分**：信号只有"处理臂带、控制臂不带"才算归因；并给每枚候选按**内容**打指纹（mode + 活动 title/place_id；`plan_id` 每次 generate 都是新铸造的，不能当身份） | 这一版才咬得住。差分 = `[]` ⇒ `SILENT_CANDIDATE_LOSS` |

⇒ **同一份产品数据，四轮给出三个不同标签**；差别全在我的判据。我把四轮收据都留着发出去，
因为"最后那个词"单独看会让人以为我一上来就量对了。

## 3 · 在写"用户无处可知"之前，五道门全部搜完**完整响应体**（不是截断窗口）

第一版这里我只存了前 1,400 字符就去判"没有冲突文本"——**而 `conflicts` 那个键正好在被截掉的那一段里**。
那是我的量具缺陷，产出的正是最贵的一类假阴性。已改成：判定在**未截断的完整 body** 上算，
存盘副本才截断，并把每一项具名信号的**计数**连同差分一起写进收据（`hard_cap_doors_full2.json`）。

| 门 | HTTP | 完整长度 | 在完整 body 上搜到的具名归因信号 |
| --- | --- | --- | --- |
| A `PUT travelers/{id}/capabilities` | 200 | 3,914 | `conflicts` **×1** —— 位置是 `traveler_twin.conflicts`，值 **`[]`**（属于 twin 摘要，不是"这次写入与目录冲突"的答复）；能力本身列进 `summary.hard` |
| B `GET travelers/{id}/capabilities` | 200 | 1,229 | **无**（`reason_code/conflicts/excluded/unsatisfied/blocked_by/ACCESSIBILITY_*/LUGGAGE_ACCESS_UNAVAILABLE` 全 0） |
| C `GET journeys/{id}/plans` | 200 | 185,902 | 归因信号**全 0**；只有 `place-design-library` 作为**数据**出现 71 次 |
| D0 控制臂 `plans/generate` | 201 | 111,545 | 归因信号全 0；`place-design-library` 出现 **43** 次（数据） |
| D1 处理臂 `plans/generate` | 201 | 74,357 | 归因信号全 0；`place-design-library` 出现 **28** 次（数据，少了一份候选量） |

**差分（唯一有意义的问法）**：`处理臂有、控制臂没有` 的归因信号 = **`[]`**。

⇒ 结论可以是硬的：**这五道门里没有一处说明"为什么少了一枚候选"**；那枚地点 id 在响应里只是被规划的**数据**，
从来不是解释。全组里唯一带"冲突"形状的东西是 `traveler_twin.conflicts`，而它是空的。


## 4 · 建议单（我不改产品，编号请你挂）

**候选被硬能力过滤掉时，`POST plans/generate` 的响应应带具名归因**：至少
`{excluded_candidates: [{content 指纹或 plan 标识, reason_code: LUGGAGE_ACCESS_UNAVAILABLE, place_id, capability_code}]}`
一类的机器可读块；措辞层再决定给用户看哪一句。归属：`plans/generate` 的后端车道。
判据（我这边现成能跑的）：**v4 差分判据从 `SILENT_CANDIDATE_LOSS` 翻成 `HONEST_BLOCKER` 即绿**；
反向：把归因块删掉必须红。**不要为我的探针改产品**——这条我照令执行。

## 5 · 这格没覆盖什么（照例写清）

* 只有 `seed_demo` 的那一枚 journey/traveler；只测了 `LARGE_LUGGAGE`（不掏空）与 `STEP_FREE_REQUIRED`（掏空）两形；
  `STROLLER`、四个 SOFT 码未测。
* **没在手机那棵树（`53fe8e8`）上跑**——那棵树的契约与活线不同（词表三值 vs 四值），要单独一份，不合并。
* 演示库只有 3 个地点带证据，"消失的那一枚"依赖这 3 行的分布；**这不证明真数据下的分布**。
* 无 provider、无 AI、无对外端口；`_live.db`/`_preview.db` 本件**一次都没打开**。

## 6 · 现场

`lab/snap_4d9ceae` 与 91 份收据重启后完好；我今天的临时库都已删除（`hard_cap_probe_43972.db` 等按名删）。
`%TEMP%` 里仍有 95 个 `cnx_pytest_*` 目录——**我不按名字形状清扫共享目录**（我在那条上犯过一次）：
我只删自己收据点名的那些，剩下的归各自车道自清。

— HARNESS `d291c9dc`，2026-09-23（时间戳由 Python 生成为 +08）
