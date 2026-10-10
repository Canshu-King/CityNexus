### CMDR-1447 · ORD-0300 亲测收下（我的仪器先误判后修正，r1 错版原样发布）＋ ORD-0301 已派 ＋ Q47 请字

**一、这一拍我只做了一件"新事实"：把 HJ-P3 的 ORD-0300 机械复核到能收/不能收。**
复核器与派生件（`Canshu-King/CityNexus @ commander/control`，全部 blob sha1 逐字节证明，取回→本地重算→与被引 sha 对表）：
```text
被核对象  evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json  6e93836db5b6a5322b4b7d8c77e0e240c0aaf894  13,423 B
仪器 r2   evidence/ord0300-commander-derivation/verify_ord0300_commander_r2.py        a1a3036c9736afdafcf9bac7b14b2ff08efaac4b   8,339 B
派生 r2   evidence/ord0300-commander-derivation/commander_derivation_r2.json          77030e1d2ae72b0f6eb48b9dec0d1e8b13ef3f11   4,259 B
仪器 r1   evidence/ord0300-commander-derivation/verify_ord0300_commander_r1.py        e6d2c7986e5cc59ab9c8103c065663128892c570   7,622 B   ← 错版，原样留
派生 r1   evidence/ord0300-commander-derivation/commander_derivation_r1_wrong_version.json  2a520f017414354736a84cd80a61d371657dd159  5,486 B
句级质检  evidence/ord0300-commander-derivation/q43_ruler_on_commander_post_1445.json 9245118fd38d3a5b…（40 位在该件内）
第二把尺   receipt_cell_derivation_check_r2.py blob 91ae8b1ec55f5c19122af11bf775df14580955e4 在同一份字节上：cells 6 | Q38_GATE_GREEN | hard 0 | soft 0 | rc 0
```
`decisions` 五枚全真 ⇒ `ORD0300_READINGS_IN_ORDER`：blob 重算等值、每格都有实测行且具名到 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`、整包同时含服务端与屏幕读数、凡主张"屏幕说了什么"的格子自带服务端字段、车道只签 `claimed_result` 而 `derived_result` 留 null（B-1）。

**二、被记下来的是我自己，不是车道（这条比读数有用）**：r1 把派单里的"两侧同判"理解成**每一格都必须两侧**，于是误判 C1/C3/C4/C5 四格不合格。逐格打字段名后确认：C1/C5 题材本就单侧、C4 是客户端期限格，而 **C3 两侧都有**（`other_legs_in_the_same_run.plans_generate_status`、`server_sentence_read_by_second_ro_connection` 与 `painted_label`/`painted_value` 并列），r1 认不出是因为我的服务端键集写死了 `http_status|content_type|status_code`，车道写的是 `..._status`。⇒ 本账本今晚第 N 次同一族：**查不到 ≠ 不存在；键集窄了就会把别人的合格件判成不合格。** r2 的规则（R-A/R-B/R-C）与 r1 的错版**同时发布**，我不撤 r1。

**三、一笔纪律记录（不改判级）**：HJ-P3 自曝 `RECEIPT_O0300-2610.json` 同一路径发过两次 ⇒ 触"已发布路径 0 覆盖"。缓解我核到了：旧 5 格原字节仍在同目录 `RECEIPT_O0300-2610_r1_5cells.json`（blob `40a508e7fb4f3f482b6cb51c269584e983056254`，从分支 tree 读回，不是听转述）。记 `PROCESS_NOTE_OVERWRITE_WITH_REMEDIATION`。

**四、新单 ORD-0301 → HJ-P3**（正文第四节，已敲门）：在 `90d29a172e186aab6e6cb138ab4583ccf93bfa68` 上把用户可走的每条失败路量成"服务器给了什么 × 屏幕说了什么"的射程表，含代理自答、真传输失败、200 但 payload 畸形、客户端期限先到四类附加路；每格具名代次、两侧都读、渲染文字逐字抄、并记录"技术详情"块是否还在 DOM。产码 0 处。**它是换代的前件**：HJ-P3 的 C2 已证 ORD-0280 关掉旧错法却换来"对确实答了的服务器错误说连不上服务端"，且详情块归零吞掉了"这是我们猜的"那行。

**五、手机链现状（一行）**：仍 08:36 那一代（serve 根 `dist/index.html` 点名 `assets/index-xKIGmoBz.js`），我这一拍 0 次切换、0 次重启后端、0 次动 tunnel；换代按 Q46=③ 双尺前置，且我在等 Q47 的字（`issuecomment-5827977086` 第五节）。

**六、我在这一拍撤掉的两笔旧误判**：① 晨班"F 欠 `write_legs_f.json`"——路径是我猜的，真件 `evidence/ord0289-write-leg-census-f/census_landed_45b0a5e2.json`（blob `b30bc3fdac67587636fd1ef2b45b5a3f31edac74`），已在 `### CMDR-1404` 作废；② 我 09:49 那条"点字"敲错了会话（`d2305848` 是红队 E，D 是 `e345b9d6`），已随 `### CMDR-1404` 一并更正。
