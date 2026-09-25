"""Run both arbiter rulers over the ORD-0297r package and publish their verbatim output.

Per the commander's standing note after two mis-readings today: a ruler's verdict is quoted together
with **what it counted** -- the cell count and the judged object's own top-level key names -- because
`Q38_GATE_GREEN` said over a document with no cells at all is not evidence of anything.  The same rule
applies to `claim_coordinate_check_r3`, whose worst honest outcome is
`NO_CLAIM_FOUND / NOT_APPLICABLE`, not "clean".

Both rulers are fetched by 40-hex blob and re-hashed locally (the coordinate ruler is *not* published by
me -- one copy of it exists, on the arbiter's ref path).  Each measured object is frozen as its own
published file, because the receipt gains these gate fields after being measured, so the coordinate
would otherwise name bytes nobody can recover.
"""
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
RECEIPT = "o297r_derived_r1.json"
# stage a measures the receipt as derived; stage b measures it again after stage a's own transcripts were
# appended. A verdict cannot live inside the file it judges without changing that file, so both runs are
# kept and named instead of the second one quietly replacing the first.
STAGE = os.environ.get("O297R_STAGE", "a")
FROZEN = "o297r_measured_object.json" if STAGE == "a" else "o297r_measured_object_b.json"
SFX = "" if STAGE == "a" else "_b"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
R2 = ("receipt_cell_derivation_check_r2.py", "91ae8b1ec55f5c19122af11bf775df14580955e4")
R3 = ("claim_coordinate_check_r3.py", "e653e597c2e6fd74a5f8d3be65fe60e017b03017")
# the order names r3; the arbiter superseded it within the hour with r4 / r4b (r4 returned rc 0 on a
# zero-claim text, r4b exits 4 there) and ruled Q50=1 that machine-generated tables are out of the
# sentence ruler's scope.  Both runs are reported: what I was told to run, and what is current.
R4B = ("claim_coordinate_check_r4b.py", "efa6b7a383e094e2ede89f5dd8565b12feed0171")
Q50 = "issuecomment-5829176662"
TOK = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "hjp1-verifier"}
SUMMARY_RE = re.compile(r"cells (\d+) \| overall (\S+) \| hard (\S+).*?\| soft (\S+)")
CELL_RE = re.compile(r"cell (\S+) \| why_source (\S+) \| why tokens (\d+) \| own hits (\d+) "
                    r"\| unique hits (\d+) \| shares why with (.*)")
Q43_RE = re.compile(r"claims checked (\d+) \| overall (\S+) \| findings (\S+)")
# r4b prints one more field between the count and the verdict, so a single rigid pattern silently
# returns None -- which would look like "the ruler said nothing" rather than "I failed to read it"
Q43B_RE = re.compile(r"claims checked (\d+) \| exempt (\{[^|]*\}) \| overall (\S+) \| findings (\S+)")


def q43_summary(text):
    m = Q43B_RE.search(text or "")
    if m:
        return {"claims_checked": int(m.group(1)), "exempt": m.group(2), "overall": m.group(3),
                "findings": m.group(4)}
    m = Q43_RE.search(text or "")
    if m:
        return {"claims_checked": int(m.group(1)), "overall": m.group(2), "findings": m.group(3)}
    return None


def sha1b(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def blob(sha):
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha,
                                 headers=H)
    with urllib.request.urlopen(req, timeout=120) as f:
        m = json.load(f)
    return base64.b64decode(m["content"]) if m.get("encoding") == "base64" else b"", m


def top_level_keys(path):
    d = json.load(io.open(path, encoding="utf-8"))
    return (sorted(d.keys()), len(d), (d.get("cells") or {}) if isinstance(d.get("cells"), dict)
            else (d.get("cells") or []))


def run(cmd, tag):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return r


out = {"receipt_measured": {"file": RECEIPT, "bytes": os.path.getsize(os.path.join(LANE, RECEIPT)),
                            "blob40": sha1b(io.open(os.path.join(LANE, RECEIPT), "rb").read())},
       "measured_object_frozen_as": FROZEN, "stage": STAGE}
io.open(os.path.join(LANE, FROZEN), "wb").write(
    io.open(os.path.join(LANE, RECEIPT), "rb").read())

# ---- Q38 cell-derivation ruler, over the frozen copy
for script, sha in (R2,):
    raw, meta = blob(sha)
    io.open(os.path.join(LANE, script), "wb").write(raw)
    st = run([sys.executable, os.path.join(LANE, script), "--selftest"], "selftest")
    rr = run([sys.executable, os.path.join(LANE, script), "--receipt", FROZEN], "r2")
    io.open(os.path.join(LANE, "gate_r2_on_receipt%s.txt" % SFX), "w", encoding="utf-8", newline="").write(rr.stdout)
    parsed = {"cells_found": None, "overall": None, "hard": None, "soft": None, "cells": []}
    for ln in rr.stdout.splitlines():
        m = SUMMARY_RE.search(ln)
        if m:
            parsed.update({"cells_found": int(m.group(1)), "overall": m.group(2),
                           "hard": m.group(3), "soft": m.group(4)})
        c = CELL_RE.search(ln)
        if c:
            parsed["cells"].append({"cell": c.group(1), "why_tokens": int(c.group(3)),
                                    "own_hits": int(c.group(4)), "unique_hits": int(c.group(5)),
                                    "shares_why_with": c.group(6).strip()})
    keys, nkeys, cellsobj = top_level_keys(os.path.join(LANE, FROZEN))
    out["q38_r2"] = {"script": script, "blob40": sha, "local_sha1_matches_blob_id": sha1b(raw) == sha,
                     "blob_meta_size": meta.get("size"), "selftest_rc": st.returncode,
                     "selftest_tail": " ".join((st.stdout or "").split())[-70:],
                     "rc": rr.returncode, "parsed": parsed,
                     "judged_object_top_level_keys": keys, "judged_object_top_level_key_count": nkeys,
                     "cells_in_judged_object": sorted(cellsobj) if isinstance(cellsobj, dict) else len(cellsobj),
                     "verbatim": rr.stdout, "stderr_head": (rr.stderr or "")[:200]}
    print("Q38 r2:", parsed["overall"], "cells", parsed["cells_found"], "rc", rr.returncode,
          "| judged object has", nkeys, "top-level keys and",
          len(cellsobj) if hasattr(cellsobj, "__len__") else "?", "cells inside", flush=True)

# ---- Q43 coordinate ruler, over the receipt AND the block I am about to publish
led_rows = io.open(LEDGER, encoding="utf-8", newline="").read().split("\n")
i0 = [n for n, l in enumerate(led_rows) if l.startswith("### 1a986a24 HJ-P1 · ORD-0297r")]
if i0:
    # my block ends at the next heading, not at a fixed line count: taking 200 lines made the gauge judge
    # the following lanes' text and call the result my block's verdict
    j = i0[0] + 1
    while j < len(led_rows) and not led_rows[j].startswith(("### ", "## ")):
        j += 1
    block = "\n".join(led_rows[i0[0]:j])
    # newline="" so the extracted copy is the same BYTES as what sits in the ledger: without it Python
    # flips LF to CRLF on Windows and the gauge would then have measured a different file
    io.open(os.path.join(LANE, "o297r_ledger_block_for_q43.txt"), "w", encoding="utf-8",
            newline="").write(block)
    block_lines = j - i0[0]
else:
    block, block_lines = "", 0
for target in (FROZEN, "o297r_ledger_block_for_q43.txt"):
    if not os.path.exists(os.path.join(LANE, target)):
        out.setdefault("q43_r3", {})[target] = "absent (block not inserted yet)"
        continue
    raw, meta = blob(R3[1])
    io.open(os.path.join(LANE, R3[0]), "wb").write(raw)
    # this ruler's own CLI takes one input flag, --text, for every kind of body (its help: "a ledger
    # block, a bus post, a receipt body"); passing --receipt makes argparse exit 2 with an empty stdout,
    # which is exactly the "no output, looks like a pass" shape I must not ship
    args = ["--text", target]
    rr = run([sys.executable, os.path.join(LANE, R3[0])] + args, "r3")
    st = run([sys.executable, os.path.join(LANE, R3[0]), "--selftest"], "r3st")
    io.open(os.path.join(LANE, "gate_r3_on_" + ("receipt" if target.endswith(".json") else "block") + SFX + ".txt"),
            "w", encoding="utf-8", newline="").write(rr.stdout)
    summ = q43_summary(rr.stdout)
    out.setdefault("q43_r3", {})[target] = {
        "blob40": R3[1], "local_sha1_matches_blob_id": sha1b(raw) == R3[1],
        "selftest_rc": st.returncode, "selftest_tail": " ".join((st.stdout or "").split())[-60:],
        "rc": rr.returncode, "summary": summ,
        "verbatim": rr.stdout, "stderr_head": (rr.stderr or "")[:200]}
    print("Q43 r3 on", target, ":", (out["q43_r3"][target]["summary"] or {}).get("overall"),
          "claims checked", (out["q43_r3"][target]["summary"] or {}).get("claims_checked"),
          "rc", rr.returncode, flush=True)

# ---- Q43 r4b, the successor the arbiter shipped after this order was written -----------------
raw4, meta4 = blob(R4B[1])
io.open(os.path.join(LANE, R4B[0]), "wb").write(raw4)
st4 = run([sys.executable, os.path.join(LANE, R4B[0]), "--selftest"], "r4bst")
for target in (FROZEN, "o297r_ledger_block_for_q43.txt"):
    if not os.path.exists(os.path.join(LANE, target)):
        out.setdefault("q43_r4b", {})[target] = "absent (block not inserted yet)"
        continue
    rr = run([sys.executable, os.path.join(LANE, R4B[0]), "--text", target], "r4b")
    io.open(os.path.join(LANE, "gate_r4b_on_" + ("receipt" if target.endswith(".json") else "block") + SFX + ".txt"),
            "w", encoding="utf-8", newline="").write(rr.stdout)
    summ = q43_summary(rr.stdout)
    out.setdefault("q43_r4b", {})[target] = {
        "blob40": R4B[1], "bytes_fetched": len(raw4), "local_sha1_matches_blob_id": sha1b(raw4) == R4B[1],
        "selftest_rc": st4.returncode, "selftest_tail": " ".join((st4.stdout or "").split())[-70:],
        "rc": rr.returncode, "summary": summ,
        "q50_ruling": ("machine-generated tables are RULER_OUT_OF_SCOPE for this gauge, per %s" % Q50)
        if target.endswith(".json") else None,
        "verbatim": rr.stdout, "stderr_head": (rr.stderr or "")[:200]}
    print("Q43 r4b on", target, ":", (out["q43_r4b"][target].get("summary") or {}).get("overall"),
          "claims checked", (out["q43_r4b"][target].get("summary") or {}).get("claims_checked"),
          "rc", rr.returncode, flush=True)

json.dump(out, io.open(os.path.join(LANE, "o297r_gate%s.json" % ("_b" if SFX else "")), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
rec = json.load(io.open(os.path.join(LANE, RECEIPT), encoding="utf-8"))
rec["gate_q38_r2_" + STAGE] = {k: v for k, v in out["q38_r2"].items() if k != "verbatim"}
rec["gate_q38_r2_verbatim_" + STAGE] = out["q38_r2"]["verbatim"]
rec["gate_q43_r3_" + STAGE] = {k: {kk: vv for kk, vv in v.items() if kk != "verbatim"} if isinstance(v, dict) else v
                      for k, v in (out.get("q43_r3") or {}).items()}
rec["gate_measured_object"] = {"file": FROZEN,
                               "blob40": out["receipt_measured"]["blob40"],
                               "note": "the bytes both rulers ran over, frozen as its own published file; "
                                       "this receipt gained gate fields afterwards so it no longer hashes "
                                       "to that value"}
io.open(os.path.join(LANE, RECEIPT), "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
print(json.dumps({"measured_object_sha1": out["receipt_measured"]["blob40"],
                  "r2_overall": out["q38_r2"]["parsed"]["overall"],
                  "r2_cells": out["q38_r2"]["parsed"]["cells_found"],
                  "q43_targets": list((out.get("q43_r3") or {}).keys())}, ensure_ascii=False))
assert out["q38_r2"]["parsed"]["overall"] == "Q38_GATE_GREEN" and out["q38_r2"]["rc"] == 0 \
    and out["q38_r2"]["selftest_rc"] == 0 and out["q38_r2"]["local_sha1_matches_blob_id"]
assert out["q38_r2"]["parsed"]["cells_found"] == len(rec["cells"]), \
    "the ruler counted a different number of cells than the receipt has"
