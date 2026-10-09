"""Commander's mechanical derivation for ORD-0300 - r2.

What r1 got wrong, and why this is a ruler fix rather than a lane finding:
  r1 asserted "EVERY cell must judge both the server side and the rendered sentence".  Read against the
  published rows that accusation was false for four cells - C1/C5 are server-side-by-subject cells and C4
  is a client-deadline cell - and it was also false for C3, which DOES carry both sides
  (`other_legs_in_the_same_run.plans_generate_status` and `server_sentence_read_by_second_ro_connection`
  next to `painted_label` / `painted_value`).  r1 missed those because its server-key pattern demanded
  `http_status|content_type|bytes|elapsed_ms|client_error|status_code` and the lane wrote `..._status`.
  So r1's `both_sides_judged=False` rows were an instrument defect: too-narrow lookup + a rule applied
  to cells whose subject is one-sided.  Both are fixed here and r1 stays published as the wrong version.

r2's three rules, each derived from a row rather than typed:
  R-A every cell has >=1 measured leaf and is bound to the tip that was authoritative when it ran;
  R-B the delivery as a whole contains >=1 server-side cell AND >=1 screen-side cell under one run id
      (that is what "两侧同判" means at delivery level);
  R-C any cell that ASSERTS something about the screen (its id or verdict names screen/paint/unreachable/
      quote/details) must itself carry screen fields AND server fields - a claim about what the user
      reads cannot be made from a server row alone.
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

SERVER_KEYS = re.compile(r"http_status|content_type|\bbytes\b|_bytes|elapsed_ms|client_error|status"
                         r"|body_head|error_code|error_message|reason_code|url_tail|busy_timeout|deadline_ms", re.I)
SCREEN_KEYS = re.compile(r"screen|rendered|visible|inner_?text|painted|detail_regions|details|dom"
                         r"|label|_value|copy|sentence|data_result_status", re.I)
SCREEN_CLAIM = re.compile(r"screen|paint|unreachable|says|quote|detail|attribut", re.I)


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-ord0300-verify-r2"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            last = sys.exc_info()[1]
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"GET {path} failed after retries: {last}")


def leaves(obj, prefix=""):
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
        lv = leaves(c.get("measured"))
        names = [p for p, _ in lv]
        srv = sorted({p for p in names if SERVER_KEYS.search(p.rsplit(".", 1)[-1])})
        scr = sorted({p for p in names if SCREEN_KEYS.search(p.rsplit(".", 1)[-1])})
        claim_about_screen = bool(SCREEN_CLAIM.search(f"{c.get('id')} {c.get('verdict')}"))
        per_cell.append({
            "id": c.get("id"),
            "verdict": c.get("verdict"),
            "cell_measured_on": c.get("measured_on"),
            "R_A_measured_rows": len(names),
            "R_A_generation_bound": c.get("measured_on") == TIP,
            "server_field_count": len(srv),
            "screen_field_count": len(scr),
            "asserts_something_about_the_screen": claim_about_screen,
            # R-C only bites cells that claim about the screen; others are judged by R_A/R_B
            "R_C_ok": (not claim_about_screen) or (bool(srv) and bool(scr)),
            "why_chars": len(c.get("why") or ""),
        })

    r_a = all(x["R_A_measured_rows"] > 0 and x["R_A_generation_bound"] for x in per_cell) and bool(cells)
    any_srv = any(x["server_field_count"] > 0 for x in per_cell)
    any_scr = any(x["screen_field_count"] > 0 for x in per_cell)
    r_b = any_srv and any_scr and j.get("measured_on") == TIP
    r_c = all(x["R_C_ok"] for x in per_cell)
    ok_hash = recomputed == RECEIPT
    ok_b1 = j.get("derived_result") in (None, "", "null") and bool(j.get("claimed_result"))
    cells_making_screen_claims = [x["id"] for x in per_cell if x["asserts_something_about_the_screen"]]

    overall = ("ORD0300_READINGS_IN_ORDER" if (ok_hash and r_a and r_b and r_c and ok_b1)
               else "NOT_VERIFIED_SEE_DECISIONS")

    open("_ord0300_receipt_refetched.json", "wb").write(raw)
    ruler = subprocess.run([sys.executable, "receipt_cell_derivation_check_r2.py",
                            "--receipt", "_ord0300_receipt_refetched.json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    ruler_line = next((l.strip() for l in (ruler.stdout or "").splitlines() if "overall" in l), None)

    out = {
        "schema": "CNX_CMDR_DERIVATION_V2",
        "revision_note": "r1 (`verify_ord0300_commander_r1.py`) accused four cells of not judging both "
                         "sides; that was this instrument's fault (server-key pattern missed `*_status`, "
                         "and the both-sides rule was applied to cells whose subject is one-sided). "
                         "r2 keeps r1 published unedited.",
        "order": "ORD-0300",
        "lane": j.get("lane"),
        "run_id": j.get("run_id"),
        "asked_in": j.get("asked_in"),
        "subject_blob_cited": RECEIPT,
        "subject_bytes": len(raw),
        "recomputed_git_blob_sha1": recomputed,
        "recomputed_equals_cited": ok_hash,
        "authoritative_tip": TIP,
        "receipt_measured_on": j.get("measured_on"),
        "cells_total": len(cells),
        "cells": per_cell,
        "cells_asserting_about_the_screen": cells_making_screen_claims,
        "q38_ruler": {"instrument": "receipt_cell_derivation_check_r2.py",
                      "exit_code": ruler.returncode, "line_printed": ruler_line},
        "decisions": {
            "blob_recompute_matches_citation": ok_hash,
            "R_A_every_cell_measured_something_and_bound_to_tip": r_a,
            "R_B_delivery_has_server_side_AND_screen_side_cells_under_one_generation": r_b,
            "R_C_every_screen_claiming_cell_also_carries_server_fields": r_c,
            "B1_lane_signed_claimed_not_derived": ok_b1,
        },
        "overall": overall,
        "scope": "Proves only internal order + generation binding of the receipt's readings. It does not "
                 "sign derived_result (red team's job), does not prove the product sentence is right, "
                 "and does not decide whether this state should reach the phone.",
    }
    json.dump(out, open("_ord0300_commander_derivation_r2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("overall:", overall)
    for k, v in out["decisions"].items():
        print("   ", k, "=", v)
    for x in per_cell:
        print("  ", x["id"][:46], "| srv", x["server_field_count"], "| scr", x["screen_field_count"],
              "| screen-claim", x["asserts_something_about_the_screen"], "| R_C", x["R_C_ok"])
    print("  q38 ruler:", ruler.returncode, ruler_line)
    print("wrote _ord0300_commander_derivation_r2.json")
    return 0 if overall == "ORD0300_READINGS_IN_ORDER" else 3


if __name__ == "__main__":
    raise SystemExit(main())
