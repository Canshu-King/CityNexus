"""红集合的配对复核：全套里那 11 枚红，逐枚在"尖那一代"与"我这一代"上各跑一遍。

为什么要跑两遍同一批：两棵树的差只有我改的两枚测试文件（`git diff --name-only` 现读），
所以别的 9 枚红如果只在我的代上红，那才是我的责任；它们在两代都红 ⇒ 存量/网络抖动，与这单无关。
状态敏感的那几枚（guardian / ord224 shape-A）按常设规矩两趟读数都留，不写成"无新红"。
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
ROOTS = {"tip_00b5f25e": Path("D:/moodle/_qoder_anchor_rulers_20261002/tipfull_00b5f25e"),
         "branch_5cb0bd0a": Path("D:/moodle/_qoder_anchor_rulers_20261002/branchfull_5cb0bd0a")}
NODES = [
    "tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was",
    "tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction",
    "tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts",
    "tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording",
    "tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls",
    "tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes",
    "tests/test_qoder_city_failure_reasons.py::test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor",
    "tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at",
    "tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation",
    "tests/test_qoder_ord224_g3_generation_measurement.py::test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one",
    "tests/test_sol_guardian_projection.py::test_guardian_status_lists_runs_newest_first",
]
ANCHORS = ["tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place",
           "tests/test_qoder_ord0479_dictionary_key_shape.py::"
           "test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable"]
OUT = Path("D:/moodle/_qoder_anchor_rulers_20261002/red_pair_control_r1.json")


def run(root: Path, nodes: list[str]) -> dict:
    done = subprocess.run([PY, "-m", "pytest", *nodes, "-q", "--tb=no", "-rf",
                           "-p", "no:cacheprovider"], cwd=str(root / "backend"),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=2400)
    txt = (done.stdout or "") + (done.stderr or "")
    red = [l.split("::", 1)[0] + "::" + l.split("::", 1)[1].split(" ")[0]
           for l in txt.splitlines() if l.startswith("FAILED tests/")]
    summary = [l.strip() for l in txt.splitlines() if " passed" in l or "error" in l][-1:]
    return {"rc": done.returncode, "red": sorted(set(red)), "summary": summary,
            "seconds": None}


result = {"started": time.strftime("%m-%d %H:%M:%S"), "trees": {}}
for name, root in ROOTS.items():
    t0 = time.time()
    result["trees"][name] = {"red11": run(root, NODES), "anchors": run(root, ANCHORS)}
    result["trees"][name]["wall_seconds"] = round(time.time() - t0, 1)
    #: 先落盘再算总账：任何后面的算式出错都不该把已经跑完的读数丢掉
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(name, "wall_seconds", result["trees"][name]["wall_seconds"],
          "| red11", result["trees"][name]["red11"]["summary"],
          "| anchors", result["trees"][name]["anchors"]["summary"])
red_tip = result["trees"]["tip_00b5f25e"]["red11"]["red"]
red_branch = result["trees"]["branch_5cb0bd0a"]["red11"]["red"]
result["red11_counts"] = {"tip": len(red_tip), "branch": len(red_branch)}
result["red11_only_in_branch"] = sorted(set(red_branch) - set(red_tip))
result["red11_only_in_tip"] = sorted(set(red_tip) - set(red_branch))
result["red_sets_identical_across_generations"] = set(red_tip) == set(red_branch)
result["anchors_red_by_generation"] = {
    "tip_00b5f25e": result["trees"]["tip_00b5f25e"]["anchors"]["red"],
    "branch_5cb0bd0a": result["trees"]["branch_5cb0bd0a"]["anchors"]["red"]}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", OUT, "| identical:", result["red_sets_identical_across_generations"],
      "| counts:", result["red11_counts"],
      "| only_in_branch:", result["red11_only_in_branch"],
      "| anchors_red tip/branch:", [len(v) for v in result["anchors_red_by_generation"].values()])
