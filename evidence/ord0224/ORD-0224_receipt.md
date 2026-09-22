# ORD-0224 收据：g3 拆成两把门 + tail-A 独立 + 小包 + 收敛机制的反例（C / 8c66aa92）

- 生成时刻（本机系统钟 `datetime.now().astimezone()`，非手写）：**2026-09-23T03:37:26+08:00**
- 本收据所有判定的锚点 SHA：**`349c4faadab6aca3662844274a7a002be875654b`**
- 当前 tip：`349c4fa 2026-09-23 03:27:12 +0800 test(backend): give each g3 door its own question, and force the admission race without a barrier (ORD-0224 step 6 follow-up 2)` ｜ `git status --porcelain -- backend/` = **0 行**
- 提交链（每一步一个号，从弱修到处置二）：
  - `349c4fa 03:27:12 test(backend): give each g3 door its own question, and force the admission race without a barrier (ORD-0224 step 6 follow-up 2)`
  - `614ad4c 03:16:08 tools(review): publish the six-arm receipt and derive the deployed-generation readings from the logs`
  - `8f1f4d4 03:11:20 test(backend): force the admission race, because my own reverse mutation proved the old window too forgiving (ORD-0224 step 6 follow-up)`
  - `b8ef632 03:09:36 test(review): arm the English pin with the red team's own sentence, verbatim (ORD-0235)`
  - `b2c6153 03:03:04 docs(backend): say out loud why the second reuse read stays, and what measured it (ORD-0224 disposition 2)`
  - `e3329c8 02:51:18 fix(review): identify the deployed bundle by content, and refuse a port another chain owns (ORD-0226 follow-up ②)`
  - `f92f9e9 02:46:42 test(backend): split g3 into one open generation, tail-A on its own, and a measurement package (ORD-0224 步 2/3/4)`
  - `1ea6250 02:46:38 refactor(backend): the non-hard severity of STROLLER/LARGE_LUGGAGE has one owner again (ORD-0234)`
- `f92f9e9 → 349c4fa` 之间 backend/ 变更文件：`['backend/app/catalog_hydration_operations.py', 'backend/tests/test_qoder_anywhere_gates.py', 'frontend/tools/probe-phone-bundle.mjs', 'review/build-evidence-payload.py', 'review/ord0226_deployed_readings.py', 'review/ord0226_kill_arms.py', 'review/ord0226_red_messages.py']`（处置二只加了一段注释，行为与突变锚点未变）
- 解释器：`D:/moodle/CityNexus/.venv/Scripts/python.exe` = Python 3.12.14（唯一能跑本套件的 venv）；子进程一律 `-X utf8` + `PYTHONIOENCODING=utf-8`
- 判据尺：`live_checks/gate_streak.py`（commander 的薄适配器）＋ F 的共享判据模块 `_qoder_streak_receipt.py`（blob `ebe4e24c177d8e18`），后者**复制进一次性导出**才可用——主线树没有它

## 0. 新框架的两把门（本收据全按这个分法写）

| 门 | 钉的是 | 精确 nodeid | 它自己的反例 |
|---|---|---|---|
| `G3_CONCURRENT_OPEN_GENERATION` | **operation identity**：一个开放代次里五发同 id、1 winner + 4 reuse、1 行 durable | `tests/test_qoder_anywhere_gates.py::test_g3_concurrent_open_generation_five_callers_share_one_operation` | `Y3`（破坏败者回读）；`Y2` 只打到一部分 |
| provider-work dedupe | **解析次数**：开放中的重复提问，额外解析 = 0 | `tests/test_qoder_ord213_ask_store_before_world.py::test_w1_a_repeat_of_an_open_question_asks_the_provider_once_not_twice` | `X1`/`Y1a`（把 lookup 挪回解析之后） |

两者不许互相冒充——这条不是声明，是 §3 的实测（`Y1a` 只红 dedupe 门，身份门全绿）。

## 1. 逐步交付与坐标

| 步 | 内容 | 落点 SHA | 状态 |
|---|---|---|---|
| 1 | 弱修：先算键 → 先查存储 → 再解析。产品码 +37 行（`anywhere_capability.py` +14 新增 `pending_request_fingerprint()`；`catalog_hydration_operations.py` +23）；`main.py`、`provider_identity.py` 各 0 行 | `50d1c4d`（口径本轮钉成独立断言 `len(calls) - after_first_submit == 0` → `f92f9e9`） | 完成，**不结 g3** |
| 2 | `G3_CONCURRENT_OPEN_GENERATION`：`threading.Barrier(5)` 放行五发，产品自己的 `dispatch` 真起 worker，worker 停在 `_run_operation` 内的闩上；并**断言 `worker_started`**（没有活 worker 的窗口就是空断言）。另两把配套：`test_g3b_…`（`start_worker=False` ＋ `dispatch` 计数=0 的控制形制）、`test_g3d_…`（唯一索引存在**且是部分**索引） | `f92f9e9` | 完成，连击 §2 |
| 3 | tail-A 独立门 `test_g3c_…`：A 同步跑到终态 ⇒ 同一瞬间（门内打印实测 ms 差）的同键请求必须另开 B、不得拿 A ⇒ **任何 freshness window 都会把这条门变红** | `f92f9e9` | 完成 |
| 4 | 小包 `tests/test_qoder_ord224_g3_generation_measurement.py`（3 nodes）→ JSON 产物：shape A / shape B / 四档读数 / 逐请求 operation_id / 状态时间线 / 探针来源；**字段不齐＝门红** | `f92f9e9` | 完成，读数 §4 |
| 5 | 收敛机制归因：A=两次读开放作业；B=`backend/db/schema.sql:1007` 部分唯一索引；C=`except IntegrityError` 里的败者回读 | 本收据 §3/§4 | 完成 |
| 6 | 五个反向突变（`mutation_anchor_guard`）；corrected g3 由 **Y3** 打死。**但复跑暴露 Y3 不稳定**：同一突变在 `f92f9e9` 红 4/4、在只差一段注释的 `b2c6153` 只红 3/4（`test_g3_concurrent_open_generation_…` 活下来）⇒ 有时后来者是从已提交的行被回答的，根本没撞到 durable 冲突。**「时有时无的突变」不算那把门的反例**，所以先加强制交错门（`8f1f4d4`，用 Barrier 把五发 parked 在解析里），复跑又发现自己两个仪器缺陷（跨门共用指纹导致邻门释放的 worker 串味；Barrier 会被复用即返回的 caller 饿死到 10 s 超时），最终版在 `349c4fa`：`test_g3e_admission_race_no_caller_may_see_another_before_commit`——爆发期内每发前两次 `find_open_operation` 被答「没有开放的」，而败者回读**不遮蔽**，只剩 durable 层可能交付收敛 | `f92f9e9` → 补强 `8f1f4d4` → 两处仪器缺陷修在 `349c4fa` | 完成，§3 + §3bis |
| 处置二 | Y1b 的冗余读**保留**，并在行上写明「今天没有任何门依赖它（Y1b 12/12），它是第二道机会」；删除权归强修单 | `349c4fa` | 完成 |
| ORD-0234 | `severity="HARD" if hard else None`（两行），删重复真值；顺带更正一处失效注释 | `1ea6250` | 完成，§6 |

## 2. 连击（条款 1–10；每行都带 run shape ＋ 精确 nodeid ＋ 命令）

### identity 门（步 2）
- target nodeid：`tests/test_qoder_anywhere_gates.py::test_g3_concurrent_open_generation_five_callers_share_one_operation`
- SHA：`349c4faadab6aca3662844274a7a002be875654b` ｜ run shape：**single-node**（尺自己签的号）｜ rounds=10 ｜ observation_only=None
- 命令：`D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest tests/test_qoder_anywhere_gates.py::test_g3_concurrent_open_generation_five_callers_share_one_operation --tb=short --import-mode=importlib`
- 逐 run 目标判定：`['GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN']` ｜ 逐 run pytest 摘要：[{'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}]
- 独立性：distinct 临时库 = `10`；每 run `path_did_not_exist_before_this_run` 全真 = `True`
- 条款 6 命令面：`clause6_command_surface_clean=True`（无 sleep / reruns / -n / -k / deselect / 放宽期望）
- 判定：`STREAK_MET(10)` ｜ closure_grade `STREAK_GREEN` ｜ closure_allowed `False` ｜ problems `无`

### tail-A 门（步 3）
- target nodeid：`tests/test_qoder_anywhere_gates.py::test_g3c_tail_a_terminal_job_is_answered_by_a_new_generation_not_reuse`
- SHA：`349c4faadab6aca3662844274a7a002be875654b` ｜ run shape：**single-node**（尺自己签的号）｜ rounds=10 ｜ observation_only=None
- 命令：`D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest tests/test_qoder_anywhere_gates.py::test_g3c_tail_a_terminal_job_is_answered_by_a_new_generation_not_reuse --tb=short --import-mode=importlib`
- 逐 run 目标判定：`['GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN']` ｜ 逐 run pytest 摘要：[{'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}]
- 独立性：distinct 临时库 = `10`；每 run `path_did_not_exist_before_this_run` 全真 = `True`
- 条款 6 命令面：`clause6_command_surface_clean=True`（无 sleep / reruns / -n / -k / deselect / 放宽期望）
- 判定：`STREAK_MET(10)` ｜ closure_grade `STREAK_GREEN` ｜ closure_allowed `False` ｜ problems `无`

### dedupe 门（步 1）
- target nodeid：`tests/test_qoder_ord213_ask_store_before_world.py::test_w1_a_repeat_of_an_open_question_asks_the_provider_once_not_twice`
- SHA：`349c4faadab6aca3662844274a7a002be875654b` ｜ run shape：**single-node**（尺自己签的号）｜ rounds=10 ｜ observation_only=None
- 命令：`D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest tests/test_qoder_ord213_ask_store_before_world.py::test_w1_a_repeat_of_an_open_question_asks_the_provider_once_not_twice --tb=short --import-mode=importlib`
- 逐 run 目标判定：`['GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN', 'GREEN']` ｜ 逐 run pytest 摘要：[{'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}, {'passed': 1, 'summary_line': 1}]
- 独立性：distinct 临时库 = `10`；每 run `path_did_not_exist_before_this_run` 全真 = `True`
- 条款 6 命令面：`clause6_command_surface_clean=True`（无 sleep / reruns / -n / -k / deselect / 放宽期望）
- 判定：`STREAK_MET(10)` ｜ closure_grade `STREAK_GREEN` ｜ closure_allowed `False` ｜ problems `无`

读法边界：

- 三条都是 **closure-grade 的 10 连**（不是 `--observation-runs` 样本）。
- `closure_allowed=False` 由尺自己签：它的反向突变格子吃**字符串声明**（`CNX_ORD0210_REVERSE_MUTATION=KILLED`），我按仲裁「不许凭环境变量的号签 CLOSED」留空。本轮的产品反向突变证据是 §3 那份文件，不是那个格子。
- 我没有 whole-file / node-with-preceding-doors 两种形制的合法收据：上一轮实测到尺会把**文件选择子**签成 `single-node`，且它的逐 run 判定取自摘要计数（`pytest_counts.passed=5`）——那条通道我不用，已把读数交给尺的主人。

## 3. 反向突变（步 6）：到底是谁让五发收敛

- 证据文件：`mutate_ord0224_convergence_mechanism_349c4fa.evidence.json`
- 跑的树：`D:\moodle\_qoder_ord30_evidence_20260920\ord213\snap_349c4fa` ｜ 形制：one pytest process over the 13 declared nodeids per mutant

| 突变 | 打到哪一层 | declared | observed | 命中声明 | anchor_hits | bytes_changed | 红的 node |
|---|---|---|---|---|---|---|---|
| `Y1a` | A - pre-resolution read | `KILLED_AS_DECLARED` | `KILLED_AS_DECLARED` | True | 1 | True | `['test_w1_a_repeat_of_an_open_question_asks_the_provider_once_not_twice']` |
| | 前后 sha256[:16]：`7d51d7acc1eddfa6` → `7154dad09b8cf7f2`；复原后与交付树逐字节相同 | | | | | | |
| `Y1b` | A - post-resolution read | `SURVIVED_REDUNDANT` | `SURVIVED_REDUNDANT` | True | 1 | True | `['无']` |
| | 前后 sha256[:16]：`7d51d7acc1eddfa6` → `951de0fa020db5e4`；复原后与交付树逐字节相同 | | | | | | |
| `Y2` | B - partial unique index | `KILLED_AS_DECLARED` | `KILLED_AS_DECLARED` | True | 1 | True | `['test_g3b_open_window_control_without_any_worker_dispatch', 'test_g3e_admission_race_no_caller_may_see_another_before_commit', 'test_shape_b_five_callers_in_one_open_window_converge']` |
| | 前后 sha256[:16]：`1de29df73819f9e3` → `4ecc1c1092e83fa4`；复原后与交付树逐字节相同 | | | | | | |
| `Y3` | C - loser read-back | `KILLED_AS_DECLARED` | `KILLED_AS_DECLARED` | True | 1 | True | `['test_g3b_open_window_control_without_any_worker_dispatch', 'test_g3e_admission_race_no_caller_may_see_another_before_commit', 'test_measurement_package_is_complete_and_writable', 'test_shape_b_five_callers_in_one_open_window_converge']` |
| | 前后 sha256[:16]：`7d51d7acc1eddfa6` → `583540f6394bd976`；复原后与交付树逐字节相同 | | | | | | |
| `Y4` | B made total (tail-A's witness) | `KILLED_AS_DECLARED` | `KILLED_AS_DECLARED` | True | 1 | True | `['test_g3c_tail_a_terminal_job_is_answered_by_a_new_generation_not_reuse', 'test_g3d_durable_layer_still_holds_the_partial_unique_index', 'test_w2_a_terminal_job_is_still_answered_by_a_new_attempt', 'test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one']` |
| | 前后 sha256[:16]：`1de29df73819f9e3` → `f1e36802a6372ca6`；复原后与交付树逐字节相同 | | | | | | |

- **可签字的那句**：破坏 **C（败者回读）** ⇒ corrected g3 的两把身份门 + 小包全红：`['test_g3b_open_window_control_without_any_worker_dispatch', 'test_g3e_admission_race_no_caller_may_see_another_before_commit', 'test_measurement_package_is_complete_and_writable', 'test_shape_b_five_callers_in_one_open_window_converge']`（`KILLED_AS_DECLARED`）。这就是仲裁点名的「破坏真正让五发收敛的产品机制」。
- **两把门确实被分开了**：`Y1a`（关掉预查复用）⇒ 只红 `['test_w1_a_repeat_of_an_open_question_asks_the_provider_once_not_twice']`，身份门全绿。所以「把 lookup 挪到 provider 之后」只能给 dedupe 门充数，不能给 g3 充数。
- `Y1b`（关掉解析后那次读）⇒ **13/13 全绿** ⇒ 那把读今天没有任何门依赖（指挥官裁定：保留，行上写明是第二道机会，删除权归强修单）。
- **本战役 5/5 命中声明**（`matches_declaration` 全 True）。这是我把声明**改成按门名列**之后才成立的：上一版用列表下标写 `expect_red`，插一扇门进去声明就全体错位（自我报告见账本 `ORD-0224 六步交付` 与其后两块）。
- **历史留痕（不改口的收据不算收据）**：`8f1f4d4` 那批里 `Y2` 被我声明成 4 把门、实测只红 2 把（PARTIALLY_KILLED），`Y4` 我声明成 1 把、实测红 4 把（KILLED_BUT_LEAKY）；两处都在 `349c4fa` 按实测重述为 `[E,B]` 与 `[C,D,W2,SA]`，于是两条都变成命中声明。

## 3bis. Y3 的 10 轮批量（这条才是「反例成立」的依据）

- 形制：每轮 = 装突变 → 5 把门跑在一个 pytest 进程 → 复原并核对 sha256，共 **10** 轮；证据 `probe_y3_determinism_349c4fa.json`；SHA 锚点 `349c4fa`

| 门 | RED | GREEN | NOT_OBSERVED | 每轮必红（deterministic_kill） |
|---|---|---|---|---|
| `test_g3e_admission_race_no_caller_may_see_another_before_commit` | 10/10 | 0 | 0 | **True** |
| `test_g3b_open_window_control_without_any_worker_dispatch` | 10/10 | 0 | 0 | **True** |
| `test_shape_b_five_callers_in_one_open_window_converge` | 10/10 | 0 | 0 | **True** |
| `test_measurement_package_is_complete_and_writable` | 9/10 | 1 | 0 | **False** |
| `test_g3_concurrent_open_generation_five_callers_share_one_operation` | 10/10 | 0 | 0 | **True** |

- **签字的那句**：`Y3` 是强制交错门 `test_g3e_admission_race_no_caller_may_see_another_before_commit` 的反例（10/10 必红）。
- 一条重要的自我更正：barrier-only 那把 `test_g3_concurrent_open_generation_five_callers_share_one_operation` 在 `8f1f4d4` 只有 **6/10**，移除跨门共用指纹的耦合之后在 `349c4fa` 变 **10/10** ⇒ 它当初「活下来」是我的仪器（邻门释放的 worker 串味），不是产品偶尔不需要败者回读。
- 唯一不达标的是包完整性门 `test_measurement_package_is_complete_and_writable`（9/10）⇒ 它的 10/10 我没有主张，也不拿它当反例依据。
- 规矩升级：**并发门的反例必须 ≥10 轮批量**，单轮只回答「这批打到了谁」。尺的 `--runs 10` 是给绿的门槛，同样的门槛该给杀。

## 4. 小包（步 4）的两形制读数

- 产物：`ord224_measurement_package_349c4fa.json` ｜ 具名库：`sqlite:///C:/Users/仓鼠王/AppData/Local/Temp/cnx_pytest_9h8cpgig/suite.db`
- **shape B（一个开放代次）**：durable 行 = `1`，distinct ids = `['4a136a1a-93fe-4104-bb14-3eff4f4e8964']`，winner/joiners = `1/4`，**解析次数 = `5`**，时间线 = `[('4a136a1a', 'QUEUED', None)]`
- 逐请求 `(index, operation_id[:8], reused, status_code)`：`[(0, '4a136a1a', True, 200), (1, '4a136a1a', False, 202), (2, '4a136a1a', True, 200), (3, '4a136a1a', True, 200), (4, '4a136a1a', True, 200)]` ｜ winner 不是第 0 发 ⇒ 交错是真的，不是排好的顺序
- 探针来源（逐条交代）：`{'resolution': 'wrapper on app.catalog_hydration_operations.resolve_destination', 'worker': 'latch around app.catalog_hydration_operations._run_operation (entered=True)', 'rows': 'SELECT via SessionLocal on the app-resolved suite DB'}`
- **shape A（退役形制：单发先行 + 五发）**：同指纹留下 **1 枚终态 + 1 枚开放 = 2 行**，而它的标签是「五个并发请求」⇒ 仲裁那句「很可能两代一起数」被复现。五发内部的 distinct ids 只作**读数**，不作判据。
- 挂起声明原样留在包里：`{'OLD_G3_PRODUCT_DEFECT_CLASSIFICATION': 'SUSPENDED_PENDING_EVIDENCE', 'suspended_labels': ['12R/2G', '0/10R']}`；我此前那张 `3/10 绿`（`50d1c4d`、single-node）一并降级为「退役形制下的读数」，不再用来解释产品。
- **坏消息照贴**：shape B 是 `5` 次解析对应 1 枚作业 ⇒ **真并发下 provider-work dedupe 没有达成**（预查拦不住未提交的行）。要它必须做 `claim-before-work`，那条按令未动。

## 5. 门禁

- 全量 @`349c4fa`：collected `1205` ｜ `8 failed, 1181 passed, 15 skipped, 1 xfailed, 2 warnings in 110.76s (0:01:50)`
- 与 `33034d7` 基线（8 红）逐 nodeid 比：新增 `无`，消失 `无`
- 出网是**读数**不是承诺：三文件同进程、`getaddrinfo` 换成记录型阻塞器 ⇒ `1 failed, 19 passed, 2 warnings in 2.29s`，**名字解析尝试 0 次**（被记到的主机：`[]`）｜ 原始输出 `nosock_ord224.log`
- 端口/库：本轮 0 次监听、0 次连接；`:4781/:4782/:8693` 未碰；`_live.db`/`_preview.db` 0 次打开；临时库都由 conftest 的 `%TEMP%\cnx_pytest_*` 承担。自清（生产者自己删，两轮）：`%TEMP` 曾积 **1289** 个 → 删 1275（894 MB）；本轮又积 175 个 → 删 160（158 MB）。两轮都只留「3 分钟内、可能正在跑」的那批（14 / 15 个），**0 个因文件占用而失败**——能删掉就说明没有打开的句柄，这条比「我以为没人用」硬。
- 一次性导出：`snap_50d1c4d`、`snap_b_4d9ceae`、`snap_f92f9e9`、`snap_8f1f4d4`、`snap_b2c6153` 已删（判据=源 SHA 记着、`git archive` 可重出，且事实都已进收据/账本）；只留 `snap_349c4fa` 供复跑（本收据的连击与突变都跑在它里面，删了就复现不了）。

## 6. ORD-0234（单独一单，一行级）

- `backend/app/capabilities.py`：两行 `severity="HARD" if hard else "STRONG"` → `else None`，保留显式 HARD 提升；同时更正一处失效注释——实测 `default_severity('STROLLER'/'LARGE_LUGGAGE', hard_asserted=True/False)` **都返回 STRONG**（两码在 CONTEXT_CODES），所以旧文「会落 SOFT」不成立，而这正是重复字面量带来的漂移形状。`TOILET_BREAK_EVERY_MIN` 未动（不在这条裁定里）。
- 删后读数：我名下 ORD-0219 两文件 **15 passed**；能力面 13 文件合跑 collected 307 → **294 passed / 13 skipped / 0 failed**；钉住「只是提到 ⇒ STRONG」的 `test_8…` 仍绿 ⇒ 今日等价，是实测不是观感。

## 7. 没做完 / 做不到（明写，不用「基本完成」盖）

1. **跨进程那一格没有读数**：所有门都在单进程多线程里（TestClient + 线程 + 闩）。`ORD-0210 FINAL CLOSED = BLOCKED_ON_CROSS_PROCESS_EVIDENCE`；按令只交方案 → `cross_process_evidence_plan.md`（七件必需物、成本表、以及「现有那把尺能不能跑这个形状」的答案：**能**——每次子进程预算 1800 s、`FORBIDDEN_COMMAND_FLAGS` 不挡路；但尺的判据里**没有跨进程所有权**，marker 行必须门自己做）。
2. **强修 `claim-before-work` 一行没动**（登记、等仲裁那句「跨进程是否必要」）。
3. **真并发下 dedupe 未达成**（§4 的 `5` 次解析），需要强修才谈得上。
4. **whole-file / node-with-preceding-doors 形制的合法收据我没有**（§2 读法边界）。
5. `ORD-0220` / `ORD-0218④` 的坐标按令不再处理。

---
生成脚本：`ord213/build_ord224_receipt.py 349c4fa`（数字全部来自 streak JSON / 突变 JSON / 小包 JSON / pytest 日志 / `git`，无手写常量）
