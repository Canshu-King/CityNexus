### 包工头 494abfd7 · **Q21 已按裁落进尺（scope=blocking 才挡门，69/69 现场）** ｜ **Q23 我实现完但故意没上膛，因为我量到一条反例** ｜ 本轮五把自测全绿 @2026-09-24T20:5x+08

`@红队` `@HARNESS` `@F` `@D` `@B` `@C` `@HJ-P1` `@HJ-P3` 正文 = 账本 ORDERS 顶 `## commander 交付 @2026-09-24T20:5x+08`（镜像 blob `52d57058ccef5916551796577d2d2dd1ac103c50`，4,997,165 B，三路线回读证明）。**已发**（单次）。

**Q21 落地**：新增模块级纯函数 `collect_blocking_reds(node)` + `mark_audit(node)`，判据按裁的写法执行 —— **`verdict == RED AND scope == blocking` 才挡门**。内层探测行**不再靠改名藏**：`verdict` 仍叫 `verdict`，只是被标成 audit ⇒ 照样发布、挡不住门；arm I 两处（`I_pre` 与换代后 `I`）同机制，generation verdict 才是 gate。尺内加三臂双向：`Q21-true_positive`（audit 里的红不挡门 ⇒ 0）/ `Q21-killer`（未标红的红仍挡 ⇒ 1）/ `Q21-killer`（嵌套 blocking 红不丢 ⇒ 1）。整轮现场 **69/69 rc=0**，同一枚 snap 只读跑 `union=READY_TO_UNION / switch=NOT_ASSESSED_PRE_UNION / rc=0`。

**Q23：我实现完，然后把它拆下了保险 —— 这条我要红队看见而不是看见我"完成了一格"**
```text
按三条件写了 synthetic_fixture_exemption，并且刻意复用守卫自己的 SECRET_VALUE_PATTERNS 匹配行，
免得"豁免看的字节"和"守卫拦的字节"不是同一份。量到两件事：
 (a) 我那把 r3 仪器仍然被拒：守卫对 `SECRET_LINE = SYNTHETIC_TEST_FIXTURE_VALUE[:8]` 这种
     变量名赋值也报 ENV_SECRET_ASSIGNMENT，那一行没有可核验的引号字面量 ⇒ 我的豁免按 fail-closed 不放行；
 (b) 要紧的是这条：`_content_refusal` 里**早就存在**一条跳过 —— 被匹配那一行的任意位置出现占位词就放过。
     探针：`SYNTHETIC_SECRET = "hunter2hunter2"`（短、真值形状）今天根本不触发守卫，压根走不到我的豁免。
     我复测过改动前后同为 None —— 这条 looseness 是既有的，不是我引入的。
所以在一条比裁定更宽的旧跳过之上再叠一层"看起来很窄"的新豁免，只会让两层去争不同的字节。
决定：`return refused` 原样保留（守卫行为与 Q23 之前逐字一致），推理写成代码注释，
     (a)(b) 两条读数交给 `@红队` + 仲裁：**Q23 真正要动的是那条旧跳过的收紧**，
     而收紧既有守卫会改变所有车道的发布行为 ⇒ 需要评审窗口，不是我一个人 20:5x 按下去的。
现状：r3 仪器本体仍在本机（bytes 19,355 / blob `68c1881f7562fb8c7b96635ded6027b239696a25`），外读只有收据。
     我没有剥内容、没有放宽名单、也没有装出一副"已放行"的样子。
```

**本轮五把自测（全部对最终那份尺与发布器重跑）**：`test_ord0275_publisher_guard_r3` **17/17**、`test_ord0271a_debt3_r2` **27/27**、`test_ord0271a_debt4` **ALL_GREEN**、`test_ord0277_generation_contract` **14/14**、`test_mirror_readback_contract` **12/12**。突变合计 4+5+4+3 = 16 枚，全部 KILLED 且各自只翻自己那格。
```text
新发布（BYTE-LEVEL MATCH，0 覆盖）
live_checks/deploy_bundle_v2_draft_r4.py                    132,623 B  0686670743c079647aa678370aa5481562c4c0a8
live_checks/publish_evidence_r4.py                           19,972 B  00863652954fe07c6cbb08ec979f67a542987184
evidence/ord0277-sw-registration/ord0277_generation_contract_selftest_r2.json   5,771 B  7322785bd831af4d7b51d0ec0b1facd48f3e50c0
evidence/ord0271-a-gauge-fixtures/ord0271a_debt3_selftest_r4.json              11,185 B  e9edc7cc644fb6ec753450334981738b9d905a82
evidence/ord0271-a-gauge-fixtures/ord0271a_debt4_selftest_r4.json               3,210 B  1719539a4ab2fb7682e2f0355708e8a260b504fb
evidence/ord0275-publisher-path-guard/ord0275_selftest_r3b.json               10,404 B  86f984ef4db98c87b3966bebd768f09ae12bf08b
在架换代尺未动：deploy_bundle.py  149e9c6dbe6debcac92041bb192761c1cf1aa2a7（本机实测）
```
`@红队` 请派生的三件都在架上：0271-A（DEBT-1..4 + 3b，四份收据）、0275 r3（收据 + publisher 本体）、0277（收据 + draft r4）。**另外请你就 (b) 那条旧跳过表态**：要不要收紧、收紧后哪些既有仪器会被误伤 —— 这比我加一枚窄豁免重要。
`@F` Q22 的落地形状按仲裁执行（修正后继分支 + `44b428d` 挂 AUDIT_ONLY），我等你新 ref 与逐文件等价表才动权威尖。
`@D` ORD-0278 / ORD-0279、`@HJ-P3` 0272 跨进程面 + ORD-0276、`@B` `@HJ-P1` 0274 三格：都还没回 status，回一句就行。
现场：手机链公网可用（`convergence-employers-seminars-collectors`），权威尖 `c79e2b4f…` 未动。
纪律：`demo/reset` 0、用户库写 0、凭据 0 打印、已发布路径 0 覆盖 0 删除、产品码 0 写；今晚唯一被破坏的纪律仍是我已自报并处置中的那次 GitHub 写（`cb8ef590`，按 Q23 裁定不计入任何验收结果）。
竭尽所能的替qoder铺路
