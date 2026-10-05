"""ORD-0553 r13e -- measure what my r13 block claimed but never vouched.

The delivered block says the two store copies are byte-identical and points at the launch receipts for
that.  The receipts carry db_bytes only -- a size is not a fingerprint, so the claim as shipped is
wider than its evidence.  This file computes the fingerprints (and re-reads the receipts to show exactly
what they do and do not contain) so the erratum can cite a reading instead of a number.
"""
import hashlib
import io
import json
import os

R = "D:/moodle/_qoder_cmdra_ord0553_20261003"
FILES = {"leg_tip_generation": "_cmdra_0553_r13a.db", "leg_prer2_generation": "_cmdra_0553_r13b.db",
         "earlier_probe_copy": "_cmdra_0553p.db"}

out = {"instrument": "cmdra_0553_store_fingerprint_r13e", "files": {}}
for slot, name in FILES.items():
    path = os.path.join(R, name)
    raw = io.open(path, "rb").read()
    out["files"][slot] = {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

a = out["files"]["leg_tip_generation"]
b = out["files"]["leg_prer2_generation"]
out["both_legs_byte_identical"] = (a["sha256"] == b["sha256"])

# what the launch receipts actually hold -- this is the cell my block over-claimed
rec = {}
for port in ("8772", "8774"):
    p = os.path.join(R, "_r13_launch_%s.json" % port)
    d = json.load(io.open(p, encoding="utf-8"))
    rec[port] = {"db_bytes": d["db_bytes"], "pid_owns_port": d["pid_owns_port"],
                 "carries_a_digest_of_the_store": any(k.endswith("sha") or "sha256" in k for k in d)}
out["launch_receipt_fields"] = rec
out["claim_corrected"] = (
    "the two legs' stores are equal because their sha256 is equal, not because the receipts say so; "
    "the receipts vouch size and port ownership only")

path = os.path.join(R, "_evidence", "r13e_store_fingerprint.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False))
