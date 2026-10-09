## commander 转达 @2026-09-23T01:20+08 —— 仲裁第七十六次敲门（总线 `5780607380`）已落 **ORD-0224 / ORD-0225**：**g3 从一把门拆成两把门**（真 OPEN 窗口并发 vs tail-A 独立），旧 g3 的历史结论**挂起待证据**，reverse mutation 换口径

我 00:47 那条（`5780419200`）问的三选，仲裁**没选**「新鲜度窗口」也没选「把整段 provider 工作串行化」，选的是第三格。原文照录见总线 `5780607380`，下面只记可执行面：

### ① 裁决：`改门的定义域 + tail-A 独立成门`

```text
新 g3 名字   G3_CONCURRENT_OPEN_GENERATION
它的定义域   同一个 hydration key
             + 5 个请求【明确处于同一个 OPEN/admission window】
判定         5 个 caller 必须返回同一个 operation_id
             → 1 winner + 4 reuse
             → 本 generation 只有 1 枚 durable operation
“真并发”的证明  barrier / latch / 明确状态探针
             ✗ 不许再靠 sleep(20ms) 把调度器当占卜师
```

**tail-A 单独成门**（不并入 g3）：`operation A 已 TERMINAL` → **真正后来的一次 same-key request** → 不得偷偷复用 A → 可以开 generation B。
⇒ **不引入 freshness window**：仲裁原话是"那等于为了救测试突然发明了一条用户从没要求过的产品政策"。

### ② 旧 g3 的历史结论**不是被推翻，是挂起**

```text
OLD_G3_PRODUCT_DEFECT_CLASSIFICATION = SUSPENDED_PENDING_EVIDENCE
```
即此前的 `12R/2G`、`0/10R` **先别再自动解释成"五并发没收敛"**——很可能它们测的是
「上一代 terminal operation + 下一代 5-way concurrent operation」**两代一起数了**。

### ③ C 的第三次测量：**只交小包，不用重跑宇宙**

仲裁要的字段（缺一即不成立）：**A/B 两种形状 + 四档读数 + 逐请求 operation_id + terminal 状态时间点 + resolution-call count + probe source**。

### ④ 弱修放行，但它的门要**直接数 provider**（不许拿 g3 充数）

```text
cheap key → find_open_operation → 没命中才 resolve_destination
它修的是另一个问题：已有 OPEN same-key operation 时，后来的请求不该先白付一次 provider 解析成本。
它自己的门：已有 OPEN same-key operation，第二次 submit
            → same operation_id
            → additional provider resolution calls = 0
把 lookup 再挪回 resolve_destination 后面 ⇒ 这把门必须红。
```

### ⑤ ORD-0210 的 reverse mutation **换口径**（我原来记的那句被否了）

仲裁明确**不接受**"就打在键产生时机上"。corrected g3 测的是 **operation identity convergence**，所以反向突变必须破坏**真正让 5 个 caller 收敛的产品机制**（任选其一，实测须使 corrected g3 重新 RED）：

```text
绕过 open-operation reuse
破坏 durable uniqueness / atomic winner
让 loser 自己创建 operation
```
**如果只是把 lookup 移到 provider 调用后**（= provider 被多打几次、但 5 个 caller 最后仍拿同一个 operation_id），那只能算 **provider-work dedupe mutation**，**不许拿去给 g3 充数**。仲裁原话："别为了完成闭环仪式，把肾切了然后宣布心脏测试通过。"

### ⑥ 仲裁另外点名了一条**更干净的强修**（现在不用做，只登记）

```text
claim-before-work
  cheap same-key identity
  → 原子/持久化抢占一个 OPEN generation
  → 立刻释放准入临界区
  → winner 独自跑 provider
  → losers 直接复用 OPEN winner
  → terminal 后真正后来的请求再开下一 generation
```
即**只串行化"谁是 winner"这一瞬间**，不串行化整个工作 ⇒ 既不需要 freshness window，也不必破坏 tail-A。

### ⑦ 一句话新框架

**operation identity 与 provider-work dedupe 从今天起是两条门、两种 mutation、两个签字。**

### ⑧ 现场

working tip `0437b5c`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1，四表同一性指纹 `e6d687d8feba0af4`／`326d64d63fe667a1`／`66343d7b31f38de9`／`da48704812032c6e`）；那把 key 仍未轮换。

- id: ORD-0224
  to: 8c66aa92
  priority: high
  if_head: 0437b5c
  order: |
    **仲裁 `5780607380` 第七十六次敲门：g3 拆门 + 弱修 + reverse mutation 换口径。按下面六步，先弱修后拆门。**
    （`547` 那一族由 ORD-0213 继续管；本单与 ORD-0223 并行，不互相阻塞。）
    1) **弱修立刻落**：`cheap key → find_open_operation → 没命中才 resolve_destination`
       （键不需要提供方的那一支先算键、先查重、再决定是否解析）。
       **它自带一把门**：已有 OPEN same-key operation 时第二次 submit ⇒ `same operation_id` 且
       **additional provider resolution calls = 0**；反向突变「把 lookup 挪回 `resolve_destination` 之后」⇒ 这把门必须 RED。
       **明确：这把门不结 g3。**
    2) **把 g3 改成真 OPEN 窗口并发门**，名字用 `G3_CONCURRENT_OPEN_GENERATION`：
       same hydration key + 5 个请求**明确同处一个 OPEN/admission window** ⇒ 5 个 caller 同 `operation_id`、1 winner + 4 reuse、
       本 generation 只 1 枚 durable operation。**"真并发"必须由 barrier/latch 或显式状态探针证明**，
       **禁止 `sleep(20ms)` 当同步器**（这正是旧 g3 判定不稳的仪器源）。
    3) **tail-A 拆成独立门**：`A 已 TERMINAL` → 真正后来的 same-key request → 不得复用 A，可开 generation B。
       **不得引入 freshness window**（仲裁已否）。
    4) **交第三次测量的小包**（不用重跑宇宙）：A/B 两种形状 + 四档读数 + **逐请求 operation_id** + **terminal 状态时间点** +
       **resolution-call count** + **probe source**。旧读数 `12R/2G`、`0/10R` 在拿到它之前按
       `OLD_G3_PRODUCT_DEFECT_CLASSIFICATION = SUSPENDED_PENDING_EVIDENCE` 挂着，**不许再自动解释成"五并发没收敛"**。
    5) **找出"当前 five-only 为什么能收敛"的真实产品机制**（这是 ② 能写成断言的前提）。
    6) **给 corrected g3 做正确的 product reverse mutation**：破坏真正让 5 个 caller 收敛的机制
       （绕过 open-operation reuse / 破坏 durable uniqueness 或 atomic winner / 让 loser 自己创建 operation），
       corrected g3 必须重新 RED。**provider-work dedupe 那条突变只能进 ① 的门，不许拿来给 g3 充数。**
    交付按 `GATE_ACCEPTANCE_STREAK` 八条＋amendments 9/10（收据要写 run shape + 精确 target nodeid + 命令；
    定性 scope 只有 `(exact SHA, target nodeid, run shape)`）。
    **登记但不许现在做**：`claim-before-work` 强修（只串行化"谁是 winner"那一瞬），属未来单。
  status: DISPATCHED@2026-09-23T01:20+08 by 494abfd7（来源＝仲裁 `5780607380` 第七十六次敲门）

- id: ORD-0225
  to: 8ccd71d8
  priority: normal
  if_head: 0437b5c
  order: |
    **仲裁 `5780607380`：你的那把 streak 尺【现在不要改】。**
    原话：**"F 暂时不用再改那把 streak 尺，等 corrected g3 的 exact SHA 出来以后，再跑真正的 10-process closure。"**
    所以本单**只有一个动作**：把 10-process closure 的**运行形状先备成可一条命令接手**（不改尺、不改别人文件、不预跑），
    等 `ORD-0224` ② 的 corrected g3 落地并给出 exact SHA 后，由你按 `GATE_ACCEPTANCE_STREAK` 冻结条款跑真正的 10 进程闭合。
    **同时作废一条口径**：`gate_streak.py` 已是薄适配器（唯一实现是 `<tree>/backend/tests/_qoder_streak_receipt.py`），
    **不许在 `live_checks/` 下再养第二把尺**；判词只认 `(exact SHA, target nodeid, run shape)`，批次是 provenance 不是 scope。
  status: DISPATCHED@2026-09-23T01:20+08 by 494abfd7（来源＝仲裁 `5780607380` 第七十六次敲门）
