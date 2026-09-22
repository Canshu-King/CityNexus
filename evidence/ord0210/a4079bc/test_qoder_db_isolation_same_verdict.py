"""ORD-0210 · 常驻门：**量具形状 + 逐 run 定性**（机制层，16:10 冻结顺序的第 1 步）。

口径演进（务必按最新版读，别引用旧措辞）：
1. 14:4x 最初：同一 nodeid 在"干净库"与"脏库"上必须同判定。
2. 15:2x 改口径：ORD-0211 已把后端套件钉到**每进程新临时库**（`tests/conftest.py` 的
   `mkdtemp(prefix="cnx_pytest_")`），"脏库"这一半不再存在 ⇒ 验收改成**独立进程连跑 10 次全绿**。
3. 15:58 仲裁冻结 `GATE_ACCEPTANCE_STREAK` 八条（总线 `5773071703`）。
4. 16:10 冻结顺序（总线 `5773209274`）点名本门要接的两件：
   `FLIP_WITHOUT_SHARED_STATE classification` + `acceptance-streak logic wired`，并且
   **"mechanism can be ACCEPTED even while target g3 is still RED/FLIPPING"**。
5. 16:40 仲裁追加第 9/10 条（总线 `5773588112`）：**形制是收据的一部分**；
   **定性范围 = (exact SHA, target node id, run shape)**；
   **"Whole-command/file exit is not a proxy for the target node."**

⇒ 本门分成两种模式，这一点是**故意的**，别合并：
* **机制模式（默认，常驻套件）**：跑真靶子（默认 2 个独立进程），只断言**收据/量具合法**
  ——每 run 一个不同的、app 自己解析并打印出来的临时库，跑前该路径不存在，首尾行数有记录，
  命令面没有放宽开关，逐 run 有目标节点自己的判定，定性结论带形制。**靶子红不是本门的红。**
  这正是第 4 条那句"机制可先签收"的机器形状；否则本门会变成套件里的一条常红，
  污染别人的红集合读数（commander 16:3x 为 ORD-0217 说过的同一个理由）。
* **验收模式（`CNX_ORD0210_MODE=acceptance`）**：C 的 ORD-0213 修复落地后由人显式开，
  必须**正好 10 个独立进程**（少一个直接 SETUP 红，不许用环境变量放宽第 2 条）且全绿；
  第 6 条的自证文本没写 ⇒ 最多 `STREAK_GREEN`，`closure_allowed` 恒 False。

判据本身在 `backend/tests/_qoder_streak_receipt.py`（与 `contracts/gate-acceptance-streak.yaml`
一一对应）。**第 10 条的"从多节点容器输出里抽逐 run 目标节点判定"不在这里** —— 那是
commander 17:5x 认领的 `live_checks/gate_streak.py` 修正，本门只拒绝"拿容器 exit 当目标节点代理"，
不另起一份抽取器（免得出两份实现各说各话）。

边界（仲裁原话照录）：
    resolved absolute DB path must be printed/receipted
    never point tests at _live.db or user DB
"""

from __future__ import annotations

import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any

import pytest

TESTS_DIR = pathlib.Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:  # 导出树的 rootdir/cwd 各种形状都要能 import 到判据模块
    sys.path.insert(0, str(TESTS_DIR))

from _qoder_streak_receipt import (  # noqa: E402
    CLOSURE_GRADE_REVERSE_RESULTS,
    CLASSIFICATIONS,
    FORBIDDEN_DB_NAMES,
    RECEIPT_PREFIX,
    REQUIRED_RECEIPT_FIELDS,
    REQUIRED_RUN_FIELDS,
    RUN_SHAPES,
    SHAPE_REQUIRED_FLAGS,
    SINGLE_NODE,
    WHOLE_FILE,
    NODE_WITH_PRECEDING_DOORS,
    classify_target_node,
    clause6_command_surface,
    corroborate_node_outcome,
    decode_child_text,
    node_outcome_from_exit,
    observation_only,
    has_decoding_damage,
    summarize_pytest_counts,
    parse_resolved_path,
    path_is_forbidden,
    receipt_problems,
    read_text_bytes,
    resolved_path_problems,
    run_freshness_problems,
    parse_pytest_selectors,
    shape_command,
    streak_verdict,
    verify_run_shape,
)

BACKEND = TESTS_DIR.parent
REPO = BACKEND.parent

#: 靶子（ORD-0210/0213 点名的那条竞态门）。
TARGET_NODEID = (
    "tests/test_qoder_anywhere_gates.py::"
    "test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation"
)

#: 本门跑靶子的形制：**单节点**（一次进程里只有这一条用例被点名）。
RUN_SHAPE = SINGLE_NODE

ROUNDS_ENV = "CNX_GATE_ISOLATION_ROUNDS"
MODE_ENV = "CNX_ORD0210_MODE"
DECLARATION_ENV = "CNX_ORD0210_CLAUSE6"
#: 反向突变证据（仲裁源审计 ①）：验收模式必须交，值 ∈ `_qoder_streak_receipt` 那张表。
REVERSE_MUTATION_ENV = "CNX_ORD0210_REVERSE_MUTATION"

#: 第 2 条是"10 CONSECUTIVE independent processes"，验收模式里这个数字**不许被放宽**。
ACCEPTANCE_ROUNDS = 10
#: 机制模式只为验量具形状，默认 2 个进程（1 个证明不了"逐 run 互不相同"）。
MECHANISM_ROUNDS = 2

#: 账本与 commander 的锚点 guard（源审计 ②：不许只把"我跑过 guard"当纪律写在话里）。
#: 标题字面**由 guard 自己定义**（`HEADING`），我这里不留第二份，免得它改了还各自以为健康。
LEDGER_NAME = "CITYNEXUS_AGENT_CONTROL.md"
ANCHOR_GUARD_PATHS: tuple[str, ...] = (
    r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ledger_anchor_guard.py",
    "live_checks/ledger_anchor_guard.py",
)

#: 首尾行数读哪几枚表（与 commander 工具的 COUNT_TABLES 对齐；不在就是 NO_TABLE，不编数）。
COUNT_TABLES = ("journeys", "plan_versions", "travelers", "catalog_hydration_operations")


# ======================================================================================
# 跑靶子的形状
# ======================================================================================
def _python() -> str:
    return sys.executable


def _mode() -> str:
    raw = os.environ.get(MODE_ENV, "").strip().lower()
    if raw in ("", "mechanism"):
        return "mechanism"
    if raw == "acceptance":
        return "acceptance"
    pytest.fail(f"SETUP 失败：{MODE_ENV}={raw!r} 只认 mechanism / acceptance")
    raise AssertionError  # unreachable


def _argv() -> list[str]:
    """跑靶子的**命令面** = 仲裁源审计 ③ 冻结的单节点形制：恰好一条 nodeid +
    `--tb=short --import-mode=importlib`，**不带** `-rA`（它把逐 run 报告混进 stdout）、
    **不带** `-p`（那是改跑法，不是在记读数）。仍然刻意没有 `-q`：`-q` 会把打印
    `resolved=` 的 header 段一起压掉（commander 15:2x 踩过，我第一次也踩过）。
    命令面由 `_qoder_streak_receipt.shape_command` 生成 ⇒ 形制与 argv 只有一份定义。"""

    return shape_command(SINGLE_NODE, [TARGET_NODEID], python=_python())


def _rounds(mode: str) -> int:
    raw = os.environ.get(ROUNDS_ENV, "").strip()
    if not raw:
        return ACCEPTANCE_ROUNDS if mode == "acceptance" else MECHANISM_ROUNDS
    try:
        value = int(raw)
    except ValueError:
        pytest.fail(f"SETUP 失败：{ROUNDS_ENV}={raw!r} 不是整数")
        raise AssertionError
    if mode == "acceptance" and value != ACCEPTANCE_ROUNDS:
        pytest.fail(
            f"SETUP 失败：验收模式必须正好 {ACCEPTANCE_ROUNDS} 个独立进程（第 2 条），"
            f"你给了 {value}。要少跑就用机制模式，别拿环境变量放宽第 2 条。"
        )
    return max(1, value)


def _under_test_sha() -> str:
    """被测 SHA：环境变量优先，其次 git；都没有就如实写 UNKNOWN（导出树没有 `.git`）。
    第 1 条要求 exact SHA ⇒ 判据模块会拒收 UNKNOWN。
    git 的输出按**字节**读、走同一把回退解码链（源审计 ①：不许有第二套读文本的方式）。"""

    declared = os.environ.get("CNX_UNDER_TEST_SHA", "").strip()
    if declared:
        return declared
    proc = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                          capture_output=True)
    stdout, _ = decode_child_text(proc.stdout or b"")
    return stdout.strip() or "UNKNOWN"


def _norm(path: Any) -> str:
    """Windows 上 `%TEMP%` 可能是 8.3 短名，而 conftest 打印的是 resolve 后的长名。
    不归一就会把"同一个目录"看成两个（假独立）或反过来（假重复）。"""

    try:
        return os.path.normcase(os.path.realpath(str(path)))
    except OSError:
        return os.path.normcase(str(path))


def _temp_dirs() -> set[str]:
    root = pathlib.Path(tempfile.gettempdir())
    return {_norm(p) for p in root.glob("cnx_pytest_*") if p.is_dir()}


def _row_counts(path_str: str) -> dict[str, Any]:
    """只读取行数；文件不在 ⇒ 如实 `absent`，非 SQLite ⇒ `NOT_APPLICABLE`，都不编数。"""

    path = pathlib.Path(str(path_str))
    if not path.is_file():
        return {"absent": True}
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return {"error": "READ_ONLY_OPEN_FAILED"}
    try:
        have = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        out: dict[str, Any] = {"absent": False, "table_count": len(have)}
        for table in COUNT_TABLES:
            out[table] = (con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                          if table in have else "NO_TABLE")
        return out
    finally:
        con.close()


def _assert_not_user_db(path: Any) -> None:
    """**大小写不敏感**（源审计 ③）：Windows 上 `D:/moodle/CityNexus/_LIVE.DB` 打开的就是
    `_live.db`，用裸 `Path.name` 撞字面会被它绕过去。归一化交给共享判据 `path_is_forbidden`。"""

    hit = path_is_forbidden(path)
    if hit:
        pytest.fail(
            f"拒绝：本门绝不碰 {path}（归一化后命中被保护的库 {hit!r}；"
            f"{FORBIDDEN_DB_NAMES} 是用户数据与预览真值，Windows 路径大小写不算两回事）"
        )


def _run_once(index: int, before: set[str]) -> dict[str, Any]:
    """跑**一个独立进程**的靶子并攒出第 4/9 条要的逐 run 字段。

    子进程文本协议（仲裁源审计 5775293071 ①/③ 的硬要求，也正是 `gate_streak.py` 栽的地方）：
    * **先拿完整字节**（`capture_output=True`，不开 `text=True`）；
    * **stdout 与 stderr 分开解码**，各记自己用的 codec —— 拼成一坨会让一条 `resolved=` 被跨流
      粘连成 `<日志前缀>resolved=…`，路径当场被改坏；
    * 解码走 UTF-8 → gb18030 → surrogateescape 的回退链，**不许** `errors="replace"`：
      静默替换出的 U+FFFD 会伪装成"这一行不存在"，第 1 条要的解析路径就这样丢了。
    `node_outcome` 只从退出码读，且只在 `RUN_SHAPE == single-node` 时读得出来（第 10 条）；
    退出码 2/3/4/5 ⇒ `NOT_OBSERVED`（**一条都没跑绝不记成绿**）。
    traceback 行只当**诊断文本**打印，不参与判定 —— 否则就又变成"拿输出猜结论"。
    """

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("CITYNEXUS_DATABASE_URL", None)  # 让 conftest 自己钉：证明"app 自己解析"这件事

    argv = _argv()
    proc = subprocess.run(argv, cwd=str(BACKEND), env=env, capture_output=True, timeout=900)
    stdout, stdout_codec = decode_child_text(proc.stdout or b"")
    stderr, stderr_codec = decode_child_text(proc.stderr or b"")
    decoder = f"stdout={stdout_codec};stderr={stderr_codec}"
    after = _temp_dirs()

    # 退出码要能被**摘要计数**佐证，否则不许当结果（实测的假绿通道：整条 skip ⇒ exit 0）。
    counts = summarize_pytest_counts(stdout or stderr)
    raw_outcome = node_outcome_from_exit(proc.returncode, run_shape=RUN_SHAPE,
                                        nodeids_in_command=[TARGET_NODEID])
    outcome, corroboration = corroborate_node_outcome(raw_outcome, run_shape=RUN_SHAPE,
                                                     counts=counts)

    printed, path_source = parse_resolved_path(stdout, stderr)
    created = sorted(after - before)
    if not printed and created:
        db_path, path_source = str(pathlib.Path(created[0]) / "suite.db"), "temp_dir_diff_only"
    else:
        db_path = printed or "NOT_PRINTED"
    if db_path != "NOT_PRINTED":
        _assert_not_user_db(db_path)

    parent_preexisted = bool(db_path) and _norm(pathlib.Path(db_path).parent) in before
    if parent_preexisted:
        initial: dict[str, Any] = {"error": "RESOLVED_PATH_PREEXISTED_BEFORE_THIS_RUN"}
    elif db_path == "NOT_PRINTED":
        initial = {"error": "NO_RESOLVED_PATH_CAPTURED"}
    else:
        # 第 3 条的"fresh"在这里是**量到的**：这条路径在本次进程之前不存在。
        initial = {"absent": True, "path_did_not_exist_before_this_run": True}

    failure = next((ln.strip()[:180] for ln in (stdout + "\n" + stderr).splitlines()
                    if "AssertionError" in ln or ln.strip().startswith("E ")), "")

    # 只记录、不改判：这一轮期间 %TEMP% 里冒出来的**别人家的** cnx_pytest_* 目录，
    # 就是"这台机器当时还有别的车道在跑"的实测证据。并发时序门的读数对机器负载敏感，
    # 而第 10 条的定性范围里（SHA / nodeid / 形制）没有这一格 —— 先把它量下来再说。
    mine = _norm(pathlib.Path(db_path).parent) if db_path != "NOT_PRINTED" else ""
    foreign = sum(1 for d in (after - before) if d != mine)

    shape = verify_run_shape(
        run_shape=RUN_SHAPE, argv=argv, nodeids=[TARGET_NODEID],
        nodeids_in_command=[TARGET_NODEID], streams_separate=True, decoder=decoder)
    return {
        "run_index": index,
        "exit_code": proc.returncode,
        "node_outcome": outcome,
        "node_outcome_uncorroborated": raw_outcome,
        "pytest_counts": counts, "corroboration": corroboration,
        "resolved_absolute_db_path": db_path,
        "initial_row_counts": initial,
        "final_row_counts": _row_counts(db_path) if db_path != "NOT_PRINTED"
        else {"error": "NO_RESOLVED_PATH_CAPTURED"},
        "path_source": path_source,
        "child_decoder": decoder,
        # 受损位是**量出来的**，不是"我声称用了哪档 codec"：标签可以撒谎，文本里的 U+FFFD 撒不了。
        "stdout_damage": has_decoding_damage(stdout),
        "stderr_damage": has_decoding_damage(stderr),
        "streams_separate": True,
        "resolved_path_problems": resolved_path_problems(db_path),
        "run_shape_verified": shape["run_shape_verified"],
        "run_shape_problems": shape["problems"],
        "foreign_temp_dirs_during_this_run": foreign,
        "diagnostic_red_line": failure,
    }


def _build_receipt() -> dict[str, Any]:
    mode = _mode()
    rounds = _rounds(mode)
    argv = _argv()
    clean, hits = clause6_command_surface(argv)
    declared = os.environ.get(DECLARATION_ENV, "").strip()

    rows: list[dict[str, Any]] = []
    for index in range(1, rounds + 1):
        before = _temp_dirs()
        row = _run_once(index, before)
        rows.append(row)
        print(f"[round {index}/{rounds}] exit={row['exit_code']} "
              f"outcome={row['node_outcome']} db={row['resolved_absolute_db_path']} "
              f"| 行数 {row['final_row_counts'].get('catalog_hydration_operations', '?')} "
              f"| {row['diagnostic_red_line'][:90]}")

    outcomes = [r["node_outcome"] for r in rows]
    paths = [r["resolved_absolute_db_path"] for r in rows]
    sha = _under_test_sha()
    shape_verified = all(r["run_shape_verified"] for r in rows)
    shape_problems = sorted({p for r in rows for p in r["run_shape_problems"]})
    reverse = os.environ.get(REVERSE_MUTATION_ENV, "").strip()
    receipt = streak_verdict(
        runs=rows, rounds=rounds, sha=sha, target_nodeid=TARGET_NODEID,
        run_shape=RUN_SHAPE, command=" ".join(argv[1:]),
        independence_declared=bool(declared), clause6_declared=bool(declared),
        clause6_command_surface_clean=clean, clause6_command_surface_hits=hits,
        run_shape_verified=shape_verified, run_shape_problems=shape_problems,
        reverse_mutation_required=(mode == "acceptance"),
        reverse_mutation_result=reverse,
    )
    receipt["classification"] = classify_target_node(
        sha=sha, target_nodeid=TARGET_NODEID, run_shape=RUN_SHAPE,
        node_outcomes=outcomes, resolved_db_paths=paths,
    )
    receipt["mode"] = mode
    receipt["clause6_declaration"] = declared or "（未声明）"
    receipt["reverse_mutation_result"] = reverse or "（未交）"
    receipt["runs"] = rows
    return receipt


def _print_receipt(receipt: dict[str, Any]) -> str:
    cls = receipt["classification"]
    lines = [
        "\n[ORD-0210 收据 · 机制层已接线]",
        f"  模式            = {receipt['mode']}",
        f"  SHA             = {receipt['sha']}   (第 1 条)",
        f"  工作树          = {REPO}",
        f"  解释器          = {_python()}",
        f"  目标 nodeid     = {receipt['target_nodeid']}",
        f"  跑法形制        = {receipt['run_shape']}   (第 9 条)",
        f"  形制校验        = {receipt['checks'].get('run_shape_verified')}"
        f"；不合规项 {receipt['checks'].get('run_shape_problems')}",
        f"  命令            = {receipt['command']}   (每 run 一个独立进程)",
        f"  轮数            = {receipt['rounds']}  绿 {receipt['green']} / 红 {receipt['red']}"
        f" / 未观测 {receipt['not_observed']}",
        f"  重复解析路径    = {receipt['duplicate_db_paths']}",
        f"  缺路径的 run    = {receipt['runs_missing_db_path']}",
        f"  第 6 条         = {receipt['clause6_note']}",
        f"  streak 结论     = {receipt['verdict']}",
        f"  可结案          = {receipt['closure_allowed']} (第 5 条绿 + 第 2 条 10 进程"
        f" + 第 6b 条自证 + 反向突变证据)",
        f"  结案判级        = {receipt['closure_grade']}   ← 10/10 绿但没有反向证据时是"
        " STREAK_GREEN，不是 CLOSED",
        f"  反向突变        = required={receipt['reverse_mutation_required']} "
        f"result={receipt['reverse_mutation_result']}"
        f"（结案级 ∈ {list(CLOSURE_GRADE_REVERSE_RESULTS)}）",
        f"  机器并发        = 各轮期间另有 "
        f"{[r.get('foreign_temp_dirs_during_this_run', 0) for r in receipt['runs']]} 个"
        "别人的临时库（**只记录，不参与判定**：并发时序门对负载敏感，先把它量下来）",
        f"  目标节点定性    = {cls.get('named_shape')}",
        f"  定性依据        = {cls.get('reason')}",
    ]
    if str(cls.get("sample_note") or "").strip():
        lines.append(f"  ⚠ 样本        = {cls['sample_note']}")
    for row in receipt["runs"]:
        lines.append(
            f"    run {row['run_index']}: exit={row['exit_code']} outcome={row['node_outcome']}"
            f" path_source={row['path_source']} db={row['resolved_absolute_db_path']}"
            f" 解码={row.get('child_decoder', '?')}"
            f" 形制校验={row.get('run_shape_verified', '?')}"
            f" 跑前={row['initial_row_counts']} 跑后={row['final_row_counts']}"
            f" 邻居进程={row.get('foreign_temp_dirs_during_this_run', '?')}"
            + (f" 红在={row['diagnostic_red_line'][:70]}" if row["diagnostic_red_line"] else "")
        )
    text = "\n".join(lines)
    print(text)
    return text


SHARED_NAMES = ("ISOLATION_BREACH", "DIRTY_DB_FALSE_GREEN", "DIRTY_DB_FALSE_RED")


def _instrument_problems(receipt: dict[str, Any]) -> list[str]:
    """把一份收据读成"量具/收据哪几条不合规"。**靶子红不在这里** —— 那是产品的账。"""

    problems = receipt_problems(receipt)
    for row in receipt["runs"]:
        # freshness / 路径合规 / 解码受损 这三条**判据在共享模块里**（仲裁 §3：判据留在 test
        # 文件里 ⇒ 别的引用方可绕过）。门只转述共享判据的结果，不再各算一遍。
        for shared_problem in run_freshness_problems(row):
            problems.append(f"run {row['run_index']}：{shared_problem}")
        for key in ("initial_row_counts", "final_row_counts"):
            counts = row.get(key)
            if isinstance(counts, dict) and "error" in counts:
                problems.append(f"run {row['run_index']} 的 {key} 读失败（{counts['error']}）："
                                "解析出来的路径打不开 = 收据里的路径不可信，不是产品红")
        if not row.get("run_shape_verified"):
            problems.append(f"run {row['run_index']} 的形制证据没过校验（第 9 条）："
                            f"{row.get('run_shape_problems')}")
    cls = receipt["classification"]
    if cls.get("classification") not in CLASSIFICATIONS + SHARED_NAMES:
        problems.append(f"定性名字不在冻结词表里：{cls.get('classification')!r}")
    if not str(cls.get("named_shape") or "").endswith(f"({receipt['run_shape']})"):
        problems.append("定性结论没带形制后缀：第 9 条『形制是收据的一部分』")
    only, note = observation_only(cls)
    if only:
        problems.append(f"只有单次观测却想谈结论：{note}")
    return problems


# ======================================================================================
# 1 · 机制模式：跑真靶子，只断言量具形状（靶子红不是本门的红）
# ======================================================================================
def test_1_the_mechanism_produces_a_valid_receipt_for_a_flipping_target():
    receipt = _build_receipt()
    text = _print_receipt(receipt)
    problems = _instrument_problems(receipt)

    assert not problems, (
        "期望：机制模式下**量具形状**完全合法（每 run 一个 app 自己打印的新临时库、首尾行数、"
        "逐 run 目标节点判定、形制与 SHA 进收据、命令面无放宽开关）；"
        f"实际不合规项：{problems}\n{text}"
    )
    # 靶子翻不翻是产品的账（ORD-0213 归 C）。这里只钉一句：结论**必须**被形制限定过。
    assert receipt["classification"]["named_shape"].startswith(
        receipt["classification"]["classification"]), (
        f"期望：定性结论字符串里带 (<shape>)；实际 {receipt['classification']['named_shape']!r}"
    )


def _fake_row(index: int, path: str) -> dict[str, Any]:
    return {
        "run_index": index, "exit_code": 1, "node_outcome": "RED",
        "resolved_absolute_db_path": path,
        "initial_row_counts": {"absent": True, "path_did_not_exist_before_this_run": True},
        "final_row_counts": {"absent": False, "journeys": 0},
        "path_source": "app_printed_receipt_line",
        "child_decoder": "stdout=utf-8;stderr=utf-8",
        "stdout_damage": "", "stderr_damage": "", "streams_separate": True,
        "resolved_path_problems": [], "run_shape_verified": True, "run_shape_problems": [],
        "foreign_temp_dirs_during_this_run": 0, "diagnostic_red_line": "",
    }


def _fake_receipt(rows: list[dict[str, Any]], outcomes: list[str],
                  shape_suffix: str = "(single-node)",
                  shape_verified: bool | None = None,
                  reverse_mutation_result: str = "",
                  reverse_mutation_required: bool = False) -> dict[str, Any]:
    argv = _argv()
    clean, hits = clause6_command_surface(argv)
    verified = (all(r.get("run_shape_verified", True) for r in rows)
                if shape_verified is None else shape_verified)
    problems = sorted({p for r in rows for p in r.get("run_shape_problems", [])})
    receipt = streak_verdict(
        runs=rows, rounds=len(rows), sha="50b35e0", target_nodeid=TARGET_NODEID,
        run_shape=RUN_SHAPE, command=" ".join(argv[1:]),
        clause6_command_surface_clean=clean, clause6_command_surface_hits=hits,
        run_shape_verified=verified, run_shape_problems=problems,
        reverse_mutation_required=reverse_mutation_required,
        reverse_mutation_result=reverse_mutation_result)
    receipt["classification"] = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=RUN_SHAPE,
        node_outcomes=outcomes, resolved_db_paths=[r["resolved_absolute_db_path"] for r in rows])
    receipt["classification"]["named_shape"] = (
        f"{receipt['classification']['classification']}{shape_suffix}")
    receipt["runs"] = rows
    receipt["mode"] = "mechanism"
    return receipt


def test_1b_the_instrument_judge_acts_on_both_directions():
    """本门的红/不红由 `_instrument_problems` 说了算 ⇒ 这把判词自己必须双向咬得住。"""

    good = _fake_receipt([_fake_row(1, _paths(2)[0]), _fake_row(2, _paths(2)[1])],
                         ["RED", "GREEN"])
    assert _instrument_problems(good) == [], (
        f"期望：一张形状正确的机制收据判为合规；实际 {_instrument_problems(good)}")

    inferred = _fake_receipt([_fake_row(1, _paths(2)[0]),
                              _fake_row(2, _paths(2)[1])], ["RED", "GREEN"])
    inferred["runs"][1]["path_source"] = "temp_dir_diff_only"
    assert any("不是 app 打印的" in msg for msg in _instrument_problems(inferred)), (
        "期望：路径只是靠临时目录差集猜出来的 ⇒ 必须报警（第 1 条边界要的是 app 自己打印）；"
        f"实际 {_instrument_problems(inferred)}")

    no_shape = _fake_receipt([_fake_row(1, _paths(2)[0]), _fake_row(2, _paths(2)[1])],
                             ["RED", "GREEN"], shape_suffix="")
    assert any("形制后缀" in p for p in _instrument_problems(no_shape)), (
        "期望：定性结论没带 (<shape>) ⇒ 违反第 9 条，必须报警；"
        f"实际 {_instrument_problems(no_shape)}")

    damaged = _fake_receipt([_fake_row(1, _paths(2)[0]), _fake_row(2, _paths(2)[1])],
                            ["RED", "GREEN"])
    damaged["runs"][0]["stdout_damage"] = "含 U+FFFD（errors='replace' 的产物：那一行的原字节已经丢了）"
    assert any("解码受损" in p2 for p2 in _instrument_problems(damaged)), (
        "期望：某轮量到解码受损 ⇒ 本门的判词必须点名它（这一格红 = 我把受损读数当干净用）；"
        f"实际 {_instrument_problems(damaged)}")

    shared = _fake_receipt([_fake_row(1, _paths(1)[0]), _fake_row(2, _paths(1)[0])],
                           ["RED", "GREEN"])
    problems = _instrument_problems(shared)
    assert any("no_two_runs_share_a_temp_db" in p or "ISOLATION_BREACH" in p or
               "STREAK_INVALID" in p for p in problems), (
        f"期望：两个 run 共用一份库 ⇒ 判据必须拒绝（第 7 条 / 两则分类）；实际 {problems}")
    assert shared["classification"]["classification"] == "ISOLATION_BREACH", (
        f"期望：这一格的定性落在 ISOLATION_BREACH 而不是 FLIP；"
        f"实际 {shared['classification']['named_shape']}")


# ======================================================================================
# 1a · 验收模式：C 修完之后由人显式开；第 2/5 条在这里才咬
# ======================================================================================
@pytest.mark.skipif(_mode() != "acceptance", reason=(
    "验收模式（第 2/5 条）需要 C 的 ORD-0213 修复落地后由 "
    f"{MODE_ENV}=acceptance 显式开；套件里默认只跑机制模式，免成本门变常红"))
def test_1a_acceptance_streak_is_ten_independent_green_processes():
    receipt = _build_receipt()
    text = _print_receipt(receipt)

    # 源审计 ② 的那一格：验收路径以前只比 verdict/classification，**没跑共享判据**，
    # 于是"每进程新库"这条只在机制模式里被机械强制。现在两条路径共用同一把 `_instrument_problems`。
    problems = _instrument_problems(receipt)
    assert not problems, (
        "期望：验收模式下量具形状也完全合法（含逐 run 的 fresh 校验、解码器、形制校验）；"
        f"实际不合规项：{problems}\n{text}")
    for row in receipt["runs"]:
        fresh = row["initial_row_counts"]
        assert isinstance(fresh, dict) and fresh.get("path_did_not_exist_before_this_run") is True, (
            f"期望：验收必须逐 run 量到『这条路径在本次进程之前不存在』（第 3 条，走共享判据）；"
            f"实际 run {row['run_index']} 的跑前读数是 {fresh}\n{text}")

    assert receipt["rounds"] == ACCEPTANCE_ROUNDS, (
        f"期望：验收必须 {ACCEPTANCE_ROUNDS} 个连续独立进程（第 2 条）；"
        f"实际 {receipt['rounds']}\n{text}")
    assert receipt["verdict"] == f"STREAK_MET({ACCEPTANCE_ROUNDS})", (
        f"期望：第 5 条『all 10 runs GREEN』；实际 {receipt['verdict']}"
        f"（绿 {receipt['green']}/{receipt['rounds']}）\n{text}")
    assert receipt["classification"]["classification"] == "STABLE_GREEN", (
        f"期望：streak 达成时目标节点定性是 STABLE_GREEN({RUN_SHAPE})；"
        f"实际 {receipt['classification']['named_shape']} —— {receipt['classification']['reason']}")

    # 源审计 ①：结案要有**独立**反向证据；10/10 绿 + 没交反向突变 ⇒ 只到 STREAK_GREEN。
    reverse = os.environ.get(REVERSE_MUTATION_ENV, "").strip()
    declared = bool(os.environ.get(DECLARATION_ENV, "").strip())
    assert receipt["reverse_mutation_required"] is True, (
        "期望：验收模式下反向突变是**必需项**（mechanism 模式不要求）")
    if reverse not in CLOSURE_GRADE_REVERSE_RESULTS or not declared:
        assert receipt["closure_allowed"] is False and receipt["closure_grade"] == "STREAK_GREEN", (
            "期望：没写第 6 条自证文本、或没交 KILLED/STREAK_BROKEN 级别的反向突变时，"
            f"closure_allowed 必须 False、判级只能 STREAK_GREEN；实际 "
            f"{receipt['closure_allowed']}/{receipt['closure_grade']}"
            f"（required={receipt['reverse_mutation_required']} "
            f"declared={declared} reverse={reverse or '（未交）'}）\n{text}")
    else:
        assert receipt["closure_allowed"] is True and receipt["closure_grade"] == "CLOSED", (
            f"期望：STREAK_MET + 10 进程 + 自证文本 + 反向突变 {reverse} 齐 ⇒ 可谈结案；"
            f"实际 {receipt['closure_allowed']}/{receipt['closure_grade']}")


# ======================================================================================
# 2 · 历史形状保留：脏库喂出的假绿 / 干净库里的真红，两个方向要能分开叫
# ======================================================================================
def test_2_the_dirty_db_directions_stay_named_not_merged():
    def classify(clean_verdict: str, dirty_verdict: str) -> str:
        if clean_verdict == dirty_verdict:
            return "CONSISTENT"
        if clean_verdict == "FAIL" and dirty_verdict == "PASS":
            return "DIRTY_DB_FALSE_GREEN"
        if clean_verdict == "PASS" and dirty_verdict == "FAIL":
            return "DIRTY_DB_FALSE_RED"
        return "UNKNOWN"

    assert classify("FAIL", "PASS") == "DIRTY_DB_FALSE_GREEN", (
        "期望：干净红/脏绿 ⇒ 前序运行留下的行把门喂绿，报警")
    assert classify("FAIL", "FAIL") == "CONSISTENT", (
        "期望：干净红/脏红 ⇒ **真红**（真缺陷，不是仪器问题，不许叫 flaky）")
    assert classify("PASS", "PASS") == "CONSISTENT"
    assert classify("PASS", "FAIL") == "DIRTY_DB_FALSE_RED", "期望：干净绿/脏红 ⇒ 脏库把门弄红"


# ======================================================================================
# 3 · 边界自证：绝不碰用户库
# ======================================================================================
def test_3_the_user_databases_are_never_touched():
    """`pytest.fail` 抛的 `Failed` 不继承 `Exception` ⇒ 必须抓 `BaseException`。"""

    for name in FORBIDDEN_DB_NAMES:
        with pytest.raises(BaseException) as caught:
            _assert_not_user_db(BACKEND / name)
        assert name in str(caught.value), (
            f"期望：拒绝信息里点名被保护的库 {name}；实际 {str(caught.value)[:120]!r}")


# ======================================================================================
# 4 · 第 10 条：定性范围 = (SHA, target node id, run shape)
#    下面四组输入就是 17:5x 账本里那四行读数，一格不改地喂进判据
# ======================================================================================
def _paths(n: int) -> list[str]:
    return [f"C:/tmp/cnx_pytest_{i:02d}/suite.db" for i in range(n)]


def test_4a_the_four_frozen_readings_classify_as_the_arbiter_wrote_them():
    single = classify_target_node(
        sha="56d20ec", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["GREEN"] + ["RED"] * 9, resolved_db_paths=_paths(10))
    assert single["named_shape"] == "FLIP_WITHOUT_SHARED_STATE(single-node)", (
        f"期望：单门形 1 绿 / 9 红、10 个不同新临时库 ⇒ FLIP_WITHOUT_SHARED_STATE(single-node)"
        f"（commander 17:5x 自纠的那一格）；实际 {single['named_shape']}"
        f" —— {single['reason']}")

    preceded = classify_target_node(
        sha="56d20ec", target_nodeid=TARGET_NODEID, run_shape=NODE_WITH_PRECEDING_DOORS,
        node_outcomes=["GREEN"] * 7 + ["RED"] * 3, resolved_db_paths=_paths(10))
    assert preceded["named_shape"] == (
        "FLIP_WITHOUT_SHARED_STATE(node-with-preceding-doors-in-one-process)"), (
        f"期望：带前序门那一形 7 绿 / 3 红 ⇒ FLIP 并**带上这一形自己的名字**；"
        f"实际 {preceded['named_shape']}")
    assert preceded["named_shape"] != single["named_shape"], (
        "期望：同一 SHA、同一 nodeid，不同形制必须给出**不同**的具名结论（第 10 条的定域）")

    whole_file_blind = classify_target_node(
        sha="56d20ec", target_nodeid=TARGET_NODEID, run_shape=WHOLE_FILE,
        node_outcomes=["NOT_OBSERVED"] * 10, resolved_db_paths=_paths(10))
    assert whole_file_blind["classification"] == "UNCLASSIFIED_IN_THIS_SHAPE", (
        f"期望：整文件 0/10 绿但拿不到逐 run 目标节点判定（那是 g5 红带着整条命令红）"
        f"⇒ 不许给 g3 定性；实际 {whole_file_blind['classification']}")
    assert whole_file_blind["classification"] != "STABLE_RED", (
        "期望：'整条命令红' 不是 '目标节点恒红' 的代理 —— 这正是 17:5x 那句自纠")

    whole_file_scoped = classify_target_node(
        sha="56d20ec", target_nodeid=TARGET_NODEID, run_shape=WHOLE_FILE,
        node_outcomes=["RED"] * 10, resolved_db_paths=_paths(10))
    assert whole_file_scoped["named_shape"] == "STABLE_RED(whole-file)", (
        f"期望：一旦逐 run 抽出了目标节点自己的判定（10 红）⇒ 这一形可以定 STABLE_RED；"
        f"实际 {whole_file_scoped['named_shape']} —— 抽取器在 gate_streak.py，本门只吃它的输出")


def test_4b_many_reds_is_not_the_same_as_always_red():
    """把 commander 17:5x 那句自纠钉成机器判据：**红得多 ≠ 恒红**。"""

    nine_red_one_green = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["RED"] * 9 + ["GREEN"], resolved_db_paths=_paths(10))
    naive_majority_rule = "STABLE_RED" if nine_red_one_green["red"] > 5 else "FLIP"
    assert nine_red_one_green["classification"] == "FLIP_WITHOUT_SHARED_STATE", (
        f"期望：目标节点自己两种结果都出现过就叫翻，与红多红少无关；实际 "
        f"{nine_red_one_green['classification']} —— {nine_red_one_green['reason']}")
    assert naive_majority_rule == "STABLE_RED", (
        "这条断言在钉一个反例的形状：'多数红 ⇒ 恒红' 的多数表决规则会给出 STABLE_RED。"
        "如果它哪天不红了，说明有人把判据改成了多数表决 —— 那是要报警的方向")

    always_red = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["RED"] * 10, resolved_db_paths=_paths(10))
    assert always_red["named_shape"] == "STABLE_RED(single-node)", (
        f"期望：10 红 ⇒ STABLE_RED(single-node)；实际 {always_red['named_shape']}")
    always_green = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["GREEN"] * 10, resolved_db_paths=_paths(10))
    assert always_green["named_shape"] == "STABLE_GREEN(single-node)", (
        f"期望：10 绿 ⇒ STABLE_GREEN(single-node)；实际 {always_green['named_shape']}")


def test_4c_one_isolated_observation_never_becomes_a_verdict():
    """第 8 条：一次孤立 GREEN 只是观察。本模块取的是保守读法（<2 run 一律不定性）。"""

    one_green = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["GREEN"], resolved_db_paths=_paths(1))
    assert one_green["classification"] == "UNCLASSIFIED_IN_THIS_SHAPE", (
        f"期望：单次绿不定性（第 8 条）；实际 {one_green['named_shape']}")
    only, note = observation_only(one_green)
    assert only is True and "第 8 条" in note, f"期望拿到第 8 条判词；实际 {only}, {note[:60]}"

    two_green = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["GREEN", "GREEN"], resolved_db_paths=_paths(2))
    assert two_green["classification"] == "STABLE_GREEN", (
        f"期望：两个独立 run 的边界另一侧 —— 2 全绿就该定 STABLE_GREEN（判据不是无脑拒绝）；"
        f"实际 {two_green['classification']} —— {two_green['reason']}")
    assert observation_only(two_green)[0] is False

    no_sha = classify_target_node(
        sha="UNKNOWN", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["RED"] * 9 + ["GREEN"], resolved_db_paths=_paths(10))
    assert no_sha["classification"] == "UNCLASSIFIED_IN_THIS_SHAPE", (
        f"期望：没有 exact SHA ⇒ 定性的三把键缺一把，判不了；实际 {no_sha['classification']}")

    # —— 机制模式实测那一把给出来的读数就是这一形制（2 run 全红）：名字合法，但不能被当结案读数 ——
    two_red = classify_target_node(
        sha="b05a3b2", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["RED", "RED"], resolved_db_paths=_paths(2))
    assert two_red["classification"] == "STABLE_RED", (
        f"期望：2 run 全红在第 10 条字面下就是 STABLE_RED；实际 {two_red['classification']}")
    assert "1/10" in two_red["sample_note"] and "样本只有 2" in two_red["sample_note"], (
        f"期望：样本不够分时必须带一句警告（不然明天有人拿它当 g3 的定性读数）；"
        f"实际 sample_note={two_red['sample_note']!r}")
    ten_red = classify_target_node(
        sha="b05a3b2", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["RED"] * 10, resolved_db_paths=_paths(10))
    assert ten_red["sample_note"] == "", (
        f"期望：跑满第 2 条的 10 个进程后，警告该自动消失（它是量出来的，不是写死的话术）；"
        f"实际 {ten_red['sample_note']!r}")
    flip = classify_target_node(
        sha="b05a3b2", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["RED"] * 9 + ["GREEN"], resolved_db_paths=_paths(10))
    assert flip["sample_note"] == "", (
        f"期望：FLIP 结论本来就需要两种结果都出现过，不该背样本警告；实际 {flip['sample_note']!r}")


def test_4d_a_shared_db_path_is_not_a_flip_without_shared_state():
    """仲裁两则分类的另一半：**同一个解析库** + 判定会翻 ⇒ ISOLATION_BREACH，不许叫 FLIP。"""

    one_path = _paths(1)[0]
    shared = classify_target_node(
        sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        node_outcomes=["GREEN"] * 5 + ["RED"] * 5, resolved_db_paths=[one_path] * 10)
    assert shared["classification"] == "ISOLATION_BREACH", (
        f"期望：十个 run 共用同一份临时库时，翻判定只能叫 ISOLATION_BREACH / DIRTY_DB_FALSE_*；"
        f"实际 {shared['classification']} —— {shared['reason']}")
    streak = streak_verdict(
        runs=[{"run_index": i + 1, "exit_code": 0 if i < 5 else 1,
               "node_outcome": "GREEN" if i < 5 else "RED",
               "resolved_absolute_db_path": one_path, "path_source": "app_printed_receipt_line",
               "child_decoder": "stdout=utf-8;stderr=utf-8",
               "initial_row_counts": {"absent": True,
                                      "path_did_not_exist_before_this_run": True},
               "final_row_counts": {"journeys": i}}
              for i in range(10)],
        rounds=10, sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        command="pytest " + TARGET_NODEID, run_shape_verified=True)
    assert streak["verdict"].startswith("STREAK_INVALID_shared_db_path"), (
        f"期望：第 7 条把这条 streak 判废；实际 {streak['verdict']}")


# ======================================================================================
# 5 · streak 判定接线：每一格不合法都要有名字，且**绿的那一侧也要能算出来**
# ======================================================================================
def _synthetic(outcomes: list[str], paths: list[str] | None = None) -> list[dict[str, Any]]:
    paths = paths or _paths(len(outcomes))
    exit_of = {"GREEN": 0, "RED": 1}
    return [
        {"run_index": i + 1, "exit_code": exit_of.get(o, 2), "node_outcome": o,
         "resolved_absolute_db_path": paths[i], "path_source": "app_printed_receipt_line",
         "child_decoder": "stdout=utf-8;stderr=utf-8",
         "initial_row_counts": {"absent": True, "path_did_not_exist_before_this_run": True},
         "final_row_counts": {"journeys": 1}}
        for i, o in enumerate(outcomes)]


def test_5_the_streak_ladder_names_every_failure_shape():
    base = dict(sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
                command="pytest " + TARGET_NODEID, run_shape_verified=True)

    ok = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10, **base)
    assert ok["verdict"] == "STREAK_MET(10)", (
        f"期望：10 个独立进程全绿 ⇒ STREAK_MET(10)（第 5 条），判据不许只会说红；实际 {ok['verdict']}")
    assert ok["closure_allowed"] is False, "期望：没声明第 6b 条 ⇒ 不签结案"
    assert ok["closure_grade"] == "STREAK_GREEN", (
        f"期望：绿了但没结案证据 ⇒ 判级 STREAK_GREEN；实际 {ok['closure_grade']}")

    # 源审计 ①：自证文本齐了也**还不够**结案——要有独立的反向突变证据。
    declared = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10,
                              clause6_declared=True, independence_declared=True, **base)
    assert declared["closure_allowed"] is False, (
        "期望：STREAK_MET + 10 进程 + 第 6b 条自证，但**没交反向突变** ⇒ 仍不签 CLOSED"
        f"（实际 {declared['closure_allowed']}/{declared['closure_grade']}）")
    assert declared["closure_grade"] == "STREAK_GREEN", (
        f"期望判级停在 STREAK_GREEN；实际 {declared['closure_grade']}")
    assert any("反向" in n or "STREAK_GREEN" in n for n in [declared["closure_note"]]), (
        f"期望判级理由里点名缺的是哪一格；实际 {declared['closure_note'][:120]!r}")

    closed = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10,
                            clause6_declared=True, independence_declared=True,
                            reverse_mutation_required=True,
                            reverse_mutation_result="KILLED", **base)
    assert closed["closure_allowed"] is True and closed["closure_grade"] == "CLOSED", (
        f"期望：齐了反向突变 KILLED ⇒ 才可谈结案；实际 "
        f"{closed['closure_allowed']}/{closed['closure_grade']}")
    broke = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10,
                           clause6_declared=True, independence_declared=True,
                           reverse_mutation_result="STREAK_BROKEN", **base)
    assert broke["closure_allowed"] is True, (
        f"期望：STREAK_BROKEN 与 KILLED 同级（都证明保护点破坏后门会红/断）；实际 "
        f"{broke['closure_allowed']}")
    survived = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10,
                              clause6_declared=True, independence_declared=True,
                              reverse_mutation_result="SURVIVED", **base)
    assert survived["closure_allowed"] is False and survived["closure_grade"] == "STREAK_GREEN", (
        f"期望：反向突变 SURVIVED（破坏保护点门不红）⇒ 绝不能签结案；实际 "
        f"{survived['closure_allowed']}/{survived['closure_grade']}")
    junk = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10,
                          clause6_declared=True, independence_declared=True,
                          reverse_mutation_result="绿了就算过", **base)
    assert junk["checks"]["reverse_mutation_value_valid"] is False, (
        "期望：词表外的反向突变值本身是收据缺陷，不能当'没交'含糊过去")
    assert any("reverse_mutation_value_valid" in p for p in receipt_problems(junk)), (
        f"期望 receipt_problems 点名这一格；实际 {receipt_problems(junk)}")
    assert receipt_problems(closed) == [], (
        f"期望：一份齐证的结案收据判为合规；实际问题 {receipt_problems(closed)}")

    one_red = streak_verdict(runs=_synthetic(["GREEN"] * 9 + ["RED"]), rounds=10, **base)
    assert one_red["verdict"] == "STREAK_NOT_MET(9/10_green)", (
        f"期望：一次红就不达成，并把绿数写进名字；实际 {one_red['verdict']}")

    blind_rows = _synthetic(["NOT_OBSERVED"] * 10)
    unobserved = streak_verdict(runs=blind_rows, rounds=10,
                                **dict(base, run_shape=WHOLE_FILE))
    assert unobserved["verdict"].startswith("HARNESS_INVALID_target_verdict_not_scoped"), (
        f"期望：整文件形制下拿不到逐 run 目标节点判定 ⇒ 量具不合法，不是 10 绿；"
        f"实际 {unobserved['verdict']}")

    missing_path = _synthetic(["GREEN"] * 3)
    missing_path[1]["resolved_absolute_db_path"] = "NOT_PRINTED"
    v = streak_verdict(runs=missing_path, rounds=3, **base)
    assert v["verdict"].startswith("HARNESS_INVALID_no_resolved_db_path"), (
        f"期望：有一轮没解析出库 ⇒ HARNESS_INVALID；实际 {v['verdict']}")

    missing_rows = _synthetic(["GREEN"] * 3)
    del missing_rows[2]["final_row_counts"]
    v = streak_verdict(runs=missing_rows, rounds=3, **base)
    assert v["verdict"].startswith("RECEIPT_INCOMPLETE"), (
        f"期望：缺第 4 条字段 ⇒ RECEIPT_INCOMPLETE；实际 {v['verdict']}")

    v = streak_verdict(runs=_synthetic(["GREEN"] * 2), rounds=2,
                       **dict(base, run_shape="", command=""))
    assert v["verdict"].startswith("RECEIPT_INCOMPLETE"), (
        f"期望：没写形制/命令 ⇒ 第 9 条直接判收据不完整；实际 {v['verdict']}")

    dirty = streak_verdict(runs=_synthetic(["GREEN"] * 2), rounds=2,
                           clause6_command_surface_clean=False,
                           clause6_command_surface_hits=["--reruns"], **base)
    assert dirty["verdict"].startswith("HARNESS_INVALID_relaxed_command_surface"), (
        f"期望：命令面有放宽开关 ⇒ 量具不合法，**两模式都硬判**；实际 {dirty['verdict']}")

    forbidden = _synthetic(["GREEN"] * 2, paths=["D:/moodle/CityNexus/_live.db",
                                                "C:/tmp/cnx_pytest_x/suite.db"])
    v = streak_verdict(runs=forbidden, rounds=2, **base)
    assert v["verdict"] == "ABORT_FORBIDDEN_TARGET", (
        f"期望：解析路径里出现 _live.db ⇒ 立刻中止，红绿都不许往下算；实际 {v['verdict']}")


def test_5e_ten_distinct_but_pre_existing_databases_are_never_a_streak():
    """仲裁第三次源审 §3 点名的洞：

    > `streak_verdict()` 只检查 `initial_row_counts` 字段存在 ⇒
    > 10 个不同但**预先存在**的库全绿仍可能 `STREAK_MET(10)`。

    所以判据必须长在**共享模块**里（谁调都躲不过），这里逐格试：
    预先存在 / 路径靠差集猜 / 压根没量过 —— 三格都不得出 streak，正向对照必须仍然绿。
    """

    def rows_with(initial=None, source="app_printed_receipt_line"):
        rows = _synthetic(["GREEN"] * 10)
        for row in rows:
            if initial is not None:
                row["initial_row_counts"] = dict(initial)
            row["path_source"] = source
        return rows

    stale = streak_verdict(runs=rows_with({"absent": False, "journeys": 4182,
                                          "path_did_not_exist_before_this_run": False}),
                           rounds=10, sha="800b682", target_nodeid=TARGET_NODEID,
                           run_shape=SINGLE_NODE, command="pytest " + TARGET_NODEID,
                           run_shape_verified=True, clause6_declared=True,
                           independence_declared=True,
                           reverse_mutation_required=True, reverse_mutation_result="KILLED")
    assert stale["checks"]["every_run_fresh"] is False, (
        "期望：库在本次进程之前就存在 ⇒ every_run_fresh False")
    assert stale["verdict"].startswith("HARNESS_INVALID_run_not_fresh"), (
        f"期望：这种批次具名判量具不合法，**不得** STREAK_MET；实际 {stale["verdict"]}")
    assert stale["closure_allowed"] is False and stale["closure_grade"] == "NOT_MET", (
        f"期望不可结案；实际 {stale['closure_allowed']}/{stale['closure_grade']}")
    assert any("every_run_fresh" in p for p in receipt_problems(stale)), (
        f"期望 receipt_problems 点名 freshness 这一格；实际 {receipt_problems(stale)[:3]}")

    inferred = streak_verdict(runs=rows_with({"absent": True,
                                             "path_did_not_exist_before_this_run": True},
                                             source="temp_dir_diff_only"),
                              rounds=10, sha="800b682", target_nodeid=TARGET_NODEID,
                              run_shape=SINGLE_NODE, command="pytest " + TARGET_NODEID,
                              run_shape_verified=True)
    assert inferred["verdict"].startswith("HARNESS_INVALID_run_not_fresh"), (
        f"期望：路径是差集猜出来的也不算隔离证据；实际 {inferred["verdict"]}")

    unmeasured = streak_verdict(runs=rows_with({"absent": True}),
                                rounds=10, sha="800b682", target_nodeid=TARGET_NODEID,
                                run_shape=SINGLE_NODE, command="pytest " + TARGET_NODEID,
                                run_shape_verified=True)
    assert unmeasured["verdict"].startswith("HARNESS_INVALID_run_not_fresh"), (
        f"期望：没量过跑前状态 = 不知道新不新 ⇒ fail-closed；"
        f"实际 {unmeasured["verdict"]}")

    fresh = streak_verdict(runs=rows_with({"absent": True,
                                          "path_did_not_exist_before_this_run": True}),
                           rounds=10, sha="800b682", target_nodeid=TARGET_NODEID,
                           run_shape=SINGLE_NODE, command="pytest " + TARGET_NODEID,
                           run_shape_verified=True, clause6_declared=True,
                           independence_declared=True,
                           reverse_mutation_required=True, reverse_mutation_result="KILLED")
    assert fresh["verdict"] == "STREAK_MET(10)" and fresh["closure_allowed"] is True, (
        f"期望正向对照：三格都真量到 fresh 时 streak 与结案照常成立（判据不是无脑拒绝）；"
        f"实际 {fresh['verdict']}/{fresh['closure_allowed']}")
    assert receipt_problems(fresh) == [], f"期望齐证收据合规；实际 {receipt_problems(fresh)[:3]}"


def test_5b_exit_code_five_is_not_a_green_run():
    """最容易被自己骗的一格：`collected 0` 的退出码是 5，"没报错"不等于"跑绿了"。

    这一格的 `node_outcome` **必须从退出码算出来** —— 我第一版把它写成字面量 `NOT_OBSERVED`，
    于是"把未知退出码读成绿"的突变过去时这条仍然全绿（`M2` 那次实测就是这么暴露的）。
    """

    derived = [node_outcome_from_exit(5, run_shape=SINGLE_NODE,
                                      nodeids_in_command=[TARGET_NODEID]) for _ in range(10)]
    assert derived == ["NOT_OBSERVED"] * 10, (
        f"期望：退出码 5（collected 0）逐次都读成 NOT_OBSERVED；实际去重后 {sorted(set(derived))}")
    v = streak_verdict(
        runs=[{"run_index": i + 1, "exit_code": 5, "node_outcome": derived[i],
               "resolved_absolute_db_path": _paths(10)[i],
               "path_source": "app_printed_receipt_line",
               "child_decoder": "stdout=utf-8;stderr=utf-8",
               "initial_row_counts": {"absent": True,
                                      "path_did_not_exist_before_this_run": True},
               "final_row_counts": {"absent": True}}
              for i in range(10)],
        rounds=10, sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        command="pytest " + TARGET_NODEID, run_shape_verified=True)
    assert v["green"] == 0 and v["not_observed"] == 10, (
        f"期望：10 次 collected=0 ⇒ 绿 0、未观测 10；实际 绿 {v['green']} 未观测 {v['not_observed']}")
    assert v["verdict"].startswith("HARNESS_INVALID_target_verdict_not_scoped"), (
        f"期望：这种『全都没跑』的批次判成量具不合法，而不是 STREAK_MET；实际 {v['verdict']}")


def test_5d_host_contention_is_recorded_but_never_moves_a_verdict():
    """我加这一格是**为了记录**，不是为了多一条验收：冻结的是十条，我不替仲裁加第十一条。"""

    quiet = _fake_receipt([_fake_row(1, _paths(2)[0]), _fake_row(2, _paths(2)[1])],
                          ["RED", "RED"])
    busy_rows = [_fake_row(1, _paths(2)[0]), _fake_row(2, _paths(2)[1])]
    for row in busy_rows:
        row["foreign_temp_dirs_during_this_run"] = 9
    busy = _fake_receipt(busy_rows, ["RED", "RED"])

    assert busy["verdict"] == quiet["verdict"] == "STREAK_NOT_MET(0/2_green)", (
        f"期望：邻居进程多少**不改变** streak 结论；实际 quiet={quiet['verdict']}"
        f" busy={busy['verdict']}")
    assert busy["classification"]["named_shape"] == quiet["classification"]["named_shape"], (
        f"期望：定性同样不受影响；实际 {busy['classification']['named_shape']}"
        f" vs {quiet['classification']['named_shape']}")
    assert all(isinstance(r["foreign_temp_dirs_during_this_run"], int) for r in busy["runs"]), (
        "期望：这一格是量出来的整数，不是写死的字符串")


def test_5c_only_the_single_node_shape_may_read_a_verdict_off_the_exit_code():
    assert node_outcome_from_exit(0, run_shape=SINGLE_NODE, nodeids_in_command=[TARGET_NODEID]) \
        == "GREEN"
    assert node_outcome_from_exit(1, run_shape=SINGLE_NODE, nodeids_in_command=[TARGET_NODEID]) \
        == "RED"
    for code in (2, 3, 4, 5, None):
        assert node_outcome_from_exit(code, run_shape=SINGLE_NODE,
                                      nodeids_in_command=[TARGET_NODEID]) == "NOT_OBSERVED", (
            f"期望：退出码 {code}（中断/内部错/用法错/收集 0 条）读不出目标节点判定")
    whole = streak_verdict(runs=_synthetic(["GREEN"] * 2), rounds=2,
                           sha="50b35e0", target_nodeid=TARGET_NODEID,
                           run_shape=WHOLE_FILE, command="pytest tests/")
    assert whole["checks"]["all_green"] is True, (
        "（内部一致性）合成 run 全绿时 all_green 该为 True —— 若这句红，是本测试自己坏了")
    assert node_outcome_from_exit(1, run_shape=WHOLE_FILE,
                                  nodeids_in_command=[TARGET_NODEID, "other::g5"]) == "NOT_OBSERVED", (
        "期望：多节点容器红 ≠ 目标节点红（第 10 条原话）；这一格必须永远读不出判定")


# ======================================================================================
# 6 · 词表与契约对齐（免得门和契约各长一套名字）
# ======================================================================================
def test_6_the_frozen_vocabulary_matches_the_contract():
    import yaml

    contract = REPO / "contracts" / "gate-acceptance-streak.yaml"
    assert contract.is_file(), f"期望契约 {contract} 存在（词表的单一权威）"
    doc = yaml.safe_load(contract.read_text(encoding="utf-8"))
    assert doc["id"] == "GATE_ACCEPTANCE_STREAK_V1", f"实际 {doc['id']!r}"
    assert tuple(doc["run_shapes"]) == RUN_SHAPES, (
        f"期望形制词表与契约逐项相同（顺序即文档顺序）；契约 {doc['run_shapes']} / 判据 {RUN_SHAPES}")
    assert tuple(doc["target_node_classifications"]) == CLASSIFICATIONS, (
        f"期望定性词表一致；契约 {doc['target_node_classifications']} / 判据 {CLASSIFICATIONS}")
    rules = doc["shared_state_rules"]
    assert "FLIP_WITHOUT_SHARED_STATE" in rules["different_fresh_db_paths_and_still_flips"], (
        f"期望契约把'不同新库还翻'指向 FLIP；实际 {rules}")
    assert "ISOLATION_BREACH" in rules["same_resolved_db_path_and_verdict_changes"], (
        f"期望契约把'同库+判定变化'指向 ISOLATION_BREACH；实际 {rules}")
    assert set(doc["clauses"]) == set(range(1, 11)), (
        f"期望契约十条齐全（1..10）；实际 {sorted(doc['clauses'])}")
    # —— 字段名单与门/判据必须逐项同序：commander 补第 9/10 条时按这张表出字段就能直接喂进来 ——
    assert tuple(doc["required_per_run_fields"]) == REQUIRED_RUN_FIELDS, (
        f"期望逐 run 字段与判据的 REQUIRED_RUN_FIELDS 逐项同序（含 node_outcome 这一格）；"
        f"契约 {doc['required_per_run_fields']} / 判据 {list(REQUIRED_RUN_FIELDS)}")
    assert tuple(doc["required_receipt_fields"]) == REQUIRED_RECEIPT_FIELDS, (
        f"期望收据头字段同序；契约 {doc['required_receipt_fields']} / "
        f"判据 {list(REQUIRED_RECEIPT_FIELDS)}")
    assert list(doc["required_for_closure"]) == ["clause6_declaration"], (
        f"期望只有第 6b 条的自证文本是**结案**必填而非收据合规项；"
        f"实际 {doc['required_for_closure']}")
    for banned in doc["not_accepted"]:
        assert isinstance(banned, str) and banned.strip(), (
            f"期望 not_accepted 每条都是非空句子；实际 {banned!r}")
    # —— 源审计 5775293071 新增的四节也要与代码同表，不能只写在文档里 ——
    assert set(doc["closure_ladder"]) == {"NOT_MET", "STREAK_GREEN", "CLOSED"}, (
        f"期望结案三档名字与判据一致；实际 {sorted(doc['closure_ladder'])}")
    assert tuple(doc["reverse_mutation"]["closure_grade_results"]) == \
        CLOSURE_GRADE_REVERSE_RESULTS, (
        f"期望结案级反向突变结果与判据同序；契约 {doc['reverse_mutation']['closure_grade_results']}"
        f" / 判据 {list(CLOSURE_GRADE_REVERSE_RESULTS)}")
    scope = str(doc["measurement_only"])
    assert "ORD-0218" in scope, (
        f"期望 g5 被列成 measurement-only（源审计 ④），不在这张表上结案；实际 {scope[:120]!r}")
    assert "ORD-0218" not in str(doc["applies_to"]), (
        f"期望 applies_to 里不再把 g5 当结案门；实际 {doc['applies_to']!r}")
    argv_tail = [str(x) for x in doc["run_shape_argv"]["single-node"]][-2:]
    assert tuple(argv_tail) == SHAPE_REQUIRED_FLAGS[SINGLE_NODE], (
        f"期望契约的单节点 argv 尾巴与判据一致；契约 {argv_tail} / "
        f"判据 {list(SHAPE_REQUIRED_FLAGS[SINGLE_NODE])}")
    corrob = doc["outcome_corroboration"]["helpers"]
    import _qoder_streak_receipt as _shared
    for helper in corrob:
        assert callable(getattr(_shared, helper, None)), (
            f"期望契约点名的佐证函数真的存在且可调用：{helper}；共享模块里没有这个名字")
    assert "skip" in str(doc["outcome_corroboration"]["channel"]).lower(), (
        f"期望契约写清假绿通道的成因（skip ⇒ exit 0）；实际 "
        f"{doc['outcome_corroboration']['channel']!r}")
    fresh_doc = doc["freshness_predicate"]
    assert "streak_verdict" in str(fresh_doc["lives_in"]), (
        f"期望契约写明 freshness 判据长在结论函数里（不在某扇门里）；实际 {fresh_doc['lives_in']!r}")
    stale_row = _fake_row(1, _paths(1)[0])
    stale_row["initial_row_counts"] = {"absent": False, "journeys": 7,
                                      "path_did_not_exist_before_this_run": False}
    assert run_freshness_problems(stale_row), (
        "期望：预先存在的库被共享判据点名（这条红 = 判据又退回只在门里）")
    stale_row2 = _fake_row(2, _paths(1)[0])
    stale_row2["initial_row_counts"] = {"absent": True}
    assert any("path_did_not_exist_before_this_run" in m for m in run_freshness_problems(stale_row2)), (
        f"期望：没量过跑前状态也算不合规；实际 {run_freshness_problems(stale_row2)}")
    assert not run_freshness_problems(_fake_row(3, _paths(1)[0])), (
        f"期望正向对照：齐证的行判为干净；实际 {run_freshness_problems(_fake_row(3, _paths(1)[0]))}")
    stale_probe = streak_verdict(
        runs=[dict(_fake_row(i + 1, _paths(10)[i]),
                   initial_row_counts={"absent": False,
                                       "path_did_not_exist_before_this_run": False})
              for i in range(2)],
        rounds=2, sha="418c37a", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        command="pytest " + TARGET_NODEID, run_shape_verified=True)
    assert stale_probe["verdict"].startswith(str(fresh_doc["verdict_when_violated"])), (
        f"期望契约写的 verdict 名字与阶梯实际产出一致（契约 {fresh_doc['verdict_when_violated']!r}）；"
        f"实际 {stale_probe['verdict'][:70]!r}")
    assert "replace" in str(doc["reader_chain"]["never"]), (
        f"期望契约把 errors=\"replace\" 明确列为禁止；实际 {doc['reader_chain']['never']!r}")


# ======================================================================================
# 7 · 成本与放宽护栏：这套形状不许被自己人悄悄改宽
# ======================================================================================
def test_7_the_door_cannot_be_relaxed_by_its_own_knobs():
    assert MECHANISM_ROUNDS >= 2, (
        f"期望：机制模式至少 2 个进程，否则'逐 run 互不相同'根本无从谈起；实际 {MECHANISM_ROUNDS}")
    assert MECHANISM_ROUNDS <= 3, (
        f"期望：机制模式常驻套件，轮数要小（P5：不养大套件成本）；实际 {MECHANISM_ROUNDS}")
    assert ACCEPTANCE_ROUNDS == 10, (
        f"期望：第 2 条的数字是 10，改这个数就是改仲裁的冻结；实际 {ACCEPTANCE_ROUNDS}")
    assert RUN_SHAPE in RUN_SHAPES and RUN_SHAPE == SINGLE_NODE, (
        f"期望：本门自己的形制只能是 single-node（命令里就点名一条）；实际 {RUN_SHAPE!r}")
    clean, hits = clause6_command_surface(_argv())
    assert clean, (
        f"期望：本门跑靶子的命令面干净；实际命中放宽开关 {hits} —— 那就是我自己违反了第 6 条")
    assert not clause6_command_surface(["pytest", "x::y", "--reruns", "3"])[0], (
        "期望：扫描器对 --reruns 报警（否则这句判据是空炮）")
    assert not clause6_command_surface(["pytest", "x::y", "--collect-only"])[0], (
        "期望：只收集的一批 run 绝不能被当 10 次绿")
    assert clause6_command_surface(["pytest", "x::retry_window_gate", "-p", "no:randomly"])[0], (
        "期望：nodeid 里带 'retry' 这种词不算放宽（避免把判据做成误伤机器）")


# ======================================================================================
# 8-11 · 源审计 5775293071 ①②③ 的反例：每一格都要"真字节 / 真 argv / 真 guard 读数"
# ======================================================================================
def test_8_the_byte_reader_handles_gb18030_invalid_bytes_and_valid_utf8(tmp_path):
    """源审计 ①：文本必须先读**完整字节**，再按 UTF-8 → gb18030 → surrogateescape 回退。

    三张真文件 + 一段真粘连，不是我口头描述的形状。
    """

    hanzi = "仓鼠王·受保护承诺"
    p_gb = tmp_path / "gb18030.txt"
    p_gb.write_bytes(hanzi.encode("gb18030"))
    text_gb, codec_gb = decode_child_text(read_text_bytes(p_gb))
    assert text_gb == hanzi and codec_gb == "gb18030", (
        f"期望：真 gb18030 字节用 gb18030 档解回原文；实际 text={text_gb!r} codec={codec_gb!r}")
    assert "\ufffd" not in text_gb, "期望：不许出现静默替换字符（那会把一行收据伪装成不存在）"

    p_bad = tmp_path / "invalid.bin"
    p_bad.write_bytes(b"resolved=C:\\Users\\" + b"\xff\xfe\x81\x40" + b"\\suite.db")
    text_bad, codec_bad = decode_child_text(read_text_bytes(p_bad))
    assert "surrogateescape" in codec_bad and "\ufffd" not in text_bad, (
        f"期望：既不是 UTF-8 也不是 gb18030 的字节走 surrogateescape（可逆、不伪装），"
        f"实际 codec={codec_bad!r} text={text_bad!r}")
    assert text_bad.encode("utf-8", errors="surrogateescape") == p_bad.read_bytes(), (
        "期望：surrogateescape 必须字节可逆 —— 否则路径被改过还看不出来")

    p_ok = tmp_path / "utf8.txt"
    p_ok.write_bytes((RECEIPT_PREFIX + "C:/tmp/cnx_pytest_a/suite.db | declared_by=conftest temp dir\n"
                      ).encode("utf-8"))
    path_ok, why_ok = parse_resolved_path(read_text_bytes(p_ok).decode("utf-8"), "")
    assert path_ok == "C:/tmp/cnx_pytest_a/suite.db" and why_ok == "app_printed_receipt_line", (
        f"期望：合法 UTF-8 收据行正常解析；实际 {path_ok!r} / {why_ok!r}")

    glued = "09:12:03 WARNING something " + RECEIPT_PREFIX + "C:/tmp/x/suite.db"
    path_try, why_try = parse_resolved_path(glued, "")
    assert path_try == "", (
        f"期望：前缀前还有内容（跨流粘连的形状）⇒ 拒绝，不交一条被改坏的路径；实际 {path_try!r}")
    assert "粘连" in why_try or "截断" in why_try, f"实际原因句：{why_try!r}"
    # 双向对照：同一行没有前缀污染时必须能取到路径（证明上面那条红不是无脑拒绝）
    clean_line = RECEIPT_PREFIX + "C:/tmp/x/suite.db | declared_by=conftest temp dir"
    assert parse_resolved_path(clean_line, "")[0] == "C:/tmp/x/suite.db"


def test_9_the_single_node_shape_cannot_be_backed_by_other_argv():
    """源审计 ③：形制不能只靠一个自由文本字段声明 —— argv 必须逐字属于那一形。"""

    frozen = shape_command(SINGLE_NODE, [TARGET_NODEID])
    assert frozen == ["-m", "pytest", TARGET_NODEID, "--tb=short", "--import-mode=importlib"], (
        f"期望：单节点形制的命令面正好是冻结的那一串；实际 {frozen[1:]}")
    assert _argv()[1:] == frozen, (
        f"期望：本门跑的 argv 与冻结形制逐项相同；实际 {_argv()[1:]}")
    for stray in ("-rA", "-p"):
        assert stray not in _argv(), f"期望：形制 argv 里不许有 {stray}（它会把报告混进 stdout / 改跑法）"

    verified = verify_run_shape(run_shape=SINGLE_NODE, argv=_argv(), nodeids=[TARGET_NODEID],
                               nodeids_in_command=[TARGET_NODEID], streams_separate=True,
                               decoder="stdout=utf-8;stderr=utf-8")
    assert verified["run_shape_verified"] is True, (
        f"期望：本门的真 argv 过校验（这条红说明校验器自己坏了）；实际 {verified['problems']}")

    # 反例 A：拿"带前序门"的命令冒充 single-node
    preceded = [sys.executable, "-m", "pytest", "tests/a.py::g1", "tests/a.py::g2",
                "--tb=short", "--import-mode=importlib"]
    bad_a = verify_run_shape(run_shape=SINGLE_NODE, argv=preceded, nodeids=[TARGET_NODEID],
                             nodeids_in_command=[TARGET_NODEID], streams_separate=True,
                             decoder="stdout=utf-8;stderr=utf-8")
    assert bad_a["run_shape_verified"] is False and any(
        "2 条 selector" in m for m in bad_a["problems"]), (
        f"期望：single-node 声明配多节点 argv ⇒ 拒收；实际 {bad_a['problems']}")

    # 反例 B：多带一条 selector 的命令冒充 clean single-node
    # （仲裁第四次源审点名的洞；**我第一版把这一格断言成 True**，等于把洞写成了"正确行为"。）
    cross = [sys.executable, "-m", "pytest", TARGET_NODEID, "--tb=short",
             "--import-mode=importlib", "tests/seed.py::test_seed"]
    bad_b = verify_run_shape(run_shape=SINGLE_NODE, argv=cross, nodeids=[TARGET_NODEID],
                             nodeids_in_command=[TARGET_NODEID], streams_separate=True,
                             decoder="stdout=utf-8;stderr=utf-8")
    assert bad_b["run_shape_verified"] is False, (
        f"期望：single-node 声明却抽出 2 条 selector ⇒ 必须拒（形制不能靠'包含'成立）；"
        f"实际通过校验，argv_selectors={bad_b['argv_selectors']}")
    assert any("2 条 selector" in p for p in bad_b["problems"]), (
        f"期望具名指出多带 selector；实际 {bad_b['problems'][:2]}")
    assert len(bad_b["argv_selectors"]) == 2, (
        f"期望返回值里就带上抽出来的 selector，便于别人复核；实际 {bad_b['argv_selectors']}")
    claim = verify_run_shape(run_shape=SINGLE_NODE, argv=cross, nodeids=[TARGET_NODEID],
                             nodeids_in_command=cross[3:], streams_separate=True,
                             decoder="stdout=utf-8;stderr=utf-8")
    assert claim["run_shape_verified"] is False, (
        "期望：调用方**声称**的 nodeids_in_command 要与从 argv 抽出的逐项相等，声称不被采信")
    bad_c = verify_run_shape(run_shape=SINGLE_NODE, argv=[sys.executable, "-m", "pytest",
                                                         TARGET_NODEID, "--tb=short"],
                             nodeids=[TARGET_NODEID], nodeids_in_command=[TARGET_NODEID],
                             streams_separate=True, decoder="stdout=utf-8;stderr=utf-8")
    assert any("--import-mode=importlib" in p for p in bad_c["problems"]), (
        f"期望：缺 `--import-mode=importlib` 的 argv 不算冻结形制；实际 {bad_c['problems']}")
    bad_d = verify_run_shape(run_shape=SINGLE_NODE, argv=_argv(), nodeids=[TARGET_NODEID],
                             nodeids_in_command=["tests/other.py::g5"], streams_separate=True,
                             decoder="stdout=utf-8;stderr=utf-8")
    assert bad_d["run_shape_verified"] is False, (
        f"期望：命令里点名的 nodeid 与声明的 target 不符 ⇒ 拒收；实际 {bad_d['problems']}")
    bad_e = verify_run_shape(run_shape=SINGLE_NODE, argv=_argv(), nodeids=[TARGET_NODEID],
                             nodeids_in_command=[TARGET_NODEID], streams_separate=False,
                             decoder="stdout=utf-8;stderr=utf-8")
    assert any("拼成了一坨" in p for p in bad_e["problems"]), (
        f"期望：stdout/stderr 被拼接 ⇒ 形制证据不成立（gate_streak.py 的那格）；{bad_e['problems']}")
    bad_f = verify_run_shape(run_shape=SINGLE_NODE, argv=_argv(), nodeids=[TARGET_NODEID],
                             nodeids_in_command=[TARGET_NODEID], streams_separate=True,
                             decoder="stdout=utf-8/surrogateescape;stderr=utf-8/replace")
    assert any("静默替换" in p for p in bad_f["problems"]), (
        f"期望：解码器里有 replace ⇒ 报警；实际 {bad_f['problems']}")

    receipt = _fake_receipt([_fake_row(i + 1, _paths(10)[i]) for i in range(10)],
                            ["GREEN"] * 10, shape_verified=False)
    assert receipt["verdict"].startswith("HARNESS_INVALID_run_shape_unverified"), (
        f"期望：形制没校验过 ⇒ streak_verdict 不出结论（第 9 条）；实际 {receipt['verdict']}")


def test_9c_selector_parsing_does_not_invent_or_miss_selectors():
    """`parse_pytest_selectors` 本身也要双向钉：多抽一个就把正例判死，少抽一个就放过假形制。"""

    py = sys.executable
    plain = [py, "-m", "pytest", "tests/a.py::g3", "--tb=short", "--import-mode=importlib"]
    assert parse_pytest_selectors(plain)[0] == ["tests/a.py::g3"], (
        f"期望恰好抽出那一条 selector（`-m pytest` 与两个开关都不是 selector）；"
        f"实际 {parse_pytest_selectors(plain)}")
    spaced = [py, "-m", "pytest", "tests/a.py::g3", "--tb", "short", "--import-mode=importlib"]
    assert parse_pytest_selectors(spaced)[0] == ["tests/a.py::g3"], (
        f"期望 `--tb short` 的取值 `short` 不被当成 selector；实际 {parse_pytest_selectors(spaced)}")
    file_only = [py, "-m", "pytest", "tests/a.py", "--tb=short", "--import-mode=importlib"]
    assert parse_pytest_selectors(file_only)[0] == ["tests/a.py"], (
        f"期望 whole-file 的 selector 抽得到；实际 {parse_pytest_selectors(file_only)}")
    empty = [py, "-m", "pytest", "--tb=short", "--import-mode=importlib"]
    assert parse_pytest_selectors(empty)[0] == [], (
        f"期望没有 selector 时抽出空列表（不能把 --tb=short 当 selector）；"
        f"实际 {parse_pytest_selectors(empty)}")
    v = verify_run_shape(run_shape=SINGLE_NODE, argv=empty, nodeids=[TARGET_NODEID],
                        nodeids_in_command=[TARGET_NODEID], streams_separate=True,
                        decoder="stdout=utf-8;stderr=utf-8")
    assert v["run_shape_verified"] is False and any(
        "抽不出任何 positional selector" in m for m in v["problems"]), (
        f"期望：没有 selector 的命令不许被签成任何形制；实际 {v['problems'][:2]}")
    # 声明与实际相等才放行（顺序也是判据的一部分）
    two = [py, "-m", "pytest", "g1", "g2", "--tb=short", "--import-mode=importlib"]
    same = verify_run_shape(run_shape=NODE_WITH_PRECEDING_DOORS, argv=two,
                           nodeids=["g1", "g2"], nodeids_in_command=["g1", "g2"],
                           streams_separate=True, decoder="stdout=utf-8;stderr=utf-8")
    diff = verify_run_shape(run_shape=NODE_WITH_PRECEDING_DOORS, argv=two,
                           nodeids=["g2", "g1"], nodeids_in_command=["g2", "g1"],
                           streams_separate=True, decoder="stdout=utf-8;stderr=utf-8")
    assert same["run_shape_verified"] is True, (
        f"期望正向对照：逐项同序相等 ⇒ 放行；实际 {same['problems'][:2]}")
    assert diff["run_shape_verified"] is False and any(
        "同序" in m for m in diff["problems"]), (
        f"期望：声明顺序与 argv 不一致 ⇒ 拒（顺序也是形制的一部分）；实际 {diff['problems'][:2]}")


def test_9b_a_skipped_target_is_never_counted_as_a_green_run():
    """实测出来的假绿通道（我这把尺自己的）：整条 `@pytest.mark.skip` ⇒ pytest **exit 0**，
    而 `node_outcome_from_exit(0)` 会说 GREEN ⇒ 十条 skipped 就能拼出 `STREAK_MET(10)`。

    用**真子进程**验三件：先证 exit 真的是 0（不成立就没有通道要堵），再证佐证层把它降级，
    最后拿正向对照证明降级不是无脑拒绝（真跑过的 GREEN/RED 必须保留）。
    """

    import tempfile

    root = pathlib.Path(tempfile.mkdtemp(prefix="cnx_f_skipprobe_"))
    (root / "pytest.ini").write_text("[pytest]" + chr(10), encoding="utf-8")
    node = "test_probe.py::test_probe_case"
    skipped_src = (
        "import pytest" + chr(10) * 2
        + "@pytest.mark.skip(reason='ORD-0210 假绿通道探针')" + chr(10)
        + "def test_probe_case():" + chr(10) + "    assert True" + chr(10)
    )
    (root / "test_probe.py").write_text(skipped_src, encoding="utf-8")
    argv = [sys.executable, "-m", "pytest", node, "--tb=short", "--import-mode=importlib"]

    proc = subprocess.run(argv, cwd=str(root), capture_output=True, timeout=300)
    stdout, _ = decode_child_text(proc.stdout or b"")
    counts = summarize_pytest_counts(stdout)
    assert proc.returncode == 0, (
        f"（前提）这条 skipped 探针的 exit 应当是 0 —— 不是 0 就没有假绿可堵；"
        f"实际 {proc.returncode}；摘要 {stdout.splitlines()[-1:]!r}")
    assert counts.get("skipped", 0) >= 1 and counts.get("passed", 0) == 0, (
        f"期望摘要读到『skipped≥1 且 passed=0』；实际 {counts}")

    raw = node_outcome_from_exit(proc.returncode, run_shape=SINGLE_NODE,
                                nodeids_in_command=[node])
    assert raw == "GREEN", (
        f"（前提）旧口径会说绿；这一格红说明旧口径已经改过，本测试的前提要重估。实际 {raw}")
    fixed, why = corroborate_node_outcome(raw, run_shape=SINGLE_NODE, counts=counts)
    assert fixed == "NOT_OBSERVED", (
        f"期望：exit 0 但 passed=0 ⇒ 降级 NOT_OBSERVED；实际 {fixed} / {why[:120]}")

    rows = []
    for i in range(10):
        row = _fake_row(i + 1, _paths(10)[i])
        row.update(node_outcome="NOT_OBSERVED", exit_code=0, pytest_counts=dict(counts))
        rows.append(row)
    receipt = streak_verdict(runs=rows, rounds=10, sha="800b682", target_nodeid=node,
                            run_shape=SINGLE_NODE, command=" ".join(argv[1:]),
                            run_shape_verified=True, clause6_declared=True,
                            independence_declared=True)
    assert receipt["green"] == 0, f"期望十条 skipped 的绿数为 0；实际 {receipt['green']}"
    assert receipt["verdict"].startswith("HARNESS_INVALID_target_verdict_not_scoped"), (
        f"期望：这种批次判量具不合法，**绝不** STREAK_MET；实际 {receipt['verdict']}")
    assert receipt["closure_allowed"] is False and receipt["closure_grade"] == "NOT_MET", (
        f"期望不可结案；实际 {receipt['closure_allowed']}/{receipt['closure_grade']}")
    assert any("no_unobserved_run" in p for p in receipt_problems(receipt)), (
        f"期望 receipt_problems 点名这一格；实际 {receipt_problems(receipt)}")

    (root / "test_probe.py").write_text(
        "def test_probe_case():" + chr(10) + "    assert True" + chr(10), encoding="utf-8")
    proc2 = subprocess.run(argv, cwd=str(root), capture_output=True, timeout=300)
    stdout2, _ = decode_child_text(proc2.stdout or b"")
    counts2 = summarize_pytest_counts(stdout2)
    kept, why2 = corroborate_node_outcome("GREEN", run_shape=SINGLE_NODE, counts=counts2)
    assert proc2.returncode == 0 and kept == "GREEN" and "一致" in why2, (
        f"期望正向对照：真通过的一轮 GREEN 必须保留（不然判据就是误伤机器）；"
        f"实际 exit={proc2.returncode} kept={kept} counts={counts2} why={why2[:80]}")
    kept_red, why_red = corroborate_node_outcome("RED", run_shape=SINGLE_NODE,
                                                counts={"failed": 1})
    assert kept_red == "RED", f"期望 failed=1 时 RED 保留；实际 {kept_red} / {why_red[:80]}"
    no_counts, why_nc = corroborate_node_outcome("GREEN", run_shape=SINGLE_NODE, counts=None)
    assert no_counts == "NOT_OBSERVED", (
        f"期望：没计数就没佐证 ⇒ fail-closed 降级；实际 {no_counts} / {why_nc[:80]}")


def test_10_the_ledger_anchor_guard_is_machine_gated_not_a_promise():
    """源审计 ②：我不许再靠话说"写前写后各跑了一次 guard"。门里真跑它。"""

    import importlib.util

    guard_path = next((pathlib.Path(p) for p in ANCHOR_GUARD_PATHS
                       if pathlib.Path(p).is_file()), None)
    assert guard_path is not None, (
        f"期望找到 commander 的 `ledger_anchor_guard.py`（候选 {ANCHOR_GUARD_PATHS}）——"
        "它是 guard 的唯一实现，我没有也不该有第二份")
    spec = importlib.util.spec_from_file_location("_cnx_ledger_anchor_guard", str(guard_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, "board_start", None)), (
        f"期望 guard 暴露 board_start()：{[n for n in dir(module) if not n.startswith('_')]}")

    # 账本路径以 **guard 自己的常量**为准：导出树里没有账本，若只看 REPO.parent 这一格就会
    # 永远 skip —— 而正式读数恰恰是在导出树里产的，那等于没装这道闸。
    candidates = [pathlib.Path(str(p)) for p in (
        os.environ.get("CNX_LEDGER_PATH", "").strip(),
        str(getattr(module, "LEDGER", "") or ""),
        str(REPO.parent / LEDGER_NAME)) if str(p or "").strip()]
    ledger = next((c for c in candidates if c.is_file()), None)
    assert ledger is not None, (
        f"期望找到账本本体（候选 {candidates}）；找不到就说明这道闸在本机没有对象，"
        "不许静默 skip")
    lines = read_text_bytes(ledger).decode("utf-8", errors="surrogateescape").splitlines()
    exact = [i for i, line in enumerate(lines) if line.rstrip() == module.HEADING]
    assert len(exact) == 1, (
        f"期望：guard 自己定义的 `HEADING` 在账本里精确出现 1 次（实际 {len(exact)} 次，"
        f"行号 {exact[:4]}）—— 这个标题被整文件重写吃掉过两次，所以只能机器判")
    start = module.board_start(lines)
    assert start is not None and lines[start].startswith("- id: ORD-"), (
        f"期望 board_start() 指向一条 `- id: ORD-` 榜单条目（第 {start} 行 = "
        f"{lines[start][:40]!r}）；它认定不了榜首就没资格当插入锚")
    report = subprocess.run([sys.executable, str(guard_path)], capture_output=True, timeout=120)
    report_text, _ = decode_child_text((report.stdout or b"") + (report.stderr or b""))
    assert report.returncode == 0, (
        f"期望：guard **只报告**（不带 --fix）退出码 0；实际 {report.returncode}，"
        f"输出 {report_text[:200]!r}")
    assert "anchor occurrences: 1" in report_text and "HEALTHY" in report_text, (
        f"期望报告里写着锚点 1 次且 HEALTHY；实际 {report_text[:220]!r}")

    # 我自己的块：落在榜内（标题行之后）、非空、且到下一个 `## ` 为止不被切开。
    f_headings = [i for i, line in enumerate(lines) if line.startswith("## lane F `8ccd71d8`")]
    assert f_headings, "期望账本里至少有一块 lane F 自己的交付块"
    for i in f_headings:
        assert i > exact[0], (
            f"期望 lane F 的块在 `## ORDERS`（第 {exact[0] + 1} 行）之后的榜内；"
            f"实际在第 {i + 1} 行")
        j = i + 1
        while j < len(lines) and not lines[j].startswith("## "):
            j += 1
        assert j - i - 1 >= 3, (
            f"期望第 {i + 1} 行那块有正文（到下一个 `## ` 之前只有 {j - i - 1} 行）")
        assert not any(lines[k].startswith("## ORDERS") for k in range(i + 1, j)), (
            f"期望那块内部不再出现 `## ORDERS`（出现即榜被切碎，插入位置不可信）")


def test_11_a_protected_database_cannot_be_reached_under_another_case():
    """源审计 ③：Windows 大小写不敏感，`_LIVE.DB` 就是 `_live.db`。"""

    assert path_is_forbidden("D:/moodle/CityNexus/_live.db") == "_live.db"
    assert path_is_forbidden("D:/moodle/CityNexus/_LIVE.DB") == "_live.db", (
        "期望：大写的 `_LIVE.DB` 一样被拦（裸字面比较会漏）")
    assert path_is_forbidden("D:\\moodle\\CityNexus\\_Preview.DB") == "_preview.db"
    assert path_is_forbidden("C:/tmp/cnx_pytest_a/suite.db") == "", (
        "期望：正常临时库不该被误拦（双向都试）")
    for shape in ("D:/moodle/CityNexus/_LIVE.DB", "sqlite:///D:/moodle/CityNexus/_Live.db"):
        with pytest.raises(BaseException) as caught:
            _assert_not_user_db(shape)
        assert "_live.db" in str(caught.value), (
            f"期望拒绝信息里点名被保护的库；实际 {str(caught.value)[:140]!r}（输入 {shape}）")
    bad = resolved_path_problems("C:\\Users\\\ufffdan\\Temp\\cnx_pytest_x\\suite.db")
    assert any("解码受损" in p for p in bad), (
        f"期望：路径里出现 U+FFFD ⇒ 这条路径已被解码改坏，必须报警；实际 {bad}")



