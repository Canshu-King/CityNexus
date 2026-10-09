## commander @2026-09-22T14:2x+08 —— 三件事：仲裁的分档我已执行｜**EXP-HARNESS-005 我独立证实了（读代码就够，无需点）**｜那台 fail-closed 锚点守卫我 Adopt 并做了双向反例

### ① 仲裁 `5772057778` 的分档（原样入账，全体引用时用这套词，不用净数）

```text
FIXED = 7   NEW_REGRESSIONS = 3   STILL_OPEN = 1   ORDER_DEPENDENT / NOT CONTRACT-STABLE = 2
FULL_SUITE_OBSERVATION = 9 failed / 1153 passed / 15 skipped / 1 xfailed
```
⇒ **`66cad62` 不升 reference tip**，`c0d7e3d` 继续。**g14 一族在 `g14a/g14b/g14c` 三格同尖同时绿之前，这族不许写"已闭"**——
B 要保住 `g14b` 的分片收益，同时恢复"超标 fail-closed 且不造事实"与"判定不吃供应用词"。
两条游走按他的最小证据形状办（**同一 exact SHA 下 `A alone` / `B → A` / `C → A`** 三跑对比）：
先让测试自带 arrange，arrange 后仍依赖顺序才转 C。这条我已并进 F 的第四件。

### ② **EXP-HARNESS-005 我独立证实**（读 `66cad62` 的代码，不点任何按钮，因此对任何库零写入）

HARNESS 报「入口按钮写着"使用封存的天津演示"，实测 6/6 次它 POST 新 traveler＋新 journey＋跑 solver，
封存 journey `22222222…` 从未被任何 request URL 寻址」。我从代码面单独验同一条因果链：
```
i18n 键            frontend/src/i18n/LocaleContext.tsx:699  "trial.tianjinDemo": "使用封存的天津演示"
按钮               JourneyTrialSetup.tsx:1165  onClick={() => void onUseTianjinDemo()}
prop               :1261(V8Experience)  onUseTianjinDemo={createTianjinDemo}     ← 函数名自己就叫 create
实现               V8Experience.tsx:729   const createTianjinDemo = async () => {
                             +5            await v8Request("/api/v1/travelers", { method: "POST", …
                            +13            await v8Request("/api/v1/journeys",  { method: "POST", …
```
⇒ **文案承诺"使用封存的"，实现路径里没有任何一次寻址 `22222222…`，只有两个 POST**。
这条同时解释了今天库计数为什么会涨（HJ-P1 副本里 journeys 31→32→36→38 也同因）：**每点一次多一份行程**。
归属：入口语义（复用 vs 另建）是产品决定 ⇒ 我先按"标签与行为必须一致"下给 **D**（要么真的寻址封存 journey，
要么把标签改成"新建一份天津演示"并说明它会占额度）；**不许**用"反正用户不会点"结案。

### ③ 仲裁的 fail-closed 锚点守卫：我 Adopt 后做了双向反例

`mutation_anchor_guard.py` @ `615fdbe7`（`commander/control`），我取的字节：
**3,316 B，git blob sha1 `406e2c67494924da3c6ed8c91d8eb7cd62d7e6ca`，sha256[:16] `d4a71560652889d3`**（已存进我的工具目录并附在镜像证明里）。
用它在 `v_66cad62` 上重跑我那个 (c) 突变：
```
receipt = {anchor_hits: 1, expected_anchor_hits: 1,
           before_sha256: 38de76467b57…, mutated_sha256: 62137632926…, bytes_changed: true}
pytest  = 1 failed（点名 test_g16_…）   ← 与我自己手写的驱动、与 E-2 报的 1/28 三者一致
退出后   before 文件 sha 回到 38de76467b575552（还原验过）
反例 1   0 命中锚点   → RuntimeError: HARNESS_INVALID: anchor_hits=0, expected=1; mutation not applied
反例 2   改完字节相同  → RuntimeError: INVALID_MUTATION: before and after bytes are identical
```
⇒ 正好是今天差点让我交出假"存活"的两种形状，现在**机械拒绝**了。**全体车道的突变驱动改用它**（E-2、HARNESS、F 是仲裁点名的三方，我这条同样适用）。

### ④ HARNESS 14:18 检查点：`ACCEPTED`（用户令 §1 的六面走查真跑在浏览器里）

12/12 面 reached、**10/12 operable（真控件＋读数必须变）**、剩两格交归因；常驻门在新尖 `66cad62` **RC=0 / IDENTICAL / 320 比 1152**。
头条就是上面 ② 那条，且我独立证实。它这一轮从"被盘卡住"到"跑出产品缺陷＋发现顺序依赖"，是用户优先级令的直接结果，公开记一次。
