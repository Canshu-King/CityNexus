## commander 验收 @2026-09-23T02:08+08 —— **B 找到 C 路：静默丢失的具名原因可以落在一条「前端已经在调」的读取面上，`main.py` 一行都不用动**；F 交 ORD-0225（我据此修了自己适配器的两个缺陷）

### ① B `c01d72a3` 的 ORD-0219③ 落点（我签，这是本轮最好的 C 路证据）

```text
读路径   GET /api/v1/journeys/{journey_id}/agent-feed
         app/main.py:6709（路由）→ :6716（审计查询）→ _audit_projection app/main.py:6619
         兜底分支 else: event_type = action  ⇒ 未知 action 名原样带出，不需扩白名单
         返回值带 "facts": after（:6699）
前端已在调 frontend/src/api/citynexus.ts:855 getAgentFeed
         main.tsx:213（journey 载入）与 main.tsx:336 refreshAuthoritativeFeed → setAgentFeed(feed.events)
         摄入处不按 event_type 过滤
备选读取面 GET .../history（main.py:6600）、.../reflect（main.py:6729，前端 citynexus.ts:1014 也在调）
```
⇒ **公共读取面本来就在那儿** ⇒ 那 2 行 `main.py` header 改动**不需要**，B 只准备不落地是对的（不为一个不需要的东西留半成品）。**这条把我 01:48 的分裂口径从"断路"改回"可闭环"**：`API_LEVEL_NAMED` 不必经过 `main.py`。

**定稿口径（照收）**：提交 `a96fabf`（2 files +120）；两节点 `test_a_dropped_candidate_leaves_a_named_fact_on_a_route_the_frontend_already_calls`、`test_the_named_reason_points_at_the_stop_whose_demo_evidence_conflicted`；杀手 **M9**（把 action 改名 ⇒ 事实失去可寻址名）与 **M10**（无条件也写 ⇒ 专杀"不该出现却出现"那半）；**11 条门全绿，`nodes_without_a_killing_arm=[]`**；分母 **9 failed / 1170 passed（交集 9 未变，collected 1195）**。
它另做了一件对的事：g9a/g9b 本来就是红的锁时长门，它**把改动摘掉重跑并比对失败原文**（`DID NOT RAISE` / `observed provider calls = 0` 一致）⇒ 排除法，而不是靠"红集合没变"宣称无关。

**仪器教训（入册）**：B 今晚上**第二次**踩同一族坑——`getattr` 读**混合形状**列表时，dict 形的 capability 行被**静默跳过**，事实里 `hard_rule_codes` 只剩两项；是它自己的断言在写账本**之前**把它拓红的。⇒ **凡混合形状列表，先列形状再取值，不要直接 `getattr`**；"先断言、后落账"的顺序继续保持。

**交接要求已下**：`USER_VISIBLE_HALF` 仍归 D `e345b9d6`，B **不做前端、不写文案**，改为给我一份**字段级交接清单**（`agent-feed` 里那条事实的完整字段名 + 一个真实例子的值；"一条都不出现"的反例形状；前端最小渲染需要哪几个字段名）。拿到后我原样转给 D，不让 D 反推。

### ② F `8ccd71d8` 的 ORD-0225 交付（我签）＋由此修掉我自己的两个缺陷

**禁制三条全守**：尺一字节未动（`_qoder_streak_receipt.py` sha256[:12] `5528700cfbe7`）、未碰 `live_checks/**`、**本轮 closure 子进程 = 0**（矩阵自断言）。**12 格具名退出码**（`0` 唯一含义＝CLOSED）＋**9/9 守卫实测**。**两步式**（先只测量，再从被测树 import 同一把尺判一次，强制两次 verdict 逐字相等，不等就撤等级为 `WITHHELD_REFUSED`）**我接受为正确形状**。

**它指出我适配器的两个真缺陷，我当场修完**（`live_checks/gate_streak.py`，blob `4510825b2d803d37`，12,232 B）：
1. `clause6_declared` 原写死 `False`（注释说"由车道声明"）⇒ 后果是**只跑适配器永远到不了 CLOSED**。改为可由交付方显式传入（`--clause6-declared` / `CNX_CLAUSE6_DECLARED=1`）；默认仍 fail-closed，**但会自己把这句话印出来**，不靠别人发现。
2. 退出口径改为**只有 `closure_grade == CLOSED` 才返 0**；`STREAK_MET` 不再直接返 0（仅显式 `--observation-runs` 的观察跑可返 0，且自印"这是我的自述、不是闭合"）。**与部署量具那个"宽松判词冒充严格判词"是同一族。**

**一处必须说白的限度**：这两处修，我验的是**编译 + `--help` 里能看到新参数 + 在主线树上正确以 `SHARED_MODULE_MISSING` 拒跑（fail-closed）**；**"CLOSED / 非 CLOSED"那条分支我还没有用一次真闭合跑驱动过**（主线没尺、corrected g3 还不存在）⇒ 我**不**写成已验证，等第一次真 closure 现场驱动。

**F 报的真发现**：**主线导出树里没有那把尺**（它在 `0748a1f` 上的真实读数 `13`）。⇒ 已要求它在 closure 收据里把**哪棵树带尺**写成一个坐标（路径 + 尺 sha256 前缀）——"主线没尺"本身就是必须出现在收据里的发现。
**我的两个决定**：① **今晚不并线**（合分支是分支政策问题，仲裁先前定过不复用旧分支名/不 force/gate 绿了再走非破坏性新分支），F 不许动，我把这个问题请给仲裁；② 它的 12 格退出码表**须补第 13 格**——**SHA 不在权威树（只是本地未推送）⇒ 拒跑**，理由就是 `EXTERNALLY_READABLE_EVIDENCE`：本地 SHA 不是坐标。

### ③ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:58 复核）；那把 key 仍未轮换。
