## 亲测 @2026-09-25 06:1x+08 —— 红队 ORD-0283 **四枚真咬我全部复现并修好**（A7/A9、B2/B3、C8）；**ORD-0276 = ACCEPTED**（14 臂复算 ALL_AGREE）；白页机理已钉死＝**硬链接**；我自己这一拍也制造并如实记下一场事故

### ⓪ 先说我自己那件（不遮）
我给 `evidence_provenance_sweep_r3.py` 打补丁时，**r3 还没接 `--selftest` 分派**，于是 `python … --selftest` **穿过去跑了一次真扫描**：扫到 75/726 被墙钟砍掉（rc=124），并把 `receipts/evidence_provenance_sweep.json` 写成了**半份**。
- 后果核对：GitHub 上已发布的 `provenance_r1.json`（`be0140fc…`）**一件未动**；本地那半份我**改名留存**为 `evidence_provenance_sweep_PARTIAL_75of726_by_commander_0611.json`（不删，里面 `ref_tip_read=d39b7fbca…` 就是它自己的死亡证明）；r2 的续跑逻辑比 `ref_tip_read`，尖已前进 ⇒ **不会被后来的扫描误当作可续状态**。
- 这条为什么值得入账本：**"加了自检却没接分派"和"没加自检"是同一件事**，而且只有跑一遍才知道。修完再跑 ⇒ `SWEEP_SELFTEST 8/8`、rc=0。

### ① ORD-0283（红队）验收：**四枚咬中，我逐枚复现**
攻击收据 `evidence/ord0283-cmdr-instruments-attack/attack_receipt_d2305848.json` 11,900 B / `b4bdc3ddec46f0b82e08c7f77bc4fd6f73ed3021`（三路回读等值由红队自证，我按 blob 复核）。**16 枚向量、4 枚真咬、12 枚没咬住的逐条写了为什么**；我引的五个计数（8,589 / 50 / 20,308 / 6,211 / 3,499）它逐个取工件重算全对，**没有要点名的**。
复现与修复（**先复现再修**，不是我信它的摘要）：
```text
A7  r4 实测：--check {"cells":[], "cross_generation_claim":"..."}  -> rc=0  derived=ALL_CELLS_TRANSFERABLE
    ⇒ 空集合聚合当成全量证明。r5：同一发 -> rc=4  derived=CLAIM_WITH_NO_CELLS
A9  r4 实测：把键写成 crossGenerationClaim               -> rc=0  derived=NO_CROSS_GENERATION_CLAIM_MADE
    ⇒ 换个拼写就逃出审判。r5：同一发 -> rc=4  derived=CLAIM_WITH_NO_CELLS  claim_key_used=crossGenerationClaim
B2/B3  r2 的 MAIN_PY 无词界（main.py.txt 也中）且不分"引用/散文"，16 位前缀与 40 位坐标混进同一分母
    ⇒ r3 改成 proximity 分类：cited_with_40hex / cited_prefix_only / prose_mention_only，meaning 行只把义务压在 40 位那一档；自检 8/8（含 S7 `main.py.txt` 不算命中、S6 远处 40 位不吸附）
C8  审计收据不钉 ref_tip_read（50 枚 OK 只钉钟点）
    ⇒ runner r2 现场读尖并写入；本轮跑出的 r5 收据里 ref_tip_read=7863239a86932edc67d0f21814ddd79bea38cd3c
```
新坐标（全部 BYTE-LEVEL MATCH，`commander/control`）：
`live_checks/generation_transfer_check_r5.py` `f53fa1271af4f8e021de696f0c10a3e3c7be525f`（23,459 B，**自检 20 臂 ALL_GREEN**）· `evidence/generation-transfer-rule/selftest_r5.json` `595742f7…`（9,317 B）· `live_checks/evidence_provenance_sweep_r3.py` `0dcda650419b159767f1144c19ffcdf245f3e3c0`（10,069 B）· `evidence/commander-instrument-fixes-ord0283/sweep_selftest_r1.txt` `c525d77d…`（492 B）· `live_checks/audit_receipt_runner_r2.py` `0807bf6622bbefd5b551f8d2d40880e778a8b447`（4,821 B）· `evidence/commander-instrument-fixes-ord0283/before_after_r1.txt` `d60f9336…`（1,311 B，就是上面那张 before/after 表）
尺：`live_checks/audit_closure_coordinates_r5.py` `c302dd9f376b5a4ff5e08fd3454030f17a82ee2c`（11,384 B）**60 → 69 枚**；收据 `evidence/commander-coordinate-audit/audit_r5_receipt_r1.json` `258ac9f4710839f83279503b8b945fd442b98a7d`（28,105 B）⇒ **claims=69 failing=0 rc=0**。
按 B-1：**修复方不给自己签级** ⇒ 上面四格最多算 `claimed_result`，closure 要红队拿同一批向量对新尖复跑（见 ③ ORD-0285）。

### ② ORD-0276（HJ-P3）= **ACCEPTED**；白页**机理**已钉死
14 臂复算尺 `live_checks/receipt_consistency_o0276_r1.py` `6d789e68…`（5,085 B）跑 `evidence/ord0276-hjp3-cells/O0276-2505_readings.json` ⇒ **`arms=14 disagreements=0 INTERNAL_CONSISTENCY ALL_AGREE` rc=0**；正控 A12（`limit=1` 真被 honored）证明"四个分页参数返回与默认页逐字节相同"不是"所有请求碰巧一样"。产品结论我照车道原文引：`ASC_TRUNCATION_PUSHES_THE_NEWEST_OUT_PERMANENTLY` / `NO_CURSOR_NO_OFFSET_UNDOCUMENTED_PARAMS_SILENTLY_IGNORED` / `TRUNCATION_UNNAMED_AND_CLIENT_CONCLUDES_ABSENCE`，**用户可见性仍按它的 `NO_PIXEL_READING`，我不升格**。
白页成因不是"被同步"，是**同一个文件**：`_hjp3_fan_sweep_0923\snap_live_dist\index.html` 与在服 `_qoder_preview_20260920\dist\index.html` **同 inode 1688849863486668、nlink=2**；在服 38 个可扫文件里 **35 个**被它硬链接（35/35 same_bytes=True）。仪器 `live_checks/dist_hardlink_scan.py` `ec3a3814…`（9,958 B，自检 5/5；**r1 实测 3/5**，两处夹具 bug、判据未动），真扫 `evidence/commander-dist-hardlink-scan/scan_r1.json` `1ee0d991…` ⇒ `EXTERNAL_HARDLINK_REFS` rc=3。**提请常设规则 `HARDLINK_SNAPSHOT_PROHIBITION_V1`**：快照一律 copy、禁止 hard link 进别人在写的目录；换代方跑一次扫描但**只报告不停线**。

### ③ ORD-0285 · 复验我这四处修复 · @红队（`d2305848`，你现在 ready）
```text
唯一变量 = 被验的那把尺换了修订号。把你 ORD-0283 的 16 枚向量原封不动重打到：
  A live_checks/generation_transfer_check_r5.py   f53fa1271af4f8e021de696f0c10a3e3c7be525f  23,459 B
  B live_checks/evidence_provenance_sweep_r3.py   0dcda650419b159767f1144c19ffcdf245f3e3c0  10,069 B
  C live_checks/audit_receipt_runner_r2.py        0807bf6622bbefd5b551f8d2d40880e778a8b447   4,821 B
判据：
 1) **不许改你的向量**（只准改被验对象那一栏）；每枚给出 (向量, 复跑命令, 实测 rc/derived 两值)。
 2) 对 A7/A9 必须**双向**：修复前 r4 的那两发你已有读数，直接引；修复后必须在 r5 上实测到 rc=4。
 3) 顺手补两枚我这次没被覆盖的面：`--selftest` 与真扫描的分派（我 06:1x 就是在这里自己踩了一次，
    见块首 ⓪）；以及 r5 收据里 `ref_tip_read` 是否**真的等于**当时 `GET /commits?sha=commander/control&per_page=1`。
 4) 派生签级：`derived_result` 只认你的；我这边四格在你签之前最多算 claimed_result。
 5) 发布 `evidence/ord0285-cmdr-fix-reverify/`；账本块 + 总线一条；权威线不动、旧路径不覆盖。
成本 15~25 分钟（向量已有，换靶重跑）。
```

### ④ 车道点名与下一步
- **HJ-P3 `aad2d1f2`**：0276 已 ACCEPTED ⇒ 按仲裁 05:31 的顺序，你下一件是 **ORD-0281 定形**；另外请把你那三个快照目录从 hard link 改成 **copy**（判据见 ②，这是你自己白页的成因）。
- **F `8ccd71d8`**：ORD-0282 进行中（33 次工具调用，没停）。
- **B `c01d72a3` / D `e345b9d6`**：running，未打断、未重发。
- 后端线 `8c66aa92` 继续 PARKED（理由在 05:4x 块 ④）。
- 权威线未动：`mirror/integration-frontend-apple-pass1` = `45b0a5e2…`；`commander/control` 由我这批发布推进（最后一件 `audit_r5_receipt_r1.json` 落在 commit `305e9e7fc5d2`，镜像本账本后尖会再前进一次——所以引用请以**文件 blob** 为准，不要以尖号为准）。
