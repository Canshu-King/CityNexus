"""ORD-0417 lane: replay the commander's re-cut, read-only, and record what it reports.

`merge-tree --write-tree` predicts a merge without touching a worktree, an index or a ref, which is the
only honest way for a lane to check a claim about the authoritative line.  It is run for two pairs: the
branch the commander named (r2) and the branch this lane just delivered (r8), both against the same tip,
so the two readings are comparable and neither is quoted from memory.

Exit codes are part of the reading: 0 = clean, 1 = conflicts (git's documented meaning here), anything
else is a tool failure and is reported as such rather than passed off as a result.

usage: python ord0417_recut_check_r1.py <tip-40-hex> <out-file> <label=commit> [<label=commit> ...]
"""
import json
import subprocess
import sys

TIP = sys.argv[1]
OUT = sys.argv[2]
pairs = sys.argv[3:]

rec = {"tool": "git merge-tree --write-tree (read-only: no worktree, no index, no ref is written)",
       "tip": TIP, "runs": []}
for spec in pairs:
    label, _, commit = spec.partition("=")
    p = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "merge-tree", "--write-tree", TIP, commit],
                       capture_output=True, text=True)
    out = (p.stdout or "").splitlines()
    conflicts = [l for l in out if l.startswith("CONFLICT")]
    rec["runs"].append({
        "label": label, "commit": commit, "exit_code": p.returncode,
        "predicted_tree": out[0] if out else None,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "product_conflicts": [c for c in conflicts if not c.split()[-1].startswith("review/")],
    })

json.dump(rec, open(OUT, "w", encoding="utf-8", newline=chr(10)), indent=1, ensure_ascii=False)
print(json.dumps({r["label"]: {"rc": r["exit_code"], "conflicts": r["conflict_count"],
                               "product": len(r["product_conflicts"])} for r in rec["runs"]}))
