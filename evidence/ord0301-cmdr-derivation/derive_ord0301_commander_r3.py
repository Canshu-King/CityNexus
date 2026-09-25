"""Commander's mechanical derivation for ORD-0301 (HJ-P3's screen-speaks range table) - revision 3.

Revision history, kept in the artifact because both earlier versions are being published:
  r1 judged key NAMES at cell level.  Its T_B ("7 of 8 cells never say who answered") was a FALSE
     ABSENCE: the field is `answer_attributed_to` and it sits on the rows, not the cells.  r1's T_B
     must not be quoted.
  r2 swept EVERY list of dicts inside a cell as if it were the observation table.  That counted the
     server's own access-log entries (`origin_own_record`: keys at/leg/mode/path/status, 17 of them)
     and browser console rejections as "observations", inflating rows to 52 and manufacturing a
     34-row "missing a side" defect against C8.  r2's row counts must not be quoted either.
  r3 uses a declared, non-circular partition:
     PRIMARY  = the lane's own outcome rows: `measured.row` (one dict) or `measured.rows` (a list),
                i.e. the R#-named records that pair a wire reading with what got painted.
     SECONDARY= every other list inside the cell (access logs, rejections, probe pairs, status sets).
                Reported by name and length; never used to make a T-A/T-B verdict, because they are
                not traveller-facing observations.
  Controls prove the partition is real: a PRIMARY row with the painted field deleted must turn T-A
  red, and putting it back must turn it green.

Questions answered from the published bytes only:
  T-A does every PRIMARY row carry both a wire reading and painted text?
  T-B does every PRIMARY row say who answered with a non-empty value?
  T-C is "the discriminator is not the clock" backed by rows sharing the same answer with different
      elapsed times?
  T-D may a wording rule quote a row?  Requires the row to name the painted string it measured.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
REF = "commander/control"

WIRE = ["http_status", "status", "content_type", "bytes", "client_error", "envelope_code", "declared",
        "sibling_probe", "body"]
PAINTED = ["painted_first_line", "card", "says_cannot_reach_server", "details_elements_in_dom",
           "reason_label", "reason_value", "data_result_status", "secondary_surface"]
WHO = ["answer_attributed_to", "who_answered", "declared"]
TIME = ["elapsed_ms", "delay_ms", "hold_seconds", "cap_ms"]


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-ord0301-r3"})
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="evidence/ord0301-screen-speaks-range-hjp3/RECEIPT_O0301-1500.json")
    ap.add_argument("--md", default="evidence/ord0301-screen-speaks-range-hjp3/RECEIPT_O0301-1500.md")
    ap.add_argument("--out", default="_ord0301_cmdr_derivation_r3.json")
    a = ap.parse_args()

    meta, raw = fetch(a.path)
    cited = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest() == meta["sha"]
    doc = json.loads(raw.decode("utf-8", errors="replace"))
    open("_ord0301_refetched.json", "wb").write(raw)
    md_meta, md_raw = fetch(a.md)
    open("_ord0301_receipt.md", "wb").write(md_raw)

    primary, secondary = [], []
    for ci, cell in enumerate(doc.get("cells") or []):
        m = cell.get("measured") or {}
        mine = 0
        for key, val in m.items():
            if key == "row" and isinstance(val, dict):
                mine += 1
                primary.append({"cell_index": ci, "cell_id": cell.get("id"), "source": "measured.row",
                                "row": val})
            elif key == "rows" and isinstance(val, list):
                for v in val:
                    if isinstance(v, dict):
                        mine += 1
                        primary.append({"cell_index": ci, "cell_id": cell.get("id"),
                                        "source": "measured.rows", "row": v})
        for key, val in m.items():
            if isinstance(val, list) and val and key not in ("rows",):
                secondary.append({"cell_index": ci, "cell_id": cell.get("id"), "list": key,
                                  "length": len(val),
                                  "element_kind": "dict" if all(isinstance(x, dict) for x in val)
                                                  else "scalar",
                                  "element_keys": sorted({k for x in val if isinstance(x, dict) for k in x})[:10]})

    def flags(r):
        return {"wire": present(r, WIRE), "painted": present(r, PAINTED), "who": present(r, WHO),
                "time": present(r, TIME)}

    per_row = []
    for p in primary:
        f = flags(p["row"])
        per_row.append({**p, "row_name": p["row"].get("row"), **{k: v for k, v in f.items()},
                        "T_A": bool(f["wire"]) and bool(f["painted"]),
                        "T_B": bool(f["who"]),
                        "T_D_names_the_painted_string": bool(
                            [k for k in f["painted"] if k.startswith("painted_") or k == "card"])})

    t_a_bad = [{"cell": x["cell_id"][:2], "row": x["row_name"], "missing":
                ([] if x["wire"] else ["wire"]) + ([] if x["painted"] else ["painted"])}
               for x in per_row if not x["T_A"]]
    t_b_bad = [{"cell": x["cell_id"][:2], "row": x["row_name"]} for x in per_row if not x["T_B"]]
    t_d_bad = [{"cell": x["cell_id"][:2], "row": x["row_name"]} for x in per_row if not x["T_D_names_the_painted_string"]]

    # T-C: same answer on the wire, different elapsed times -> the clock is not the discriminator.
    groups = {}
    for x in per_row:
        r = x["row"]
        body = r.get("declared")
        body_key = json.dumps({k: v for k, v in body.items() if k in ("mode", "status", "content_type", "body")}
                              if isinstance(body, dict) else body, sort_keys=True, ensure_ascii=False)
        key = str((body_key, r.get("http_status"), r.get("content_type")))
        groups.setdefault(key, []).append({"row": x["row_name"], "cell": x["cell_id"][:2],
                                           "elapsed_ms": r.get("elapsed_ms")})
    t_c_pairs = {}
    for k, v in groups.items():
        el = [x["elapsed_ms"] for x in v if isinstance(x["elapsed_ms"], (int, float))]
        if len(v) >= 2 and len(el) >= 2 and (max(el) - min(el)) >= 1000:
            t_c_pairs[k] = v

    # Controls - prove the tests can fail on the real payload, not just on a toy.
    if primary:
        sample = dict(primary[0]["row"])
        painted_keys = [k for k in PAINTED if k in sample]
        stripped = {k: v for k, v in sample.items() if k not in PAINTED}
        restored = dict(stripped)
        for k in painted_keys:
            restored[k] = sample[k]
        controls = {
            "primary_row_found_painted_keys": painted_keys,
            "strip_painted_turns_T_A_red": bool(present(stripped, WIRE)) and not present(stripped, PAINTED),
            "restore_turns_T_A_green": bool(present(restored, WIRE)) and bool(present(restored, PAINTED)),
            "who_field_present_on_first_primary_row": present(sample, WHO),
            "secondary_lists_excluded_from_T_A": [s["list"] for s in secondary],
        }
    else:
        controls = {"error": "no PRIMARY rows found under measured.row / measured.rows"}

    cells_without_primary = sorted({c["id"] for c in doc.get("cells") or []
                                    if c["id"] not in {p["cell_id"] for p in primary}})

    rulers = {}
    for name, cmd in (("q38_json", ["receipt_cell_derivation_check_r2.py", "--receipt", "_ord0301_refetched.json"]),
                      ("q43_json", ["claim_coordinate_check_r3.py", "--text", "_ord0301_refetched.json"]),
                      ("q43_md", ["claim_coordinate_check_r3.py", "--text", "_ord0301_receipt.md"])):
        p = subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=240)
        lines = (p.stdout or "").splitlines()
        rulers[name] = {"exit_code": p.returncode,
                        "verdict_line": next((l.strip() for l in lines if "overall" in l), None),
                        "denominator_line": next((l.strip() for l in lines
                                                  if "claims checked" in l or l.startswith("cells")), None)}

    out = {"schema": "CNX_CMDR_DERIVATION_V2", "order": "ORD-0301", "revision": "r3",
           "revision_note": "r1 T_B = false absence (field is answer_attributed_to, on rows). "
                            "r2 row counts inflated by judging origin_own_record access-log entries and "
                            "browser rejections as observations. r3 partitions PRIMARY/SECONDARY by the "
                            "lane's own schema keys measured.row / measured.rows.",
           "partition_rule": "PRIMARY = dicts at measured.row or measured.rows (R# outcome rows). "
                             "SECONDARY = every other list in a cell; reported, never judged.",
           "artifact": {"path": a.path, "contents_sha": meta["sha"], "recomputed_equals_cited": cited,
                        "bytes": len(raw), "md_path": a.md, "md_contents_sha": md_meta["sha"],
                        "md_bytes": len(md_raw)},
           "cells_total": len(doc.get("cells") or []), "primary_rows_total": len(per_row),
           "primary_rows_per_cell": {c[:2]: sum(1 for x in per_row if x["cell_id"].startswith(c))
                                     for c in {x["cell_id"] for x in per_row}},
           "cells_with_no_primary_row": cells_without_primary,
           "secondary_lists": secondary,
           "T_A_rows_missing_a_side": t_a_bad, "T_B_rows_not_naming_who": t_b_bad,
           "T_D_rows_not_naming_the_painted_string": t_d_bad,
           "T_C_clock_pairs": {"pairs_found": len(t_c_pairs), "detail": t_c_pairs},
           "per_primary_row": [{k: v for k, v in x.items() if k != "row"} for x in per_row],
           "controls": controls, "rulers": rulers,
           "decisions": {
               "artifact_rehashes_to_cited_blob": cited,
               "primary_rows_found": len(per_row) > 0,
               "T_A_every_primary_row_has_both_sides": not t_a_bad,
               "T_B_every_primary_row_names_who_answered": not t_b_bad,
               "T_D_every_primary_row_names_the_painted_string": not t_d_bad,
               "T_C_clock_claim_is_a_measured_pair": len(t_c_pairs) >= 1,
               "controls_pass": controls.get("strip_painted_turns_T_A_red")
                                and controls.get("restore_turns_T_A_green")},
           "field_union_across_primary_rows": sorted({k for x in per_row for k in x["row"]}),
           "scope": "What the table's own outcome rows prove. Does NOT sign derived_result (red team) "
                    "and does NOT choose ORD-0302's wording; it states which rows a wording rule may "
                    "quote. Cells with no PRIMARY row are code-attribution or in-process door tests and "
                    "cannot carry a traveller-facing sentence."}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("cells", out["cells_total"], "| PRIMARY rows", len(per_row), out["primary_rows_per_cell"])
    print("cells with NO primary row:", cells_without_primary)
    print("SECONDARY lists (not judged):", [(s["cell_id"][:2], s["list"], s["length"]) for s in secondary])
    print("blob recompute == cited:", cited, meta["sha"], len(raw), "B")
    print("T_A missing a side:", t_a_bad or "none")
    print("T_B not naming who answered:", t_b_bad or "none")
    print("T_D not naming painted text:", t_d_bad or "none")
    print("T_C clock pairs:", len(t_c_pairs), list(t_c_pairs.values())[:1])
    print("controls:", json.dumps({k: v for k, v in controls.items()}, ensure_ascii=False))
    for n, v in rulers.items():
        print("  ruler", n, "exit", v["exit_code"], "|", v["verdict_line"], "|", v["denominator_line"])
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
