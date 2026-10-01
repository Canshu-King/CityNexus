"""Generation 5 -- what actually differs between the delivered backend tree and the CE-1 mutant.

The arm is only a counter-example if one file moved.  The first CE-1 run in the earlier generation
produced a fourth mutant red caused by a file the throwaway tree did not carry
(`frontend/src/generated/api.ts`, which the accepted contract arm reads), and a missing file is an
instrument artifact, not a finding -- so this proof exists and runs after every CE-1 pair.
"""
import hashlib
import json
import os
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
SKIP = {"node_modules", ".git", "dist", "__pycache__", "review", ".pytest_cache"}
ROOTS = ["backend", "data", "contracts", os.path.join("frontend", "src", "generated")]
CAND, MUT = "wt22", "mutgen9"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


out = {"tool": "gen9_ce1_tree_proof_r1", "took_local": datetime.now().astimezone().isoformat(),
       "candidate_tree": CAND, "mutant_tree": MUT, "dirs": {}}
for rel in ROOTS:
    a_root, b_root = os.path.join(LANE, CAND, rel), os.path.join(LANE, MUT, rel)
    files = {}
    for root, dirs, names in os.walk(a_root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for n in names:
            full = os.path.join(root, n)
            files[os.path.relpath(full, a_root).replace("\\", "/")] = full
    differing, missing = [], []
    for f, full in sorted(files.items()):
        mate = os.path.join(b_root, f)
        if not os.path.exists(mate):
            missing.append(f)
        elif sha(full) != sha(mate):
            differing.append(f)
    out["dirs"][rel.replace("\\", "/")] = {"files_compared": len(files), "differing": differing,
                                           "absent_from_mutant_count": len(missing)}
out["files_compared_total"] = sum(d["files_compared"] for d in out["dirs"].values())
out["only_main_py_differs"] = all(set(d["differing"]) <= {"app/main.py"} for d in out["dirs"].values())
out["candidate_main_sha256"] = sha(os.path.join(LANE, CAND, "backend", "app", "main.py"))
out["mutant_main_sha256"] = sha(os.path.join(LANE, MUT, "backend", "app", "main.py"))
path = os.path.join(LANE, "evidence", "gen9_ce1_tree_proof_r1.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
print("WROTE " + path)
