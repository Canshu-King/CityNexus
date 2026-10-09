### commander 亲测 @2026-09-21 20:4x —— 把 ORD-0152 从"AI 读错预算"**改成代码级定位**：那个 0 不是模型给的，是**行程上下文缺行时产品自己写死的默认值**（`stay_budget=0`、`party_size=1`），并且**被原样送去问供应商**

我读的是 `53fe8e8..e9efec6` 都一样的后端（`git diff --name-only 53fe8e8 e9efec6 -- backend/` 行数 = 0）：
- `app/stay_mobility.py:159-176 _context()`：当这趟行程**没有 `JourneyTripContext` 行**时，代码**就地造一行**，
  写死 `party_size=1`、`occupancy={"adults":1}`、**`stay_budget_amount_minor=0`**（`stay_budget_currency` 才用行程的）；
- 列本身也带 0 默认：`app/db/models.py:801 stay_budget_amount_minor: default=0, server_default="0"`；
  另两处同样写 0：`stay_mobility.py:169`、`app/operations/v9.py:1137`；
- 然后 `app/stay_mobility.py:1774-1780` 把这个上下文**原样发进供应商请求**：`trip.stay_budget.amount_minor = 0`、`party_size = 1`。
- 硬预算门在 `app/services.py:1567`（`total_cost > journey.budget_amount_minor` ⇒ 拒绝）与
  `services.py:1045`（`budget_fit` 用 `max(1, budget)`）⇒ **一旦"住宿预算=0"进了请求，供应商必然 `NO_OFFERS_FROM_PROVIDER`**
  （HJ-P1/P4 两条"住宿 top_k=[]"就是这个形状），而屏幕回头说"你去调整预算"。

**所以定性改了**：**不是"AI 把预算读成 0"，是"产品在缺信息时凭空补了一个 0 和 1 个人"**。
用户明写"我们两个人…别超过一千六百块"，一旦上下文行不存在，产品就按**1 个人、住宿预算 ¥0**去问世界，
再把问不到结果的锅甩回用户。**这条同时违反 R7（同一确定性内核）与"provenance 必须诚实"**：
一个凭空造出来的事实没有任何来源，却决定了候选与拒绝。

**我据此给 C 的硬要求**（原文已发消息，单子里 ORD-0152 范围按本块扩大）：
① **缺上下文不许补 0/补 1**：`party_size`、`occupancy`、`stay_budget` **一律从 Journey 已有事实派生**
  （Journey 有 `budget_amount_minor`/`budget_currency`；人数若真不知道，就**具名要求补充**，不是猜）；
② 供应商请求里的 `stay_budget.amount_minor == 0` 必须是**不可能状态**：要么用行程预算，要么根本不发这次请求并给具名原因；
③ 门：(a) 建行程时写"2 人 / ¥1600" ⇒ 上下文与供应商请求里必须是 2 与 160000（minor），**不得出现 0/1**；
  (b) 上下文缺失路径单测必须断言"没有凭空 0"；(c) 一条杀得掉的突变（把默认改回 0 必须红）；
④ 复现不出就交"复现不出 + 分母"（sha/端口/库/解释器/输入原话/请求序列 + 供应商请求体）。
