"""Record the two arbiter rulers I ran, without publishing a second copy of anybody's ruler.

Why this exists: the acceptance says "交前自跑两把尺 ... 并把原样输出一起发".  The verbatim outputs go
out as their own files; the ruler *code* stays a single copy on the arbiter's ref path, addressed by its
40-hex blob id.  So this file proves which bytes I actually executed: fetched by blob id over HTTPS,
re-hashed locally with the git blob framing, and required to match the coordinate in the order.
If the bytes had differed, the ruler I ran would not be the ruler the arbiter signed -- that is the only
thing this record can falsify, and it fails loudly rather than quietly.
"""
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
RULERS = [("receipt_cell_derivation_check_r2.py", "91ae8b1ec55f5c19122af11bf775df14580955e4", "Q38 cell-derivation"),
          ("claim_coordinate_check_r3.py", "e653e597c2e6fd74a5f8d3be65fe60e017b03017", "Q43 claim-coordinate"),
          ("claim_coordinate_check_r4b.py", "efa6b7a383e094e2ede89f5dd8565b12feed0171",
           "Q43 claim-coordinate, the successor the arbiter shipped after this order was written")]
gate = json.load(io.open(os.path.join(LANE, "o297r_gate.json"), encoding="utf-8"))


def sha1b(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


out = {"policy": "the ruler itself is not duplicated into this package; it is addressed by blob id on the "
                 "arbiter's ref path, and the copy executed here was fetched by that id and re-hashed",
       "rulers": []}
for fn, sha, what in RULERS:
    p = os.path.join(LANE, fn)
    row = {"script": fn, "what_it_judges": what, "expected_blob40": sha, "present_locally": os.path.exists(p)}
    if row["present_locally"]:
        raw = open(p, "rb").read()
        row["bytes"] = len(raw)
        row["local_sha1_matches_expected"] = sha1b(raw) == sha
    g = (gate.get("q38_r2") if "r2" in fn else None)
    if g:
        row["selftest_rc"] = g.get("selftest_rc")
        row["selftest_tail"] = g.get("selftest_tail")
        row["judged_object"] = "o297r_measured_object.json"
        row["cells_counted_by_ruler"] = (g.get("parsed") or {}).get("cells_found")
        row["overall"] = (g.get("parsed") or {}).get("overall")
        row["hard"] = (g.get("parsed") or {}).get("hard")
        row["soft"] = (g.get("parsed") or {}).get("soft")
        row["judged_object_top_level_key_count"] = g.get("judged_object_top_level_key_count")
        row["judged_object_top_level_keys"] = g.get("judged_object_top_level_keys")
        row["verbatim_output_file"] = "gate_r2_on_receipt.txt"
    else:
        sect = "q43_r4b" if "r4b" in fn else "q43_r3"
        tag = "r4b" if "r4b" in fn else "r3"
        t = (gate.get(sect) or {}).get("o297r_measured_object.json")
        if t:
            row["selftest_rc"] = t.get("selftest_rc")
            row["selftest_tail"] = t.get("selftest_tail")
            row["judged_object"] = "o297r_measured_object.json"
            row["summary"] = t.get("summary")
            row["verbatim_output_file"] = "gate_%s_on_receipt.txt" % tag
            row["q50_scope_note"] = t.get("q50_ruling")
        b = (gate.get(sect) or {}).get("o297r_ledger_block_for_q43.txt")
        if isinstance(b, dict):
            row["ledger_block_summary"] = b.get("summary")
            row["ledger_block_verbatim_output_file"] = "gate_%s_on_block.txt" % tag
        elif b:
            row["ledger_block_summary"] = str(b)
        # running this prose gauge over the JSON receipt grades timestamps, ports and character counts as
        # bare numeric claims.  The arbiter settled that question rather than me: Q50=1 rules the
        # machine-generated table face RULER_OUT_OF_SCOPE for the sentence gauge
        # (issuecomment-5829176662, relayed by the commander, so COMMANDER_RELAYED).  The run is kept as
        # it printed; only the scope label comes from the ruling.
        if isinstance(t, dict):
            row["on_json_receipt"] = {"rc": t.get("rc"), "summary": t.get("summary"),
                                      "scope": "RULER_OUT_OF_SCOPE per Q50=1 (issuecomment-5829176662, "
                                               "COMMANDER_RELAYED) -- a number inside a machine-generated "
                                               "table is not prose written for a human",
                                      "verbatim_output_file": "gate_%s_on_receipt.txt" % tag}
    out["rulers"].append(row)
io.open(os.path.join(LANE, "o297r_ruler_copies.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
assert all(r.get("local_sha1_matches_expected") for r in out["rulers"]), \
    "a ruler ran whose bytes were not the blob the order named"
