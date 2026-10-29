# 接班件 · GO-FROM-BLANK 三刀收口后的下一手（2026-10-29 上午）

代次：权威线 `rescue/v3-final-departure-20261022` 现尖 `4f90d7027c0154030013349d78f66b8453a8cb78`
（每笔 push 后都用 `git ls-remote origin <枝>` 回验）。工作树 `D:/moodle/_cmdr_rescue_v3_1022`。
本文件只写"下一手怎么接"，交付事实以账本与两份结果文档为准。

## 一、三刀现状（不要重做）

| 刀 | 状态 | 一手证据 |
| --- | --- | --- |
| 第一刀：真 Chrome 两档从空白走到 ACTIVE | 已交 | 报告 §13.x 与 `trial/results/20261026_gozero/` 的 390/430 屏证；闭同代保留见 #339 |
| 第二刀 2a：可展开的工具时间线 + 来源披露 | 已交 | 产品改动 `frontend/src/trial/mobile/WorkspaceActions.tsx`；两档屏证与只读探针一对一，代次负对照同文件 |
| 第二刀：新旧差异与「费用：未知」 | 分析已交、等裁语 | `trial/results/20261029_COST_UNKNOWN_UNREACHABLE_ANALYSIS.md`（契约把缺失费用折成 0，屏上那支不可达） |
| 第二刀：接受后主动刷新 | 已交（前班） | 交付件 §9 表内 `bf110…`、`bj115…` 两代整链 |
| 第三刀：只修过期断言 + QUICK_CARD 同步 | 已交 | 交付件 blocker 清单；平板 `USER_VERIFIED=PENDING` 未动 |

## 二、等点单的六件（本班一律不自取）

1. 凭证族九十七枚（整套 231 枚里最大一块）：要不要开具名夹具修单。修理面静态量得 868 处、散在 121 枚测试文件；
   尺 `trial/human_walk/_cmdr_bearerless_read_census_r166.py:39` 带正控制（看不见已知那处就 ABORT）。
2. 「费用：未知」：甲（契约改可选并定自动门语义）／乙（只补展示标记）。
3. #332 会话找回：甲（可续设备凭证）／乙（显式再认证＋配对）／丙（说清并忘掉本地指针）／丁（给 Revolution 一个行程地址）。
4. demo 种子时钟与种子形状：过期断言廿六枚与 `DEMO_START_REFUSED: journey must be PLANNED with a selected plan`
   同指一处；口径未定（种子跟着 `execution_clock.now()` 走，还是夹具显式覆写）。
5. 文中引用的 33 枚未入库工件：逐枚点名入库（并发写者与更早班次的文件不许顺手动），短名引用改写成相对全路径另开一刀。
6. 账本 GitHub 镜像（#331）：本地账本是权威且最新；把多兆账本推到 GitHub 属对外可见写，等操作者点名。

## 三、重放命令（照抄可用；解释器只有一枚能跑）

- 后端整套（约 4.7 分钟，末行务必落盘）：
  `cd D:/moodle/_cmdr_rescue_v3_1022/backend && PYTHONIOENCODING=utf-8 "D:/moodle/CityNexus/.venv/Scripts/python.exe" -m pytest -q --tb=line -p no:warnings`
- 红集合成因表（分组数不等于 pytest 自己的 failed 就 ABORT 不出表）：
  `"D:/moodle/CityNexus/.venv/Scripts/python.exe" trial/human_walk/_cmdr_full_red_reason_census_r164.py`
- 凭证族分辨探针（包 `TestClient.get`，只观察；对照跑在测试活着时，挪到 sessionfinish 会因签发夹具已拆而 503）：
  `PYTHONPATH=trial/human_walk ... -m pytest -q <测试文件们> -p _cmdr_unsigned_experience_probe_r155 --tb=no`
- 私有门三臂（不带／假 bearer／六十四零）：`trial/human_walk/_cmdr_journey_read_arms_r165.py`（只读）
- 引用取回普查：`trial/human_walk/_cmdr_cited_artifact_audit_r179.py`
- 提交一律走门：`trial/human_walk/_cmdr_pathspec_commit_gate_r119.py -m <msg> <点名路径…>`；
  自检 `--selftest` 已挂在发布门 `assistant-screen-text` job 里。
- 账本：块写 `D:/moodle/_qoder_ledger_inbox/<会话id>_<HHMM>.md`（首行 `### `），代插门
  `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ledger_insert_after_r2.py "<ORDERS 锚>" <块>`；
  落地后归档 `trial/human_walk/_cmdr_archive_landed_blocks_r1.py <块>`（账本读不到标题行就不许归档）。

## 四、在场栈与库（别按端口猜代次）

- 干净树 `E:/_cmdr_tip_113` 在 `dea0328e0b`（旧代次，屏证用它要注明代次），vite `:14464`、后端 `:60364`，
  库 `E:/_cmdr_tip_113_data/citynexus_v3_rescue_113.db`；课堂树 `E:/_cmdr_clean_1028` 已在
  `c89f4a5ad6`（本班 09:02 挪上去的，porcelain 现读 0 行），vite `:14462`、后端 `:60362`。
  2026-10-29 10:02 现读：两枚 vite 都回 200、两枚 `/api/v1/health` 都 `status=ok`（`ai_state=CONFIGURED_UNVERIFIED`），
  且只有课堂那枚把 `WorkspaceActions.tsx` 编到带 `rev-agent-tool-source` 的版本（回执
  `trial/results/20261026_gozero/bz187-stack-generation.txt:5`）—— 所以主人要亲自走平板验收，走的是课堂 `:14462`，
  它才是最新代次；vite 从磁盘改编译，挪树不用重起进程。尺：`trial/human_walk/_cmdr_stack_generation_r187.py:43`。
- 2026-10-29 10:08 现读（同一把尺重跑一次，回执已刷新）：课堂树 `E:/_cmdr_clean_1028` 现在
  `93f15989b5`、porcelain 现读零行，课堂 vite 仍把同一枚模块编到带披露串的那版
  （`trial/results/20261026_gozero/bz187-stack-generation.txt:3` 与 `trial/results/20261026_gozero/bz187-stack-generation.txt:5`）；
  `:14464` 那只仍停在 `dea0328e0b`，同一枚模块 `serves_disclosure=False`
  （`trial/results/20261026_gozero/bz187-stack-generation.txt:6`）—— 正反两面都还在，所以"课堂＝最新代"是量出来的。
  **接班的人别信本文档里的静态代次**：这一行落进仓库时它自己就又把课堂树顶旧了一代，
  现读用 `git -C E:/_cmdr_clean_1028 rev-parse --short HEAD`，或重跑那把尺。
- 2026-10-29 10:11 定档：课堂树不再逐代追尖，停在 `88b891d22c`（回执
  `trial/results/20261026_gozero/bz187-stack-generation.txt:3` 记的就是它，porcelain 现读零行）。
  它之上的提交只动 `trial/` 文档与回执本身、没动一枚产品字节，所以课堂 vite 交出的模块仍是
  `bytes=215557` 且 `serves_disclosure=True`
  （`trial/results/20261026_gozero/bz187-stack-generation.txt:5`）。要主人踩的产品代码＝这一代；
  `USER_VERIFIED` 仍空着，等主人亲测。
- 2026-10-29 10:43 只读预检（尺的 URI 带 `mode=ro`，路径不是课堂 canary 目录就 ABORT，写不进去）：
  出发门的先决条件在库上已成立 —— 一枚 `PLANNED` 行程（城市 `CN-RV-01A815A96E65`，窗口
  2026-12-03T09:00 → 2026-12-04T21:00 +08），其 `active_plan_version_id` 指向一枚 `SELECTED` 方案
  （回执 `trial/results/20261026_gozero/bw219-classroom-preflight.txt:6`）；库里另有 ACTIVE 两枚、DRAFT 三十六枚、
  CANDIDATE 方案二十枚（`:3` 与 `:4`）。
  **但这一栈上没有任何冻好的移动事实**：`mobility_facts` 与 `route_acquisition_operations` 两张表总行数现读为零
  （`trial/results/20261026_gozero/bw219-classroom-preflight.txt:7`、`trial/results/20261026_gozero/bw219-classroom-preflight.txt:8`）
  ⇒ 主人按「每段步行不超过 1 公里」那一格时，屏上只能靠当场真捕获、或走「未知／估算」那句；
  那是库里没证据，不是屏坏了。要带真路线进课堂得先让那一栈真捕一次（要有键且 provider 可达），
  这一条按口径没代跑 —— 尺：`trial/human_walk/_cmdr_classroom_preflight_r219.py`。
  补一条决定性的好消息：课堂那栈自己报 `amap` 状态为 `READY`、`provenance=LIVE`、坐标系 `GCJ02`
  （只读探针 `trial/human_walk/_cmdr_classroom_provider_probe_r221.py`，掩码后的回执
  `trial/results/20261026_gozero/bw221-classroom-provider-readiness.txt:4`）—— 所以「零事实」是**还没捕**，
  不是**捕不到**：主人按下去的那一趟真能长出路线证据。回执里十三字符以上的串全部掩码，
  尺本身带一道泄漏闸（出现长十六进制/基六十四形状就 ABORT 不落盘），键值从未进文件。
- 高德键只从 User 级环境变量 `CITYNEXUS_AMAP_WEB_KEY` 进进程，不打印、不落盘。
- 旅客 bearer 在 sessionStorage（设计如此，不是缺陷）；行程指针在 localStorage 带 `ownerTravelerId`。

## 五、本班踩过的坑（接班直接用）

- 代插门拒过两块：一次因表格里 `33 个` 这类"数字＋量词"同行没坐标，一次因坐标行号是凭印象写的；
  改法是行号一律现读、量词同行挂 `文件:行`，或改中文数词。
- 文档追加一律走"字节保形"小尺（报告是 CRLF 为主、交付件是 LF），并断言插入点之前逐字节未变。
- 屏证与收据只能是 `.txt`（`.log` 被 .gitignore 吞），文件名带完整前缀（短名会让取回普查认不出）。
## 六、10-29 午前补：那三十九枚「方案不是权威」已经落到某一臂，待点的是一格声明

- 归因（正文 `trial/results/20261026_GO_FROM_BLANK_REPORT.md:3464`）：三十九次拒绝全部出自
  `backend/app/services.py:799`，命中维度只有一处 —— 营业时间那个词。夹具 helper 在
  `backend/tests/test_v12_authoritative_trip_execution.py:104` 写 `NORMALIZED`，判据只认
  `backend/app/services.py:599` 的四个词；成本那一维 132 处地点行全部已解（回执
  `trial/results/20261026_gozero/bw245-sealed-arm-state-v13.txt:10`）。封套豁免读的键在
  `backend/app/services.py:791`，那批行的 metadata 全没写（同一回执 `:7`）。
- 待点二选一，动的都只是夹具字节：甲＝compose 之后补一次
  `backend/tests/test_v12_authoritative_trip_execution.py:122` 那步封套（同树先例
  `backend/tests/test_r28_execution_truth.py:80`、`backend/tests/test_r55_live_progress_drift_product.py:88`）；
  乙＝把 `:104` 那个词换成判据认的四词之一。没人点单就不动，也别把它算进"产品坏了"。
- 只登记不判死：`backend/app/operations/v9.py:358` 也写同一个词，而
  `backend/app/main.py:19305` 把它的 provider 归成服务器自有结构、选用门却没排除它
  （排除条件 `backend/app/services.py:768`）。真路由那一臂实测根本没走到这扇门
  （`trial/results/20261026_gozero/bw245-sealed-arm-state-staylife.txt:3`），所以这条留给裁决，不写成用户面缺陷。
- 本班踩到的仪表坑（接班直接用）：同一把尺跑多条臂，回执必须按臂分文件。这一条原本没做，
  第二臂直接把第一臂的读数覆盖了一次；补救是给探针加一枚 tag（
  `trial/human_walk/_cmdr_sealed_arm_state_r245.py:25`，用 `CITYNEXUS_PROBE_RECEIPT_TAG`），
  再把三臂全部重放，三份回执各自现读才敢写进正文。
- 观察-only 的自证方式记一次：判"探针没改变判定"用的是同数对照（带与不带插件都是
  18 条失败加 9 条通过），只承认耗时变长，不认"应该没影响"。
- 14.20 的交接句（10-29 午）：一按「选这家酒店」就出发，而那扇门一次没被问。
  分母读数在 `trial/results/20261026_gozero/bw250-stay-plan-against-select-gate.txt:3`（整条真路由走查
  对 `backend/app/main.py:20040` 那次的调用记 零，唯一一条是正控制 `:8`，所以「零」不是尺没咬）；
  成因在 `backend/app/operations/v9.py:761` 与 `backend/app/operations/v9.py:779`（住下选用直接把
  方案与行程推成出发态），其后 `backend/app/main.py:18182` 挡回方案选用、`backend/app/main.py:20015`
  幂等早退放行出发门。两条待裁口径已写进账本，本班不代裁。
- 14.21 的交接句：把「谁推出发态」和「谁问过门」排成一张表（尺
  `trial/human_walk/_cmdr_promotion_gate_pairing_r253.py:21`，自检两枚已知锚
  `trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:6` 与
  `trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:20` 各归其栏）。
  接班的人要点名的是 `backend/app/main.py:19038` 那一格（主人真机按「接受这一版」走的实现，
  同一函数里看不见门；它前面那步方案选用 `backend/app/main.py:18289` 是看得见的）。
  「不先选用、直接接受」那一趟还没走查过 —— 别把它写成缺陷，先量。
- 仪表句（本班新踩的一次）：只记拒绝的尺会把「门被问了并放行」与「门根本没被问」混成同一个零。
  `trial/human_walk/_cmdr_stay_plan_select_gate_r250.py:75` 改记每次回答，并在同进程用真数据
  直接问门一次当正控制（`trial/human_walk/_cmdr_stay_plan_select_gate_r250.py:196`），
  正控制不被 trace 看见就 ABORT。以后凡写「某扇门 0 次」都得带这一格。
- 14.23 与 14.24 的交接句（10-29 午）：那把引用取回尺又改了自己一次（模板/通配的标记在目录部分，
  原先只看文件名 ⇒ 两枚模板被当成「找不到」），当代数在
  `trial/results/20261026_gozero/by179-cited-artifact-audit.txt:6`，叁拾叁枚未入库自同回执 :9 起逐枚点名。
  更要紧的一格：玖 处**已暂存**的前端组件 import 着 git 不认识的模块（共 柒 枚模块在树上没 add、
  也没被 .gitignore 命中），分层读数 `trial/results/20261026_gozero/bw270-half-delivery-generation.txt:3`
  记 HEAD 零处 —— 所以现尖没坏，坏在下一笔提交。提交门已装闸
  （`trial/human_walk/_cmdr_pathspec_commit_gate_r119.py:111`，拒则 rc=6、不写东西），
  两向自测与真树判别都过了。接班的人别去替当事人 add：那 柒 枚是别人的写面，点名让当事人补一句即可。
- 同一拍还量到：`backend/app/main.py:19060` 与 `backend/app/main.py:19061` 两条 URL 共用同一个实现，
  所以 §14.22 的「一拖就 503」罩两个入口 —— 这是共用实现的推及，第二条 URL 没再真跑一遍。
