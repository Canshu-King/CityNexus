# 日历导出（ORD-0496 切片 3）：移植接法、它必须改的那一处接缝、以及量具自己错过六次（2026-10-15 02:35）

这份文件只写接缝与实测，不写功能介绍。所有行号是**当前工作树现读**（`grep -n` / 逐行读），
源树一侧的行号来自移植源尖 `eeb8b8d2fd`。逐字搬的件按 sha1 说话，不按印象说话。

## 1. 两边到底有什么（先把「搬了什么、是不是逐字」钉准）

| 件 | 移植源 `eeb8b8d2fd` | 融合基线 `594f9a4e75` | 本片落地后 |
|---|---|---|---|
| 导出器 | `backend/app/calendar_export.py` 351 行 | **无此文件** | **有**，sha1 `9fceab781c` **与源树逐字节相同**（纯语法件，不碰 HTTP、不碰 session，所以没有任何一处需要为这棵树改） |
| 那扇门 | `main.py:4120` `GET .../calendar.ics`，签名 `(journey_id, session)` | 无 | `main.py:27391`，签名 `(journey_id, request, session)` —— **多出来的那一枚 `request` 就是本片全部的接缝**（§2） |
| 门前的助手 | `_calendar_journey(session, journey_id)`（`main.py:4043`，走 `require`） | 无 | `_calendar_principal:27283`、`_calendar_scope_param:27296`、`_calendar_journey_not_found:27314`、`_calendar_journey:27323`、`_calendar_activities:27346`；`main.py:53` 引入导出器的 4 枚名字 |
| 前端模块 | `features/trip/calendarExport.ts` 146 行 | **无此文件** | **160 行**，sha1 `9507025278`（**与源树不同**，差在 §2 第三条：发凭据 + 两处口径注释） |
| 屏幕 | `TripItinerary.tsx` 里那枚按钮 | 无 | `TripItinerary.tsx:294-307`（`calendar-export` / `calendar-export-notice`） |
| 全局词典 | 9 枚 `calendar.*` | 0 | **9 枚 × 两语 = 18 行**，`LocaleContext.tsx:330-338`（en）与 `:1291-1299`（zhCN），**三枚提交、每枚 ≤3 键** |
| 守门测试 | `backend/tests/test_qoder_ord0496_calendar_export.py` 15 条 | 无 | **17 条**（sha1 `43b688a5b0`，与源树 `080683d5dc` 不同：§3 的改造），另加活口 `frontend/e2e/qoder-ord0496-calendar-export-390x844.spec.ts` |
| 布景事实 | `review/ord0496/store_shape_census_r1.py` | 无 | **有**，sha1 `c0006692cd` 与源树逐字节相同（有一枚臂断言这枚文件在场，所以它必须真在场并且真跑得动） |

源树自己的分片口径也记一下，因为它解释了为什么这棵树上「一片」里有按钮：源树 `main.py:4038` 的注释写着
「ORD-0496 slice 1 = 门与契约，屏幕入口是 slice 2，故意不在这儿」。融合树的切片 3 一次带走门 + 屏幕，
契约（`contracts/openapi.yaml` 声明 + 生成客户端）**没带**，见 §6。

## 2. 唯一一处非改不可：这扇门在这棵树上不能是匿名的

源树的门收 `journey_id` 就发日历：`_calendar_journey` 里是 `require(session, Journey, journey_id, "Journey")`，
拿到就把整条行程的时刻表发出去。融合树的 charter 与自己已经落地的先例（切片 1 的 `_checkin_journey_read`、
收藏门 `_collection_payloads`、足迹门）都是另一条规矩：**行程子门一律从签名凭据里解出旅行者，再比
`journeys.traveler_id`**，并且结构性地拒收查询里写来的 `traveler_id`（切片 1 已把这条写进契约：
`COLLECTION_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED`）。所以：

- `_calendar_principal(request, session)` 就是 `app/traveler_principal.resolve_traveler_principal`，
  与打卡/收藏同一枚；它没配密钥时 **503 关门**，不会被读成「谁都能导出」。
- `_calendar_scope_param(request)`：查询里出现 `traveler_id` ⇒ **422 `CALENDAR_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED`**，
  点名拒收。忽略它是更坏的答案：调用方会以为自己的话被听了。凭据这一关在它前面。
- `_calendar_journey(session, journey_id, principal)`：**「没有这趟」与「这趟是别人的」是同一枚应答**
  （404 + `JOURNEY_NOT_FOUND` + `details.journey_id`），所以谁也不能拿它探一枚 id 在不在。
  回收站里的那趟是 **409 `CALENDAR_JOURNEY_IN_RECYCLE_BIN`**，不是 404：行还在，找回还得回来。
- 源树的 404 是把 `reason_code` **贴到 `require` 自己抛的那枚异常上**（它要保住读权威的原话）；
  融合树这侧 `require` 不知道主人是谁，所以 `_calendar_journey_not_found` 自己造 404，
  句子按 `require` 的模板写：`Journey {id} was not found`。**这是一处口径差，不是同一件代码**——
  它 echoes 调用方自己送进来的 uuid（ORD-0500 早就抱怨过读权威这句），本片不改邻居的措辞。
- 三条 `CALENDAR_SOURCE_UNREADABLE`（`ACTIVE_PLAN_NOT_DECLARED` / `ACTIVE_PLAN_ROW_ABSENT` /
  `ACTIVE_PLAN_BELONGS_TO_ANOTHER_JOURNEY`）、六枚 `X-CityNexus-Ics-*` 头、以及头里的算术
  `activities = events + skipped_no_clock + skipped_no_stamp` **全部照源树**，一个字没改。
- 前端 `calendarExport.ts` 跟着改一处：`fetch(CALENDAR_PATH(id), { headers: travelerAuthHeaders() })`
  （`travelerSession.ts:55`）。它原来那三枚服务端名字是照 `contracts/openapi.yaml` 读的，
  **这棵树的契约还没声明这枚操作**，所以注释改成照 `backend/app/main.py` 读；凭据类拒绝落
  `UNRECOGNISED`（源树没有这条通道，因为源树没有凭据）。

## 3. 测试怎么搬的：先按原样跑，再改

先按**逐字节复制**跑了一遍：**15 failed / 0 passed**。红因是接缝不是移植——每一枚都红在
`401 REQUEST_ERROR` / `error.request_error` 上（门现在要凭据）。这一步先做，是为了让「15 枚红」成为
一条**可引用的读数**，而不是我事后说「原样搬会红」。

改造清单（与切片 1/2 的打卡文件同一套）：

1. 模块级 autouse fixture 塞一枚一次性 `CITYNEXUS_TRAVELER_AUTH_SECRET`（`_TEST_SECRET`，本单专用，非生产密钥）；
2. `_auth(traveller_id)` 用产品自己的服务端签名口 `issue_traveler_token` 造凭据；
3. `_journey()` 把主人记进 `_OWNER`，`_trip()` 返回 `"traveler"`，于是每枚臂的作用域在请求之前就是已知的；
4. `_ics(journey, headers=None)`：`None` 才是匿名，`{}` 是「带一枚空 header 集」，两者不能混——
   这就是切片 1 记过的 `headers={}` 陷阱；
5. 未知那趟改成 `_auth(_probe_traveller())` 签名的请求（否则它测的是「没这趟」而不是「不是你的这趟」）；
6. 尾部两枚依赖生成客户端的臂**不删**，改成 `DEFERRED_TO_THE_CONTRACT_LEG` +
   `test_the_two_source_arms_deferred_to_the_contract_leg_are_still_deferred_and_measured`：
   每次跑都现读路由在不在、契约里声明了没有，并 `assert not declared` ——
   **契约一落地这枚臂就喊红**，欠的腿不会因为换人而蒸发；
7. 新增三枚融合臂：匿名导出（不给日历字节）、别人凭据的合法 token 与「没有这趟」逐字同形（把 id 归一后比）、
   查询里点名别人 ⇒ 422 点名拒收。

结果：`pytest -q tests/test_qoder_ord0496_calendar_export.py` ⇒ **17 passed**（首趟 3.37s，控制腿里另量到 3.82s）。

还有一枚臂断言 `review/ord0496/store_shape_census_r1.py` 这枚文件在场（它要读真库形状），
所以我把 census 也搬了，并**自己重跑**它而不是引用源树写下的数：活动行 `total = 134`、带偏移的 `offset_plus = 134`。

## 4. 量具自己错过的九次，九次全在我这侧（不在产品那一侧）

1. **门控反向对照的第一版瞄错了人。** `review/ord0496/gate_can_go_red_r1.py` 第一版拿
   `if "traveler_id" in request.query_params:` 与 `return resolve_traveler_principal(request, session)`
   当锚点——这两串在 `main.py` 里**各出现 3 次**（收藏门、日历门、足迹门各一份），`replace(old, new, 1)`
   改到的是别人的门，于是日历臂稳稳绿着，读起来像「这条保证不重要」。现在锚点全部**断言唯一**
   （`TARGET_NOT_UNIQUE` 就报「控制过期」而不是「通过」），两处正文锚点带上日历函数自己的名字。
   改完：**CONTROLS_RAN=4 CONTROLS_THAT_BIT=4**，两枚被改文件跑完 `byte_identical=YES`。
2. **玻璃控制台的汇总读法把红跑读成绿跑——同一条 bug 我第二次犯。**
   `review/ord0496/glass_can_go_red_r1.py` 第一版取「最后一条含 passed/failed 的行」，
   而 Playwright 的 line reporter 把 setup 项目的 `1 passed` 与 chromium 项目的 `1 failed` 写在两行，
   于是三枚**真的 rc=1** 的控制被打印成 `GREEN 1 passed`。这与 `QODER_RESULT.md` §7.1 是同一个形状。
   现在：读**所有**计数行、`rc` 与计数不一致就报 `READER_BROKEN`、每趟原始输出落盘
   （`_glass_ctl_<run>.log`）事后可审；并且加了一条**未篡改的 BASELINE 腿**——
   不然一枚永远喊 RED 的读法能给自己刷 3/3。读法先离线拿 5 枚样本量过（含那枚真实 baseline 日志）才去跑栈。
   改完：**BASELINE GREEN passed=2；CONTROLS_RAN=3 CONTROLS_THAT_BIT=3**，两枚被改文件 `restored=True`。

3. **`summary()` 里的贪婪 `.` 把 156 读成 6。** 新写的 `review/ord0496/slice3_gates_r1.py` 第一版用
   `^.*(\d+) failed` 读 pytest 尾行，`.*` 吃掉 `15`、捕获组剩 `6`，四趟样本全被打成 `failed=5/6`——
   一位数看着完全合理，因为没有对照。现在锚成 `^(\d+) failed, (\d+) passed, …, (\d+) errors? in`，
   并且加了一条自我校验：**同一份日志里 `FAILED/ERROR` 行数必须等于尾行的 `failed+errors`**
   （实测 162=155+7、163=156+7 四趟全等）。这条等式是唯一能让「读错一位」当场现形的东西。
4. **词典闭包第一版多数出一枚键，且把她人的文件算进来。** 原样式匹配任意被引号包住的
   `calendar.*`，于是 `calendarExport.ts:143` 那枚**下载文件名兜底** `"calendar.ics"` 被当成词典键，
   打出 `ASKED 10 / MISSING 1`。虚报的破口与漏报的破口一样贵，所以只认两种形状：屏幕上的
   `t("calendar.x")` 与 `calendarExport.ts` 拒答表里的值 `: "calendar.x"`，**并且把每枚键的出处行号打出来**
   （`ASKED calendar.done <- TripItinerary:139 t()`）。改完：要 9 枚、词典有 9 枚、缺 0、共 18 行（两语各一份）。
5. **一句话被误判成「不是词典答的」。** 同枚文件里那句
   `GLASS_NOTICE_exported_IS_A_DICTIONARY_VALUE` 第一版拿存档句子去词典里做**字面**包含——
   `calendar.done` 的模板是 `已下载 {events} 个日程…`，渲染出来是 `已下载 9 个日程…`，
   于是**真出处**被判 False（这是我这一片第一次假红，之前的两次都是假绿）。改成把占位符与数字都折成 `#`
   再比，两句都 True。
6. **「89 行 CRLF」是我上一版自己写错的，现已改成 88。** 存档那枚文件 `count(b"\r\n") = 88`、
   `endswith(b"\r\n") = True`、`split(b"\r\n")` 得 **89 段且末段为空**——我上一版把**段数**当行数和另一趟的读数混在了一起
   （所以「上一趟 89、这一趟 88」根本不是两趟有差，是我拿两种数法各读了一次）。
   教训落到脚本里：`slice3_gates_r1.py` 现在同时打 `crlf_pairs / physical_lines_nonempty /
   是否以 CRLF 收尾`，不让人再拿一个孤零零的「行数」说话。

7. **差集那枚标签把自己骗了，同一次改动里还写出了一枚恒空的交集。**
   `slice3_gates_r1.py` 原先打 `RED_ONLY_IN_SLICE3_STABLE_IN_BOTH_SAMPLES`，减数是上一尖两趟的**交集**，
   于是「上一尖只红过一趟」的名字被报成「新且稳定」——实际值 `1` 就是上一尖也红过的那枚 `g3_xproc`。
   同一枚 diff 里我把「红于全部样本」写成 `set().intersection(*sets.values())`：**空集**做 receiver，恒为空，
   「逐趟归属表」当场把整片红面（一百多枚）当差集打了出来。改成 `set.intersection(*sets)`。
   现在四行标签各自描述自己的算法（`…_AND_IN_NEITHER_…` / `…_BUT_ALREADY_FLAKY_ON_…` 各两行），
   并补了 `MEMBERSHIP_TABLE`：`- Y Y Y`／`Y - - -`／`- - Y -` 三行，谁在哪趟红过是可点的，不用信我这句「稳定」。
   这枚是本轮最值钱的修法：**没有那张表，`1` 会顺理成章读成「切片 3 带来一枚新红」**，
   而真数是 §1b 那次空白对照（同码两棵树、基线 2/16 对本尖 1/16）。
8. **`grep -c` 的退出码被当成「文件不存在」**：第 14 条刚立完「判不存在之前先在文件系统里找一遍」，
   我就用 `grep -c live_view backend/app/services.py || echo "NO FILE"` 得出「融合树没有这枚文件」，
   并把它当切片 3b 的未知项写进文档。零命中（回 `0`、退出码 `1`）与文件缺失是两回事；
   现读三棵树这枚文件都在（融合尖 132459 B / 融合基线 125832 B / 源树 96762 B），为 0 的是里面的 `live_view`。
   这条与 `QODER_RESULT.md` §7 第 6 条（`REMOTE_TIPS` 那枚 `rc=0` 的空读数）同形状，
   差别只在这次是**非零码**被读成不存在：凡靠退出码分支的判断都要自带一枚存在性腿。

9. **核「一杖最多三枚键」的那条正则吃不下下划线**。我先用一条 bash `grep -oP '^\+\s+"[a-zA-Z.]+"(?=:)'` 数每枝提交新增的键，
   字符类里没有 `_`，于是 `calendar.refused.not_found` 与 `calendar.refused.not_calendar` 两枚凭空消失，
   中间那枝被打成「2 枚键」（真数 3）。**错的方向是少报**，看着像更守规矩，所以没人会去查它——
   同一个字符类若长在 ASKED 那一侧，闭包会因为「不问了」而绿，那才是它贵的地方。
   修法不是改 bash，是把这条审计搬进仓库（`slice3_gates_r1.py::dictionary_branch_audit`）：字符类 `[A-Za-z0-9_.]+`、
   逐枝打印键名、并自带一枚**合成自检**（拿 `+  "calendar.refused.not_found": "x",` 喂 reader，读不全就 BROKEN + 退出码 1）。
   反向对照同样搬进仓库并可跑：`python review/ord0496/slice3_gates_r1.py --run-control dictclass`
   **在进程内**把字符类换成我写错的那枚 `[A-Za-z.]`（不写盘、不留脏文件）⇒ 审计必须红，实测
   `CONTROL dictclass BITE rc= 1`、总数 **20 → 18**、两枝被读成 2 枚键、`OVER_3_KEYS` 仍是 **0**（少报伪装成守规矩）；
   换回正解 ⇒ `DICTIONARY_BRANCH_COMMITS 8 / KEYS_ADDED_TOTAL 20 / OVER_3_KEYS 0 / SELF_CHECK PASS`（逐枝 3,3,3,3,3,3,1,1）。

另外四枚「量具能吐红」的反向对照也做了：
`tsc` 那侧往 `calendarExport.ts` 塞一行 `const CONTROL: number = 'not a number';` ⇒
`error TS2322` 点名这枚文件，改回 ⇒ 两枚 config 各 **0 错误行**（所以那两个 0 是「文件在程序里」而不是「没在看」）；
`CRLF` 那侧本片 6 枚新/改文本文件逐枚数 `\r\n` ⇒ **0**；
spec 的 tsc 闸这侧把新加的 `census.bare_line_feeds` 写成 `…_typo` ⇒ **唯一一条 `error TS2551`**（`_tsc_specs_slice3_tamper_r1.txt`），
改回 ⇒ `TSC_RC=0 / 0 错误行`，被改文件 `RESTORED byte_identical=True`；
`tsc` 那枚 `--noEmit -p` 两枚 config 也各自重跑过，仍 **0 错误行**。

## 5. 玻璃上的数（390×844，Chromium，runId `slice3base022320`，2026-10-15 02:23）

复跑一条命令（它自己带 BASELINE 腿，落 `_glass_ctl_<run>.log`）：

```
cd CityNexus && PYTHONIOENCODING=utf-8 D:/moodle/CityNexus/.venv/Scripts/python.exe \
  review/ord0496/glass_can_go_red_r1.py            # 玻璃闸 + 三枚反向对照
PYTHONIOENCODING=utf-8 D:/moodle/CityNexus/.venv/Scripts/python.exe \
  review/ord0496/slice3_gates_r1.py                # 把所有数从 git／文件／日志现读重打一遍
```

**这一节的数只从存档件读**（`reports/qoder-ord0496-calendar/{manifest.json,exported.ics}`），
第二枚脚本就是把这条规矩写成代码的：`GLASS_*` 每行都是拿存档字节另算，再与 manifest 里的字段并列打出来比。

| 尺 | 数 | 这一行钉住的是 |
|---|---|---|
| 玻璃闸本身 | BASELINE（未篡改）**rc=0 / 2 passed**；三枚控制各 **rc=1 / failed=1 passed=1**；`CONTROLS_RAN=3 CONTROLS_THAT_BIT=3`；被改文件 `restored=True` | 上一版这一节引的是 `slice3r1`，那趟的存档已被覆盖——现在引的这趟就是存档那枚文件的来路 |
| Chromium 真收下的文件 | `2879` 字节，sha256 前 16 位 `2d3eb7cea9c2456e`（与 manifest 里的 `agree=True`），`9` 枚 `BEGIN:VEVENT` / `9` 枚 `END:VEVENT` | 下载不是「屏幕自说」，是浏览器落的那枚文件；`exported.ics` 已存档，路径按仓库相对记 |
| 同一枚文件的独立语法量 | `88` 对 CRLF、**裸 LF 0**、非空物理行 `88`、**超过 75 octet 的行 0**、最长行**恰好 75**、折行续行 `0`、`DTSTART/DTEND/UID/DTSTAMP` 各 `9` | 这几条不是引用导出器自己的断言，是我拿存档字节另算的；断言也进了 spec（裸 LF 与非 75 上限各一条 `expect`），所以它下次红会喊 |
| 门与文件对账 | 头 `X-CityNexus-Ics-Events=9` == 文件里数出来的 `9`；`activities 9 = events 9 + no_clock 0 + no_stamp 0`（脚本打 `sums=True`） | 头里的算术在真布景上成立（不是只在 pytest 的合成行上成立） |
| 屏幕那两句是否词典答的 | `已下载 9 个日程，可在日历 App 里打开那个文件。` 与 `日历没能导出，所以没有下载任何东西。`——折掉占位符/数字后**都在词典里**（`IS_A_DICTIONARY_VALUE True×2`） | 句子来自词典而不是硬编码；导出句里的 `9` 来自字节（`countCalendarEvents(body)`），不是来自头 |
| 文件名 | `Tianjin · stay-aware weekend--d746ac1b-ca9f-451a-8366-b57296f3b549.ics` | RFC 5987 那半真到了玻璃上：中文/带空格的标题没被转写成第二个名字 |
| 无凭据那一腿 | 屏幕句同上第二句；**写盘 0 枚**；门 `401`；应答 `content-type` 不含 `text/calendar` | 拒绝不发日历字节；且屏幕上没有键名（`calendar.` 子串按事实量） |
| 按钮标签 | `导出日历`（zh-CN 词典答的，`button_label` 是 `innerText()` 读回来的） | 九枚键在玻璃上答的是句子 |
| 跨趟会不会变 | 三趟独立新库（`d27f4079…`／`0b30025f…`／`d746ac1b…`）**行程 id 不同 ⇒ UID 不同 ⇒ sha 不同**（`7fb59c4d…`→`2d3eb7ce…`），而**字节数 `2879` 与事件数 `9` 三趟全等**（这两条是每趟控制台 `[ord0496][glass] events=… bytes=…` 现读的，其余计数只在这一趟的存档上量过） | 导出器的规矩是「`DTSTAMP` 用行自己的 `updated_at`、不用请求的墙钟」（`calendar_export.py` 决定 2），所以「同一条行程导两次是同一串字节」这条**在门那侧**由 `test_two_exports_are_the_same_bytes_and_moving_the_rows_moment_moves_the_stamp`（测试文件 `:961`）钉住；跨趟换的是布景，不是导出器不确定 |

## 6. 这一片不证明的几件事（别按「就绪」读）

1. **不证明「没有可用时刻」那条腿在玻璃上成立**：这枚布景的 9 行活动全带偏移
   （`no_clock=0 no_stamp=0`），跳过并计数那两枚臂**只有门证**。想让它上玻璃，得先有一版带裸日期/无时区行的布景。
2. **不证明契约与生成客户端**：`contracts/openapi.yaml` 里这枚操作**没声明**（现读 `calendar.ics` 命中 0），
   源树那两枚读生成客户端的臂按 §3.6 挂着喊话。融合树的契约与源树差 **1488 行**，
   且这棵树没有 codegen 脚本 ⇒ 契约腿另开一刀，别把它算进本片。
3. **切片 3 的 abort 半条没开工**，而且它不是一枚门的事：源树 `abort_journey`（`main.py:3529`）要
   `journeys.aborted_at` / `abort_reason` 两枚列（源树 `db/schema.sql:139-140`）、
   `app/services.py::journey_live_view`（源树命中 2 处）、以及**每一枚行程应答**多带 `live_view`。
   融合树与融合基线的 `schema.sql` 里这三样**现读全 0 命中**。这棵树的建表只认 `schema.sql`（ORM 类不长表），
   所以 abort 是一片**带库面改动**的活，不塞进本片的提交线里。
4. **不证明 `vite build` / 真机 PWA**：这条分支上 `node_modules` 是只读 junction，构建会写盘，一次都没跑过。
5. **不证明「退出登录的人看得见为什么」**：无凭据那一腿现在落 `UNRECOGNISED`，句子是「日历没能导出」，
   而事实是「先登录」。源树没有凭据概念，所以它没有这句话。要补是第 10 枚键 + 一处分类改动，
   超出「移植」范围，**报给号令者定**，我不顺手扩面。

## 7. 全量套件这两趟样本，以及一枚我在源树上找到的仪器破口

同一枚解释器（`D:/moodle/CityNexus/.venv`）、各自新库、`-p no:cacheprovider`、`-q`；
数由 `review/ord0496/slice3_gates_r1.py` 现读日志，不由控制台手抄。

| 尺 | 本尖（切片 3）样本一 | 本尖样本二 | 上一尖（切片 1+2）两趟 |
|---|---|---|---|
| 尾行 | **156 failed / 2081 passed / 7 errors / 388.73s** | **155 / 2082 / 7 errors / 427.20s** | 155 / 2065 / 7 errors / 367.76s 与 155 / 2065 / 7 errors / 392.17s |
| `FAILED`+`ERROR` 行数 | 163 | 162 | 162、162 |
| 与尾行 `failed+errors` 是否相等 | **相等** | **相等** | 相等、相等 |

红名集合的对照（只认集合不认总数，理由与上一版一样：总数在这两棵树里主要由测试互相踩决定）：

- **同一尖两趟之间的差**：`SAME_TIP_SAMPLES_FLIPPED 1` ——
  `test_r87_first_live_city_discovery.py::test_r87_live_discovery_keeps_member_receipts_private_and_blocks_ungrounded_opening`
  样本一红、样本二绿；上一尖两趟都绿。⇒ 单枚样本内的翻转，不构成回归证据。
- **两棵树的红名并集都是 163 枚**，只差一枚：本尖独有 `r87…`（上面那枚翻转的），上一尖独有
  `test_r44_resilient_operator_brain.py::test_operator_brain_blocked_lineage_reuses_incident_then_resumes`
  （上一版记下的那枚 flake，本尖两趟**都绿**）。
- **`g3_xproc` 那枚要说清三件事**，别一句话说成「切片 3 带来的」：
  本尖两趟**都红**、上一尖样本二**也红**（4 趟里 3 红），而**基线树自己单跑 8 趟也红过 1 趟**；
  三处（基线树单跑红、本树单跑红、本树套件内红）**失败点逐位一致**：
  `tests/test_qoder_g3_xproc_http.py:401 → :195 in _wait_for_serving → :84 in _http →
  ConnectionRefusedError [WinError 10061]`，只有端口号不同。

那枚破口的形状（读了代码，不是猜的）：`_wait_for_serving` 的循环每圈先 `proc.poll()`、再拿
`_http("GET", port, HEALTH)` 探一次；而 `_http` 只把 `HTTPError` 当读数（docstring 自己写着
「4xx/5xx are readings, not exceptions to swallow」），**`URLError`（连接被拒）不在它吞的范围里，
循环里也没有 `try`**。子体是 `python -X utf8 worker.py <port>` 起的，父体在 `Popen` 返回后**立刻**探，
此时端口还没 bind ⇒ 第一圈就把 `URLError` 抛出测试，`READY_DEADLINE_S = 120` 那两条
（「子体先退了」「120 s 内没答 200」，两条都自报「仪器故障不是产品结论」）**根本轮不到说话**。
所以这枚门的红/绿实际是 Windows 进程启动时序的掷骰子，与它要证的跨进程收敛毫无关系。

**我没改它。** 一行就能补（循环里连 `URLError` 一起吞、或先等 `_listening_pid(port)` 再探），
但改别人的测试来让自己这趟的数变绿，正是该喊不该做的事——它同时污染号令者那一侧的套件读数，
所以这条作为**给包工头的报告项**写在这儿：`G3_XPROC_READINESS_POLL_SWALLOWS_NOTHING`。

本片那 17 枚 `test_qoder_ord0496_calendar_export.py` 的臂只在**本尖**存在（上一尖还没有这枚文件，
所以拿它做跨尖对照没有意义），本尖两趟里 **0 枚红**；门那侧另有 `import app.main` 的收集期闸与
`glass_can_go_red_r1.py` 的 BASELINE 腿各绿着。
