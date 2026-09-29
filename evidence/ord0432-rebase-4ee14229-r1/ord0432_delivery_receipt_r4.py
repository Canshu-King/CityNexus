"""ORD-0432 third re-delivery: the same computed audit, rebuilt for the 4ee14229 base.

Numbers come from the pytest logs and the two witness receipts; the fast-forward claim is answered by
`git merge-base --is-ancestor` against the live tip, and the ref coordinate by `git ls-remote`.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
WT = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
TASKS = Path.home() / "AppData/Local/Temp/qoder-cli/D--moodle/b93628aa-165b-47e2-8d59-0be8db2280f8/tasks"
REMOTE = "ssh://git@ssh.github.com:443/Canshu-King/CityNexus.git"
TIP = "4ee14229f80691cf8e5ea913375c0caf83ac02ee"
REF = "refs/heads/review/Q-ord0432-robust-blind-to-major-3"
OUT = LANE / "ORD0432_DELIVERY_r4.json"  # 4 logs, computed
LOGS = {"tip_baseline_4ee14229": "bambmj7c2.output",
        "candidate_before_teardown": "b9l1ga220.output",
        "candidate_my_file_ignored": "b440brt09.output",
        "candidate_with_teardown": "bd5numls9.output"}


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(WT), *a], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def suite(name: str) -> dict:
    path = TASKS / name
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    m = re.search(r"(\d+) failed.*?(\d+) passed.*?(\d+) skipped.*?(\d+) xfailed.*?in ([\d.]+)s", text, re.S)
    return {"source_log": name, "parsed": bool(m),
            "failed": int(m.group(1)) if m else None, "passed": int(m.group(2)) if m else None,
            "skipped": int(m.group(3)) if m else None, "xfailed": int(m.group(4)) if m else None,
            "seconds": float(m.group(5)) if m else None,
            "total_from_counts": sum(int(m.group(i)) for i in range(1, 5)) if m else None,
            "red_nodeids": sorted(set(re.findall(r"^FAILED (\S+)", text, re.M)))}


def main() -> int:
    out: dict = {"suite": {k: suite(v) for k, v in LOGS.items()}}
    base = set(out["suite"]["tip_baseline_4ee14229"]["red_nodeids"])
    cand = set(out["suite"]["candidate_with_teardown"]["red_nodeids"])
    out["regression_check"] = {"candidate_only_nodeids": sorted(cand - base),
                              "baseline_only_nodeids": sorted(base - cand),
                              "candidate_is_subset_of_baseline": cand <= base,
                              "my_new_file_in_either_red_set": sorted(
                                  n for n in cand | base if "test_dsh_twin_disruption" in n)}

    pair = {}
    for port, label in ((8721, "unfixed_tip_4ee14229"), (8722, "rebased_candidate_be98c7d9")):
        body = json.loads((LANE / f"ORD0432_WITNESS_{port}.json").read_text(encoding="utf-8"))
        pair[label] = {"verdict_envelope_blind": body["VERDICT_envelope_blind_to_events"],
                       "after_major": {k: body["2A_after_major_closure"][k]
                                       for k in ("robust", "risk_reason_codes")},
                       "control_event_after": {k: body["2B_after_control_event"][k]
                                               for k in ("robust", "risk_reason_codes")},
                       "flags": {k: v for k, v in body.items() if k.startswith("W")}}
    out["witness_pair"] = pair

    arms = json.loads((LANE / "ORD0432_REVERSE_ARMS.json").read_text(encoding="utf-8"))
    out["reverse_arms"] = {"round0_unmutated_exit": arms["round0_unmutated"]["exit"],
                           "arm_exits": {k: v["exit"] for k, v in arms["arms"].items()},
                           "red_lists_disjoint_pairs": arms["red_lists_disjoint_pairs"],
                           "mutated_files": sorted({v.get("file") for v in arms["arms"].values()}
                                                   if all("file" in v for v in arms["arms"].values())
                                                   else "see receipt key arms")}

    ff = subprocess.run(["git", "-C", str(WT), "merge-base", "--is-ancestor", TIP, "HEAD"],
                        capture_output=True)
    ls = subprocess.run(["git", "ls-remote", REMOTE, REF], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    out["landing_shape"] = {"tip": TIP, "tip_is_ancestor_of_candidate_rc": ff.returncode,
                            "ref": REF, "ref_readback": (ls.stdout or "").split()[:1]}
    out["candidate_commits"] = git("log", "-2", "--format=%H %ad %s", "--date=iso").splitlines()
    out["product_files_changed"] = git("diff", "--name-only", TIP, "HEAD").splitlines()
    diff = git("diff", "--numstat", TIP, "HEAD")
    out["diff_numstat"] = diff.splitlines()
    st = subprocess.run(["git", "-C", str(WT), "status", "--porcelain"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    out["worktree_dirty_entries"] = len([x for x in st.stdout.splitlines() if x.strip()])

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"regression_check": out["regression_check"],
                      "witness": {k: v["verdict_envelope_blind"] for k, v in pair.items()},
                      "after_major": {k: v["after_major"] for k, v in pair.items()},
                      "landing_shape": out["landing_shape"],
                      "totals": {k: {kk: v[kk] for kk in ("failed", "passed", "total_from_counts", "parsed")}
                                 for k, v in out["suite"].items()},
                      "product_files": len(out["product_files_changed"]),
                      "dirty": out["worktree_dirty_entries"]}, ensure_ascii=False, indent=1)[:1800])
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
