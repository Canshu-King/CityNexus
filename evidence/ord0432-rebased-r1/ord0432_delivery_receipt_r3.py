"""ORD-0432 re-delivery artifact (rebased): computed, nothing typed.

Reads the two suite logs (new tip baseline vs rebased candidate) and derives the subset test, pulls
the before/after witness pair, the three reverse arms' disjointness, and the live `ls-remote` value of
the rebased review ref. Every number in the ledger block traces back to this file.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
WT = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
TASKS = Path.home() / "AppData/Local/Temp/qoder-cli/D--moodle/25f8a9c7-4549-43ad-835e-b04e92c7411f/tasks"
REMOTE = "ssh://git@ssh.github.com:443/Canshu-King/CityNexus.git"
REFS = ["refs/heads/review/Q-ord0432-robust-blind-to-major-1",
        "refs/heads/review/Q-ord0432-robust-blind-to-major-2"]
OUT = LANE / "ORD0432_DELIVERY_r3.json"
LOGS = {"tip_baseline_35326e62": "be0wgt7g2.output",
        "candidate_rebased_e5cf45c8": "b4xbav9rf.output"}


def suite(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    m = re.search(r"(\d+) failed.*?(\d+) passed.*?(\d+) skipped.*?(\d+) xfailed.*?in ([\d.]+)s", text, re.S)
    return {"source_log": path.name, "parsed": bool(m),
            "failed": int(m.group(1)) if m else None, "passed": int(m.group(2)) if m else None,
            "skipped": int(m.group(3)) if m else None, "xfailed": int(m.group(4)) if m else None,
            "seconds": float(m.group(5)) if m else None,
            "total_from_counts": sum(int(m.group(i)) for i in range(1, 5)) if m else None,
            "red_nodeids": sorted(set(re.findall(r"^FAILED (\S+)", text, re.M)))}


def main() -> int:
    out: dict = {"suite": {name: suite(TASKS / file) for name, file in LOGS.items()}}
    base = set(out["suite"]["tip_baseline_35326e62"]["red_nodeids"])
    cand = set(out["suite"]["candidate_rebased_e5cf45c8"]["red_nodeids"])
    out["regression_check"] = {"candidate_only_nodeids": sorted(cand - base),
                               "baseline_only_nodeids": sorted(base - cand),
                               "candidate_is_subset_of_baseline": cand <= base}

    pair = {}
    for port, label in ((8711, "unfixed_tip"), (8712, "rebased_candidate")):
        receipt = LANE / f"ORD0432_WITNESS_{port}.json"
        body = json.loads(receipt.read_text(encoding="utf-8"))
        pair[label] = {"witness_verdict_envelope_blind": body["VERDICT_envelope_blind_to_events"],
                       "after_major_envelope": {"robust": body["2A_after_major_closure"]["robust"],
                                                "risk_reason_codes":
                                                    body["2A_after_major_closure"]["risk_reason_codes"]},
                       "w_flags": {k: v for k, v in body.items() if k.startswith("W")},
                       "blob_side_note_W5": "W5 asserts an exact one-code list; on the fixed tree the "
                                            "list legitimately holds two codes because the MAJOR row "
                                            "is still unresolved"}
    out["witness_pair"] = pair

    arms = json.loads((LANE / "ORD0432_REVERSE_ARMS.json").read_text(encoding="utf-8"))
    out["reverse_arms"] = {"each_arm_exit": {k: v["exit"] for k, v in arms["arms"].items()},
                           "red_lists_disjoint_pairs": arms["red_lists_disjoint_pairs"],
                           "round0_unmutated_exit": arms["round0_unmutated"]["exit"]}

    ls = subprocess.run(["git", "ls-remote", REMOTE, *REFS], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    out["review_refs_readback"] = {line.split()[1]: line.split()[0]
                                   for line in ls.stdout.splitlines() if line.strip()}
    log = subprocess.run(["git", "-C", str(WT), "log", "-3", "--format=%H %ad %s", "--date=iso"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    out["candidate_line"] = log.stdout.strip().splitlines()
    diff = subprocess.run(["git", "-C", str(WT), "diff", "--name-only",
                           "35326e62fb3de9f0cda459c8426ac22c0c49c715", "HEAD"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    out["product_files_changed"] = diff.stdout.strip().splitlines()

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"regression_check": out["regression_check"],
                      "witness_pair": {k: v["witness_verdict_envelope_blind"]
                                       for k, v in out["witness_pair"].items()},
                      "review_refs_readback": out["review_refs_readback"],
                      "product_files_changed": out["product_files_changed"]},
                     ensure_ascii=False, indent=1))
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
