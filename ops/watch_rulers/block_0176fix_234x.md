### SESSION=494abfd7 · ORD-0176 的**机制**我要更正：`solver_mode` 不是被 `payload()` 静默丢的——那里会抛具名 `ValueError`；丢发生在更早的 FastMCP 签名绑定。修法不变，**但要先做一次定位实验** @本机钟 23:4x

`STATUS: MY-MECHANISM-CLAIM-CORRECTED-AGAIN | 依据＝`agent-mcp/citynexus_mcp/schemas.py:24-72` 原文直读（权威树 HEAD）| 这是我今晚第三次"前提核得不干净"，同一毛病 |`

**我原来写的（ORD-0176 + 总线 `5762891922`/`5763094222` 里那句"MCP 白名单静默丢弃"）不准确：**
```python
SAFE_ARGUMENT_NAMES = frozenset({ ... "reason", "candidate_count", "city_code", "q", "category", ... })   # 无 solver_mode ✅ 这半成立
def payload(self):
    unknown = sorted(set(payload) - SAFE_ARGUMENT_NAMES)
    if unknown:
        raise ValueError(f"unknown CityNexus Agent arguments: {unknown}")      # ← 这里不是静默丢，是具名抛错
```
⇒ 所以 `solver_mode` 若能进到 `payload()`，调用方会拿到 **ValueError（具名失败）**，而不是"请求成功但参数没了"。
⇒ **"静默"只可能发生在更早的一步**：FastMCP 按工具签名绑定 arguments，**不在签名里的键根本到不了 `payload()`**。
  这与 Hermes 车道今天的读数一致（它写的是"两处各丢一次：MCP 层按签名丢 + 网关 422"），**我却在单里把机制写成 `:71` 丢弃**——机制说错了，结论方向没错。

**因此 ORD-0176 增加"第 0 步：先定位，别急着改"**
0. 做一次实验：通过 MCP 发一次带 `solver_mode="v2"` 的 `request_replan`，只观察三件——
   (a) 调用方拿到的是 `ValueError/422`（说明到了 `payload()`），还是 **200 成功**（说明在签名绑定处就没了）；
   (b) 网关侧收到的 body 里有没有 `solver_mode`；
   (c) 落库/返回的提案实际用哪个 solver（`deterministic` 还是 `v2`）。
   ⇒ 三种结论分别对应三种修法，**不许跳过这步直接改白名单**：
   - 若在签名处丢 ⇒ 要么把参数加进工具签名并透传，要么让它**在绑定处就具名拒绝**；
   - 若到 `payload()` 抛 ValueError ⇒ 现在是"响亮失败"，那要改的是**把它变成契约里明写的拒绝理由 + 屏幕/回执可读**，不是加白名单；
   - 若真的成功且被忽略 ⇒ 才是我原来说的那种静默，优先级最高。
1. 无论走哪条，**验收门不变**：两条 H10b 腿必须报告**同一个 effective `solver_mode`**（回显字段）；
   突变仍要做：把 `solver_mode` 从"允许/转发"路径摘掉而请求仍回 200 ⇒ 门必红。
2. 口径不变：**"Parameter discarded is not boundary honoured."**（仲裁冻结句）——
   但这句话现在挂在"实验之后确认存在丢弃"的前提上，**不再由我断言机制**。

**给自己的记条**：今晚三次同类（"两处算 identity"、"没审核入口"、"payload 静默丢弃"）都是同一个错：**拿一次命名尝试/一次 grep 的负面结果当能力普查**。
下次写"缺 X"的单，必须先答一句：**我是按名字找的，还是按能力找的？** 按名字找的，只能写成"未找到 X 命名的实现"。

status: ORD-0176 机制更正（ValueError 具名抛错 ≠ 静默丢弃；疑在 FastMCP 签名绑定处），新增"第 0 步定位实验"，门与口径不变
evidence: `agent-mcp/citynexus_mcp/schemas.py:24-72` 原文；Hermes 车道"两处各丢一次"的既有读数；本块三分支修法

#### 附：**账本的 `## ORDERS` 标题行被某次整体重写吃掉了，我已还原**（这是控制面事故，不是排版问题）
- 发现方式：我 23:36 的插入脚本 `assert anchor_count == 1` 当场失败；查 `grep` 发现**全文没有任何一行以 `## ORDERS` 开头**，
  而 139 条 `- id: ORD-####` 与 ORD-0150…0180 全部健在 ⇒ **不是内容丢失，是结构行被吞**。
- 影响面（这才是重点）：标题是**所有车道插入工具的锚点**。它一没，
  别人的写入会**静默 ABORT**——账本里已经能看到两处这种自述（`…按行首精确匹配取偏移…`、`匹配数变成 0 ⇒ 它当场 ABORT 而没有乱写`）。
  也就是说：这一段时间里，**可能有车道的交付登记根本没落进账本**，而它自己以为写了。
- 处置：我用"锚定唯一 `CLAIMED: ORD-0179 by dc19d662` 行 + 前插标题 + 逐字节可还原证明"恢复了标题（`restored. anchor count now: 1`），
  恢复后顺序正确：`## ORDERS（收件箱…）` → 车道 CLAIMED → `- id: ORD-0180`。
- **给全线的两条硬要求**（从本条起生效）：
  ① **不要改、不要重排、不要"顺手清理"任何共享章节标题行**（`## LANE_PROTOCOL` / `## DELIVERIES` / `## ORDERS`）——
     它们是机器锚点，不是文案；要改结构先在 ORDERS 里说一句，由我统一改。
  ② **插入前必须自证锚点命中数 == 1，命中 0 就停手并上报**（今晚至少两个工具做到了，这是对的）；
     命中 0 时**不要**退化成"append 到文件末尾"——那会把看板撕成两截。
