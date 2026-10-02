# ORD-0500 r6 -- 英文档那一格：读数单（基座 `dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5`，候选 = 本枝）

生成 `2026-10-02T17:06:16.021670+08:00`。本代新取的读数才写在这页上；r5 那一代的屏幕数不在这里折算，只在第八节按枝点名。

## 一、两枚面的身份（同一枚工作树换字节再换回来，换回后逐枚 blob 验过）

| 面 | 入口 JS | CSS | bundle 字节 | tsc check | tsc all | build |
|---|---|---|---|---|---|---|
| TIP_dc9dc10f | index-C2qctsTa.js | index-CTUw3tbX.css | 1580845 | 0 | 0 | 0 |
| O0500_R6 | index-C2dITzmr.js | index-1BWtJQ-v.css | 1584676 | 0 | 0 | 0 |

换回候选字节之后的核对：`every_path_matches_the_commit` = True，`worktree_clean_after_restore` = True，不吻合的枚数 0；基座面上不存在（本单新增）的路径 4 枚。件 `receipts/build_faces_r6.json`。

## 二、四趟屏幕读数（390x844、触摸档、判据读渲染文字；每趟一份新私库）

| 跑 | locale | 控件 | 中心命中 | 句主 | 拒绝句枚数 | 屏上 CJK 枚 | CJK 段落 | 屏上标（中/英/按状态） |
|---|---|---|---|---|---|---|---|---|
| TIP_dc9dc10f_zh | zh-CN | 6 | 5 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 6 | 364 | ["菜单", "行程", "跟随系统", "住宿", "预订", "花费", "把这趟旅行收成一张长图", "图上每一天", "就是这块屏上已经排好的那些", "展开行程长图"] | 1/0/1 |
| TIP_dc9dc10f_en | en-US | 6 | 5 | ["Old Town Gate", "Riverside Museum", "Central Food Hall", "Tech Art Center", "Nexus River Cruise Pier", "Skyline Dinner House"] | 6 | 2 | ["中文"] | 0/1/1 |
| O0500_R6_zh | zh-CN | 6 | 5 | ["Old Town Gate"] | 1 | 201 | ["菜单", "行程", "跟随系统", "住宿", "预订", "花费", "把这趟旅行收成一张长图", "图上每一天", "就是这块屏上已经排好的那些", "展开行程长图"] | 1/0/1 |
| O0500_R6_en | en-US | 6 | 5 | ["Old Town Gate"] | 1 | 2 | ["中文"] | 0/1/1 |

- TIP_dc9dc10f_en 那句逐字：The server already holds a stamp for this stop, so this trip kept the one it had — nothing was overwritten.
- O0500_R6_en 那句逐字：This stop is already stamped (2 Oct, 16:52); nothing new was written — the trip keeps the stamp it had.
- O0500_R6_zh 那句逐字：这一站已经打过卡了（服务器记的是 10月2日 16:51），这次没有再盖一枚，行程里还是原来那一枚。

屏上那两枚 CJK 字是 `["中文"]` —— 语言切换控件自己的名字，两代都在、与我这笔无关；所以判据按「除这枚标签外 en 屏无 CJK，且拒绝句与控件名无 CJK」写，不写「整屏 0 枚」（那样基座也红，量的就不是我这笔了）。

每趟的面身份两证齐：入口名取自被服务的 index.html 并与 `build_faces_r6.json` 记的名比对，服务字节与磁盘字节 html/bundle 都相等（`identity_ok` 逐趟 [true, true, true, true]）；第三证具名 `NOT_AVAILABLE_BY_CMDR`（vite preview 不往我控制的日志写请求行）。

## 三、词汇闸（十一行 × 两档，逐行）

| 行 | en 值所在行 | en 里的 CJK | 占位符 | 调用点供上的参数 |
|---|---|---|---|---|
| activityNotInJourney | 56 | none | [] | ["button"] |
| activityUnknown | 52 | none | [] | ["button"] |
| duplicateAt | 44 | none | ["moment"] | ["button", "moment"] |
| duplicateNoMoment | 48 | none | [] | [] |
| journeyInBin | 76 | none | [] | ["button"] |
| journeyUnknown | 80 | none | [] | ["button"] |
| placeUnknown | 60 | none | [] | ["button"] |
| targetAmbiguous | 72 | none | [] | ["button"] |
| targetRequired | 68 | none | ["button"] | ["button"] |
| unexpected | 88 | none | ["status"] | ["status"] |
| unreachable | 84 | none | [] | [] |

闸总结：GREEN，检查 11 行，命中 0 条。件 `receipts/checkin_copy_rows_r6.json`。

## 四、两枚反件（各咬自己那一格，跑完按原字节还原）

| 反件 | 做什么 | 期望 | 退出 | 命中的判据 | 还原后退出 | 还原后判据 | 字节回来了 |
|---|---|---|---|---|---|---|---|
| M1_hard_coded_label_back | 把写死的中文控件名放回英文行 | RED | 1 | ["A1_CJK_IN_ENGLISH_ROW"] | 0 | GREEN | True |
| M2_placeholder_left_unsupplied | 把调用点的 button 参数摘掉，句子里留下花括号 | RED | 1 | ["B1_UNSUPPLIED_PLACEHOLDER", "B2_LABEL_IS_INTERPOLATED"] | 0 | GREEN | True |

控制趟 GREEN（退出 0）；`every_mutant_bit` = True。件 `receipts/checkin_copy_rows_mutants_r6.json`，五次闸跑各留一件 （`checkin_copy_rows_r6_control / _M1 / _M1_revert / _M2 / _M2_revert.json`）。

## 五、门里的臂（服务端没被我碰，还是要在本代跑一遍）

- `2` 两套 ["tests/test_qoder_ord0500_journey_refusal.py", "tests/test_qoder_ord0476_checkins.py"] 个文件在私库 `r6_pytest.db` 上跑：退出 0，尾行逐字 16 passed, 2 warnings in 2.55s；跑后库里 9 行。
- 共享库前后：字节 7213056 对 7213056、mtime_ns 1790644827980246600 对 1790644827980246600，未被动过 = True。
- 三枚 `backend/app/main.py` blob：候选 `6448e5e74c394c18aad96c231ef4865540a75f20`、r5 那笔 `6448e5e74c394c18aad96c231ef4865540a75f20`、现尖 `86049dcb17b8d44ac4dc1a0b6106b8d9cbb9753b`——前两枚同一枚，所以我带的是 r5 的后端字节、不是我又改了一版。

## 六、Q64 曝光尺：本代两侧各一趟

| 面 | 格总数 | 图内模块 | 未解析 import | 解析诊断 |
|---|---|---|---|---|
| 基座 dc9dc10f | 6 | 327 | 55 | 0 |
| 候选 r6 | 6 | 330 | 55 | 0 |

格总数相等：True；逐枚（文件:行）集合相等：True；候选侧多出的格：无。也就是「把该档屏幕自己的控件名插进句子」这条路没有把正文值送进任何共用 helper。

## 七、这单还欠的一格（要裁，我不自己拍）

- 字典里 `["checkin.duplicate", "checkin.refused"]` 这几行现在没有读者（读计数逐行 [0, 0, 0, 0]），行号是 [118, 119, 1253, 1254]。留、删、还是让我屏回去读，三种形状的代价在我 19:40 那块里写过；本轮按推荐的「留着 + 钉住」做，没动那枚热文件。

## 八、不在本代的东西（具名，不折算）

- r5 那一代的六趟屏幕普查、三枚门探针、两枚反件在枝 `review/newlane-ord0500-phone-checkin-entry-r5` 的 `review/ord0500-checkin/` 里，本单不重述其数。
- 手机第二站中心不可按那一格：本代四趟仍然量到 [["TIP_dc9dc10f_zh", 5], ["TIP_dc9dc10f_en", 5], ["O0500_R6_zh", 5], ["O0500_R6_en", 5]] 枚可按（基座与候选同数），归滚动容器与底栏两家，号令者已裁。
- 真机与隧道：NOT_MEASURED；整套 Playwright 验收：NOT_EXECUTED（只跑本单载体与词汇闸）；`targetRequired` 那句在屏幕上不可达（打卡钮永远带着一站的名字），所以它由第三节那道闸覆盖，不拿假可达的桩去凑一趟屏读。
