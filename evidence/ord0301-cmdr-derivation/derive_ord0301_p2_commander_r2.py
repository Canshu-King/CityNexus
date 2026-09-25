"""Commander's first-hand derivation for ORD-0301 pass 2 (HJ-P3's 24-row re-issue).

Schema note, printed into the artifact: pass 2's rows are NOT flat.  Each row carries
`server_side` and `screen_side` sub-dicts, so the flat key lists used for pass 1 would silently
collect nothing here.  This script reads the nested keys it actually finds and prints them.

Tests, all computed over the fetched rows:
  C-1  Do pass 1 and pass 2 use the same row ids for the same observations?  (If a bare `R17` could
       mean two things, no downstream order may cite one without naming its batch.)
  T-A  every row has a server reading AND a screen reading
  T-B  every row says who answered
  T-D  every row carries painted text (`painted_first_line` non-empty)
  X-4  200 + a specific cause asserted + no 技术详情 block + no reason label/value
       = "the screen states a cause with nothing underneath it"
  X-5  the painted sentence tells the traveller to look in 技术详情 WHILE `details_elements_in_dom`
       is 0 = the copy points at UI that is not there.  This one is a defect B can be handed directly.
       Two-way guard: rows whose details count is > 0 must not be flagged.
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
REF = "commander/control"
DIR = "evidence/ord0301-screen-speaks-range-hjp3"
DETAILS_WORDS = ("技术详情", "技术詳細", "technical details")


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-p2-r2"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (k + 1))
    raise SystemExit("GET " + path + " failed: " + str(last))


def fetch(path):
    meta = get("/repos/" + REPO + "/contents/" + path + "?ref=" + urllib.parse.quote(REF, safe=""))
    raw = base64.b64decode(get("/repos/" + REPO + "/git/blobs/" + meta["sha"])["content"])
    return meta, raw


def sha1_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_ord0301_p2_cmdr_derivation_r2.json")
    a = ap.parse_args()

    m1, raw1 = fetch(DIR + "/RECEIPT_O0301-1500.json")
    m2, raw2 = fetch(DIR + "/RECEIPT_O0301P2-1540_r2.json")
    m3, raw3 = fetch(DIR + "/table_O0301_p2_24rows.json")
    p1 = json.loads(raw1.decode("utf-8", "replace"))
    p2 = json.loads(raw2.decode("utf-8", "replace"))
    tab = json.loads(raw3.decode("utf-8", "replace"))

    rows = tab["rows"]
    ids2 = [r["row"] for r in rows]
    ids1 = list(p1["table"]["rows"])

    # C-1: same id must mean the same observation - compare the run id + stamp + verdict
    fp1 = {}
    for cell in p1["cells"]:
        m = cell.get("measured") or {}
        cand = ([m["row"]] if isinstance(m.get("row"), dict) else []) + list(m.get("rows") or [])
        for r in cand:
            if isinstance(r, dict) and r.get("row"):
                fp1[r["row"]] = (r.get("run_id"), r.get("policy_stamp"), r.get("verdict"))
    fp2 = {r["row"]: (r.get("run_id"), r.get("policy_stamp"), r.get("verdict")) for r in rows}
    shared = [i for i in ids2 if i in fp1]
    mismatched = [i for i in shared if fp1[i] != fp2[i]]
    pass2_only = [i for i in ids2 if i not in fp1]

    per, x5_unflagged_positive = [], []
    for r in rows:
        s = r.get("server_side") or {}
        c = r.get("screen_side") or {}
        paint = (c.get("painted_first_line") or "") .strip()
        fulltext = (c.get("painted_text") or "").strip()
        det = c.get("details_elements_in_dom")
        mentions_details = any(w in fulltext for w in DETAILS_WORDS)
        x4 = (s.get("http_status") == 200 and bool(paint) and det == 0
              and not c.get("reason_label_painted") and not (c.get("reason_value_painted") or "").strip())
        x5 = mentions_details and det == 0
        if mentions_details and isinstance(det, int) and det > 0:
            x5_unflagged_positive.append(r["row"])
        per.append({"row": r["row"], "class_as_asked": r.get("outcome_class_as_asked", "")[:14],
                    "verdict": r.get("verdict"),
                    "server_keys_present": sorted(k for k, v in s.items() if v not in (None, "", [], {}))[:10],
                    "screen_keys_present": sorted(k for k, v in c.items() if v not in (None, "", [], {}))[:10],
                    "T_A": bool(s) and bool(c),
                    "T_B": bool(s.get("answer_attributed_to")),
                    "T_D": bool(paint),
                    "painted_first_line": paint[:40],
                    "details_elements_in_dom": det,
                    "mentions_technical_details_in_copy": mentions_details,
                    "X_4_cause_without_evidence_block": bool(x4),
                    "X_5_copy_points_at_absent_details_block": bool(x5),
                    "app_threw_on_the_body": r.get("app_threw_on_the_body")})

    t_a = [x["row"] for x in per if not x["T_A"]]
    t_b = [x["row"] for x in per if not x["T_B"]]
    t_d = [x["row"] for x in per if not x["T_D"]]
    x4 = [x["row"] for x in per if x["X_4_cause_without_evidence_block"]]
    x5 = [x["row"] for x in per if x["X_5_copy_points_at_absent_details_block"]]
    not_measured = [x["row"] for x in per if x["verdict"] == "NOT_MEASURED"]

    out = {"schema": "CNX_CMDR_DERIVATION_V2", "order": "ORD-0301", "phase": "pass2", "revision": "r2",
           "artifacts": {
               "pass1_receipt": {"path": DIR + "/RECEIPT_O0301-1500.json", "sha": m1["sha"],
                                 "recomputed": sha1_of(raw1), "bytes": len(raw1)},
               "pass2_receipt": {"path": DIR + "/RECEIPT_O0301P2-1540_r2.json", "sha": m2["sha"],
                                 "recomputed": sha1_of(raw2), "bytes": len(raw2)},
               "pass2_table_24rows": {"path": DIR + "/table_O0301_p2_24rows.json", "sha": m3["sha"],
                                      "recomputed": sha1_of(raw3), "bytes": len(raw3)}},
           "schema_probe": {"pass2_row_top_keys": sorted(rows[0]), "server_side_keys": sorted(
               (rows[0].get("server_side") or {})), "screen_side_keys": sorted(
               (rows[0].get("screen_side") or {}))},
           "C_1": {"pass1_row_count": len(ids1), "pass2_row_count": len(ids2),
                   "shared_ids": shared, "shared_ids_with_different_fingerprint": mismatched,
                   "pass2_only_ids": pass2_only},
           "T_A_rows_missing_a_side": t_a, "T_B_rows_not_naming_who": t_b,
           "T_D_rows_with_empty_painted": t_d,
           "X_4_cause_asserted_with_no_evidence_block": x4,
           "X_5_copy_points_at_an_absent_details_block": x5,
           "X_5_positive_control_not_flagged_because_details_present": x5_unflagged_positive,
           "verdict_NOT_MEASURED_rows": not_measured,
           "per_row": per,
           "decisions": {
               "all_three_artifacts_rehash_to_cited": (m1["sha"] == sha1_of(raw1)
                                                       and m2["sha"] == sha1_of(raw2)
                                                       and m3["sha"] == sha1_of(raw3)),
               "C_1_row_ids_are_stable_across_batches": not mismatched,
               "T_A_every_row_has_both_sides": not t_a,
               "T_B_every_row_names_who_answered": not t_b,
               "T_D_every_row_carries_painted_text": not t_d,
               "X_4_shape_is_present_in_the_rows": len(x4) > 0,
               "X_5_shape_is_present_in_the_rows": len(x5) > 0},
           "scope": "What the published 24 rows themselves say. Does not sign derived_result, does not "
                    "grade HONEST/MISLEADS (that is the lane's judgment rule and the red team's to "
                    "derive), and does not choose wording. X_4 and X_5 are shapes observed in readings, "
                    "each reproducible row by row."}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("rehash all three:", out["decisions"]["all_three_artifacts_rehash_to_cited"])
    print("C-1 shared:", len(shared), "| different-meaning:", mismatched or "none", "| pass2-only:", len(pass2_only))
    print("rows", len(rows), "| T_A missing:", t_a or "none", "| T_B missing:", t_b or "none",
          "| T_D empty painted:", t_d or "none")
    print("X-4 cause w/o evidence block:", x4 or "none")
    print("X-5 copy points at absent 技术详情:", x5 or "none", "| positive control (details>0, not flagged):",
          x5_unflagged_positive or "none")
    print("NOT_MEASURED rows:", not_measured)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
