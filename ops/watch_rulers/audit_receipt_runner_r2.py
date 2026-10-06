"""Run any revision of the coordinate-audit ruler and emit a receipt whose verdicts are derived.

Usage: audit_receipt_runner_r1.py <ruler_module.py> <out.json>
The ruler must expose CLAIMS = ((repo_path, declared_blob, declared_bytes, cited_by), ...).
Each cell's verdict is computed here from the values read back off the readable branch; the summary
counts are aggregated from those booleans.  Nothing in the output is a hand-written "OK".
"""
import hashlib
import importlib.util
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
import read_remote_file as rr  # noqa: E402


def blob_of(path):
    data = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), len(data)


def tip_of(branch):
    """The commit sha the readable branch pointed at WHEN this receipt was written (ORD-0283/C8).

    Without it, "60 claims OK at 06:0x" cannot be replayed against the same tree: `commander/control`
    moves every time anyone publishes.  Route note (a trap I have hit twice): `/commits/{ref}` returns a
    LIST of commits, so the tip is `/commits?sha=<ref>&per_page=1`.
    """
    try:
        page = rr.get(f"{rr.API}/repos/{rr.REPO}/commits?sha={rr.BRANCH}&per_page=1")
        c = page[0] if isinstance(page, list) and page else page
        return c.get("sha"), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {str(exc)[:90]}"


def load_ruler(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", "_ruler"), name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "CLAIMS"):
        raise SystemExit(f"{name} has no CLAIMS")
    return mod


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 5
    ruler_path, out_path = sys.argv[1], sys.argv[2]
    ruler = load_ruler(ruler_path)
    instr_sha, instr_bytes = blob_of(ruler_path)
    tip, tip_err = tip_of(rr.BRANCH)
    print("ref tip read:", (tip or "UNREADABLE"), (tip_err or ""))
    cells = []
    for path, want, size, why in ruler.CLAIMS:
        cell = {"path": path, "declared_blob": want, "declared_bytes": size, "cited_by": why,
                "remote_blob": None, "remote_bytes": None, "read_error": None}
        try:
            meta = rr.get(f"{rr.API}/repos/{rr.REPO}/contents/{path}?ref={rr.BRANCH}")
            cell["remote_blob"] = meta.get("sha")
            cell["remote_bytes"] = meta.get("size")
        except Exception as exc:  # noqa: BLE001
            cell["read_error"] = f"{type(exc).__name__}: {str(exc)[:90]}"
        cell["blob_matches"] = cell["remote_blob"] == want
        cell["size_matches"] = cell["remote_bytes"] == size
        cell["verdict"] = "OK" if (cell["blob_matches"] and cell["size_matches"]) else "FAIL"
        cells.append(cell)
    failing = sum(1 for c in cells if c["verdict"] != "OK")
    out = {
        "schema": "CNX_COORDINATE_AUDIT_RECEIPT_V2",
        "instrument": {"repo_path": "live_checks/" + os.path.basename(ruler_path),
                       "blob": instr_sha, "bytes": instr_bytes},
        "runner": {"repo_path": "live_checks/audit_receipt_runner_r1.py",
                   "blob": blob_of(os.path.abspath(__file__))[0],
                   "bytes": blob_of(os.path.abspath(__file__))[1],
                   "command": f"python live_checks/audit_receipt_runner_r1.py {os.path.basename(ruler_path)} {out_path}"},
        "branch": rr.BRANCH, "repo": rr.REPO,
        "ref_tip_read": tip, "ref_tip_read_error": tip_err,
        "tip_read_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generated_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cells": cells, "claims": len(cells), "failing": failing,
        "overall": ("ALL_COORDINATES_RESOLVE" if failing == 0 and tip else
                    "TIP_UNREADABLE_RECEIPT_NOT_REPLAYABLE" if failing == 0 else
                    "SOME_COORDINATES_DO_NOT_RESOLVE"),
        "coverage_note": "Audits only that each cited path resolves byte-for-byte on the readable branch. "
                         "It says nothing about whether numbers inside a receipt are true; those are judged "
                         "by verifier receipts / recomputation rulers (e.g. receipt_consistency_o0276_r1.py).",
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("claims", len(cells), "failing", failing, "ruler_blob", instr_sha, "ruler_bytes", instr_bytes)
    print("ref_tip_read", tip, "overall", out["overall"])
    print("wrote", out_path)
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
