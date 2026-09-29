#!/usr/bin/env python3
"""ORD-0440 second half - do the four fixes actually account for the drop? (ruler arms)

The claim being defended is a number: the door's own ruler reads `cells_total` 12 on the tip and 8 on
this tree. A number that only appears in the fixed tree proves nothing about which change moved it, so
each arm below puts ONE removed condition back, re-runs the same ruler over the same tree, and records
what it reads. Every arm restores its file byte-for-byte and the run fails loudly if an anchor was not
found (an arm that never applied proves nothing).

    python review/ord0440/exposure_arms_r1.py <worktree> <out-json>
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / "review/n3_0440_evidence_r1/exposure_arms_r1.json"
RULER = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ui_exposure_taint_ast_r7b.cjs")
PANEL = ROOT / "frontend/src/features/discovery/DestinationPreparationPanel.tsx"
FACTS = ROOT / "frontend/src/components/CnxMeasuredFacts.tsx"

ARMS = [
    {
        "name": "A1 the capability read prints the exception's own sentence again",
        "file": PANEL,
        "find": '      setCapabilityError(failureSentence("check", nameTheFailure(error), zh));',
        "replace": '      setCapabilityError(error instanceof Error ? error.message : "The capability read failed.");',
        "expect": "cells_total goes back up by exactly 1",
    },
    {
        "name": "A2 the job's error prose is mounted again instead of the named code's sentence",
        "file": PANEL,
        "find": '  const serverSentence = serverError\n    ? failureSentence("read", nameTheFailure(serverError), zh)\n    : "";',
        "replace": '  const serverSentence = serverError && typeof serverError === "object"\n    ? String((serverError as { message?: unknown }).message ?? "")\n    : "";',
        "expect": "cells_total goes back up by exactly 1",
    },
    {
        "name": "A3 the stop failure prints the exception's own sentence again",
        "file": PANEL,
        "find": '      setActionError(failureSentence("stop", nameTheFailure(error), zh));',
        "replace": '      setActionError(error instanceof Error ? error.message : "Could not stop this preparation.");',
        "expect": "cells_total goes back up by exactly 1",
    },
    {
        "name": "A4 the fold's anchor goes back to a spread (what the first version did)",
        "file": FACTS,
        "find": '          data-cnx-field="http_status"',
        "replace": '          {...{ "data-cnx-field": "http_status" }}',
        "expect": "the receipt cell returns: the exception needs the field name readable off the source",
    },
]


def sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def measure(out: Path) -> dict:
    proc = subprocess.run(
        ["node", str(RULER), "--tree", str(ROOT / "frontend/src"), "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    if not out.exists():
        return {"exit": proc.returncode, "error": (proc.stderr or "")[-200:]}
    data = json.loads(io.open(out, encoding="utf-8").read())
    return {
        "exit": proc.returncode,
        "cells_total": data.get("cells_total"),
        "by_slot": data.get("cells_by_slot"),
        "files": sorted({h.get("file") for h in data.get("hits", [])}),
        "exonerated": [(h.get("file"), h.get("file_line")) for h in data.get("attributed_in_fold", [])],
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    baseline = measure(OUT.parent / "exposure_arm_baseline.json")
    results = []
    for arm in ARMS:
        path: Path = arm["file"]
        raw = path.read_bytes()
        before = sha(path)
        text = raw.decode("utf-8")
        if arm["find"] not in text:
            results.append({"name": arm["name"], "applied": False,
                            "note": "ANCHOR_NOT_FOUND - this arm never ran and proves nothing"})
            continue
        path.write_bytes(text.replace(arm["find"], arm["replace"], 1).encode("utf-8"))
        reading = measure(OUT.parent / f"exposure_arm_{abs(hash(arm['name'])) % 10000:04d}.json")
        path.write_bytes(raw)
        results.append({
            "name": arm["name"], "expect": arm["expect"], "applied": True,
            "reading": reading,
            "delta_vs_baseline": None if baseline.get("cells_total") is None or reading.get("cells_total") is None
            else reading["cells_total"] - baseline["cells_total"],
            "restored_byte_identical": sha(path) == before,
        })
    final = measure(OUT.parent / "exposure_arm_after_restoring.json")
    payload = {
        "ruler": str(RULER),
        "ruler_blob_command": "git -C D:/moodle/CityNexus cat-file blob d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2",
        "tree": str(ROOT).replace("\\", "/"),
        "baseline_this_tree": baseline,
        "arms": results,
        "after_restoring_everything": final,
        "all_arms_applied": all(r.get("applied") for r in results),
        "restored_to_baseline": final.get("cells_total") == baseline.get("cells_total"),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("baseline cells_total", baseline.get("cells_total"))
    for r in results:
        print(" ", r["name"][:56], "| applied", r.get("applied"), "| cells",
              (r.get("reading") or {}).get("cells_total"), "| delta", r.get("delta_vs_baseline"),
              "| restored", r.get("restored_byte_identical"))
    print("after restoring cells_total", final.get("cells_total"))
    return 0 if (payload["all_arms_applied"] and payload["restored_to_baseline"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
