"""Commander's mechanical derivation for ORD-0300 (HJ-P3's W2 / T-b re-measurement).

Why a program instead of reading the post: the standing rule is that a verdict field must be DERIVED
from measured rows, never typed.  ORD-0300's own acceptance criteria were (1) generation binding,
(2) both-sides judgement - a server-side field AND the sentence actually rendered on screen, (3) the
old cells kept and re-labelled rather than edited.  Each of those is checkable from the published
bytes, so this script fetches them by 40-hex blob sha, recomputes git's hash, and answers the three
criteria per cell.  Nothing here asserts that the product is fixed; it asserts what the receipt proves.
"""
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
TIP = "90d29a172e186aab6e6cb138ab4583ccf93bfa68"
RECEIPT = "6e93836db5b6a5322b4b7d8c77e0e240c0aaf894"
KEEP_5CELL = "40a508e7fb4f3f482b6cb51c269584e983056254"
SERVER_KEYS = re.compile(r"http_status|content_type|bytes|elapsed_ms|client_error|status_code", re.I)
SCREEN_KEYS = re.compile(r"screen|rendered|visible|inner_?text|dom|details|label|copy|sentence", re.I)


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-ord0300-verify"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001 - transient TLS jitter on this network is measured, not assumed
            last = sys.exc_info()[1]
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"GET {path} failed after retries: {last}")


def leaves(obj, prefix=""):
    """Flatten to (path, value) so key-name tests run over whatever nesting the lane chose."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += leaves(v, f"{prefix}[{i}]")
    else:
        out.append((prefix, obj))
    return out


def main():
    d = get(f"/repos/{REPO}/git/blobs/{RECEIPT}")
    raw = base64.b64decode(d["content"])
    recomputed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    j = json.loads(raw.decode())
    cells = j.get("cells") or []

    per_cell = []
    for c in cells:
        lv = leaves(c.get("measured") if isinstance(c.get("measured"), (dict, list)) else c)
        server_paths = sorted({p for p, _ in lv if SERVER_KEYS.search(p.rsplit(".", 1)[-1])})
        screen_paths = sorted({p for p, _ in lv if SCREEN_KEYS.search(p.rsplit(".", 1)[-1])})
        per_cell.append({
            "id": c.get("id"),
            "verdict": c.get("verdict"),
            "cell_measured_on": c.get("measured_on"),
            "generation_binding_ok": c.get("measured_on") == TIP,
            "server_side_fields_present": len(server_paths),
            "server_field_paths": server_paths[:6],
            "screen_side_fields_present": len(screen_paths),
            "screen_field_paths": screen_paths[:6],
            "both_sides_judged": bool(server_paths) and bool(screen_paths),
            "why_chars": len(c.get("why") or ""),
            "derived_result_present": "derived_result" in c,
        })

    sup = j.get("supersedes")
    sup_rows = sup if isinstance(sup, list) else ([sup] if sup else [])
    sup_relabel_ok = bool(sup_rows) and all(
        re.search(r"SUPERSEDED|supersed", json.dumps(s, ensure_ascii=False)) for s in sup_rows)

    # independent second ruler: the project's own per-cell derivation gate, run on the published bytes
    open("_ord0300_receipt_refetched.json", "wb").write(raw)
    ruler = subprocess.run([sys.executable, "receipt_cell_derivation_check_r2.py",
                            "--receipt", "_ord0300_receipt_refetched.json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    ruler_line = next((l.strip() for l in (ruler.stdout or "").splitlines() if "overall" in l), None)

    ok_gen = all(x["generation_binding_ok"] for x in per_cell) and j.get("measured_on") == TIP
    ok_both = all(x["both_sides_judged"] for x in per_cell)
    ok_cells = len(per_cell) > 0
    ok_hash = recomputed == RECEIPT
    # B-1: the delivering lane must NOT sign its own closure
    ok_b1 = j.get("derived_result") in (None, "", "null") and j.get("claimed_result") not in (None, "")

    overall = ("ORD0300_READINGS_IN_ORDER" if (ok_hash and ok_cells and ok_gen and ok_both and ok_b1)
               else "NOT_VERIFIED_SEE_DECISIONS")

    out = {
        "schema": "CNX_CMDR_DERIVATION_V1",
        "order": "ORD-0300",
        "lane": j.get("lane"),
        "run_id": j.get("run_id"),
        "asked_in": j.get("asked_in"),
        "subject_blob_cited": RECEIPT,
        "subject_bytes": len(raw),
        "recomputed_git_blob_sha1": recomputed,
        "recomputed_equals_cited": ok_hash,
        "authoritative_tip_at_run": TIP,
        "cells_total_declared_by_lane": len(cells),
        "cells": per_cell,
        "supersedes_rows": len(sup_rows),
        "supersedes_relabelled_not_deleted": sup_relabel_ok,
        "q38_ruler": {"instrument": "receipt_cell_derivation_check_r2.py",
                      "exit_code": ruler.returncode, "line_printed": ruler_line},
        "keep_5cell_copy": {"cited_blob": KEEP_5CELL,
                            "note": "the lane preserved the earlier 5-cell bytes under "
                                    "RECEIPT_O0300-2610_r1_5cells.json after having published twice at "
                                    "the same path - recorded as a discipline breach WITH remediation, "
                                    "this field only states the copy exists at that sha in the tree."},
        "decisions": {
            "blob_recompute_matches_citation": ok_hash,
            "at_least_one_cell_measured": ok_cells,
            "every_cell_bound_to_authoritative_tip": ok_gen,
            "every_cell_judges_server_AND_rendered_text": ok_both,
            "lane_did_not_sign_its_own_derived_result": ok_b1,
        },
        "overall": overall,
        "scope": "Answers only: are the receipt's readings internally in order and generation-bound. "
                 "Does NOT prove the product copy is fixed, does NOT sign derived_result (red team's), "
                 "and does NOT judge whether the swap should carry this state to the phone.",
    }
    json.dump(out, open("_ord0300_commander_derivation_r1.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("overall:", overall)
    for k, v in out["decisions"].items():
        print("   ", k, "=", v)
    for x in per_cell:
        print("  cell", x["id"], "| verdict", x["verdict"], "| gen", x["generation_binding_ok"],
              "| server", x["server_side_fields_present"], "| screen", x["screen_side_fields_present"],
              "| both", x["both_sides_judged"])
    print("  q38 ruler:", ruler.returncode, ruler_line)
    print("wrote _ord0300_commander_derivation_r1.json")
    return 0 if overall == "ORD0300_READINGS_IN_ORDER" else 3


if __name__ == "__main__":
    raise SystemExit(main())
