## commander 亲测 @2026-09-25T01:4x+08 —— 仲裁回裁定（NOTE_1/NOTE_2/S15/Q24/0272）+ 红队宣布「0275 可以闭、条件三撤回」⇒ 我签 CLOSED；并按 ② 把 DEBT-1 仪器改成"守自己的规则"，26/26 全绿、仪器本体与收据**双双可外读**

### ① 仲裁这一轮裁了什么（01:3x+08，我刷新网页后读到的全文）
```text
NOTE_2 -> 选②：不给自己开"规则名白名单"。新增常驻规则 PUBLISHER_RECEIPT_DISCLOSURE_RULE：
          收据允许 rule_hit: ENV_SECRET_ASSIGNMENT 这类"规则名"；禁止复制守卫的原始拒绝句 / 完整异常行。
          NOTE_2 不再开新洞单，归入 PUBLISHER_SECRET_SCAN_DEBT_1 的两个子项：
              DEBT_1a detection correctness
              DEBT_1b diagnostic disclosure boundary
NOTE_1 -> 保持现状并钉成固定回归格：Authorization: Bearer <占位词> 仍判 RED；
          裁定原话性质是"不是缺陷，是安全不变量"（若为方便测试放行，真 token 就跟着出门）。
S15    -> 批准，并定名 PUBLISHER_SELF_PUBLICATION_CONTRACT，要求双向：
          正控 源码只用散文描述漏洞 => GREEN；反控 源码嵌入凭据形状的字面量 => RED。
Q23 口径 -> 不许写 "synthetic exemption complete"，要写：
          detection tightening = DONE / synthetic exemption = NOT_ENABLED / receipt disclosure boundary = ADDED
Q24    -> R-SCHEMA-01/02 生效；HJ-P3 属 methodology correction 不是 result invalidation（标 SCHEMA_SOURCE_METHOD_CORRECTED，不推倒）；
          今后"必须重跑"的判据清单：表结构 / 字段存在 / index / constraint / migration / schema version；
          "不必重跑"：既有 API 行为 / HTTP 状态 / UI 展示 / 锁竞争 / 网络超时（schema 只当运行环境载体）。
0272   -> 认可我现在的顺序：等修正分支 + lineage 明确 + 可外读，再谈 ff-only；不得因为 selftest 绿就动权威尖。
```
`@全部车道` 从今天起 **收据里不要抄守卫的拒绝原文**，写规则名。这条会影响每个人已经写好的写法，谁的历史收据含原文，在下次自然修订时改掉，不要覆盖旧件。

### ② 红队的裁定与我的签字
`@红队`（`1bf501033c1caee202181c07ecd1cc9b0b568d31`，8,021 B，新路径 `evidence/ord0271-a-gauge-fixtures/verifier_rederivation_r3_d2305848.json`）四件重派生：DEBT-3 `_r3` **真冷跑** 27/27 + M1..M5 全 KILLED、provenance `materialised_from_published_blob`；r4 现场两件 69/69 与 PRE_UNION 分别判 `ALL_EXPECTATIONS_MET` / `PRE_UNION_FACE_HONEST`；0275 对 r5+ r3c 重跑 17/17、cells 零差异；并且**撤回它自己的"条件三"**，给出元规则：被自家守卫拒收的工件不阻塞闭单，只要 (a) 收据在架 (b) 收据带齐重建输入 (c) 验方自陈证据等级 (d) "不可发布"本身已在架披露。
⇒ 我据此签 **ORD-0275 = CLOSED**（仪器单，无落地/换代面；派生坐标 `b657a289…` + `1bf50103…` + 收据 `2ded6ef9…`）。

### ③ 但我没有停在"可以带着不可见本体闭单"——按 ② 的裁定把本体救回来了
DEBT-1 的仪器按新规则重写：夹具改成运行时拼装（源码里不再留凭据形状字面量）、每个字段过 `rule_hit()` 只存规则名、并把契约钉成三格：
```text
S15a 发布器自身源码（散文描述漏洞）        GREEN
S15b 发布器源码嵌入凭据形状字面量          RED      （双向，按裁定的反控）
S17  拼装出的夹具与被判的形状逐字节等价    GREEN     （"能发布"不等于"少测了"）
S18  本仪器自己的源码能被自己测的守卫放行  GREEN
     26/26 ALL_GREEN；4 枚突变各自只翻声明的集合（MA{S3} / MB{S2,S11,S12,S13} / MC{S13} / MD{S12}）
新坐标（BYTE-LEVEL MATCH，0 覆盖 0 删除）：
     live_checks/test_publisher_placeholder_value_scan_r2.py  19,038 B  a67086eace45ce3a9fc3beace28bffb7d18dccec  commit 58e73bb4c851
     evidence/publisher-placeholder-scan-debt1/selftest_r2.json  9,455 B  4ba73c313441c3de925cb10442c39f5476af3206  commit 8aca911e5a19
     旧 r1 件（本机 58d758e1… / 9,620 B）从未在架，保持原位不追改；上一块里"本机有、外读没有"那句对本体已由本块取代。
```
状态字按裁定的写法记：`detection tightening = DONE / synthetic exemption = NOT_ENABLED / receipt disclosure boundary = ADDED`。

### ④ 现场与纪律
手机链 00:05 换过一次地址（隧道到 Cloudflare 边缘 `198.41.200.x:7844` i/o timeout，本机四层实测 200 ⇒ 归因隧道），新地址 `https://convinced-planets-calculations-laid.trycloudflare.com`，01:3x 复测首页 / 主 JS / health / 北京 8 地点两侧全通（断网期间没有把我误导成"产品挂了"）。
闭单不动尖：权威线仍 `c79e2b4f…`；换代那一面 `promotion_state = PENDING_UNION_AND_POST_SWITCH`，所以 **0271-A / 0277 只到"验收通过、待同代换代复跑"**——真正的换代需要重新构建 dist，而别人 `frontend/src` 脏时我不构建（这条是钉过的），不在夜里偷跑。
纪律：`demo/reset` 0、用户库写 0、凭据 0 打印（两份新收据发布前核过字面口令/其 base64/`Basic` 均为 0）、已发布路径 0 覆盖 0 删除（本轮新增 2 件产物）、产品码 0 写。

