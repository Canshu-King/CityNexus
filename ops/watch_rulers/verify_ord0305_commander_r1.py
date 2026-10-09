"""Commander's first-hand check of lane E's ORD-0305 verifier derivation, and of the one limit E
declared ("I can derive that the target arm flipped, but not that ONLY it flipped").

The point of this script: E's limit is closable from B's own published bytes, and I would rather
say so with a computation than ask for another run.  B's `ord0281_arms_matrix.json` carries, per
counter-arm, an `outcomes` map over all seven arms.  Exclusivity = the failed set of a counter-arm
run equals exactly the arm that counter-arm names, and everything else keeps its baseline outcome.
"""
import base64
import hashlib
import io
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "cmdr-ord0305-verify"}
REPO = "Canshu-King/CityNexus"
REF = urllib.parse.quote("commander/control", safe="")


def get(path):
    for k in range(5):
        try:
            req = urllib.request.Request("https://api.github.com" + path)
            for a, b in H.items():
                req.add_header(a, b)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            time.sleep(2 * (k + 1))
    raise SystemExit("GET " + path + " failed")


def blob(sha):
    return base64.b64decode(get("/repos/" + REPO + "/git/blobs/" + sha)["content"])


def sha1(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


E_PATH = "evidence/ord0305-write-deadline-keyed/verifier_derivation_d2305848.json"
E_SHA = "16bfbf78cda8c7fefd0553fcd98de12045ea2c7e"
# Paths below were read from the branch listing, not guessed: lane B has since re-cut a second
# generation, so the matrix the delivery post cited (f51894dc) now lives under a
# `previous_generation__` name while the live one is 911ec748.
M_PATH = "evidence/ord0281-keyed-write-deadline-gen2/ord0281_arms_matrix.json"
M_SHA = "911ec7483c88ad43e3eae673e2a956a43aef89ec"
M1_PATH = "evidence/ord0281-keyed-write-deadline-gen2/previous_generation__ord0281_arms_matrix.json"
M1_SHA = "f51894dc6559cce14013a461c982a5f7da54dd8c"

emeta = get("/repos/" + REPO + "/contents/" + E_PATH + "?ref=" + REF)
eraw = blob(E_SHA)
ev = json.loads(eraw.decode("utf-8", "replace"))

# --- 1. what did the verifier actually sign, cell by cell? -------------------------------
cells = ev.get("cell_by_cell_derived_result")
shape = {"type": type(cells).__name__, "count": (len(cells) if hasattr(cells, "__len__") else None)}
values = {}
if isinstance(cells, dict):
    for k, v in cells.items():
        values[k] = (v.get("derived_result") if isinstance(v, dict) else v)
elif isinstance(cells, list):
    for v in cells:
        if isinstance(v, dict):
            values[str(v.get("cell") or v.get("id") or v.get("arm"))] = v.get("derived_result")
lit_pass = sum(1 for v in values.values() if str(v).strip().upper() in ("PASS", "TRUE", "OK"))
banned_literal = lit_pass > 0  # "PASS" as a literal is not a derivation

# --- 2. close E's declared limit from B's own matrix --------------------------------------
mmeta = get("/repos/" + REPO + "/contents/" + M_PATH + "?ref=" + REF)
mraw = blob(M_SHA)
mx = json.loads(mraw.decode("utf-8", "replace"))


def exclusivity(mx):
    """Derive per-run independence from the delivery lane's OWN (status, expectation) pairs.

    `runs` carries every configuration the lane executed: `pristine` (nothing mutated) plus the three
    counter-arms.  A counter-arm is independent when exactly one arm deviates from its own expectation
    and the pristine run has none - which is what "only the target went red" means in bytes.
    """
    runs = mx.get("runs") or {}
    rows = []
    for name, blk in runs.items():
        per = (blk or {}).get("per_arm") or {}
        flipped = sorted(k for k, v in per.items()
                         if isinstance(v, dict) and v.get("status") != v.get("expectation"))
        rows.append({"run": name, "arms": len(per), "flipped_vs_own_expectation": flipped,
                     "rc": (blk or {}).get("rc")})
    pristine = [r for r in rows if r["run"] == "pristine"]
    counter = [r for r in rows if r["run"].startswith("ca_")]
    ok_pristine = bool(pristine) and pristine[0]["flipped_vs_own_expectation"] == []
    ok_counter = bool(counter) and all(len(r["flipped_vs_own_expectation"]) == 1 for r in counter)
    distinct = len({tuple(r["flipped_vs_own_expectation"]) for r in counter}) == len(counter)
    return rows, {"pristine_flipped_nothing": ok_pristine,
                  "each_counter_arm_flips_exactly_one": ok_counter,
                  "the_flipped_arms_are_all_different": distinct,
                  "all_exclusive": bool(ok_pristine and ok_counter and distinct)}


rows2, sum2 = exclusivity(mx)

m1raw = blob(M1_SHA)
mx1 = json.loads(m1raw.decode("utf-8", "replace"))
rows1, sum1 = exclusivity(mx1)
gen2 = {"base_tip": mx.get("base_tip"), "spec": mx.get("spec"), "verdict": mx.get("verdict")}
gen1 = {"base_tip": mx1.get("base_tip"), "spec": mx1.get("spec"), "verdict": mx1.get("verdict")}

# --- 3. the ruler, on the verifier's own file --------------------------------------------
rulers = {}
open("_ord0305_verifier_raw.json", "wb").write(eraw)
p = subprocess.run([sys.executable, "receipt_cell_derivation_check_r2.py", "--receipt", "_ord0305_verifier_raw.json"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
rulers["q38"] = {"exit": p.returncode,
                 "line": next((l.strip() for l in (p.stdout or "").splitlines()
                               if "overall" in l or "cells" in l), None),
                 "first_lines": (p.stdout or "").splitlines()[:3]}

m1meta = get("/repos/" + REPO + "/contents/" + M1_PATH + "?ref=" + REF)
out = {
    "schema": "CNX_CMDR_ACCEPTANCE_CHECK_V1", "order": "ORD-0305", "lane": "d2305848 (red team / verifier)",
    "artifacts": {
        "verifier_derivation": {"path": E_PATH, "contents_sha": emeta["sha"], "cited": E_SHA,
                                "recomputed": sha1(eraw), "matches": sha1(eraw) == E_SHA, "bytes": len(eraw)},
        "gen2_arms_matrix": {"path": M_PATH, "contents_sha": mmeta["sha"], "cited": M_SHA,
                             "recomputed": sha1(mraw), "matches": sha1(mraw) == M_SHA, "bytes": len(mraw)},
        "gen1_arms_matrix_renamed": {"path": M1_PATH, "contents_sha": m1meta["sha"], "cited": M1_SHA,
                                     "recomputed": sha1(m1raw), "matches": sha1(m1raw) == M1_SHA,
                                     "bytes": len(m1raw)}},
        "generation_shapes": {"gen2": gen2, "gen1": gen1},
    "verifier_cells": {"shape": shape, "derived_results": values,
                       "any_literal_PASS_instead_of_derivation": banned_literal},
    "limit_E_declared": "cannot independently verify that ONLY the target arm went red",
    "limit_closed_from_delivery_lane_bytes": {
        "gen2": {"runs": rows2, "summary": sum2},
        "gen1": {"runs": rows1, "summary": sum1},
        "meaning": ("the published matrices carry an outcomes map over all seven arms per counter-arm run, "
                    "so exclusivity IS computable from the delivery lane's own bytes"
                    if (rows2 or rows1) else "no runs map found - cannot close this way")},
    "rulers": rulers,
    "scope": "Commander's own reading of the verifier artifact + both generations of the delivery's matrix. "
             "It does not re-sign E's derived_result, does not replace the red team, and is NOT a landing: "
             "landing happens ff-only by me after the candidate's parent equals the tip I re-read at that "
             "moment."}
json.dump(out, io.open("_ord0305_cmdr_acceptance_check_r1.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("rehash: verifier", out["artifacts"]["verifier_derivation"]["matches"],
      "| gen2 matrix", out["artifacts"]["gen2_arms_matrix"]["matches"],
      "| gen1 matrix", out["artifacts"]["gen1_arms_matrix_renamed"]["matches"])
print("gen2 shape:", json.dumps(gen2, ensure_ascii=False)[:200])
print("gen1 shape:", json.dumps(gen1, ensure_ascii=False)[:200])
print("verifier cells:", shape, "| literal-PASS present:", banned_literal)
print("derived results:", json.dumps(values, ensure_ascii=False)[:400])
print("GEN2 runs (base_tip %s):" % str(gen2["base_tip"])[:12])
for r in rows2:
    print("  ", r["run"], "arms", r["arms"], "flipped", r["flipped_vs_own_expectation"], "rc", r["rc"])
print("GEN2 summary:", json.dumps(sum2))
print("GEN1 runs (base_tip %s):" % str(gen1["base_tip"])[:12])
for r in rows1:
    print("  ", r["run"], "arms", r["arms"], "flipped", r["flipped_vs_own_expectation"], "rc", r["rc"])
print("GEN1 summary:", json.dumps(sum1))
print("q38 on the verifier file:", rulers["q38"])
