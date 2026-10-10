## commander 转达 @2026-09-23T03:15+08 —— 仲裁三条（`5782298826` ＋ `5782328456`）：**②③ 正式签关闭**；**跨进程必须补、Y3 也要杀一次跨进程门**；`calls=5` 拆成独立单 `PROVIDER_WORK_COALESCING`；**ORD-0237 只留"真取消"一条路**；泄露 key 切成 **credential epoch**

### ① ORD-0220②③：**它独立复核后正式签 `CLOSED(FIXED_IN_GENERATION)`**

它直接读 `commander/control` 的 blob 并核了 raw fields：三份权威 replication 收据（`ui3a b0eabb67ebc7a0ba` / `ui3b f9677d9e1548ea38` / `ui3c c85caa2bcc129c43`，各 2,249 B）、`generation_server_map.json 63add3bb3712a69e`(5,833 B)、勘误 v3 `c3bd975b960a1c9f`(7,160 B)：
```text
ui3a/ui3b/ui3c  scrollY=652 / hintY=572 / inView=true（三份一致）
三进程 PID 各不同；三份 base 分别 :8781/:8782/:8783
三份 served_bundle 都是 index-DtQ86lsQ.js / 1,231,985 B / sha256 cf3a08108ffba413…
⇒ 与它先前签过的 deployed current bundle 同一字节身份
②  三份都读到 D_afterFixingField.liveRegionText == ''
状态：ORD-0220② CLOSED(FIXED_IN_GENERATION) ｜ ORD-0220③ CLOSED(FIXED_IN_GENERATION) ｜ REAL_PHONE_GATE still OPEN
```

### ② 我的三条口径问题，它的答复

```text
跨进程      → 【必须补】。要 G3_XPROC_LOSER_READBACK；10/10 fresh cross-process；并且【Y3 也要杀一次跨进程门】
g3 的杀手   → 【只要 Y3 这一种真实杀手】（实测 A 与 B/C 互为冗余、单一突变杀不掉 g3 这件事它接受）
calls=5     → 【不是 correctness blocker】：identity 正确、工作没合流；会浪费额度/延迟/触发 rate limit
              ⇒ 顺序冻结：
                FIRST  corrected g3 + G3_XPROC_LOSER_READBACK（10/10 fresh cross-process，Y3 杀一次跨进程门）
                       ⇒ identity / ORD-0210 closure
                THEN   separate ticket  PROVIDER_WORK_COALESCING
                       cold 5-way same key：provider resolution calls == 1 / operation ids == 1 /
                       tail-A terminal -> new generation unchanged / 反向突变只杀 coalescing 门
```
**为什么现在不立刻强修（它的理由，我照录）**：我们刚把 identity 机制收敛到 B/C，且还差跨进程这一格；此时改成 `claim-before-work` 会**移动正在验的事务机制**——"终点线还没拍照先重铺跑道"。
强修方向仍是 **claim-before-work / short durable admission claim**：只原子决定 winner，winner 才做 provider work，losers 复用 OPEN claim；**不要把 provider 整段锁进临界区，更不要引入 freshness window**。
**升级条件**：若后续量到 provider resolver 有**计费副作用 / 不可幂等写 / 严格 rate-limit 会让请求失败**，再把这条 gap 升为 blocker；按现读数**先独立排队**。

### ③ ORD-0237 被它收窄成**一条路**

它冻的验收形状：
```text
B. after-send / in-flight cancel
   -> server 收到针对 exact run/mission 的取消
   -> 终态变成 CANCELLED（或等价的显式取消态）
   -> 该 run 之后【不得再有任何产品步骤落库 plan/result】
C. race：cancel 到达前 run 已终态
   -> 报 ALREADY_FINISHED / 真实终态，【不许撒谎改标成 CANCELLED】
D. 重开 / 硬刷新
   -> 被取消的 run 仍可被找到（以"已取消"出现），不得静默消失
E. 幂等
   -> 重复取消不产生新工作 / 重复副作用
F. 3 个时序臂（early / middle / late in-flight）语义一致
G. 反向突变：移除/忽略 server-side 取消交接 ⇒ 取消门必须 RED
```
**实现注意（照录）**：**不许"abort 当前 POST 然后祈祷 server 也停了"**——取消必须有**可寻址的 server-side 身份**（mission/run/request token）。若点击发生在客户端还没拿到 mission id 的窗口，就需要 **request correlation / idempotency identity**，或保留响应通道拿到 id 后再兑现 `cancel_requested`；否则最危险的 race 仍然开着。
⇒ **我 ORD-0237 里那个 (B)"明说只关界面"被否**：**"改文案 ＋ 结果继续静默丢失"不算第二个合法选项**。只有产品明确改成**后台任务模型**才允许另一条路，而那也要求该 run 在重开/Agent 页可找回并最终展示结果。

### ④ 泄露 key：正式切成 **credential epoch**（不再混分母）

```text
AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED
release-grade AI availability verdict = BLOCKED
今夜 6 趟保留为诊断样本（其中 3 趟 FAILED_EXTERNAL）⇒ 任何"AI 腿全通"都不成立
轮换后开新 epoch：AI_CREDENTIAL_EPOCH = ROTATED_<timestamp>
  从 0 重新计 release-grade AI samples；旧 epoch 只留历史诊断，不给新环境背锅、也不让新环境替旧失败洗白
安全边界：已知泄露 credential 【不应再被用于后续 release-grade 测试】；轮换前 AI 实跑最多记
        EXTERNAL_ENV_UNTRUSTED / OBSERVATION_ONLY；能不用就停用
```

### ⑤ 它对本轮签字的限度（我照实记）

它说：我 03:02 那块给了机制读数，但它在 `commander/control` 当前可读 tree 里**还没找到 ORD-0224 / `f92f9e9` / `50d1c4d` 的权威 evidence 坐标** ⇒ **它裁的是关闭政策与验收形状，不冒充已外审六步包**。要签只需发布：
```text
corrected g3 source/patch coordinate ｜ w1/tail-A/xproc receipts ｜ Y1a/Y3 mutation receipt
10-run cross-process receipt ｜ exact source/test SHA
```
⇒ **C 那六步目前只在本地/账本里，还没有外审坐标** —— 这是我的派单缺口，已在下一条里向 C 要。

### ⑥ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；那把 key 仍未轮换（**且已升格为 epoch 问题**）。
