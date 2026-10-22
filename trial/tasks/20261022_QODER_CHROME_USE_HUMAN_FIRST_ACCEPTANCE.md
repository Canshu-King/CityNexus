# P0｜Qoder Chrome-use 真人视角操作验收（2026-10-22）

**当前施工负责人：Qoder。分支：rescue/v3-final-departure-20261022，PR #43；统一任务：Issue #42。**

用户最新硬要求：**别再只写后端测试、API 收据、绿色统计。让 Qoder 使用 chrome-use 插件/CLI 实际模仿普通人操作 CityNexus App，先看屏幕，再点，再修，最后才回归。**

## 一、Chrome-use 必须真实接起来

1. 优先使用用户点名的开源 [chrome-use](https://github.com/leeguooooo/chrome-use)，即真实 Chrome 扩展与本地 CLI/MCP，不是 Playwright 伪装成已经有人操作。先在 Windows Qoder 会话检查安装与浏览器连接：

    chrome-use --help
    chrome-use status
    chrome-use skills get core

2. 如果未安装，检查官方仓库/发布包、扩展和 Windows 安装说明；按许可和环境权限安装配置。在独立测试 Chrome profile 上验证真实页面可读取、可点击。**不要拿“插件没装”当下一轮停工借口**。
3. 核对版本后，以官方 core 指南为准。以下只是已公布的 CLI 交互示例，实际按钮引用必须从当时浏览器的 snapshot 获取：

    chrome-use --session citynexus-v3-human open http://127.0.0.1:14332/revolution
    chrome-use --session citynexus-v3-human snapshot -i
    chrome-use --session citynexus-v3-human click @e3 --observe
    chrome-use --session citynexus-v3-human snapshot -i --diff
    chrome-use --session citynexus-v3-human screenshot ./trial/results/human-01.png

4. 若 Qoder 当前宿主无法接 chrome-use，使用 **Qoder 官方 Browser Agent / Chrome Browser Connector / Computer Use** 操作现有 Chrome，记录退化原因及实际浏览器连接方式。Qoder IDE Agent Mode 可通过 /browser 显式调用；桌面应用可在 Settings → Computer control → Browser → Google Chrome 开启连接。重点是真正操作 Chrome、截图观察，不是某个插件名。
5. 使用项目独立测试 profile + 非生产后端 + 隔离的 canary DB。不能读取或上传个人密码、Token、支付、邮箱、其他网页，不能在真实账号上擅自发起购买/预订/邀请/权限更改。保留用户现有真实数据。

## 二、第一轮要像完全不认识这 App 的年轻用户

先实际打开产品入口，用眼睛看，不先读前端代码定位按钮。不设成功用的 localStorage、Journey ID，也不直接调用 API 代替人的点击。记录首次打开 30 秒能不能发现 Agent 入口、地图和下一步，哪些词让人看不懂，是否点了按钮毫无反应。

**统一故事：** 2026-11-02 至 11-03 北京两天，人均预算 ¥500，喜欢古迹与胡同小吃，不要太赶；后续希望第二天下午轻松湖边散步。多人场景是“我、阿杰、小雨”三名各自登录的测试成员。

按屏幕自然执行：

1. 从真正的启动器或 /revolution 首屏开始。输入一句自然语言旅行愿望，创建同一 Journey/GoalTask。看看是否有人类能理解的“正在研究”，不是假动画，也不是后台默默运行。
2. 与真实 Agent 继续对话。它提问就按屏上选择，观察研究过程、工具调用、任务进度与结果；如果只有连续追问，始终没有可用日程，必须记录为产品断点，而不是先用 plans/generate 造好方案。
3. 点开地图和地点详情，看真实地点照片及来源、营业/票价/转场状态。若在线服务打不开，显示 UNKNOWN/估算/待核实与可继续的动作，不能把 mock-city 离线北京地点或 V3 设计示意图说成 LIVE_PROVIDER。
4. 尝试选 A/B/C，切第二天，回到地图，再回到日程。若三方案未生成，保留红色真实阻塞，不许拿另一个预造 CN-BEIJING Journey 来冒充第一趟 Agent 成功。
5. **通过唯一 Agent 聊天入口**发：“把 11 月 3 日下午换成轻松的湖边散步，其他安排不动。”必须比较修改前后 slots，刷新/切 tab/浏览器返回后恢复。**用户手动在日程编辑器添加内容与 Agent 自动理解并修改是两个不同结果，不准混报。**
6. 从同一个 Journey 的草案继续“准备出发”：看真实待办，补可验证来源，点“选用这份方案”，可行时点“确认方案，开始行程”，真实服务端 SELECTED/ACTIVE；缺少 provider 事实则 BLOCKED 且告诉用户下一步，不能另开一趟 mock-city 旅行绕过。
7. ACTIVE 后点下一站/地图导航/行程守护，查看 Agent 真实状态和操作记录。没有真实风险时安静显示“暂无需要调整”，不能造假天气事件。多人流程需三个独立本人登录点击，2/3 不改正式共享计划，3/3 再按当前权威规则判断是否生效。
8. 从空状态、部分成果、错误状态分别再操作：刷新、返回、切 tab、键盘遮挡、供应商网络失败、模型超时、用户不授权在线搜索。每个错误都应有能点的下一步。

**手机 390×844、430×932 与桌面各实际试一次；模拟 Chrome 移动视口 ≠ 真实手机硬件。**

## 三、真人视角优先的工作节奏

绝不能先写 50 个后端 tests 才肯打开页面。顺序改为：

**真实 Chrome 打开 → 找一个普通人会卡住的步骤 → 现场屏幕截取 BEFORE → 定位前后端原因 → 改最窄的产品代码 → 再用真实 Chrome 重新点击同一路径 → 截取 AFTER → push 代码。**

- 第一轮即使只走到第 2 步，必须真实展示“我从哪点进去 / 哪里找不到下一步”。红色的产品体验报告比 500 个只在后端通过的测试更有价值。
- 不要用已经知道 DOM testid 的 Playwright 脚本替代不认识 App 的用户；chrome-use 操作者最初应依屏幕上的自然语言、可见按钮和截图作决定。
- 发现“AI 暂未开启”、地图空白、技术术语占满界面、页面不知去哪继续、未知费用被写成免费、刷新丢失、十个按钮一样大等问题，优先直接修前端。
- 现有用户功能（真实 Agent DISCUSS、照片地图、三方案、准备出发、Guardian/多人）全部保留。可以使用 e2e/单元测试作为改动后的回归护栏，但不能宣称测试全绿就代表体验完成。
- Qoder 在 rescue 分支修复并及时提交；PR #23/#35 不抢写，不 force push，不重置用户 DB，保持权限与来源诚实。每个切片都向 Issue #42 和 PR #43 留可访问链接。

## 四、证据交付合同

交付一份独立中文报告：

    trial/results/20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md

截图 / 可选录屏放：

    trial/results/20261022_v3_human_chrome/

每一屏包括：时间、URL/视口、Chrome 工具、用户看到的文字、上一点击/下一点击、截图文件、该步实际后端请求结果（凭据打码）、是否同 journey_id/task_id、provider provenance、能否继续。统计首个 Agent 入口点击数/耗时、死路/返回次数。未测值写 NOT_MEASURED，不能编造漂亮数字。

分离四种结果：**LIVE_PROVIDER / MOCK_CATALOG / MODEL_SUGGESTION / UNKNOWN**。截图不能替代可验证事实；本地实验库不能说是真实游客行程。

报告必须公开这些门禁：

- CHROME_USE_CONNECTED = YES / NO（或 BROWSER_FALLBACK_USED 及原因）
- HUMAN_BROWSER_USED = YES / NO
- NOVICE_FIRST_CLICK = PASS / BLOCKED（首屏发生了什么）
- SAME_JOURNEY_GOAL_TO_ACTIVE = PASS / BLOCKED（同一个 ID 的整条链，另建演示 Journey 不能算）
- AGENT_RESEARCH_GROUNDED = LIVE / PARTIAL / BLOCKED
- AGENT_NATURAL_LANGUAGE_HALF_DAY_EDIT = PASS / BLOCKED / NOT_ATTEMPTED
- RELOAD_RECOVERY = PASS / BLOCKED
- GUARDIAN_COLLECTIVE = PASS / BLOCKED / NOT_ATTEMPTED
- PRODUCT_FIX_SHA + BEFORE_SCREENSHOT + AFTER_SCREENSHOT
- USER_VERIFIED = PENDING（除非用户本人使用真实手机通过）

每次推进必须至少修复一个真实可见的人类操作阻塞，或者明确证实阻塞在无法由本轮修复的外部依赖并给出替代行动。最后另交一页**十步以内图文试玩说明**，能让用户自己从首页找 Agent、进入地图、选择方案、继续旅行，不要教用户先读 REST 接口。

## 五、参考和边界

- [当前产品 PR #43](https://github.com/Canshu-King/CityNexus/pull/43) 已有 Chrome/Chromium 手动点击的部分证据；但 Agent 对话 + mock-city 出发并非同一真实 Journey。
- 当前 Agent 半天改动实测是旅客在日程编辑器 **手动改**，不是 Agent 自己按自然语言改。
- 真实地点供应商仍有 TLS/代理问题，需要从浏览器里观察错误后优先解决“用户该去哪继续”。
- 原始十屏在 docs/revolution/v3-design，做产品交互参考，不能直接当运行 UI。
- Chrome-use 官方：https://github.com/leeguooooo/chrome-use；Qoder 官方浏览器：https://docs.qoder.com/user-guide/chat/browser-agent；Qoder 原生 Computer Use：https://docs.qoder.com/qoder/computer-use。

**最终目标：普通人能在真实浏览器里独立完成旅行流程，而不是开发者在 API 实验台上证明它理论上能运行。**
