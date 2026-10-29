## 11. 城市那一拒：交款前的「保存为正式候选方案」第一次真按到 409，以及我那把假绿的类型闸（10-29 凌晨）

### 11.1 这一节是从交付件 7 的第 5 条 blocker 走出来的

那条 blocker 原话是「『和 Agent 补齐出发资料』之后，被拒的方案没有『应用这一版』的可达键（#336 的分辨仍未跑成）」。
它一直是"未经检验的说法"而不是事实，因为没有人真按过这条链。bf110 按了：冷开 `/revolution`（430×932 真 Chrome，
零 dirty 的 E:/_cmdr_clean_1028 @ `ea51658c9a`，vite :14462 / 后端 :60362，自己的 SQLite），发那句话，
`SKIP` 掉提问轮，等研究结束（屏上 `已整理 2 天 · 6 项安排`，t=95.2），进「我的旅程」到那趟行程，勾「按以上时间准备方案」
（`CONFIRMED true was=false`），按「保存为正式候选方案」。

结果不是 blocker 说的那一格，而是更前面的一格先拒了：

```
HTTP POST 409 /api/v1/journeys/3d9715f7-…/agent/goal-tasks/f58ef668-…/prepare-plan
BODY {"error":{"code":"CONFLICT","message":"PLACE_NOT_IN_JOURNEY_CITY", … ,"details":null,"error_receipt_id":"CNX-CVZ9RFNC"}}
```

屏上旅客读到的是最后一句兜底话「这次未能保存，时间仍留在这里，可以重试。」
（收据 `trial/results/20261026_gozero/bf110-replan-apply-full-chain-430-r2.txt:35` 起）。
所以这一趟对第 5 条 blocker 的读数要如实写：**没走到** `rev-v3-replan` / `rev-v3-replan-apply` 那两格，
因为在它们之前的 promote 那一按就被 409 挡下了；八枚 `rev-v3-*` 键在挡下之后的计数都是 `count=0`。
这条链在真机上仍然没有屏证，只是原因换了：不再是"键没接回来"，而是"上一步先把人拒了"。

### 11.2 探针：这一拒到底是对谁拒的（只读，不动库、不动键）

`trial/human_walk/_bg_probe_city_refusal_r111.py`（输出 `trial/results/20261026_gozero/bg111-city-refusal-probe.txt`）
以 `mode=ro` 打开那枚 canary 库，逐槽摊开 `goal_preparation.py` 两条绑点路径实际会用到的键。
被拒的 6 槽里 5 槽绑在本行程城市池内，唯一一格偏了：

```
slot 1:0 title="北海公园（北岸/北门进，看白" place_id=amap:B000A80UL1 lead=True lead_region=MATCHED
         canonical_rows=1 bound_city=CN-RV-D39D52531220 MISMATCH=True via site_268_lead_canonical
```

行程自己的城市码是 `CN-RV-A0EDFF4347FE`，同城池里 48 处地点。同一份探针读 bd106 那趟（当年 201 两次的行程）时，
六槽的 `place_id` 全是空串，六格都写 `via no_binding_at_all`（同文件 `:15` 起）——
也就是说 **bd106 的 201 不是"地点都绑对了"，而是"根本没有绑"**，所以城市这道门压根没被触发。
这把 §9 里"干净屏、零 4xx"那句话的边界说清了：那条路径通，是因为它走的是无绑定的分支。

一句话事实：这道门拒得对（那一处地点确实登记在另一个城市池的清单上），
但它拒的是"重复按也不会变"的一类，而屏上写的是"可以重试"。

### 11.3 产品刀：这道门现在说得出是哪一格（不改判据，只把凭据带出来）

- 后端 `backend/app/agent/goal_preparation.py:72` 新增 `refuse_place_city(...)`，两处 raise（`:286`、`:306`）改走它：
  `message` 逐字保持 `PLACE_NOT_IN_JOURNEY_CITY`（旧读者一律不破），另挂 `reason_code` 与
  `details = {sequence_no, title, date, place_name, place_city_code, journey_city_code}`，
  形制与同一文件里给时间规则用的 `refuse_schedule_row` 一致（信封读法在 `app/main.py:884-892`）。
- 前端 `frontend/src/trial/mobile/departureGaps.ts:401`、`:403` 新句子，旅客读到的是
  「第 4 项「北海公园（北岸/北门进…）」对上的地点记在另一座城市的清单上，不在这趟旅行的城市里。改时间没有用——回到探索，换一处同城的地点再保存。」
  没有行级 details 时也有同一枚作者的一句兜底话（`placeCityRefusalSentence(null)`），
  所以不会再掉回"可以重试"。
- 卡片按 `reason_code` 先分流再选句子：`frontend/src/trial/mobile/DraftDepartureCard.tsx:30`（新 `refusalReason`）、
  两处 catch 分别在 `:150` 与 `:231`，兜底分支在 `:167`。**必须先分流**：城市那枚 details 也带 `sequence_no`，
  直接喂给 `scheduleRefusalSentence` 会把"地点在别的城市"念成"这一项的时间对不上"——错归因比一句空话更坏。
- 测试 `backend/tests/test_cmdr_city_refusal_names_the_row_r1.py` 三条：`:119` 候选 id 那一处点名，
  `:137` 把同一行放回本城就不该再被"错城市"拒（判别对照臂），`:150` 走 research-lead canonical 那一处也必须点名。

### 11.4 读数（现取，不是复述）

- 三条新臂与既有 `test_qoder_schedule_refusal_names_the_row_r1.py` 五条一起跑：**8 passed**
  （解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`，pytest 8.4.2，CPython 3.12.14；
  命令 `cd backend && python -m pytest tests/test_cmdr_city_refusal_names_the_row_r1.py tests/test_qoder_schedule_refusal_names_the_row_r1.py -q`；
  先 `--collect-only` 数到 3 条才跑）。
- 判别性：把 `goal_preparation.py` 退回 `HEAD` 那版、测试不动，重跑同样三条 → **2 failed, 1 passed**，
  红在 `KeyError: 'reason_code'` 与 `TypeError: 'NoneType' object is not subscriptable`，即"点名"这两格确实靠新代码才成立。
  跑完把改动原样写回，`git diff --numstat` 读回 32/2，与提交前一致。
- `uv sync` 那次在这棵树里落了个 168K 的 `backend/.venv`（不是既有环境），已删除，树恢复原状。
- 两把尺重跑不改：`RAW_ERROR_SINKS 0 files_checked=17`、`COLLISIONS 0`（308 支臂、226 枚字面截图名）。

### 11.5 我提交了一次"半条改动"，以及那把假绿的类型闸（自报）

`e351f5089c` 里那枚 `DraftDepartureCard.tsx` 是**半成品**：两处 catch 已经在调 `refusalReason` 和
`placeCityRefusalSentence`，但 `refusalReason` 的定义与 import 都不在文件里——我在提交前对同一枚文件做了四次编辑，
另有一个写者也在写它，落进提交的是拼起来的半条改动。后果不是"不好看"：那句引用在未定义标识符上，
旅客一旦真触发保存被拒，卡片会当场抛 ReferenceError。

更该记的是**我为什么没自己发现**：我跑的 `npm run typecheck` 用的是 `frontend/tsconfig.check.json:16` 的 `include`——
只有 5 枚具名文件，既不含 `DraftDepartureCard.tsx`，也不含 `departureGaps.ts`。那次"clean"对我改的文件什么都没说，
而我把它当成证据写进了上一条提交信息里。CI 的 `Typecheck current V3 product` 步骤用的也是这枚窄配置，
所以门禁同样看不见这类问题（这与"吞掉判语的尺比哑尺更坏"是同一族）。

修好的读法：宽配置 `frontend/tsconfig.typecheck.json`（`include = src/**/*.ts, src/**/*.tsx`）跑全树
`npx tsc -p tsconfig.typecheck.json --noEmit`，输出 0 行、退出码 `0`（退出码写在重定向之后读，不经管道，
以免被 `head` 吃掉）。修复提交 `5182018dab`，推送后 `git ls-remote` 回读枝尖逐位相同。
半条改动那版没在真栈上被按到过（干净树跑的是 `E:/_cmdr_clean_1028` 那一代，不含这次改动），
所以旅客侧没有暴露窗口——这是运气，不是流程有效。

没有做、且要点名的两件：
1. 把 `tsconfig.check.json` 扩到这两枚文件（或让 CI 那步改跑宽配置）。我没顺手做，因为这枚配置是别人正在写的表面，
   扩进去可能把别人已有的红一起变成我的红；这一条要主人点头或由那枚文件的写者自己改。
2. 新句子的**屏上**证词。真机跑的 vite 服务的是干净工作树那一代，要看到新句子得把那棵树推到本代并重启后端；
   我没有重启——在跑的后端环境里带着地图键，重启会把它丢掉，而这个会话不能打印也不能重写那枚键。
   所以 §11.3 那句新文案目前只有代码与后端 details 两级证据，屏证待补（下一条命令：
   `git -C E:/_cmdr_clean_1028 checkout <本代> -- backend/app/agent/goal_preparation.py frontend/src/trial/mobile/DraftDepartureCard.tsx frontend/src/trial/mobile/departureGaps.ts`
   之后按原环境重启 :60362，再跑 bf 臂按到那一格读句子）。

### 11.6 顺手量到的两条别的fact（不改口径，只落账）

- `journey_missions` 才是任务行的落处：库里根本没有 `agent_goal_tasks` / `agent_artifacts` 这两张表
  （`pragma table_info` 现读为空表），我在第一次探库里先猜了列名 `destination_json` 并撞上 `no such column`，
  随后改成先摊 `pragma table_info` 再查——猜列名会印出一张假 n/a 的表。
- 行程与地点两边都用 `CN-RV-<12 位十六进制>` 这种随机城市池码；同一座真城市（北京）在库里可以同时挂在多枚池码下
  （现读 48 / 30 / 24 三堆），`amap_region.adcode=110000` 与 `research_places[].adcode=110101` 是真的，
  但城市码这一层与 adcode 没有可比性。这就是 10-25 那条"城市池 adcode 缺口"今天换了一种伤法：
  它不再是"读不到城市"，而是"读到了一个别的城市池的同一处地方"。
