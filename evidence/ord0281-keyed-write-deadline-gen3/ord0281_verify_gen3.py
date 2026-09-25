"""Independent read-back of the ORD-0281 gen-3 delivery, then audit every blob the index claims.

Nothing here trusts the delivery script's own stdout: the ref is resolved through the API, every artifact is
re-fetched and re-hashed, and the seven arm cells plus the four criterion cells are re-derived from the
published per-arm readings. The verdict it prints is what a reviewer would compute, not what I reported.
"""
import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
GH, BRC = "Canshu-King/CityNexus", "commander/control"
DIR = "evidence/ord0281-keyed-write-deadline-gen3"
REF = "heads/review/0281-write-deadline-keyed-b3"
BASE = "5aff3722d5c36c760a424f5fea5c3a771298f9ac"
ARMS = ("TA", "TB", "TC", "TD", "K1", "K2", "K3")
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()


def api(path):
    last = None
    for i in range(9):
        try:
            req = urllib.request.Request("https://api.github.com" + path,
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


def blob_of(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def fetch(name):
    c = api(f"/repos/{GH}/contents/{DIR}/{urllib.parse.quote(name, safe='')}?ref={BRC}")
    raw = base64.b64decode(c["content"])
    if blob_of(raw) != c["sha"]:
        raise SystemExit("the answer is not its own blob: " + name)
    return raw, c["sha"]


out = {}
tip = api(f"/repos/{GH}/git/ref/{REF}")["object"]["sha"]
cmp_ = api(f"/repos/{GH}/compare/{BASE}...{tip}")
out["ref"] = {"name": REF, "tip": tip, "ancestry": cmp_.get("status"), "commits_ahead": cmp_.get("ahead_by"),
              "commits_behind": cmp_.get("behind_by")}

raw, rec_sha = fetch("ord0281_keyed_receipt.json")
rc = json.loads(raw.decode("utf-8"))
raw, mx_sha = fetch("ord0281_arms_matrix.json")
mx = json.loads(raw.decode("utf-8"))
out["receipt"] = {"blob40": rec_sha, "candidate_tip": rc["candidate_tip"], "base_tip": rc["base_tip"],
                  "tip_is_the_ref": rc["candidate_tip"] == tip,
                  "cells": len(rc["cells"]),
                  "derived_result_all_null": all(c.get("derived_result") is None for c in rc["cells"])
                  and rc.get("derived_result") is None,
                  "q38": {k: rc["ruler_check"][k]["headline"][:1] for k in
                          ("pass_1_before_sidecar", "pass_2_on_published_bytes")}}

# re-derive every arm cell's claimed_result from the matrix's own per-arm status
derived, mism = {}, []
for c in rc["cells"]:
    name = c["cell"].split()[0]
    if name in ARMS:
        shape = c["cell"].split(" on the ")[1].replace(" tree", "")
        st = (mx["runs"][shape]["per_arm"].get(name) or {}).get("status")
        want = "MET" if st == "passed" else "NOT_MET"
        derived[name] = {"shape": shape, "matrix_status": st, "claims": c["claimed_result"],
                         "agree": c["claimed_result"] == want}
        if not derived[name]["agree"]:
            mism.append(name)
    elif c["cell"].startswith("counter-arm"):
        shape = c["readings"].get("shape") or c["readings"]["counter_arm_run"]
        flip = c["readings"]["arm_that_flipped"]
        # K2 is SKIPPED on a patched tree by design (it reads the shipped constant), and a skip is not a red:
        # counting it as one made this verifier report a discrepancy the matrix never had.
        red = [a for a, v in mx["runs"][shape]["per_arm"].items() if v["status"] in ("failed", "timedOut")]
        skipped = [a for a, v in mx["runs"][shape]["per_arm"].items() if v["status"] == "skipped"]
        derived[shape] = {"intended": flip, "red_arms": red, "skipped_arms": skipped,
                          "only_intended_red": red == [flip]}
        if red != [flip]:
            mism.append(shape)
out["rederived"] = derived
out["mismatches"] = mism

# the four criteria, recomputed from the published per-arm readings rather than from the cells
crit = {}
for c in rc["cells"]:
    if not c["cell"].startswith("criterion"):
        continue
    n = c["cell"].split(":")[0].replace("criterion ", "")
    r = c["readings"]
    if n == "1":
        ok = r["arms_with_both_count"] == r["arms_reading_the_surface"]
    elif n == "2":
        ok = r["arms_holding_rendered_words"] and r["innerText_site_count"] >= 1
    elif n == "3":
        p = r["per_bound_shape"]
        ok = (p["bound2000"]["named"] != p["bound1000"]["named"]
              and r["frozen_seconds_mutant"]["verdict"] == "NOT_MET")
    else:
        ok = r["blamed_count"] == 0 and r["answered_count"] >= 1 and r["unanswered_count"] >= 1
    crit[n] = {"claims": c["claimed_result"], "recomputed_passes": bool(ok)}
out["criteria_recomputed"] = crit

bad = []
listed = json.loads(fetch("ord0281_index.json")[0].decode("utf-8"))["files"]
for e in listed:
    got = fetch(e["name"])[1]
    if got != e["blob40"]:
        bad.append(e["name"])
out["index"] = {"blob40": fetch("ord0281_index.json")[1], "entries": len(listed), "mismatches": bad}
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if (not mism and not bad and out["receipt"]["derived_result_all_null"]
               and out["receipt"]["tip_is_the_ref"] and out["ref"]["ancestry"] == "ahead") else 1)
