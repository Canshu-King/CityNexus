# ORD-0281 · 写腿期限 · 定形（判据 + 反例 + 射程）· HJ-P3 aad2d1f2

> 只出形状，不改产品字节；产码归 @B，`derived_result` 归 @红队。依据全部来自已发布读数与本轮现场（见 `O0281-SHAPE-2506_witness.json`）。

## 0. 先把机理钉准（否则反例咬不到承重的那处）

1. 期限常量与写腿豁免在同一文件：`frontend/src/lib/readDeadline.ts:15` `READ_DEADLINE_MS = 12_000`；同文件 `:43-45` 对非 GET/HEAD 直接 `return fetch(input, init)`。作者的自陈在 `:10-12`：**故意只覆盖读腿**，理由是"中止写腿时服务器可能还在收尾，那是幂等问题，本单不问"。
2. **更大一层在调用点**：写腿根本不进这个包装。`frontend/src` 实测 33 处裸 `fetch`，其中 **13 处是写**；带 `signal`（手动取消）的只有 **2** 处，带计时器的 **0** 处。⇒ 今天症状的承重处是**入口裸 fetch**，不是 `vb()` 那半个 `if`。只修 `readDeadline.ts` 的写分支**修不到这一格**（这条必须写进判据，否则 B 会绿错文件）。
3. 资产锚点（两枚都给，免争执）：`async function vb(` 在 `271706`，判决句 `if(r!=="GET"&&r!=="HEAD")return fetch(t,e);` 在 `271777`；本轮重算 char==byte（该点之前无多字节字符），当前在服的字节里同一对锚点是 `271707 / 271778`。
4. 运行时（两代同形）：写锁窗口内的写腿 `32286, 32328, 32335` ms（`c79e2b4`）与 `32379` ms（`dcae1bc9`），**客户端错误一律为 null**（是服务器答的，不是客户端掐的）；手动取消那发是 `7046` ms ⇒ `AbortError: signal is aborted without reason`。

## 1. 四枚必测格（每格：判据 / 反例 / 红态名）

**共同判据口径**：两侧同判——服务端字段（HTTP 状态、`error.message`、`error.code`、回执 `response_status`）与屏幕渲染文字（`innerText`，不读 data 属性）都用 `==`，配一枚"等值必须认"的正控与一枚标点漂移反控（沿用 ORD-0279 的判据自测三件）。verdict 一律从实测行派生，**不写 `PASS` 字面量**。时长是读数不是断言（Q25：`claim_kind=runtime_measured` 永不跨代继承）。

### T-a 期限内被服务器回答 ⇒ 不许出现期限文案
- 判据：写腿拿到服务器状态；渲染文本中不含期限句；若服务器给了句子，标签「服务器给出的原因」下的值必须 `==` 服务器 `error.message`。
- 正控：origin 50 ms 内答 200 ⇒ 正常文案，期限句出现即红。
- 红态名：`DEADLINE_TEXT_SHOWN_ON_TIME_ANSWER`。

### T-b 超过期限 ⇒ 客户端自处，且句子必须属于写腿
- 判据（三件同时成立）：
  (i) 等待由**客户端期限**结束，且与"用户点取消"可区分（不同错误名/不同 cause；读腿那套已有 `ReadDeadlineMissed` 的名字先例，写腿要自己的名字，不许复用读腿错误名）；
  (ii) 屏上句子具名"**服务端没在期限内回答**"并带常量值，**不得**复用读腿那句「后台连一个字也没回答」（写腿不能声称"什么都没发生"，因为副作用可能已经落地）；
  (iii) 不得冒充服务器原话：期限句**不许**占用标签「服务器给出的原因」；该标签只允许出现在服务器真的给了句子时。
- 反例 1（静默源站，接受连接不答）：期限内必须出现 (ii) 的句子，且不出现成功文案 ⇒ 拿不到即红 `WRITE_LEG_STILL_UNBOUNDED`。**今天这一格必然红**：13 处裸 fetch 写点里带计时器的是 0 处（§0-2）。
- 反例 2（期限后 1 ms 才答 200）：不许显示成功，也不许显示"服务器说失败"；只能进 T-d 的"结果未知"态。
- 反例 3（origin 答裸 500 / 21 B `text/plain`）：标签「服务器给出的原因」下若出现 `HTTP 500` ⇒ 仍按 ORD-0279 的 `CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON` 红（这一条与 0280 共享判据，**修复点不同文件**）。
- 红态名：`WRITE_LEG_STILL_UNBOUNDED` / `WRITE_DEADLINE_IMPERSONATES_SERVER`。

### T-c 常量可命名、可配置、可被反例咬
- 判据：期限值有**单一来源**（导出名），且写腿与读腿若各一枚必须两枚都命名；"把常量改小 ⇒ T-b 更早触发"必须**可执行**：以 `X` 与 `X/2` 两个值各跑一次，触发时刻随常量移动（判据只看"是否随常量移动"这一形状，不硬编码秒数）。
- 反例 1：只改读腿常量、写腿不变 ⇒ 红 `DEADLINE_NOT_APPLIED_TO_WRITE_LEGS`（这正是今天代码的形状）。
- 反例 2：常量在资产里出现两份内联值 ⇒ 红 `DEADLINE_CONSTANT_NOT_SINGLE_SOURCE`。
- 覆盖声明：本轮现场实测到一个不利事实——在静默源站上，`/v8/hub` 引导屏 25781 ms 内**没有**任何期限文案，输入目的地得到的是本地推导行；说明期限在读腿之间都不均匀（33 处裸 fetch 里也有读）。**所以 T-c 必须逐腿点名"哪条腿带常量"，不在射程内的要具名列出，不许沉默。**

### T-d 中止之后重发的语义 ⇒ 三态必居其一且被命名
- `REPLAYED_SERVER_ANSWER`：有耐久身份的腿（`plans/generate` 的 `plans.generate:<header>` / `plans.generate:cont:<mission>` 回执）重发 ⇒ 读回同一份，比正文时**先去 `trace_id`**（我 0279-X 已把这条判据基础钉过：整段正文比必假不等）。
- `FRESH_WRITE_WITH_KEY`：带新键、服务器给新答案 ⇒ 允许，但屏上不许把它写成"上一发的结果"。
- `UNKNOWN_OUTCOME_NOT_PRESENTED_AS_NONE`：无耐久身份的腿（`agent/commands`：不带键、实测不落回执、副作用是 mission INSERT）中止后 ⇒ 屏幕必须写"结果未知，先去核对，别当没发生"，并且**不许自动补发第二发**。
- 反例 1：无键路径中止后自动重发 ⇒ 库里出现第二条 mission 行 ⇒ 红 `DUPLICATE_SIDE_EFFECT_AFTER_ABORT`（用 SQL 判行数，不用页面文案判）。
- 反例 2：有键路径中止后重发，而回执已被别的进程填好 ⇒ 必须 replay，不许改写。这一支我 09-25 已跨进程验过会翻（`OBSERVED_CROSS_PROCESS_FLIP`，守卫在位 B rowcount=0 / 拆掉 B rowcount=1），所以 T-d 的"有键"一支今天就有地基，不依赖未落候选。
- 与 0274 的对表：0274 管**换代/在飞写收敛**（反例是"在飞即 reload 必红"），0281 管**一条写腿被期限结束之后的语义**（反例是上面两条）。两单共用"中止≠没发生"这一句屏上事实，但**修复点不同文件**，谁也不许把自己的绿算成对方的。

## 2. 射程（文件清单，只列不改）

- 机理与常量：`frontend/src/lib/readDeadline.ts`（`:15`、`:43-45`）。
- 期限文案的现有归属：`frontend/src/lib/failureAttribution.ts`（`:192` 判定、`:390-407` 读腿句子）。
- 写腿入口（本轮逐处实测，signal/timer 已标）：
  - `frontend/src/features\execution\LiveRecovery.tsx:225 POST signal=False timer=False`
  - `frontend/src/features\notifications\PushCapabilityCard.tsx:56 POST signal=False timer=False`
  - `frontend/src/features\planning\PlanComparison.tsx:88 POST signal=False timer=False`
  - `frontend/src/features\planning\PlanWithAiSheet.tsx:491 POST signal=True timer=False`
  - `frontend/src/features\planning\PlanWithAiSheet.tsx:598 POST signal=True timer=False`
  - `frontend/src/features\recovery\V14RecoveryTruthPanel.tsx:69 POST signal=False timer=False`
  - `frontend/src/features\simulation\simulationAdapter.ts:229 POST signal=False timer=False`
  - `frontend/src/features\simulation\simulationAdapter.ts:296 POST signal=False timer=False`
  - `frontend/src/features\simulation\simulationAdapter.ts:335 POST signal=False timer=False`
  - `frontend/src/features\simulation\simulationAdapter.ts:376 POST signal=False timer=False`
  - `frontend/src/features\stay\HotelsPanel.tsx:63 POST signal=False timer=False`
  - `frontend/src/features\stay\HotelsPanel.tsx:64 POST signal=False timer=False`
  - `frontend/src/features\stay\HotelsPanel.tsx:87 POST signal=False timer=False`
- 不在射程：读腿包装本身（ORD-0263 已闭）；服务端 `busy_timeout`/锁语义（ORD-0262 线）；`agent/commands` **缺幂等键**这件事的修复（建议单开一张——不然 T-d 的"无键路径"永远只能报"未知"，而那是另一件事的根因，不该被期限单顺手吞掉）。

## 3. 顺序与依赖（写给 @B 与号令者）

- 可先行：T-a/T-b/T-c（不依赖任何未落候选；T-b 的静默源站反例我这侧已有一次现场配置可复用）。
- 依赖已落地：T-d 的"有键重放"一支依赖 ORD-0272 的回执 + K8 守卫（已在 `dcae1bc9`）。
- 建议落地次序：**先让写腿带可命名期限（T-b/T-c），再把中止后的语义收成三态（T-d）**；反过来会先引入一个还没有身份支撑的"中止"，正读腿作者当年回避的那个坑。

## 4. 我这侧不做的

- 不改产品字节（本轮全部是只读导出 + 私有面/一次性库 + 现场探针）；不产码；不签 `derived_result`。
- 本轮未拿到的读数也照写：读腿期限文案**没有在引导屏上出现**（`NOT_OBTAINED_ON_THIS_SURFACE`），我不拿 ORD-0263 的旧收据冒充本轮现场。
