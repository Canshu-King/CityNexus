## commander 亲测 @2026-09-24T23:4x–23:5x+08 —— 红队派生件到达（三件 ALL_GREEN，我按 B-1 只认它的 derived_result）；它点出的两条我今夜当场修完并发了新坐标；F 的 Q22 修正枝我自己复核成立但**暂不动尖**

### ① 验收：`@红队` 的派生件（不是我复述，是它的收据）
`evidence/ord0271-a-gauge-fixtures/verifier_derivation_window_d2305848.json` 12,263 B `b657a289e885a2de2f6447b89eebae9a54a05be0`
```text
item2 DEBT-3   derived_result=ALL_GREEN  27/27  killers M1..M5 全 KILLED
               field_level_reproduction: fields=221 differing=6（4 条本地路径 + 2 条时间戳）verdict_fields_differing=0
item3 DEBT-4   全绿（A/B 两支 worker sha 交叉对上同一代 88a7d980b3ffcbd6）
item4 ORD-0277 derived_result=ALL_GREEN  14/14  K1..K4 全 KILLED  fields=110 differing_after_stripping_t=1（只有目录名）
item5 live     66/66 期望全中（48 枚是"期望 RED"的突变臂，全 RED）；PRE_UNION 那件判 PRE_UNION_FACE_HONEST
item6 0275     对我那句元问题给了裁定：收据在架、本体不可外读 = SUFFICIENT FOR CLOSURE，三条件
```
⇒ `ORD-0271-A / ORD-0277` 的**验收条件已成立**；闭单仍要等 ① item5/item6 对新读数重派生（见 ②③）② 换代那一面（同代复验）。我不自宣 CLOSED。

### ② 它点的第一条：我的仪器**冷跑必死**——已修，双向证过
成因（它写的，我复现了）：`fetch_blob()` 取完字节就把 raw 丢了，下一步去 `io.open()` 一个**只在我工作树里存在**的 cache 路径 ⇒ 新目录 `FileNotFoundError`，一格都没执行。
修法：cache 不存在时从**已 sha 验证的发布 blob** 落盘，并把 provenance 写进那一格（`materialised_from_published_blob` / `pre_existing_local_copy`）——这样"从分支取回"与"用我自己旧副本"在收据里永远分得开。
```text
同一台机器两向读数（不是两次同配置）：
  热跑   provenance=pre_existing_local_copy        overall GREEN 27/27
  冷跑   把两份 cache 改名后 provenance=materialised_from_published_blob，仍 27/27
         重建出的两份字节与原发布件同长：66,470 / 26,281
新坐标：live_checks/test_ord0271a_debt3_r3.py   25,704 B  cababfe9097b3d901730c37d13682a0310c6f20e  commit 7efabb5c98c5
        evidence/ord0271-a-gauge-fixtures/ord0271a_debt3_selftest_coldrun_r5.json  11,293 B  40ed7864a39aaabeea56d76c0fc7cd2a60c37d49  commit 8e3f5bab9382
        旧 `_r2` 仪器与旧收据原位不动（0 覆盖 0 删除）
```

### ③ 它（和侧会话 8d206bab）点的第二条：**r4 没有一份"现场跑"点名**——已补
原话：今天 `deploy_bundle_v2_draft.py` 这个**文件名**下换过三版字节（`b0c9cd6a` 121,967 → `5bdc7525` 129,139 → `0686670743` 132,623），而所有现场件只背书到第二版。这条我认：`.py` 文件名不是坐标，同一天三版字节共用一个名字，正是我们自己钉过的"源坐标与产物不同 sha 就不是坐标"。
```text
用 r4 跑 --selftest（对真链，不部署）：69/69 arms GREEN，收据内 gauge_git_blob_sha1=0686670743c079647aa678370aa5481562c4c0a8 / gauge_bytes=132623
  -> evidence/ord0271-a-gauge-fixtures/live_selftest_69arms_r4_gauge_0924_233853.json  28,852 B  9cde913ccbf8c9c6d6459b54fc8a270e446456c8  commit 20355864c07d
用 r4 跑一次 PRE_UNION preflight：union_readiness=READY_TO_UNION，reds=[]，switch_readiness=NOT_ASSESSED_PRE_UNION，F 四探真打（proxy×2 + tunnel×2）
  -> evidence/ord0271-a-gauge-fixtures/live_preunion_ready_to_union_r4_gauge_0924_234113.json  31,425 B  124619bd387493ef4ee5227a91f8b97a7f180cb1  commit 73e9de1a367b
两份发布前都做过凭据检查：字面口令 0 次、其 base64 组合 0 次、"Basic" 0 次（口令只从 run/preview_auth.txt 读，不落证据）
给全线的一条命令形状（我自己先踩了）：不带 `CNX_DEPLOY_PROXY_BASE` / `CNX_DEPLOY_TUNNEL_BASE` 时 F 判 **RED**（rc=4），不是 UNPROBED —— 这是 fail-closed 的正确行为，但很容易被误读成"产品红"；真要声明没探，用 `--allow-proxy-unprobed`。
旧的两份（5bdc7525 那一版的观察）保留原位，不覆盖也不删。
```

### ④ F 的 Q22 修正后继枝：形状我**自己**复核成立，落地暂缓
```text
git/ref/heads/review/ord0272-continuation-corrected -> dcae1bc964125c3a975916f6bf667794cc19622a（ref 在 origin）
parents=[c79e2b4f4efe414dba22a071a7136ae10b5c84aa]  ← 父就是权威尖；compare = ahead / ahead_by=1 / behind_by=0
tree=d96c2974924d19831495f2945117d4221a1b6d62   与 aa29612c8 的 tree 同一枚  ⇒ 没有硬摘
compare 44b428da83e4...dcae1bc96 = diverged（反向亦测）  ⇒ 44b428d 不是它的祖先，Q22 的"不进权威线"成立
变更面：backend/app/main.py +241/-36，backend/app/schemas.py +5/-0，backend/tests/test_qoder_ord0272_continuation.py +457/-0（新增），contracts/openapi.yaml +22/-0；frontend 命中 0 个文件
决定：**不动尖**。差的不是形状，是一枚坐标诚信 —— F 收据里 21 条载体 nodeid 有 4 条的根与它自己写的 run cwd 不匹配（侧会话读数，我按它复述并派 F 补正）。落地后 verifier 按 nodeid 复收会让 K2/K3/K4 "收不到"，那是坐标错、不是产品红，而我 refuse 拿已知错的 nodeid 跑真验收。
另记一笔不追责：F 23:13 引用"通知帖 5816724931"在总线里不存在（单件路由 404 + since= 列了当时段 11 条）；它名下真实存在的是 5814089692（20:27）与 5816835442（23:13）。引用自己发过的东西必须贴**回读到的** id。
```

### ⑤ Q-a 的落地状态（我 22:5x 问红队的方向题，它选①，仲裁 23:0x 已批，我已实现）
见上一块 `## commander 亲测 @2026-09-24T23:2x+08`：`publish_evidence_r5.py` = `ea4416dbafa7ac84718c3d87bd56394fb5ca5f7b`（22,464 B，BYTE-LEVEL MATCH），23 格 + 4 枚突变。红队 item6 里引的 `publisher_r4 00863652…` 与 `r3b 86f984ef…` 现在是**被取代的坐标**，我已请它对新读数重派生。
红队 Q-b 的自报我也记账转仲裁：`ORD-0253 Phase A/B`、`ORD-0225 Y123/Y23`、`ORD-0200/0201/0204` 家族的 0→N 行数读数全部标 `schema_source: replayed_DDL`；下一次自然修订加字段，不现在重跑；不受影响的（锁行为/信封）它已具名。
naming_nit（DEBT-4 仪器写本地名不带 `_r5`）我接受，但**不把发布号写回仪器**（那正是今天漂移的病根），改法是收据加 `published_paths` 字段把本地名↔发布名机械对上，下一版做。

### ⑥ 车道状态
`@红队` 收到三件重派生请求（item5 对 r4 现场件、item6 对 publisher r5 + r3c、DEBT-3 对 `_r3` 冷跑件）；`@F` 收到 4 条 nodeid 补正 + 一句可复跑收集读数的要求；`@B` `@D` 已叫（status 待回）；侧会话 `8d206bab` 已替我终止两条死尾（HARNESS、HJ-P1）并把 HJ-P1 那条未发出的消息重投。
纪律读数：`demo/reset` 0、用户库写 0、凭据 0 打印（本轮两份现场件发布前逐串核过）、已发布路径 0 覆盖 0 删除（本轮新增 6 件产物 + 4 件我自己的只读仪器）、产品码 0 写、权威尖 `c79e2b4f…` 未动。

