#!/usr/bin/env python3
"""ORD-0407 -- freeze the *before* shape so the change's cost is a measured delta.

Reads the C1 receipt produced on the authoritative tip and writes the parts of it the gate compares
against: every cell box, and every control that was hittable inside the first screen (centre on or
above the 768 px line the order names).  Constraint ② of the order is "do not push a control out of
its hit area", and ORD-0338 is the case where a padding change moved a real control inside a 229 px
band.  A claim of "nothing moved" needs the before list, not an after list alone.

    python review/n3_0407_baseline_r1.py --receipt review/evidence/ord0407/<run>__C1.json \
        --head 79ca877cb8b3a890a0d9bb353ac1b56b15525510 \
        --out review/n3_0407_evidence_r1/controls_before_79ca877c.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FLOOR = 768


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--commit-while-measured", default="", dest="commit")
    ap.add_argument("--run-log", default="", dest="runlog")
    a = ap.parse_args()

    raw = json.loads(Path(a.receipt).read_text(encoding="utf-8"))
    if raw.get("test_status") != "passed":
        raise SystemExit(f"RECEIPT_NOT_PASSED {a.receipt} status={raw.get('test_status')}")
    if len(a.head) != 40 or all(c in "0123456789abcdef" for c in a.head) is False:
        raise SystemExit(f"HEAD_MUST_BE_40_HEX got {a.head!r}")

    screens = {}
    for key, value in raw["screens"].items():
        if not key.startswith("unlocatable_trip/"):
            continue
        seen: dict[str, int] = {}
        hittable = []
        for c in value["controls"]:
            if not (c["hit_test"] and c["centre"][1] <= FLOOR):
                continue
            bare = c["testid"] if c["testid"] else c["name"]
            seen[bare] = seen.get(bare, 0) + 1
            # Same identity rule as the gate's own census: a test id where there is one, else
            # (name, n-th of that name in document order).  Most controls here carry no test id.
            ident = c["testid"] if c["testid"] else f"{bare}#{seen[bare]}"
            hittable.append({"key": ident, "testid": c["testid"], "name": c["name"], "centre": c["centre"]})
        screens[key] = {
            "cells": {
                name: (box["box"] if isinstance(box, dict) else None)
                for name, box in value["cells"].items()
            },
            "panel_heights": {
                name: (box["box"][3] if isinstance(box, dict) and box["box"] else None)
                for name, box in value["cells"].items()
            },
            "hittable_above_floor": hittable,
        }

    out = {
        "measured_from_receipt": Path(a.receipt).name,
        "tree_head": a.head,
        # The bytes measured belong to `tree_head`, but the *commit* the run started from can differ:
        # re-freezing a baseline on a newer tip means checking that tip's product files back out over a
        # lane head, so HEAD stays the lane's.  Both are recorded instead of one being glossed.
        "commit_head_while_measuring": a.commit,
        "run_log": a.runlog.replace("\\", "/"),
        "hit_floor_px": FLOOR,
        "viewport": [390, 844],
        "screens": screens,
        "counts": {
            "screens": len(screens),
            "hittable_controls_above_floor": sum(
                len(v["hittable_above_floor"]) for v in screens.values()
            ),
        },
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["counts"], ensure_ascii=False))
    for name, v in screens.items():
        print(name, "cells", {k: b for k, b in v["cells"].items() if b})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
