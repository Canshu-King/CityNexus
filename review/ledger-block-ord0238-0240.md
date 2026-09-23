### 🇬🇧 e345b9d6（SESSION=e345b9d6）ORD-0238 + ORD-0240 交付：把"她说了什么 / 系统存了什么 / 系统真的按什么规划"钉成三格各有读数；节奏只做定位、不硬映 enum；模型原文挪进「技术详情」并标归属 @2026-09-23 12:5x+08 → **`b4ee4f8`**（父 **`2ab69f2`**，含 `a1cc0c1` 在其祖先链）

#### ① 压轴验收：三层真值分开钉（仲裁 03:29 那句"任一格没读数就不许写已修"，我照这条写）

| 层 | 门里真正被断言的东西 | 现场读数（我自己的门跑出来的，不是转述） |
| --- | --- | --- |
| **L1 她说了什么** | 确认页必须把她按的 chips **原样**回显 | `ord0238-1` GREEN：`美食、亲子` 与 `紧凑` 两句**逐字符等值**，字面量存在门里（**不 import 产品常量**，ORD-0226 那条教训照用） |
| **L2 系统存了什么** | 行程建好之后，服务器 `GET /travelers/{id}/preferences` 里必须有她勾的那两行 | `ord0238-2` GREEN ⇒ 实测两行 `{category:"interest", key:"food", value:true, weight:0.5}` 与同形 `key:"family"`（`layer2-stored-preference-rows.json`，journey `57c63ccb-ad39-4026-9a5b-2e8a022f6413` / traveler `f984e04b-baa7-4303-9636-faaace6ebd57`）。**只断言 `0.5/true`**：投影里没有 `source` 字段，权重是产品常量"说了、未排序"，不是她给的排序 |
| **L3 系统真的按什么规划** | 方案标题**只能声称规划器真拿了的输入** | `ord0238-3` GREEN：新句 `我们按这座城可核验的地点和你的预算，生成了 2 个可选方案。`，断言里逐字禁止出现 节奏 / 兴趣 / pace / interest（`:211`）；另加一次黑盒探针（有 interest 行 vs 无任何偏好行，各打一次真端点）⇒ **`verdict = INCONCLUSIVE(refused=VALIDATION_ERROR/VALIDATION_ERROR)`**（两臂都 422，没产出就没法比较） |

**没修的那一半我写清楚，不拿 L2 冒充 L3**：把她说的话存进契约早就定义的 KV 行 ≠ 规划开始读它。`generate_plans(session, journey, planning_mode, candidate_count, place_ids)`（`backend/app/services.py:1417`）**不读任何 traveler_preferences 行**——这一格是后端消费者缺口，不在我写域；L3 我签的是"标题不再越权"，**没有**签"规划按兴趣"。

写侧三条契约约束照守：`PUT /travelers/{id}/preferences` 是**整表替换**、重复键 422 ⇒ 新档 `src/api/travelerPreferences.ts` 的 `syncStatedInterests()` 先 `GET` 现状、把**所有非 interest 行原样带回**、再 PUT 并集、再读回确认；调用点在 `V8Experience.tsx` 的 `createJourney` 里行程 POST 之后，用 `try/catch` 吞失败（注释写明为什么不能把一次偏好同步失败说成"行程没建成"），不阻塞建行程。

#### ② ORD-0238(b)：节奏只做定位（六个读数，一个字不猜）

```text
前端词表：frontend/src/features/setup/JourneyTrialSetup.tsx:244-248  PACE_OPTIONS = relaxed | balanced | packed
后端词表：backend/app/schemas.py:12                                    PlanningMode = balanced | budget | explore | strict_schedule
⇒ 两张表只共享 "balanced" 这一个字符串。把它读成"对得上"就是仲裁点名的那个坑（把丢数据 bug 换成语义猜测 bug），
   所以**我没有把 relaxed/packed 映成 planning_mode**：创建请求里的 planning_mode 仍走它自己的控件，节奏 chips 不进那个字段。

"pace 现在是否存在任何请求体或表列？" —— 三条实测（用 -w，把命中的行本身印出来，不写"已确认没有"）：
  contracts/openapi.yaml            grep -w pace = 0 行
  backend/app/db/models.py          grep -w pace = 0 行
  backend/app/**/*.py               grep -rnw pace = 4 行，全部在 capabilities.py（:220 与 :642 是注释；
                                    :237 是一份 token 表里的 "slow pace"；:874 从自由文本认 慢一点/慢速/slow pace/take it slowly）

"服务端有没有可承接字段？" —— **有存储、没有字段**：
  data/mock/traveler_demo.json:12 已经有一行 {"category":"pace","key":"relaxed","value":true,"weight":0.7}
    ⇒ 通用 KV 装得下节奏；
  但 :874 那一条消费者读的是 extract_capabilities_from_text(...) 三个调用点传进去的**话语文本**
    （agent/mission.py:240 的 command、ai/copilot_contract.py:497 与 ai/semantic_compiler.py:327 的 message），
    **没有任何一处读 traveler_preferences 的行**（三条调用点即全部调用点）。
⇒ 结论按单子明写：**"节奏接上规划器"需要后端字段或后端消费者**，请你拆单；我这边只落了"标题不再谎称按节奏规划"（=L3）。
   顺带一条不是我决定的事实：她**打字的**那句话今天已经能被 :874 消费，所以"话进系统"与"chip 进系统"是两条不同的路。
```

#### ③ ORD-0240：先定位，再选"留着原文但标明是谁的话"（四件逐条）

**定位（改之前就量到的通路）**：那句话从 `PlanWithAiSheet.tsx` 的 `result.summary` 直接进 DOM——旧代码就是一行 `<p className="plan-ai-summary">{result.summary}</p>`（改前 `:818`）；`result.summary` 是 AI 规划**响应体字段**，**从未进过 i18n**：整句在 `frontend/src/` **0 命中**，在 `src/i18n/` 的三个文件（`LocaleContext.tsx` / `travelerLabels.ts` / `tripOperations.ts`）**0 命中**。

- **① 中文 locale 屏上不得出现未标注的英文模型句** ⇒ `ord0240-1` GREEN：主文案区（两层扫描里"看得到"那一层）不含 `Detected hard constraints`。
- **② 技术详情里展示原文必须带标签** ⇒ `ord0240-2` GREEN：`plan-ai-model-output` 之前必须有 `plan-ai-model-label`，标签文字逐字符是 `模型原始输出（未翻译，不代表本界面的结论）`（`model-output-labelled-reading.json`）。
- **③ 反向突变：把英文串塞回渲染路径 ⇒ 门必须红** ⇒ `killD4` 做到了（红集 `[ord0240-1, ord0240-3]`）；另 `killD5` 只撕掉标签 ⇒ 只有 `ord0240-2` 红；`killD6` 把 `details` 默认展开 ⇒ 只有 `ord0240-3` 红。
- **④ 不许把这句加进翻译表冒充"已翻"** ⇒ 0 命中（上面已印清单与命中数）。表里新增的只有标签与结构句；动态模型散文**不进**任何字典。
- 形状上的取舍：我没有"翻成中文"（翻一句没有源语言的自由散文=再造一次未标注内容），而是把它挪进 `技术详情` 的 `details` 里并标归属；服务器给的拒绝码仍走它自己的 `plan-ai-detail-kind` + `plan-ai-reason`，两类文字各带各的标签。

#### ④ 六臂矩阵：**6/6 KILLED**、`anchor_hits=1 / bytes_changed=True / restored_exact=True` 六中、`treeUnchangedByThisRun=True`、`invalidStackArms=[]`

```text
killD1 review-drops-what-she-picked  红集 [ord0238-1]                独占
killD2 interests-never-reach-server  红集 [ord0238-2]                独占
killD3 headline-claims-pace-again    红集 [ord0238-3]                独占
killD4 model-words-back-in-main-flow 红集 [ord0240-1, ord0240-3]     ← 共享，见下面那段，我自首
killD5 model-words-unlabelled        红集 [ord0240-2]                独占
killD6 disclosure-open-by-default    红集 [ord0240-3]                独占
每臂之前重跑 owner spec 整文件基线：6 次基线各 `4 passed`（3 节点 + `real-seed` setup project 那一格，运行形状就是这么报的）；
每臂之后再跑一次"同一突变 × 另一个文件"的镜像跑：6 次镜像全部 `4 passed` ⇒ 两个 spec 互不依赖，没有一条尺管两边。
守卫 = live_checks/mutation_anchor_guard.py :: temporary_guarded_replace（还原后按 sha256 复核，不是按"看起来一样"）
```

**`ord0240-1` 的 `exclusiveKiller` 是 `[]`，这一格我不粉饰**：`killD4` 把英文句挪回正文，同时破坏了"正文干净"（1）与"关闭的 `details` 里的文字才算不上屏"（3）——**同一条不变量的两端**，所以一次突变红两格。要拆成两条独占杀手，我能想到的两种写法（只加标签不回正文 / 只回正文不加标签）已经分别是 D5 与 D4；再硬造只会得到一条同义突变。**是否要求每格独占，请裁定**；若要求，我按你给的判据补，不自己发明判据。

#### ⑤ 回归读数与代次坐标

- `npx tsc -p tsconfig.check.json --noEmit` ⇒ **exit 0**；`npx tsc -p tsconfig.typecheck.json --noEmit` ⇒ **exit 0**（12:3x 重跑，跑在**已提交字节**上：`git status --short -- frontend/src` = **0 行**；日志 `review/tsc_b4ee4f8.log`）。
- 新档节点数：`qoder-stated-versus-stored-versus-planned.spec.ts` = **3** 个 `test(`、`qoder-model-words-are-labelled.spec.ts` = **3** 个。
- **代次自证**（因为门跑在 commit 之前，收据里 `head` 写的是父尖 `c40097c`）：收据 `filesAfter` 的四个文件 sha256 与 `git show b4ee4f8:<path>` **逐一相等**——`JourneyTrialSetup.tsx f88b41e5ade5d96b…`、`V8Experience.tsx 753e0e38bbf05a83…`、`PlanComparison.tsx 406d613bcd217f35…`、`PlanWithAiSheet.tsx abc0515d397f6271…` ⇒ 被判绿的字节就是我交付的字节。
- **STALE_SURFACE 重测**（预览链第四次重建之后，本机钟 12:04+08）：服务中包 `assets/index-DtQ86lsQ.js`，**按内容**自证 sha256 `cf3a08108ffba413fca1e67c90e10e8d9428070899c6bdbcd36ab283a13c443a` / 1,231,985 B，与盘上 `D:/moodle/_qoder_preview_20260920/dist` 那一份**逐字节同一** ⇒ 代次**没换**，所以旧读数是"同一代上的旧读数"而不是错代读数。三格重读：ORD-0220③/0222① 被拦提示 `还需要填写：总预算` 在 **150 ms** 时已进视口（`scrollAt150=652`、`inViewport=True`、`opacity=1`、`scroll-behavior` html/body 均 `auto`、`stickyAncestor=False`），补完后退到 `''`；ORD-0216④ 入口标签 `使用封存的演示行程`、向导屏不再提城市；只读保证 `blockedWrites=[]`、`creationPostsAttempted=0`（`preview-chain-recheck-after-rebuild.json`）。
- **你 12:1x 那块 ④ 拦住换代的事实，此刻解除了**：`git status --porcelain -- frontend/src` = **0 行**（tip `b4ee4f8`）。我可以随时按 `git archive` 出干净导出树给你构建；我没有碰 `:4781` 正在服务的那份 dist，也没有新建隧道。

#### ⑥ 我这一轮的仪器错误（五条，全修在门里，没削任何断言）

1. **第一版归属不独占**：一条突变红多格。修法是把"上屏"这一主张挪到真正拥有它的节点、把 D3 收窄到 fallback 通路，并补 D6（默认展开）当第 6 把杀手——不是把断言放松。
2. **空对空的绿（这一条最险）**：0240 的门第一次跑，stub 落在 `BLOCKED:CATALOG_EMPTY` 那一屏，于是"英文不在屏上"是**测了个不存在的界面**通过的。补了正控（目录 stub 让城市有数据、路由计数器证明 stub 真开火、`/plans` 排序：基线 0 方案 → 一次 1 个真候选）之后才让它先红后绿；`sentenceHomes()` 那格诊断是为此加的，不是装饰。
3. **`getAttribute("open")` 拿到 `""`**：`<details open>` 的属性值是空串，falsy ⇒ 我把"默认展开"读成"没展开"，`ord0240-2` 在 `ord0240-3` 的突变下假红。改 `hasAttribute("open")`。
4. **`PlanComparison.tsx:82` 在没有 CANDIDATE 方案时 `return null`**：我曾把"标题不含节奏字样"当绿，其实那块根本没渲染；同一次调试里一个 `page.goto` 又把 onboarding 向导弹开（`setupOpen:true`），靶子换了。分别用真候选行、去掉 reload、并在路由注册之后再导航修掉。
5. **`expect(locator).toHaveCount(0)` 在路由拦截下会挂到超时**：换成 `expect.poll(() => count()).toBe(0)`；同理 `innerText()` 之前必须有节点名的 `toBeVisible({timeout:20_000})` 兜住，否则一次判错要吃满 300 s。

#### ⑦ 证据面（9 件已发布 `Canshu-King/CityNexus @ commander/control / evidence/ord0238/`，每件 201 + BYTE-LEVEL MATCH；下面 sha1 是这 9 个字节此刻用 `git hash-object` 重算出来的，不是抄我自己的话）

```text
f6093002430afd2e  MANIFEST.txt                              997 B
b12125f4d02fea78  b4ee4f8__b4ee4f8.patch                 48,136 B  sha256 c7df9d4708882a11…
dfaef7f3f3469633  b4ee4f8__changed-files.txt                468 B  sha256 450842389d69f90f…
f9cba7e670007c4d  b4ee4f8__source-and-parent.txt            694 B  sha256 eadcc0c57832deb8…   ← 重试后才拿到 MATCH
b1034812c6ea7b87  layer2-stored-preference-rows.json        882 B  sha256 4344a1a4e2fc541d…   ← 重试后才拿到 MATCH
86e014db4c57a078  layer3-planner-input-probe.json           877 B  sha256 e899783238bbca86…
b6ab672365f0ac98  model-output-labelled-reading.json        492 B  sha256 94e2bb634da12bb8…
5929c5dbf44e55bf  mutation-receipts.json                 14,790 B  sha256 c883a8e4063be490…
c6d114a1cb8ab825  preview-chain-recheck-after-rebuild.json 4,365 B  sha256 d0ce65f921ab4713…
```
两件第一次报 `MISMATCH after retries`（SSL `UNEXPECTED_EOF` 吃掉了回读，没吃掉 PUT），第二次跑读回 `already identical` + BYTE-LEVEL MATCH ⇒ 坐标以上表为准。六臂原始收据另存 `review/evidence/ui-overnight/ord0238-0240-arms-six-arms-v2.json`（驱动 `review/ord0238_0240_kill_arms.py`，已随 `b4ee4f8` 进仓）。

#### ⑧ 仍挂着的 / 下一步

- **ORD-0232 端到端那一格仍是 `BLOCKED_ON_MERGE(a96fabf)`**（#68）：`a96fabf` 只在 `agent/canary-ord198-20260922` 上，我不并别人的分支；可跑件 `review/ord0232_e2e_replay.py` 实测 `REPLAY_EXIT=7 STATUS: BLOCKED_ON_MERGE`，合流后一条命令就出收据。渲染那一半（`8f42cb7`）四格四把独占杀手已经收了。
- **ORD-0246 / ORD-0247 我已读到**（11:2x 那块），归我，顺序排在本单收口之后：
  - 0246：`submit()` 里要的是**同步重入门**（React 提交之前就拒第二击），不是 `disabled={busy}` 那种渲染态；判据 = 同 tick 两击 ⇒ 1 POST / 1 行，并且必须有一臂把门挪回渲染态、把它杀红，收据按 `CNX_REVERSE_MUTATION_RECEIPT_V1`。aad2d1f2 已经备好同口径尺（今天量到的是 2 POST / 2 行、`b.disabled` 三段全 false）——那是**它的读数**，我会自己复现，不拿它的绿当我的绿。
  - 0247：`<summary>`（"高级：结构化数据"）命中框 311×14 px，移动端 44px 这条要过；判据 = `elementFromPoint` 命中的**就是该控件本身**（我在 ORD-0248 那条第 10 下见过的反面教材：只拿到"父容器命中 + 后果"不算证）。
- 本轮**没有变好的**：L3 那格 `INCONCLUSIVE` 依旧是 `INCONCLUSIVE`——它不是我的门坏，是规划器在两臂都拒（`VALIDATION_ERROR`）；兴趣/节奏对最终方案的影响，今天仍然没有可读的第二层证据。

`STATUS: ORD-0238-THREE-LAYERS-PINNED-L3-INCONCLUSIVE-BY-DESIGN | ORD-0240-DONE-SIX-ARMS-ONE-SHARED-KILLER-SELF-REPORTED | files frontend/src/{api/travelerPreferences.ts(新),app/V8Experience.tsx,features/planning/PlanComparison.tsx,features/planning/PlanWithAiSheet.tsx}+frontend/e2e/{qoder-stated-versus-stored-versus-planned.spec.ts(新),qoder-model-words-are-labelled.spec.ts(新),_qoderTextScan.ts}+review/ord0238_0240_kill_arms.py(新)；**backend/ 0 个文件、JourneyTrialSetup.tsx 本轮只读未改** | tests tsc 两配置 exit 0 ＋ 两 spec 各 3 节点（基线各 4 passed）＋ 六臂 6/6 KILLED、镜像 6/6 独立、restored_exact 六中 | blocker 有（两条具名：`generate_plans` 不读偏好 ⇒ L3 只能 INCONCLUSIVE；`a96fabf` 未合流 ⇒ ORD-0232 端到端仍 BLOCKED）| writes 全在我自己的 `_run<id>.db`，预览台只读（`blockedWrites=[]`、`creationPostsAttempted=0`）；`:4781` 正在服务的 dist、`_live.db`/`_preview.db`、B 的 spike 树一字节未动；公网 0 写；未 `demo/reset` | evidence 上列 9 blob + 本节`

**插入收据（本脚本当场测）**：写前 `@BYTES_BEFORE@` B、纯 LF（`CRLF=@CRLF_BEFORE@`）、`sha256` 前 16 位 `@SHA_BEFORE@`（本机钟 `@NOW@`）；`## ORDERS（收件箱` 全文唯一（`count=@ANCHOR_BEFORE@`）、切点 `@CUT_BEFORE@`；我的块 `@BLOCK_BYTES@` B。写后回读：块出现 `@BLOCK_COUNT@` 次、锚点 `@ANCHOR_AFTER@` 份、**把我的区域整段拿掉是否与写前逐字节相同** = `@ROUNDTRIP@`、写后 `@BYTES_AFTER@` B / sha256 前 16 `@SHA_AFTER@` / 锚点切点回到 `@CUT_AFTER@`。文件别人在续写，所以我只对「我这一段可逆」负责。
