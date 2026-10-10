- id: ORD-0218
  to: d291c9dc
  priority: normal
  if_head: 56d20ec
  order: |
    **g5「AI no-op 必须说清是哪种 no-op」的可见性契约（仲裁 16:40 立单，极窄）。**
    它现在在固定形制下 **10/10 稳定红**，而且早先明确不在 C 的收口清单里；继续悬空只会永久污染 whole-file 读数。
    **第一步只做诊断，不许先改产品码、不许挑归属**：
    1. exact SHA ＋ run shape ＋ **逐 run 的目标节点 verdict**（不是整条命令的 exit——仲裁 16:40 的原话：容器命令红不能冒充目标节点红）；
    2. 打印**确切的失败断言**，以及它期望的产品行为是什么；
    3. 追一条链：缺的行为是 **outcome 发射层**、**API 投影层**、还是 **UI 消费层**；
    4. 追完再定归属，不许因为名字里有"AI"就默认塞给 C——若产品事实已存在、只是 UI 不消费，归 D；若 outcome/reason 根本没从后端产生，再归对应 backend writer。
    四条禁令不变：不许放宽门、不许 skip、不许改断言换绿、不许用措辞匹配绕过。
    交付形态：一页诊断（含上面四项）＋**一张建议单**（写清归谁、第一步是什么），单子由我签发，你别自己开 ORD 号。
  status: DISPATCHED@2026-09-22T17:5x+08 by 494abfd7（来源＝仲裁 `5773588112` 第六十二次敲门回执）

## commander 执行令（第四条）@2026-09-22T17:5x+08 —— streak **第 9/10 条冻结**；仲裁**纠正我一条分类**（g3 单门形不是 STABLE_RED）；**g5 立单 ORD-0218**；Qoder 崩溃 + 电脑重启后**12 条车道全部 cold**

### ① 冻结原文照录（来源＝总线 `5773588112` @16:40:22）

```text
GATE_ACCEPTANCE_STREAK amendment

9. RUN_SHAPE_IS_PART_OF_THE_RECEIPT
   Every streak receipt must name the exact run shape and command surface:
   - single-node
   - node-with-preceding-doors-in-one-process
   - whole-file
   It must also record the exact target node id(s), ordering, and command.

10. CLASSIFY_THE_TARGET_NODE_WITHIN_THE_SHAPE
    Classification is scoped to: (exact SHA, target node id, run shape).
    FLIP_WITHOUT_SHARED_STATE(<shape>) => the TARGET NODE itself has both GREEN and RED outcomes across fresh independent DB/process runs.
    STABLE_RED(<shape>)             => the TARGET NODE itself is RED in every run of that same shape.
    STABLE_GREEN(<shape>)           => the TARGET NODE itself is GREEN in every run of that same shape.
    Whole-command/file exit is not a proxy for the target node.
    A whole-file run that is RED because another node failed cannot classify the target node.
```

**他纠正我的那一句我先认下来**：我 16:1x 说"我 14 次那把严格说是 STABLE_RED(单门形)"——**错**。单门形里 1/10 绿、历史 2/14 绿，**目标节点自己两种结果都出现过** ⇒ 正确写法是 `FLIP_WITHOUT_SHARED_STATE(single-node)`。我把"红得多"当成了"恒红"，这正是他说的"拿容器命令的 exit 替目标节点定性"的同一类错。

**按他的口径重写当前读数（今后引用一律用这个版本）**：

```text
g3 / single-node:                              1 GREEN / 9 RED (HARNESS 10-run) ＋ 2 GREEN / 12 RED (Commander 14-run)
                                               => FLIP_WITHOUT_SHARED_STATE(single-node)
g3 / node-with-preceding-doors-in-one-process: 7 GREEN / 3 RED
                                               => FLIP_WITHOUT_SHARED_STATE(node-with-preceding-doors-in-one-process)
g3 / whole-file:                               命令 0/10 GREEN，但那是因为 g5 10/10 RED
                                               => g3 在该形制下 UNCLASSIFIED_IN_THIS_SHAPE（必须抽出 g3 的逐 run 节点判定）
g5 / whole-file:                               若 10 个 run 里 g5 自己每次都 RED
                                               => STABLE_RED(whole-file)
```

我的量具 `live_checks/gate_streak.py` 已经把 `--node` 与形制写进收据（第 9 条天然满足），但**第 10 条我还没做**：它现在只按进程 exit 判 green/red，**没有把目标节点的逐 run verdict 单独抽出来**。⇒ 我自己认领这条工具修正，改完在两向自检上重跑并贴读数（**这是量具，不是产品门**，不占车道名额）。

### ② g5 → ORD-0218（已下单，归 HARNESS `d291c9dc`）

仲裁立单，**第一步只做诊断、不挑归属**：exact SHA ＋ 形制 ＋ 逐 run 目标节点 verdict、确切失败断言、以及"缺的行为在 outcome 发射／API 投影／UI 消费 哪一层"的追踪；追完才定归属（产品事实已在、只是 UI 不消费 ⇒ 归 D；后端根本没产出 ⇒ 归对应 backend writer；**不许因为名字里有 AI 就默认塞给 C**）。我把它派给 HARNESS 是因为它 16:27 刚做完同形制的 30 进程读数、手上有现成量具，**不是**因为它该修。

### ③ 崩溃 + 重启后的现场（17:48 实测）

```text
Qoder 进程崩溃过一次（用户报），随后电脑重启；两次都把我 16:48 刚重建的预览链打没了
:4781 / :4782 / :8693 再次全部无监听
working tip 已走到 50b35e0（16:41，D 交 ORD-0216：向导提示按当前值重算＋预算对成双向门）—— 这是崩溃前就落盘的，不是崩溃造成
账本完好：2,851,957 B / 23,652 行 / 纯 LF；「重启恢复 @16:50」块与 `- id: ORD-0217` 都在
用户库（只读）：journeys 3 / travelers 3 / plan_versions 19 / commitments 1 / bookings 1 —— 与 16:29 读数逐项相同
```

**12 条车道全部 cold**（`8c66aa92` / `8ccd71d8` / `c01d72a3` / `e345b9d6` / `d2305848` / `d291c9dc` / `1a986a24` / `4e974ae5` / `aad2d1f2` / `d4b04a0f` / `9baacb24` / `5ea3bedc`）⇒ 17:5x 逐条发窄定位唤醒（各一行、不含任务正文）。
**预览链**：按用户 17:4x 的新口径（基建类活尽量转给车道/GPT），我**不再自动重建**；链当前是断的，用户手机此刻连不上——这一条我明说，不含糊。
