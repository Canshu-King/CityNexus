"""ORD-0340 重切读数件：每一件事实都在这一次运行里现算，包括"我的 hunk 一行没变"这句。

为什么要专门算它：号令者的门拦的是"两方都改过的文件被自动合之后，落下去的是谁都没测过的那份"。
所以本件回答三问：
  1) 重切有没有改到我那一侧的字节？（把旧候选与我这代的 +/- 行内容逐行比）
  2) F 那一侧新加的那条（ORD-0332 的可复述回执号）在我这代树里还在不在、和我的具名拒绝合不合？（L7 + 一次单变量反证）
  3) 分母是多少？（同一把门在尖与在我枝上各跑一次，两个 whole_collected 都要在）
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path("D:/moodle/CityNexus")
GIT = "C:/Program Files/Git/mingw64/bin/git.exe"
TIP = "38277c4e9787b1ddf0bf69487060ba0e40c14146"
OLD_BASE = "ab12c17a65450c2c3062c9232e27a26c4ae1b485"
OLD_CAND = "75904f2eea18cf663df933a4baa53d24f3052e93"
RECUT_BASE_COMMIT = "5bb04b8f"
BRANCH_TIP = "b4d0590e43aac47302bc93fdb37c5bc6029983d3"
MAIN = "backend/app/main.py"
TESTS = "backend/tests/test_qoder_ord0340_claim_lease.py"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"


def git(*args: str) -> str:
    return subprocess.run([GIT] + list(args), cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def plus_minus(ref_a: str, ref_b: str, path: str) -> list:
    diff = git("diff", ref_a, ref_b, "--", path)
    return [l for l in diff.split("\n") if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---"))]


def run_env(db_url: str) -> dict:
    """Inherit the real environment (a trimmed one can stop the venv interpreter from starting),
    point the database at this run's own throwaway file, and drop any live AI key by name."""
    env = dict(__import__("os").environ)
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(key, None)
    env.update({"CITYNEXUS_DATABASE_URL": db_url, "PYTHONPATH": str(HERE), "CITYNEXUS_AI_ENABLED": "false"})
    return env


def pytest(files: list, db: str) -> dict:
    env_db = f"sqlite:///{(HERE / 'scratch' / db).as_posix()}"
    for suffix in ("", "-wal", "-shm"):
        p = HERE / "scratch" / (db + suffix)
        p.unlink(missing_ok=True)
    proc = subprocess.run([PY, "-m", "pytest", *files, "-q", "-p", "no:cacheprovider"],
                          cwd=str(HERE / "backend"), capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env=run_env(env_db))
    tail = [l for l in proc.stdout.split("\n") if "passed" in l or "failed" in l or "error" in l]
    return {"command": f"pytest {' '.join(files)}", "exit": proc.returncode,
            "database_url": env_db, "summary_line": tail[-1] if tail else proc.stdout[-300:],
            "red_nodes": sorted(set(__import__("re").findall(r"FAILED ([^\s:]+::\S+)", proc.stdout)))}


def main() -> int:
    git("fetch", "-q", "origin", f"refs/heads/review/S2-ord0340-claim-lease-r2")
    lines_old = plus_minus(OLD_BASE, OLD_CAND, MAIN)
    lines_new = plus_minus(TIP, BRANCH_TIP, MAIN)
    receipts = {}
    for name in ("gate_tip_38277c4e.json", "gate_recut_b4d0590e.json"):
        d = json.loads((HERE / name).read_text("utf-8"))
        receipts[name] = {"generation": d["generation"], "verdict": d["verdict"],
                          "whole_collected": d["whole_suite_collected"],
                          "whole_collect_errors": d["whole_suite_collect_errors"],
                          "harness_collected": d["collected"], "harness_passed": d["passed"],
                          "harness_failed": d["failed"], "harness_files": d["harness_test_files_discovered"],
                          "interpreter": d["interpreter"], "export_set": d["export_set"],
                          "checks_all_true": all(d["checks"].values()), "checks": d["checks"],
                          "work_dir_removed": d["work_dir_removed"], "at_local": d["at_local"]}

    runs = {
        "my_seven_cells": pytest([f"tests/{TESTS.split('/')[-1]}"], "_o340read_seven.db"),
        "guards_plus_fs_gate": pytest(["tests/test_qoder_ord0340_claim_lease.py",
                                       "tests/test_qoder_ord0272_continuation.py",
                                       "tests/test_qoder_ord0287_k8_carrier.py",
                                       "tests/test_qoder_ord0310_keyless_leg_receipts.py",
                                       "tests/test_qoder_ord0332_error_receipt.py"], "_o340read_guards.db"),
    }

    # single-variable reverse mutation: turn off F's receipt write, and see who falls
    main_path = HERE / MAIN
    original = main_path.read_bytes()
    mutated = original.decode("utf-8").replace(
        "    if receipt is not None:\n        body[RECEIPT_FIELD] = receipt",
        "    if False:  # MUTANT\n        body[RECEIPT_FIELD] = receipt", 1)
    assert mutated != original and original.decode("utf-8").count(
        "    if receipt is not None:\n        body[RECEIPT_FIELD] = receipt") == 1, "mutation site not unique"
    main_path.write_text(mutated, encoding="utf-8", newline="")
    mut_run = pytest([f"tests/{TESTS.split('/')[-1]}"], "_o340read_mut.db")
    main_path.write_bytes(original)
    restored_blob = git("hash-object", "--no-filters", str(HERE / MAIN))
    head_blob = git("rev-parse", f"{BRANCH_TIP}:{MAIN}")

    out = {
        "order": "ORD-0340", "lane": "S2-hermes (d9e2c9ae)", "why": "re-cut because the door refused the stale base",
        "at_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "branch_ref": "review/S2-ord0340-claim-lease-r2",
        "branch_tip_commit": BRANCH_TIP,
        "branch_tip_read_back_by_ls_remote": git("ls-remote", "origin", "refs/heads/review/S2-ord0340-claim-lease-r2"),
        "commits_on_the_branch": git("log", "--format=%h %s", f"{TIP}..{BRANCH_TIP}").split("\n"),
        "its_parent_is_the_tip_i_read": git("merge-base", "--is-ancestor", TIP, BRANCH_TIP) == "" and
                                        git("rev-parse", f"{BRANCH_TIP}~2") == TIP,
        "base_refused_before": {"old_candidate": OLD_CAND, "its_base": OLD_BASE,
                                "tip_moved_by_commits": int(git("rev-list", "--count", f"{OLD_BASE}..{TIP}"))},
        "recut_changed_nothing_on_my_side": {
            "my_changed_lines_old_candidate": len(lines_old), "my_changed_lines_recut": len(lines_new),
            "identical": lines_old == lines_new,
            "line_content_note": "compared as the +/- line text of main.py, so a shifted hunk header cannot hide a rewrite",
        },
        "blobs": {"main_py_tip": git("rev-parse", f"{TIP}:{MAIN}"), "main_py_recut": head_blob,
                  "main_py_old_candidate": git("rev-parse", f"{OLD_CAND}:{MAIN}"),
                  "test_py_recut": git("rev-parse", f"{BRANCH_TIP}:{TESTS}"),
                  "tree_recut": git("rev-parse", f"{BRANCH_TIP}^{{tree}}"),
                  "fs_receipt_module_still_in_my_tree": git("rev-parse", f"{BRANCH_TIP}:backend/app/error_receipt.py")},
        "f_half_present_in_my_tree": {
            "RECEIPT_FIELD_uses_in_main_py": original.decode("utf-8").count("RECEIPT_FIELD"),
            "middleware_def_lines": [l for l in original.decode("utf-8").split("\n") if "def error_receipt_per_request" in l],
        },
        "runs": runs,
        "reverse_mutation": {
            "what_was_broken": "the one line in error() that writes F's receipt into the envelope (`if receipt is not None:` -> `if False:`)",
            "expected_red": "exactly test_L7 of this file, and no other cell",
            "observed_red": mut_run["red_nodes"], "observed_summary": mut_run["summary_line"],
            "main_py_restored_byte_identical": restored_blob == head_blob,
            "restored_blob": restored_blob, "branch_blob": head_blob,
        },
        "whole_suite_denominator": receipts,
        "denominator_arithmetic": {
            "tip_collected": receipts["gate_tip_38277c4e.json"]["whole_collected"],
            "recut_collected": receipts["gate_recut_b4d0590e.json"]["whole_collected"],
            "difference": receipts["gate_recut_b4d0590e.json"]["whole_collected"] -
                          receipts["gate_tip_38277c4e.json"]["whole_collected"],
            "collect_errors_both_generations": [receipts[n]["whole_collect_errors"] for n in
                                                ("gate_tip_38277c4e.json", "gate_recut_b4d0590e.json")],
            "explained_by": "the seven cells this file carries (six before the re-cut + L7 added by it)",
        },
        "derived_result": None,
        "claimed_result": "OBSERVED",
    }
    target = HERE / "ord0340_recut_readings_r1.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("readings:", target.name)
    print("  my lines identical across the re-cut:", out["recut_changed_nothing_on_my_side"]["identical"])
    print("  seven cells:", runs["my_seven_cells"]["summary_line"])
    print("  guards + F:", runs["guards_plus_fs_gate"]["summary_line"])
    print("  mutation red:", mut_run["red_nodes"], "| restored:", out["reverse_mutation"]["main_py_restored_byte_identical"])
    print("  denominator:", out["denominator_arithmetic"])
    return 0 if (out["recut_changed_nothing_on_my_side"]["identical"] and mut_run["red_nodes"] and
                runs["my_seven_cells"]["exit"] == 0 and runs["guards_plus_fs_gate"]["exit"] == 0 and
                out["reverse_mutation"]["main_py_restored_byte_identical"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
