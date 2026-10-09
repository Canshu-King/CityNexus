### commander 请示 @2026-09-23T02:09+08 —— **要你裁一条分支政策**：streak 尺不在主线上，而 closure 需要"corrected g3 + 尺"同在一棵树；另报两件已闭环的事

#### ① 请裁：尺要不要并线、什么时候并

**事实（两处独立读数）**：
- F `8ccd71d8` 的守卫矩阵里，第 `13` 格在 `0748a1f` 上的实测就是"树里没尺"；
- 我的适配器在主线导出树上**直接拒跑**：`SHARED_MODULE_MISSING: D:\moodle\_qoder_integration_20260919\tests\_qoder_streak_receipt.py not found`（它故意不带本地副本，避免养第二把尺）。

**冲突**：`GATE_ACCEPTANCE_STREAK` 的 10-process closure 需要**同一个树里既有 corrected g3、又有那把尺**，而现在尺只在 F 的分支 `agent/f-ord210-20260922`（未并主线）。corrected g3 还没生（C 在 ORD-0224 上）。
**三选（我倾向 iii，理由在下面）**：
- **(i) 现在就把尺并进主线**：好处是以后任何 closure 跑在主线即可；代价是**在 corrected g3 还没出现时先动主线**，而那把尺本来是随 ORD-0210 一起来的、并不属于本轮。
- **(ii) 等 corrected g3 落地后一次并**：只动一次主线；但如果那次并出问题，**纠正门与尺同时受影响**，排查面更大。
- **(iii) 不并线，改为"导出 candidate SHA 的树 + 以具名依赖打上尺"并在收据里写清两个坐标**：好处是不动主线、依赖显式可审（收据里写"哪棵树带尺 + 尺 sha256 前缀"）；代价是收据多一层解释，且**"closure 跑在一个非主线树上"必须明写**，不能看起来像跑在主线。
**我的顾虑（想让你看见）**：无论选哪个，都**不许**出现"在某棵树上跑绿了、然后声称主线绿"。这一点请你在裁定里写死。
**在你回话前 F 不并线**（它已按我的要求停手）。

#### ② 已闭环：B 找到 C 路，**`main.py` 一行都不用动**

`ORD-0219③` 的静默丢失可以落在**一条前端已经在调**的面上：`GET /api/v1/journeys/{id}/agent-feed`（`main.py:6709` → 审计查询 `:6716` → `_audit_projection :6619`），兜底分支 `else: event_type = action` 把未知 action 名**原样带出**，返回带 `"facts": after`；前端 `citynexus.ts:855 getAgentFeed` 已在用（`main.tsx:213` / `:336`），摄入处不按 event_type 过滤。⇒ 我 01:48 那 2 行 header 就不需要了，B 只准备不落地是对的。
`a96fabf`（2 files +120）；杀手 M9/M10；**11 门全绿、`nodes_without_a_killing_arm=[]`**；分母 **9 failed / 1170 passed（交集 9 未变）**，且它**把改动摘掉重跑比对失败原文**才排除 g9a/g9b 的关联（不是靠"红集合没变"）。
`USER_VISIBLE_HALF` 仍归 D `e345b9d6`——B 已被告知**不写文案、不动前端**，改为交我一份**字段级清单**，我原样转 D。

#### ③ 我自己两个缺陷的修复（F 抓的）

`live_checks/gate_streak.py` blob `4510825b2d803d37`：
1. `clause6_declared` 不再写死 `False`（原来会导致**只跑适配器永远到不了 CLOSED**，且是别人发现才知道），改为可显式传入，默认 fail-closed 但**自己把这句话印出来**；
2. 退出码改为**只有 `closure_grade == CLOSED` 才返 0**（`STREAK_MET` 不再直接返 0），与部署量具那个"宽松判词冒充严格判词"同族。
**限度我写明**：只验了编译 + `--help` + 主线树上正确拒跑（fail-closed）；**CLOSED/非 CLOSED 分支尚未被真闭合跑驱动过**，等第一次真 closure 现场驱动，我不写成已验证。

#### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。

力所能及竭尽全力的替qoder铺路。
