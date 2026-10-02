# ORD-0500 r6 -- 英文档那一格：读数单（基座 `06ad00b0267c2bef08d4cdcbae2e5a206ded8666`，候选 = 本枝 `71e855fa492901075a5abc8e0db97fee37b17d8e`）

生成 `2026-10-03T05:09:35.419513+08:00`。本代新取的读数才写在这页上；r5 那一代的屏幕数不在这里折算，只在第八节按枝点名。

## 一、两枚面的身份（同一枚工作树换字节再换回来，换回后逐枚 blob 验过）

| 面 | 入口 JS | CSS | bundle 字节 | tsc check | tsc all | build |
|---|---|---|---|---|---|---|
| TIP_06ad00b0 | index-DeyXt9ON.js | index-BeJMb-k7.css | 1620076 | 0 | 0 | 0 |
| O0500_R14 | index-Dfm4dhFz.js | index-BeJMb-k7.css | 1619618 | 0 | 0 | 0 |

换回候选字节之后的核对：`every_path_matches_the_commit` = True，`worktree_clean_after_restore` = True，不吻合的枚数 0；基座面上不存在（本单新增）的路径 0 枚。件 `receipts/build_faces_r6.json`。

## 二、四趟屏幕读数（390x844、触摸档、判据读渲染文字；每趟一份新私库）

| 跑 | locale | 控件 | 中心命中 | 句主 | 拒绝句枚数 | 屏上 CJK 枚 | CJK 段落 | 屏上标（中/英/按状态） |
|---|---|---|---|---|---|---|---|---|
| O0500_R14_zh | zh-CN | 6 | 5 | ["Riverside Museum"] | 1 | 308 | ["菜单", "行程", "跟随系统", "住宿", "预订", "花费", "把这趟旅行收成一张长图", "图上每一天", "就是这块屏上已经排好的那些", "展开行程长图", "中止之后"] | 1/0/1 |
| O0500_R14_en | en-US | 6 | 6 | ["Old Town Gate"] | 1 | 2 | ["中文"] | 0/1/1 |
| TIP_06ad00b0_zh | zh-CN | 6 | 5 | ["Riverside Museum"] | 1 | 308 | ["菜单", "行程", "跟随系统", "住宿", "预订", "花费", "把这趟旅行收成一张长图", "图上每一天", "就是这块屏上已经排好的那些", "展开行程长图", "中止之后"] | 1/0/1 |
| TIP_06ad00b0_en | en-US | 6 | 6 | ["Old Town Gate"] | 1 | 2 | ["中文"] | 0/1/1 |

- TIP_06ad00b0_en 那句逐字：This stop is already stamped (3 Oct, 05:00); nothing new was written — the trip keeps the stamp it had.
- O0500_R14_en 那句逐字：This stop is already stamped (3 Oct, 04:58); nothing new was written — the trip keeps the stamp it had.
- O0500_R14_zh 那句逐字：这一站已经打过卡了（服务器记的是 10月3日 04:57），这次没有再盖一枚，行程里还是原来那一枚。

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

- `2` 两套 ["tests/test_qoder_ord0500_journey_refusal.py", "tests/test_qoder_ord0476_checkins.py"] 个文件在私库 `r6_pytest.db` 上跑：退出 0，尾行逐字 16 passed, 2 warnings in 2.31s；跑后库里 9 行。
- 共享库前后：字节 7213056 对 7213056、mtime_ns 1790644827980246600 对 1790644827980246600，未被动过 = True。
- 三枚 `backend/app/main.py` blob：本轮候选 `8b5c56d248560028f2d3de0dc9f697de06630243`、r5 那一笔 `6448e5e74c394c18aad96c231ef4865540a75f20`、判读时现尖 `8b5c56d248560028f2d3de0dc9f697de06630243`。候选与 r5 同一枚 = False（不是：基座走过别人好几笔，这枚文件别处也动过）；候选与判读时的现尖同一枚 = True，这一枚相等就是「产品字节已经在线上」的字节证，所以 r6 那阵子用来撑「同一笔 hunk」的形状核对（`git diff --numstat` 14 增 2 删）在本轮不再是必要的说法。具名 `CHECKIN_JOURNEY_UNKNOWN` 的枚数：工作树 2 处、本枝 HEAD `6f358b79ad9a` 2 处（这两个数是渲染本页时现读的，不是抄上来的）。

## 六、Q64 曝光尺：本代两侧各一趟

| 面 | 格总数 | 图内模块 | 未解析 import | 解析诊断 |
|---|---|---|---|---|
| 基座 dc9dc10f | 6 | 341 | 58 | 0 |
| 候选 r6 | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED | NOT_MEASURED |

格总数相等：False；逐枚（文件:行）集合相等：False；候选侧多出的格：无。也就是「把该档屏幕自己的控件名插进句子」这条路没有把正文值送进任何共用 helper。

## 七、这单还欠的一格（要裁，我不自己拍）

- 字典里 `[]` 这几行现在没有读者（读计数逐行 []），行号是 []。留、删、还是让我屏回去读，三种形状的代价在我 19:40 那块里写过；本轮按推荐的「留着 + 钉住」做，没动那枚热文件。

## 八、不在本代的东西（具名，不折算）

- r5 那一代的六趟屏幕普查、三枚门探针、两枚反件在枝 `review/newlane-ord0500-phone-checkin-entry-r5` 的 `review/ord0500-checkin/` 里，本单不重述其数。
- 手机第二站中心不可按那一格：本代四趟仍然量到 [["O0500_R14_zh", 5], ["O0500_R14_en", 6], ["TIP_06ad00b0_zh", 5], ["TIP_06ad00b0_en", 6]] 枚可按（基座与候选同数），归滚动容器与底栏两家，号令者已裁。
- 真机与隧道：NOT_MEASURED；整套 Playwright 验收：NOT_EXECUTED（只跑本单载体与词汇闸）；`targetRequired` 那句在屏幕上不可达（打卡钮永远带着一站的名字），所以它由第三节那道闸覆盖，不拿假可达的桩去凑一趟屏读。

## 九、r8：本枝注释里那四枚行号（只改了这一枚文件，且它不在前端图里）

| 说法 | 屏幕上原来写的 | 现尖读到的 | 那一行的原文 |
|---|---|---|---|
| require | 810 | 818 | def require(session: Session, model: type, identifier: str, label: str): |
| lookup | 3912 | 4256 | existing = session.scalars( |
| integrity | 3948 | 4292 | except IntegrityError as exc: |
| caught_by | 3965 | 4309 | "caught_by": "unique_index", |

- 行号来源不是记忆：尖 `569b8472b134e5562ef396e38681870b9c26536a` 的 `backend/app/main.py` 共 14476 行，打卡那扇门自己的区间按路由路径行定位到 [4210, 4329]，四枚锚都要求落在这段里并且段内唯一。件 `receipts/reanchor_r8.json`。
- 反件与闸自己也被反件验过：写坏正文（少一枚反引号）被 `ABORT_TEXT_CHANGED` 拒、把锚定短语改掉被 `ABORT_ANCHOR_PHRASE` 拒、正件跑通且「把每个数字遮掉之后正文逐字相同」= True。三臂 ["PASS", "PASS", "PASS"]。件 `receipts/reanchor_r8_selftest.json`。
- 这枚文件不在前端图里：`frontend_files_referencing_the_test` = []。本代不改前端字节，所以页面第六节那两枚面的入口名与 bundle 字节仍是 r7 那一代（第八节已具名），本页重渲染时没有把它们当作本轮新读数。
- 顺带把全线源码注释里的 `path:line` 都开了一遍：175 枚引文、71 个文件，逐条按现尖核对；本单自己那 4 枚全 OK，其余不 OK 的 16 枚归别的单子（清单在件里，只读，我没动别人手上的判据）。件 `receipts/citation_audit_r8.json`。

| 不 OK 的形状（159 枚 OK 不列） | 枚数 |
|---|---|
| BLANK_LINE_CITED | 13 |
| ORPHAN_BARE | 1 |
| UNRESOLVED_PATH | 2 |


## 十、r9 与 r10：把「自家注释行号不许腐烂」装进随代必跑的闸（r10 把闸的范围改成按作者定）

| 项 | 读数 |
|---|---|
| 闸判的树尖 | 441c98320521b9d0fcd17d1aab904f45473ffbab |
| 扫的文件 | 8 枚（本单写集，按 `git log` 现读）；其中带引文被判的 1 枚 |
| 判与不判 | 看到 22 条，判 8 条，不判 14 条（不判=那一行的作者 commit 不在本单名下，逐条带 `owner_commit`）；本单名下 commit 11 枚 |
| 查的引文 | 22 枚，其中 4 枚带内容钉子（句子声称那一行写着什么，就真去读那一行） |
| 判语 | GREEN，红 0 枚，各类计数 {"OK": 8, "NOT_THIS_LANES_CITATION": 14, "CITED_FILE_ABSENT": 0, "CITED_LINE_BEYOND_FILE": 0, "CITED_LINE_IS_BLANK": 0, "CITED_LINE_CONTENT_MISMATCH": 0, "CITED_PHRASE_GONE_FROM_COMMENT": 0} |
| 钉子的来处 | 与 r8 那把尺的读数相符 = True（从枝里 receipts/reanchor_r8.json 现读） |
| 换代复读（件 `day25_anchor_recheck_r14.json`，尖 `06ad00b0267c2bef08d4cdcbae2e5a206ded8666`） | 四枚锚仍是 {"require": 818, "lookup": 4256, "integrity": 4292, "caught_by": 4309}；注释里现引的就是 {"require": 818, "lookup": 4256, "integrity": 4292, "caught_by": 4309}；本枝产品路径与上一枝逐枚等值 = False |

反件 6 枚各咬一格（含 M5/M6 那对反方向的作者件），全在临时目录里、不碰工作树（`18` 份副本，判它用的登记清单仍取真实仓库的 3280 条）：[["C1_control_copy", "GREEN", "GREEN", true], ["M1_beyond_file", "RED", "CITED_LINE_BEYOND_FILE", true], ["M2_blank_line", "RED", "CITED_LINE_IS_BLANK", true], ["M4_wrong_but_in_range", "RED", "CITED_LINE_CONTENT_MISMATCH", true], ["M3_absent_file", "RED", "CITED_FILE_ABSENT", true], ["C2_after_revert", "GREEN", "GREEN", true], ["M5_foreign_line_not_judged", "GREEN", "GREEN", true], ["M6_same_line_claimed_mine", "RED", "CITED_LINE_BEYOND_FILE", true], ["C3_after_foreign_revert", "GREEN", "GREEN", true]]。控制趟 GREEN、还原后 GREEN、副本字节回来了 = True、`wt22` 干净 = True。件 `receipts/citation_gate_r10_mutants.json`。

闸拦不住的那一格也具名：它只能读「那一行现在写着什么」，读不出「这句话本来想指哪一行」；所以钉子换代的唯一合法路径是重跑 `reanchor_r8.py` 让它重新量锚并落新件，而不是手改这几个字符串。

