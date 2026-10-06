"""Run the r3 coordinate audit and emit a machine-checkable receipt (no literal verdicts).

Every verdict in the receipt is derived at write time from (declared blob, declared size) vs the
values read back from `commander/control`; the summary counts are aggregated from those derived
booleans, not typed.  The instrument's own blob is recomputed from the file bytes so a reader can
prove WHICH ruler produced the receipt.
"""
import hashlib
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import read_remote_file as rr  # noqa: E402
import audit_closure_coordinates_r3 as ruler  # noqa: E402

INSTR = "audit_closure_coordinates_r3.py"


def blob_sha(path):
    data = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), len(data)


def main():
    instr_sha, instr_bytes = blob_sha(INSTR)
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
        "instrument": {"repo_path": "live_checks/" + INSTR, "blob": instr_sha, "bytes": instr_bytes},
        "branch": rr.BRANCH,
        "repo": rr.REPO,
        "command": "python live_checks/audit_closure_coordinates_r3.py  (per-cell contents API read: "
                   "GET /repos/Canshu-King/CityNexus/contents/<path>?ref=commander/control)",
        "generated_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cells": cells,
        "claims": len(cells),
        "failing": failing,
        "overall": "ALL_COORDINATES_RESOLVE" if failing == 0 else "SOME_COORDINATES_DO_NOT_RESOLVE",
        "coverage_note": "This audits ONLY that each cited path resolves byte-for-byte on the readable "
                         "branch. It says nothing about whether the numbers inside a receipt are true; "
                         "those are judged by the verifier receipts named in each cell.",
    }
    name = "audit_r3_receipt.json"
    with open(name, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("claims", len(cells), "failing", failing, "instrument_blob", instr_sha, "bytes", instr_bytes)
    print("wrote", name)
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
