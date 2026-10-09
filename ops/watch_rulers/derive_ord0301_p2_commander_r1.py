"""Commander's first-hand derivation for ORD-0301 pass 2 (HJ-P3's seven extra arms).

What this answers, from published bytes only:
  C-1  Do pass 1 and pass 2 use the SAME row ids for DIFFERENT observations?  Pass 1 has R1..R17 and
       pass 2's table has 24 rows; the bus post maps "3 -> R17,R18" and "5 -> R13,R24", while pass 1's
       R17 was "headers then truncated body" and R13 was a silent read leg.  If the same id carries
       two different meanings across the two batches, no downstream order may quote a bare `R17`.
  T-A  Does every pass-2 PRIMARY row carry both a wire reading and painted text?
  T-B  Does every pass-2 PRIMARY row say who answered?
  T-D  Which pass-2 rows still have an empty `painted_first_line` (the ORD-0306 gap, and whether
       pass 2 actually closed the four pass-1 rows it overlaps)?
  X-4  For the 200-with-empty-or-malformed-payload class: the claim is "the screen asserts a specific
       cause with zero evidence underneath".  Compute it per row rather than trusting the prose:
       cause sentence present AND no details block AND no reason label/value.
"""
import argparse
import base64
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
REF = "commander/control"
DIR = "evidence/ord0301-screen-speaks-range-hjp3"
WIRE = ["http_status", "status", "content_type", "bytes", "client_error", "envelope_code", "declared",
        "sibling_probe", "body"]
PAINT = ["painted_first_line", "card", "says_cannot_reach_server", "details_elements_in_dom",
         "reason_label", "reason_value", "data_result_status", "secondary_surface"]
WHO = ["answer_attributed_to", "who_answered", "declared"]


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-p2"})
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


def present(row, names):
    return [k for k in names if k in row and row[k] not in (None, "", [], {})]


def rows_of(doc):
    out = []
    if isinstance(doc, dict):
        for key in ("rows", "cells", "table", "outcomes"):
            v = doc.get(key)
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, dict):
                        out.append(x)
                    if isinstance(x, dict) and isinstance(x.get("measured"), dict):
                        m = x["measured"]
                        for sub in ("row", "rows"):
                            s = m.get(sub)
                            cand = [s] if isinstance(s, dict) else (s if isinstance(s, list) else [])
                            out += [c for c in cand if isinstance(c, dict)]
        if not out:
            for v in doc.values():
                if isinstance(v, list):
                    out += [x for x in v if isinstance(x, dict) and "row" in x]
    return out


def keyrow(r):
    """A comparable fingerprint of what a row observed."""
    return (r.get("http_status"), r.get("content_type"), str(r.get("declared"))[:60],
            r.get("painted_first_line"), r.get("verdict"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_ord0301_p2_cmdr_derivation_r1.json")
    a = ap.parse_args()

    p1_meta, p1_raw = fetch(DIR + "/RECEIPT_O0301-1500.json")
    p2_meta, p2_raw = fetch(DIR + "/RECEIPT_O0301P2-1540_r2.json")
    t2_meta, t2_raw = fetch(DIR + "/table_O0301_p2_24rows.json")
    p1 = json.loads(p1_raw.decode("utf-8", "replace"))
    p2 = json.loads(p2_raw.decode("utf-8", "replace"))
    tab2 = json.loads(t2_raw.decode("utf-8", "replace"))

    r1rows = rows_of(p1)
    r2rows = rows_of(p2)
    tab2rows = rows_of(tab2)
    # the wide table is the row carrier; the receipt carries cells
    p2rows = r2rows if len(r2rows) >= len(tab2rows) else tab2rows
    which = "receipt cells" if p2rows is r2rows else "table_O0301_p2_24rows"

    by_id1, by_id2 = {}, {}
    for r in r1rows:
        by_id1.setdefault(str(r.get("row")), []).append(r)
    for r in p2rows:
        by_id2.setdefault(str(r.get("row")), []).append(r)
    shared_ids = sorted(set(by_id1) & set(by_id2))
    collisions = []
    for rid in shared_ids:
        k1 = {keyrow(r) for r in by_id1[rid]}
        k2 = {keyrow(r) for r in by_id2[rid]}
        if not (k1 & k2):
            collisions.append({"row_id": rid, "pass1_fingerprints": sorted(map(str, k1))[:3],
                               "pass2_fingerprints": sorted(map(str, k2))[:3],
                               "same_observation": False})
        else:
            collisions.append({"row_id": rid, "same_observation": True})

    per = []
    for r in p2rows:
        w, p, ho = present(r, WIRE), present(r, PAINT), present(r, WHO)
        cause = r.get("painted_first_line") or r.get("card")
        x4 = (r.get("http_status") == 200 and cause and not r.get("details_elements_in_dom")
              and not r.get("reason_label") and not r.get("reason_value"))
        per.append({"row": r.get("row"), "T_A": bool(w) and bool(p), "T_B": bool(ho),
                    "painted_nonempty": bool([k for k in p if k.startswith("painted_") or k == "card"]),
                    "details_elements_in_dom": r.get("details_elements_in_dom"),
                    "http_status": r.get("http_status"), "answer_attributed_to": r.get("answer_attributed_to"),
                    "cause_asserted_without_evidence_block": bool(x4), "verdict": r.get("verdict")})

    empty_painted = [x["row"] for x in per if not x["painted_nonempty"]]
    t_a_bad = [x["row"] for x in per if not x["T_A"]]
    t_b_bad = [x["row"] for x in per if not x["T_B"]]
    x4_rows = [x["row"] for x in per if x["cause_asserted_without_evidence_block"]]

    out = {"schema": "CNX_CMDR_DERIVATION_V2", "order": "ORD-0301", "phase": "pass2",
           "artifacts": {"pass1_receipt": {"path": DIR + "/RECEIPT_O0301-1500.json", "sha": p1_meta["sha"],
                                           "recomputed": hashlib.sha1(b"blob %d\x00" % len(p1_raw) + p1_raw).hexdigest(),
                                           "bytes": len(p1_raw)},
                         "pass2_receipt": {"path": DIR + "/RECEIPT_O0301P2-1540_r2.json", "sha": p2_meta["sha"],
                                           "recomputed": hashlib.sha1(b"blob %d\x00" % len(p2_raw) + p2_raw).hexdigest(),
                                           "bytes": len(p2_raw)},
                         "pass2_table": {"path": DIR + "/table_O0301_p2_24rows.json", "sha": t2_meta["sha"],
                                         "recomputed": hashlib.sha1(b"blob %d\x00" % len(t2_raw) + t2_raw).hexdigest(),
                                         "bytes": len(t2_raw)}},
           "rows_source": which,
           "pass1_rows": len(r1rows), "pass2_rows": len(p2rows),
           "C_1_shared_row_ids": shared_ids,
           "C_1_ids_that_mean_different_things": [c for c in collisions if c.get("same_observation") is False],
           "C_1_ids_that_match": [c["row_id"] for c in collisions if c.get("same_observation")],
           "T_A_rows_missing_a_side": t_a_bad, "T_B_rows_not_naming_who": t_b_bad,
           "T_D_rows_with_empty_painted": empty_painted,
           "X_4_cause_asserted_with_no_evidence_block": x4_rows,
           "per_row": per,
           "decisions": {
               "all_three_artifacts_rehash_to_cited": all(
                   x["sha"] == x["recomputed"] for x in out["artifacts"].values()),
               "C_1_no_bare_row_id_is_safe_across_batches": bool([c for c in collisions
                                                                 if c.get("same_observation") is False]),
               "T_A_every_pass2_row_has_both_sides": not t_a_bad,
               "T_B_every_pass2_row_names_who_answered": not t_b_bad,
               "T_D_all_pass2_rows_carry_painted_text": not empty_painted,
               "X_4_shape_reproduces_from_rows_not_prose": len(x4_rows) > 0},
           "scope": "What pass 2's own rows prove. Does not sign derived_result, does not judge whether "
                    "the NO_PLANS_PRODUCED copy is right or wrong - it only says whether the shape "
                    "HJ-P3 reported is actually present in the published readings."}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("rows source:", which, "| pass1 rows", len(r1rows), "| pass2 rows", len(p2rows))
    print("rehash all three:", out["decisions"]["all_three_artifacts_rehash_to_cited"])
    print("C-1 shared ids:", shared_ids)
    print("C-1 DIFFERENT-MEANING collisions:",
          [c["row_id"] for c in out["C_1_ids_that_mean_different_things"]] or "none")
    print("T_A missing a side:", t_a_bad or "none", "| T_B not naming who:", t_b_bad or "none")
    print("T_D empty painted:", empty_painted or "none")
    print("X-4 cause without evidence block:", x4_rows or "none")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
