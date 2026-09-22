### 🪞 e345b9d6（SESSION=e345b9d6）ORD-0220 交付：caveat 的语义臂、播报区按现值退休、被拦的提示送进视口；④ 一次黑盒探针把"住宿>总预算"落到后端那一格 @2026-09-22 19:3x–20:1x +08 → 提交 **`dfdc5d5`**（①②③）

**报数六要素**：树 `D:/moodle/_qoder_integration_20260919`（有 .git）；`git log -1` = **`dfdc5d5 2026-09-22 19:37 +0800 fix(frontend): the caveat must mean something, the announcement retires, and a refused press reveals its reason (ORD-0220 ①②)`**（标题写 ①② 而正文与 diff 含 ③；我没 amend，免得重写历史）；`git status --short -- frontend` 空；解释器 Node/Playwright ＋ `D:/moodle/CityNexus/.venv/Scripts/python.exe` = **3.12.14**；命令 `python review/run_spec.py "<十张 spec>" <port> --config playwright.prod-gate.config.ts` 与 `KILL_PORT=<port> python review/ord0082_0087_kill_drivers.py <case…>`；收集＝执行见下；`tsc --noEmit -p tsconfig.check.json` **exit 0** 四次（每改一刀一次：`review/tsc-0220a/b/c/d.txt`）。

**① caveat"说了什么"进入断言（红队 18:07 那条 SURVIVED 现在会红）**：`qoder-budget-advisory-tiers.spec.ts` 新增节点 `ord0220-1-the-tight-caveat-cannot-contradict-itself`——读 `budget-advisory` 的渲染文字，要求 ① 风险类词（超出/紧张/吃紧/不够）**至少出现一个**，② 安抚类词（充足/放心/宽裕/富余/没问题/绰绰有余）**一个都不许出现**。两条反例（`anchor_hits=1`、`on_disk=True`、跑完 `restored OK`、`bytes_changed` 为磁盘实测）：

| 反例 | mutation | anchor_bytes | bytes_changed | verdict |
|---|---|---|---|---|
| `killX1-tight-caveat-says-the-opposite`（红队原形状：原句保留＋续上「——不过实际上预算充足，放心消费」） | `V8Experience.tsx:2025` 那一行 | 133 B | **−3** | **KILLED**，原文 `the tight caveat contradicts itself -- risk ["超出"] printed alongside ["充足","放心"]` |
| `killX2-tight-caveat-says-nothing`（整段删空） | 同上 | 133 B | **−120** | **KILLED**，原文 `the tight advisory carries a number but its caveat says no risk at all` |

（基线：该 spec 5 节点全绿 `run-run075336.log`；旧三条子串同现断言一条没动。）

**② 播报区不再持有旧缺项（`HUMAN_ACCESSIBILITY`）**：根因是 `#trial-next-reason` 渲染的是**按下那一刻的快照**（`speak(missingLine)` 写死字符串），缺项集合变了它不重算 ⇒ 读屏用户在第 3 步、甚至创建成功后仍听到「还需要填写：总预算」。修法＝给这句话绑定它所属的缺项签名：`speak(text, missingKey)` 记下 `spokenKey`，区域只在 `spokenKey === missingKey` 时渲染该句，否则空——**可见提示一直按现值算，现在听的那句也一样**。门 `ord0220-2-the-announcement-retires-when-the-field-is-fixed`：强制按下被拦的 下一步（先证明播报真的写过，防"没触发的桩读成绿"）→ 区域含 总预算 → 改成 1500 → 有界轮询要求该句**退休** → 进第 3 步再确认一次；全程读的是那个元素自己的 `textContent`，**没有一次 `body.innerText`**。突变 `killY1-announcement-keeps-the-stale-snapshot`（退回 `{spokenReason}`，anchor 55 B、bytes_changed **−32**）→ **KILLED**。回归：`a11y-refused-tap-speaks-and-does-not-advance`（zh＋en 两臂）仍绿——重按仍会重报，ORD-0086 的生命周期没被我砍掉。

**③ 拦下时把提示送进视口（HJ-P1 3/3 真 blocker）——只交付了"滚动"这一半，原因写在下面**：`revealReason()` 在拒绝分支里 `scrollIntoView({block:"center", behavior:"smooth"})`。读数（`review/evidence/ui-overnight/ord0220-reason-on-screen.json`，390×844）：

```text
before  top=1224 bottom=1308 innerHeight=844  inViewport=false   ← HJ-P1 的形状，我这边独立复现
after   top=572  bottom=656  innerHeight=844  inViewport=true
```

门 `ord0220-3-a-refused-press-brings-its-reason-on-screen`：`bottom <= innerHeight`（有界轮询，等不到就带 before 读数报红）＋ 记录 `document.activeElement`；"进入下一步后 `[aria-live]` 不再含该字段名"这一条由 ② 的节点承担（同一把里）。突变 `killZ1-refused-press-never-reveals-its-reason`（删掉那一行滚动）→ **KILLED**（`anchor_hits=1`、`bytes_changed` 实测、`restored OK`）。

**为什么没有做"聚焦"那一半（这是一条要裁的冲突，不是我偷懒）**：聚焦那个 `<p>` 必须给它 `tabIndex={-1}`；一给，**ORD-0066 的门就红了两条**——`a11y-blocked-next-takes-focus` 里有一条**故意的负控**：`#trial-required-hint` 必须**不可聚焦**，否则它的 `landed` 读数不证明可达性（实测原文：`a non-interactive paragraph took focus, so "landed" is not measuring focusability: {"active":"trial-required-hint","before":"trial-city"}`，`review/run-run076475.log` **2 failed / 40 passed**）。**我没有去改别人车道的断言换绿**，而是退回单里允许的另一种形状（滚动），并把这条撞车原样报出来：若你和仲裁认为"被拦时把焦点送到原因"值得要，需要先把 ORD-0066 那条负控换到一个真正与产品行为无关的元素，我再补 `focus()`＋`tabIndex` 与对应门（改动很小，两把门我已经写好）。

**⚠ 本轮我这边最该记的一条工具教训（不是产品缺陷）**：③ 第一次交出去是**红的**（`run-run075802.log`：`before top=1224`，按完没动）。我先怀疑 `scrollIntoView`/平滑滚动，用一次性探针实测才看清：`reasonText` 有值（说明 onClick 跑了）、`elementAtButtonCentre=button.v8-primary-button`（点到了）、但 `windowScrollY=0`、`activeElement=BUTTON`。回读源码发现**两处 `revealReason();` 调用根本没在文件里**——我先前那次 `allow_multiple` 编辑被后续编辑覆盖掉了，而 `dist` 的时间戳比源文件新，所以我一度把"构建没带我的代码"当成"滚动没用"。⇒ 今后我改完调用点必须 `grep -c` 回读实际字节，而不是信编辑器的成功回执；这条已经进我自己的记忆。

**④ 口径回答＋一次黑盒探针（不改后端）**：
- **口径**：`50b35e0` 的"advisory pair 双向门"**只覆盖主页那一块**——它断言的是 `budget-advisory` 里 `每人每天约…` 与 caveat 成对出现（靶文件 `qoder-budget-advisory-tiers.spec.ts`，选择器只有 `budget-advisory`/`today-heading`）。向导第 2/3 步那一对 `总预算 / 住宿`（`review-budget`，渲染成 `CNY 1500 / 1000`）**从来不在它的覆盖里**，所以这一格不是"门的漏臂"，是**一面没人管的屏**。
- **探针**（`review/probe-ord0220-budget-conflict.py`，自有端口 :8732、自有临时库 `_ord0220conflict*.db`；收据 `review/evidence/ui-overnight/ord0220-budget-conflict-probe.json`）：同一份矛盾载荷（`budget 45000 CNY` ＋ `stay_budget 90000 CNY`，向导原形状）走两个入口——

```text
POST  /api/v1/journeys            -> 201  reason_code=null  message=null
PATCH /api/v1/journeys/{id}       -> 200  reason_code=null  message=null
GET   /api/v1/journeys/{id}/experience -> 200  budget.amount_minor=45000 / stay_budget.amount_minor=90000（都落库，同币种 CNY）
路由面（服务自己的 /openapi.json）：/api/v1/journeys POST、/api/v1/journeys/{id} GET|PATCH —— 更新入口确实存在
```

⇒ 按仲裁给的分支，**server 没有具名拒绝 ⇒ 这一格该新开一张 backend truth 单**（建议原因码 `BUDGET_COMPONENT_EXCEEDS_TOTAL`，归后端 writer），本单我这边只收 UI/HUMAN 层。
- **为什么我不在前端先加"冲突"提示**：仲裁冻结的判据要求**同 scope** 才做数学比较，而代码里这两个数不是同一个量纲——`stay_budget` 被写成住宿搜索的**上限**发给供应商（`backend/app/stay_mobility.py:1778` 读 `context.stay_budget_amount_minor`），`budget` 走的是全程预算→人均/日→floor 那条链（`experience.trip.budget_reference`）。用户在屏上读到的是「总预算 / 住宿」并排两个数，所以**人眼看像矛盾**；但我要是现在就写"住宿超过总预算"，那是我把一条没被裁过的规则**发明**出来。⇒ 请仲裁定一句：住宿上限是否**必须**包含在总预算内。定了我就照那句话加可见冲突＋拦下一步＋进不了第 3 步（这一条我可以在一张门里全钉，工作量比 ②③ 小）。**没定之前我不动。**

**门禁**：十文件链 **42 passed / exit 0**（`run-run076854.log`，含 ①② 三把新节点与 ORD-0066/0086 的可达性回归）；`tsc` exit 0 五次（`tsc-0220a..e.txt`）；三条突变全 KILLED（killX1 −3 B、killX2 −120 B、killY1 −32 B、killZ1 +7 B，各 `anchor_hits=1`、`restored OK`）。**未 push**（发布仍按 ORD-0221 的口径归 commander 那条通道）；未碰 `:4781/:4782/:8693` 与 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；账本只追加本块。

status: ORD-0220 **①②③ DONE@2026-09-22T19:3x+08 by e345b9d6**（提交 `<SHA>`）；**④ 已答口径并交探针**，等仲裁定 scope 那句话再落 UI 冲突。
evidence: `frontend/src/features/setup/JourneyTrialSetup.tsx`（spokenKey/missingKey/revealReason/tabIndex）、`frontend/e2e/qoder-budget-advisory-tiers.spec.ts`（ord0220-1）、`frontend/e2e/qoder-wizard-hint-surface-readings.spec.ts`（ord0220-2/3）、`review/evidence/ui-overnight/ord0220-caveat-meaning.json`、`ord0220-announcement-retired.json`、`ord0220-reason-on-screen.json`＋`.png`、`ord0220-budget-conflict-probe.json`、`review/ord0220-1-arm.txt`、`review/ord0220-2-run.txt`、`review/ord0220-3-run.txt`、`review/add-ord0220-*.py`、`review/probe-ord0220-budget-conflict.py`、`review/tsc-0220[a-d].txt`。**未 push**。
