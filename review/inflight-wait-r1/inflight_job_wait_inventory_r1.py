"""读在飞作业尺族清点 - 列出"提交作业之后不等终态就断言结论字段"的测试位置。

为什么要有这张表（点单原话）：这类臂的判据是服务端作业的结论字段，而作业跑在后台线程上；臂不等
终态就读，红不红取决于那一拍线程有没有关，于是整链里出现"同字节两趟不同红"的噪声，别人得替车道
猜是不是自己引入的。产品侧本来自带等待器：两枚都叫 `wait_for_operation`（定义在各模块里，行号由本脚本现读，不写死在注释里以免腐烂）；测试侧的本地形制
是 `_wait_closed` / `_wait_terminal` / `_submit_and_close` 这一类轮询循环（本仓已有一枚臂用了它）。

这个脚本只做一件事：按 AST 逐文件逐测试函数判定"提交点 → 断言点之间有没有等待"，输出可直接派单的
名单（测试 path:line、该模块自带的等待器名、修法一句话）。它不修任何文件。

跑法（cwd=backend）：
    D:/moodle/CityNexus/.venv/Scripts/python.exe ../review/inflight-wait-r1/inflight_job_wait_inventory_r1.py
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
TESTS = BACKEND / "tests"
OUT = Path(__file__).resolve().parent / "INFLIGHT_WAIT_INVENTORY_r1.json"

# what counts as putting a job in flight (product door or module submit)
SUBMIT_MARKERS = (
    "HYDRATIONS",
    "/api/v1/catalog-hydrations",
    "/api/v1/stay-generations",
    "_replay_semantics",
    "_burst_via_route",
    "submit_operation",
)
# a function that runs the work in-process cannot be in flight - these are excluded, not judged
DETERMINISTIC_MARKERS = (
    "start_worker=False",
    "_run_operation(",
    "run_once(",
    "fake_dispatch",
    "replace(operations.dispatch",
    "_store_job(",
)
WAIT_CALL_NAMES = (
    "wait_for_operation",
    "_wait_closed",
    "wait_closed",
    "_wait_terminal",
    "wait_terminal",
    "_submit_and_close",
    "_settled",
    "abandon_operation",
)
WAIT_ATTR_SUFFIXES = (".join",)
TERMINAL_READ_MARKERS = (
    "TERMINAL_STATUSES",
    "COMPLETED",
    "FAILED",
    "UNAVAILABLE",
    "ABANDONED",
    "OPEN_STATUSES",
    "QUEUED",
    "RUNNING",
)
# fields a worker writes after the submit returns - asserting them without waiting is the defect
JOB_FIELDS = (
    "outcome",
    "result_json",
    "error_json",
    "provider_attempts",
    "survey",
    "candidates",
    "canonical_destination_id",
    "pending_destination_label",
    "destination_pending_key",
    "job_status",
)


def calls_and_names(node: ast.AST):
    """Yield (dotted_name, lineno) for every Call and Attribute/Name load in a subtree."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            yield (dotted(sub.func), sub.lineno)
        elif isinstance(sub, (ast.Attribute, ast.Name)):
            yield (dotted(sub), getattr(sub, "lineno", 0))


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return (dotted(node.value) + "." + node.attr) if isinstance(node.value, (ast.Name, ast.Attribute)) else node.attr
    if isinstance(node, ast.Call):
        return dotted(node.func)
    return ""


def source_slice(src: str, node: ast.AST) -> str:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start) or start
    return "\n".join(src.splitlines()[start - 1 : end])


def classify_module_call(body_src: str, names: list[str]) -> str | None:
    for waiter in WAIT_CALL_NAMES:
        if waiter in names:
            return waiter
    if ".join" in body_src or "join(timeout" in body_src:
        return "thread.join"
    if "for _ in range(" in body_src and ("time.sleep" in body_src or "perf_counter" in body_src):
        return "inline poll"
    if any(marker in body_src for marker in TERMINAL_READ_MARKERS) and "while" in body_src:
        return "inline while poll"
    return None


def measure_waiters() -> dict:
    """Line numbers are read now, not remembered - a shipped `:1173` rots the day upstream moves."""

    found = {}
    for rel, needle in (
        ("app/catalog_hydration_operations.py", "def wait_for_operation("),
        ("app/stay_generation_operations.py", "def wait_for_operation("),
        ("app/agent/autorun.py", "def stop_autorun("),
    ):
        path = BACKEND / rel
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        line = next((i for i, l in enumerate(lines, 1) if needle in l), None)
        found[rel] = {"symbol": needle.replace("def ", "").rstrip("("), "definition_line": line}
    return found


def main() -> int:
    files = sorted(p for p in TESTS.glob("*.py"))
    rows = []
    for path in files:
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        file_waiters = sorted({w for w in WAIT_CALL_NAMES if (w + "(") in src})
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
            fsrc = source_slice(src, fn)
            lo, hi = fn.lineno, (fn.end_lineno or fn.lineno)
            if any(marker in fsrc for marker in DETERMINISTIC_MARKERS):
                continue
            submits = sorted({
                ln
                for nm, ln in calls_and_names(fn)
                if any(m in nm for m in SUBMIT_MARKERS) and lo <= ln <= hi
            })
            if not submits:
                continue
            # an assert that reads a job-written field
            asserted = []
            for node in ast.walk(fn):
                if not isinstance(node, ast.Assert):
                    continue
                test_src = source_slice(src, node.test)
                if not lo <= node.lineno <= hi:
                    continue
                if any(('"%s"' % f) in test_src or ("[%s]" % f) in test_src or (".%s" % f) in test_src for f in JOB_FIELDS):
                    asserted.append(node.lineno)
            if not asserted:
                continue
            asserted = [a for a in asserted if a > submits[0]]
            if not asserted:
                continue
            waiter = classify_module_call(fsrc, [nm for nm, _ in calls_and_names(fn)])
            if waiter:
                continue
            rows.append(
                {
                    "test": "backend/tests/%s:%d" % (path.name, submits[0]),
                    "function": fn.name,
                    "submit_at_lines": sorted(set(submits))[:6],
                    "first_job_assert_line": min(asserted),
                    "job_fields_touched": sorted({f for f in JOB_FIELDS if ('"%s"' % f) in fsrc or ("[%s]" % f) in fsrc or (".%s" % f) in fsrc}),
                    "waiter_in_same_file": file_waiters or None,
                    "fix": None,
                }
            )

    for row in rows:
        holders = row["waiter_in_same_file"]
        if holders:
            row["fix"] = "在该断言之前调用本文件已有的 %s（同模块自带等待器）即可闭红" % holders[0]
        else:
            product = "app.catalog_hydration_operations.wait_for_operation" if "hydration" in row["function"] or "g10" in row["function"] else "app.stay_generation_operations.wait_for_operation"
            row["fix"] = "补一次终态等待（本地 _wait_closed 轮询或直接 %s）再断言结论字段" % product

    payload = {
        "generated_by": "89f2e2d6",
        "purpose": "读在飞作业尺族全树清点（可直接派单的名单）",
        "test_files_scanned": len(files),
        "candidate_sites": len(rows),
        "product_waiters": measure_waiters(),
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("test_files_scanned %d" % payload["test_files_scanned"])
    print("candidate_sites %d" % payload["candidate_sites"])
    for row in rows:
        print("%-58s %-46s first-assert:%s waiter-in-file:%s" % (
            row["test"], row["function"][:44], row["first_job_assert_line"],
            ",".join(row["waiter_in_same_file"] or ["NONE"])))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
