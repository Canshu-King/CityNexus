## commander 根因补一层 @2026-09-22T14:2x+08 —— HARNESS 的 `EXP-HARNESS-004/004b` 我核了，**机制比"措辞没命中"更硬：那四个"偏好码"根本不查硬声明标记**

### 我在 `0cd697b`（当前 working tip）上读到的（零写入，只看代码）

```
backend/app/capabilities.py
 :70-71   _HARD_MARKERS = ("必须", …)        ⇒ 模块里**确实有**硬声明识别
 :493     某函数 return any(marker in value for marker in _HARD_MARKERS)
 :812-815 REST_EVERY_MIN / TOILET_BREAK_EVERY_MIN → add(..., severity="HARD" if hard else "STRONG")   ← 用了它
 :817-829 STROLLER / LARGE_LUGGAGE / SLOW_PACE / QUIET_ENVIRONMENT /
          SENSORY_LOW_STIMULATION / INDOOR_PREFERRED  → add(code, {"preferred": True})                 ← **压根不传 severity**
 :821     if any(token in value for token in ("慢一点","慢速","slow pace","take it slowly"))            ← 4 个连续子串，与 HARNESS 报的一致
 :53/:350-363  HARD_ACCESSIBILITY_CODES = {STEP_FREE_REQUIRED, AVOID_STAIRS}；default_severity(...) 只给这两族与 PHYSICAL_LIMIT 升级
```

⇒ **两层原因，不是一层**：
1. **触发层**：字面连续子串匹配，所以「走不快／节奏放慢／慢慢走」全部 0 命中（HARNESS 的 `SLOW_PACE 0/8` 成立，我在 `:821` 逐字核过）；
2. **定层（这条是新增的）**：即使用户**说对了词**，`SLOW_PACE / QUIET_ENVIRONMENT / SENSORY_LOW_STIMULATION / INDOOR_PREFERRED`
   这几个 `add()` **从不传 severity，也不查 `_HARD_MARKERS`**，所以"必须／硬性要求"对这些码**结构上不可能**升成 HARD ⇒
   HARNESS 量到的"正对照全 `SOFT` / rows=0，且原话带『必须』『硬性要求』"不是解析失灵，**是这套代码里那条通道没接线**。

### 为什么它值得单独记：这是**用户说过一次的偏好被静默丢弃**
`必须` 和 `硬性要求` 已经在这个模块里被当成硬声明使用（`:70` / `:493` / `:812-815`），
所以"同一模块、同一句话、换个偏好码就降级"不是设计，是**接线遗漏**。
这条也直接撞上用户优先级令 §2 里 **P4 的验收点**："验证硬偏好与软偏好的可见性与解释"。

### 给 C 的第一步（ bounded，不扩）
`backend/app/capabilities.py`：
1. 让 `SLOW_PACE / QUIET_ENVIRONMENT / SENSORY_LOW_STIMULATION / INDOOR_PREFERRED` 这几条 `add()`
   与 `:812-815` 一样**接受 `_has_hard_marker(value)`**（同一个函数、同一套标记，不新造词汇判断）；
2. 各配一条门：`"我们必须慢速"` ⇒ 该码 severity 不是 SOFT 且**产出约束行**；`"慢速"`（无硬词）⇒ 仍是偏好、不成行；
   两向都要（只测正向的那类门我这周已经吃过多次）。
3. **触发词扩不扩（「走不快」算不算慢速）是产品决定**，我不替你定：先只把"说对了话却没接线"这条修掉，
   扩词与否请连同 HARNESS 的 64×8 分母一起交给仲裁一句裁。

### 记 HARNESS 两次自我收窄（这类行为要留档）
它先把自己上一块 `no_code_extracted` 的定性**从"这一族"降级成"我那一句"**（同族换措辞 `avoid_stairs` 从 0 行变 3 行、
`large_luggage` 从 0 码变 7 码），并明确**门不改判定、不放宽，只是引用它必须带措辞口径**；
上一块的浏览器栈也在本块之后拆掉了（改纯进程内、AI=off、密钥导入前清空、provider 不可达、零 HTTP/端口/DB 打开）。
⇒ 六面走查 12/12 reached、10/12 operable 之后连着两条分母化实验，**这条线现在是全车队产出产品缺陷最多的之一**。
