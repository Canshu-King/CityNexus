# HJ-P2 第二份读数 · 北京（唯一有地点数据的城市）· finding `d4b04a0f/02`

- 车道：HJ-P2 承诺密集型旅行者（SESSION `d4b04a0f`）；时间 2026-09-22 19:31–19:47（+08）
- 产物归属：**线上同一支产物** `index-BCF4ptyk.js`（sha256 `f3bda3d6…51d0e9`，1,230,082 B）。我用本车道自起的
  `vite preview :8493 --outDir <部署 dist>` 供它，后端 = 本车道 uvicorn `:8453` 读**我自己的一次性副本库**。
  ⇒ 手机看到的字节与我校验的字节同一支；写只进我的副本。
- AI 臂：本车道 `GET /api/v1/agent/runtime-status` → **`deepseek_configured: true`**（抽屉印「这台服务已接入 AI 模型。」`data-ai-state=ready`）。
  **这是与第一份读数不同的臂**（r6 是 `unconfigured` 臂），两条不互相覆盖。
- 走法：全部真人点击 + 屏上读数；API 只用于 3 次只读 `GET` 与收尾的行级复验，**没有用 API 造任何成功**。

---

## 1. 这一轮走通的部分（先把好消息说清）

```text
新建行程 → 目的地「北京」→ 屏上立刻回显「已自动设置：中国 · 人民币 · 中国标准时间」，
  字段标题变成「抵达北京 / 离开北京」→ 下一步 → 人数与偏好（默认值仍标「我们替你填的」）→
  确认创建 → 枢纽「北京之旅 9月23日 10:00 — 9月25日 20:00 · 2 位旅行者 · 3 天」
AI 抽屉 → 输入 43 字（含两笔"已订"）→「开始规划」由 disabled=true 变可点 → 点
  → POST /journeys/5e9fd913…/agent/commands   200（mission d9812c58…）
  → POST /journeys/5e9fd913…/plans/generate   201
  → 枢纽印出逐日预览（3 天、7 段路程、住宿候选）
```
副本库行级读数（`mode=ro`，全在 `beijing_chain_r7.json`）：

```text
journeys.city_code = CN-BEIJING（这一次是对上的，北京在 CITY_FACTS 里）
plan_versions 本趟 3 条：version_no 1/2/3，全部 status=CANDIDATE、source=INITIAL
  成本 49000 / 49000 / 45000 minor，utility 0.9298 / 0.9356 / 0.9312
activities 跨这 3 条方案 = 23 条
journeys.active_plan_version_id = None    journeys.status = DRAFT
```
⇒ **方案生成这一环在北京是通的**（第一份读数里 `plan_versions` 恒 19 是因为我选的两座城没有 place 行，不是规划器坏了）。

## 2. finding `d4b04a0f/02`：三条候选方案都生成了，**屏幕上没有"选定"这条路**，而工作台说"还没有可看的行程"

| 位置 | 屏上原文 | 服务端事实 |
|---|---|---|
| 枢纽（今天） | 「方案概览 / **以下只是其中一个候选方案的预览，你还没有采用它。**」+ 3 天逐日卡 | 3 条 `CANDIDATE` 已落库 |
| 行程工作台 `/v8/trips` 的「行程」页 | 大标题「**还没有可看的行程**」+「这个行程还没有选定的方案。**先让 AI 帮你规划**，选定方案后这里会显示逐日安排。」+ 唯一 CTA「AI 帮我规划」 | 行程存在、3 条方案存在、23 条活动存在 |
| 点日卡（第 1 天）之后 | 仍是同一句「你还没有采用它」 | — |

- **走过的 3 个界面上，含"采用/选定/激活/生效"字样的可见控件 = 0 个**（探针：`button,[role=button],a` 且 rect 可见，按渲染文字匹配）。
- 服务端**有**这条路：`openapi.json` 139 条路径里 `POST /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select`（另有 `…/stay-options/{option_id}/select`）。
- 判类 **`HUMAN_BLOCKER` + `HUMAN_MISLEADING`**：
  1. 「还没有可看的行程」在"有行程、有 3 条方案"的时候印出来，是**假空态**（与我第一轮报的「我的」屏同一形状，新界面）；
  2. 它给的唯一出路是"先让 AI 帮你规划"——**这一步我刚做完并且成功了**（201 + 3 条 CANDIDATE）。照它说的做只会回到同一屏，形成闭环死路；
  3. 结果：承诺密集人设的整条后续链（开始执行 → 推进活动 → 中断 → 重规划 → 接受方案）**在这条自建行程上无法开始**，因为 `active_plan_version_id=None`、`status=DRAFT`，而界面不给选定入口。
- **分母要说全（不许把没查的算成没有）**：我只走了 枢纽、`/v8/trips` 的「行程」页、日卡三处。
  **没走**：`/v8/trips` 的住宿/预订/花费页、实时行程、地图、Copilot、恢复与执行、旅行者画像、城市探索、旅行票夹、行程工作台（枢纽那个按钮被 AI 抽屉遮罩挡住，我的探针如实报了 `COVERED_BY:TEXTAREA`，没算成"点过了"）。
  ⇒ 结论口径是「**这三处没有选定入口**」，不是「全产品没有」。

## 3. finding `d4b04a0f/03`（对承诺密集人设最要命的一条）：0 条承诺的行程，方案上印着「承诺保全 0.98」

```text
我在那 43 个字里明说了两笔已经发生的事实：
  「第二天上午必须去故宫，门票已经买好了，不能改时间」
  「晚上和朋友在后海吃饭，位子已经订好」
落库结果（本趟）：commitments = 0 行，constraints = 0 行，wallet = {"reservations":[],"commitments":[]}
而三条候选方案的 score_breakdown 里：commitment_preservation = 0.98 / 0.98 / 0.98
```
⇒ **一个"承诺保全"分数在没有任何承诺可保全的行程上被算出并展示**（0.98 不是 1.0，说明它不是"空集恒真"的写法，而是拿别的东西打了分——具体拿什么我没测，不猜）。
对承诺密集型旅行者，这是**信任反转**：产品用"承诺保全"这个措辞告诉用户"你的既定安排被照顾了"，而它其实一条都没登记。
判类 **`TRUTH_DEFECT` + `HUMAN_MISLEADING`**。
最小判据（不猜实现）：`commitments=0` 时该维度不得渲染成"承诺保全 0.98"这类肯定式分数——要么显示"本趟还没有承诺"，要么不参与评分；
反例门：造一条无承诺行程 → 生成方案 → 断言屏上不出现承诺保全的肯定式读数。

## 4. 顺带记下的两条（同屏可见，不另立 finding）

- **`TRANSIT STAY锚点` / `BICYCLE ARRIVAL锚点` / `AUTO DEPARTURE锚点` 仍在直印**，日卡里还有 `Wednesday`、`Check in`、`Overnight`、英文景点名混排 ⇒ 与 **ORD-0222**（号令者 19:00 亲测、`e345b9d6` 的续单）同向，我这条是**第三个独立界面读数**（产物 `BCF4ptyk`，我自己副本库、我自己的 profile，无跨道因素）。
- 「底图未加载，显示的是路线示意。」——离线时这句是**诚实的**，记功；`执行游标 ABSENT` 那句也已成人话（ORD-0208 ① 复验第二次）。

## 5. 写隔离（收尾复验，行级）

```text
我的副本  走查后：journeys 6（+北京 5e9fd913…）、plan_versions 22（+3，全在我这趟名下）、travelers 6
线上库    _live.db  ：journeys 3 / travelers 3 / plan_versions 19 / commitments 1  —— 与本轮开始前逐项相同
                     我这趟 id 命中 0；三个库主文件 stat 探测前后未变（只读）
另一共享库 _preview.db：31 / 45 / 9 未变，命中 0
收尾：:8453 与 :8493 监听数 0（先按命令行逐条认出 PID 4396=我的 uvicorn、24632=我的 vite 才终止）
      权威树 `git status --porcelain | grep -c hjp2` = 0
禁令自查：没按「重置到场景起点」；没写任何共享库；没新建隧道；没占 :4781/:4782/:8693；没上传 .db/凭据。
```

## 6. 坐标（`EXTERNALLY_READABLE_EVIDENCE`）

见同目录 `manifest_r7b.json`：本文件、`beijing_chain_r7.json`、`r7_07_workbench.png`（假空态那一屏）、`r7_09_daycard.png`（枢纽"你还没有采用它"那一屏）、`openapi_plan_lifecycle_paths.json`，
每件都给 git blob sha1 + 发布 commit + 逐字节回读结果。
`LOCAL-ONLY, no resolvable coordinate`：工作树尖（本地未 push）、我的副本库（禁载物）、隧道 URL（重启换名）——耐久坐标是那支产物的 sha256。
