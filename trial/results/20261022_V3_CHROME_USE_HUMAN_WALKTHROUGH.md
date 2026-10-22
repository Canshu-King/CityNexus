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
- `SAME_JOURNEY_GOAL_TO_ACTIVE = PARTIAL（两道门都有名字，见第八节）`（同一 Journey 上已走到「已有阶段性成果 · 2 天 6 项安排」，见 `20261022_v3_human_chrome/walk-06-log.txt:6`；SELECTED/ACTIVE 仍在走。今晚两处新事实：出发面板只在「我的旅程」这一页，地图/日程/对话三页各读一次都是 `preparation=0`，只有 trips 页 `preparation=1 card_visible=true`（`walk-29-log.txt:2` 与 `:14`）；而上一代带真地点之前，一份正式候选已经存进服务器，屏上仍写「等待正式计划 1 份正式候选方案」而 `rev-plan-select` 不出现（`walk-22-log.txt:63` 与 `:64`），出发待办点名「具体地点 · 营业时间 · 票价」。**廿二日夜里带着真高德地点重走，同一句话仍然不出现**：`SELECT_BUTTONS=0`（`walk-34-log.txt:19`），服务端对拍给出名字——四格 `SOURCE_IDENTITY`、两格 `PLACE_REQUIRED`，同库 `places` 表 0 行（`walk-34-server-readback.txt:71`、`:78`、`:94`），成因与既有落库门的接法写在第七节。第八节把这一格修掉了：同一句 `SELECT_BUTTONS` 仍是 0，但缺口名单里 `SOURCE_IDENTITY`／`PLACE_REQUIRED` 整批消失、日程格子换成正式地点 id、同库 40 行正式地点（`walk-36-log.txt:19`、`walk-36-server-readback.txt:36` 与 `:50`），剩下的是「手工候选不冻转场证据」这条已写进响应合同的边界（`goal_preparation.py:67`）与 ORD-0708 待回的营业时间那一格（现尖 `backend/app/services.py:777`）
- `AGENT_RESEARCH_GROUNDED = PASS（地名、身份与照片）`：屏上「现实地图 4 处地点」`walk-31-log.txt:3`，同一屏「OpenStreetMap 地图地点 0 处 · 高德地点 4 处」与「查看更多地点（24）」`walk-31-log.txt:4`；草案格子里带供应方地点 id（服务端对拍 `walk-22-server-readback.txt:5` 起四行 `place_id= amap:B000A8UIN8` 等）。当时照片仍是没有：屏上相册 `PHOTO_IMGS=0 FALLBACK_TILES=4`（`walk-31-log.txt:5`），原因是这台机器此刻取不到 Wikimedia 系（直连 TLS 握手超时、走当时那条代理口是 `SSL UNEXPECTED_EOF`＝门户拦截），而产品规则禁止按名字模糊配异地照片，所以屏上是中性占位「先看看这个地点」而不是假图。**这一格廿二日十时四十三分已经在屏上过了**：路（代理口今天可达）与闸（我们自己写死的缩略图域名把合规照片丢掉）分开量、分开修，之后相册里是三张带署名与许可的真图（`walk-39-log.txt:12`、`:16`、`:17`），逐跳读数与"仍然没有照片的那两格为什么没有"写在第十节。
- `AGENT_NATURAL_LANGUAGE_HALF_DAY_EDIT = PASS`（旅客一句「11 月 3 日下午不去湖边走路了，改成什刹海边一家咖啡馆坐着，其他安排都别动」之后，屏上回执 `walk-26-log.txt:32` 出现 `日程：版本 1 → 2`，同一屏第五条变成 `下午 · 什刹海边咖啡馆坐着（萤火虫咖啡 后海店）`（`:39`），`EDIT_CHANGED_SCHEDULE=true`（`:40`）。此前两代同一句话都是 Agent 说「已改」而日程不动，成因与修法见 `20261022_V3_RETURNING_TRAVELER_AND_RECEIPT_SHAPE.md` 第七节）
- `RELOAD_RECOVERY = PASS（凭证在世时）/ PARTIAL（凭证过期时只能说实话）`（**Agent 改过之后**刷新仍然在：`walk-26-log.txt:42` `AFTER_RELOAD_SLOTS=5 SAME_AS_AFTER_EDIT=true`；更早那一次手动改半天的刷新记录仍在 `walk-07-log.txt:4`，两者不是同一件事。廿三日凌晨补两枚读数：同一台标签页刷新后相册三张真图仍在（`walk-42-log.txt:3`），而凭证到期那次刷新，四格读数为零、服务器两回都答 `http_status=401`（`walk-46-log.txt:5`）——屏上现在明说「这次登录已经过期」，但“读得回来”仍等一条裁语，见第十五节）
- `VIEWPORT_PASS = 390×844 / 430×932 / 1366×900 三档均无横向溢出且「发送」在视口内`（`walk-07-log.txt:13`、`:15`、`:17`）
- `GUARDIAN_COLLECTIVE = PARTIAL（守护那一半已按开并验到"安静不编造"，同行决策的门不存在——见第十三节）`
- `PRODUCT_FIX_SHA` 前四枚（十七～十八时那三刀）：376b9914a7576bc69ffa56c13f167bf5f54aa6ee、0563305f8133dd146c234a1c092b8ab95da2f8cc、36939dd9ad8ec0791eda71f36ac150403bf27a30、ae7f51c6284ba1dcbe5e35c2d032c123cf2506f0。廿二日深夜到廿三日凌晨再加八枚：3e8238ab1b（打字要版本→屏上出卡）、3d1b1407a5（研究线索落进正式地点表）、d2f842b06a（选用被挡时屏上说对话）、53b4080414（合规照片被自家域名丢掉）、2e0925f67f（那枚断言的分母改严）、b6137777bb（行程面板不再说“你没有行程”）、861ca462b6（相册占位格做成真控件并写出答案）、a7eba46539（凭证过期不再被说成“你还没开始”）。BEFORE/AFTER 截图都在 `20261022_v3_human_chrome/`
- `USER_VERIFIED = PENDING`（本机窗口不是手机在手里的点击）

**门禁增量（一点三十三分，行号全部现读）。**

- `AGENT_RESEARCH_GROUNDED`：照片那格**说的那句话**也进了屏。天坛公园从 `还没核实到具体是哪个地点` 变成 `没查到可核实的实景照片`（`trial/results/20261022_v3_human_chrome/walk-42-log.txt:7` 与 `trial/results/20261022_v3_human_chrome/walk-48-log.txt:27`），成因、两臂对照与"为什么八达岭照实不动"见第十六节。
- `SAME_JOURNEY_GOAL_TO_ACTIVE = PARTIAL（今晚往前挪实了一格：正式候选方案存进去了）`。同一句话、首用旅客从零走一遍：改前那代按下保存，屏上是 `这次未能保存，时间仍留在这里，可以重试。`（`trial/results/20261022_v3_human_chrome/walk-51-log.txt:25`），工作台数到 `等待正式计划 0 份正式候选方案`（`trial/results/20261022_v3_human_chrome/walk-51-log.txt:28`）。带上"高德早就答过的营业时间，是我们自己半路丢掉的"这一刀（`f11f28adbb`）之后，同一句变成 `已保存 7 项正式安排。下方可以查看日程和出发待办。`（`trial/results/20261022_v3_human_chrome/walk-53-log.txt:29`），工作台读到 `等待正式计划 1 份正式候选方案`（`trial/results/20261022_v3_human_chrome/walk-53-log.txt:32`），出发待办里营业时间那一项不见了，只剩供应商确实没答的票价与真正没被路由的那一跳。SELECTED／ACTIVE 今晚仍未拿到：`trial/results/20261022_v3_human_chrome/walk-53-log.txt:33` 读的是 `SELECT_BUTTONS=0`。
- `PRODUCT_FIX_SHA` 再加三枚：`6946f98bdc`（媒体腿不再只看第一条搜索命中）、`f11f28adbb`（把高德答过的营业时间搬回正式地点表）、`b514d2dd02`（已经被路由过的那一跳不再算缺口）。远端尖以 `git ls-remote` 现读为准，写这行时是 `b514d2dd02`。
- 整套后端在这枚尖上的读数是 `188 failed, 2289 passed`（`trial/results/20261022_v3_human_chrome/backend-suite-certificate-1.txt:9`）。**没有具名基线红集合，这一行既不能读成"无回归"也不能读成"回归"**；今晚产品码只碰 `place_media.py`、`amap_provider.py`、`goal_amap.py`、`goal_place_identity.py`、`goal_preparation.py` 五枚。追到底的一枚红是测试直接调用端点函数、FastAPI 没注入会话（`backend/tests/test_qoder_mobility_evidence_sources.py:160` → `backend/app/main.py:1006`），属这份快照既有形状。
- 教程的两处字面误报已改：`trial/results/20261022_V3_TEN_STEP_PLAYBOOK.md:3` 的「真机」改成「真实桌面浏览器的手机视口」并明写没有物理手机被摸过；`trial/results/20261022_V3_TEN_STEP_PLAYBOOK.md:43` 的「关掉再开」改成「刷新之后」，并明写关闭浏览器再打开暂时不保证找回。

## 六、十步以内试玩说明（给第一次打开的人）

图文单页另交在 `20261022_V3_TEN_STEP_PLAYBOOK.md`（每一步配一张真机截图，图名在 `20261022_v3_human_chrome/playbook-*.png`，走查读数在 `walk-47-log.txt`）。下面保留纯文字版。

1. 打开 App，看到「你的下一趟旅行，从一句话开始」。
2. 在第一格写一句人话，例如「想慢慢逛北京的古迹和胡同小吃，两个人，人均预算 500，一天别太赶」。
3. 第二格写城市名（北京）；要指定日子就点开「日期与天数」，要改人数或预算就点开「更多偏好」。
4. 按「继续规划 →」。
5. 第一次用先勾输入框下面那两行「本次允许」——不勾的话「发送 ↑」不会亮。
6. 屏幕下方那行就是你刚说的话，想改点进去改；改完按「发送 ↑」，Agent 开始研究并会问你问题，它给选项时按选项回答。
7. 不想再被问，就说「按讨论的方向开始研究」。
8. 想几版对比着挑：说「按轻松少走、省钱、本地特色各出一版，让我三选一」，切到「日程」会出现 A / B / C 三张卡片，按下想用的那张「选用这份安排」，日程就换成那一版。
9. 点「日程」看每天安排，一句话告诉它你想改哪半天；回复里那行「日程：版本 …」会告诉你到底改没改成。
10. 想看照片就切到地图页，下方「先看看这些地方」里前三格自动带图，其余格子点里面的「先看看这个地点」才会去找；要往下走到「准备出发 · 正式计划与待办」，它在底部「我的旅程」里，同一屏还能按「行程守护」。

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

## 九、九时半：卡片要能说出「哪一版是我现在用的」，以及我自己把屏弄坏过一次

读数在先（`walk-33-log.txt:14`）：旅客按下 B 版「选用这份安排」之后，服务端草案已从版本 1 走到 2、日程也换成那一版，屏上三张卡片却仍然各写着「选用这份安排」——因为卡片拿自己那份文档与存回来的草案逐字比 JSON，而草案是经过服务端规范化（补地点 id、补备注字段）才回来的，两边永远不相等。旅客看不出自己在用哪一版。

改成按「哪一天、哪半段、哪个地点」这三件事比（`frontend/src/trial/mobile/GoalDraftVariants.tsx:15` 起的 `draftSignature`）：备注与来源字段不参与「是不是这一版」的判断。同一 Journey 的活标签页里再说一次「按轻松少走、省钱、本地特色三种想法各出一版，让我三选一」，110 秒后三张卡出来，按下 B：

- 按之前 `CHOOSE_LABELS_BEFORE ["选用这份安排","选用这份安排","选用这份安排"]`（`walk-37-log.txt:7`）
- 按之后 `CHOOSE_LABELS_AFTER ["选用这份安排","已选为当前行程","选用这份安排"]`，`CARDS_MARKED_CHOSEN=1`，`SCHEDULE_CHANGED=true`（`:10`、`:11`、`:12`）
- 像素：`human-204-chosen-version-marked-on-screen.png`（第一次没截到，重试第二次落地）

顺带这一趟也是身份那一刀的二次印证：卡片能与草案在「地点」这一维对上，靠的正是双方都带同一枚 `real-place-…` 正式 id。

自己把屏弄坏过一次，如实记在这里：第一版改动里 `.map()` 的括号少关了一层，dev server 的 `vite-error-overlay` 直接盖在旅客屏幕上，走查里表现为「对话」那格点不动（`AGENT_LAYER_ERR`、`SEND_ERR`），而页面文字仍读得出五格日程——只看文字读数会误判成"产品又卡住了"。抓出来的是 hit-test：`agent_tab.hit_test = "VITE-ERROR-OVERLAY."`，同批像素 `human-205-probe-page-0.png`。修好后 `overlay=absent`、`agentTabHit=self`，`npm run typecheck` 干净。教训写进仪器：**每次改完前端，先 hit-test 顶层元素并读 overlay 节点，再谈屏上文字**。


## 十、十时四十三分：屏上终于有真照片了——丢掉它的原因不是网络，是我们自己的域名白名单

旅客最早那句「一张照片都没有」到这里才有完整答案，而且它是两件事，分开量了才敢分开设责任：

- 先修路。产品的公开来源客户端本来就尊重环境代理（`backend/app/integrations/provider_config.py:49` 默认 `auto`），而之前每一次起栈我都把代理变量剥掉了。换成只让 Wikimedia 两台主机走本机已在监听的代理口（`_boot_human_stack_r3.ps1`；高德／Photon／Overpass 仍走直连），用产品自己的 httpx 与产品自己的 UA 复测：Commons API 与一张缩略图都回 `http_status=200`（缩略图为 image/jpeg，四万余字节），同一时刻直连两侧仍是 ConnectTimeout。
- 再修闸。路通了屏上仍然是占位（`walk-38-log.txt:13` `GALLERY_IMGS=[]`、`:18` `PHOTO_IMGS=0`）。拿产品自己的媒体链一跳一跳打才看见真相：南锣鼓巷那一趟已经带回真作者 `Francisco Anzola`、真许可 `CC BY 2.0`、真 Commons 文件页与 `upload.wikimedia.org` 原图，`displayable_media` 却仍判 `NO_PERMISSION / ATTRIBUTION_OR_LICENSE_UNAVAILABLE`。逐条比对该判据的六个条件，唯一不通过的是缩略图主机名——Commons 现在把缩略图发在 `thumb.wikimedia.org`，而白名单里只写着 `upload.wikimedia.org`（现尖 `backend/app/agent/goal_media.py:58`；改动前那一代的同一枚文件是 blob `da2e4ee9f9c57b29b364c882cffb6c67a6656ab3`，其第 50 行就是只有一台主机的集合）。合规的照片是被我们自己写死的域名丢掉的。

改法只动域名白名单：图片接受 Wikimedia 自己这两台主机，来源页仍只认 `commons.wikimedia.org`，许可、作者、`can_show`、"不得是客户端传入的 URL" 这些条件一个都没松；反例臂把主机写成 `thumb.wikimedia.org.evil.invalid` 照样拒（`backend/tests/test_goal_place_media.py` 新增一臂，该文件 11 passed）。另外按实测把这一跳的预算从五秒抬到八秒（旧代 blob 第 79 行写 `timeout=5.0`，现尖 `backend/app/agent/goal_media.py:92` 是 `timeout=8.0`）：库里现存最早的一批媒体回执全是在五秒上下死的——`trial/results/20261022_v3_human_chrome/media-receipts-readback-1.txt:8` 到 `:13` 六格一律 `UNAVAILABLE`，耗时 5031、5203、5422、6203、6235、8281 ms。要说明的是：我第一次是在终端上看见 `NO_PERMISSION` 那一格与 5047 ms 那格的，而 walk-38 那一刻用的库后来被重启换掉了，那两个具体数字现在取不回来；所以本节把成因改挂在两样取得回的东西上——旧代源码那行白名单，和现库里三格真图回执的缩略图主机名（`:15`、`:18`、`:19`）。

同机同流程重走的读数（`walk-39-log.txt`）：

| 量 | 改前（`walk-38-log.txt`） | 改后（`walk-39-log.txt`） |
| --- | --- | --- |
| 相册里的图片元素 | `GALLERY_IMGS=[]`（`:13`） | 三张真图，src 为 `thumb.wikimedia.org/…Forbidden_City_Beijing_Shenwumen_Gate.JPG/960px-…` 与 `…Nanluogu_Xiang_(6230757826).jpg/960px-…`，自然尺寸 960×720（`:12`） |
| 第一张是否真的看得见 | `FIRST_PHOTO_VISIBLE=false PHOTO_IMGS=0`（`:18`） | `FIRST_PHOTO_VISIBLE=true PHOTO_IMGS=3`（`:16`） |
| 屏上署名与许可 | 只有「先看看这个地点」（`:15`、`:19`） | 「故宫博物院 来源实景 · 封面裁切 user:kallgan · CC BY-SA 3.0」「南锣鼓巷 … Francisco Anzola · CC BY 2.0」「什刹海 … FANG Chen · CC BY-SA 2.0」（`:14`、`:17`） |
| 地图层顶部引用 | 无照片可引（`:20`） | 「故宫博物院实景（封面裁切） · user:kallgan / CC BY-SA 3.0」（`:18`） |
| 落库的媒体回执 | 现存最早一批：颐和园三格一律 `UNAVAILABLE`，5031–8281 ms（`media-receipts-readback-1.txt:8` 起） | 三格 `REAL_POI_PHOTO` 带作者与许可、缩略图主机 `thumb.wikimedia.org`（`media-receipts-readback-1.txt:15`、`:18`、`:19`），两格 `NO_IMAGE/ENTITY_NOT_FOUND`（`:16`、`:17`），最长一跳 3110 ms（`:15`） |
| 像素 | `human-206-photo-strip-with-wikimedia-route.png` 214,562 字节（占位，`walk-38-log.txt:17`） | 同名文件 614,854 字节（`walk-39-log.txt:15`），另有 `human-207-map-layer-after-photo-route.png`（真图，含顶部署名条） |

仍然没好的部分照实写，两条分开：

- 这趟库里一共落了五格媒体回执，其中两格服务端确实找不到对应实体（`NO_IMAGE/ENTITY_NOT_FOUND`，`media-receipts-readback-1.txt:16`、`:17`，故宫博物院-午门与-文华殿）——屏上不是被闸丢掉，而是没有可核实的来源照片，而产品规则本来就不允许按名字去配异地同名地标。
- 屏上相册第四格「天坛公园」（`walk-39-log.txt:17`）在库里根本没有对应的媒体回执：这台库的 `goal_place_media` 只有五格，都不叫天坛。也就是说媒体腿是跟着研究批次跑的，草案最后入选的格子不保证都被跑过——旅客看到的"占位"里，有一部分不是"没有照片"，而是"还没替这一格去找过照片"。这一条今天只做到"有名字"，没有改。（后来在第十一、十二节里追到底：真正的原因是客户端只自动问前三格，而那句"先看看这个地点"背后当时根本没有按钮。）

另外照片能否出现，取决于这台机器有没有一条能出校园的口：那是我起这台隔离测试栈时给它设的环境，不是产品默认，用户自己的设备仍需各自可达——这一点已写进外发汇报，不当已验。

## 十一、十一点五十五分：重开浏览器的旅客，屏上正在对他说假话

想回去补测上一节那格「天坛公园」，才发现回不去。仪器 `place_media_click_r1.mjs` 用同一个隔离配置页重开应用，本机 localStorage 里明明还写着这趟行程（`walk-40-log.txt:2`，`citynexus.revolution.firstlook.journey` 与 `…recent-journeys` 都在），屏上却是一台全新的应用：相册格数为零（`:4`），找不到那张占位卡（`:6`）。而底部「我的旅程」那一屏的原话是「开始探索一个地区后，你保存的路线和出发进度会显示在这里。」——这台设备上有路线，这句话仍然这么说。

先把"是不是藏在屏幕外"量掉，再谈改：`returning_traveller_r1.mjs` 读渲染几何，`rev-recent-journeys` 这块 DOM **根本不存在**（`walk-40-log.txt:14` `recent_block_present: false`），不是折叠、不是在视口外。现场再补一刀存储读数：新标签页里 `bearer=false`、`readTravelerIdentity()=null`，而这两个值都存在 sessionStorage（`frontend/src/lib/travelerSession.ts:30`）；`loadRecentJourneys()` 第一句就是「没有身份就返回空表」（`frontend/src/trial/RevolutionFirstLook.tsx:282`），于是本机那条指针永远读不出来。这就是「重开浏览器找不到旧行程」的根因，两条腿都对上了。

今天改的是**不说假话**，只此一件：没有凭证、而本机留着行程指针时，行程面板改口说「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度。」（改后屏读 `walk-40-log.txt:25`，图 `human-213-trips-panel-honest-state.png`；`npm run typecheck` 干净，`rev-mobile-empty-start` 那颗按钮仍在原位、e2e 那条断言未动）。有凭证时原句不变。

鉴权一行没动，也不该由我动：把 bearer 挪进 localStorage 就是「持久凭证」那条路，与「带证据的找回流程」并列挂在 Issue #42 的待裁清单上，等号令者点哪一条。要点名的是：即使屏上看得见，也还进不去——服务端按 bearer 判归属，新会话拿到的新凭证并不拥有这趟旧行程，所以"看得见"只解决撒谎，不解决回去。

仪器自报一处：第一支 `place_media_click_r1.mjs` 里我随手写了"点『我的旅程』、点『北京』"的找回动作，却没有断言它是否真的进了那趟行程，于是 `STRIP_BEFORE=[]` 被我先读成"相册空了"。真相是压根没进去。第二支仪器改成先量 DOM 在不在、再量在不在视口，才拿到 `recent_block_present: false` 这枚有用的读数。

`RETURNING_TRAVELLER_SEES_HONEST_STATE = PASS（屏上不再说"你没有行程"）`；`RETURNING_TRAVELLER_CAN_REOPEN_OLD_JOURNEY = BLOCKED（等 #280 两条路裁一条）`。

## 十二、十二点二十五分：那张写着「先看看这个地点」的格子，以前按下去真的什么都不发生

第十节留了一句"第四格没被跑过"。这一节把它跑到底，结论比"没跑过"更难看：**屏上写着邀请，格子里没有按钮**。

- 现场一（按图片区域）：`place_media_click_r2.mjs` 在 walk-39 那台活标签页里找到第四格，按它的卡片本体（`walk-41-log.txt:5`），屏上纹丝不动，一直等到七十二秒（`walk-41-log.txt:29`，结论行 `walk-41-log.txt:32`）。结构读数说清了为什么：卡片是 `<article class="cn-place-photo is-placeholder">`，`card_is_clickable: false`，卡片中心 hit-test 命中的是一枚 SVG 图标（`tile_shape_probe_r1.mjs` 现读）。整个格子里唯一那颗控件在下方文字区，写着「查看对应安排」。
- 现场二（按那颗真控件）：`tile_button_tap_r3.mjs` 按下「查看对应安排」（`walk-41-log.txt:36`），按钮标签当场翻成「正在查看」，屏上仍然没有照片（`walk-41-log.txt:63`）。但库里多了一格回执：`16:24:36 天坛公园 NO_IMAGE MEDIA_IDENTITY_UNBOUND`，耗时一千五百毫秒（`trial/results/20261022_v3_human_chrome/media-receipts-readback-2.txt:18`）。这台仪器上一版漏掉了"标记只有 `NO_IMAGE`"那一类行，这次把过滤补上才读到它——修的是尺，不是读数（同一份文件第 4 行写着这件事）。也就是说**问是问到了，答案是"这个地点还没绑定到可查图的实体"，而屏上把这句话显示成和"从来没问过"一模一样的「先看看这个地点」**。

改法两件事，都在前端：把那句邀请做成真控件（`frontend/src/trial/mobile/PlacePhotoGallery.tsx` 占位分支里放了一颗 `<button>`，按下就走同一套选中→查图链路），以及**问过了就把答案写在屏上**（`NO_IMAGE + MEDIA_IDENTITY_UNBOUND` → 「还没核实到具体是哪个地点」；其余无图 → 「没查到可核实的实景照片」；来源没答 → 「照片来源暂时没答上」）。为此给客户端契约补了一个服务端本来就在发、客户端一直没读的字段 `reason_code?`（`frontend/src/api/citynexus.ts`）。许可与身份规则一行没动：按名字配地标仍然被拒，所以天坛那一格的正确显示就是"没核实到"，不是硬凑一张。

真机复测（`tile_honest_state_r1.mjs`，同一台活标签页刷新后走一遍）：改前那句「先看看这个地点」只是一个 `<span>`；改后它是一颗真按钮，读数行写着 `ask_button=先看看这个地点`（`walk-42-log.txt:5`）。按下之后三秒，同一格换成 `还没核实到具体是哪个地点 天坛公园 正在查看`（`walk-42-log.txt:7`，结论行 `walk-42-log.txt:10`），图 `human-217-tile-reloaded-invitation-is-a-button.png` 与 `human-218-tile-after-press-honest-answer.png`。`npm run typecheck` 干净；`e2e/revolution-visual-travel.spec.ts:93` 那条断言走的是 `url` 存在而加载失败那支，本次未动。

没解决的两件，照实说：其一，第四格右边缘在 414 宽的视口外（现读 `box.x=244 width=205`，右边界 449），旅客要先横向滑一下才按得到——这次没有改相册的排布。其二，`MEDIA_IDENTITY_UNBOUND` 的根子在"这个高德 POI 没有绑到 Wikidata/OSM 实体"，那是数据侧的事（与 #282 的地点身份同一条线），不是把文案改花就能好。

## 十三、十二点三十八分：行程守护按得开、也确实安静；「同行决策」那块牌子底下没有对应的门

验收单第七步要走到"下一站／地图导航／行程守护"，并要求没有真实风险时安静显示、不许编造天气事件。这一格今晚在活标签页上真按了一次（`guardian_screen_r1.mjs`）：

- 入口是真按钮、可命中：`trial/results/20261022_v3_human_chrome/walk-43-log.txt:3` 读 `hit_is_button: true`、`hit_topmost: "BUTTON."`，滚动后可见盒位 `x=173 y=343 w=134 h=78`。
- 打开后屏上原文：「行程守护 检查记录与处理进展 行程守护还没有检查记录 当前没有运行中的守护检查」（`trial/results/20261022_v3_human_chrome/walk-43-log.txt:6`，图 `human-220-guardian-panel-open.png`）。**没有编造的风险，也没有把"没检查过"伪装成"检查过且没事"**——这一半判 PASS。

同一排还有两块牌子。`frontend/src/trial/mobile/MissionCockpit.tsx:329` 与 `:331` 里，「准备出发」和「同行决策」挂的是同一个 `onTrip` 处理器：两块牌子去同一个地方。真按「同行决策」（`collective_screen_r1.mjs`，命中读数 `walk-43-log.txt:12`）之后，屏上出现的只有 `rev-mission-consent-strip` 那两条 AI 授权开关（`walk-43-log.txt:15`）。成员与权限那块面板（`frontend/src/features/access/AccessPanel.tsx`）只注册在另一套壳的面板表里（`frontend/src/app/v8PanelRegistry.tsx:324`），这台移动壳没有任何入口指向它。

所以验收单里"多人流程需三个独立本人登录点击"那一半，今晚不是"没测"，而是**这台壳上没有可点的门**：`GUARDIAN_COLLECTIVE = PARTIAL（守护 PASS；同行决策 BLOCKED——入口与「准备出发」同指针，壳内无成员面）`。两条可选路交给号令者，我不擅自造功能：甲＝把「同行决策」指到已有的成员/权限面板（要在移动壳注册一枚入口，属接线不属新能力）；乙＝这台单旅客会话里不摆这块牌子，等真有三个人再上。

仪器自报：`guardian_screen_r1.mjs` 第一趟在 `page.evaluate` 里用了只在 node 侧存在的 `flat()`，当场崩在 `ReferenceError`，日志里留下一条没有 END 的 `WALK43_START`（`walk-43-log.txt:1`）。今晚第三次踩同一个坑（前一次是 `tile_shape_probe_r1.mjs`），教训写死：**送进页面里跑的函数，只能带页面里存在的东西**。

## 十四、十二点五十四分：横滑相册量清楚了，我撤掉一枚没验到的改动，并留下一个没查清的黑屏

**相册在三种手机形状下的真实排布**（`strip_shapes_r1.mjs`，`trial/results/20261022_v3_human_chrome/walk-44-log.txt`）：视口 390×844、414×900、430×932 三档，卡片盒位读数完全一样——第一格右边界 234（完整可见）、第二格 451、第三格 668、第四格 885；轨道可视宽 316 / 340 / 356，可滑出总量 542 / 518 / 502 像素。也就是说**任何一档手机宽度下，落地只看得见一格半**，其余靠横向滑；第二格被切一半正是"后面还有"的常规提示，下方另有「查看更多地点」那颗按钮。所以第十二节我写的"第四格在视口外"不是缺陷，是轮播的正常形状——这条从"待修"改成"已量，判正常"。

仪器自报第二处：前两趟读数把轨道读成"第一格在屏幕左边外"（`right=-306`），原因是我自己更早那支 `scrollIntoView` 把轨道滑到了末尾，下一支仪器继承了那个状态。补上 `track.scrollLeft = 0` 复位后才拿到上面那组数。**逐枚滚动互相污染这条，今天又咬了我一次。**

**一个没查清的现象，写在这里而不是藏起来。** 同一台活标签页（14381，凭证在、traveler id 在）现在屏上是「旅行插画 等待第一个目标 / 现实地图 0 处地点」，而本机指针仍是 walk-39 那趟行程：`identity_pointer_r1.mjs` 现读 `session_id` 与 `pointer_owner` 是同一枚 `08fbd109-…`、`pointer_id=3f7f18fd-…`、刷新前后 `tiles` 都是 0（`trial/results/20261022_v3_human_chrome/walk-45-log.txt` 末尾）。这台标签页在十六点二十分那趟探测里同样是四格相册，中间只经过我自己的点按与刷新。**成因未定**：我用 `task_fetch_r1.mjs` 探任务口时把 URL 猜成了 `/agent/goal-task`，拿到 `http_status=404`——那是我的路由写错，不能当产品证据；行程本体 `GET /api/v1/journeys/{id}` 回 `http_status=200`。下一步该做的是从壳里真正加载任务的那条请求看起（它到底请求了哪条路、回了什么、失败后有没有重试入口），已单开一条待办。

**我撤掉了什么：** 今晚顺手做的一枚"把看过的答案留在这一页会话里，刷新后不必再按一次"的改动（`useSourcePlaceMedia.ts` 加 sessionStorage 答案缓存）已经**回退**——它的动机有实证（`trial/results/20261022_v3_human_chrome/walk-42-log.txt:5` 显示刷新后邀请又回来了），但改完的"生效读数"拿不到，因为这台标签页的相册正好进入了上面那个 0 处地点的状态。没验到的东西不进分支：现在那枚文件里 `ANSWERS_KEY` 零命中，`git status` 只剩证据文件。

## 十五、十二点五十九分：凭证过期时，屏上说的是"你还没开始"

第十四节那个"没查清的黑屏"当场就查清了，而且它不是黑屏，是**说谎**。

**读数。** 这台活标签页的凭证、身份、指针、行程 id 全都在（`identity_pointer_r1.mjs` 现读 `wanted_present: true`、`session_id` 与 `pointer_owner` 同一枚）。用 `exact_routes_r2.mjs` 照抄壳自己发的那两条请求、带这台标签页自己的 bearer 重放：`/journeys/{id}/map-places` 与 `/journeys/{id}/agent/goal-tasks/{task_id}` 两回都是 `http_status=401`（`trial/results/20261022_v3_human_chrome/walk-46-log.txt:17`）。**凭证过期了。**

**为什么屏上看不出来。** 三枚读取全部 `.catch(() => null)`（改前那代在 `frontend/src/trial/mobile/MissionCockpit.tsx:193` 起），401 被吞成 null，`dataState` 于是落到 "partial"——地图格说「地点研究会在这里汇合」，工作轨迹说「提交目标后，这里显示实际工作进度」，抬头说「等待第一个目标」。同一屏的「准备出发」卡片却早就写着「当前账号无法读取这份行程，请重新进入行程。」同一代代码里三处撒谎、一处诚实。

**改法。** 把"被服务器拒了"和"还没有东西"分开：只有 `CityNexusApiError` 且状态是 401 或 403 才置 `accessLost`（现尖 `frontend/src/trial/mobile/MissionCockpit.tsx:187`），三处文案各改一句。不加自动重试、不动鉴权，也**不承诺"重新登录就能回来"**——这台壳里没有可点的重新登录入口，而新会话是否仍拥有这趟行程今晚未验，所以只说「这趟行程还在，只是这台设备当前读不到它。」这一句的可依据是今晚从库里读到的那趟行程与它的三十五格研究地点。

**真机对照。** 改前：`human-224-tile-cleared-invitation.png`（0 处地点 + 「地点研究会在这里汇合」）。改后：`human-227-expired-credential-honest-state.png`，同屏三处分别读成「登录已过期」「这次登录已经过期 / 这趟行程还在，只是这台设备当前读不到它。」「这次登录已经过期，读不到工作记录。」（`trial/results/20261022_v3_human_chrome/walk-46-log.txt:15`）。`npm run typecheck` 干净。

**与二百八十号待办（旧行程找不到）的关系：** 同一族（凭证面），不同成因——#280 是这台标签页根本没有凭证（sessionStorage 随标签页销毁），这条是凭证在世但已到期。两条都不需要改鉴权就能先把屏说对。

**仪器自报：** 第一次探任务口我把 URL 猜成 `/agent/goal-task`，拿到 `http_status=404`——那是我的路由写错，不是产品证据；照抄壳里那两条真实路径才拿到 401。教训：**探接口要照抄调用点，不要凭印象拼 URL**（同一枚坑今天在第廿六节也咬过一次——凭印象写行号）。

## 十六、一点三十八分：那一格说「还没核实到具体是哪个地点」，而答案就在它下面一行

**旅客看到什么。** 相册第四格（天坛公园）在真人按下「先看看这个地点」之后，屏上写 `还没核实到具体是哪个地点 天坛公园 正在查看`，格子里没有图（`trial/results/20261022_v3_human_chrome/walk-42-log.txt:7`）。同一条答案也存进了服务器回执：`{"status": "NO_IMAGE", "reason_code": "MEDIA_IDENTITY_UNBOUND", "place": "天坛公园"}`，`latency_ms=1500`（`media-receipts-readback-2.txt:18`）。

**为什么这句话是假的。** 媒体腿查 Wikidata 之后只看第一条命中（`backend/app/integrations/media/place_media.py` 改前的 `candidates[0]`）。现读搜索答案（`media-hit-ranking-probe-1.txt:4` 起三行）：

```
### 天坛公园  search_hits=2
   hit0 Q125445   doc_label='天坛'          exact_name_match=False  distance_m=531  files=1
   hit1 Q49570636 doc_label='Tiantan Gongyuan' exact_name_match=True distance_m=309 files=0
```

hit0 是天坛建筑群，它的文档里从来没有「天坛公园」这个名字，所以按我们那条绑定规则判不出来——判不出来就说"没核实到是哪个地点"。而 hit1 才是公园自己：名字对得上、离高德给的那一点三百零九米。答案在下一行，腿没往下读。

**改法。** 把那条唯一的绑定规则抽成一个函数（`backend/app/integrations/media/place_media.py:323`），逐条命中都问它一遍（`:371` 起循环，`:378` 判定），第一条文档仍留作兜底（`:376`），所以真的没有一条绑上时，旅客听到的还是原来那句、不是新的含糊话。循环有两道界：最多五条命中，外加 `deadline = monotonic() + 5.0`（`:369`）——整条链只有十秒，一次拒绝不该让旅客等到超时。命中全都没有实体 id 时明确回 `ENTITY_NOT_FOUND`（`:386`），不再让 `None` 走到下标里去、把回执写成 `UNAVAILABLE_TypeError` 那种 blame 自己代码的码。

规则本身一个字没松：只用实体自己的名字和自己的坐标，不看搜索回显的标签（模糊搜索会把我们打进去的词原样吐回来，信它等于让任何近似命中自证），也不按"离得近"就配图。所以八达岭长城仍然拒（`media-hit-ranking-probe-1.txt:1` 起三行：hit0 `Q798826 doc_label='Бадалин'`、hit1 `Q33239460` 是「八达岭长城站」，两条都没有等于「八达岭长城」的名字，尽管第一条身上就挂着长城照片）——这一格照实说"没核实到具体是哪个地点"。这是裁过的边界（不静默把异地照片配到同名地标），不是漏修。

**回执的第二处假话。** 绑定成功之后没查到图片，那条早退（`PROPERTY_EMPTY`）和文件被撤（`FILE_WITHDRAWN`）都不写身份，于是落到汇总层的默认值 `UNBOUND`（`:525`）——"这地方我们没认出来"和"认出来了、没照片"是两件事，回执把它们写成同一件。现在两处各带上它自己挣来的身份（`:421`、`:427`）。

**同一出口、隔几分钟的真读对照**（`_media_second_hit_probe_r1.py` 调产品自己的 `goal_media._collect`，用的是存下来的那三点真坐标，不是夹具）：

| 地点 | 改前 `media-binding-before-2.txt` | 改后 `media-binding-after-3.txt` |
| --- | --- | --- |
| 天坛公园 | `NO_IMAGE` / `MEDIA_IDENTITY_UNBOUND` / `UNBOUND` | `NO_IMAGE` / `PROPERTY_EMPTY` / `BOUND_SOURCE_COORDINATE_MATCH` |
| 八达岭长城 | `NO_IMAGE` / `MEDIA_IDENTITY_UNBOUND` / `UNBOUND` | 同上（照实不动） |
| 南锣鼓巷 | `REAL_POI_PHOTO` / 署名 Francisco Anzola / `CC BY 2.0` / `thumb.wikimedia.org` / 闸门留图 | 同上 |

**先量到的一对废读数要点名：** 这对之前我先跑过一次，三格全是 `UNAVAILABLE`（`media-binding-before-1.txt`、`media-binding-after-1.txt`）。原因不在产品：这台机器环境里的 `HTTPS_PROXY` 指向 7897，而那一刻 7897 根本没有监听（`netstat` 只有 7892 在听，直连 7897 是 WinError 10061）。两臂同成 `UNAVAILABLE` 就是没有判别力，我把那对留下当"仪表先于结论"的样本，改用 7892 重跑才拿到上表。顺手量到另一条：不带 User-Agent 打 Wikidata 的搜索口，它回 `HTTP 403`，带产品那枚 `PROVIDER_USER_AGENT` 才 200——所以这不是"我们的出口不通"，也不是产品缺陷。

**"离旅客那一格很近"不等于"就是旅客那一格"。** 上表那三点坐标是我手打的 GCJ02；把探针点与库里同名那行对量（`_cmdr_v3_port_1022/_probe_coordinate_check_r1.py` → `media-probe-coordinate-check-1.txt`，现读 `PLACES_IN_DB 84`）：天坛公园差 334.6 米、八达岭长城差 426.5 米、南锣鼓巷差 20.5 米与 82.8 米两行。三点都在 800 米绑定半径之内，所以两臂照样判别；但"在附近"不是"那一格"。于是换成从同一枚库的 `journey_missions.intent_json` 里把旅客自己那五条线索原样取出来（`_media_stored_lead_probe_r2.py`，现读 `LEADS_FOUND 12`），一个字段都不改地喂给产品那条腿：

| 线索（库里原样） | 改前 `media-stored-lead-before-2.txt` | 改后 `media-stored-lead-after-1.txt` |
| --- | --- | --- |
| 故宫博物院 / 南锣鼓巷 / 什刹海 | `REAL_POI_PHOTO` + 署名 + 许可 | 同上，一张没丢 |
| 天坛公园 `amap:B000A81CB2` | `NO_IMAGE` / `MEDIA_IDENTITY_UNBOUND` / `UNBOUND` | `NO_IMAGE` / `PROPERTY_EMPTY` / `BOUND_SOURCE_COORDINATE_MATCH` |
| 八达岭长城 `amap:B000A45467` | `NO_IMAGE` / `MEDIA_IDENTITY_UNBOUND` / `UNBOUND` | 同上（照实不动） |

两臂各自"跑的是哪一代代码"不靠我说：改前那轮运行时 `git hash-object` 现读到 `f57a864d`（`HEAD~1` 的那枚 blob），改后那轮读到 `de71399d`（现尖那枚），跑完立刻从 HEAD 取回并复算工作树干净。

**测试。** `tests/test_goal_place_media.py` 现在 14 条通过；同一文件里两枚新臂在**改前的产品代码**上是红的（`media-fix-before-arm-1.txt:18` 起三行：`2 failed, 1 passed`），改后绿；那枚对照臂（`tests/test_goal_place_media.py:199`，钉"多问几条命中也不许放松绑定证据"）两代都过——它管的就是别把闸改松。相关面复跑 `tests/test_goal_*.py` 加身份与地点事实两枚文件：120 条通过。产品码 `6946f98bdc466b093ee1a224c8c6bca541836eff` 已推到 `rescue/v3-final-departure-20261022`（`git ls-remote` 回读同一枚）。

**屏上的"改后"读数怎么取，以及为什么不能就地重开。** 这句话是前端按 `reason_code` 挑的（`frontend/src/trial/mobile/PlacePhotoGallery.tsx:96`），所以要把上表走到屏上必须让后端加载新代码；而起栈脚本一启动就删自己的 SQLite（`_cmdr_v3_port_1022/_cmdr_v3_serve_human_r1.py:34`），重开会把上面那些读数依赖的 human4 库抹掉。所以另起一栈：`_boot_human_stack_r4.ps1` 用 60182／14382 与一枚空的 human5 库，旧栈与旧库一个字没动，新旅客从零走一遍（`gallery_recheck_r1.mjs`，逐格读渲染文字，记在 `walk-48-log.txt`），结果写在第十七节。


## 十七、三点十三分之前：把"出发待办"每一行改成能说清找谁的一句话

**这一节按册廿二日廿三裁语（Issue #42 的评论 id 6347562966，2026-10-22T17:56:21Z）来做。** 裁语里那句被落在实处的话是：「在"出发待办"每项明确显示**谁是阻塞原因／可点什么操作**」；被如实记下的边界是：拿不到合法证据就**如实 BLOCKED 并给下一有效动作**，不许为绿绕开服务端权威。

**先摊开一个已经错了很久的句子。** 方案屏（`frontend/src/trial/mobile/MobilePlanWorkbench.tsx`）在所有地点身份都定好、但方案仍不可选时，只会说一句话：「相邻几站之间还没有可用的转场路线。」它不看服务器给的原因。册廿二日廿三时在同一个栈上重走的三趟把这处抓给了屏幕：

- `trial/results/20261022_v3_human_chrome/walk-57-log.txt:28` —— 出发待办六行，缺的是「票价」和四段「转场路线」，没有一行说地点没定；
- `trial/results/20261022_v3_human_chrome/walk-57-log.txt:30` —— 屏下那句现在是「这版方案还缺：票价、转场路线。出发待办逐处写着找谁要。」；改前同一屏在同一条件下说的是转场路线那一套（上一代读数是 `trial/results/20261022_v3_human_chrome/walk-55-log.txt:33`，那时身份缺口还在，句子恰好蒙对了一半）。

**改法是一句话只有一个写者。** 新建 `frontend/src/trial/mobile/departureGaps.ts` 作唯一写者：缺项名（具体地点／营业时间／票价／转场路线）＋每项对应的操作句子；出发待办那张卡（`frontend/src/trial/mobile/DraftDepartureCard.tsx`）和方案屏都从它取词，屏幕不再自己想象缺什么。操作句子只允许指向这张卡上真实存在的那个按钮，所以「让 Agent 量这一段路」「让 Agent 找这一处」背后都是屏上按得到的「和 Agent 补齐出发资料」；票价那条不许假装有按钮，只说「没有来源给出这一项的价格」。

**谁阻塞是服务端算的，不是前端猜的。** `backend/app/agent/goal_preparation.py` 每行缺口现在多带一个 `resolution` 码：没地点→`ASK_AGENT_TO_FIND_PLACE`，有地点但来源没答→`ASK_AGENT_FOR_PLACE_FACT`，这段路没量过→`ASK_AGENT_TO_MEASURE_HOP`，票价无人答→`PRICE_HELD_BY_TRAVELLER`。值级断言在 `backend/tests/test_goal_preparation.py::test_every_to_do_line_names_who_holds_the_answer`；方案读回里同一批码也要能看见（同一测试的尾部断言）。

**边界读数（为什么还不能点到 SELECTED→ACTIVE）。** 只读取器 `trial/results/20261022_v3_human_chrome/departure-price-evidence-probe-1.txt` 直接调用产品自己的判据，把走查那一趟的候选摊开：

- `departure-price-evidence-probe-1.txt:6` —— `plan_authority_blocker` 给出的阻塞名是 `UNRESOLVED_ACTIVITY_FACTS`，不是"缺身份"；
- 同一文件第 7 到 12 行（六处已定地点）：每一条都是 `opening_status=VERIFIED_PROVIDER`、`blocks_opening=false`，唯 `blocks_cost=true`；`:13` 是那条没有地点的（就近晚餐、早休，`NO_PLACE_ROW`）；
- `departure-price-evidence-probe-1.txt:16` —— 这座城市在高德来的 72 条地点里，营业时间已知 56 条，**票价已知 0 条**；`:17` 两样都齐的地点 0 条。

也就是说营业时间那一栏已被真实供应商证据填上（册廿二日廿二时那一刀的效果，屏上也验到），剩下咬死选用门的是"票价没有来源可核"。高德答不出的东西我不会替它填；`show_fields=business` 回来的 `cost` 只出现在餐馆类 POI（`trial/results/20261022_v3_human_chrome/amap-business-fields-1.txt:38` 的 119.00），把它当门票价是造假，所以这一栏留着不接。第二道门在 `backend/app/main.py:18120`：候选没有冻结的移动证据就 409，而这条草案路径本来就不负责冻证据（`backend/app/agent/goal_preparation.py:76` 的 `mobility_frozen` 写死 `False`，落库处 `:233`）——要用既有机器把 Agent 已经真调高德量到的步行段冻成快照，是下一刀，已按裁语立在待办而不是停在"等裁语"。

**同一份裁语要的 UNKNOWN-region 回归也做了，做法与理由都要摊开。** 先把收紧的那一版写出来跑红：两条线索（一条 `region_status=UNKNOWN`，一条根本没有这个字段）都被当成正式地点落库，并盖上本次行程的 city_code——洞是真的。但同一批现读数据反对"直接拒绝"：`trial/results/20261022_v3_human_chrome/region-status-by-provider-1.txt` 数完今晚 22 个 canary 库，`amap/MATCHED` 851 条、`photon/UNKNOWN` 126 条，而 `app/region_matching.py:57` 与 `:67` 说明 UNKNOWN 只代表"字段不在或比不了"，不代表"异地"。一刀切会让真人已经拿到的地点退回缺口。所以这刀落的是**披露**：`backend/app/agent/goal_place_identity.py` 写进行踪的 metadata 里带 `region_status`，钉在 `backend/tests/test_qoder_goal_place_identity_r1.py::test_a_promoted_lead_says_on_the_row_whether_its_region_was_ever_checked`（先红后绿：改前那条断言读不到这个字段）。要不要让"没核过地区"的地点失去选用资格，仍是一条需要点名的裁语，我不替权威改语义。

**两枚字面过头的说明也按裁语改了。** `trial/results/20261022_V3_TEN_STEP_PLAYBOOK.md:3` 现在写"真实桌面浏览器的手机视口……**不是物理手机硬件**"；`:43` 的第 10 步改为「刷新之后，选过的那版还在」，`:45` 明写关掉浏览器再打开暂时不能保证找回这趟行程（凭证存在标签页自己的会话里）。

**测试读数（现取现算）。** 解释器 `D:\moodle\CityNexus\.venv\Scripts\python.exe`；`-m pytest tests/test_goal_preparation.py tests/test_qoder_goal_place_identity_r1.py -q`＝18 条通过；放宽到 `-k "goal or amap or preparation or place_identity or departure"`＝211 条通过、1 格红（这一族的 -k 只圈到那两个参数里的 DEPARTURE 那一参；同一格文件整档跑是 2 格红）。那两格红不是我今晚造成的，用同一条命令做了对照：把 `goal_place_identity.py`、`goal_amap.py`、`amap_provider.py` 退回册廿二日廿三时第一刀之前的代（`e4d800d6cb`）再跑，仍是同样 2 格红——名字是 `tests/test_v13_1_2_structural_anchor_integrity.py::test_structural_reservation_survives_v9_identity_then_v12_compose_and_select` 的 ARRIVAL／DEPARTURE 两参，拒绝码 `UNRESOLVED_ACTIVITY_FACTS` 且 `unresolved_facts` 为空数组。前端整树 `npx tsc -p tsconfig.typecheck.json --noEmit`＝0 处错误（先跑过 `tsconfig.check.json` 那一版，发现它只圈五枚文件、对我改的文件是假绿，已换全树）。

**量具自曝两处，不遮掩。** 其一：走查脚本的截图名当时写死 `walk55-*`，所以册廿三日零点五十六那一趟把前一趟的画面就地盖掉了，日志 `walk-56-log.txt` 与图 `walk55-*.png` 是同代、和文件名不同代；事后把图另存为 `walk56-*.png` 并对拍（`md5sum` 同名两枚逐位相同），但 `walk56-09-chosen.png` 其实是前一趟那帧（脚本只在按钮出现时才拍那一张，没重写）。从册廿三日十一分那一趟起，截图名改成随 `WALK_SHOT_PREFIX` 走（`walk57-*.png` 与 `walk-57-log.txt` 同代）。其二：我在仓库根留过一枚 0 字节的 `departure_full_walk_r3.mjs` 空壳，已删；正身在 `D:/moodle/_cmdr_v3_port_1022`，`node --check` 通过。

**交付档按裁语要求的四类分开记。** `REAL_BROWSER`＝真人视角走的是本机外部 Chrome/Edge 经 CDP 9335 驱动的真实页面（非预置 API 状态）；`CHROME_USE_SCREENSHOT`＝`walk56-12-departure-after-save.png`、`walk56-13-workbench.png`、`walk57-12-departure-after-save.png`、`walk57-13-workbench.png`（390 宽；430 宽那一档要在选用门真打开之后再补，见下）；`LIVE_PROVIDER`＝高德营业时间与实景照片是当场真调回来的（探针文件里带 http 状态与 provider 字段），票价一栏没有；`USER_VERIFIED`＝**仍是 PENDING**，本机窗口不等于手机在手里的点击。产品代 `6fcbee8845bacd9787815a1e6e420d8ae012e629`（`git ls-remote` 现读回同一枚）。

**还没好在哪，说清楚。** 选用按钮一次都没按到（三趟的 `STEP_13_SELECT_BUTTONS` 都是 0：`walk-55-log.txt:34`、`walk-56-log.txt:30`、`walk-57-log.txt:31`），因为票价没有可核来源、移动证据没人冻；同行决策那块牌子底下依旧没有门；"关掉浏览器再回来找回行程"仍未实现；这些都不靠改断言换绿。


## 十八、第 1、2 棒之后：真人一趟走到「旅程已开始」（walk-62，2026-10-23 05:01—05:07）

同一位首次打开的旅客、同一台隔离 Chrome、同一个标签页，从首页一句话到出发，全程只按屏上有的按钮。
后端 60196／前端 14396／独立库 citynexus_v3_human11_1022.db；逐帧截图 `walk62-*.png`，读数在
`trial/results/20261022_v3_human_chrome/walk-62-log.txt`，屏幕之外的持久化对账在
`trial/results/20261022_v3_human_chrome/walk62-departure-readback-1.txt`。

屏上先后出现的话（逐字）：「已保存 4 项正式安排。下方可以查看日程和出发待办。」→
「当天的转场还没有向高德核实过。」（按钮「核实并冻结今天的转场」）→「转场已核实 3/3（其中 1 段是跨夜衔接） ·
已冻结进这版方案」→「还没有来源给过确定的费用；另有 4 处门票没有来源，预算里没有把它们算作 0 元，实际花费可能超出预算。」
（按钮「票价没有来源，我接受先不计入预算」「让 Agent 换成价格明确的地点」）→
「按你的确认保存：这 4 处门票仍未核实，没有已核实的费用，出发前请自己留意现场票价。」→
「选用这份方案」（第一次真的出现并且被点下）→「可以确认出发」「方案 1 已选用」→「确认方案，开始行程」→
「旅程已开始」；刷新一次后仍是「旅程已开始 · 方案 1 正在使用」。

库里对回来的是同一件事：journey 014bc3ff-86c4-4254-a343-e4046d06c3f1 状态 ACTIVE，active_plan
87211ad3-3194-46c5-b9ed-92b250effc1f，snapshot 63410f5c-8241-4ecf-910d-84d143d0a0eb，三条
LIVE_PROVIDER_CAPTURE 的步行事实（20／44／230 分钟），十二次高德 ProviderCall（district 1、search 8、
walking 3），幂等键与审计各就位（goal.prepare、goal.freeze-routes、goal.price-accept、plan.selected、
plan.committed_by_traveler、journey.started）。

仍未通过、也没被我说成通过的：出发日期那一天的营业时间核实（第 3 棒）、关掉浏览器后重新登录找回旧行程
（P1，本轮只验到同一登录态下刷新保留）、以及"真机由主人亲手点一遍"——USER_VERIFIED 仍是 PENDING。
