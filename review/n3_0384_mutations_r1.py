#!/usr/bin/env python3
"""ORD-0384 counter-examples: break the derivation and the empty state, require the gate to go red.

M1_rule_ignores_the_field -- the budget item is listed whenever the object exists, declared or not.
   X1 must catch it: the screen carries an item the response does not support.
M2_empty_state_unreachable -- the clean branch can never render, so a fully answered response shows an
   empty band with no line and no action. X3 must catch it.

Both files are restored byte-for-byte and the sha256 is re-checked before anything is claimed.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

WT = r"D:/moodle/_qoder_n3_ord0357"
LIB = os.path.join(WT, "frontend", "src", "lib", "pretripChecklist.ts")
PANEL = os.path.join(WT, "frontend", "src", "features", "checklist", "PretripChecklistPanel.tsx")
SPEC = "e2e/qoder-ord0384-pretrip-checklist.spec.ts"

MUTATIONS = [
    {"id": "M1_rule_ignores_the_field", "file": LIB,
     "find": "  if (stayBudget && stayBudget.declared === null) {\n",
     "put": "  if (stayBudget) {\n"},
    {"id": "M2_empty_state_unreachable", "file": PANEL,
     "find": "      {items.length === 0 ? (\n",
     "put": "      {items.length < 0 ? (\n"},
]


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    report = {"spec": SPEC, "arms": []}
    for m in MUTATIONS:
        raw = io.open(m["file"], "rb").read()
        before = sha(m["file"])
        if raw.count(m["find"].encode()) != 1:
            report["arms"].append({"id": m["id"], "status": "ANCHOR_NOT_UNIQUE",
                                   "occurrences": raw.count(m["find"].encode())})
            print("%s -> ANCHOR_NOT_UNIQUE (%d)" % (m["id"], raw.count(m["find"].encode())))
            continue
        io.open(m["file"], "wb").write(raw.replace(m["find"].encode(), m["put"].encode()))
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(WT, "review", "n3_e2e_r1.py"),
                 "--wt", WT, "--target", SPEC, "--tag", "n3" + m["id"][1:3].lower(), "--timeout-min", "16"],
                capture_output=True, text=True, errors="replace")
            lines = [l.strip() for l in r.stdout.splitlines()
                     if any(k in l for k in ('"run_id"', '"exit_code"', '"passed"', '"failed"'))]
        finally:
            io.open(m["file"], "wb").write(raw)
        after = sha(m["file"])
        arm = {"id": m["id"], "file": m["file"].replace("\\", "/"), "mutation": m["put"].strip(),
               "runner_exit_code": r.returncode, "gate_went_red": r.returncode != 0,
               "runner_lines": lines, "sha256_before": before, "sha256_after_restore": after,
               "restored_byte_identical": before == after,
               "verdict": "COUNTEREXAMPLE_HOLDS" if r.returncode != 0 and before == after else "INVALID"}
        report["arms"].append(arm)
        print("%s -> exit %s red=%s restored=%s" % (m["id"], r.returncode, r.returncode != 0, before == after))
    ok = report["arms"] and all(a.get("verdict") == "COUNTEREXAMPLE_HOLDS" for a in report["arms"])
    report["all_arms_hold"] = ok
    out = os.path.join(WT, "review", "evidence", "ord0384", "mutations_r1.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print("READING " + out.replace("\\", "/"))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
