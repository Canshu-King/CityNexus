# ORD-0263 · 产品修复交付（写者：B `c01d72a3`）

生成时间 2026-09-23T19:29:32+08:00（本机钟）。树 `D:\moodle\_qoder_b_lane_20260923` 分支 `agent/b-c01d72a3-ord0263`，根父 = 权威尖 `dea8410be809ebf6c5046581873584e9dbf32b64`；权威分支未被我移动，权威 worktree 内 0 次 commit。

## 0. 一句话

两样机制都补了：**每次数据读有截止期限**，以及**分类器不再把"答了但非 2xx"与"根本没答"折叠成同一句话**。HARNESS 的三格在他自己的判据下由 RED×3 变成 GREEN×4（S1 本来绿），尺字节未动（blob 见 §4），自测 7/7 两侧都跑过。

## 1. 现场与纪律（全部由收据算出）

- 面：`vite preview :4431` → 我自己的源站 `:8431`；库 `ord0263_8431.db`（新建文件，非复制：`db_is_new_file_not_a_copy=True`）。
- 归属双向证明：我的 journey `22222222-2222-4222-8222-222222222222` 经代理回 `200` 且回显同 id=`True`；一个不存在的 id 回 `404`（期望 `404`）⇒ `ownership_verdict=PROVEN`。
- `demo/reset` 未发过：`demo_reset_issued=False`；用户库未开：`user_db_opened=False`；零出网：AI off / resolver off / Photon → 127.0.0.1:9 绊线。
- 禁止端口 0 次请求；起面时它们各自的监听者如实记下：`{"4781": [47376], "4782": [33880], "8693": [33104], "4185": [47124], "8713": [52820], "4411": [], "4412": [], "8411": []}`。
- 改动文件（工作树实测）：4 个已跟踪 + 1 个新文件 `frontend/src/lib/readDeadline.ts`；`git diff --stat`：
```text
frontend/src/api/citynexus.ts          |   3 +-
 frontend/src/app/V8Experience.tsx      |  75 +++++++++++++++++-------
 frontend/src/i18n/LocaleContext.tsx    |   2 +
 frontend/src/lib/failureAttribution.ts | 101 +++++++++++++++++++++++++++++----
 4 files changed, 146 insertions(+), 35 deletions(-)
```

## 2. 两条病因，在我这棵树上的真实形状

| 病因 | 命令里点的行 | 权威尖 `dea8410` 上的实测 |
|---|---|---|
| 一：探针把两态折叠 | `V8Experience.tsx:198 return response.ok` | 这一行当时还在，但**它已不是 S2 的发射点**：R14/ORD-0169 之后 S2 走 `classifyReadFailure → SERVER_ERROR`，屏上不再出现「网络不可用」；折叠仍然在**只有探针能说话**的那一态成立，我为此补了 **S4**（读永不回答 + 探针答 500）。 |
| 二：数据读没有期限 | `api/citynexus.ts:642 requestJson` | 该行确实无 AbortController/超时（grep 只命中签名本身）；**但 boot 真正卡住的是同文件外的 `V8Request`（V8Experience 自带的 `v8Request`）**，所以两条通道我都上了期限，只上一条会留下同一个骨架屏。 |

期限值只有一枚来源：`export const READ_DEADLINE_MS = 12_000;`，文案里的秒数由 `READ_DEADLINE_SECONDS` 注入，不手写第二个数字。
只覆盖 GET/HEAD：写请求在期限处被客户端放弃时服务器可能仍在落地，那是幂等题目，不是本单授权我顺手改的。

## 3. 三格（+ 第四态）·修前 / 修后

读的是渲染文字（`innerText`）与产品自己写的 `window.citynexusAttribution`；源站事实由我另一次探针量得，与产品结论分字段存放。

| 态 | 构造 | 源站（我的探针） | 屏上（逐字片段） | 判据 |
|---|---|---|---|---|
| S1 | 修前探针 200 / 修后 200 | 200 vs 200 | 修前 `菜单 / 今天 跟随系统 EN DE  晚上好  Demo之旅  10月10日 09:00 — 10月10日 19:` → 修后 `菜单 / 今天 跟随系统 EN DE  晚上好  Demo之旅  10月10日 09:00 — 10月10日 19:` | **GREEN → GREEN** |
| S2 | 修前探针 500 / 修后 500 | 500 vs 500 | 修前 `服务器  服务器这次没能把行程读出来  服务器自己报错了（HTTP 500）。这是它那边的问题，不是你填错了什么。可` → 修后 `服务器  服务暂时不可用  服务器刚才答了你，但它自己报错了（HTTP 500）。这是服务暂时不可用，不是你填错了什` | **RED → GREEN** |
| S3 | 修前探针 PROBE_WINDOW_ELAPSED / 修后 PROBE_WINDOW_ELAPSED | PROBE_WINDOW_ELAPSED vs PROBE_WINDOW_ELAPSED | 修前 `CN  正在准备城市周末行程…  锚点 · 住宿 · 出行事实 · 可行性` → 修后 `没有回音  等了 12 秒，这台服务器一个字也没回答  这一发读取到了期限仍然没有任何回答：服务器既没有拒绝，也没有` | **RED → GREEN** |
| S4（第四态，不计入三格） | 读永不回答，而 `/api/v1/health` 答 500 | 500 / 500 | 修前 `CN  正在准备城市周末行程…  锚点 · 住宿 · 出行事实 · 可行性`（None）→ 修后 `服务器  服务暂时不可用  服务器刚才答了你，但它自己报错了（HTTP 500）`（12.42 s） | 同一条 V1 规则：**RED → GREEN**；label None → ORIGIN_ERROR_WITH_SNAPSHOT |

三格汇总：修前 1/4 绿 → 修后 4/4 绿；判据自测（同一把尺的 killer，不判产品）：`GREEN 7/7`。

修后每条读数里被量到的位（不是我的手判）：
- `V1_origin_error_5xx` measured = {"http_status": 500, "says_network_words": false, "says_service_words": true, "says_snapshot_words": true, "navigator_onLine": true}
- `V2_no_answer` measured = {"fetch_thrown": true, "settled_within_deadline": true, "classified_label": "NETWORK_UNREACHABLE_WITH_SNAPSHOT", "retry_door_present": true, "still_on_loading_skeleton": false, "snapshot_present": true, "seconds_to_settle": 16.58}
- `V3_distinctness` measured = {"s2_label": "ORIGIN_ERROR_WITH_SNAPSHOT", "s3_label": "NETWORK_UNREACHABLE_WITH_SNAPSHOT", "same_sentence": false, "s3_is_unclassified_skeleton": false}

## 4. 判据没有被改过一个字节

- 路径 `D:\moodle\_qoder_harness_ord0254\tools\ord0263_verifier.py`，blob `ed8a61dc79d87cc2acf18ef93ecca7caf89b4b83`（= 发布坐标 `ed8a61dc79d87cc2acf18ef93ecca7caf89b4b83`，运行前后复验 `True`）。
- 我只在我进程里把它的输出目录指到自己（`mod.BASE -> my order dir`），没有动任何规则、正则或词表。

## 5. 4 把反向突变（机制没了一样会红，不是文案红）

| 臂 | 拆掉的东西 | 主张的格 | 实测该格 | 派生判级 | 顺带红的格（同一份证据，不另计） | 应恒绿 | 逐字节还原 |
|---|---|---|---|---|---|---|---|
| M1_remove_the_per_read_deadline | `lib/readDeadline.ts` anchor_hits=1 | V2_no_answer | **RED** | **KILLED_BY_THIS_ARM** | ["V3_distinctness"] | {"V1_origin_error_5xx": "GREEN", "V3_distinctness": "RED", "S1_live": "GREEN"} | True |
| M2_force_the_cached_copy_fact_false | `lib/failureAttribution.ts` anchor_hits=1 | V1_origin_error_5xx | **GREEN** | **SURVIVOR (arm did not move the cell it claims)** | [] | {"V2_no_answer": "GREEN", "V3_distinctness": "GREEN", "S1_live": "GREEN"} | True |
| M2b_discard_the_copy_read_back | `app/V8Experience.tsx` anchor_hits=1 | V1_origin_error_5xx | **RED** | **KILLED_BY_THIS_ARM** | [] | {"V2_no_answer": "GREEN", "S1_live": "GREEN"} | True |
| M3_collapse_the_probe_back_to_silence | `app/V8Experience.tsx` anchor_hits=1 | S4_probe_speaks | **RED** | **KILLED_BY_THIS_ARM** | [] | {"V1_origin_error_5xx": "GREEN", "V2_no_answer": "GREEN", "V3_distinctness": "GREEN", "S1_live": "GREEN"} | True |

幸存臂不装作击杀：`M2` 的 `mayOffer=false` 没动任何一格，反而指出了真正的载体——V1 那句快照是 `boot` 回读到本地副本（`setCachedCopySaved(Boolean(saved))`）撑起来的，所以补了 `M2b` 直接丢掉那次测量，V1 才红。

聚合：arms_total=4 / 已证逐字节还原=4 / 缺还原证明=[] ⇒ all_byte_exact=True；还原后工作树 `git status --porcelain` = `M frontend/src/api/citynexus.ts
 M frontend/src/app/V8Experience.tsx
 M frontend/src/i18n/LocaleContext.tsx
 M frontend/src/lib/failureAttribution.ts
?? frontend/dist_mut_M1_deadline/
?? frontend/dist_mut_M2_copyfact/
?? frontend/dist_mut_M2b_copyreadback/
?? frontend/dist_mut_M3_probe/
?? frontend/dist_ord0263_post/
?? frontend/dist_ord0263_pre/
?? frontend/src/lib/readDeadline.ts`

## 6. 六面读数（ORD-0254 那套分母），修前 vs 修后

| 面 | 修前 | 修后 | 该面自己印出的证据 | 正文是否逐字相同 |
|---|---|---|---|---|
| today | reached=True operable=False | reached=True operable=False | ["还没有安排", "取自服务器场景"] | True |
| journey | reached=True operable=True | reached=True operable=True | ["行程工作台", "方案健康度"] | True |
| map | reached=True operable=True | reached=True operable=True | ["地图 · 一目了然", "尚未获取地图位置"] | True |
| ai | reached=True operable=True | reached=True operable=True | ["已核验的行程事实"] | True |
| wallet | reached=True operable=True | reached=True operable=True | ["我的行程与偏好", "已确认的预订"] | True |
| simulation | reached=False operable=False | reached=False operable=False | [] | True |

点名不包装：
- entered the journey through the sealed-demo control
- simulation: no hit-tested control matched words ["模拟","Simulation"]; labels seen: ["菜单","跟随系统","EN","DE","启用 Web Push","×","询问 Copilot","今天","行程","地图","Copilot","我的"]
- simulation: no hit-tested control matched words ["模拟","Simulation"]; labels seen: ["菜单","跟随系统","EN","DE","启用 Web Push","✦ CityNexus Copilot","今天","行程","地图","Copilot","我的","关闭","今天","实时行程","地图","行程工作台","住宿选择","城市探索","旅行票夹","Copilot","恢复与执行","智能守护","旅行者画像","行程","我的"]
- simulation: opened the 菜单 drawer and looked again
- `today` 那一面的 operable 按构造不可测：进入行程后我就停在 hub，同页再点「今天」正文不会变；**从别面回到今天那一腿我没测**，这一格是空缺不是绿灯。
- `map` 历史上就是红的，修前后同字：`尚未获取地图位置` + `这个行程还没有可信的坐标` ⇒ 不当回归。

## 7. 边界与未做

- HARNESS 附带那格（整站下线访问深链 `/v8/hub` 没有 SW 兜底）**未动**，指挥官已列待仲裁。
- ORD-0266（sheet busy 标志无引用计数）归 D，未动。
- S3 的 DNS 失败与"加载后连接被拒"两变体未造；我的期限对三者同形，但只有 timeout 这一种被量过。
- 写请求（POST/PUT）不带期限：那会把"客户端放弃"伪装成"服务器没做"，属幂等题目。

## 8. 工件清单（发布前本机 blob）

- `capture_M1_remove_the_per_read_deadline.json` blob `1413aad9ea2e538fcb7523f03aac3242968b4132` 12,086 B
- `capture_M2_force_the_cached_copy_fact_false.json` blob `01c456bcb6df74c5ae2c18b81e64325e9efe21cf` 13,678 B
- `capture_M2b_discard_the_copy_read_back.json` blob `87cf10d8370618a69167d869bec122113be69757` 14,773 B
- `capture_M3_collapse_the_probe_back_to_silence.json` blob `0ff80bcebec16e29d13df7138a4b95f5ce1e8544` 13,800 B
- `capture_post.json` blob `54199b966f89b60b42005727285d90c2f07e7da4` 13,837 B
- `capture_pre.json` blob `ef46e4d0dd18bd0778f67f8f64ac85854519c5e3` 11,922 B
- `ord0263_verifier_selftest.json` blob `b47c3a22caed2b941ff94a2c85375c5956a01594` 2,677 B
- `ORD_0263_B_FIX.md` blob `fa9fc31d9bd6ddab8e49484da46083f8268f2c26` 16,726 B
- `q263_reverse_mutation_receipt.json` blob `b73e5d4e414503ca099463ea1a8ec199135b578b` 7,187 B
- `raw_reads_M1_remove_the_per_read_deadline.json` blob `68d809d3c8bc9ca199760c1aa39af7e15132c7a7` 14,544 B
- `raw_reads_M2_force_the_cached_copy_fact_false.json` blob `9bac2d638ea722037191acd283d286f0ef4c4464` 16,537 B
- `raw_reads_M2b_discard_the_copy_read_back.json` blob `094fc54879d3309911c18a8c9c2fd037b2bf08ac` 17,316 B
- `raw_reads_M3_collapse_the_probe_back_to_silence.json` blob `18ec9a5627a4326504b63273b5754e40c096ceda` 16,613 B
- `raw_reads_post.json` blob `288b45f89ca8d4b07bdfd1e131839f28f33c66be` 16,680 B
- `raw_reads_pre.json` blob `739c3df432ec90fada41cee482ae135fb1d997b4` 14,158 B
- `read_M1_remove_the_per_read_deadline_enter.json` blob `4cc9c256f6c8352315a682d1d11941e45c1528a4` 3,365 B
- `read_M1_remove_the_per_read_deadline_S1_live.json` blob `86d7278412d6dcf1c7e38a9125a0a8fff8d77940` 2,871 B
- `read_M1_remove_the_per_read_deadline_S1_live_restored.json` blob `d3fbfd89b6197ef267c8b55550e7a82fc4a9c512` 2,821 B
- `read_M1_remove_the_per_read_deadline_S2_origin_error.json` blob `0820a3241dd5bfaa84e583ac898fb23593bc5f8e` 2,370 B
- `read_M1_remove_the_per_read_deadline_S3_no_answer.json` blob `f7d6076ae2ff796840b7d67af00e1af4feb68450` 1,371 B
- `read_M1_remove_the_per_read_deadline_S4_probe_speaks.json` blob `3688bebd9b461decf372080e7126bed03b30a336` 1,343 B
- `read_M2_force_the_cached_copy_fact_false_enter.json` blob `d147d485a9f7eade7f0751560245727f1f92c486` 3,369 B
- `read_M2_force_the_cached_copy_fact_false_S1_live.json` blob `e48b6343a6a896d203869b7276f977f6e3a9f9e3` 2,830 B
- `read_M2_force_the_cached_copy_fact_false_S1_live_restored.json` blob `afe7c77aef0ac5ae5c9e0d56e50bfa341c05c500` 2,757 B
- `read_M2_force_the_cached_copy_fact_false_S2_origin_error.json` blob `13cd39da19d99ddeea57dff5bb5932796efcfe9f` 2,306 B
- `read_M2_force_the_cached_copy_fact_false_S3_no_answer.json` blob `7ddecd41b68cf49c77db12555594ecf3774ce234` 2,541 B
- `read_M2_force_the_cached_copy_fact_false_S4_probe_speaks.json` blob `a8cedc00a237caa5ae4b722bfdae0945d9574ca9` 2,305 B
- `read_M2b_discard_the_copy_read_back_enter.json` blob `1844a844013daa52713ed16c578b212aab5a6471` 4,546 B
- `read_M2b_discard_the_copy_read_back_S1_live.json` blob `3ab676be7a0e5bb40331f1cfabc2aa13f822b80a` 2,870 B
- `read_M2b_discard_the_copy_read_back_S1_live_restored.json` blob `caa252b82cc7d89a36eeb2e29abfb7adf0918455` 2,751 B
- `read_M2b_discard_the_copy_read_back_S2_origin_error.json` blob `d3f32372fa520ee58ab3bbb441b2cbbdc2c81c06` 2,138 B
- `read_M2b_discard_the_copy_read_back_S3_no_answer.json` blob `04729123a864427ba6bc79082699f823cea8f24c` 2,359 B
- `read_M2b_discard_the_copy_read_back_S4_probe_speaks.json` blob `b000904e7679d546ac0f118e6849b7c32e7843d3` 2,137 B
- `read_M3_collapse_the_probe_back_to_silence_enter.json` blob `607b35cf51e5f713096988d229025c72e813ec3f` 3,371 B
- `read_M3_collapse_the_probe_back_to_silence_S1_live.json` blob `caf57eedd0a8866c464079d0cf2ed14f42227efe` 2,877 B
- `read_M3_collapse_the_probe_back_to_silence_S1_live_restored.json` blob `b26dd33e77ff9d9171d7ecfc86672064514ca902` 2,759 B
- `read_M3_collapse_the_probe_back_to_silence_S2_origin_error.json` blob `8db36987a4d16533bca1e1837d08a501d9d87393` 2,375 B
- `read_M3_collapse_the_probe_back_to_silence_S3_no_answer.json` blob `5d06b1c33bd3982efff6c1304113c9ca4a23051c` 2,543 B
- `read_M3_collapse_the_probe_back_to_silence_S4_probe_speaks.json` blob `7c7d0f51879b8b0b7a221e2d724c70e849dbdc51` 2,259 B
- `read_post_enter.json` blob `44731850c27eeb87991d5977ba4f8fd9802cbcef` 3,337 B
- `read_post_S1_live.json` blob `384dcfe659b9966b9588a256ee47fd61ccb2794b` 2,844 B
- `read_post_S1_live_restored.json` blob `36770b8f6934f8cb3e059ef746e3a822f05927cc` 2,875 B
- `read_post_S2_origin_error.json` blob `9b0b47d563bcf232e292d93985d7eb6d0763976e` 2,343 B
- `read_post_S3_no_answer.json` blob `20386f78be1257ba3c79eca44c98af574a5faab4` 2,510 B
- `read_post_S4_probe_speaks.json` blob `e3699cd8fb5fcd4b4713b12a802acea4f169e4f8` 2,342 B
- `read_pre_enter.json` blob `b27ddbde2ffc6c22e84cb61ced9107a5e52b6765` 3,337 B
- `read_pre_S1_live.json` blob `4f7aa98342252ff42e0f79f2cca99f2e00b119a4` 2,843 B
- `read_pre_S1_live_restored.json` blob `058a1f9351023a3d2767002e5548952a593554af` 2,874 B
- `read_pre_S2_origin_error.json` blob `da79cf7b88020d38cfc358c3b4421140ade76472` 2,044 B
- `read_pre_S3_no_answer.json` blob `1cfa6fd6d3c882080812e1d5e28d2ea62e09ea01` 1,343 B
- `read_pre_S4_probe_speaks.json` blob `0b371f5813427227796290d592d9287a1893154f` 1,315 B
- `sixface_post.json` blob `b941205dbf8728b155f55c1d1744b3e2babff72a` 8,150 B
- `sixface_pre.json` blob `175edc7fbb4abb9649602bf0af5e0844c1c31293` 8,144 B
- `surface_receipt.json` blob `64bff8725c40fb8e258dbc8fc6e5ab416d81d6ef` 1,774 B
- `verdict_M1_remove_the_per_read_deadline.json` blob `35c76b353aa14ee0d5317e95891800d99043bb64` 2,583 B
- `verdict_M2_force_the_cached_copy_fact_false.json` blob `87d351aadb914511f0df58a051db986414ea9a6b` 2,682 B
- `verdict_M2b_discard_the_copy_read_back.json` blob `4ca6421bc739a02312affd2b5e25a3eb6bfa7251` 2,672 B
- `verdict_M3_collapse_the_probe_back_to_silence.json` blob `9f88b9ffb17d6a6f9f2b72f87dc4183bb6079026` 2,692 B
- `verdict_post.json` blob `7b5faad7698d5971b8658cacdedfd197dfcb9881` 2,620 B
- `verdict_pre.json` blob `5ca63d6f823c68aa3ee7396e1b17112459079091` 2,527 B
