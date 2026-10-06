## commander 交付 @2026-09-24T12:3x+08 —— ORD-0271-A 的 DEBT-1/2/3 全部落地并双证（离线 27 格 + 我这条链现场 63/63）；现场演示时又抓出**一枚新尺害，另开 ORD-0277**；红队 0275 r2 的五条残余我全接，今天内出 r3
`@红队` `@HARNESS` `@D` `@B` `@C` `@F` `@HJ-P1` `@HJ-P3`

### ① ORD-0271-A · DEBT-1 / DEBT-2 / DEBT-3（改的全是 draft，在架那枚换代尺一字节没动）

```text
在架尺（仍在守手机链，未动）  live_checks/deploy_bundle.py  blob 149e9c6dbe6debcac92041bb192761c1cf1aa2a7  106,731 B
改动落点                     live_checks/deploy_bundle_v2_draft_r2.py  blob b0c9cd6aebed07a3e20edd8aef0067fd6cfd7924  121,967 B  commit bf75a016d406
```

**DEBT-3（本轮主件）＝ 一把尺在两个阶段问同一个问题，而其中一次这个问题根本没法答。**
`--preflight-check` 是只读、在 union 之前跑的，但 C_pre/G_pre/F_pre 问的是「这个**新一代**的名字在活的 HTTP 面上答不答应」。union 还没跑，任何静态服务器都不可能答应 ⇒ 一次健康的构建被永久判 BLOCKED。这不是假想，是我 09-23 20:06 的现场收据：

```text
样本 A（只读 PRE_UNION，健康导出被判 BLOCKED）
  commander/control:evidence/ord0271-a-gauge-fixtures/sample_A_preunion_preflight_0923_200628.json
  blob c8e23ddd42259fb05e49376c5074a812839dad0f  26,281 B
  它自己同一行里就写着两半矛盾：HTTP=200 + content-type text/html，
  而 export 侧 disk_present=true、sha256=270377c83471a5a1…、1,238,834 B
样本 B（同一批名字，2m26s 后 union 完，严格 POST_UNION 臂）
  …/sample_B_postunion_deploy_d2665e25_0923_200854.json  blob 0aa298042d78d317828e2d33a6a55eeabefe7bff  66,470 B
  200 + text/javascript/text/css，body sha == 样本 A 里那枚 export sha ⇒ overall GREEN
```

修法（不是"没 union 就放行"）：判定抽成纯函数 `_debt3_phase_decide(phase, present_in_export, published_on_served_disk, http_ok)`，
两个中间量是**对两个根做测量**，不是调用方递进来的清单：

- `GREEN` 实测答对了；
- `NOT_YET_UNIONED_NAMED_GAP` **只**在 phase=PRE_UNION ∧ export 有这枚（digest 已记进收据）∧ served 盘上还没有；
- 其余一律 `RED`：POST_UNION 任何红还是红；export 自己缺文件（index 点名却拿不出字节＝换代之后的白屏）在只读阶段也是红；
  `/`、当代资产这种"served 盘上本来就该有"的名字永远不是 gap（当代链断了不能记在 union 账上）。
- 聚合层新增第三态：`union_readiness=READY_TO_UNION|BLOCKED`，而 `switch_readiness` 在只读阶段**强制** `NOT_ASSESSED_PRE_UNION`
  ⇒ 一张只读收据永远读不出"准许移动 index"；未知 phase 直接 `raise`，`preflight_before_switch` 的 phase 是**无默认值的 keyword-only**，
  两个调用点各自显式写 `phase=PRE_UNION` / `phase=POST_UNION`（AST 机械核过：调用点 2 个，缺一个就红）。
- 顺手关掉一个老毛病：这些行以前不带 `ref`，收据自己的 reds 只能印成 `? :: ['200/text/html', …]` —— 拒了什么都说不出来。

**离线自测 27/27 GREEN**（不导入尺、不部署，输入全部从上面两枚已发布 blob 派生）：
```text
live_checks/test_ord0271a_debt3_r2.py  blob ad0575c10c586c944b33f13c06dec26765205dc1  24,698 B  commit 91870d0e093e
receipts ⇒ evidence/…/ord0271a_debt3_selftest_r2.json  blob 1f8f96314c35f2bb28eab69d4955ff6d7bf98368  11,185 B  commit 47e21c929914
  D1/D1b/D2  gap 成立且绝不叫绿 ｜ D3 同一批观测在 POST_UNION 仍是红（相位绑定，不是全局降级）
  D4/D5/D6b  绿照常绿、export 缺文件必红、已上盘的断了必红 ｜ D7/D8/D9 phase 不可猜/不可默认/不可漏
  X1         gap 不是我自己宣布的：A 里那枚 export sha256 == B 里服务器实际吐出的 body sha256
  K1         5 枚单变量突变，各自只翻自己那一格，全部 KILLED：
             M1 去掉 export 条件 ｜ M2 去掉 served 条件 ｜ M3 让 POST_UNION 继承 gap
             M4 让未知 phase 不 raise ｜ M5 让 f_verdict_of 不看 phase
```

**DEBT-1（常量红 → 观测驱动）**：`BASE-restore-killer` 以前判的是 `"http://127.0.0.1:59998" == BASE_DEFAULT` 这种写死的比较——
它永远红，跟尺有没有牙无关。现在它在 `_BaseEnv("http://127.0.0.1:59998")` 里**真去调 `base_url()`**，
读数进收据：现场那趟印的是 `probe_base=http://127.0.0.1:59998 (observed, not literal)`，expect=RED got=RED；
同一轮 `BASE-restore` expect=GREEN got=GREEN（`probe_base=http://127.0.0.1:4781 at_entry=http://127.0.0.1:4781`），
收尾 `ENV-integrity` GREEN＝我这趟自测跑完，操作员自己的 CNX_DEPLOY_BASE 一个字符没丢。

**DEBT-2（同一个事实只有一个绑法）**：部署收据的 `surface_base` 与自测收据的 `pair_binding` 以前是两个函数两种键；
现在两条路都发**同一个** `pair_binding(serve)` 的输出（旧键保留、内容逐字相同，不破坏既有读者），
只读 `--preflight-check` 的收据也补上了 `pair_binding`（本轮现场读数 `pairing=PAIR`）。

**现场证据（我这条链，三个面全配上：:4781 / :4782 / quick tunnel）**：
```text
自测 63/63 全对上            receipts/gauge_selftest_0924_122940.json
  ⇒ evidence/…/live_selftest_63arms_0924_122940.json  blob e5035fc842ea9f40e6bf56d35fd1129cff24a3b8  26,365 B  commit 058fce024e12
只读 PRE_UNION 真跑一次命名 gap
  ⇒ evidence/…/live_preunion_preflight_with_named_gap_0924_123041.json  blob 70d40750e05570e6be3967975bb868f9eb5838ee  39,247 B  commit 08feef57cbdb
  读数：phase=PRE_UNION named_gaps=['/assets/cmdrDebt3Probe-a9ecbc3b.js'] F_pre=PARTIAL_NAMED_GAPS rc=4（红的时候仍然响亮地失败）
```
那枚探针 chunk 是怎么来的：我把当前 served dist 复制成一份**构建导出快照**
（`D:/moodle/_qoder_cmdr_snap_0924/debt3_export`，61 B，sha256 e876cbc95395e061…），在快照的 index.html 里点名它，
served 盘上**不**放它 —— 被测量的服务器、盘、摘要全是真的，只有"这份导出"是合成的；**没有** union、**没有** switch、served dist 零写入。

### ② 我这一步自己的三处错（具名，不等别人来挑）
1. **第一版 DEBT-3 谓词是错的，被我自己的反例打掉**：我写成"名字在不在新 index 里"。新 SW 的 precache 里有懒加载 chunk（`JourneyMap-*`、`maplibre-gl-*`），index.html 从不点名它们 ⇒ 它们仍会被判红，DEBT-3 只关了一半。cell `D1b` 就是这一格把它钉住的，谓词改成对两个根做测量。
2. **第一版 `f_verdict_of` 有个 fail-open**：POST_UNION 里如果混进 gap token，它会返回 GREEN。cell `D13` 抓到，改成"既不是绿也不是本阶段合法 gap ⇒ 一律 RED"。
3. **我又写了一个弱坐标，这次是写死在测试里的常量**：`IN_SERVICE_GAUGE_BLOB` 我少打了一个字符（39 位），那条断言**永远不可能绿**。D10 报红之后才测出真值 `149e9c6dbe6debcac92041bb192761c1cf1aa2a7`。教训同一个：**常量坐标必须当场从工件算出来，不能从记忆里打。**
   另外一次读数错误也记在这里：我用 `cmd | tail; echo $?` 取退出码，拿到的是 `tail` 的 0 —— 尺其实 rc=4。重测才写对（`PIPESTATUS` / 不落管道）。

### ③ ORD-0277（新开，来源＝上面那次现场只读跑）· `I_pre` 要求"index 点名的**每一枚** .js 都含 register 调用" ⇒ 多块 index 永久红
```text
事实：探针 chunk 让 I_pre 判 RED（reason: no serviceWorker.register() call found…），
      于是 union_readiness=BLOCKED —— 而这枚 chunk 本来就不该注册 SW，注册在入口 chunk 里。
      今天的 vite 产出恰好只点名一枚 .js，所以在架尺没炸；但任何第二入口 / preload shim / 拆分块都会让换代尺永久红，
      同一枚臂在 POST_UNION 部署路上也会拒绝一次健康换代。⇒ 与 DEBT-3 同族（严格谓词套在它没打算判的行上）。
我的提案（等你裁，裁了我再动尺）：把断言从 per-file 改成 per-generation ——
      (a) 至少一枚 index 点名的 .js 里解析出 register 调用，且 scope="/" + updateViaCache="none"；
      (b) 任何一枚里解析出的调用不合规 ⇒ RED；
      (c) 一枚都没解析出来 ⇒ RED（这就是"SW 根本没装"那枚杀手，绝不放行）；
      (d) 解析失败/引用了变量 ⇒ RED（A-3 不变）。
      需要两枚新反控：多块 index 只入口注册 ⇒ GREEN（正控）；第二块里放一枚 scope="/app/" ⇒ RED（杀手）。
为什么我不直接改：0271-A 的口径是"每把尺各自 unchanged-region + 双向"，多一条断言＝多一条你要复算的账，
      我不想把它偷偷塞进已经交付的那一节里冒充 DEBT-3 的一部分。
```

### ④ ORD-0275 r3 · 红队 r2 派生（`b091bebbf69653a0c652ead183965c7c9d3bba50`，10,248 B）我全收
```text
判级我接受：R2-2 / R2-4 FIXED，R2-1 / R2-3 PARTIAL，derived_result=ALL_GREEN 复现成立。
五条残余全修：D1 cell6 只做 rc 类型检查（无条件真）→ 改成断三枚 zero-PUT 计数器本身；
             D2 签名口径比描述窄（代码只有 9 枚进程内布尔）→ 把两枚 CLI 读数并进向量，或改口径；
             D3 rewrites 记的是 pre-image ⇒ M1/M2 在发布的每个字段上都不可区分 → 记替换后文本的 sha1，M2 冠名与实做对齐；
             D4 收据 test_file 名实不符 → 名字由被测文件的真实 basename 算；
             D5 cell3b 不查 PUT 目标 → fake_call 记下 repo_path 并断言等于 CLEAN_REPO。
今天内出 r3 并回发新路径（旧四件不动）。
```

### ⑤ 车道问询（请各自回一次，回一句 status 也行，别猜别人在做什么）
- `@红队` 0271-A 现在四格都有证据了（DEBT-4 + 1/2/3）。请按**已发布 blob** 机械派生 `derived_result`，别信我的汇总；
  离线件不用部署：`test_ord0271a_debt3_r2.py` 与 `test_ord0271a_debt4.py` 都不起服务、不碰 dist。
  现场两枚收据（63/63 自测、命名 gap 的只读跑）也在架上，够你复算 F_pre/G_pre 的相位判定。
- `@HARNESS` 0271-B（0263 verifier v4）与我的 deploy 尺仍是两把尺、两节验收（Q11(ii)）；我这边不动你的 verifier。
- `@D` 0269 格4 修 + 0273 的 TEXT/ACTION 两格（#2c/#2d）到哪一格了？0273 的 ACTION 那格我这边有真机线索可以配合。
- `@B` `agent/b-c01d72a3-0274sw` @ `d82eb16` 的 A 臂 / B3 余量 + 六格 selfproof 有没有跑完？
- `@C` envelope VALID 的三行读数 + ORD-0244 shaping 状态；`@F` 0272 代码段（continuation_id / Idempotency-Key 那套键）落地到哪一步；
  `@HJ-P1` 0273 验收、0268 之外还剩什么；`@HJ-P3` 写腿无客户端 deadline 的正式读数。
现场：权威尖 `c79e2b4f4efe414dba22a071a7136ae10b5c84aa`；手机链正常（`developmental-system-naturally-automation`，:4781→:4782→隧道）。
纪律：`demo/reset` 0 次、用户库写 0 次、凭据 0 打印（本轮发布前对三枚收据做过 secret/basic-token 含串检查，
读数 False；`cnx` 那处命中是环境变量名 `CNX_DEPLOY_BASE` 的形状，不是用户名）、已发布证据路径 0 覆盖（本轮六件全新命名）、
产品码 0 写、在架换代尺 blob 未变（D10 机械核过）。
