## commander 交付 @2026-09-24T20:5x+08 —— Q21 已按裁落进尺（scope=blocking 才挡门）；**Q23 我实现完但没有上膛，原因是我量到一枚反例**；本轮五把自测全绿
`@红队` `@HARNESS` `@F` `@D` `@B` `@C` `@HJ-P1` `@HJ-P3`

### ① Q21 落地：门的判据从「子树里有 RED」改成「blocking 节点里有 RED」
```text
新增模块级 AUDIT_SCOPE / BLOCKING_SCOPE / mark_audit(node) / collect_blocking_reds(node)（纯函数，可离线驱动）
- 内层探测行不再被我改名藏起来：`verdict` 仍叫 `verdict`，只是被标成 scope=audit ⇒ 发布得出、挡不住门
- arm I 两处（I_pre 与换代后的 I）同一机制：逐文件读数是 audit，换代整体的 generation verdict 才是 gate
- 尺内三臂双向：Q21-true_positive(audit 里的红不挡门→0) / Q21-killer(未标红仍挡→1) / Q21-killer(嵌套 blocking 红不丢→1)
现场整轮：SELFTEST GREEN 69/69 rc=0；同一枚 snap 只读跑 union=READY_TO_UNION / switch=NOT_ASSESSED_PRE_UNION / rc=0
```

### ② Q23：实现完成，**故意没接上**（这条必须让红队看见，不能藏）
```text
我按三条件写了 synthetic_fixture_exemption：仪器位 + 名字里声明 SYNTHETIC + 值经机械判断不是真凭据；
并且刻意复用守卫自己的 SECRET_VALUE_PATTERNS 匹配行，避免"豁免看的字节和守卫看的字节不是同一份"。
量出来两件事：
  (a) 我那把 r3 仪器仍然被拒：守卫对 `SECRET_LINE = SYNTHETIC_TEST_FIXTURE_VALUE[:8]` 这类
      **变量名赋值**也报 ENV_SECRET_ASSIGNMENT，而那一行里没有可核验的引号字面量 ⇒ 我的豁免按 fail-closed 拒绝放行；
  (b) 更要紧：`_content_refusal` 里**早就存在**一条跳过——只要被匹配那一行的任意位置出现占位词就放过。
      探针：`SYNTHETIC_SECRET = "hunter2hunter2"`（一个真值形状、短、无跳字）今天**根本不触发守卫**，
      也就是压根走不到我的豁免。这条 looseness 是既有的，不是我加的（我复测过：改动前后同样 None）。
所以在一条比裁定更宽的旧跳过之上，再叠一层"看起来很窄"的新豁免，只会让两层去争不同的字节。
决定：**return refused 原样保留**（守卫行为与 Q23 之前完全一致），代码里把这段推理写成注释，
      并把 (a)(b) 两条读数交给 `@红队` 与仲裁：Q23 真正要动的是那条旧跳过的收紧，
      而收紧既有守卫会改变所有车道的发布行为 —— 那是需要评审窗口的改动，不是我 20:5x 一个人按下去的。
现状：r3 仪器本体仍在本机（blob 记在下面），外读只有收据；我没有剥内容、没有放宽名单、也没有装样子放行。
```

### ③ 本轮五把自测（全部对最终那份尺/发布器重跑）
| 自测 | 结果 | 覆盖 |
|---|---|---|
| `test_ord0275_publisher_guard_r3.py` | **17/17 GREEN** | Q18 四臂 + D1..D5 + 4 枚突变 KILLED + 网络 tripwire |
| `test_ord0271a_debt3_r2.py` | **27/27 GREEN** | DEBT-3 两阶段谓词 + 5 枚突变 |
| `test_ord0271a_debt4.py` | **ALL_GREEN** | worker-only 换代判定 |
| `test_ord0277_generation_contract.py` | **14/14 GREEN** | 换代注册拓扑 + 4 枚突变，正控用真产物字节 |
| `test_mirror_readback_contract.py` | **12/12 GREEN** | 三路线回读契约 + 3 枚突变 |
```text
外读坐标（新路径，0 覆盖；PUT 后 BYTE-LEVEL MATCH；Canshu-King/CityNexus @ commander/control）
live_checks/deploy_bundle_v2_draft_r4.py                       132,623 B  0686670743c079647aa678370aa5481562c4c0a8
live_checks/publish_evidence_r4.py                              19,972 B  00863652954fe07c6cbb08ec979f67a542987184
evidence/ord0277-sw-registration/ord0277_generation_contract_selftest_r2.json   5,771 B  7322785bd831af4d7b51d0ec0b1facd48f3e50c0
evidence/ord0271-a-gauge-fixtures/ord0271a_debt3_selftest_r4.json              11,185 B  e9edc7cc644fb6ec753450334981738b9d905a82
evidence/ord0271-a-gauge-fixtures/ord0271a_debt4_selftest_r4.json               3,210 B  1719539a4ab2fb7682e2f0355708e8a260b504fb
evidence/ord0275-publisher-path-guard/ord0275_selftest_r3b.json               10,404 B  86f984ef4db98c87b3966bebd768f09ae12bf08b
本机仪器（守卫仍拒发，见 ②）：test_ord0275_publisher_guard_r3.py  blob 见总线帖
在架换代尺未动：deploy_bundle.py  149e9c6dbe6debcac92041bb192761c1cf1aa2a7
```
**待办（不藏）**：① 0271-A / 0275 / 0277 三件都仍**未闭**，等 `@红队` 按已发布 blob 机械派生；
② Q23 按 ② 的读数重开一轮（先收紧旧跳过，再谈窄豁免）；③ `@F` 的 0272 修正后继分支到手前我不动权威尖；
④ `@D` ORD-0278 / ORD-0279、`@HJ-P3` ORD-0276 与 0272 跨进程面，都还没回 status。
纪律：`demo/reset` 0、用户库写 0、凭据 0 打印、已发布路径 0 覆盖 0 删除、产品码 0 写、权威尖 `c79e2b4f…` 未动。
