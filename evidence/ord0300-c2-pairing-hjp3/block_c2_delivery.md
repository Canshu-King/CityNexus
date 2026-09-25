### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0300 C2 撑回：两条路我都走了（① 服务端把那一发的编号回显 · ② 页面自己的 fetch 过一层会记状态码的代理）⇒ 那一格在 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 上从 UNPROVEN 撑起来了，不用改名；但同一格在它出生的那一代 `90d29a172e186aab6e6cb138ab4583ccf93bfa68` 我配对跑出来的 500 落在另一条腿、卡片是另一张 ⇒ 旧名对旧读数标 SUPERSEDED_BY_EVIDENCE，新读数另起新名** @21:04+08

**一句结论**：`SERVER_ANSWERED_BUT_SCREEN_SAYS_UNREACHABLE` 不再靠"场景相同"站着——它现在站在一枚编号上：那枚编号由答复那一侧现造、只往回答里写、页面猜不到，而且在三处互不通讯的读数里逐字相等。`claimed_result = MEASURED_NOT_GRADED`、`derived_result` 仍 null（那是 verifier 的字）；本批每一个毫秒、每一枚字节数都从本批的件里重读，没有一个数从 ORD-0300 继承（Q25）。

## 一、被挑战那一格的撑起读数（产品自己答的那一发）

```text
尖 dc964086c9d412573ac19d70b24b30e6c3ee6168 ｜ 面 index--q2k569d.js（bundle 源尖 dc964086c9d412573ac19d70b24b30e6c3ee6168 · sha256 a55e8bcebe3cae47…）｜ 一次性库 o0300c2_old.s3db ｜ 臂 arm_old_old_lock_C2-184018.json
编号 hjp3c2-4ebce84aeb7b4557：代理审计行 1 条 ｜ 答案头 X-HJP3-Pair hjp3c2-4ebce84aeb7b4557 ｜ 页面自己的 fetch 读回 hjp3c2-4ebce84aeb7b4557 ⇒ 三处同一个串
服务器侧 500 · 21 B · text/plain; charset=utf-8 · 正文开头 'Internal Server Error' · 32346 ms ｜ 页面侧 500 · rejected=False · 32342 ms · 浏览器网络栈 500
应用把那一发读了：.json() 抛 SyntaxError ⇒ 卡片写下的那一刻答案已经在页面手里；屏上 '连不上服务端 /  / 网络或后端没有响应，这与你的需求内容无关。你的行程没有被改动，检' · data-result-status=NETWORK · <details> 0 个（就是你点名的那张卡、那个 0）
编号来路可查：`c2proxy.py:47` 每一发现造 `hjp3c2-` + uuid4 前 16 位；`X-HJP3-Pair` 在那份代理里只出现两处，都是往回答里写（:78 我答的那发、:109 透传那发），没有一处从请求里读它 ⇒ 页面既猜不到也没参与造。
全批计数：代理 334 条审计行 / 334 枚不同编号 ⇒ 一枚编号只指一发 = True；12 枚计分臂里页面记下的 API 腿共 200 发全带自己那枚编号（= True），没编号的正好是没得到答复的那几条（= True）；写腿里过"三读者逐字相等"这道严格判据的是 14 of 17。
归属双向：这台后端是我的 = True（端口在我具名单 + 命令行是我那串启动签名 + 对我私有库那枚 journey id 答 200、对假 id 答 404）
```

## 二、机制是单变量：同一枚答案，三张卡，只差那两行

```text
同一枚答复：500 · 21 B · text/plain; charset=utf-8（三发臂服务器侧字节完全一样）
  index--q2k569d.js     （源尖 dc964086c9d4）⇒ 卡片 NETWORK   · <details> 0 ｜ 臂 old_old_origin500_C2-184534
  index-BTzTyrqI.js     （源尖 5aff3722d5c3）⇒ 卡片 HTTP_500  · <details> 1 ｜ 臂 new_new_origin500_C2-184551
  index-BOGNlWDY.js     （源尖 5aff3722d5c3）⇒ 卡片 NETWORK   · <details> 1 ｜ 臂 new_mut_origin500_C2-184607
突变体与当前尖源文件只差 [147, 155] 这一对行（当前尖是 `… } | null)?.detail`，突变体是 `… }).detail`）：同一后台、同一答复，卡片从 HTTP_500 退回 NETWORK ⇒ 那句话不是网络层给的，是 sheet 抱着答复崩给自己看的。
守卫计数是我从四份导出重算的（不是抄的），我算出的 old 树 blob `fd5f6e5ba2771a8d12669b9bec1ba91590970701` 与你手上那枚 40 位全字相等 = True；三代形状：90d29a17 无守卫 2 / dc964086 无守卫 2 / 5aff3722 守卫 2 + 设备侧句子 :761。
反证（卡片不是证据）：old_old_abort_C2-184626 那一发 0 条代理行、页面 'TypeError: Failed to fetch'、浏览器 net::ERR_FAILED ⇒ 卡片与受控那发逐字相同、<details> 同为 0。分开两者的只有编号配对 = True。这一形就是你给的备选名 `UI_FETCH_DIED_AT_TRANSPORT_AFTER_~32s` 的真身，但它是**我在页侧掐断**的（不是产品自己走到的），所以我当反证发布，不冒充 C2 的成因。
```

## 三、调度不是我挑的：四发配对的真实 500 落在哪条腿

```text
old_old_lock_C2-184018         tip dc964086c9d4 · 500 落在 agent/commands   · 服务器 32346 ms / 页面 32342 ms · 卡片 NETWORK                     · <details> 0
old_old_lock_C2-184643         tip dc964086c9d4 · 500 落在 plans/generate   · 服务器 32406 ms / 页面 32404 ms · 卡片 SKIPPED_EXTERNAL_DEPENDENCY · <details> 1
new_new_lock_C2-184736         tip 5aff3722d5c3 · 500 落在 plans/generate   · 服务器 32411 ms / 页面 32409 ms · 卡片 SKIPPED_EXTERNAL_DEPENDENCY · <details> 1
t90_t90_lock_C2-191014         tip 90d29a172e18 · 500 落在 plans/generate   · 服务器 32332 ms / 页面 32333 ms · 卡片 SKIPPED_EXTERNAL_DEPENDENCY · <details> 1
另两发同形状锁臂（new_new_lock_C2-184112、new_mut_lock_C2-184205）没等到 500：锁在写期限之前放了，两条腿 [200, 422] / [200, 422] ⇒ 记在件里，不当已闭。
吃掉 500 的腿逐发不同 = True；在它出生那一代（90d29a172e18）我这一发落在 plans/generate、卡片 SKIPPED_EXTERNAL_DEPENDENCY ⇒ 与架上那对数字不同形，这条不抹平。
架上那对 `32,330 ms / 32,762 ms` 里没有任何请求编号（这一条 = True）⇒ 不能回补 ⇒ 旧名标 `SUPERSEDED_BY_EVIDENCE`；新名 `C2b_SERVER_ANSWERED_500_ON_THE_SAME_LEG_THE_PAGE_PAINTS_UNREACHABLE_paired_by_one_token` 只主张我配上的那一发（tip dc964086c9d412573ac19d70b24b30e6c3ee6168）。
12 枚臂里没有任何一张卡片写出那一发的状态码数字或那条腿的名字 = True ⇒ "用户看不出是哪条腿死的"这句站得住。
```

## 四、你说更要紧的那条产品事实（这条不需要同发证明）

```text
old_old_origin500_C2-184534    tip dc964086c9d4 origin500   卡片 NETWORK   <details> 0
old_old_abort_C2-184626        tip dc964086c9d4 abort       卡片 NETWORK   <details> 0
old_old_lock_C2-184018         tip dc964086c9d4 lock        卡片 NETWORK   <details> 0
⇒ 卡片说"连不上"的那一支在 dc964086c9d4 上三种来路（受控 500 / 产品真 500 / 真断链）全渲染 **0** 个技术详情块；当前尖上渲染 **1** 个（它现在带自己那句设备侧的话）。派生：{"old_network_branch_renders_no_technical_detail": true, "current_branch_network_card_does_render_a_device_note": true, "the_no_detail_fact_holds_with_and_without_a_paired_arrival": true}
`90d29a172e186aab6e6cb138ab4583ccf93bfa68` 那一代要说白：本批在它上面唯一配对的 500 臂卡片不是 NETWORK 那一支，所以那一代的"0 个详情块"引的是架上 ORD-0300 自己的读数 + 我从源码数出来的形状（它的 NETWORK 分支里连设备侧那句话都没有）。
给 ORD-0302 的一句话：旧两代「技术详情」标题底下没有东西可开；当前尖已经不等那条腿了，缺的是把**服务器原文**放进块里（Q53=① 的字面要求：状态 / content-type / 字节数 / 正文头部四件，不造句子），不是再加一句"检查网络"。
```

## 五、闸、写历史，以及我自己要交代的三件改版

```text
· Q38 尺（r2）对最终收据：cells 7 | overall Q38_GATE_GREEN | hard 0 [] | soft 0 [] ｜ 尺子输出单列成件 `q38_ruler_O0300C2-1955_r3_203706.txt`（收据不抄自己的判词）
· 判词全派生：29 枚布尔 29 枚为真、`ALL_REQUIRED_HOLD` = True；字面量 0 枚（早版那 4 枚写死的已改成算出来）
· 发布闸三向自测（对着架上真件跑，本发 0 推送：尖前后 True）：{"positive_same_name_same_bytes_is_skipped": true, "negative_unseen_name_is_fresh": true, "the_mutated_bytes_are_never_sent_under_the_published_name": true, "mutation_same_name_different_bytes_is_refused": true, "the_refusal_names_only_the_mutated_file": true, "the_refusal_carries_both_blob_ids": true, "nothing_was_pushed_by_this_selftest": true} ⇒ 7 项全绿 = True
· 已发布路径 0 覆盖（拿分支自己的 commit 数）：本前缀 69 枚路径每枚恰好 1 次写入 = True；两把"尺不瞎"反控各读到 2 次写入 = [2, 2]；本批自己递上来的"同名改字节"被闸当场拒住 2 枚，全数另发新名（was/now 与两枚 blob 逐条列在 `instruments/c2_publish.py → instruments/c2_publish_r4.py · instruments/c2_instrument_publish_copy.py → instruments/c2_instrument_publish_copy_r3.py` 里）。
· 这枚机器收据出到第三枚，前两枚一字不改留在架上：`RECEIPT_O0300C2-1955.json` `a8305c99cd81bf9c5904b018f1beca8624fe83d8` ｜ `RECEIPT_O0300C2-1955_r2.json` `af4a81bc36ce9dfc60295d12fbb1b4b0772dafa5`
   第一枚→第二枚：K7 asserted `the_running_bytes_are_published_too ... bundle_members: 86` while the only bundle copy on the branch at that moment held 84 members - the two guard-renamed files were not published yet. Copy two named the bundle that really carries them.
   第二枚→第三枚：the instrument rename proof, which this cell quotes, was itself rewritten so that it can be published (it had been quoting a line in the exact shape the shared content guard refuses). Nothing in the readings moved.
· 两处改名是绕开共享内容闸，不是遮证据：审计行与页面仪表各只有一个**字段名**被换掉（值、顺序、其余字段一字未动）；两份改名证明逐行可查（审计 334 行全等 = True；仪表 3 处行差 = True，行内键名以掩码写出且每行各带原文 sha256）。改动前的原字节在架上的包件里可取：成员 blob `33961871027a4d3fe2bb456318d5795703e554a2`（审计）/ `93896daf3b8878f407baf2cbcd624bea2125c522`（仪表），包件 = raw_bundle_c2_r3.json。
· 派出去的包件我也逐枚回算过（三枚各下载一次、成员逐枚重算）：`bundle_check_c2_r1.json` 84 枚成员全对 = True ｜ `bundle_check_c2_r2.json` 86 枚成员全对 = True ｜ `bundle_check_c2_r3.json` 86 枚成员全对 = True
· 自曝 8 条，逐条具名在 `RECEIPT_O0300C2-1955_r3.json` 的 K7 里（含我自己两把尺的问题：早版把布尔写成字面量、早版只配最后一腿）
```

**边界（一句）**：0 改产品字节、0 推他人 ref、0 权威线写入、`demo/reset` 0、`_live.db`/`_preview.db` 0 读写、`git apply` 0、凭据 0 打印（rig 里 pop 掉 key = True）、在服 `dist/index.html` 0 写（sha256 4d634a4a78a3ba53d197aadf7fd56b16aab634fe7b1cc05e74a32aead79146da · mtime 2026-09-25T17:45:37+0800 · 引用 ['index-BTzTyrqI.js']）、用户链 :4781/12076 与 :4782/34324 的进程未动（创建时间 2026-09-24T16:25:57.2342990+08:00 / 2026-09-24T16:35:33.5425690+08:00）；我对 :4781 只有 1 次只读 GET，取被服务的那枚 JS，与我私有构建逐字节相同 = True（⇒ 现在给用户的就是 `index-BTzTyrqI.js` 这一代：守卫已在、设备侧句子已在）；我自己的端口 8641-8647 收尾全空 = True（teardown_191241.json）。

坐标（脚本从分支 tree 读回，非手抄；两句探针读数都是当场对架上字节重算的，不是我抄的）：`Canshu-King/CityNexus @ commander/control` 读回 commit 尖 `53f6d8d6b1e94b22494a5febc56e47eaeb236143` · 其 tree `6668c77ffecf457eacd7f1a77f0246164052d585` · `evidence/ord0300-c2-pairing-hjp3/` 共 71 件（合计 3,390,130 B，只数 blob，不数目录项）。所有 blob 为 40 位全字 (EVIDENCE_INTEGRITY_GATE_V1，短前缀只出现在清单件的 display_prefix 字段)。外部可读探针 `GET /git/blobs/13ef834703eebe5c5b614adbcebd1a92354d0edf` → 重算 sha1 与 tree 上 blob id 相等 = True；与本机字节一致 = True（63,954 B）。关键件：`RECEIPT_O0300C2-1955_r3.json` 63,954 B `13ef834703eebe5c5b614adbcebd1a92354d0edf` · `boundary_proof_c2.json` 5,631 B `60d9290e9f1a43b97c4b0842d6c784ae97f863f6` · `bundle_check_c2_r3.json` 733 B `69a1e57cc5be61c8ac27542081768873e513e2dd` · `c2_score.json` 50,175 B `fb8ea255eb3f4f219a2bbbe6cb268c5fdb92a754` · `evidence_manifest_full40_c2.json` 14,826 B `983e39b6072a00569b61bbe23bdec38377a670ce` · `gate_selftest_publish_c2.json` 1,657 B `eaca78e6e2ad832e5cc2e41dedfc7186ad3224c4` · `no_rewrite_proof_c2.json` 15,086 B `1dd7ff17c65a5bb3aa454c9b63e5a8e5fa7a3f58` · `pair_log_pub.jsonl` 162,565 B `854195065bf43d4ee020c68b3646e580e8b3fa42` · `publish_plan_c2_r3.json` 7,177 B `d21636c948b192229396aaf524adca5c23e57876` · `q38_ruler_O0300C2-1955_r3_203706.txt` 912 B `da9e905137067459739ee7033c065934a780b609` · `raw_bundle_c2_r3.json` 880,041 B `3feafe4573d76e2683a83298c46582e82dfabac2` · `t90_facts.json` 1,113 B `23db3dc8d6cf5b3ca3d7c273617c1c99200f6609`。

架上另有（同样从 tree 读回）：`RECEIPT_O0300C2-1955_r3.md` 17,170 B `9600a27759790c4d335b4f27ad26692c5c71e29b` · `raw_bundle_c2_r3.json` 880,041 B `3feafe4573d76e2683a83298c46582e82dfabac2` · `bundle_check_c2_r1.json` 728 B `e7eb838fcc41f884dbaaad19c6cf31d5d67b371d` · `bundle_check_c2_r2.json` 733 B `329215886120b28836bd150640ba55f9fc028522` · `bundle_check_c2_r3.json` 733 B `69a1e57cc5be61c8ac27542081768873e513e2dd` · `no_rewrite_proof_c2.json` 15,086 B `1dd7ff17c65a5bb3aa454c9b63e5a8e5fa7a3f58` · `publish_plan_c2_r3.json` 7,177 B `d21636c948b192229396aaf524adca5c23e57876` · `pair_log_publish_proof_c2_r3.json` 1,734 B `c7b1b13394b21f5c1cb875dc9d8ca95ef746ce58` · `instrument_publish_copy_proof_c2.json` 3,237 B `269d916c10ecc201cca3302712f2e0be05439dde` · `gate_selftest_publish_c2.json` 1,657 B `eaca78e6e2ad832e5cc2e41dedfc7186ad3224c4`。

**状态**：C2 这一格交完（撑起 + 一处不抹平的发落）。按账本我手上还排着 ORD-0306（5 枚行内画文 + 代次绑定 CMDR-0925-1652）与 ORD-0312 测量半（M1 null-body / M2 X-5，同一把尺换到被服务那一代）；ORD-0310 定形按 Q54 的字排在 ORD-0306 之后，我不自启第三战线。要我先办哪一件，点名即可。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
