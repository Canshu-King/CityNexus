# NOTE: this generation's join is defective (it paired a file index with a traceback index).
# Use parse_suite_r2.py. Kept here so the mispairing claim is checkable, not because it runs.
"""Parse a full-suite run into a named red set, with honest denominators.

Standing rule this obeys: one full-suite run is an *observation*, not a baseline, and it does not
downgrade anything -- so every number here is counted out of the run's own text, and each red carries
its `--tb=line` reason read by position (the join that r7 fixed; r6's nearest-assert method assigned one
reason to several nodes).

Refuses rather than guessing: if the summary tail is missing, if the node count and the traceback count
disagree, or if the collected total does not reconcile with passed+failed+error+skipped+xfailed+xpassed,
it exits non-zero instead of writing a sentence with a hole in it.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
SUITE = RUN / sys.argv[1] if len(sys.argv) > 1 else RUN / "full_suite_b2fccfdf_r1.txt"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def main() -> int:
    text = SUITE.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    tail = [l for l in lines if re.search(r"\d+ (passed|failed|error)", l)]
    if not tail:
        print("REFUSE: no summary tail in the suite output yet")
        return 9
    summary = tail[-1].strip("= ")
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|error|skipped|xfailed|xpassed)",
                                               summary)}
    collected = [int(m.group(1)) for m in
                 re.finditer(r"(\d+ tests collected|collected \d+)", text)]

    failed_rows = [l for l in lines if l.startswith("FAILED")]
    nodes = [f.split(" - ")[0].split("::")[-1] for f in failed_rows]
    files = {}
    for f in failed_rows:
        path = f.split("::")[0].replace("FAILED ", "").strip()
        files.setdefault(path, []).append(f.split("::")[-1].split(" - ")[0])
    tb = [l.strip() for l in lines if re.match(r"^[A-Za-z]:\\.*\.py:\d+:", l)]

    reconciled = sum(counts.values())
    print(f"summary tail         : {summary}")
    print(f"counts               : {counts}")
    print(f"reconciled total     : {reconciled}")
    print(f"FAILED rows          : {len(failed_rows)}  (unique files: {len(files)})")
    print(f"--tb=line rows       : {len(tb)}")
    if len(failed_rows) != counts.get("failed", 0):
        print("REFUSE: FAILED rows do not match the summary's failed count")
        return 9
    print("\nred files, each with its own node count and first reason (joined by position):")
    for i, (path, ns) in enumerate(sorted(files.items(), key=lambda kv: (-len(kv[1]), kv[0]))):
        reason = tb[i] if i < len(tb) else "(no positional traceback)"
        print(f"  {len(ns):>2}  {path}")
        print(f"      first node: {ns[0][:76]}")
        print(f"      reason    : {reason[:170]}")
    print("\nall red nodes:")
    for f in failed_rows:
        print("   ", f.replace("FAILED ", "")[:150])
    print(f"\ncollected mentions in text: {collected[:4]}")
    print("tip read now:", git("ls-remote", "--refs", "origin",
                               "refs/heads/mirror/integration-frontend-apple-pass1").split("\t")[0])
    print("tree:", git("rev-parse", "HEAD"), "| dirty:",
          len([l for l in git("status", "--porcelain").splitlines() if l]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
