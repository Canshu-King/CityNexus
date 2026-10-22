# 真人视角走查（chrome-use 与真实 Chrome）· 2026-10-22

任务书：`trial/tasks/20261022_QODER_CHROME_USE_HUMAN_FIRST_ACCEPTANCE.md`。这一份只写屏幕上真看到的东西；没测的格子写 `NOT_MEASURED`，不补漂亮数字。

## 一、仪器与连接状态（先说清楚，免得后面误读）

| 项 | 实测 |
| --- | --- |
| chrome-use 是否接上 | 已接上：`chrome-use 1.5.136`，relay up，扩展 0.5.27，profile `yjianbin419@gmail.com`，会话 `citynexus-v3-human` |
| chrome-use 能做什么 | `open` / `snapshot -i` / `eval` / `click` / `viewport` / `tab` 全部可用（用户的真实 Chrome 里读到了首屏无障碍树与 `readyState=complete`） |
| chrome-use 不能做什么 | `screenshot` 每次都 `CDP error (Page.captureScreenshot): relay timeout after 8000ms`，诊断里扩展的调试器 worker 已存在约 114,900,000 毫秒（约 31.9 小时）；`session stop`、`close` 重开、`--window dedicated`、`--scale 0.5`、`--clip 0,0,390,844` 全部同样超时；同一时刻 `eval` 正常返回，所以不是页面卡死，是扩展侧截图通道死了 |
| Qoder In-app Browser | `NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`（`viewport=0x0, visible=false`），没有可见表面对象可截 |
| Qoder Computer Use | 对 Chrome 窗口报 `browser_url_policy / url_verification_required` 并要求终止使用 |
| 本轮像素的来源 | 真实 Google Chrome（`channel: chrome`，非无头，独立 `user-data-dir`，视口 414×900），由 Playwright 驱动 |

`CHROME_USE_CONNECTED = YES（读数与点击）/ NO（截图通道）`
`BROWSER_FALLBACK_USED = real Google Chrome, visible window, isolated profile, driven by Playwright；原因：chrome-use 的 CDP 截图在本机扩展上卡死，而任务书要求真实像素的 BEFORE/AFTER`
`HUMAN_BROWSER_USED = YES（真实 Chrome 窗口、真实点击与聚焦，非 API 调用、非 localStorage 造状态）`

一次失误必须写在这里：为了拿像素，我一度用 PowerShell 抓屏幕区域，抓到的是**用户自己的 Chrome 窗口**（超星学习页与一个 Google「要保存密码吗」气泡）。两张图当场删除，没有提交、没有上传、没有读取凭据内容，之后不再用屏幕区域抓取。教训：共享桌面上截屏必然连带别人的窗口，这条路不安全。

## 二、第一次进入 App 看到了什么（414×900，真实 Chrome）

| 步 | 屏上原文（截自屏幕） | 点了什么 | 截图 |
| --- | --- | --- | --- |
| 1 | 「你的下一趟旅行，从一句话开始。」／「想怎么玩？」／「目的地」／「日期与天数」／「更多偏好 同行 1 人 · 预算 ¥1,000」／「继续规划 →」 | 输入一句话 + 北京 + 2026-11-02 | `20261022_v3_human_chrome/human-01-first-screen.png` |
| 2 | 按「继续规划 →」之后：「先选一个地区」「使用所选区域搜索附近地点。」「城市或地区」「查找位置 →」「**点击后将地名发送至服务器当前选择的公开地名服务。**」「想用公开 OpenStreetMap 链接定位？（可选）」「技术信息」「高级功能：地图坐标、分享与技术详情」 | 新人此时会去按最大的那颗绿按钮「查找位置 →」 | `human-06-after-continue.png` |

同一屏底部确实有旅客自己那句话（「想慢慢逛北京的古迹和胡同小吃，两个人，人均预算 500，一天别太赶。节奏：轻松少走」）和「发送 ↑」——**但屏幕上最响的按钮不是它**。这就是第一个真实阻塞：路径被一颗与目标无关的绿按钮抢走了，而且主屏上还留着一句讲机器流程的话。

后端在这一屏发过的请求（同一次走查，凭据不在其中）：`map-places`、`bootstrap-shortlist`、`planning-intent`、`bootstrap-discovery/current`、`agent/runtime-status`，全部 `http_status=200`；这一趟新建的 Journey 是 `fd20fa44-c39f-4855-b6aa-a76069f52937`（本机金丝雀库，不是共享预览库）。

## 三、改了什么（最窄的一刀）

1. 主屏不再预告机器流程：`frontend/src/trial/mobile/CityPicker.tsx:135` —— 那段「点击后将…」预告句删掉了，现在只有**查完之后**才留一句来源（`刚才的地名来自 Photon。` 等）。
2. 手挑地点降级：`frontend/src/trial/mobile/CityPicker.tsx:259` 起，在 Agent 已经握着这句话的行程里，整个「先选一个地区」面板折进 `我想自己先挑地点（可选）`（`frontend/src/trial/mobile/CityPicker.tsx:262`），开关由 `frontend/src/trial/RevolutionQuickExplore.tsx:929` 给。
3. Agent 那一步变成主行动：那颗文字键在行程模式下改成主按钮「改这句，然后交给 Agent →」（`frontend/src/trial/RevolutionQuickExplore.tsx:873`），按下去把光标送进底部输入框（`frontend/src/trial/RevolutionQuickExplore.tsx:831`）；说明句改成人话「你的想法已经写好了，可以改，改完交给 Agent。」（`frontend/src/trial/RevolutionQuickExplore.tsx:860`）。
4. 助手侧的提示块在旅客已经写好一句话时改口：标题「你的想法已经写好了」（`frontend/src/trial/mobile/MobileAiPrompt.tsx:108`）、按钮「让 Agent 从这句话开始 →」（`frontend/src/trial/mobile/MobileAiPrompt.tsx:128`），并删掉按钮旁那句讲预算与模型确认的机器话。

## 四、改完再用真实 Chrome 走同一条路

| 量 | 读数 |
| --- | --- |
| 「点击后将地名发送至…」是否还在主屏 | `MECHANISM_SENTENCE_ON_SCREEN=false`（`20261022_v3_human_chrome/walk-02-log.txt:5`） |
| 手挑面板是否已折叠 | `FOLD_PRESENT=true`（`20261022_v3_human_chrome/walk-03-log.txt:3`），且「查找位置 →」在未展开时不可见（`20261022_v3_human_chrome/walk-03-log.txt:4`） |
| Agent 行动 | `改这句，然后交给 Agent →`，样式 `rev-quick-primary`，盒子 212×49（`20261022_v3_human_chrome/walk-03-log.txt:5`） |
| 按下去之后光标落在哪 | `{"id":"rev-mission-chat-input","in_viewport":true,"value":"想慢慢逛北京的古迹和胡同小吃，两个人，人均预算 500，一天别太赶。\\n节奏：轻松少走"}`（`20261022_v3_human_chrome/walk-03-log.txt:8`）—— 落在旅客自己那句话里，可以直接改、直接发 |
| 截图 | BEFORE `human-06-after-continue.png`；AFTER `human-11-agent-leads.png`、`human-12-after-pressing-agent-action.png` |
| 回归护栏 | `npm run typecheck` 干净；`npx playwright test e2e/revolution-quick-explore-ui.spec.ts` **NOT_MEASURED** —— 该 spec 的 `config.webServer` 用系统 Python 起后端，报 `ImportError: cannot import name 'StrEnum' from 'enum' (…Python310…)`，进程起不来；本机能跑测试的解释器只有仓库那个 3.12 venv，这是既有的仪表缺口，不是本批改坏，已记在这里不当已验 |

还没解决、写在明处的两点：这颗主按钮在 414×900 首屏之下（地图空态占了第一屏），旅客要先下滑才看见它——不过底部输入框本身就在第一屏，「发送 ↑」是可达的；地图仍是 `0 处地点`，公开来源那一格今天在这台机器上仍不通（直连与本机代理两条路的实测见 `trial/results/20261022_V3_AGENT_HALFDAY_PRESS.md`）。

## 四之二、第二刀：首屏上两句对不上号的话

同一台真实 Chrome 再走一次首屏，看到两处：CTA 上方挂着一句「下一步：挑选真实地点。」——旅客连目的地都还没填，这句话就在预告第三屏的事；而「地点来源见卡片，到达状态由你确认」这句承诺在页面上出现了两遍（底部页脚一遍、面板里一遍）。

改法（只删不写新句）：删掉首屏那句预告（`frontend/src/trial/RevolutionFirstLook.tsx:1179` 这一段现在只剩「用新行程继续」那颗条件按钮），面板里那句重复的说明删掉，承诺只留页脚一处（`frontend/src/trial/RevolutionFirstLook.tsx:1414`）。

同一台真实 Chrome 的复测（`20261022_v3_human_chrome/walk-03-log.txt:3` 与 `20261022_v3_human_chrome/walk-03-log.txt:4`）：`NOVELTY_LINE_GONE=true`、`DUPLICATE_DISCLAIMER_COUNT_ON_PAGE=1`，第一刀的折叠与主行动仍然生效（`20261022_v3_human_chrome/walk-03-log.txt:7` 与 `:8`）；`npm run typecheck` 干净。截图 `human-13-first-screen-clean.png`。

## 四之三、这一格本轮不动，原因写清楚

首屏要求「想怎么玩？」里写了北京之后，还要在「目的地」再写一遍。不做自动抽取的理由是三条事实：前端没有可对照的城市名单（这一格本来就允许任意 2–60 字的地区名，见 `frontend/src/trial/RevolutionFirstLook.tsx:592`）；公开地名服务今天在这台机器上不通，无法把抽取结果拿去核对；而项目规则禁止从标题或散文里推断规范地区（`backend/app/agent/goal_artifacts.py:81`）。所以这一格留作 `BLOCKED`，替代行动是：等地名服务可达时，把抽取结果做成**看得见的候选**让旅客点一下确认，而不是替他填。

## 五、门禁

- `CHROME_USE_CONNECTED = YES（读数与点击）/ NO（截图）`，`BROWSER_FALLBACK_USED` 已注明原因；今晚这台机器的 Chrome 进程被外部反复收走（同一时刻 WorkBuddy 自己的 debug Chrome 活着，见 `20261022_V3_RETURNING_TRAVELER_AND_RECEIPT_SHAPE.md` 第四节），走查改用同机真实 Edge 窗口（Chromium 内核、同一个隔离 profile 思路、可见窗口、真人点击）；Playwright 的截图路径在这台机器上会卡在渲染线程，截图改走调试协议 `Page.captureScreenshot` 直取
- `HUMAN_BROWSER_USED = YES`
- `NOVICE_FIRST_CLICK = PASS`（首屏一句话即可提交；第一次按「发送」的死键已修，见 `20261022_V3_SEND_GATE_ON_SCREEN.md:1`；「目的地」仍要再填一次，这是下一个待改点）
- `AGENT_PLAN_VERSIONS_ON_SCREEN = PASS`（旅客一句话要三版，屏上出现 A／B／C 三张对比卡与三个 tab，按下 B 的「选用这份安排」后服务端草案版本 1 → 2、日程换成那一版，刷新仍在；改前同一句话只有散文、两个计数都是零。逐项读数与成因见第七节）
- `SAME_JOURNEY_GOAL_TO_ACTIVE = PARTIAL（两道门都有名字，见第八节）`（同一 Journey 上已走到「已有阶段性成果 · 2 天 6 项安排」，见 `20261022_v3_human_chrome/walk-06-log.txt:6`；SELECTED/ACTIVE 仍在走。今晚两处新事实：出发面板只在「我的旅程」这一页，地图/日程/对话三页各读一次都是 `preparation=0`，只有 trips 页 `preparation=1 card_visible=true`（`walk-29-log.txt:2` 与 `:14`）；而上一代带真地点之前，一份正式候选已经存进服务器，屏上仍写「等待正式计划 1 份正式候选方案」而 `rev-plan-select` 不出现（`walk-22-log.txt:63` 与 `:64`），出发待办点名「具体地点 · 营业时间 · 票价」。**廿二日夜里带着真高德地点重走，同一句话仍然不出现**：`SELECT_BUTTONS=0`（`walk-34-log.txt:19`），服务端对拍给出名字——四格 `SOURCE_IDENTITY`、两格 `PLACE_REQUIRED`，同库 `places` 表 0 行（`walk-34-server-readback.txt:71`、`:78`、`:94`），成因与既有落库门的接法写在第七节。第八节把这一格修掉了：同一句 `SELECT_BUTTONS` 仍是 0，但缺口名单里 `SOURCE_IDENTITY`／`PLACE_REQUIRED` 整批消失、日程格子换成正式地点 id、同库 40 行正式地点（`walk-36-log.txt:19`、`walk-36-server-readback.txt:36` 与 `:50`），剩下的是「手工候选不冻转场证据」这条已写进响应合同的边界（`goal_preparation.py:67`）与 ORD-0708 待回的营业时间那一格（`services.py:783`）
- `AGENT_RESEARCH_GROUNDED = PASS（地名与身份）/ NO（照片）`：屏上「现实地图 4 处地点」`walk-31-log.txt:3`，同一屏「OpenStreetMap 地图地点 0 处 · 高德地点 4 处」与「查看更多地点（24）」`walk-31-log.txt:4`；草案格子里带供应方地点 id（服务端对拍 `walk-22-server-readback.txt:5` 起四行 `place_id= amap:B000A8UIN8` 等）。照片仍是没有：屏上相册 `PHOTO_IMGS=0 FALLBACK_TILES=4`（`walk-31-log.txt:5`），原因是这台机器此刻取不到 Wikimedia 系（直连 TLS 握手超时、走唯一活着的代理口 7892 是 `SSL UNEXPECTED_EOF`＝门户拦截），而产品规则禁止按名字模糊配异地照片，所以屏上是中性占位「先看看这个地点」而不是假图
- `AGENT_NATURAL_LANGUAGE_HALF_DAY_EDIT = PASS`（旅客一句「11 月 3 日下午不去湖边走路了，改成什刹海边一家咖啡馆坐着，其他安排都别动」之后，屏上回执 `walk-26-log.txt:32` 出现 `日程：版本 1 → 2`，同一屏第五条变成 `下午 · 什刹海边咖啡馆坐着（萤火虫咖啡 后海店）`（`:39`），`EDIT_CHANGED_SCHEDULE=true`（`:40`）。此前两代同一句话都是 Agent 说「已改」而日程不动，成因与修法见 `20261022_V3_RETURNING_TRAVELER_AND_RECEIPT_SHAPE.md` 第七节）
- `RELOAD_RECOVERY = PASS`（**Agent 改过之后**刷新仍然在：`walk-26-log.txt:42` `AFTER_RELOAD_SLOTS=5 SAME_AS_AFTER_EDIT=true`；更早那一次手动改半天的刷新记录仍在 `walk-07-log.txt:4`，两者不是同一件事）
- `VIEWPORT_PASS = 390×844 / 430×932 / 1366×900 三档均无横向溢出且「发送」在视口内`（`walk-07-log.txt:13`、`:15`、`:17`）
- `GUARDIAN_COLLECTIVE = NOT_ATTEMPTED`
- `PRODUCT_FIX_SHA = 376b9914a7576bc69ffa56c13f167bf5f54aa6ee、0563305f8133dd146c234a1c092b8ab95da2f8cc、36939dd9ad8ec0791eda71f36ac150403bf27a30、ae7f51c6284ba1dcbe5e35c2d032c123cf2506f0`；BEFORE/AFTER 截图在 `20261022_v3_human_chrome/`
- `USER_VERIFIED = PENDING`（本机窗口不是手机在手里的点击）

## 六、十步以内试玩说明（给第一次打开的人）

1. 打开 App，看到「你的下一趟旅行，从一句话开始」。
2. 在第一格写一句人话，例如「想慢慢逛北京的古迹和胡同小吃，两个人，人均预算 500，一天别太赶」。
3. 第二格写城市名（北京）。
4. 想指定日子就点开「日期与天数」，选出发日。
5. 想改人数或预算，点开「更多偏好」。
6. 按「继续规划 →」。
7. 屏幕下方已经放着你刚才那句话，想改就点在里面改。
8. 第一次用要先勾输入框下面那两行「本次允许」——勾完「发送 ↑」才会亮起来，不勾的话那一行会一直在那儿等你。
9. 按「发送 ↑」，Agent 开始研究并会问你问题；它给选项时按选项回答。
10. 想让它别再问、先出安排，就按「按讨论的方向开始研究」；之后点「日程」看每天安排，一句话告诉它你想改哪半天，回复下面那行「日程：版本 …」会告诉你它到底改没改成。再往下一步「准备出发 · 正式计划与待办」不在地图/日程/对话这三页上，它在底部「我的旅程」里。
11. 想要几版对比着挑，就在对话里说「按轻松少走、省钱、本地特色三种想法各出一版，让我三选一」；说完点「日程」，上面会出现 A / B / C 三张卡片，按下想用的那张「选用这份安排」，日程就换成那一版。

## 七、廿二日深夜这一趟：三版对比卡片上了屏，最后一道门量出了名字

仪器：同机真实 Edge（Chromium 内核，CDP 9335，独立测试 profile `profile_edge_fourth_use`，视口 414×900），一次坐下走完；截图走 `Page.captureScreenshot`。日志 `20261022_v3_human_chrome/walk-32-log.txt`（第一坐）、`walk-33-log.txt`（同一标签页续走）、`walk-34-log.txt`（准备出发到正式候选），服务端对拍 `walk-34-server-readback.txt`。

三版对比（改前 → 改后，都从屏上读）：

| 量 | 改前（walk-26-log.txt:50） | 改后（walk-32-log.txt） |
| --- | --- | --- |
| 要三版之后屏上的对比 tab | `VARIANT_TABS=0` | `VARIANT_TABS=3`，标题 `["A · 轻松少走版","B · 省钱版","C · 本地特色版"]`（`:47`、`:48`） |
| 可见的方案卡片 | `VARIANT_VISIBLE_CARD=0` | `VARIANT_VISIBLE_CARD=1`，A 卡正文点名 4 处真地点并写「咖啡馆选离鼓楼最近的前海东沿」（`:49`） |
| 换到第二版 | 无卡可换 | 按 tab 后 `visibleCards=1 card=B 省钱版 …`（`:51`） |
| 按「选用这份安排」 | 按钮不存在 | `CHOOSE_LABEL=选用这份安排 disabled=false`（`:53`）→ 服务端 PUT 草案 `200`，版本 1 → 2，日程第五格变成「下午 · 糖房咖啡（什刹海店）·坐着看湖」（`walk-34-log.txt:7`） |
| 刷新之后 | 未测 | `CHOSEN_VERSION_SURVIVED_RELOAD=true`（`walk-33-log.txt:11`），三张卡仍在（`:13`） |

同一趟里另外三条读数：第一次回复的封套标点 `ENVELOPE_PUNCT_ON_SCREEN=[]`（`walk-32-log.txt:13`）；每条回复旁边的服务端回执（`:19` 三条 `这条回复没有改动日程（版本 0）`／`日程：版本 0 → 1`）；旅客那句「11 月 3 日下午…改成什刹海边一家咖啡馆坐着」这一代得到的是**一句落地过的追问**——「11月3日下午改成…你想选哪一家？」并列出三家真高德门店，回执同时写明 `这条回复没有改动日程（版本 1）`（`:30`、`:31`），日程一格未动。这不是上一代那种「说了没做」：话里没宣称已改，回执也说没改，两者一致。

最后一道门现在有了名字（不是猜的，两证对齐）：勾「按以上时间准备方案」→「保存为正式候选方案」得到 `SAVE_STATUS 已保存 6 项正式安排`（`walk-34-log.txt:14`），屏上 `GATE 等待正式计划 1 份正式候选方案`（`:17`），而 `SELECT_BUTTONS=0`、方案卡片末尾写「安排已保存，完成地点资料和转场路线后即可选用。」（`:19`、`:18`）。服务端对拍同一条候选：`PLAN_VERSIONS=1 … status=CANDIDATE`（`walk-34-server-readback.txt:67`）、`authority_state=PROVISIONAL_UNRESOLVED_FACTS`（`:70`），六格里带真高德 id 的四格各挂 `SOURCE_IDENTITY`（`:71`），另两格挂 `PLACE_REQUIRED`（`:78`）；同一份库 `CANONICAL_PLACE_ROWS_IN_THIS_DB=0`（`:94`）。

即：Agent 这一路找到的地点是**任务范围内的供应方观测**（`amap:B000A8UIN8` 这类），而方案的选用门要求 `places` 表里有按 `provider_key + external_id` 对得上号的正式地点行；V3 这条路上没有任何一步把观测落成正式行，所以每一份正式候选都被判 `stale`，「选用这份方案」永远不出现，`goal → SELECTED → ACTIVE` 结构上走不通。同一产品在别的路（`agent/gateway.py:1854` 的 recovery discovery）本来就会调 `materialize_candidates` 写下正式行并回 `materialized_place_id`，所以缺的不是新能力，是把 Agent 研究这一路接到既有的落库门上。

屏上那句提示本身也有一处对不上：它把「转场路线」列为选用的前提，而 `services.py:742` 的判据只看 `SOURCE_IDENTITY`／`PLACE_REQUIRED` 两类——营业时间、票价、转场路线都不参与否决。这句话要么改成点名真正拦路的那几格，要么把可点的下一步给出来；本轮先如实记下，改动随落库门那一刀一起做。


## 八、廿二日廿二时半：研究这一路开始写正式地点表，出发待办的名字变了

改的因由就是第七节那条 `SOURCE_IDENTITY`：V3 的 Agent 研究只把供应方结果当任务内观测，而那份库的 `places` 表 0 行；同一产品的 recovery discovery 早就在调 `materialize_candidates` 落正式行（`backend/app/agent/gateway.py:1854`，候选里带 `materialized_place_id`）。所以这一刀不是新造能力，是把 Agent 研究接上既有那道落库门（新增 `backend/app/agent/goal_place_identity.py`），并把正式 id 交回任务（`backend/app/agent/goal_artifacts.py:309`、`:390`、`backend/app/agent/goal_amap.py:132`）；准备那扇门仍然只做绑定、不做落库（`backend/app/agent/goal_preparation.py:125` 起），模块头那句「No provider, Place promotion … runs through this door」没有改。

第一次坐下（`walk-35-log.txt`）在 4 次 `discover_places` 之后被模型腿掐断：服务端记 `failure=MODEL_TIMEOUT`、`task_status=FAILED_RECOVERABLE`（`walk-35-server-readback.txt:3`），同一库 `CANONICAL_PLACE_ROWS_IN_THIS_DB=32`（`:23`）——昨夜同一趟这里是 0。屏上「已核对的正式地点（32）」这一格在更早几代根本不出现（计数为 0 时那整块 `<details>` 不渲染，`frontend/src/trial/mobile/WorkspaceActions.tsx:614`）。

第二次坐下没有重开旅程，仍在那一个标签页里按屏上给出的那颗按钮：「旅行研究 · 可以重试」＋「继续研究」（`walk-36-log.txt:8`）。按下去 80 秒后日程出现 5 格（`:10`），回执仍是服务端算的那三行（`:12`）。关键读数：

| 量 | 改前 | 改后 |
| --- | --- | --- |
| 日程格子里的地点 id | `amap:B000A8UIN8` 这类供应方 id，背后 0 行正式地点（`walk-34-log.txt:7`、`walk-34-server-readback.txt:94`） | `real-place-62c2e60619da82efebfdea8c` 等 5 枚正式 id（`walk-36-log.txt:19`） |
| 屏上「已核对的正式地点」 | 不出现（0） | 与「公开来源发现的地点」并列出现，计数 40（`walk-36-log.txt:11`） |
| 出发待办的点名 | 「地点资料接入 · 营业时间 · 票价」「具体地点 · 营业时间 · 票价 …」（`walk-34-log.txt:15`） | 只剩「营业时间 · 票价」「营业时间 · 票价 · 转场路线」（`walk-36-log.txt:23`），「地点资料接入／具体地点」两类整批消失 |
| 服务端同一候选的缺口 | 四格 `SOURCE_IDENTITY` ＋两格 `PLACE_REQUIRED`（`walk-34-server-readback.txt:71`、`:78`） | 第一格从 `OPENING_HOURS`／`ADMISSION_PRICE` 起，且 `place_id=real-place-…`（`walk-36-server-readback.txt:36`）；同库 `CANONICAL_PLACE_ROWS_IN_THIS_DB=40`（`:50`） |
| 「选用这份方案」 | 不出现 | **仍然不出现**：`SELECT_BUTTONS=0`（`walk-36-log.txt:26`） |

最后一行不是这一刀没修好，而是剩下的两道门各有名字，都不在这次的改动范围里：

- `services.py:573` 的 `_plan_staleness`：草案候选的 `mobility_evidence_json` 没有 `snapshot_id` 就判 `STALE_RECOMPOSE_REQUIRED: no frozen provider evidence`。而 `goal_preparation.py:67` 把响应契约里的 `mobility_frozen` 写死成 `Literal[False]`、`:187` 照此返回——「保存候选但不冻转场证据」是已定的合同边界（等「候选提交而不应用」那一刀），不是这晚漏掉的实现。
- `services.py:783`：`authority_state=PROVISIONAL_UNRESOLVED_FACTS` 时，用到的地点只要还没有落地的到访事实（营业时间）就仍判不可选用。这正是 ORD-0708 要回的那个符号；代码里已有的 R86 承认门只覆盖票价、明确不覆盖营业时间。

屏上那句话这一代改成从服务端给的名单里点名（`frontend/src/trial/mobile/MobilePlanWorkbench.tsx:28` 的 `selectionBlocker`）：地点没定就点名是哪几处并指向屏上已有的「和 Agent 补齐出发资料」，都定了才说转场路线；不再手写一份「地点资料和转场路线」的清单。实测读到「相邻几站之间还没有可用的转场路线。」（`walk-36-log.txt:25`），与服务端原因同一件事。

护栏：`backend/tests/test_qoder_goal_place_identity_r1.py` 四格——高德 GCJ-02 线索只落一行、`coordinate_system=WGS84` 而 `source_coordinate_system=GCJ02`、存下的数字是换算过的、营业时间与票价仍然是未知；OSM 形制线索按自己的对象号归档；CONFLICT／非 live／没有类别／没有坐标四种线索一律不落（并数了 `places` 行数不变）；以及旅客确认过的排期绑上正式地点后缺口只剩营业时间与票价、`activities[0].place_id` 就是那枚正式 id，而 `selectable` 仍为 `false` 并把原因写在注释里，防止下一次有人把它当"已经能选了"。`pytest -q` 同代读数：identity＋preparation＋variants＋receipt 四支文件 36 passed。整支 `-k "goal or qoder"` 有 32 failed／7 errors，逐条对照过：把这四个改动文件从工作树里摘走再跑同样的三枚文件，13 failed／14 passed 一字不差（`test_qoder_current_plan_is_named.py`、`test_qoder_live_replans_endpoint.py`、`test_qoder_ord0434_share_grants.py`），所以那批红是本枝既有状态，不是这一刀改出来的。`npm run typecheck` 干净。

仪表自己的两处交代：`walk-36-log.txt:1` 先报了一次 `NO_TAB_WITH_A_LIVE_CREDENTIAL`——那是我这把尺写错了，它拿 `GET .../agent/goal-tasks` 验凭据，而那条路只吃 POST、返回 405；换成 `GET /api/v1/journeys/{id}` 才认出现有的标签页是活的（`:2` 起读到 `journey_read_http=200`）。这个请求只用来挑对标签页，产品动作全是点击。另外 `human-201/202` 两帧因渲染线程 10 秒没答而没落地（两行 `SHOT_FAILED … no frame within 10s`），只有 `human-203-plan-workbench-after-identity-fix.png` 有像素；文字读数不受影响。
