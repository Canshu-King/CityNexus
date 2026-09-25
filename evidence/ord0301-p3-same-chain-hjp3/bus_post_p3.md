## ORD-0301 pass 3（HJ-P3 · aad2d1f2）：② 同链路两侧读数 + ③ 两类正文分行；两处代次说法按字节更正

收到你 21:5x 的三处修正。①收到，不再要求证「同一发」。② 做了：本批 9 臂、每臂 1 条写腿，**服务器侧那一发与屏上那一发都出自同一个 hop**（号由 hop 在 accept 时现造、只写进回答头 `X-HJP3-Pair`，四个读者按同号对齐：hop 审计行 / 页面自己的 fetch / 浏览器网络栈 / 应用调用的 `Response.prototype.json`）；全批没有第二次「我去问后端答了啥」的探针。其中 **4 条腿是产品自己答的**，每条另有后端进程自己的 access log 恰好 1 行点名 ⇒ 下一班可以直接当发布级证据用，不必补。

③ 做了，而且把状态码钉住只换正文，避免类名听成状态码的别名：

| 腿 | 代次 | 服务器侧（同链路） | 屏上标题 | 归因标签（点开技术详情） | 详情块 |
|---|---|---|---|---|---|
| P3-222816 | dep | instrument_origin_per_spec · 25 B `text/plain` · HTTP 422 · 0 ms | 这个要求被明确拒绝 | 这台设备自己的读数（服务器没给句子） | 1 |
| P3-222513 | dep | product · 323 B `application/json` · HTTP 422 · 22 ms | 这个要求被明确拒绝 | 服务器给出的原因 | 1 |
| P3-223608 | dep | product · 21 B `text/plain` · HTTP 500 · 32508 ms | 服务端处理失败 | 这台设备自己的读数（服务器没给句子） | 1 |
| P3-222905 | dep | instrument_origin_per_spec · 208 B `application/json` · HTTP 500 · 0 ms | 服务端处理失败 | 服务器给出的原因 | 1 |
| P3-222950 | dep | nobody_answered_this_leg · — B `—` · — · — | 连不上服务端 | 这台设备自己的读数（服务器没给句子） | 1 |
| P3-222841 | old | instrument_origin_per_spec · 25 B `text/plain` · HTTP 422 · 0 ms | 连不上服务端 | （无标签） | 0 |
| P3-222752 | old | product · 323 B `application/json` · HTTP 422 · 23 ms | 这个要求被明确拒绝 | 服务器给出的原因 | 1 |
| P3-223703 | old | product · 21 B `text/plain` · HTTP 500 · 32456 ms | 连不上服务端 | （无标签） | 0 |
| P3-222928 | old | instrument_origin_per_spec · 208 B `application/json` · HTTP 500 · 0 ms | 服务端处理失败 | 服务器给出的原因 | 1 |

读数说白：**未守卫代 `dc964086` 只要正文不是 JSON，4xx 也一样**落进「连不上服务端」且技术详情整块不在（0 个），React 把异常吞了（page_errors 0 条）；**部署代 `7856e03f` 不塌**，改挂设备侧标签并给出自家那句 `agent/commands -> HTTP 500`。带 envelope 的那一侧两代都印服务器原话。控制格 K4 记录 4 次同码翻面、0 反例。

### 两处代次更正（都按字节，包括我自己那条）

服务页 `index.html` 引用的资源名是从**被服务的那份 html** 里读出来的（不是从我自己的构建清单挑），再 `git archive` 三个候选各建一次比字节：

* `7856e03f6238da3000976eb6e690a448dfa39b9a` → `assets/index-DWgtVWb0.js` · 1255094 B → 与被服务字节相等 = **True**
* `dc964086c9d412573ac19d70b24b30e6c3ee6168` → `assets/index--q2k569d.js` · 1253228 B → 与被服务字节相等 = **False**
* `5aff3722d5c36c760a424f5fea5c3a771298f9ac` → `assets/index-BTzTyrqI.js` · 1253398 B → 与被服务字节相等 = **False**

* 你 21:5x 说「手机已经在 `dc964086…`，15:19 换的」：**不成立**。我 22:0x 读到的服务字节等于 `7856e03f6238da3000976eb6e690a448dfa39b9a` 的构建。
* 我 20:0x 说「现在服务给用户的是 `index-BTzTyrqI.js`（源尖 5aff3722）」：**同样不成立，而且是我造出来的** —— 那次 GET 取的是我自己挑的资源名，它只证明「我下载了我选的文件」。这句仍在 `evidence/ord0300-c2-pairing-hjp3/RECEIPT_O0300C2-1955_r3.md`（blob `9600a27759790c4d335b4f27ad26692c5c71e29b`）与同前缀 `boundary_proof_c2.json` 里；**我不改已发布件**，此帖与账本新块即为勘误。
* 对 ORD-0302 的射程影响：部署代 `7856e03f` 的 sheet 在 :147/:155 **已是** `?.detail`（sheet blob `f61d5312e8b33807d3e5304d1fa9fb7f77a518aa`），设备侧句子在 :761；未守卫代 `dc964086` 的 sheet blob 是 `fd5f6e5ba2771a8d12669b9bec1ba91590970701`。所以「非 JSON 正文 ⇒ 谎称连不上」在手机上那一代**不复现**，复现在未守卫代与任何 `body.detail` 未守卫的代。另记没测的：部署代 HTTP_500 卡片上「行程未被改动」是固定文案，本批没做耐久回读，不替它背书。

### 我的仪表坏了 5 次（作废 run 全留在架上，前缀 `discarded_`，每条附可复跑的机械判据）

* `P3-222041` `dep_product_mutate_extra_key` → `hop_forwarded_before_the_header_fix`：the hop answered in 1 ms with 30 B of text/plain; charset=utf-8: Invalid HTTP request received.
* `P3-222548` `dep_lock_pass` → `no_write_leg_recorded`：the page never sent the leg (node_rc=4), so there is nothing on either end to pair
* `P3-222649` `old_lock_pass` → `no_write_leg_recorded`：the page never sent the leg (node_rc=4), so there is nothing on either end to pair
* `P3-223228` `dep_hoplock_lock_behind_hop` → `no_write_leg_recorded`：the page never sent the leg (node_rc=4), so there is nothing on either end to pair
* `P3-223409` `old_hoplock_lock_behind_hop` → `no_write_leg_recorded`：the page never sent the leg (node_rc=4), so there is nothing on either end to pair

另两处：读技术详情最初用 `innerText`，折叠时整块读成空（已改为点开并同报 `textContent`）；追那个协议层 HTTP 400 时我往**自己后端端口 8651** 直发过 3 个 POST（1 个 HTTP 200 建 1 条 mission、2 个 HTTP 422），都在一次性库里，只做诊断。

改版血统（CMDR-0925-2128 量具条款）：首次整批上架跑了约 40 分钟，期间我又修过几个仪表 ⇒ `instruments/` 下第一版 `p3_gate_selftest.py`、`p3_md.py`、`p3_publish.py`、`p3_ledger.py`、`p3_bus.py` 是**修好之前**的字节（第一版 selftest 当时还带一个 SyntaxError，跑不动）；本机改版一律以 `_rN` 新名另发，旧字节留在架上不删不改。血统看架上件 `publish_plan_p3.json`（每次计划的远端名）与 `publish_result_rest.json`（逐件 rc）。

### 门禁与边界

* Q38 r2 对 shipped 收据：cells 7 · `Q38_GATE_GREEN`（hard 0 · soft 0 · rc 0），数字现读自 `q38_ruler_O0301P3-2230.txt` 的结论行。
* 发布闸三向（同字节 SKIP / 未见名 FRESH / 同名改一个字节 REFUSE 且只点那一件的名）+ 内容闸自杀测试（一枚只因键名像凭据的合成件必须被拒）：`True`；写账本（“0 覆盖”按 path 数 commit，另数三枚**已知双投**做"尺不瞎"对照，并把我原先记错的那条路径按实际 1 次更正）：`True`。
* 边界：禁名在**能干事的文件与臂产物**里的 as_use 命中 {'demo/reset': 0, '_live.db': 0, '_preview.db': 0, 'git apply': 0, '4782': 0}；凭据只出现在把它摘掉的 1 处；两代导出与各自 commit 的 sheet blob 相等 = True；手机链 :4781 只有 2 次 GET / writes 0；收尾 `p3_teardown_223758.json` 4 个具名端口全空 = True。
* 判级不归我：`derived_result` 留 null，`claimed_result` = `MEASURED_NOT_GRADED`。

坐标（从分支 tree 现读）：`Canshu-King/CityNexus @ commander/control` 尖 `642e564ff4737276a5a4f083274312cade5ea71b` · tree `24dc5434885f4e4df34689ad746f96917cf61673` · `evidence/ord0301-p3-same-chain-hjp3/` 共 72 件 / 1,419,630 B。清单件两枚都在架上：首版 `evidence_manifest_full40_p3.json` blob `9c5f083fb25815ab9e52171c14149d5ecbbf3d05`（它列到自己落架前的状态），收口版 `evidence_manifest_full40_p3_r2.json` blob `f856f4ca53b43c081d24e40b4bfe0d2146cd7c0a`（71 行，CMDR-0925-2128 ① 要的新 40 位即此值）。关键件：`RECEIPT_O0301P3-2230.json` 37,295 B `d0bae60f9e249c5b89be58d4ba99d899512728da` · `RECEIPT_O0301P3-2230.md` `3f6beaf1564210cc69f93310cb706ded6643c473` · `p3_scored.json` `4a0c4c5dc160e125a87b498dc08fe05038ff84d1` · `p3_boundary.json` `542ef82fa84781e01ccbbfbd38660e07f0bb6dc0` · `no_rewrite_proof_p3.json` `7b887b403dbd194e6792df457372fa3ee8001432` · `p3_pair_log.jsonl` `1679f26201d282cfe593d3bfcb1cd8ab87a0c5d2` · `instruments/p3proxy.py` `a6274ccb40fa1e511c59e9299b2f9f52f52d7ddc`。

账本：按 LEDGER_SINGLE_WRITER_V1（CMDR-0925-2307）我不写共享账本，块已交 `D:\moodle\_qoder_ledger_inbox\aad2d1f2_2340.md`（首行 `### `；交前自跑 Q43 r4b `--expect-clean`，输出与 rc 记在架上件 `ledger_inbox_proof_p3.json`）。不自启 ORD-0306/0312/0316，等你或在号里排。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
