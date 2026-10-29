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
  库 `E:/_cmdr_tip_113_data/citynexus_v3_rescue_113.db`；课堂树 `E:/_cmdr_clean_1028` 在 `:14462/:60362`。
  2026-10-29 09:22 现读四个端口都在 LISTENING。
- 高德键只从 User 级环境变量 `CITYNEXUS_AMAP_WEB_KEY` 进进程，不打印、不落盘。
- 旅客 bearer 在 sessionStorage（设计如此，不是缺陷）；行程指针在 localStorage 带 `ownerTravelerId`。

## 五、本班踩过的坑（接班直接用）

- 代插门拒过两块：一次因表格里 `33 个` 这类"数字＋量词"同行没坐标，一次因坐标行号是凭印象写的；
  改法是行号一律现读、量词同行挂 `文件:行`，或改中文数词。
- 文档追加一律走"字节保形"小尺（报告是 CRLF 为主、交付件是 LF），并断言插入点之前逐字节未变。
- 屏证与收据只能是 `.txt`（`.log` 被 .gitignore 吞），文件名带完整前缀（短名会让取回普查认不出）。
