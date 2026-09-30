# ORD-0485 -r4 / ORD-0500 r2 -- 现尖 822db3d9 读数单（本代全部重量，无跨代折算）

生成时间 `2026-10-01T03:30:46.169654+08:00`；量具与件都在 `D:/moodle/_qoder_phone_ord0485_20260930`。

## 一、本代的产物身份（两枚候选 + 基座 + 反件）

| 面 | 入口资产 | 打包字节数 | 打包 sha256（本机字节） | tsc check | tsc all | build |
|---|---|---|---|---|---|---|
| TIP_7862c6de | index-DaHdgt6W.js | 1547460 | 5311bae9cf7a4075… | 0 | 0 | 0 |
| O0485_R4 | NOT_MEASURED | NOT_MEASURED | None… | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED |
| O0500_R3 | index-B-4JbgaK.js | 1551214 | ff502d6eb49ec0ad… | 0 | 0 | 0 |
| O0500_CLIENTBOOL_MUTANT | index-BnrJYfML.js | 1551242 | 13684cc891c74261… | 0 | 0 | 0 |

本机字节 sha256，不是 git 物件，不可 cat-file；件 `evidence/gen7_builds_r1.json`。

## 二、打卡门在本代的普查（390x844 与 1280x800 各一趟，每趟一份新库）

| 跑 | 视窗 | 站数 | 控件枚数 | 中心命中可按 | 盒 | 到屏时门里行数 | 屏上已打卡枚数 |
|---|---|---|---|---|---|---|---|
| TIP_7862c6de_phone | 390x844 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| TIP_7862c6de_desktop | 1280x800 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_R3_phone | 390x844 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_R3_desktop | 1280x800 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_CLIENTBOOL_MUTANT_phone | 390x844 | 6 | 6 | 6 | ["44x44", "54x44"] | 0 | 3 |
| PRE_SLICE2_dcb90ccc_phone | 390x844 | 6 | 0 | 0 | [] | 0 | 0 |

## 三、真发一发：行数前后与那句拒绝

| 跑 | 请求序列 | 行数 前→后 | 重复点击后屏上拒绝句枚数 | 句主 | 句子 |
|---|---|---|---|---|---|
| TIP_7862c6de_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 6 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 服务器说这一站已经有一枚印了，所以这次没有覆盖，行程保留它原有的那一枚。 |
| TIP_7862c6de_desktop | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 6 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 服务器说这一站已经有一枚印了，所以这次没有覆盖，行程保留它原有的那一枚。 |
| O0500_R3_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Old Town Gate"] | 这一站已经打过卡了（服务器记的是 10月1日 03:21），这次没有再盖一枚，行程里还是原来那一枚。 |
| O0500_R3_desktop | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Old Town Gate"] | 这一站已经打过卡了（服务器记的是 10月1日 03:22），这次没有再盖一枚，行程里还是原来那一枚。 |
| O0500_CLIENTBOOL_MUTANT_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Tech Art Center"] | 这一站已经打过卡了（服务器记的是 10月1日 03:22），这次没有再盖一枚，行程里还是原来那一枚。 |
| PRE_SLICE2_dcb90ccc_phone | [] | 0→0 | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED |

## 四、门里的拒绝原文（四字段陈列，不造句子）

- 基座 wt7：NOT_MEASURED（件缺）
- 候选 wt6 `main.py` sha256 `c8a3d511c7e5f473…`，库行数 0→2，共享库未被动：True

  | 用例 | http_status | content_type | body_bytes | reason_code | 句子里有 uuid | details 为 null | details |
  |---|---|---|---|---|---|---|---|
  | no_target_named | 422 | application/json | 295 | CHECKIN_TARGET_REQUIRED | False | False | {"fields": ["activity_id", "place_id"]} |
  | both_targets_named | 422 | application/json | 365 | CHECKIN_TARGET_AMBIGUOUS | False | False | {"activity_id": "3a58c470-524c-5854-aa39-6c37a350eb80", "place_id": "place-old-town"} |
  | activity_not_on_this_server | 404 | application/json | 311 | CHECKIN_ACTIVITY_UNKNOWN | False | False | {"activity_id": "809517d7-6cf1-4875-85c7-c9ac8c220075"} |
  | place_not_on_this_server | 404 | application/json | 302 | CHECKIN_PLACE_UNKNOWN | False | False | {"place_id": "809517d7-6cf1-4875-85c7-c9ac8c220075"} |
  | write_door_unknown_journey | 404 | application/json | 235 | NOT_MEASURED | True | True | NOT_MEASURED |
  | read_door_unknown_journey | 404 | application/json | 235 | NOT_MEASURED | True | True | NOT_MEASURED |
  | first_tap_on_a_real_stop | 201 | application/json | 435 | NOT_MEASURED | False | True | NOT_MEASURED |
  | same_stop_tapped_again | 409 | application/json | 434 | CHECKIN_DUPLICATE_STAMP | False | False | {"target_key": "activity:3a58c470-524c-5854-aa39-6c37a350eb80", "existing_checkin_id": "78843135-c0c4-43eb-a66c-45614d35 |
  | second_stop_tapped | 201 | application/json | 438 | NOT_MEASURED | False | True | NOT_MEASURED |
  | read_footprints_back | 200 | application/json | 876 | NOT_MEASURED | False | True | NOT_MEASURED |

## 五、反件一（服务端 409 判据摘掉）

| 侧 | 收集 | 通过 | 失败 | 退出 | 失败的臂 |
|---|---|---|---|---|---|
| candidate_wt16 | NOT_MEASURED | 16（臂名去重） | 0（臂名去重） | 0 | [] |
| mutant_wt16_ce1 | NOT_MEASURED | 13（臂名去重） | 3（臂名去重） | 1 | ["test_a_footprint_outlives_the_rows_it_pointed_at", "test_the_duplicate_answer_comes_from_the_door_and_not_from_the_index", "test_the_duplicate_is_answered_before_the_target_row_is_asked_about"] |

两枚树只差 `backend/app/main.py` 一枚文件（比对 425 枚，data/contracts/generated 全等，件 ）；交付那枚的 `main.py` 前后 sha256 同一枚：ddf42ebe8c12e42c…（本机字节 sha256，不是 git 物件，不可 cat-file）

## 六、反件二（屏上的标不是门里给的）

- TIP_7862c6de_phone：门里 0 行时屏上 0 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 2 枚
- O0500_R3_phone：门里 0 行时屏上 0 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 2 枚
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

  （同跑的库行数 base_tip：0→2，入口 index-DaHdgt6W.js，服务字节与磁盘字节相等 True）
  （同跑的库行数 candidate_o0500：0→2，入口 index-B-4JbgaK.js，服务字节与磁盘字节相等 True）
  （同跑的库行数 mutant_clientbool_ce2：0→1，入口 index-BnrJYfML.js，服务字节与磁盘字节相等 True）

## 九、没走的与不修的（具名）

- 真机与隧道：NOT_MEASURED，以上全是本机 127.0.0.1 面上的模拟器读数。
- 整套 Playwright 验收：NOT_EXECUTED，只跑本单自己的载体与邻座已收的词汇闸。
- `GET /api/v1/journeys/{id}/checkins` 那一扇门在基座代仍不给未知行程具名（`require()` 印 uuid 且 details 为 null）：本单在候选代把两扇门一起具名了，但契约侧只写 POST 的 404 —— 因为 GET 侧补 404 会撞 ORD-0476 已收的那条契约臂（`sorted(listed["responses"]) == ["200", "409"]`），那是别人手上的判据，我不改。这条缺口具名留着，不在我写集里。
