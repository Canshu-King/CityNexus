# ORD-0500 r5 -- 现尖 b604f50d1645d028c2dd1d4406caee8198a3bc2d 读数单（与 ORD-0530 同族并块后重量；曝光尺两侧对照在 receipts 里）

生成时间 `2026-10-01T15:22:40.557718+08:00`；量具与件都在 `D:/moodle/_qoder_phone_ord0485_20260930`。

## 一、本代的产物身份（基座 + 交付候选 + 反件）

| 面 | 入口资产 | 打包字节数 | 打包 sha256（本机字节） | tsc check | tsc all | build |
|---|---|---|---|---|---|---|
| TIP_b604f50d | index-BOEFmwpL.js | 1578809 | f06c435d59e9b54d… | 0 | 0 | 0 |
| O0500_R5 | index-3R2y30xz.js | 1582603 | 68d1603a25d96ff2… | 0 | 0 | 0 |
| O0500_CLIENTBOOL_MUTANT | index-lLCqupGT.js | 1582635 | 842bb39754074339… | 0 | 0 | 0 |

本机字节 sha256，不是 git 物件，不可 cat-file；件 `evidence/gen9_builds_r1.json`。

## 一′、Q64 曝光尺：基座面与候选面同代各跑一遍（CMDR 02:01 要两侧格总数相同）

| 面 | 量的树 | 格总数 | 图内模块 | 每规则命中 | unresolved import | 解析诊断 |
|---|---|---|---|---|---|---|
| 基座 | D:/moodle/_qoder_phone_ord0485_20260930\wt23/frontend | 6 | 324 | {"RAW_BODY_TO_DOM": 1, "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT": 1, "UPSTREAM_TEXT_VIA_HELPER_TO_DOM": 4} | 55 | 0 |
| 候选（本单交付） | D:/moodle/_qoder_phone_ord0485_20260930\wt22/frontend | 6 | 327 | {"RAW_BODY_TO_DOM": 1, "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT": 1, "UPSTREAM_TEXT_VIA_HELPER_TO_DOM": 4} | 55 | 0 |

两侧格总数相同：True（6 对 6）；逐枚（文件、行、规则）集合相等：True；候选侧多出的格：无。

两枚件：`receipts/exposure_tip_b604f50d_r1.json`、`receipts/exposure_r5_candidate_r1.json`。上一代（候选把服务器正文交进共用 helper 那一形）的对照留在 `receipts/exposure_r2_candidate_r1.json`：那枚 10 格（量的树 `wt9/frontend`），比基座多出的 4 枚是 `src/features/access/AccessPanel.tsx:430` 与 `src/features/access/AccessPanel.tsx:442` 与 `src/features/studio/PlanVersionHistoryPanel.tsx:87` 与 `src/features/studio/PlanVersionHistoryPanel.tsx:100`，正是本单被裁的那处缺陷。

## 二、打卡门在本代的普查（390x844 与 1280x800 各一趟，每趟一份新库）

| 跑 | 视窗 | 站数 | 控件枚数 | 中心命中可按 | 盒 | 到屏时门里行数 | 屏上已打卡枚数 |
|---|---|---|---|---|---|---|---|
| TIP_b604f50d_phone | 390x844 | 6 | 6 | 5 | ["44x44"] | 0 | 0 |
| TIP_b604f50d_desktop | 1280x800 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_R5_phone | 390x844 | 6 | 6 | 5 | ["44x44"] | 0 | 0 |
| O0500_R5_desktop | 1280x800 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_CLIENTBOOL_MUTANT_phone | 390x844 | 6 | 6 | 5 | ["44x44", "54x44"] | 0 | 3 |
| PRE_SLICE2_dcb90ccc_phone | 390x844 | 6 | 0 | 0 | [] | 0 | 0 |

## 二′、历代同一把尺的分母：各代自己的件，逐枚带 blob

本代之外的那几代，面早就不在了，数只能从它们各自冻结的交件枝里读回来（件 `evidence/prior_denominators_r5.json`，逐枚 `git ls-tree`+`cat-file`）。每行的 blob 就是那个数被读出来的那枚物件。

| 代 | 该代枝头 | 面 | 控件 | 中心命中可按 | 重复点击后拒绝句 | 读自哪枚 blob |
|---|---|---|---|---|---|---|
| r1 | 3f3ab9c24221 | O0500_CLIENTBOOL_MUTANT_phone | 6 | 6 | 1 | 55a28e015613bf0a81497be71fc4bcb86eceeea1 |
| r1 | 3f3ab9c24221 | O0500_R1_desktop | 6 | 6 | 1 | 507155d295fca89f2d4375bf822f27b08cb9a351 |
| r1 | 3f3ab9c24221 | O0500_R1_phone | 6 | 6 | 1 | 92d8c46e80ae530cb35399cce5454435314ae0a4 |
| r1 | 3f3ab9c24221 | PRE_SLICE2_dcb90ccc_phone | 0 | 0 | NOT_MEASURED | 64b4582054261fff140c27ee75e8ccaeae569fc1 |
| r1 | 3f3ab9c24221 | TIP_1e95d106_phone | 6 | 6 | 6 | 6672ff07228eab183fd23b1bd2befa8a958eaea1 |
| r2 | 75a27ae98244 | O0500_CLIENTBOOL_MUTANT_phone | 6 | 6 | 1 | 6038bb2b4c144f8c6610e7351f7ee18f3133ad46 |
| r2 | 75a27ae98244 | O0500_R2_desktop | 6 | 6 | 1 | 005ddcf7056dca7f797588fa71a471ee42e3f764 |
| r2 | 75a27ae98244 | O0500_R2_phone | 6 | 6 | 1 | 127dc83e508875465007bdf6e1348a2cbadec10f |
| r2 | 75a27ae98244 | PRE_SLICE2_dcb90ccc_phone | 0 | 0 | NOT_MEASURED | 892d7683e487f25962f135d1d7e2c47235d7b9df |
| r2 | 75a27ae98244 | TIP_822db3d9_desktop | 6 | 6 | 6 | 32b4e528a3b836ea13976fb2dfa5e1be4e5cbbc0 |
| r2 | 75a27ae98244 | TIP_822db3d9_phone | 6 | 6 | 6 | 0fcb18ee1edce050a20c57ce6dff8f966d917c3c |
| r4 | 1509357870f7 | PRE_SLICE2_dcb90ccc_phone | 0 | 0 | NOT_MEASURED | fee71aabcbd6a1260787c6417312ded8ed495435 |
| r4 | 1509357870f7 | SCROLLTEST | 6 | 5 | 1 | 758e61c2529df1a7b755d4cb21e898e2eeb958e7 |
| r4 | 1509357870f7 | TIP_1e95d106_phone | 6 | 6 | 6 | 6672ff07228eab183fd23b1bd2befa8a958eaea1 |
| r4 | 1509357870f7 | O0500_R2_phone | 6 | 6 | 1 | 127dc83e508875465007bdf6e1348a2cbadec10f |
| r5 | 35719b30aabd | TIP_b604f50d_phone | 6 | 5 | 6 | 本代那一行读自 `checkin_TIP_b604f50d_phone_390x844_r2.json`（件在本枝的树里，blob 见 `git ls-tree`） |
| r5 | 35719b30aabd | TIP_b604f50d_desktop | 6 | 6 | 6 | 本代那一行读自 `checkin_TIP_b604f50d_desktop_1280x800_r2.json`（件在本枝的树里，blob 见 `git ls-tree`） |
| r5 | 35719b30aabd | O0500_R5_phone | 6 | 5 | 1 | 本代那一行读自 `checkin_O0500_R5_phone_390x844_r2.json`（件在本枝的树里，blob 见 `git ls-tree`） |
| r5 | 35719b30aabd | O0500_R5_desktop | 6 | 6 | 1 | 本代那一行读自 `checkin_O0500_R5_desktop_1280x800_r2.json`（件在本枝的树里，blob 见 `git ls-tree`） |
| r5 | 35719b30aabd | O0500_CLIENTBOOL_MUTANT_phone | 6 | 5 | 1 | 本代那一行读自 `checkin_O0500_CLIENTBOOL_MUTANT_phone_390x844_r2.json`（件在本枝的树里，blob 见 `git ls-tree`） |
| r5 | 35719b30aabd | PRE_SLICE2_dcb90ccc_phone | 0 | 0 | NOT_MEASURED | 本代那一行读自 `checkin_PRE_SLICE2_dcb90ccc_phone_390x844_r2.json`（件在本枝的树里，blob 见 `git ls-tree`） |

缺口具名：r4 那一代的枝上只有截图、没有它自己基座面的普查 JSON，所以它那一代的中心命中枚数在这里读不到（NOT_AVAILABLE_IN_THAT_REF）。本代的枝把 JSON 与截图都放进去了，不留同样的洞。

历代对照读出的是：r1、r2 那两代的手机面枚枚中心命中，本代基座与候选一起掉到同一枚数——掉的原因不在我这两笔里，表里「基座」那一行就是证据。

## 三、真发一发：行数前后与那句拒绝

| 跑 | 请求序列 | 行数 前→后 | 重复点击后屏上拒绝句枚数 | 句主 | 句子 |
|---|---|---|---|---|---|
| TIP_b604f50d_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 6 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 服务器说这一站已经有一枚印了，所以这次没有覆盖，行程保留它原有的那一枚。 |
| TIP_b604f50d_desktop | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 6 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 服务器说这一站已经有一枚印了，所以这次没有覆盖，行程保留它原有的那一枚。 |
| O0500_R5_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Old Town Gate"] | 这一站已经打过卡了（服务器记的是 10月1日 15:01），这次没有再盖一枚，行程里还是原来那一枚。 |
| O0500_R5_desktop | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Old Town Gate"] | 这一站已经打过卡了（服务器记的是 10月1日 15:02），这次没有再盖一枚，行程里还是原来那一枚。 |
| O0500_CLIENTBOOL_MUTANT_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Tech Art Center"] | 这一站已经打过卡了（服务器记的是 10月1日 15:03），这次没有再盖一枚，行程里还是原来那一枚。 |
| PRE_SLICE2_dcb90ccc_phone | [] | 0→0 | 不适用：这一族代 0 枚打卡控件，没有可点的第二下 | 不适用 | 不适用 |

## 四、门里的拒绝原文（四字段陈列，不造句子）

件 `evidence/gen9_doors_wt23-wt22-mutgen9.json`（三枚后端各自起进程、各自一份一次性库，共享库未被触碰）。

- 基座（现尖原样） `main.py` sha256 `0ca7767bfa032d3c…`，库行数 0→2，共享库未被动：True

  | 用例 | http_status | content_type | body_bytes | reason_code | 句子里有 uuid | details 为 null | details |
  |---|---|---|---|---|---|---|---|
  | no_target_named | 422 | application/json | 295 | CHECKIN_TARGET_REQUIRED | False | False | {"fields": ["activity_id", "place_id"]} |
  | both_targets_named | 422 | application/json | 365 | CHECKIN_TARGET_AMBIGUOUS | False | False | {"activity_id": "3a58c470-524c-5854-aa39-6c37a350eb80", "place_id": "place-old-town"} |
  | activity_not_on_this_server | 404 | application/json | 311 | CHECKIN_ACTIVITY_UNKNOWN | False | False | {"activity_id": "f60b3d39-468d-4946-982d-5e07e4aef59a"} |
  | place_not_on_this_server | 404 | application/json | 302 | CHECKIN_PLACE_UNKNOWN | False | False | {"place_id": "f60b3d39-468d-4946-982d-5e07e4aef59a"} |
  | write_door_unknown_journey | 404 | application/json | 235 | null（这一格测到了：拒绝体里没有这个名字） | True | True | null（这一格测到了：拒绝句该点名的格子是空的） |
  | read_door_unknown_journey | 404 | application/json | 235 | null（这一格测到了：拒绝体里没有这个名字） | True | True | null（这一格测到了：拒绝句该点名的格子是空的） |
  | first_tap_on_a_real_stop | 201 | application/json | 435 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |
  | same_stop_tapped_again | 409 | application/json | 434 | CHECKIN_DUPLICATE_STAMP | False | False | {"target_key": "activity:3a58c470-524c-5854-aa39-6c37a350eb80", "existing_checkin_id": "7bae2cde-e646-4f3e-ad71-77dfcfaf |
  | second_stop_tapped | 201 | application/json | 438 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |
  | read_footprints_back | 200 | application/json | 876 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |

- 候选（本单交付） `main.py` sha256 `3b67577e464496ad…`，库行数 0→2，共享库未被动：True

  | 用例 | http_status | content_type | body_bytes | reason_code | 句子里有 uuid | details 为 null | details |
  |---|---|---|---|---|---|---|---|
  | no_target_named | 422 | application/json | 295 | CHECKIN_TARGET_REQUIRED | False | False | {"fields": ["activity_id", "place_id"]} |
  | both_targets_named | 422 | application/json | 365 | CHECKIN_TARGET_AMBIGUOUS | False | False | {"activity_id": "3a58c470-524c-5854-aa39-6c37a350eb80", "place_id": "place-old-town"} |
  | activity_not_on_this_server | 404 | application/json | 311 | CHECKIN_ACTIVITY_UNKNOWN | False | False | {"activity_id": "0eaea398-9976-4d66-8340-db65bbbcb672"} |
  | place_not_on_this_server | 404 | application/json | 302 | CHECKIN_PLACE_UNKNOWN | False | False | {"place_id": "0eaea398-9976-4d66-8340-db65bbbcb672"} |
  | write_door_unknown_journey | 404 | application/json | 296 | CHECKIN_JOURNEY_UNKNOWN | False | False | {"field": "journey_id"} |
  | read_door_unknown_journey | 404 | application/json | 296 | CHECKIN_JOURNEY_UNKNOWN | False | False | {"field": "journey_id"} |
  | first_tap_on_a_real_stop | 201 | application/json | 435 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |
  | same_stop_tapped_again | 409 | application/json | 434 | CHECKIN_DUPLICATE_STAMP | False | False | {"target_key": "activity:3a58c470-524c-5854-aa39-6c37a350eb80", "existing_checkin_id": "846dcab7-a4c7-4ff7-89e2-a3943dd7 |
  | second_stop_tapped | 201 | application/json | 438 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |
  | read_footprints_back | 200 | application/json | 876 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |

- 反件一（409 判据摘掉） `main.py` sha256 `f9504db1b29efde1…`，库行数 0→2，共享库未被动：True

  | 用例 | http_status | content_type | body_bytes | reason_code | 句子里有 uuid | details 为 null | details |
  |---|---|---|---|---|---|---|---|
  | no_target_named | 422 | application/json | 295 | CHECKIN_TARGET_REQUIRED | False | False | {"fields": ["activity_id", "place_id"]} |
  | both_targets_named | 422 | application/json | 365 | CHECKIN_TARGET_AMBIGUOUS | False | False | {"activity_id": "3a58c470-524c-5854-aa39-6c37a350eb80", "place_id": "place-old-town"} |
  | activity_not_on_this_server | 404 | application/json | 311 | CHECKIN_ACTIVITY_UNKNOWN | False | False | {"activity_id": "197a9b4e-3e63-4037-916e-5a57d8531c34"} |
  | place_not_on_this_server | 404 | application/json | 302 | CHECKIN_PLACE_UNKNOWN | False | False | {"place_id": "197a9b4e-3e63-4037-916e-5a57d8531c34"} |
  | write_door_unknown_journey | 404 | application/json | 296 | CHECKIN_JOURNEY_UNKNOWN | False | False | {"field": "journey_id"} |
  | read_door_unknown_journey | 404 | application/json | 296 | CHECKIN_JOURNEY_UNKNOWN | False | False | {"field": "journey_id"} |
  | first_tap_on_a_real_stop | 201 | application/json | 435 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |
  | same_stop_tapped_again | 409 | application/json | 461 | CHECKIN_DUPLICATE_STAMP | False | False | {"target_key": "activity:3a58c470-524c-5854-aa39-6c37a350eb80", "existing_checkin_id": "40789f56-e660-45ba-a413-bbb892e0 |
  | second_stop_tapped | 201 | application/json | 438 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |
  | read_footprints_back | 200 | application/json | 876 | 不适用：成功体里没有 error 对象 | False | 不适用：成功体里没有 error 对象 | 不适用：成功体里没有 error 对象 |

  反件屏侧：交付候选面 `index-3R2y30xz.js`（outDir `D:/moodle/_qoder_phone_ord0485_20260930\faces\o0500_r5`）挂在被改过的门上（判据摘掉），臂退出 0，请求序列 ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"]，拒绝句枚数 1，句主 ["Central Food Hall"]，走完臂时库里 4 行，pageerror 0 —— 状态码与句子两样都看不出是哪一层拒的，这就是假绿。

## 五、反件一（服务端 409 判据摘掉）

| 侧 | 臂数合计 | 通过 | 失败 | 退出 | 失败的臂 |
|---|---|---|---|---|---|
| candidate_wt22 | 16（= 通过 16 + 失败 0，臂名去重） | 16（臂名去重） | 0（臂名去重） | 0 | [] |
| mutant_wt22_ce1 | 16（= 通过 13 + 失败 3，臂名去重） | 13（臂名去重） | 3（臂名去重） | 1 | ["test_a_footprint_outlives_the_rows_it_pointed_at", "test_the_duplicate_answer_comes_from_the_door_and_not_from_the_index", "test_the_duplicate_is_answered_before_the_target_row_is_asked_about"] |

两枚树只差 `backend/app/main.py` 一枚文件（比对 430 枚，只有 main.py 不同＝False，件 `evidence/gen9_ce1_tree_proof_r1.json`）；交付那枚的 `main.py` 前后 sha256 同一枚：3b67577e464496ad…（本机字节 sha256，不是 git 物件，不可 cat-file）

## 六、反件二（屏上的标不是门里给的）

- TIP_b604f50d_phone：门里 0 行时屏上 0 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 2 枚
- O0500_R5_phone：门里 0 行时屏上 0 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 2 枚
- O0500_CLIENTBOOL_MUTANT_phone：门里 0 行时屏上 3 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 3 枚

## 七、词汇闸（ORD-0485）不在这一页上。

那一单量在它自己那一代（基座 0989713aa687b97f4cd40bae009a6ce493425a4b），读数单是`review/ord0485-phone-walk/GEN6_READINGS.md`，随枝 `review/newlane-ord0485-phone-walkthrough-r5` 交付；把它的数写在本单页眉下就是跨代折算，Q24 不许。

## 八、打卡真理载体（本单三臂）在三面上的通过/失败

- base_tip（Playwright 报告 report_base_tip.json）：通过 2 枚，失败 1 枚
    · failed   ord0500-1-a-duplicate-refusal-speaks-about-the-stop-that-was-tapped — 拒绝只说被按的那一站
        Error: e2e/qoder-ord0500-checkin-truth.spec.ts :: ord0500-1 — the duplicate sentence was painted under 6 stops (Old Town Gate, Riverside Museum, Central Food Hall, Tech Art Center, Nexus River Cruise Pier, Skyline Dinner House); one tap makes a statement about one stop
    · passed   ord0500-2-the-marks-on-screen-are-the-rows-in-the-door — 屏上几枚，门里几行
    · passed   ord0500-3-one-control-per-stop-and-no-second-one-appears — 一站一枚，不长第二套
- candidate_o0500（Playwright 报告 report_candidate_o0500.json）：通过 3 枚，失败 0 枚
    · passed   ord0500-1-a-duplicate-refusal-speaks-about-the-stop-that-was-tapped — 拒绝只说被按的那一站
    · passed   ord0500-2-the-marks-on-screen-are-the-rows-in-the-door — 屏上几枚，门里几行
    · passed   ord0500-3-one-control-per-stop-and-no-second-one-appears — 一站一枚，不长第二套
- mutant_clientbool_ce2（Playwright 报告 report_mutant_clientbool_ce2.json）：通过 2 枚，失败 1 枚
    · passed   ord0500-1-a-duplicate-refusal-speaks-about-the-stop-that-was-tapped — 拒绝只说被按的那一站
    · failed   ord0500-2-the-marks-on-screen-are-the-rows-in-the-door — 屏上几枚，门里几行
        Error: e2e/qoder-ord0500-checkin-truth.spec.ts :: ord0500-2 — the door answers 1 footprint row(s) while the screen paints 3 已打卡 -- a mark may only exist because a row does
    · passed   ord0500-3-one-control-per-stop-and-no-second-one-appears — 一站一枚，不长第二套

  （同跑的库行数 base_tip：0→2，入口 index-BOEFmwpL.js，服务字节与磁盘字节相等 True）
  （同跑的库行数 candidate_o0500：0→2，入口 index-3R2y30xz.js，服务字节与磁盘字节相等 True）
  （同跑的库行数 mutant_clientbool_ce2：0→1，入口 index-lLCqupGT.js，服务字节与磁盘字节相等 True）

## 九、没走的与不修的（具名）

- 真机与隧道：NOT_MEASURED，以上全是本机 127.0.0.1 面上的模拟器读数。
- 整套 Playwright 验收：NOT_EXECUTED，只跑本单自己的载体与邻座已收的词汇闸。
- `GET /api/v1/journeys/{id}/checkins` 那一扇门在基座代仍不给未知行程具名（`require()` 印 uuid 且 details 为 null）：本单在候选代把两扇门一起具名了，但契约侧只写 POST 的 404 —— 因为 GET 侧补 404 会撞 ORD-0476 已收的那条契约臂（`sorted(listed["responses"]) == ["200", "409"]`），那是别人手上的判据，我不改。这条缺口具名留着，不在我写集里。

## 十、随本轮一起改的两处注释（改的是我自己写进件里的话）

`backend/tests/test_qoder_ord0500_journey_refusal.py` 的注释里有四处 `main.py` 行号。件 `comment_anchors_r5` 在基座树（= 现尖 `b604f50d1645`）逐枚读回：新四处全部命中它声称的那句；旧四处在现尖、上一尖 `514b397f96f3`、以及那四处最初被写下的那一尖 `be0ffee216c7` 上都不命中 —— 也就是这不是上游位移，是我从一开始就没测。

  | 注释说的那件事 | 旧行号 | 旧行在现尖读作 | 旧行在上一尖读作 | 旧行在 origin 尖读作 | 新行号 | 新行在现尖读作 | 命中 |
  |---|---|---|---|---|---|---|---|
  | shared require() helper | 797 | `if argument.strip().isdigit():` | `if argument.strip().isdigit():` | `journey: Journey,` | 810 | `def require(session: Session, model: type, identifier: str, label: str):` | True |
  | door's own duplicate lookup | 3812 | `)` | `session: Session, journey: Journey, kind: str, target_key: str` | `if member.expires_at:` | 3912 | `existing = session.scalars(` | True |
  | index catch branch | 3848 | `"activity_id": identifier,` | `)` | `{"field": "created_by"},` | 3948 | `except IntegrityError as exc:` | True |
  | caught_by marker | 3865 | `` | `responses={` | `"An expiry without an offset would be a guess about whose clock it is.",` | 3965 | `"caught_by": "unique_index",` | True |

`frontend/src/features/checkin/footprint.css` 里我那段注释原话是「all six stops answer a centre hit」，而本代普查量到的是 5/6 —— 话错了，按读数改成实测句。件 `css_delta_proof_r5`：r4 那枚 blob `a56fa3a4de2f1a915019c26d1b7861269355eb00`、本轮 `ad6fafc5a8dd7c460702378342ff3e0a0bad8f1d`，差 8 增 8 删，删除行全是注释正文（`removed_are_prose_only.clean` = True），ORD-0530 的 `cn-footprints__day` 那 3 行两侧逐字相等：True，改后那句写的是 5 of 6，旧那句还在不在：False。

可达性这条本轮量到的形状（同一把尺：`scrollIntoViewIfNeeded` 后取控件自身中心的 `elementFromPoint`）：

| 面 | 站 | 控件 | 中心命中可按 | 不可按的那一枚（索引：站名） |
|---|---|---|---|---|
| TIP_b604f50d_phone | 6 | 6 | 5 | 1:Riverside Museum |
| O0500_R5_phone | 6 | 6 | 5 | 1:Riverside Museum |
| TIP_b604f50d_desktop | 6 | 6 | 6 | 无（枚枚中心命中） |
| O0500_R5_desktop | 6 | 6 | 6 | 无（枚枚中心命中） |

`scroll-margin-bottom: 92px` 那条单独造了一面重跑（面 `http://127.0.0.1:4883`，件 `receipts/checkin_SCROLLTEST_phone_390x844_r2.json`）：中心命中可按 5/6 枚，与不加这条规则的候选面 5/6 枚一样，于是撤了这条规则、不留装饰；真正要动的是滚动容器与手机底栏那两家，不在本单写集里，具名报出。
