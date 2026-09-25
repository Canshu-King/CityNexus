"""Independent read-back of the ORD-0302 delivery: resolve the coordinates off this machine, not from memory.

Everything here is an HTTP read against the GitHub API with the account token -- no local git object is
trusted, and no verdict is copied from the delivery script's own stdout. It answers three questions:
  1) does the candidate ref exist, and what are its parents?
  2) do the two files at that ref match the blobs the receipt names?
  3) does the published receipt self-derive: every cell's claimed_result recomputed from that run's own
     per-arm artifact, and derived_result null everywhere?
"""
import base64
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()
GH = "Canshu-King/CityNexus"
REF = "heads/review/0302-unreadable-server-body-b"
BASE = "dc964086c9d412573ac19d70b24b30e6c3ee6168"
DIR = "evidence/ord0302-unreadable-server-body"
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
ARMS = ("N1", "N2", "N3", "X1", "X2")


def api(path):
    # this link truncates and blips; a read that fails is retried, never guessed around
    import time
    last = None
    for i in range(8):
        try:
            req = urllib.request.Request("https://api.github.com/" + path.lstrip("/"),
                                         headers={"Authorization": "Bearer " + tok,
                                                  "Accept": "application/vnd.github+json",
                                                  "User-Agent": "citynexus-lane-B-verify"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(2 + 3 * i)
    raise last


def blob_of(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


out = {}
ref = api(f"/repos/{GH}/git/ref/" + urllib.parse.quote(REF, safe=""))
cmp = api(f"/repos/{GH}/compare/{BASE}...{ref['object']['sha']}")
tip = ref["object"]["sha"]
commit = api(f"/repos/{GH}/git/commits/{tip}")
out["ref"] = {"name": REF, "tip": tip, "parents": [p["sha"] for p in commit["parents"]],
              "ancestry_via_compare": cmp.get("status"), "commits_ahead": cmp.get("ahead_by"),
              "commits_behind": cmp.get("behind_by"),
              # `ahead` from the compare endpoint is what "strictly on top of the order's tip" means here;
              # the ref's own parent is the earlier commit of this same candidate, not the base.
              "on_top_of_base_only": cmp.get("status") == "ahead"}

FILES = {"frontend/src/features/planning/PlanWithAiSheet.tsx": "candidate_sheet.tsx",
         "frontend/e2e/qoder-ord0302-unreadable-server-body.spec.ts": "candidate_spec.ts"}
out["at_ref"] = {}
for repo_path, evidence_name in FILES.items():
    c = api(f"/repos/{GH}/contents/{urllib.parse.quote(repo_path, safe='')}?ref={tip}")
    data = base64.b64decode(c["content"])
    out["at_ref"][repo_path] = {"blob40": blob_of(data), "bytes": len(data),
                                "api_sha_agrees": c["sha"] == blob_of(data)}
    ev = api(f"/repos/{GH}/contents/{DIR}/{evidence_name}?ref=commander/control")
    ev_data = base64.b64decode(ev["content"])
    out["at_ref"][repo_path]["evidence_copy_identical"] = blob_of(ev_data) == blob_of(data)

receipt = api(f"/repos/{GH}/contents/{DIR}/ord0302_receipt.json?ref=commander/control")
rec = json.loads(base64.b64decode(receipt["content"]).decode("utf-8"))
out["receipt"] = {"blob40": blob_of(base64.b64decode(receipt["content"])),
                  "cells": len(rec["cells"]),
                  "candidate_tip_in_receipt": rec.get("candidate_tip"),
                  "derived_result_all_null": all(c.get("derived_result") is None for c in rec["cells"]),
                  "every_cell_has_readings": all(c.get("readings") for c in rec["cells"])}

# Recompute the five arm cells from the per-arm artifacts the branch carries, not from the receipt's prose.
mat = api(f"/repos/{GH}/contents/{DIR}/ord0302_arms_matrix.json?ref=commander/control")
matrix = json.loads(base64.b64decode(mat["content"]).decode("utf-8"))
recomputed, mismatches = {}, []
for arm_cell in [c for c in rec["cells"] if c["cell"].startswith(ARMS)]:
    arm = arm_cell["cell"].split()[0]
    if arm not in matrix["runs"]["fixed"].get("per_arm", {}):
        mismatches.append(arm + ": not in the matrix")
        continue
    status = matrix["runs"]["fixed"]["per_arm"][arm]["status"]
    want = "MET" if status == "passed" else "NOT_MET"
    recomputed[arm] = {"matrix_status": status, "receipt_claims": arm_cell["claimed_result"],
                       "agree": arm_cell["claimed_result"] == want}
    if not recomputed[arm]["agree"]:
        mismatches.append(arm)
out["arms_recomputed"] = recomputed
out["mismatches"] = mismatches
for shape in [s for s in matrix["runs"] if s != "fixed"]:
    flip = matrix["runs"][shape]["intended"]
    got = {a: matrix["runs"][shape]["per_arm"][a]["status"] for a in ARMS}
    only = [a for a, v in got.items() if v != "passed"]
    out.setdefault("counter_arms", {})[shape] = {"intended": flip, "red": only,
                                                 "independent": only == [flip],
                                                 "meets_expectation": matrix["runs"][shape]["meets_expectation"]}

gate = api(f"/repos/{GH}/contents/{DIR}/ord0302_claim_gate.json?ref=commander/control")
gv = json.loads(base64.b64decode(gate["content"]).decode("utf-8"))
out["claim_gate"] = {"bus": {k: v["rc"] for k, v in gv["bus_body"].items()},
                     "ledger": {k: v["rc"] for k, v in gv["ledger_block"].items()},
                     "bus_comment_id": gv.get("bus_comment_id")}
idx = api(f"/repos/{GH}/contents/{DIR}/ord0302_index.json?ref=commander/control")
iv = json.loads(base64.b64decode(idx["content"]).decode("utf-8"))
out["index"] = {"listed": len(iv["files"]), "names_itself": any(f["name"] == "ord0302_index.json"
                                                                for f in iv["files"]),
                "blob40": blob_of(base64.b64decode(idx["content"]))}

print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if (not mismatches and out["index"]["names_itself"] is False
               and out["receipt"]["derived_result_all_null"]
               and all(v["independent"] for v in out["counter_arms"].values())
               and out["ref"]["tip"] == rec["candidate_tip"]
               and out["ref"]["on_top_of_base_only"]) else 1)
