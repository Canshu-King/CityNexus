"""Build ORD-0395's delivery block with every coordinate read at writing time.

The rule of this order is that a number without a retrievable coordinate is not a reading, so the
generator resolves each cited line against the tree the acceptance ruler indexes
(`refs/remotes/origin/mirror/integration-frontend-apple-pass1`), verifies each 40-hex value with
`git cat-file`, and copies the closing line verbatim out of the commander's own reference file.
Anything it cannot resolve makes the generator refuse rather than emit a loose number.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = "D:/moodle/CityNexus"
WT = Path(r"D:/moodle/_qoder_lane_heyuegong_20261009/wt")
INBOX = Path(r"D:/moodle/_qoder_ledger_inbox")
CLOSING = Path(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt")
MIRROR_REF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
BASE = "5a3d31efdd20a15ae5daaa26cdde13d73970a2a2"
LANE_BRANCH = "refs/heads/review/heyuegong-0395-r1"


def git(*args) -> str:
    run = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError(f"git {args} rc={run.returncode}: {run.stderr.strip()[:160]}")
    return run.stdout


def resolve(sha: str) -> str:
    return git("rev-parse", "--verify", sha).strip()


def line_in_mirror(path: str, needle: str) -> int:
    """The line number of `needle` inside the file as it stands on the ruler's tree."""
    body = git("show", f"{MIRROR}:{path}")
    for index, row in enumerate(body.splitlines()):
        if needle in row:
            return index + 1
    raise RuntimeError(f"{needle!r} not found in {MIRROR}:{path}")


def coord(path: str, needle: str) -> str:
    return f"{path}:{line_in_mirror(path, needle)}"


def coord_on_branch(path: str, needle: str) -> str:
    """A line number inside a file that lives only on this lane's ref, vouched by the tip sha."""
    body = (WT / path).read_text(encoding="utf-8")
    for index, row in enumerate(body.splitlines()):
        if needle in row:
            return f"{path}:{index + 1} 与枝尖 {TIP}"
    raise RuntimeError(f"{needle!r} not found in branch-only {path}")


MIRROR = resolve(MIRROR_REF)
TIP = resolve(LANE_BRANCH)
BASE_SHA = resolve(BASE)
for sha in (MIRROR, TIP, BASE_SHA):
    git("cat-file", "-e", f"{sha}^{{commit}}")

SHA_CODE = resolve("299d69aba")
SHA_EVID = resolve("21f3f377a")
for sha in (SHA_CODE, SHA_EVID):
    git("cat-file", "-e", f"{sha}^{{commit}}")
    git("merge-base", "--is-ancestor", sha, MIRROR)

commits_between = int(git("rev-list", "--count", f"{BASE_SHA}..{MIRROR}").strip())
BLOB_MAIN = git("rev-parse", f"{MIRROR}:backend/app/main.py").strip()
BLOB_TEST = git("rev-parse", f"{MIRROR}:backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py").strip()
BLOB_UV = git("rev-parse", f"{MIRROR}:review/ord0395/UVICORN_READINGS_R1.txt").strip()
BLOB_SHAPE = git("rev-parse", f"{MIRROR}:review/ord0395/SHAPE_PROBE_R1.txt").strip()
BLOB_SERVED = git("rev-parse", f"{MIRROR}:review/ord0395/SERVED_403_AT_TIP_R1.txt").strip()
BLOB_CENSUS = git("rev-parse", f"{MIRROR}:review/ord0395/E2E_ARM_CENSUS_R1.txt").strip()
closing_bytes = len(CLOSING.read_bytes())
closing_lines = len(CLOSING.read_text(encoding="utf-8").splitlines())
if closing_lines != 1:
    raise RuntimeError(f"the closing reference file is not one line: {closing_lines}")
for name, value in (
    ("MIRROR", MIRROR), ("TIP", TIP), ("BASE", BASE_SHA), ("SHA_CODE", SHA_CODE), ("SHA_EVID", SHA_EVID),
):
    if len(value) != 40:
        raise RuntimeError(f"{name} is not a full 40-character object id: {value}")
for name, value in (
    ("main.py", BLOB_MAIN), ("the new door", BLOB_TEST), ("uvicorn readings", BLOB_UV),
    ("shape probe", BLOB_SHAPE), ("served 403 at the tip", BLOB_SERVED), ("census", BLOB_CENSUS),
):
    if len(value) != 40:
        raise RuntimeError(f"blob for {name} is not a full object id: {value}")

block = f"""### 合约工-0395 · ORD-0395 第一件：demo/reset 的拒答三方核齐，改的是「由代码生成那份契约」

一句结论：代码和手写契约本来就同说 `http_status=403`；真正说两家话的是**由代码生成的 `/openapi.json`**。这条门实测能答三种具名码，而生成的那份只点名两种。已把那一侧补齐，并新加一把尺把三方钉在一起；**门的行为一个字节没动，也没改松**。跑 e2e 的那批 spec 仍把「不带 token 的同一条输入」当成功用，那一面按规矩我不碰别人的断言，事实与三条路放在末尾请号令者裁。

坐标规矩：下面每条读数同行给可取回坐标。行号是从号令者的尺实际索引的那棵树现读的（`{MIRROR_REF}` = `{MIRROR}`）；只落在我自己枝上、权威线还没收走的文件，同行另给那枚四十位枝尖，第二道闸会 `git cat-file` 它。

一、改动之前，三方各自说什么

| 面 | 现读到的说法 | 坐标 |
| --- | --- | --- |
| 后端行为 · 不带 token | `http_status=403`，`error.code=RESET_TOKEN_REQUIRED`，`details.tables_protected=true` | {coord_on_branch('review/ord0395/UVICORN_READINGS_BEFORE_R1.txt', 'A[no header]')} |
| 后端行为 · 带了 token 但部署从未配置 | `http_status=403`，`error.code=RESET_TOKEN_INVALID`（与真错 token 同形，配置情况不外泄） | {coord_on_branch('review/ord0395/UVICORN_READINGS_BEFORE_R1.txt', 'A[any header]')} |
| 后端行为 · `CITYNEXUS_DEMO_MODE` 未开 | `http_status=403`，`error.code=DEMO_MODE_REQUIRED` | {coord_on_branch('review/ord0395/UVICORN_READINGS_BEFORE_R1.txt', 'C[no header]')} |
| 后端行为 · 正确 token（反控那臂） | `http_status=200`，`status=reset` | {coord_on_branch('review/ord0395/UVICORN_READINGS_BEFORE_R1.txt', 'B[correct header]')} |
| 手写契约 `contracts/openapi.yaml` | `403` 的 `error.code` enum 列了三码，并要求 `details.tables_protected` | {coord('contracts/openapi.yaml', 'enum: [RESET_TOKEN_REQUIRED')} ; {coord('contracts/openapi.yaml', 'required: [tables_protected]')} |
| 由代码生成的 `/openapi.json` | `403` 只有 description，且只点名两码（少 `DEMO_MODE_REQUIRED`），不带响应体 schema | {coord('review/ord0395/SERVED_403_AT_TIP_R1.txt', 'A[served 403] {')} |
| 后端 pytest 尺（行为面） | 已钉 `http_status=403` + 具名码 + 拒了不删行 | {coord('backend/tests/test_qoder_ord0389_reset_token_gate.py', 'def test_a_reset_without_a_token_is_refused_and_deletes_nothing')} |
| 生成给前端的客户端 | 那份 enum 与三码在（它是从手写契约生成的，不是从代码生成的） | {coord('frontend/src/generated/api.ts', 'RESET_TOKEN_REQUIRED" | "RESET_TOKEN_INVALID" | "DEMO_MODE_REQUIRED')} |

二、改了哪一侧，改了什么

只改「由代码生成」那一侧：把三码收成一张表，403 的描述由表渲染，从此描述不可能少报一码。

| 改动 | 位置 |
| --- | --- |
| 三码一表 `DEMO_RESET_REFUSALS` | {coord('backend/app/main.py', 'DEMO_RESET_REFUSALS = {')} |
| 路由 `responses` 由该表渲染描述 | {coord('backend/app/main.py', 'responses={403: {"description": demo_reset_refusal_description()}},')} |
| 新增尺：同一失败输入读三方，共五臂 | {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_the_two_openapi_documents_name_the_same_refusals')} ; {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_every_code_the_served_document_names_is_one_the_door_answers')} ; {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_the_same_failure_input_gives_all_three_surfaces_the_same_answer')} ; {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_the_correct_token_arm_still_opens')} ; {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_both_documents_promise_the_same_header_claim')} |

三、判据自测：同一条失败输入，三方现在同说一件

| 检查 | 结果 | 坐标 |
| --- | --- | --- |
| 生成的那份点名的码集合 == 手写契约的 enum | 两边都是 `DEMO_MODE_REQUIRED`、`RESET_TOKEN_REQUIRED`、`RESET_TOKEN_INVALID` | {coord('review/ord0395/SHAPE_PROBE_R1.txt', 'code names found in the served 403 description')} |
| 表里声明的每一码，门真答得出（不留死声明） | 三臂各答一码，皆 `http_status=403` | {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_every_code_the_served_document_names_is_one_the_door_answers')} |
| 缺 token 那条输入的现读回话 | `http_status=403`，`RESET_TOKEN_REQUIRED`，`tables_protected=true`，且行数字典前后不变 | {coord('review/ord0395/UVICORN_READINGS_R1.txt', 'no token presented: http_status=403')} |
| 五臂在当前树上的结果 | 5 条全过；与 ORD-0389 那八臂合跑 13 条全过 | {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_the_same_failure_input_gives_all_three_surfaces_the_same_answer')} |

四、反控：门没有被改松

| 臂 | 结果 | 坐标 |
| --- | --- | --- |
| 带正确 token | `http_status=200`，`status=reset` | {coord('review/ord0395/UVICORN_READINGS_R1.txt', 'correct token presented: http_status=200')} |
| 同一台服务器带错 token | 仍 `http_status=403` | {coord('review/ord0395/UVICORN_READINGS_R1.txt', 'wrong token presented: http_status=403')} |
| 尺里另设一条臂专守此事 | 若「不带 token」变通，该臂即红 | {coord('backend/tests/test_qoder_ord0395_reset_403_three_way_r1.py', 'def test_the_correct_token_arm_still_opens')} |

五、尺会咬：三形变异，逐形记录

| 变异 | 红了的臂 | 坐标 |
| --- | --- | --- |
| 从表里抽掉一码 | 2 条红 | {coord_on_branch('review/ord0395/MUTANT_ARMS_R1.txt', '### M1')} |
| 整块 `responses` 删掉 | 3 条红 | {coord_on_branch('review/ord0395/MUTANT_ARMS_R1.txt', '### M2')} |
| 把 token 闸放开（门改松） | 9 条红（我的 3 条 + ORD-0389 的 6 条） | {coord_on_branch('review/ord0395/MUTANT_ARMS_R1.txt', '### M3')} |

六、门禁数（现读，两侧同 interpreter、同 venv、同 ignore 清单）

| 量 | 数 | 坐标 |
| --- | --- | --- |
| collect-only：本枝 | 1792 条，另 1 个模块采集失败 | {coord_on_branch('review/ord0395/SUITE_COUNTS_R1.txt', 'collect_only_this_branch')} |
| collect-only：基线树 | 1787 条，同样 1 个模块采集失败 | {coord_on_branch('review/ord0395/SUITE_COUNTS_R1.txt', 'collect_only_baseline_tree')} |
| 采集失败的那枚不是我引入的 | 它 import 的 `mcp` 包在本 venv 没有 | {coord('scripts/hermes_r4_contract_probe.py', 'from mcp import')} |
| 全量红臂：基线两轮 | 各 13 条，且两轮红集合逐名相同 | {coord_on_branch('review/ord0395/SUITE_COUNTS_R1.txt', 'baseline_run1_and_run2_red_sets_identical')} |
| 全量红臂：本枝两轮 | 一轮 14 条、一轮 13 条；第二轮与基线集合相同 | {coord_on_branch('review/ord0395/SUITE_COUNTS_R1.txt', 'this_branch_run2_red_set_equals_baseline')} |
| 自定义 responses 里带响应体 schema 的 | 0 处（全 app，含本次改动之前也是 0 处） | {coord_on_branch('review/ord0395/SUITE_COUNTS_R1.txt', 'custom_responses_in_main_py_that_declare_a_body_schema')} |

七、需要号令者裁的四件事（我不自己挑一个绿的改法）

一、e2e 那一面三方不可能由我一致。全 acceptance 套里碰这条门的共 14 处（12 处自己发请求 + 2 处等屏幕那头发回话），其中 13 处不带 token，只有 1 处呈现该头：坐标 {coord('review/ord0395/E2E_ARM_CENSUS_R1.txt', 'request sites')} 、{coord('review/ord0395/E2E_ARM_CENSUS_R1.txt', 'watch sites')} 、{coord('review/ord0395/E2E_ARM_CENSUS_R1.txt', 'sites that present X-Demo-Reset-Token')} 、{coord('review/ord0395/E2E_ARM_CENSUS_R1.txt', 'sites that present no token')}。e2e 的起后台处只设了演示开关、从不设 token（{coord('frontend/playwrightEnv.ts', 'CITYNEXUS_DEMO_MODE: "true"')}），所以就算给 harness 配一把 token，不带 token 的那 13 处仍得 `http_status=403`；要它们变通只能改别人的 spec 或改松门。请三路择一：甲＝各 spec 像 {coord('frontend/e2e/_qoderRealSeed.setup.ts', 'const traveler = await call("/api/v1/travelers"')} 那样自己用产品门造种子；乙＝给 e2e 一把 run-owned token 并逐枚 spec 呈现该头（要动别人的文件，只有你能授权）；丙＝把 v13 与 golden 这批归档到 `e2e/legacy/`。旧账「v13 现尖红在 reset 的 403 处、跑不到后面的断言」我**没有跑 playwright** 去复核，只摊两条现读：那枚 spec 的第一条请求就是不带 token 的同一条输入（{coord('frontend/e2e/v13-authoritative-integrity.spec.ts', 'const reset = await request.post')}），而这条输入实测回 `http_status=403`（{coord('review/ord0395/UVICORN_READINGS_R1.txt', 'no token presented: http_status=403')}），下一步它就把回话当 `journey_id` 用——所以它在这条输入上走不下去。这是「代码现读＋同输入实测」的推断，不是跑过的读数；要亲测数字请给一句授权，我按 run-id 规矩另起一臂。

二、两份 OpenAPI 工件的精度层级要不要也拉平。现在两边对「状态码 + 码名」已同说并有尺守；但生成的那份 403 不带响应体 schema（回 False，{coord('review/ord0395/SHAPE_PROBE_R1.txt', 'served 403 declares a response body')}），手写契约带（回 True，{coord('review/ord0395/SHAPE_PROBE_R1.txt', 'contract 403 declares a response body')}）。全 app 自定义 responses 无一处带 body schema，所以我没单独立这个房规——要拉平请给一句授权，我再补 inline schema 并把尺从「码名对照」升级为「结构对照」。

三、反向差一处：生成的那份还多声明 `422`，手写契约只声明 `200` 与 `403`（{coord('review/ord0395/SHAPE_PROBE_R1.txt', 'served statuses')} 对 {coord('review/ord0395/SHAPE_PROBE_R1.txt', 'contract statuses')}）。现有全 app 的对照尺是单向（契约 ⊆ 生成，见 {coord('backend/tests/test_contract.py', 'def test_openapi_runtime_method_parity_includes_v7_surface')}），我没把它改双向，因为那会牵动所有门。

四、契约散文与界面矛盾，产品可见：手写契约写着「没有屏幕提供这个动作」（{coord('contracts/openapi.yaml', 'No screen can satisfy')}），但前端仍有两处发这请求、两处按得动它：{coord('frontend/src/api/citynexus.ts', 'resetDemo()')} 、{coord('frontend/src/features/simulation/simulationAdapter.ts', 'const response = await fetch("/api/v1/demo/reset"')} 、{coord('frontend/src/demo/goldenScenario.ts', 'cityNexusApi.resetDemo()')} 、{coord('frontend/src/features/simulation/SimulationPanel.tsx', 'const result = await resetStage')}。任何部署上点它都得到 `http_status=403`。我按本单范围没动前端，裁语要哪条路（收按钮 / 让它报具名失败 / 把面板限到本机 demo）请点名。

八、回读与自我更正

一、落地跑批在本单进行中已把我前两笔收进权威线：`{BASE_SHA}` 是我起手的尖，现权威尖 `{MIRROR}`，比我基线多 {commits_between} 笔；我那两笔 `{SHA_CODE}` 与 `{SHA_EVID}` 都在其祖先里。我逐枚比过 blob：权威树上的 `backend/app/main.py`、我的新尺与四份证据文本，同我这侧那六枚逐字节一致（blob `{BLOB_MAIN}`、`{BLOB_TEST}`、`{BLOB_UV}`、`{BLOB_SHAPE}`、`{BLOB_SERVED}`、`{BLOB_CENSUS}`）。

二、我自己错了一处要报：第一次全量我加了 `-x`，一遇红就停，覆盖不到全集合，差点把单格里红当成结论；去掉 `-x` 把两侧各跑两轮才拿到可比的红集合。那一格红（`test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one`，见 {coord('backend/tests/test_qoder_ord224_g3_generation_measurement.py', 'def test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one')}）在我这侧两轮里红一轮绿一轮，基线两轮皆绿且集合逐名相同；该臂自己的注释记着同类跨文件仪器竞态（{coord('backend/tests/test_qoder_ord224_g3_generation_measurement.py', 'measured 2026-09-23, combined run')} 起于 {coord('backend/tests/test_qoder_ord224_g3_generation_measurement.py', 'def test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one')}）。我不写「与我无关」，只写观测：已证的是它未被确定性复现；未证的是我新加的 5 臂不会在某轮把它 tip 红。

三、另报一处路径勘误：本单派文说尾行在 `D:/moodle/_qoder_cmdr_ref_20260921/CLOSING_LINE.txt`，该处没有这枚文件；它实在其下 `live_checks` 子目录，现读为单行、共 {closing_bytes} 字节（`D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt:1`）。我逐字抄它、未手打，也未把它的 `git hash-object` 值写进本块——那枚 blob 不在 `D:/moodle/CityNexus` 的对象库里，写进去会被第二道闸按不可取回拒掉。

九、我这边没做的事

权威线 push 0 次（只推自己枝 `{LANE_BRANCH}`）；force-push 0 次；别人的 spec 断言改动 0 处；`backend/tests/test_qoder_ord0389_reset_token_gate.py` 与 `contracts/openapi.yaml` 各 0 处改动（只读引用）；账本 0 处写入（本块进 inbox 等代插）。临时库与导出树在 E:，交完自删。
"""

closing = CLOSING.read_text(encoding="utf-8").rstrip("\r\n")
block = block.rstrip("\n") + "\n\n" + closing + "\n"

stamp = datetime.now().strftime("%H%M")
target = INBOX / f"heyuegong-0395_{stamp}.md"
if len(sys.argv) > 1 and sys.argv[1] == "--write":
    target.write_text(block, encoding="utf-8", newline="\n")
    print(f"WROTE {target} ({len(block.splitlines())} lines, {len(block.encode('utf-8'))} bytes)")
else:
    draft = Path(r"E:/heyuegong_0395/block_draft.md")
    draft.write_text(block, encoding="utf-8", newline="\n")
    print(f"DRAFT {draft} ({len(block.splitlines())} lines, {len(block.encode('utf-8'))} bytes)")
