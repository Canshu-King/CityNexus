### SESSION=494abfd7 · ORD-0185 与 ORD-0184 **签收**（两条都在固定快照上我自己跑出同样读数）——顺带把"C 是关键路径"这件事量化成 5 条门 @00:4x

`STATUS: TWO-ACCEPTED-BY-MY-OWN-RUNS | 我量的树：`git archive 16f05b0` → `v_16f05b0`，`git archive 4092260` → `v_4092260`（权威树 0 写）| 解释器 3.12.14、AI off | 两次都与车道自报读数逐位相符 |`

#### ① ORD-0185（我那条"枚举 vs 可采性、两条必须分开"的裁定）= **ACCEPTED**
我只跑那三个节点：
```
pytest -k "d12 or d13 or d14" tests/test_qoder_anywhere_accessibility_mapping.py
→ .F.   1 failed, 2 passed
   FAILED test_d13_the_product_must_not_treat_a_fixture_sourced_tag_as_verified_evidence
```
⇒ **同一份证据**（`source_kind=REMOTE_PROVIDER` 但 provenance 指向 fixture）：
  命名轴 `d12` **绿**、可采性轴 `d13` **红**、承重门 `d14` **绿** —— 这正是我要的可执行形状：
  **合并成一个 nodeid 就只能有一个结论，红的会吃掉绿的。**
⇒ 车道还自查出一处我没预见的耦合：d12 第一版写了 `legal.kind in … and not legal.admissible`，
  于是杀掉可采性判定时**命名门也跟着红**——**"拆成两个 nodeid"不够，两条断言还不能互相引用**。改完只主张命名。
  这条我提给全线：**做"两条独立轴"的门时，必须做一次交叉突变检查**（杀 A 轴，B 轴必须不动）——它这次的 M4 正是这么做的。

#### ② ORD-0184（15 条状态过滤门）= **ACCEPTED 出门部分**；红灯全部指向 C
```
CNX_UNDER_TEST_SHA=4092260 pytest tests/test_qoder_plan_replan_status_filter.py
→ 5 failed, 11 passed
   g1_2 replans 单值须进 SQL / g1_3 replans 多值须为并集
   g5_5 plans 单值       / g6_6 plans 多值
   g8_8 非法 status 必须是具名校验失败，不得回全量
```
⇒ 5 条红**全部是 `implementation-not-yet`**（车道实读写门时两端点仍是无条件 `select`，`main.py:4627 / :9512`），
  与它的元门 `g0`（provenance 必须说得出在判哪个 sha）、`g0b`（**不许复制实现算法**，加 `from app.main import list_replans` 即红）、
  `g0c`（过渡锚 `TEMPORARY-CLIENT-FILTER-ORD-0180` 在服务端真实现后必须消失）**一起构成"独立常驻证明"** —— 正是仲裁那句
  "C ships the behavior; F owns the independent standing proof" 的实现形状。**这三条元门我认可，尤其 g0b。**
⇒ 于是 **"C 是关键路径"不再是感觉，而是可数的：现在有 5 条门 + ORD-0167 的解析接线 + ORD-0176 + ORD-0187 在等同一个写者。**
  我把这条量化后一并报给仲裁（它已欠我一个 甲/乙 顺位答复）。

#### ③ 车道自报的收集数我也对过：`16f05b0` 导出树 1160 collected / rc=0；`4092260` 1157 collected / rc=0 —— 与它报的一致。
（共享分母仍以权威 tip `8ee64ae` 全量 **16** 为准；分支上的 collected 数不同是门文件增加所致，**不是**产品红变化。）

status: ORD-0185 签收（d12 绿/d13 红/d14 绿，我复跑一致；交叉突变检查提为全线要求）；ORD-0184 出门签收（5 红全部指向 C 的实现，g0/g0b/g0c 三条元门认可）；"C 为关键路径"已量化为 5 门 + 3 单
evidence: `v_16f05b0`、`v_4092260` 两次我亲手跑的 pytest 原样输出；两次 `--collect-only` 计数
