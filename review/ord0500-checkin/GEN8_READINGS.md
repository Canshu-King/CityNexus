# ORD-0500 r4 -- 现尖 514b397f96f3b5165b24865f4a544ab6f8020084 读数单（与 ORD-0530 同族并块后重量；曝光尺两侧对照在 receipts 里）

生成时间 `2026-10-01T13:55:46.832064+08:00`；量具与件都在 `D:/moodle/_qoder_phone_ord0485_20260930`。

## 一、本代的产物身份（基座 + 交付候选 + 反件）

| 面 | 入口资产 | 打包字节数 | 打包 sha256（本机字节） | tsc check | tsc all | build |
|---|---|---|---|---|---|---|
| TIP_514b397f | index-DAbk3Cl8.js | 1574476 | 11b79828bceccb4b… | 0 | 0 | 0 |
| O0500_R4 | index-BmVDim7u.js | 1578240 | 352fa9a5b23b866a… | 0 | 0 | 0 |
| O0500_CLIENTBOOL_MUTANT | index-r0Uk3S3Z.js | 1578272 | c542e2bedf5a56e5… | 0 | 0 | 0 |

本机字节 sha256，不是 git 物件，不可 cat-file；件 `evidence/gen8_builds_r1.json`。

## 二、打卡门在本代的普查（390x844 与 1280x800 各一趟，每趟一份新库）

| 跑 | 视窗 | 站数 | 控件枚数 | 中心命中可按 | 盒 | 到屏时门里行数 | 屏上已打卡枚数 |
|---|---|---|---|---|---|---|---|
| TIP_514b397f_phone | 390x844 | 6 | 6 | 5 | ["44x44"] | 0 | 0 |
| TIP_514b397f_desktop | 1280x800 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_R4_phone | 390x844 | 6 | 6 | 5 | ["44x44"] | 0 | 0 |
| O0500_R4_desktop | 1280x800 | 6 | 6 | 6 | ["44x44"] | 0 | 0 |
| O0500_CLIENTBOOL_MUTANT_phone | 390x844 | 6 | 6 | 5 | ["44x44", "54x44"] | 0 | 3 |
| PRE_SLICE2_dcb90ccc_phone | 390x844 | 6 | 0 | 0 | [] | 0 | 0 |

## 三、真发一发：行数前后与那句拒绝

| 跑 | 请求序列 | 行数 前→后 | 重复点击后屏上拒绝句枚数 | 句主 | 句子 |
|---|---|---|---|---|---|
| TIP_514b397f_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 6 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 服务器说这一站已经有一枚印了，所以这次没有覆盖，行程保留它原有的那一枚。 |
| TIP_514b397f_desktop | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 6 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 服务器说这一站已经有一枚印了，所以这次没有覆盖，行程保留它原有的那一枚。 |
| O0500_R4_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Old Town Gate"] | 这一站已经打过卡了（服务器记的是 10月1日 13:39），这次没有再盖一枚，行程里还是原来那一枚。 |
| O0500_R4_desktop | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Old Town Gate"] | 这一站已经打过卡了（服务器记的是 10月1日 13:40），这次没有再盖一枚，行程里还是原来那一枚。 |
| O0500_CLIENTBOOL_MUTANT_phone | ["GET:200", "POST:201", "GET:200", "POST:409", "GET:200", "POST:201", "GET:200"] | 0→2 | 1 | ["Tech Art Center"] | 这一站已经打过卡了（服务器记的是 10月1日 13:41），这次没有再盖一枚，行程里还是原来那一枚。 |
| PRE_SLICE2_dcb90ccc_phone | [] | 0→0 | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED |

## 四、门里的拒绝原文（四字段陈列，不造句子）

- 基座 wt7：NOT_MEASURED（件缺）
- 候选 wt6：NOT_MEASURED（件缺）
## 五、反件一（服务端 409 判据摘掉）

| 侧 | 收集 | 通过 | 失败 | 退出 | 失败的臂 |
|---|---|---|---|---|---|
| candidate_wt19 | NOT_MEASURED | 16（臂名去重） | 0（臂名去重） | 0 | [] |
| mutant_wt19_ce1 | NOT_MEASURED | 13（臂名去重） | 3（臂名去重） | 1 | ["test_a_footprint_outlives_the_rows_it_pointed_at", "test_the_duplicate_answer_comes_from_the_door_and_not_from_the_index", "test_the_duplicate_is_answered_before_the_target_row_is_asked_about"] |

两枚树只差 `backend/app/main.py` 一枚文件（比对 430 枚，data/contracts/generated 全等，件 ）；交付那枚的 `main.py` 前后 sha256 同一枚：eedad6bfc20ae928…（本机字节 sha256，不是 git 物件，不可 cat-file）

## 六、反件二（屏上的标不是门里给的）

- TIP_514b397f_phone：门里 0 行时屏上 0 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 2 枚
- O0500_R4_phone：门里 0 行时屏上 0 枚「已打卡」；走完两站后门里 2 行、最后一次屏读 2 枚
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

  （同跑的库行数 base_tip：0→2，入口 index-DAbk3Cl8.js，服务字节与磁盘字节相等 True）
  （同跑的库行数 candidate_o0500：0→2，入口 index-BmVDim7u.js，服务字节与磁盘字节相等 True）
  （同跑的库行数 mutant_clientbool_ce2：0→1，入口 index-r0Uk3S3Z.js，服务字节与磁盘字节相等 True）

## 九、没走的与不修的（具名）

- 真机与隧道：NOT_MEASURED，以上全是本机 127.0.0.1 面上的模拟器读数。
- 整套 Playwright 验收：NOT_EXECUTED，只跑本单自己的载体与邻座已收的词汇闸。
- `GET /api/v1/journeys/{id}/checkins` 那一扇门在基座代仍不给未知行程具名（`require()` 印 uuid 且 details 为 null）：本单在候选代把两扇门一起具名了，但契约侧只写 POST 的 404 —— 因为 GET 侧补 404 会撞 ORD-0476 已收的那条契约臂（`sorted(listed["responses"]) == ["200", "409"]`），那是别人手上的判据，我不改。这条缺口具名留着，不在我写集里。
