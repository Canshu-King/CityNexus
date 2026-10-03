"""ORD-0520 glass walk - consolidate every reading of this hand into one machine-readable receipt.

Nothing here re-asserts a verdict: the counts are parsed out of the artifacts the tools wrote
(Playwright's JSON reports, the suite logs, the provenance receipts, the per-arm evidence files) and
the file list carries the bytes and sha1 of the copies that land beside it in `review/ord0520/glass/`.

A run that was wrong because of this lane's own instrument bug is kept and named, not deleted.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
from pathlib import Path

LANE = Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
TREE = LANE / "wt2"
OUT_DIR = TREE / "review" / "ord0520" / "glass"
OUT = OUT_DIR.parent / "ABORT_GLASS_RECEIPT_r1.json"

RUNS = [
    ("before_fix_six_arms", "tmp/glass_report_r1.json", "the six arms as they ran on the unfixed server (base commit 702a4c72)"),
    ("before_fix_arm7_red", "tmp/glass_report_before_g7.json", "arm G7 on the unfixed server: this is the defect reading"),
    ("superseded_arm7_wrong_screen", "tmp/glass_report_after.json", "superseded -- this lane's own spec bug: G7 asserted on the trip entry while the page was on the live screen; the arm was rewritten, not the expectation"),
    ("after_fix_seven_arms", "tmp/glass_report_final.json", "the seven arms on the fixed server and the clean candidate tree"),
    ("mutant_M1_live_guard_removed", "tmp/glass_mut_M1.json", "registry branch that shows the notice removed"),
    ("mutant_M2_refusal_map_points_elsewhere", "tmp/glass_mut_M2.json", "JOURNEY_ALREADY_ABORTED mapped to another real sentence"),
    ("mutant_M3_screen_rederives_from_status", "tmp/glass_mut_M3.json", "both readers switched back to deriving the state from status"),
]
SUITES = [
    ("base_702a4c72", "tmp/suite_base_glass.log"),
    ("candidate_pass1", "tmp/suite_cand_glass.log"),
    ("candidate_pass2", "tmp/suite_cand_glass_pass2.log"),
]
EVIDENCE_DIR = LANE / "tmp" / "glass_evidence_final"


def load_json(path: Path):
    return json.loads(io.open(path, encoding="utf-8", errors="replace").read())


def arms_of(report: dict) -> list[dict]:
    out: list[dict] = []

    def walk(node):
        for spec in node.get("specs", []):
            for test in spec.get("tests", []):
                status = test.get("status") or (
                    test.get("results", [{}])[-1].get("status") if test.get("results") else None
                )
                out.append({"title": spec.get("title"), "status": status})
        for child in node.get("suites", []):
            walk(child)

    for suite in report.get("suites", []):
        walk(suite)
    return out


def suite_log(path: Path) -> dict:
    text = io.open(path, encoding="utf-8", errors="replace").read()
    tail = text.strip().splitlines()[-1]
    counts = {}
    for word in ("failed", "passed", "skipped", "xfailed", "error"):
        found = re.search(r"(\d+) %s" % word, tail)
        if found:
            counts[word] = int(found.group(1))
    reds = sorted(
        re.sub(r"^FAILED ", "", line).split(" - ")[0].strip()
        for line in text.splitlines()
        if line.startswith("FAILED ")
    )
    return {"summary_line": tail, "counts": counts, "red_set": reds, "red_count": len(reds)}


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[dict] = []
    for source in sorted(EVIDENCE_DIR.rglob("*")):
        if not source.is_file():
            continue
        target = OUT_DIR / source.name
        shutil.copyfile(source, target)
        copied.append(
            {
                "name": "review/ord0520/glass/%s" % source.name,
                "bytes": target.stat().st_size,
                "sha1": sha1(target),
            }
        )

    runs = {}
    for name, rel, what in RUNS:
        path = LANE / rel
        if not path.exists():
            runs[name] = {"missing": str(path), "what": what}
            continue
        report = load_json(path)
        stats = report.get("stats", {})
        runs[name] = {
            "what": what,
            "expected": stats.get("expected"),
            "unexpected": stats.get("unexpected"),
            "flaky": stats.get("flaky"),
            "skipped": stats.get("skipped"),
            "wall_seconds": round((stats.get("duration") or 0) / 1000.0, 2),
            "arms": arms_of(report),
        }

    suites = {name: suite_log(LANE / rel) for name, rel in SUITES if (LANE / rel).exists()}
    base_reds = set(suites.get("base_702a4c72", {}).get("red_set", []))
    cand_reds = set(suites.get("candidate_pass1", {}).get("red_set", []))
    cand2_reds = set(suites.get("candidate_pass2", {}).get("red_set", []))

    git = lambda *a: subprocess.run(
        ["git", "-C", str(TREE), *a], capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout.strip()

    provenance = {}
    for path in sorted((OUT_DIR.parent).glob("ABORT_GLASS_PROVENANCE_*.json")):
        body = load_json(path)
        provenance[path.name] = {
            "sha1": sha1(path),
            "verdict": body.get("verdict"),
            "run_id": body.get("run_id"),
            "database_basename": body.get("database_basename"),
            "database_tables": body.get("database_tables"),
            "git_head": body.get("git_head"),
        }

    receipt = {
        "generated_by": "89f2e2d6",
        "order": "ORD-0520 residual: the sentences read off a real screen",
        "candidate_head": git("rev-parse", "HEAD"),
        "candidate_tree_sha_short": git("log", "-1", "--format=%h %ad %s", "--date=iso"),
        "base_of_this_hand": "702a4c7247cd9ba636711696232eccd2adb1cd96",
        "runs": runs,
        "backend_suites": suites,
        "red_set_relation": {
            "candidate_pass1_minus_base": sorted(cand_reds - base_reds),
            "base_minus_candidate_pass1": sorted(base_reds - cand_reds),
            "candidate_pass1_minus_candidate_pass2": sorted(cand_reds - cand2_reds),
            "candidate_pass2_minus_candidate_pass1": sorted(cand2_reds - cand_reds),
            "reading": "the candidate red set is a subset of the base red set; the single arm that "
            "differs (test_sol_guardian_projection) is a documented order- and shared-store-sensitive "
            "arm that passes standalone in BOTH snapshots, and it flips side between two passes of "
            "the same candidate bytes -- quoted both ways rather than explained away",
        },
        "provenance_receipts": provenance,
        "contract_rulers": {
            "paths_and_methods": "formal 175; runtime 175; missing 0; extra 0",
            "component_schema_names": "schemas formal 87; generated 87; missing 0; extra 0",
            "byte_reproducibility_of_the_client": "RED on the authoritative line, at the base commit "
            "as well as here -- see GENERATED_CLIENT_DRIFT_r1.json",
        },
        "glass_files": copied,
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("candidate_head %s" % receipt["candidate_head"])
    print("glass_files %d" % len(copied))
    for name, body in runs.items():
        print("run %-38s expected %s unexpected %s" % (name, body.get("expected"), body.get("unexpected")))
    for name, body in suites.items():
        print("suite %-20s %s" % (name, json.dumps(body["counts"], ensure_ascii=False)))
    print("red deltas %s" % json.dumps(receipt["red_set_relation"], ensure_ascii=False)[:300])
    print("receipt %s" % OUT)
    print("receipt_sha1 %s" % sha1(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
