**ORD-0536 已交（车道 `1d64acf5-3f5f-48e8-a7b4-9d7a37996edb`）— 豁免全部改由一枚冻在尺里的形状表决定，而那张表在形制上写不出「某一格」**

交付只加一枚新名：`live_checks/ui_exposure_taint_ast_r8.cjs`，枝 `review/S4-ord0536-structured-exemption-r8`。已发布的 r7b / r7b1 / r7b3 / r7b4 字节一字未动，而且本轮把 r7b 与 r7b4 当对照各跑了一遍。

**先纠正一处事实（印出我读了什么）**：叫醒那轮给的现尖逐字是 `7862c6de5565c02ec0ec2dccaa9da18960603e06`，它 `git cat-file -t` 报 could not get object info；我 `git ls-remote` 现读的是 `7862c6de5565c02c20ec2dccaa9da18960603e06`（第 21 位起 `02c20ec2`）。本块所有读数都在后者上。题面 02:13 那串 `f1decd85549996bad56d0e81ce77fa4e1ceeaeab` 是 02:13 的针，我也没去复现它。

**这一单真正的缺口是我找出来的，不是题面写好的**：尺族里已经有两条结构化豁免（ORD-0408 甲的契约闭集、Q67/Q75 的折叠具名锚），它们**判得对**；坏在**豁免一生效那一格就从 `hits` 搬进别的列表，分母跟着制度走**。同一棵现尖导出树上门钉 r7b 报 6 枚、我上一轮发的 r7b4 报 5 枚，差的那枚正是 `RecoveryRequiredPanel.tsx` 上被折叠锚**静默**移走的，没人打印过依据。门 Q64 那一臂比的正是绝对格数（`preflight_and_land_r7.py:384`），所以「尺换了一代」与「候选真的长了曝光面」在门上读起来是同一件事——这才是「靠人手放」的真实形状：**数字随制度漂，只有人能把它圆回来**。

## 表（两条目，三根轴 + 一条必须量到的证据）
- `EX-1-CONTRACT-CLOSED-ENUM`：rules * ／ sink 形状家族 * ／ origin_kind `raw-body`/`prose`/`named-prose-member`/`exception` ／ 证据 `contract_closed_enum`
- `EX-2-ATTRIBUTED-FOLD`：rules UPSTREAM_TEXT_VIA_HELPER_TO_DOM/RAW_BODY_TO_DOM/UPSTREAM_READ_DIRECT/UPSTREAM_EXCEPTION_TO_DOM ／ sink 形状家族 text-in/text ／ origin_kind `raw-body`/`prose`/`exception` ／ 证据 `attributed_fold`

表的字节摘要每次跑都印在自己的输出里（`exemption_table.digest_sha1`），事后能问「是哪一枚字节放行的」。

**表写不出「某一格」是形制检查**：只认 `id / rules / sink_shape_families / origin_kinds / evidence` 五枚键，值长得像路径、扩展名、行号或 16 位格 id 就拒，家族轴里带 `:`（一整枚 sink 形状而不是一族）也拒。**六枚真跑的拒件各退 3、回 `EXEMPTION_TABLE_SCHEMA_REJECTED`**：`names_a_file`→UNKNOWN_KEY, `names_a_line`→UNKNOWN_KEY, `names_a_cell_id`→UNKNOWN_KEY, `names_one_whole_sink_shape`→FAMILY_NAMES_ONE_SINK, `invents_an_evidence_name`→EVIDENCE_NOT_IMPLEMENTED, `names_a_file_through_the_family_axis`→AXIS_NAMES_A_CELL。

**命令行也没有缝**：旗标是闭集（`--tree --file --ref --path --out --contract --selftest`）。四枚真跑各退 2：`--waive-cell`、`--exempt-cells`、`--baseline-cells` 具名 `HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL`，`--authoritative-count` 具名 `UNRECOGNISED_FLAG`；四次 `--out` 那枚文件都没被写出。

## 现尖具名报回（豁免前 8 枚 = 红 5 + 有据豁免 3；门钉那把在同一棵树报 6 hits）
- UPSTREAM_TEXT_VIA_HELPER_TO_DOM ｜ `app/V8Experience.tsx:2870` ｜ EX-2-ATTRIBUTED-FOLD ｜ 依据：fold `details`@2864 的具名锚 `http_status`@2877
- UPSTREAM_TEXT_VIA_HELPER_TO_DOM ｜ `components/CnxMeasuredFacts.tsx:81` ｜ EX-2-ATTRIBUTED-FOLD ｜ 依据：fold `details`@64 的具名锚 `http_status`@71
- UPSTREAM_TEXT_VIA_HELPER_TO_DOM ｜ `features/recovery/RecoveryRequiredPanel.tsx:299` ｜ EX-2-ATTRIBUTED-FOLD ｜ 依据：fold `details`@288 的具名锚 `dynamic:notice.field`@297

第三枚的锚是 `dynamic:notice.field`——r7b1 那条「展开写法必须伴来路标签」的形状，本轮它从**看不见**变成**看得见并且带依据**。照旧红的 5 枚一枚没藏，每枚带尺自己给的理由（属性位那枚 `NO_CODE_FIELD_NAMED_ON_THIS_CELL`，`ActivityDetail.tsx` 那枚 `NO_FOLD_CONTAINER`）。

**分母不再随豁免移动，这是量出来的**：同一棵针树把折叠条目整枚删掉 ⇒ 红 8／豁免 0；把该谓词改成「不读树就答 ok」（那就是「有人写一句就算豁免」在仪器里的样子）⇒ 红 1／豁免 7。两种改法 `cells_total` 都还是 8，而 `--selftest` 双双 SELFTEST_FAIL（退 7），点名条目分别是 `fold_pair`, `no_drift_against_the_published_partition` 与 `class_name_opens_nothing`, `contract_is_not_for_sale_to_the_fold`, `contract_pair`, `fold_pair`, `new_call_site_into_a_shared_helper_is_not_exemptible`, `no_drift_against_the_published_partition`；未改动的交付字节 SELFTEST_PASS。

## 正反两向自检（两侧读数都贴，`--selftest` 退 0，新增 9 枚臂全 met）
- `fold_pair`：折叠 + 具名锚 ⇒ cells 1、红 0（那一枚 EXEMPTED 且**仍在 cells 里**）；同一格把锚换成 JSX 注释 ⇒ cells 1、红 1，near_miss 具名 EX-2 且 `fold_without_anchor` 为真。两侧 cells 相等 ⇒ 改的是判语，不是分母。
- `contract_pair`：契约声明闭集且值在集内 ⇒ cells 1、红 0（依据里回显 enum 行号）；值在集外 ⇒ 红 1（`value_not_in_the_contract_set`）；契约根本没声明该字段 ⇒ 红 1（`CONTRACT_MISSING_ENUM`）。三侧 cells 都是 1/1/1。
- 另 7 枚管的是表与输入面：`table_cannot_name_a_cell`、`no_waiver_input_channel`、`class_name_opens_nothing`、`fold_family_excludes_the_attribute_slot`（EX-2 的家族轴里没有 `attribute`，Q71 那扇门仍关着）、`contract_is_not_for_sale_to_the_fold`（契约先拒的不会被折叠条目救回）、**`new_call_site_into_a_shared_helper_is_not_exemptible`**——你点名要我先考虑的那条形：共用 helper 多一条来路上游正文，两枚面板各长出的格**全红**，包含车道根本没打开的那枚文件，因为作者身份不是这三根轴之一、表里没有这一列。
- 旧三组按原期望仍全中：fixtures 20 条、mode 臂 2 对 2、cross 臂 7 对 7；不漂移那枚拿**已发布的** 19 条 R7 臂原期望逐条比分区，19 对 19 相等（期望不是我这一轮写的；逐条读数在件 `st_r8_full.json`，blob `b2d30767721371e2da53ed042e6efad7af097019`）。

## 与你那两侧对照（候选 10 / 现尖 6）对齐口径
两棵树按题面逐字 rev 各自重新 `git archive` 导出，三把尺在同一棵上各跑一遍：

| 树 | r7b | r7b4 | r8 豁免前 | r8 红 | r8 豁免 |
| --- | --- | --- | --- | --- | --- |
| 候选 `62f030f3` | 10 | 9 | 12 | 9 | 3 |
| 现尖 `0989713a` | 6 | 5 | 8 | 5 | 3 |
| 本轮现尖 `7862c6de` | 6 | 5 | 8 | 5 | 3 |

⇒ **r7b 那一列逐字复现你的 10 / 6**，口径接上了。三把尺的**豁免前分母逐棵相等**（三棵全 True），会漂的只有「红」那一列，而 r8 把每一枚漂移都打印出来了。

**给你那一臂的那句**：候选相对现尖按格 id 新增 4 枚、消失 0 枚，逐枚是 `UPSTREAM_TEXT_VIA_HELPER_TO_DOM|features/access/AccessPanel.tsx:474`; `UPSTREAM_TEXT_VIA_HELPER_TO_DOM|features/access/AccessPanel.tsx:462`; `UPSTREAM_TEXT_VIA_HELPER_TO_DOM|features/studio/PlanVersionHistoryPanel.tsx:87`; `UPSTREAM_TEXT_VIA_HELPER_TO_DOM|features/studio/PlanVersionHistoryPanel.tsx:100`；门那套按 (file, rule) 计数的判语指的是同一批格（`the_two_views_agree` = true），差别只在身份视图额外说得出文件与行。**我没动门**（`preflight_and_land_r7.py:384` 仍原字节），只把门可直接消费的两枚视图交出来；换判语要你点单。

## 顺手抓到一枚调用方的形红（具名报、不擅自修别人的量具）
`live_checks/patrol/_exposure_delta_r1.py:66` 取的是 `j.get("cells") or []`，而**已发布的任何一代在 `--file`/`--ref` 模式都不吐 `cells` 这枚键**。同一枚针、同一份路径各跑一遍：`JourneyTrashPanel.tsx` r7b 回 2 hits、`cells` 键长 0、按那行代码抽出的格 id 0 ⇒ 那支扫描对每枚文件拿到的都是空集，于是它那句「不会新增曝光格（按逐枚文件集合差）」在该形状下**恒为真**，与产品字节无关。r8 同一份路径回 hits 2、`cells` 键长 2，这一判语从今天起才真有力。修法是一行，但那枚脚本不是我的字节，我不重写别人的量具。

## 仍未改善（不折进已收口）
- 现尖上照旧 5 枚红格，本单不吞它们，也**没有**为它们任何一枚新增表条目——那要的是产品字节改动或你的具名裁语，不是仪器放行。
- 折叠豁免证到的是「这一格折在具名锚后面」，证不了「用户打开后读得明白」；后者仍是屏尺的活，我把这句写死在 `interpretation_limit` 里。
- EX-1 在全树模式本轮豁免 0 枚（现尖没有元素具名 `*_code` 契约字段），所以它的两向是在自检与真文件两处都跑的，我没拿一侧宣称过关。
- 门那侧换成按身份比较需要一单改门；`cells_total` 从今天起不随豁免动，但门仍钉在 r7b 上，那道比较还是绝对格数。

## 坐标
- 枝 `review/S4-ord0536-structured-exemption-r8` 头 `66cd53af64ac99c0784108ebd7b5276cc8ac2917`；对现尖只读预测 `git merge-tree --write-tree` 退出 0、预测树 `6147d21fb54ce37e1370020335eac3b4445ffc97`。
- 交付字节 blob `83819289685f4bb58c5dea728114473f66fd29ef`（`git ls-tree` 从枝尖读回，不是本机算的）。
- 证据 17 枚在 `commander/control` 的 `evidence/ord0536-structured-exemption-0339/`，逐件本机 blob 与从分支尖 `ls-tree` 读回的服务端 blob 相同（回执 blob `5732968640cfde2c480ee51660f14db8020c5da5`）。汇总读数：分区对账 `2ed661a05438f4531fc51bb8a1ec91662f701236`、反件 `17587b3a67e653639b289c81cab91a7e807ba228`、门视图 `c5ff9c584ca4fc133102091672127b932ab203c1`。
- 账本块：`_qoder_ledger_inbox/s4_0351.md`，交前 `claim_coordinate_check_r7.py --text <那块> --expect-clean` 到 `Q43_GATE_GREEN`、findings 0。
- 边界：`:8000` `:4781` `:4782` `:8693` 一枚没占；本轮 0 次起服务、0 次开端口；`_preview.db` 一字未读未写；`demo/reset` 0 次；新开整树导出 0 枚（三棵都只含 `frontend/src contracts`，逐棵 os.walk 实测，逐棵字节与合计在件 `export_sizes_r1.json`，blob `7df659cb301193cc55bdf185849cde44691df405`）；权威线 0 次移动。

一块求你读的细节：第一版发布脚本把回执里那枚键读成 `sha`，而 `cmdr_git_mirror_r1.py:185` 打印的是 `readback_blob`——于是 17 枚**早就落上去**的文件在我回执里全成了 `byte_equal: false`。第二版不重推已在的字节，改为按分支尖取真实 blob 逐件比，回执即它产的。同一轮另有一枚早批落点 `evidence/ord0536-structured-exemption-0337/`（差的就是重推那两枚 + 后加的读数件），我不删 `commander/control` 上的任何东西，等你处置。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
