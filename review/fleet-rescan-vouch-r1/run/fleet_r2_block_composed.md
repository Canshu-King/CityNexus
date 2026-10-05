### ORD-0500 手机车道（0afdb49b）全车队落地铁重扫第二代：同一枚尖上全部 review 枝逐枚按字节复判，三十五条被这一代改了判语、无人认领的计数移动零条；上一代的聚合判语是我夸了口，本代只收口不追账

一、这一代修的是我自己上一代夸过的两处口
- 快照形的手被折进了 CHANGED：这些枝的头是从孤儿根或整树快照切出来的，单枝自带近万枚路径，对着线上树逐枚比当然几乎全"不同"。上一代把它们报成"这一手的字被线上盖掉了"，那是一句没有依据的指控。本代给这一类不出判语，门槛是自带路径 ≥ 线上树的一半。件 `review/fleet-rescan-r2/tools/fleet_landed_rescan_r2.py` blob `951610708048d547bf488ccc85dab07d43a462b5`。
- 纯删除的手落进了 catch-all：一支只删不改时 SAME 与 CHANGED 都为零，上一代把它塞进 `OTHER`。本代另开 `ALL_DELETIONS_HELD` / `ALL_DELETIONS_UNDONE` / `DELETIONS_SPLIT` 三格。件 `review/fleet-rescan-r2/tools/fleet_landed_rescan_r2.py` blob `951610708048d547bf488ccc85dab07d43a462b5`。
- 还有一个我自己仪器的 bug：`git diff-tree --stdin` 不把没以换行收尾的最后一行冲出去，于是字典序最大的那枚头从来没进过批次、它的手被读成"什么都没发"。这条是对照腿 C8 报出来的（`ABORT_DIFF_TREE_EMITTED_NOTHING`），本代补了行尾换行、补了名册覆盖检查，并把"批次等于逐枚"钉成常设腿 C11。件 `review/fleet-rescan-r2/evidence/fleet_rescan_arms_r2.json` blob `9ea3b502fd80f496947b6fe440f93c3613e8089d`。

二、这一代量到的分母（现读远端，不是本地枝清单）
- 尖 `aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f`，线上树 10589 枚路径（件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`）：`refs/heads/mirror/integration-frontend-apple-pass1` 名下 review 枝 1081 条，去重后头 1035 枚，其中 42 条枝与他人共用同一枚头。
- 本地取不到的头 0 枚（全部可解，故本手一次 fetch 也没发）；批次里静默的头 2 枚，其中 2 枚经复核是真·空提交（树与每一位父相同），单列为 `EMPTY_COMMIT` 而没有当漏洞（件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`）。
- 判语分布之一（件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`）：HELD 272 条、MIXED 385 条、ALL_DIFFERENT_ON_LINE 129 条、ALL_NOT_ON_LINE 224 条。
- 判语分布之二（同一件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`）：SNAPSHOT_SHAPED 27 条、NONE_HELD_SPLIT 41 条、ALL_DELETIONS_HELD 1 条、EMPTY_COMMIT 2 条；八格合计等于 1081 条，工具在落盘前断言过这个合计。
- 可判的手 1052 条，逐枚路径合计 41263 枚：SAME 34309、NOT_ON_LINE 1819、DIFFERENT_ON_LINE 4992、删除被撤 11（件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`）。快照形那 27 条带来的 277343 枚路径不进这个分母。

三、"改了判语"必须点名，不能只说"更准了"
- 两趟对拍只在同一枚尖上发布：`r1_tip` 与 `r2_tip` 都等于 `aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f`，写手断言过。1081 条逐条比，35 条换了类别，配对逐条如下。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`。
- `MIXED` → `SNAPSHOT_SHAPED`：21 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `OTHER` → `SNAPSHOT_SHAPED`：6 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `NO_PATHS_REPORTED` → `EMPTY_COMMIT`：2 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `NO_PATHS_REPORTED` → `HELD`：2 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `MIXED` → `ALL_NOT_ON_LINE`：2 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `HELD` → `ALL_DELETIONS_HELD`：1 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `OTHER` → `ALL_NOT_ON_LINE`：1 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- 每路径计数移动的行 35 条，全部有名字，没有一条被含糊过去。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`。
- `deletion_class_split`：33 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- `recovered_from_batch_drop`：2 条。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`
- 无人认领的计数移动：0 条。这一格若非零，上线的那把对拍尺会直接以 `ABORT_UNATTRIBUTED_COUNT_MOVES` 中止，不会把没解释的数送进账本。件 `review/fleet-rescan-r2/tools/fleet_rescan_label_delta_r2.py` blob `c2d6a0a947bd8f265c7266ae85f5adde9d24f838`。
- 另 1 条不在改判语之列：`6a773af1-ord0556-route-sweep-r1` 的头在两趟之间自己前进了（`5a90d65b230d0c6d66ab5e2c05d6cebc956cffcc` → `5971231736e175d81dd4f6e5a33f4ae93a21222f`），那是别的车道推了自己的枝、我在两个坐标读到两个事实，不是这一代给同一件事换了说法。我按读数报，没有把它折进任何判语。件 `review/fleet-rescan-r2/evidence/label_delta_r2.json` blob `748cbf5804d49ca128ec9d2e322b8e136ada6a85`。

四、对照腿全绿（新闸上架要有"该红的那一次"）
- `C1_control_held_not_accused` bit=True
- `C2_different_bytes_cannot_read_same` bit=True
- `C3_missing_path_is_absent_not_changed` bit=True
- `C4_snapshot_hand_gets_no_verdict` bit=True
- `C5_pure_deletion_hand_named` bit=True
- `C6_undone_deletion_not_a_pass` bit=True
- `C7_unreadable_blob_is_not_changed` bit=True
- `C8_empty_roster_aborts` bit=True
- `C9_denominator_is_the_remote` bit=True
- `C10_no_ref_moved` bit=True
- `C11_batch_equals_per_head` bit=True
- `every_arm_bit` = True（件 `review/fleet-rescan-r2/evidence/fleet_rescan_arms_r2.json` blob `9ea3b502fd80f496947b6fe440f93c3613e8089d`）。C1 是控制腿：一支确实全 SAME 的枝不许被读成指控；C4、C5、C6、C7 各自喂一枚形状给聚合函数，证明标签是算出来的、不是写死的；C10 证明整趟扫描期间没有任何枝被我的读写动过，本手是纯读。
- 名册（每枝一行的逐枚计数）：`review/fleet-rescan-r2/evidence/fleet_rescan_r2_roster_r2.tsv` 数据行 1081 行，另 2 行抬头（抬头里的 `refs=` 与 `tip=` 就是上面断言过的同一组分母），件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_roster_r2.tsv` blob `2d4332ac45ffabede9699e0b8539e299bca44b28`。

五、这格改了口径，但没有改任何人的交付状态
- 先把影响面划清，别把话说过头：这一代改的是车队第一代读数（`tools/fleet_landed_rescan_r1.py` 那份）的**聚合标签**，而那批标签从未进过账本——只留在车道档里，我没对外报过车队级判语，所以本手没有"撤回已发布读数"这回事。真正入过账的 `LOST_LANDED_CONTENT` 用词更正是上一块 `0108` 那一次做的，与本手无关，也不受本手影响。件 `review/fleet-rescan-r2/tools/fleet_landed_rescan_r1.py` blob `26c4b1493e8e415556b7ee086c7bcfd4ca1c5d7e`。
- 受影响的是聚合判语；每路径那三个数在本代确实动过 35 行，动因在上面逐条点名，无一条含糊。要引用判语请引本代名册，件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_roster_r2.tsv` blob `2d4332ac45ffabede9699e0b8539e299bca44b28`。
- 全车队没有任何一支被这一代判成 LOST：判"丢了"需要一张仪器落地回执、指名这一手曾经匹配过哪枚尖，而本扫描不读任何回执，所以只用字节词 `NOT_ON_LINE` 与 `DIFFERENT_ON_LINE`。
- 没量的部分照旧点名：真机 `adb devices` 未跑、Playwright 套件未跑、拒绝语逐句屏读不在这一代范围内。

六、我停手的那件（等你一句）
- 甲/乙/丙未回：`refs/heads/review/0afdb49b-ord0500-anchor-form-r5` 与 `refs/heads/review/0afdb49b-ord0500-staging-door-r7` 的父仍停在尖之前那一代，我按自己推荐的乙/丙执行，这一小时里没有再推零变化的重切枝。你点头任一，我按现尖重父。
- 丙那问（这把重扫尺要不要进落地闸）仍挂起。若进闸，`SNAPSHOT_SHAPED` 的"不出判语"要一起进去，否则闸会拿快照形当红。

七、边界与复算
- 发布：`refs/heads/review/0afdb49b-fleet-rescan-r2` 头 `bc4b6fec021b921ece3194a4e0f65a800469ccfa`，单父就是尖 `aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f`；对尖改动 14 枚路径、全部落在 `review/fleet-rescan-r2/` 前缀下，该前缀之外零枚（现取 `git diff --name-only aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f..bc4b6fec021b921ece3194a4e0f65a800469ccfa`）。件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`。
- 为省共享盘，上线的是名册（125016 字节，件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_roster_r2.tsv` blob `2d4332ac45ffabede9699e0b8539e299bca44b28`）+ 摘要（3400 字节，件 `review/fleet-rescan-r2/evidence/fleet_rescan_r2_summary_r2.json` blob `9eb91e82d0001a1e41b7bd03b4dcb33667b9523e`），没把整棵 1018904 字节的逐枚 JSON 推上线；那份留在车道里，路径写在摘要顶层 `per_ref_rows_live_at` 一格。
- 线上已落字节被我覆盖零枚；名下旧枝改写零枚；删枝零枚；force-push 零次；账本直写零处（本块走收件口）；端口起停零个；重启链零次；wt22 工作树写入零处（本手只读远端 tip、ref 与 blob）。
- 复算（现取现读；尖若已走请整代重跑）：`D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_phone_ord0485_20260930/tools/fleet_landed_rescan_r2.py` 出读数，再依次 `D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_phone_ord0485_20260930/tools/fleet_landed_rescan_arms_r2.py`、`D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_phone_ord0485_20260930/tools/fleet_rescan_label_delta_r2.py`、`D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_phone_ord0485_20260930/tools/fleet_rescan_roster_r2.py`。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
