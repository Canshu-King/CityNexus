"""ORD-0504 D (ruling ①, option 甲) -- take the external analysis path out of MY OWN evidence files.

The commander's scope at 02:10: my four committed census artifacts only, 0 product bytes, every BAD row's
verdict and every count kept, and the ruler re-run to prove the denominator and both generations' totals
did not move. The three product files in my roster belong to other lanes and are not touched.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/redact_external_reference_r1.py

Running it also surfaced a defect of my own in that evidence: both artifacts were graded against a
**working tree** (`"tree": "working tree"`), so they were only reproducible as long as nobody moved the
tree. Here each generation is re-graded pinned to a commit -- the base the C paper was cut from, and the C
head itself -- then redacted, then compared row by row with what I had committed. The redaction is the
only intended difference, and a second pass must be a no-op.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
REVIEW = TREE / "review" / "ord0504"
OUT = REVIEW / "redact_external_reference_r1.txt"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

BASE_TIP = "b168b428f4ed0c9719a1aecf0bb38d98035cec9e"   # what the C paper was cut from
C_HEAD = "00ed2579aac110b61e2f75512518f37deb5a116f"     # the delivered C head
GENERATIONS = [("citation_scan_C_tip_r1", BASE_TIP), ("citation_scan_C_fix_r1", C_HEAD)]

PATTERNS = [
    (re.compile(r"(?:D:/|/)moodle/_apk_analysis_pi_travel/MAP/map_findings\.md"),
     "EXTERNAL_ANALYSIS_PATH_NOT_RECORDED"),
    (re.compile(r"(?<![/A-Za-z_.])map_findings\.md"),
     "EXTERNAL_ANALYSIS_FILE_NOT_RECORDED"),
]


def redact(text: str) -> tuple[str, int]:
    hits = 0
    for pattern, marker in PATTERNS:
        text, n = pattern.subn(marker, text)
        hits += n
    return text, hits


def run_scanner(rev: str, stem: str) -> tuple[str, str]:
    out_name = "%s_rerun.json" % stem
    report_name = "%s_rerun.txt" % stem
    env = dict(os.environ, CITATION_SCAN_OUT=out_name, CITATION_SCAN_REPORT=report_name)
    done = subprocess.run([PY, str(REVIEW / "shipped_citation_scan_r1.py"), rev], cwd=str(TREE),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if done.returncode not in (0, 1):
        raise SystemExit("REFUSE: the ruler did not run on %s (rc=%s): %s"
                         % (rev, done.returncode, (done.stdout + done.stderr)[-400:]))
    json_text = (LANE / "run" / out_name).read_text(encoding="utf-8")
    txt_text = (LANE / "run" / report_name).read_text(encoding="utf-8")
    os.remove(LANE / "run" / out_name)
    os.remove(LANE / "run" / report_name)
    return json_text, txt_text


def committed(name: str) -> str:
    done = subprocess.run(["git", "-C", str(TREE), "show", "%s:review/ord0504/%s" % (C_HEAD, name)],
                          capture_output=True)
    if done.returncode:
        raise SystemExit("REFUSE: cannot read the committed %s" % name)
    return done.stdout.decode("utf-8")


def shape(payload: str):
    """Everything a reader relies on, with the redactable strings pulled out."""
    data = json.loads(payload)
    return {
        "files_enumerated_for_scanning": data["files_enumerated_for_scanning"],
        "files_resolvable": data["files_resolvable"],
        "files_scanned_with_citations": data["files_scanned_with_citations"],
        "citations_checked": data["citations_checked"],
        "totals": data["totals"],
        "rows": [(r["citing"], r["verdict"]) for r in data["rows"]],
        "hard": [(r["citing"], r["verdict"]) for r in data["hard_rotten"]],
    }


def main() -> int:
    lines = ["ORD-0504 D | redaction of my own census artifacts, re-graded against commits", ""]
    for stem, rev in GENERATIONS:
        for suffix in (".json", ".txt"):
            name = stem + suffix
            old = committed(name)
            old_red, old_hits = redact(old)
            fresh_json, fresh_txt = run_scanner(rev, stem)
            new = fresh_json if suffix == ".json" else fresh_txt
            new_red, new_hits = redact(new)
            (REVIEW / name).write_text(new_red, encoding="utf-8", newline="\n")

            again, second_hits = redact(new_red)
            lines.append("== %s  (tree = %s)" % (name, rev[:12]))
            lines.append("   committed artifact carried %d occurrences; fresh re-grade carries %d; "
                         "second pass on the redacted text moves %d (idempotent=%s)"
                         % (old_hits, new_hits, second_hits, second_hits == 0 and again == new_red))
            if suffix == ".json":
                before, after = shape(old_red), shape(new_red)
                same_keys = all(before[k] == after[k] for k in before if k != "rows")
                lines.append("   counts and totals identical across the re-grade: %s" % same_keys)
                lines.append("   files scanned=%s resolvable=%s with citations=%s checked=%s hard=%d"
                             % (after["files_enumerated_for_scanning"], after["files_resolvable"],
                                after["files_scanned_with_citations"], after["citations_checked"],
                                len(after["hard"])))
                lines.append("   totals: %s" % json.dumps(after["totals"], ensure_ascii=False))
                lines.append("   per-row (citing, verdict) sequences identical: %s"
                             % (before["rows"] == after["rows"]))
                lines.append("   BAD roster identical: %s" % (before["hard"] == after["hard"]))
                lines.append("   tree field pinned: %s (was: %s)"
                             % (json.loads(new_red)["tree"][:12], json.loads(old)["tree"]))
            # the marker replaced the path, and no external path survives
            text = (REVIEW / name).read_text(encoding="utf-8")
            lines.append("   after writing: external path present=%s | marker present=%s"
                         % ("_apk_analysis_pi_travel" in text, "NOT_RECORDED" in text))
            lines.append("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
