## ORD-0209 @2026-09-22T14:2x+08 —— 仲裁已裁：**"使用封存的天津演示"必须只读寻址封存 journey**（EXP-HARNESS-005 的修法）

- id: ORD-0209
  to: e345b9d6
  priority: high
  if_head: 0cd697b
  order: |
    **裁决原文（总线 `5772122180` @ 14:26+08）：要。入口改成只读寻址封存 demo journey，不再 POST 新建 traveler/journey。**
    冻结边界（照录，逐条都要有证据）：
    1. 点击入口 ⇒ **只从 server-owned `/demo/scene` 取当前封存 `journey_id`**（**不要**在前端硬编码 `22222222…`）；
    2. ⇒ 选择／导航到该 journey；
    3. ⇒ **入口动作本身 0 新增 Traveler、0 新增 Journey**；
    4. ⇒ 不触发 `demo/reset`、不 reseed；
    5. ⇒ 若 `/demo/scene` 当前**没有**可用封存 journey：给**具名、可恢复**的 fail-closed 状态，
       **不得**退回到"静默 POST 新建"当兜底。
    仲裁同时钉住两条容易被绕过去的：
    - **不许**只把按钮文案改成"新建一份天津演示副本"来掩住现有行为（那是把谎言改成诚实，却没修污染）；
    - "入口只读"≠"整个 Demo 只读"：进入之后 advance／booking／interruption／replan 这些**显式 demo-owned 动作**
      继续受既有 demo ownership／R13／`PREVIEW_GUARDED` 约束，本单**不动**那一层。

    **现场已经具备服务端条件，我量过**（13:20 我恢复预览后端后打的是带鉴权的真请求）：
    `GET /api/v1/demo/scene` ⇒ 200，体里就是 `{"demo_mode": true, "journey_id": "22222222-…", "journey_status": "AC…"}`
    ⇒ 这单**应该是前端一笔改动**，不需要 C 新增端点；如果你发现需要，先在账本具名说明为什么。
    现在的错误链我已在 `0cd697b` 上逐跳核过（写进 EXP-HARNESS-005 的根因段）：
    `LocaleContext.tsx:699` 文案 → `JourneyTrialSetup.tsx:1165` `onClick → onUseTianjinDemo()` →
    `V8Experience.tsx:1261` `onUseTianjinDemo={createTianjinDemo}` → `:729` 体内只有
    `POST /api/v1/travelers`（+5）与 `POST /api/v1/journeys`（+13），**全链没有一次寻址封存 journey**。

    **验收形状（缺一项我就不签）**：
    - 一条断言读**渲染文字**（入口点完之后屏上出现的是那趟封存行程，而不是一份新行程）；
    - 一条**网络层计数**：整个入口点击期间 `POST /api/v1/travelers == 0` 且 `POST /api/v1/journeys == 0`
      （这是这条缺陷的承重位，光看 UI 变化证明不了"没偷偷建"）；
    - 一条无封存可用时的 fail-closed 读数（具名状态 + 人话 + **没有 POST**）；
    - 一个突变反例：**把实现改回 `POST` 新建，门必须红**（锚点用 `live_checks/mutation_anchor_guard.py`，
      它机械拒绝"0 命中"和"字节没变"两种假判定——今天差点骗过我的就是这两种）。
    复现率口径沿用 HARNESS：**6/6 次点击**都在建新的，所以改完请给"点 3 次 ⇒ 计数仍 0/0"的读数，而不是一次成功。
    ⚠ 顺手拆掉我自己刚才差点写下的一条**假因果**：HJ-P1 副本库里 journeys 从 31 涨到 38，
    **不能**算成这个入口造成的污染——它自己逐轮记了"建了几趟 ⇒ 行数差严格相等（+2/+2）"，那些增量是它**故意建的**。
    这个入口会偷偷建行的证据只有两条：HARNESS 的 6/6 次实测，和我在 `0cd697b` 上读到的调用链（只有两个 POST）。
    引用时请只引这两条。
  status: DISPATCHED@2026-09-22T14:2x+08 by 494abfd7（裁决＝仲裁 `5772122180`）

### 与两条待决的关系（免得车道互相等）
- **门口校验题（锚点解析不出来照样能建行程）** 我已按你的两栏问法发给仲裁（甲＝门口拒／乙＝允许建但强制归因），
  没回之前 D 只动 ② 里那条"入口不建"的，不去碰锚点校验。
- **偏好硬声明没接线**（`capabilities.py` 那几个 `add()` 从不传 severity）已给 C 第一步；
  "要不要听懂『走不快』"这种**扩词表**的问题我原样转给仲裁了，不替产品定。
