#!/usr/bin/env python3
"""ORD-0384 counter-examples, round 2: three arms, one of them a placement move.

r1 carried M1 and M2. X5 (the all-clear line may not render underneath a list of open items) needs its
own arm, and the way to break X5 is not a text substitution -- it is putting the panel back where it
first shipped, above the attention band. So this round adds a `move` operation that cuts the mount block
out of V8Experience.tsx by its own markers and re-inserts it before the band, which means the CJK comment
is never retyped by hand and cannot drift.

M1_rule_ignores_the_field       -- X1 must go red (an item the response does not support).
M2_empty_state_unreachable      -- X3 must go red (a clean response with no line and no action).
M3_all_clear_below_the_list     -- X5 must go red (bare "一切正常" printed under open items).

Every file is restored byte-for-byte and its sha256 re-checked before anything is claimed.
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
V8EXP = os.path.join(WT, "frontend", "src", "app", "V8Experience.tsx")
SPEC = "e2e/qoder-ord0384-pretrip-checklist.spec.ts"

MUTATIONS = [
    {"id": "M1_rule_ignores_the_field", "file": LIB, "cell": "X1",
     "find": "  if (stayBudget && stayBudget.declared === null) {\n",
     "put": "  if (stayBudget) {\n"},
    {"id": "M2_empty_state_unreachable", "file": PANEL, "cell": "X3",
     "find": "      {items.length === 0 ? (\n",
     "put": "      {items.length < 0 ? (\n"},
    {"id": "M3_all_clear_below_the_list", "file": V8EXP, "cell": "X5",
     "move": {"start_marker": "      {/* ORD-0384: what the server still reports",
              "end_marker": "      />\n",
              "before_marker": "      {/* Attention is its own band, not a tile squeezed"}}
]


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def mutate(text, m):
    """Return the mutated text, or raise with a reason. Never silently no-ops."""
    if "find" in m:
        if text.count(m["find"]) != 1:
            raise ValueError("ANCHOR_NOT_UNIQUE(%d)" % text.count(m["find"]))
        return text.replace(m["find"], m["put"])
    mv = m["move"]
    for k in ("start_marker", "before_marker"):
        if text.count(mv[k]) != 1:
            raise ValueError("%s_NOT_UNIQUE(%d)" % (k.upper(), text.count(mv[k])))
    i = text.index(mv["start_marker"])
    j = text.index(mv["end_marker"], i) + len(mv["end_marker"])
    block = text[i:j]
    rest = text[:i] + text[j:]
    k = rest.index(mv["before_marker"])
    return rest[:k] + block + rest[k:]


def main():
    report = {"spec": SPEC, "arms": []}
    for m in MUTATIONS:
        raw = io.open(m["file"], "rb").read()
        before = sha(m["file"])
        text = raw.decode("utf-8")
        try:
            mutated = mutate(text, m)
        except ValueError as exc:
            report["arms"].append({"id": m["id"], "status": str(exc)})
            print("%s -> %s" % (m["id"], exc))
            continue
        assert mutated != text, "the mutation was a no-op, so the arm proves nothing"
        io.open(m["file"], "wb").write(mutated.encode("utf-8"))
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(WT, "review", "n3_e2e_r1.py"),
                 "--wt", WT, "--target", SPEC, "--tag", "n3" + m["id"][1:3].lower(),
                 "--timeout-min", "18"],
                capture_output=True, text=True, errors="replace")
            lines = [l.strip() for l in r.stdout.splitlines()
                     if any(k in l for k in ('"run_id"', '"exit_code"', '"passed"', '"failed"'))]
        finally:
            io.open(m["file"], "wb").write(raw)
        after = sha(m["file"])
        arm = {"id": m["id"], "file": m["file"].replace("\\", "/"), "cell_under_test": m["cell"],
               "mutation_kind": "substitute" if "find" in m else "move",
               "runner_exit_code": r.returncode, "gate_went_red": r.returncode != 0,
               "runner_lines": lines, "stdout_tail": r.stdout.strip()[-1500:],
               "sha256_before": before, "sha256_after_restore": after,
               "restored_byte_identical": before == after,
               "verdict": "COUNTEREXAMPLE_HOLDS" if r.returncode != 0 and before == after else "INVALID"}
        report["arms"].append(arm)
        print("%s -> exit %s red=%s restored=%s" % (m["id"], r.returncode, r.returncode != 0, before == after))
        print("   tail:", (r.stdout.strip().splitlines() or [""])[-1][:200])
    ok = report["arms"] and all(a.get("verdict") == "COUNTEREXAMPLE_HOLDS" for a in report["arms"])
    report["all_arms_hold"] = ok
    out = os.path.join(WT, "review", "evidence", "ord0384", "mutations_r2.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print("READING " + out.replace("\\", "/"))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
