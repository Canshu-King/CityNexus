## 12. 「按这一版安排」那一按，终于在两代真机上走完了（blocker 5 结；城市那句仍欠屏证）

### 12.1 链走完了，而且是在两代上各走一遍

bf110 的第四趟（`trial/results/20261026_gozero/bf110-replan-apply-full-chain-430-r4.txt`，干净代 `ea51658c9a` + 我把两枚前端文件带进那一代）：

- 勾「按以上时间准备方案」→ 按「保存为正式候选方案」→ `HTTP POST 201 …/prepare-plan`，屏上「已保存 8 项正式安排。」；
- 按「核实并冻结今天的转场」→ `HTTP POST 200 …/plans/1fc18127…/freeze-routes`；
- 缺口卡片挂出来：`rev-v3-travel-gaps count=1 box=323x216@271 hitSelf=true`，短的那一段逐行写在屏上
  （「天安门广场 · 看广场与城楼外观 → 故宫博物院 · 午门入、神武门…」）；
- `rev-v3-replan`「根据路线重新安排」`count=1 disabled=false box=296x44@434 hitSelf=true` → 真按；
- 按完差异列 Surface：`rev-v3-replan-diff` 里读到「故宫博物院 · 午门入、神武门出：11:00–12:00 改成 11…」，
  接受键 `rev-v3-replan-apply` = `count=1 visible=true hitSelf=true disabled=false box=296x44@434 label="按这一版安排"`
  （同收据 `:75`、`:77`）；
- 真按它 → `HTTP POST 201 …/prepare-plan`（带合并后的时间），屏上换成
  「已按路线把 4 处往后排，这是一份新的候选方案；生效的那一份没有变。新的一版还没有核实转场；先选用这一版，再核实并冻结转场。」
  冻结键回到「核实并冻结今天的转场」，缺口块计数归 `0`（`:81`）。

bj115 把同一串在**本代尖**上又走了一遍（`trial/results/20261026_gozero/bj115-named-sentence-tip-generation-430.txt`）：
话术换成「每段步行不超过 200 米」，`REPLAN_DOOR replan=1 hit=true`（`:74`）→
`APPLY_DOOR count=1 visible=true hit=true disabled=false label="按这一版安排"`（`:85`）→ 按下去 `201`
→ `ACCEPT_KEY_WALKED true`（`:99`），全程 `LEAK api_in_body=false uuid_in_band=false`。

**所以交付件第 5 条与 #336 的"分辨复现"结：接受键在出发门报出缺口之后是挂出来、看得见、点得中、点下去真换出一版新的候选方案。**
两代各自独立一趟，不是同一次运行换说法。

### 12.2 怎么得到"代次 = 现尖且零 dirty"的第三台栈（不动别人的在飞改动）

不在 :60362 上重启（那台的 `CITYNEXUS_TRAVELER_AUTH_SECRET` 是启动时随机的，重启即作废所有 bearer），
也不在 `D:/moodle/_cmdr_rescue_v3_1022` 上直接起 vite（那棵树有别人 22 枚未提交的前端改动，屏幕就不是我的代次了）。
做法：`git worktree add --detach E:/_cmdr_tip_113 dea0328e0b`（现读 0 行 dirty）＋
`mklink /J` 把现尖那棵树的 `frontend/node_modules` 指回主干（内容可解析：`vite/bin/vite.js` 在），
再用 `trial/human_walk/_boot_rescue_stack_r113.py`（`RESCUE_ROOT=E:/_cmdr_tip_113 RESCUE_DATA=E:/_cmdr_tip_113_data
CLEAN_BACKEND_PORT=60364 CLEAN_WEB_PORT=14464`）起一对新栈：全新空库、后端 `HEALTH ok`、vite `SERVED 200`。
脚本沿用在跑那台的规矩：高德键只从进程环境继承（只印 `AMAP_KEY_INHERITED True`，值不落任何文件），
端口被别人占就拒起，端口号只列 `LISTENING` 的 PID。

### 12.3 我对干净树做过的一次有界偏离（已复原）

为了在本会话内先看到句子与链，我把 `departureGaps.ts` 与 `DraftDepartureCard.tsx` 在 18:33 复制进
`E:/_cmdr_clean_1028`（vite 会热读，实测 served 模块里已含 `placeCityRefusalSentence` 与 `refusalReason`），
18:46 用 `git checkout --` 复原；现读该树 `status --porcelain=v1` 为 0 行，两枚文件与 `ea51658c9a` 的
blob 逐位相同（`e612908c2c…`、`e7b8b738bf…`）。这段窗口内那台栈的屏证代次 = 该代 + 我这两枚文件，写在这里，不隐藏。

### 12.4 城市那句新话，仍然没有屏上证词（并且我知道为什么）

两趟新链（bf110 r4、bj115）都没有再撞到 `PLACE_NOT_IN_JOURNEY_CITY`——那一拒取决于当轮研究把哪一槽绑到了别的城市池的行上，
不可预置（也不该预置）。想复用已经拒过的那趟行程 `3d9715f7` 也不行：给 bf110 的臂加了 `SKIP_SENTENCE=1` 之后，
冷开浏览器进「我的旅程」读到的是 `CARDS 0`（`bf110-replan-apply-full-chain-430-r3.txt`），
这正是 #332 的第二种形状——库里的行程还在，会话里的身份回不来。
所以 §11.3 那句新话目前只有代码级 + `pytest` details 级证据；**不写成已证**。

### 12.5 顺手量到的一格小观察（不改判，只落账）

bf110 r4 里，按过「根据路线重新安排」之后卡片变长，缺口那一行被顶到 `box=296x75@66` 且 `hitSelf=false`
（中心点被上方固定层接走），而接受键自身 `hitSelf=true`。旅客要点的键没被压，被压的是那行读数；
要不要给这段也做让位，属 #305/#306 那一族的取舍，留给号令者或主人点头，我没有顺手改。
