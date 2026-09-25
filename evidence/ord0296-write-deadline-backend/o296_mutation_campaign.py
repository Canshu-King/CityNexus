"""ORD-0296 门体的反突变战役：每臂只拆掉我这一笔新加的一道保护，跑三轮，看有没有一格替它红。

规矩（照我自己今晚钉下的形制）：
  * 单变量：每臂一处字面替换，hunks 必须 == 1，改完必须还能 py_compile；
  * 每臂三轮，逐轮记 red；跑完按字节还原并回验 blob（还原不了就整臂作废）；
  * `carriers_removed` 只登记"因为拆这一行而红"的格子；同时报 `expected_green_stayed_green`
    与 `unexpected_red`——一臂红多格不是多份证据，归属要逐格写；
  * 不申报 KILLED：这里只写 `claimed_result`，`derived_result` 留 null（B-1，归验方）。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
SNAP = Path(os.environ.get("O296_SNAP", "D:/moodle/_qoder_f_run/snap_0296_g2/backend"))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0296_mutation_campaign_r1.json")
MODULE = "tests/test_qoder_ord0296_write_deadline.py"
ROUNDS = 3
WDIR = SNAP / "app/db/write_deadline.py"
WMAIN = SNAP / "app/main.py"
WSESS = SNAP / "app/db/session.py"

ARMS = [
    {"arm": "M1_reachability_is_not_strict", "file": WDIR,
     "before": "    return deadline > 0 and busy_timeout > 0 and deadline > busy_timeout",
     "after": "    return deadline > 0 and busy_timeout > 0 and deadline >= busy_timeout",
     "expects_red": ["test_G2_door_is_RED_when_the_deadline_sits_at_or_below_busy_timeout"],
     "why": "把「严格大于」松成「大于等于」 ⇒ 相等那一档必须被判成不可达，门要当场红"},
    {"arm": "M2_no_named_conversion", "file": WDIR,
     "before": """        raise WriteDeadlineExceeded(scenario, budget.elapsed_ms, budget.deadline_ms,
                                    str(exc)) from exc""",
     "after": "        raise",
     "expects_red": ["test_G6_lost_lock_after_the_budget_answers_under_its_own_name"],
     "expects_green": ["test_G7_lost_lock_inside_the_budget_stays_todays_error"],
     "why": "删掉超期那一支的改名 ⇒ 用户仍只能拿到没有内容的 500，G6 必红"},
    {"arm": "M3_always_renames_the_lock_failure", "file": WDIR,
     "before": """        budget.waits_lost += 1
        if not budget.expired():
            raise""",
     "after": """        budget.waits_lost += 1
        if False:
            raise""",
     "expects_red": ["test_G7_lost_lock_inside_the_budget_stays_todays_error"],
     "expects_green": ["test_G6_lost_lock_after_the_budget_answers_under_its_own_name"],
     "why": "不看预算一律改名 ⇒ 今天的错误被冒充成「期限」，G7 必红（这一臂是 G6 的反向对照）"},
    {"arm": "M4_startup_door_disabled", "file": WDIR,
     "before": """    report = configuration_verdict()
    if report["verdict"] != CONFIG_OK:
        raise WriteDeadlineConfigurationError(""",
     "after": """    report = configuration_verdict()
    if False:
        raise WriteDeadlineConfigurationError(""",
     "expects_red": ["test_G2_door_is_RED_when_the_deadline_sits_at_or_below_busy_timeout",
                     "test_G5_a_scenario_override_moves_one_route_and_names_every_other_case"],
     "expects_green": ["test_G3_door_is_GREEN_one_millisecond_above_it"],
     "why": "门只算不拦 ⇒ 不合规的配置能启动，G2 的红就没人接住"},
    {"arm": "M5_lock_wait_copied_a_second_time", "file": WSESS,
     "before": '                cursor.execute(f"PRAGMA busy_timeout={write_busy_timeout_ms()}")',
     "after": '                cursor.execute("PRAGMA busy_timeout=30000")',
     "expects_red": ["test_G4_the_lock_wait_is_written_in_exactly_one_place"],
     "why": "把 30000 再抄一份内联（0281 T-c 点名的形状）⇒ 单一来源那格必红"},
    {"arm": "M6_scenario_override_ignored", "file": WDIR,
     "before": """    overrides = scenario_overrides()
    if scenario in overrides:""",
     "after": """    overrides = scenario_overrides()
    if False:""",
     "expects_red": ["test_G5_a_scenario_override_moves_one_route_and_names_every_other_case"],
     "why": "「按场景可配」变成口号 ⇒ 覆盖那格必红"},
    {"arm": "M7_deadline_answer_status_is_500", "file": WMAIN,
     "before": "    return error(exc.code, str(exc), status=503, details=exc.details())",
     "after": "    return error(exc.code, str(exc), status=500, details=exc.details())",
     "expects_red": ["test_G8_the_answer_is_registered_and_carries_the_servers_own_words"],
     "why": "把服务端那句「我没写完」降级成 500 ⇒ 与框架裸 500 无法区分，G8 必红"},
    {"arm": "M8_effective_cap_ignores_the_budget", "file": WDIR,
     "before": "    return max(1, min(busy_timeout_ms(), deadline_ms(scenario)))",
     "after": "    return busy_timeout_ms()",
     "expects_red": ["test_G5_a_scenario_override_moves_one_route_and_names_every_other_case"],
     "why": "期限不再约束实际等待 ⇒ 那格里 min(...) 的断言必红"},
    {"arm": "M9_budget_shared_across_scenarios", "file": WDIR,
     "before": "    if budget is None or budget.scenario != scenario:",
     "after": "    if budget is None:",
     "expects_red": ["test_G10_the_budget_belongs_to_one_request_not_one_connection"],
     "why": "预算按连接共享 ⇒ 上一条请求替这一条超时，G10 必红"},
    {"arm": "M10_malformed_override_crashes_instead_of_naming", "file": WDIR,
     "before": """    try:
        deadline = deadline_ms(scenario)
    except ValueError:""",
     "after": """    try:
        deadline = deadline_ms(scenario)
    except ZeroDivisionError:""",
     "expects_red": ["test_G5_a_scenario_override_moves_one_route_and_names_every_other_case"],
     "why": "畸形覆盖从「具名配置判级」退回成 import 期崩溃 ⇒ 门那一档断言必红（0296 自查加的一臂）"},
]


def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def hunk_count(before: str, after: str) -> int:
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0))
    return sum(1 for line in diff if line.startswith("@@"))


def run_round() -> dict:
    started = time.time()
    proc = subprocess.run([PY, "-m", "pytest", MODULE, "-q", "--no-header", "-p", "no:cacheprovider",
                           "-rf", "--tb=no"], cwd=str(SNAP), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=1800)
    lines = [l for l in (proc.stdout or "").splitlines() if l.strip()]
    red = sorted({l.split("::")[1].split(" ")[0] for l in lines if l.startswith("FAILED ")})
    summary = next((l for l in reversed(lines) if "passed" in l or "failed" in l or "error" in l), "")
    return {"rc": proc.returncode, "seconds": round(time.time() - started, 2), "red": red,
            "summary_line": summary}


results = {"what": "ORD-0296 门体反突变战役（9 臂 × 3 轮，单变量、字节级还原）",
           "lane": "F 8ccd71d8", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
           "module": MODULE, "rounds": ROUNDS, "arms": [], "control_rounds": []}

print("[control] 未改动状态跑三轮")
for r in range(1, ROUNDS + 1):
    row = run_round()
    row["round"] = r
    results["control_rounds"].append(row)
    print(f"   round {r}: rc={row['rc']} red={row['red']} {row['summary_line']}")
control_green = all(not c["red"] for c in results["control_rounds"])
print("   控制轮全绿：", control_green)
if not control_green:
    print("ABORT：控制轮不绿，整批作废（不在坏底子上判击杀）")
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    sys.exit(2)

for arm in ARMS:
    path: Path = arm["file"]
    original = path.read_text(encoding="utf-8")
    if original.count(arm["before"]) != 1:
        results["arms"].append({**{k: arm[k] for k in ("arm", "why")},
                                "status": "ANCHOR_NOT_UNIQUE",
                                "anchor_hits": original.count(arm["before"])})
        print(f"[{arm['arm']}] ANCHOR_NOT_UNIQUE hits={original.count(arm['before'])} —— 不判")
        continue
    mutated = original.replace(arm["before"], arm["after"], 1)
    hunks = hunk_count(original, mutated)
    before_blob, after_blob = blob(path), hashlib.sha1(b"blob %d\0" % len(mutated.encode()) + mutated.encode()).hexdigest()
    path.write_text(mutated, encoding="utf-8", newline="\n")
    compile_ok = subprocess.run([PY, "-m", "py_compile", str(path)], capture_output=True,
                                text=True).returncode == 0
    per_round = []
    for r in range(1, ROUNDS + 1):
        row = run_round()
        row["round"] = r
        per_round.append(row)
    restored_ok = True
    path.write_text(original, encoding="utf-8", newline="\n")
    restored_ok = blob(path) == before_blob
    union = sorted(set.intersection(*[set(p["red"]) for p in per_round]) if per_round else set())
    carriers = [c for c in union if c in arm["expects_red"]]
    unexpected = [c for c in union if c not in arm.get("expects_red", [])]
    green_kept = [c for c in arm.get("expects_green", []) if c not in union]
    derived = None
    claimed = ("KILLED_CANDIDATE_ALL_ROUNDS_RED" if carriers and len(carriers) == len(arm["expects_red"])
               and all(p["red"] for p in per_round) and restored_ok and hunks == 1 and compile_ok
               else "INCONCLUSIVE_CANDIDATE")
    results["arms"].append({
        "arm": arm["arm"], "file": str(path.relative_to(SNAP)), "line_named": arm["before"].strip()[:88],
        "why": arm["why"], "hunks": hunks, "py_compile_ok": compile_ok,
        "before_blob_40": before_blob, "after_blob_40": after_blob,
        "per_round": per_round, "always_red_all_rounds": union,
        "expected_red": arm["expects_red"], "carriers_removed": carriers,
        "unexpected_red": unexpected, "expected_green_stayed_green": green_kept,
        "restored_byte_exact": restored_ok, "claimed_result": claimed, "derived_result": derived,
    })
    print(f"[{arm['arm']}] hunks={hunks} py_compile={compile_ok} carriers={len(carriers)}/"
          f"{len(arm['expects_red'])} unexpected={unexpected or '无'} 还原={restored_ok} ⇒ {claimed}")
    for p in per_round:
        print(f"      round {p['round']}: rc={p['rc']} red={len(p['red'])} {p['summary_line']}")

survivors = [a["arm"] for a in results["arms"]
             if a.get("carriers_removed") != a.get("expected_red") or not a.get("restored_byte_exact")]
results["summary"] = {"arms": len(results["arms"]),
                      "control_rounds_green": control_green,
                      "survivors": survivors,
                      "unexpected_red_total": sum(len(a.get("unexpected_red", [])) for a in results["arms"]),
                      "restore_byte_exact_every_round": all(a.get("restored_byte_exact") for a in results["arms"])}
OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\nsurvivors:", survivors or "无", "| 意外红合计", results["summary"]["unexpected_red_total"])
print("wrote", OUT.name)
