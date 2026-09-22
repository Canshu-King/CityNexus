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
    CLASSIFICATIONS,
    FORBIDDEN_DB_NAMES,
    RUN_SHAPES,
    SINGLE_NODE,
    WHOLE_FILE,
    NODE_WITH_PRECEDING_DOORS,
    classify_target_node,
    clause6_command_surface,
    node_outcome_from_exit,
    observation_only,
    receipt_problems,
    streak_verdict,
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

#: 第 2 条是"10 CONSECUTIVE independent processes"，验收模式里这个数字**不许被放宽**。
ACCEPTANCE_ROUNDS = 10
#: 机制模式只为验量具形状，默认 2 个进程（1 个证明不了"逐 run 互不相同"）。
MECHANISM_ROUNDS = 2

#: ORD-0211 在收集期打印的收据行前缀（与 commander 的工具同一个字面，两边不各写一份）。
RECEIPT_PREFIX = "ORD-0211 test database: resolved="

#: 首尾行数读哪几枚表（与 commander 工具的 COUNT_TABLES 对齐；不在就是 NO_TABLE，不编数）。
COUNT_TABLES = ("journeys", "plan_versions", "travelers", "catalog_hydration_operations")

RESOLVED_RE = re.compile(re.escape(RECEIPT_PREFIX) + r"([^\s|]+)")


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
    """跑靶子的**命令面**。刻意没有 -q：`-q` 会把打印 `resolved=` 的 header 段一起压掉
    （commander 15:2x 自己踩过，我第一次也踩过）。"""

    return [_python(), "-m", "pytest", TARGET_NODEID, "--tb=line", "-rA",
            "-p", "no:randomly", "-p", "no:cacheprovider"]


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
    第 1 条要求 exact SHA ⇒ 判据模块会拒收 UNKNOWN。"""

    declared = os.environ.get("CNX_UNDER_TEST_SHA", "").strip()
    if declared:
        return declared
    proc = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() or "UNKNOWN"


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
    if pathlib.Path(str(path)).name in FORBIDDEN_DB_NAMES:
        pytest.fail(
            f"拒绝：本门绝不碰 {path}（{FORBIDDEN_DB_NAMES} 是用户数据与预览真值）"
        )


def _run_once(index: int, before: set[str]) -> dict[str, Any]:
    """跑**一个独立进程**的靶子并攒出第 4/9 条要的逐 run 字段。

    `node_outcome` 只从退出码读，且只在 `RUN_SHAPE == single-node` 时读得出来（第 10 条）；
    退出码 2/3/4/5 ⇒ `NOT_OBSERVED`（**一条都没跑绝不记成绿**）。
    traceback 行只当**诊断文本**打印，不参与判定 —— 否则就又变成"拿输出猜结论"。
    """

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("CITYNEXUS_DATABASE_URL", None)  # 让 conftest 自己钉：证明"app 自己解析"这件事

    argv = _argv()
    proc = subprocess.run(argv, cwd=str(BACKEND), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    output = (proc.stdout or "") + (proc.stderr or "")
    after = _temp_dirs()

    match = RESOLVED_RE.search(output)
    printed = match.group(1) if match else ""
    created = sorted(after - before)
    if printed:
        db_path = printed
    elif created:
        db_path = str(pathlib.Path(created[0]) / "suite.db")
    else:
        db_path = "NOT_PRINTED"
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

    failure = next((ln.strip()[:180] for ln in output.splitlines()
                    if "AssertionError" in ln or ln.strip().startswith("E ")), "")

    # 只记录、不改判：这一轮期间 %TEMP% 里冒出来的**别人家的** cnx_pytest_* 目录，
    # 就是"这台机器当时还有别的车道在跑"的实测证据。并发时序门的读数对机器负载敏感，
    # 而第 10 条的定性范围里（SHA / nodeid / 形制）没有这一格 —— 先把它量下来再说。
    mine = _norm(pathlib.Path(db_path).parent) if db_path != "NOT_PRINTED" else ""
    foreign = sum(1 for d in (after - before) if d != mine)
    return {
        "run_index": index,
        "exit_code": proc.returncode,
        "node_outcome": node_outcome_from_exit(proc.returncode, run_shape=RUN_SHAPE,
                                               nodeids_in_command=[TARGET_NODEID]),
        "resolved_absolute_db_path": db_path,
        "initial_row_counts": initial,
        "final_row_counts": _row_counts(db_path) if db_path != "NOT_PRINTED"
        else {"error": "NO_RESOLVED_PATH_CAPTURED"},
        "path_source": "app_printed_receipt_line" if printed else (
            "temp_dir_diff_only" if created else "NONE"),
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
    receipt = streak_verdict(
        runs=rows, rounds=rounds, sha=sha, target_nodeid=TARGET_NODEID,
        run_shape=RUN_SHAPE, command=" ".join(argv[1:]),
        independence_declared=bool(declared), clause6_declared=bool(declared),
        clause6_command_surface_clean=clean, clause6_command_surface_hits=hits,
    )
    receipt["classification"] = classify_target_node(
        sha=sha, target_nodeid=TARGET_NODEID, run_shape=RUN_SHAPE,
        node_outcomes=outcomes, resolved_db_paths=paths,
    )
    receipt["mode"] = mode
    receipt["clause6_declaration"] = declared or "（未声明）"
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
        f"  命令            = {receipt['command']}   (每 run 一个独立进程)",
        f"  轮数            = {receipt['rounds']}  绿 {receipt['green']} / 红 {receipt['red']}"
        f" / 未观测 {receipt['not_observed']}",
        f"  重复解析路径    = {receipt['duplicate_db_paths']}",
        f"  缺路径的 run    = {receipt['runs_missing_db_path']}",
        f"  第 6 条         = {receipt['clause6_note']}",
        f"  streak 结论     = {receipt['verdict']}",
        f"  可结案          = {receipt['closure_allowed']} (第 5 条绿 + 第 2 条 10 进程 + 第 6b 条自证)",
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
        for key in ("initial_row_counts", "final_row_counts"):
            counts = row.get(key)
            if isinstance(counts, dict) and "error" in counts:
                problems.append(f"run {row['run_index']} 的 {key} 读失败（{counts['error']}）："
                                "解析出来的路径打不开 = 收据里的路径不可信，不是产品红")
        if isinstance(row["initial_row_counts"], dict) \
                and "error" not in row["initial_row_counts"] \
                and not row["initial_row_counts"].get("path_did_not_exist_before_this_run"):
            problems.append(f"run {row['run_index']} 没量到『跑前该路径不存在』"
                            f"（{row['initial_row_counts']}）：第 3 条的 fresh 必须是读出来的")
        if row["path_source"] != "app_printed_receipt_line":
            problems.append(f"run {row['run_index']} 的解析路径不是 app 打印出来的"
                            f"（path_source={row['path_source']}）：第 1 条边界"
                            "『resolved absolute DB path must be printed/receipted』")
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
        "foreign_temp_dirs_during_this_run": 0, "diagnostic_red_line": "",
    }


def _fake_receipt(rows: list[dict[str, Any]], outcomes: list[str],
                  shape_suffix: str = "(single-node)") -> dict[str, Any]:
    argv = _argv()
    clean, hits = clause6_command_surface(argv)
    receipt = streak_verdict(
        runs=rows, rounds=len(rows), sha="50b35e0", target_nodeid=TARGET_NODEID,
        run_shape=RUN_SHAPE, command=" ".join(argv[1:]),
        clause6_command_surface_clean=clean, clause6_command_surface_hits=hits)
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
    assert any("不是 app 打印出来的" in p for p in _instrument_problems(inferred)), (
        "期望：路径只是靠临时目录差集猜出来的 ⇒ 必须报警（第 1 条边界要的是 app 自己打印）；"
        f"实际 {_instrument_problems(inferred)}")

    no_shape = _fake_receipt([_fake_row(1, _paths(2)[0]), _fake_row(2, _paths(2)[1])],
                             ["RED", "GREEN"], shape_suffix="")
    assert any("形制后缀" in p for p in _instrument_problems(no_shape)), (
        "期望：定性结论没带 (<shape>) ⇒ 违反第 9 条，必须报警；"
        f"实际 {_instrument_problems(no_shape)}")

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

    assert receipt["rounds"] == ACCEPTANCE_ROUNDS, (
        f"期望：验收必须 {ACCEPTANCE_ROUNDS} 个连续独立进程（第 2 条）；"
        f"实际 {receipt['rounds']}\n{text}")
    assert receipt["verdict"] == f"STREAK_MET({ACCEPTANCE_ROUNDS})", (
        f"期望：第 5 条『all 10 runs GREEN』；实际 {receipt['verdict']}"
        f"（绿 {receipt['green']}/{receipt['rounds']}）\n{text}")
    assert receipt["classification"]["classification"] == "STABLE_GREEN", (
        f"期望：streak 达成时目标节点定性是 STABLE_GREEN({RUN_SHAPE})；"
        f"实际 {receipt['classification']['named_shape']} —— {receipt['classification']['reason']}")
    if not os.environ.get(DECLARATION_ENV, "").strip():
        assert receipt["closure_allowed"] is False, (
            "期望：没写第 6 条自证文本时 closure_allowed 必须是 False —— 最多签 STREAK_GREEN，"
            "不签 CLOSED（仲裁 15:58 反向要求）。这条断言红 = 判据把'绿'当成了'结案'")


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
               "resolved_absolute_db_path": one_path,
               "initial_row_counts": {"absent": True}, "final_row_counts": {"journeys": i}}
              for i in range(10)],
        rounds=10, sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        command="pytest " + TARGET_NODEID)
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
         "resolved_absolute_db_path": paths[i],
         "initial_row_counts": {"absent": True}, "final_row_counts": {"journeys": 1}}
        for i, o in enumerate(outcomes)]


def test_5_the_streak_ladder_names_every_failure_shape():
    base = dict(sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
                command="pytest " + TARGET_NODEID)

    ok = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10, **base)
    assert ok["verdict"] == "STREAK_MET(10)", (
        f"期望：10 个独立进程全绿 ⇒ STREAK_MET(10)（第 5 条），判据不许只会说红；实际 {ok['verdict']}")
    assert ok["closure_allowed"] is False, "期望：没声明第 6b 条 ⇒ 不签结案"
    declared = streak_verdict(runs=_synthetic(["GREEN"] * 10), rounds=10,
                              clause6_declared=True, independence_declared=True, **base)
    assert declared["closure_allowed"] is True, (
        f"期望：STREAK_MET + 10 进程 + 自证文本齐 ⇒ 可谈结案；实际 {declared['closure_allowed']}")
    assert receipt_problems(declared) == [], (
        f"期望：这份收据合规；实际问题 {receipt_problems(declared)}")

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
               "initial_row_counts": {"absent": True}, "final_row_counts": {"absent": True}}
              for i in range(10)],
        rounds=10, sha="50b35e0", target_nodeid=TARGET_NODEID, run_shape=SINGLE_NODE,
        command="pytest " + TARGET_NODEID)
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
    for banned in doc["not_accepted"]:
        assert isinstance(banned, str) and banned.strip(), (
            f"期望 not_accepted 每条都是非空句子；实际 {banned!r}")


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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v", "-s"]))
