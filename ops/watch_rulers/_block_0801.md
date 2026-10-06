## 亲测 @2026-09-25 08:0x+08 —— **Q38=① 已落地成可跑仪器**（`receipt_cell_derivation_check_r1.py`），对它自己的两枚真工件双向出数：**0290 硬红 / 0293 无硬缺陷但有 3 格软红**；ORD-0294 的验收改用这台尺

### ① 仪器与坐标（全部已上 `commander/control`，逐字节回读相等）
```text
live_checks/receipt_cell_derivation_check_r1.py   17,346 B  35caa42c0697faf0a8eeb0929a3e11cb53c9709a
  evidence/q38-cell-derivation-gate/selftest_20260925_0759.txt        1,253 B  bcb539459638cb035d3a5aa01d398d612efc22c0
  evidence/q38-cell-derivation-gate/gate_on_ord0290_published.json    3,192 B  9e199e7003120f86f7a59390f09565df5340b3c1
  evidence/q38-cell-derivation-gate/gate_on_ord0293_second_observer.json 3,529 B  307cab6419b8037a4923e2079a917258542e4f4e
自检：**9 臂全过**（跑 9、过 9、失败列表为空，rc=0）。硬红/软红/豁免三态都有反例臂：
  S2 三格同一句 ⇒ DUPLICATE_WHY_LITERALS；S3 两句互指对方的哈希 ⇒ 软红 WHY_NOT_FROM_OWN_READINGS；
  S4 同一句 + 假的 derived_from ⇒ 硬红 FAKE_OR_INEFFECTIVE_DERIVED_FROM；**S5 同一句 + 每格引自己独有的读数 ⇒ 绿**（豁免通道真的能用，不是只会把东西判红）；
  S6 只有一格 ⇒ NOT_ASSESSABLE（rc=4，永不当成通过）。
```
口径落地为三档（比仲裁那句话更细，因为实测把 E 的好收据也蹭红了）：**HARD**=重复句 / 缺 why / 假 derived_from；**SOFT**=句子里没有任何可机器核对的 token、或 token 不在本格读数里；**INFO**=重复句但每格都引了自己独有的读数（豁免）。**软红不会打印带 GREEN 的字样**，谁都别想拿它当通过。

### ② 对两枚真工件的实测（不是演示，是判据）
```text
ORD-0290（HJ-P1，我拦停的那份，published bytes blob c893bde2… 18,750 B，本机副本 sha1 与之相等）
   3 格 | overall Q38_GATE_RED_HARD | 硬 1 [DUPLICATE_WHY_LITERALS] | 软 3 [WHY_CARRIES_NO_EVIDENCE_TOKEN]
   三格的 why 逐字节相同、且每格句子里可机器核对的 token 数 = 0 ⇒ **机器复现了我今晚靠肉眼发现的同一件事**
ORD-0293（红队第二观察者，published blob 2a316603… 6,031 B，本机副本 sha1 相等）
   4 格 | overall Q38_GATE_SOFT_FINDINGS | 硬 0 | 软 3（R1/R3/R4 的 `derived` 句里没有一个 token 出现在本格自己的读数里；R2 命中 2 个）
```
⇒ **两条结论我照实说**：(1) 拦停 0274 的判断现在有可跑仪器背书，不再是"我觉得"；(2) **我把 0293 当"正例"是偏高的**——它没有共享句（这是硬缺陷那一档），但它的每格句子确实只写了结论词，数字在 `measured` 里而没进句子。所以口径 (a) 若按字面做成硬门，会连今晚最好的收据一起判红。**我按"硬=重复句那一档 / 软=句子不引自己读数"来分档**，并且从下一单起要求句子自带数字（下面 ③）。仲裁若要 (a) 也判硬，回一个字即可，我把 `--strict` 上膛。
**自我更正一枚（如实）**：这台尺的第一版 `blob_sha()` 只对 `"blob %d\0"` 头做哈希、漏了内容 ⇒ 打印的 sha1 是错的（`b6fe549b…`）。修好后与 `git hash-object` 逐字符相等。**发布出去的三份 JSON 都是修好之后重算再发的**，旧的那次输出没有进任何收据。
**另记一枚副本账**：我手上曾有两份 0290 副本——`_incoming_o290.json` 16,744 B（sha `1e3d350b…`，早先下载的缩进版）与从 `commander/control` 取的 **18,750 B 正本** `_published_cmdr_copy_ord0290.json`（sha `c893bde2…`）。两份 JSON 解析后深度相等（差的是排版空白），**判据用的是正本那一份**，收据里 `local_blob_equals_published_blob: true` 就是把这件事钉住。

### ③ ORD-0294 的验收判据（现在就绪，来了就能机械跑）
```text
(a) 每格 `why` 必须自带该格自己读数里的具名值（哈希 / 行差 / 状态码 / 资源名 / 路由至少一个）；
(b) 任意两格 `why` 折叠空白后相同 ⇒ 必须每格另带 `derived_from` 且指向**只有本格有**的读数，否则我这边直接判硬红；
(c) 交付后我用 `--receipt <你的修订收据> --out ...` 出数，**尺红即不落地**；跑法与坐标见 ①。
```
红队 ORD-0295 交回来时同样走这台尺（普查类收据没有多格判决就不该被它管，尺会报 NOT_ASSESSABLE，我按 ORD-0295 自己的判据验收，不混用）。

### ④ 队列与纪律
**权威线未动**（`45b0a5e2…`）；本次只往 `commander/control` 新增 4 个文件（4 次 PUT 全 BYTE-LEVEL MATCH，0 覆盖 0 删除）；用户库 0 读写；`demo/reset` 0 次；凭据 0 打印（本次发布的文件里没有凭据，探针脚本不发）；手机链最后实测 **07:49 HEALTHY**；Q39（10:00 前只带 0274 一笔落地+换代，还是等 0292/0287 齐）已提，等仲裁回符号。
