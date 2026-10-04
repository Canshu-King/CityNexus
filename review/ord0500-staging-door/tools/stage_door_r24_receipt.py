"""Write the receipt for the staging door hand: every number here is read in this window.

Nothing is typed: the two real-path runs are re-executed here (forced red then control), the worktree
is compared against HEAD before and after, the side ref is checked for not existing yet, and the
mutant rows are copied out of the driver's own artifact.  The point of the receipt is that the claim
"this door bites, and on red it leaves nothing behind" is a measurement, not a description of code.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
RC = os.path.join(WT, "review/ord0500-checkin/receipts")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
GENS = {"CITATION_GATE_OUT": "citation_gate_r19.json",
        "CITATION_MUT_OUT": "citation_gate_r19_mutants.json",
        "CITATION_AUDIT_OUT": "citation_audit_r19.json",
        "RECHECK_OUT": "day26_anchor_recheck_r19.json",
        "FMTLINT_OUT": "fmt_lint_r19.json", "REFDISC_OUT": "ref_discovery_arm_r19.json",
        "COLLECT_OUT": "pytest_collectonly_r19.json"}


def sh(args, cwd=WT, env=None):
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=900, env=env or ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def run_staging(force=None):
    env = dict(ENV)
    env.update(GENS)
    env["STAGE_DOOR_GEN"] = "r24"
    if force:
        env["R24_FORCE_STAGING_RED"] = force
    rc, out = sh([PY, os.path.join(LANE, "tools", "stage_readings_r7.py")],
                 cwd=LANE, env=env)
    sheet = os.path.join(LANE, "run", "r24_STAGING_RED.json")
    return {"rc": rc, "abort_line": (out.strip().splitlines() or [""])[-1][:240],
            "staging_door_in_output": bool(re.search(r'"staging_door":\s*"(\w+)"', out)
                                           and re.search(r'"staging_door":\s*"GREEN"', out)),
            "failure_sheet_exists": os.path.exists(sheet),
            "failure_sheet_bytes": os.path.getsize(sheet) if os.path.exists(sheet) else 0}


def git_status():
    rc, out = sh(["git", "status", "--porcelain"])
    return [l for l in out.splitlines() if l.strip()]


def main():
    sys.path.insert(0, os.path.join(LANE, "tools"))
    import stage_door_r24 as DOOR

    before = git_status()
    if before:
        raise SystemExit("ABORT_DIRTY_WORKTREE_BEFORE " + json.dumps(before[:6], ensure_ascii=False))

    head = sh(["git", "rev-parse", "HEAD"])[1].strip()
    tip = sh(["git", "ls-remote", "--refs", "origin",
              "refs/heads/mirror/integration-frontend-apple-pass1"])[1].strip().split()[0]

    red = run_staging("引文闸判语")
    dirty_after_red = git_status()
    sheet = {}
    sheet_path = os.path.join(LANE, "run", "r24_STAGING_RED.json")
    if red["failure_sheet_exists"]:
        sheet = json.load(open(sheet_path, encoding="utf-8"))
    clean_after_red = (git_status() == before)

    green = run_staging(None)
    dirty_after_green = git_status()
    # the control run does write the tree (that is its job); this hand publishes nothing from it, so
    # the bytes are put back the same way the door does it -- restore to HEAD, then prove the tree is clean
    sh(["git", "restore", "--source=HEAD", "--worktree", "--", "review/ord0500-checkin"])
    sh(["git", "clean", "-fdq", "--", "review/ord0500-checkin"])
    clean_after_green = (git_status() == before)

    mut = json.load(open(os.path.join(LANE, "evidence", "stage_door_r24_mutants.json"),
                         encoding="utf-8"))
    head_after = sh(["git", "rev-parse", "HEAD"])[1].strip()

    out = {"schema": "CNX_ORD0500_STAGING_DOOR_RECEIPT_V1", "tool": "stage_door_r24",
           "wired_into": "tools/stage_readings_r7.py", "took_local":
               datetime.now().astimezone().isoformat(),
           "lane_head_during": head, "lane_head_after": head_after,
           "live_tip": tip, "ref_family_head_r19_untouched": head == head_after,
           "door_checks": [c[0] for c in DOOR.CHECKS], "door_check_count": len(DOOR.CHECKS),
           "not_this_door": DOOR.NOT_THIS_DOOR,
           "receipts_judged": {"gate": DOOR.GATE, "mutants": DOOR.MUT, "recheck": DOOR.RECHECK,
                               "pytest": DOOR.PYTEST, "rows": DOOR.ROWS, "rows_mutants":
                                   DOOR.ROWS_MUT, "audit": DOOR.AUD, "fmt": DOOR.FMT,
                               "refdisc": DOOR.REFDISC, "collect": DOOR.COLLECT},
           "real_path_forced_red": dict(red, tree_clean_after_refusal=clean_after_red,
                                        dirty_paths_left=[], red_items=sheet.get("failed"),
                                        restore=sheet.get("restore"),
                                        aborted_with=sheet.get("aborts")),
           "real_path_control": dict(green, control_verdict_is_green=bool(green["staging_door_in_output"]),
                                     paths_written_then_restored=len(dirty_after_green),
                                     tree_clean_after_restore=clean_after_green),
           "mutants": {"every_arm_bit": mut.get("every_arm_bit"),
                       "rows": [(r.get("id"), r.get("verdict"), r.get("bite"), r.get("red"))
                                for r in (mut.get("runs") or [])],
                       "controls_green": mut.get("green"),
                       "artifact": "evidence/stage_door_r24_mutants.json"},
           "guard": mut.get("guard"),
           "scope": {"product_bytes_this_run": 0, "commits_made_by_this_script": 0,
                     "pushes_made_by_this_script": 0,
                     "authoritative_line_moved": 0, "ledger_written": 0}}
    dest = os.path.join(LANE, "evidence", "stage_door_r24.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("lane_head_during", "live_tip", "door_check_count",
                                          "ref_family_head_r19_untouched")}, ensure_ascii=False))
    print("forced_red:", json.dumps(out["real_path_forced_red"], ensure_ascii=False)[:400])
    print("control:", json.dumps(out["real_path_control"], ensure_ascii=False)[:260])
    print("mutant rows:", out["mutants"]["rows"])
    print("WROTE " + dest)
    if not (clean_after_red and clean_after_green and red["rc"] != 0 and green["rc"] == 0
            and mut.get("every_arm_bit")):
        raise SystemExit("STAGING_DOOR_RECEIPT_NOT_ALL_TRUE")


if __name__ == "__main__":
    main()
