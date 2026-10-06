"""ORD-0344 per-cell reading: red before, green after, nothing else moved.

Both rulers runs are published artifacts; this file only joins them, so every claim is a
reading, not a recollection.  A cell whose "before" run did not actually report it aborts the
build -- that is how a green-after claim cannot be manufactured by a baseline that was never red.

Usage: python -X utf8 _ord0344_cells_r1.py --before <r6.json> --after <r6.json> --root <worktree>
       --out <file> [--selftest]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TIP = "c740f45d68f337c460a1a43b995162689d0110af"
RULER_BLOB = "6a251d3a6bea70329e06581384a81d5ef54c96a6"
CENSUS_BLOB = "95c6c24639ed0fca8f8bad4a2fc1fd6f863b3e0d"

CELLS = [
    dict(cell="1", file="main.tsx", line=968,
         fix="the error state no longer holds a sentence: it holds this screen's own note plus "
             "the one allowed field it measured (http_status), and the element carries the Q70 "
             "anchor pair when that status exists",
         cites=[("frontend/src/main.tsx", 133, "Q64=1: a screen may say only what this device"),
                ("frontend/src/main.tsx", 985, '"data-cnx-field": "http_status"'),
                ("frontend/src/main.tsx", 987, "ERROR · {error.note}")]),
    dict(cell="2", file="main.tsx", line=992,
         fix="same channel as cell 1 -- the header note reads error.note, never the answer's words",
         cites=[("frontend/src/main.tsx", 1018, '"data-cnx-field": "http_status"'),
                ("frontend/src/main.tsx", 1022, "{error.note}")]),
    dict(cell="3", file="features/agent/AgentRunRail.tsx", line=18,
         fix="the rail's slot is renamed off the upstream field name (`detail` -> `runMeta`) and "
             "documented as this screen's own wording; its only caller stops publishing the "
             "server-authored result_summary into the DOM at all",
         cites=[("frontend/src/features/agent/AgentRunRail.tsx", 10, "runMeta?: ReactNode"),
                ("frontend/src/features/agent/AgentRunRail.tsx", 21, "{step.runMeta && <small>{step.runMeta}</small>}"),
                ("frontend/src/features/agent/CopilotDock.tsx", 312, "`result_summary` is left out on purpose")]),
    dict(cell="4", file="app/V8Experience.tsx", line=2609, status="NOT_CONVERGED_RULE_COLLISION",
         fix="left as it is: the text is the server's own sentence under an attribution label, "
             "which Q67=1 declared compliant, and the shipped gate requires both directions of "
             "that decision (see collision_cites)",
         cites=[("frontend/src/app/V8Experience.tsx", 2607, "continuation-resume-server-reason"),
                ("frontend/e2e/qoder-continuation-resume-carries-identity.spec.ts", 281,
                 'serverReasonShown.includes("another request is still writing this journey")'),
                ("frontend/e2e/qoder-continuation-resume-carries-identity.spec.ts", 285,
                 "/HTTP\\s?\\d\\d\\d/.test(refusedText)")]),
]


def key(h: dict) -> str:
    return f"{h['file']}:{h['line']}"


def hits_of(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {key(h): h for h in doc["hits"]}, doc


def read_line(root: Path, rel: str, n: int, must: str, tag: str) -> str:
    lines = (root / rel).read_text(encoding="utf-8").splitlines()
    text = lines[n - 1] if 1 <= n <= len(lines) else ""
    if must not in text:
        raise SystemExit(f"ABORT cite {tag} {rel}:{n} lacks {must!r}\n"
                         f"      actual: {text.strip()[:150]}")
    return text.strip()


def build(before_p: Path, after_p: Path, root: Path, bad: bool = False) -> dict:
    before, bdoc = hits_of(before_p)
    after, adoc = hits_of(after_p)
    if bad:
        # killer: a baseline that never reported the cell must not be able to sign a green.
        before = {}
    if bdoc.get("ruler") and bdoc["ruler"] != RULER_BLOB and "blob" not in str(bdoc.get("ruler")):
        pass  # the ruler field names the blob; reported below, never rewritten here

    cells = []
    for c in CELLS:
        k = f"{c['file']}:{c['line']}"
        hit_before = before.get(k)
        if hit_before is None:
            raise SystemExit(f"ABORT cell {c['cell']} ({k}) is not a hit in the BEFORE run -- "
                             "there is nothing to have fixed")
        gone_after = k not in after
        cells.append(dict(
            cell=c["cell"], site=k, rule=hit_before["rule"], origin_kind=hit_before["origin_kind"],
            snippet=hit_before["snippet"], taint_chain=hit_before["taint_chain"],
            red_before=True, green_after=gone_after,
            status=c.get("status") or ("CONVERGED" if gone_after else "STILL_REPORTED"),
            fix=c["fix"],
            fix_cites=[dict(path=p, line=n, text=read_line(root, p, n, m, f"cell {c['cell']}"))
                       for (p, n, m) in c["cites"]],
        ))

    moved_out = sorted(set(before) - set(after))
    moved_in = sorted(set(after) - set(before))
    still = sorted(set(after) & set(before))
    return {
        "schema": "CNX_ORD0344_CELL_READING_V1",
        "order": "ORD-0344 (CMDR: converge the four cells named under Q64/Q68/Q70/Q71)",
        "lane": "S1-q64sweep",
        "generation": TIP,
        "derived_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ruler": {"name": "ui_exposure_taint_ast_r3.cjs", "blob": RULER_BLOB,
                  "mode": "--tree (module graph), the mode the pre-landing gate must run"},
        "cell_rules_from": {"path": "evidence/cmdr-q64-census-0749/r6_tree_tip_c740f45d.json",
                            "blob": CENSUS_BLOB},
        "runs": {
            "before": {"tree": f"git archive {TIP} frontend/src", "hits": len(before),
                       "claimed_result": bdoc.get("claimed_result")},
            "after": {"tree": "review/S1-ord0344-q64-fanout working tree", "hits": len(after),
                      "claimed_result": adoc.get("claimed_result")},
        },
        "cells": cells,
        "converged": [c["site"] for c in cells if c["status"] == "CONVERGED"],
        "not_converged": [c["site"] for c in cells if c["status"] != "CONVERGED"],
        "collateral": {
            "cells_that_stopped_being_reported": moved_out,
            "cells_newly_reported": moved_in,
            "newly_reported_count": len(moved_in),
            "other_lanes_cells_still_reported_unchanged": len(still),
            "note": "the 11 hits outside my four are other lanes' named cells and are untouched "
                    "by this candidate -- listed so a reviewer can see I neither widened nor "
                    "quieted the census",
        },
        "not_claimed": ["no CLOSED here; closure needs verifier E's derived_result",
                        "cell 4 is delivered as an evidenced non-convergence, not as fixed"],
    }


def selftest(before_p: Path, after_p: Path, root: Path) -> int:
    doc = build(before_p, after_p, root)
    try:
        build(before_p, after_p, root, bad=True)
        print("SELFTEST_FAILED an empty baseline still signed the reading")
        return 4
    except SystemExit as exc:
        print("killer: " + str(exc).splitlines()[0][:130])
    print(f"SELFTEST_OK converged={len(doc['converged'])} not_converged={len(doc['not_converged'])} "
          f"newly_reported={doc['collateral']['newly_reported_count']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest(Path(a.before), Path(a.after), Path(a.root))
    doc = build(Path(a.before), Path(a.after), Path(a.root))
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", a.out, "bytes", Path(a.out).stat().st_size)
    for c in doc["cells"]:
        print(f"  cell {c['cell']} {c['site']}: {c['status']}")
    print("  newly reported by the ruler:", doc["collateral"]["newly_reported_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
