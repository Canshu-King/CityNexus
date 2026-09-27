#!/usr/bin/env python3
"""ORD-0384 -- counter-examples, round 5: the same four arms, plus a filter so one arm can be re-run alone.

r4 was the round that caught my own new assertion being vacuous: N4 deleted the `overflow-wrap` on the item
prose and the gate stayed GREEN, which means the Y4 overflow check I had just written did not measure the
thing I saw in the screenshot. Y4 now measures the rendered text range against the element box and the
card, and this round exists so the strengthened arm can be re-run on its own before the full set.

r3 carried N1-N3. This round adds N4, because Y4 grew a new assertion in the meantime (prose clipped by
its own box) and an assertion with no counter-example is a claim about coverage, not coverage.

The first version of this file reported only "the gate went red". That is too weak for a delivery whose
whole claim is a narrowing: an arm that reddens everything proves nothing about which cell is doing the
work. So each arm here is followed by reading the run's own log and listing the named failing cells,
which is how specificity is shown rather than asserted.

N1_rule_always_fires   -- `failures.length > 0` becomes `failures.length >= 0`, so the feasibility item is
                          listed even when the response says nothing. Must redden Y1 (an item the response
                          does not support) and Y3 (a clean response that still lists something).
N2_empty_state_action  -- the clean branch can never render. Must redden Y3 only.
N3_unanchored_leaks_back -- one of the seven dropped classes is put back into the derivation. Must redden
                          Y5, which is the cell that exists only because of the re-scoping.
N4_prose_can_overflow_its_box -- the `overflow-wrap` on the item prose is deleted, so a long server token
                          is cut at the card edge again. Must redden Y4, the cell that measures it.
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_n3_ord0357"
LIB = os.path.join(WT, "frontend", "src", "lib", "pretripChecklist.ts")
PANEL = os.path.join(WT, "frontend", "src", "features", "checklist", "PretripChecklistPanel.tsx")
CSS = os.path.join(WT, "frontend", "src", "features", "checklist", "pretripChecklist.css")
SPEC = "e2e/qoder-ord0384-pretrip-checklist.spec.ts"
LOGS = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/e2e_logs"

LEAK = ('  if (exp.selected_option_id === null || exp.selected_option_id === undefined) {\n'
        '    items.push({\n'
        '      key: "stay_not_chosen",\n'
        '      title: { zh: "还没有选定住宿", en: "No stay has been chosen" },\n'
        '      why: { zh: "反件：把一条没有契约锚的类放回屏上。", en: "mutation: an un-anchored class put back on screen." },\n'
        '      basis: { endpoint: EXPERIENCE, field: "selected_option_id", anchor: { file: CONTRACT, line: 1 } },\n'
        '      target: { route: "stay", label: { zh: "去选住宿", en: "Choose a stay" } },\n'
        '    });\n'
        '  }\n\n')

ONLY = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None

MUTATIONS = [
    {"id": "N1_rule_always_fires", "file": LIB, "cell": "Y1+Y3",
     "find": "  if (failures.length > 0) {\n", "put": "  if (failures.length >= 0) {\n"},
    {"id": "N2_empty_state_action", "file": PANEL, "cell": "Y3",
     "find": "      {items.length === 0 ? (\n", "put": "      {items.length < 0 ? (\n"},
    {"id": "N3_unanchored_leaks_back", "file": LIB, "cell": "Y5",
     "find": "  return items;\n", "put": LEAK + "  return items;\n"},
    {"id": "N4_prose_can_overflow_its_box", "file": CSS, "cell": "Y4",
     "find": ".cn-pretrip-title,\n.cn-pretrip-why { overflow-wrap: anywhere; }\n", "put": ""},
]


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def failing_cells(log_path):
    """Named cells from the runner's own log, read out of the `N) ... › <CellTitle>` failure list."""
    if not os.path.isfile(log_path):
        return None
    txt = io.open(log_path, encoding="utf-8", errors="replace").read()
    cells = re.findall(r"^\s+\d+\) \[chromium\].*?› ([XY]\d)_", txt, re.M)
    return sorted(set(cells))


def main():
    chosen = [m for m in MUTATIONS if ONLY is None or m["id"] in ONLY]
    if ONLY:
        unknown = ONLY - {m["id"] for m in MUTATIONS}
        assert not unknown, "unknown arm id(s): %s" % ",".join(sorted(unknown))
    report = {"spec": SPEC, "arms": [], "arms_requested": len(chosen), "filter": sorted(ONLY) if ONLY else "all"}
    for m in chosen:
        raw = io.open(m["file"], "rb").read()
        before = sha(m["file"])
        text = raw.decode("utf-8")
        if text.count(m["find"]) != 1:
            report["arms"].append({"id": m["id"], "status": "ANCHOR_NOT_UNIQUE",
                                   "occurrences": text.count(m["find"])})
            print("%s -> ANCHOR_NOT_UNIQUE (%d)" % (m["id"], text.count(m["find"])))
            continue
        io.open(m["file"], "wb").write(text.replace(m["find"], m["put"], 1).encode("utf-8"))
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(WT, "review", "n3_e2e_r1.py"),
                 "--wt", WT, "--target", SPEC, "--tag", "n3" + m["id"][1:3].lower(), "--timeout-min", "20"],
                capture_output=True, text=True, errors="replace")
            out = r.stdout
            run_id = (re.search(r'"run_id": "([^"]+)"', out) or [None, None])[1]
            log = (re.search(r'"log": "([^"]+)"', out) or [None, None])[1]
            counts = dict(re.findall(r'"(passed|failed)": (\d+)', out))
        finally:
            io.open(m["file"], "wb").write(raw)
        after = sha(m["file"])
        killed = failing_cells(log) if log else None
        arm = {"id": m["id"], "file": m["file"].replace("\\", "/"), "cell_targeted": m["cell"],
               "mutation": (m["put"].strip().splitlines() or ["<deletion: the anchor is removed>"])[0],
               "run_id": run_id, "runner_exit_code": r.returncode, "gate_went_red": r.returncode != 0,
               "counts": {k: int(v) for k, v in counts.items()},
               "log": log.replace("\\", "/") if log else None,
               "cells_reddened_by_name": killed,
               "targeted_cell_actually_reddened": bool(killed) and m["cell"].split("+")[0] in killed,
               "sha256_before": before, "sha256_after_restore": after,
               "restored_byte_identical": before == after,
               "verdict": ("COUNTEREXAMPLE_HOLDS" if r.returncode != 0 and before == after
                           and killed and m["cell"].split("+")[0] in killed else "INVALID")}
        report["arms"].append(arm)
        print("%s -> exit %s red=%s killed=%s restored=%s" % (
            m["id"], r.returncode, r.returncode != 0, killed, before == after))
    if len(report["arms"]) != len(chosen):
        print("ARM_COUNT_MISMATCH ran %d of %d" % (len(report["arms"]), len(chosen)))
    ok = (len(report["arms"]) == len(chosen)
          and all(a.get("verdict") == "COUNTEREXAMPLE_HOLDS" for a in report["arms"]))
    report["all_arms_hold"] = ok
    out = os.path.join(WT, "review", "evidence", "ord0384", "mutations_r5.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print("READING " + out.replace("\\", "/"))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
