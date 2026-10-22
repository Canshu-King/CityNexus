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

- `CHROME_USE_CONNECTED = YES（读与点）/ NO（截图）`，`BROWSER_FALLBACK_USED` 已注明原因
- `HUMAN_BROWSER_USED = YES`
- `NOVICE_FIRST_CLICK = PASS`（首屏一句话即可提交，见第二节；「目的地」仍要再填一次，这是下一个待改点）
- `SAME_JOURNEY_GOAL_TO_ACTIVE = BLOCKED`（这一轮只走到「Agent 输入框已握着同一句话」，尚未在同一 Journey 上走到 SELECTED/ACTIVE）
- `AGENT_RESEARCH_GROUNDED = BLOCKED`（公开地名来源今天网络不通；屏上 `0 处地点`，`UNKNOWN` 未被改写）
- `AGENT_NATURAL_LANGUAGE_HALF_DAY_EDIT = NOT_ATTEMPTED`（本轮没做；此前那格是**旅客手动**在日程编辑器改的，两者不得混报）
- `RELOAD_RECOVERY = PASS（上一棒，手动改半天之后刷新仍在）`
- `GUARDIAN_COLLECTIVE = NOT_ATTEMPTED`
- `PRODUCT_FIX_SHA = 见本文件所在提交`；BEFORE/AFTER 截图见第四节
- `USER_VERIFIED = PENDING`（本机 Chrome 窗口不是手机在手里的点击）

## 六、十步以内试玩说明（给第一次打开的人）

1. 打开 App，看到「你的下一趟旅行，从一句话开始」。
2. 在第一格写一句人话，例如「想慢慢逛北京的古迹和胡同小吃，两个人，人均预算 500，一天别太赶」。
3. 第二格写城市名（北京）。
4. 想指定日子就点开「日期与天数」，选出发日。
5. 想改人数或预算，点开「更多偏好」。
6. 按「继续规划 →」。
7. 屏幕下方已经放着你刚才那句话，想改就点在里面改。
8. 按右下角「发送 ↑」，Agent 开始研究并会问你问题。
9. 它给选项时按选项回答；想看每天安排就点「日程」，想看地点就点「地图」。
10. 安排满意后，在「日程」里按「准备出发」，再按「选用这份方案」。
