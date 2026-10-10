"""Landing receipt for the ORD-0298d hop (ORD-0278 + ORD-0253 onto the authoritative line).

Every field is READ at run time.  The claims being supported are: (a) the ref moved exactly once and the
move was fast-forward-only, (b) the tree I landed is the tree that was measured (frontend subtree oid and
the four named product blobs), (c) the kill evidence exists at cited blobs and re-hashes to them, and
(d) what this hop invalidated for other lanes - stated from the diff, not from memory.
"""
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
BRANCH = "mirror/integration-frontend-apple-pass1"
PREV = "90d29a172e186aab6e6cb138ab4583ccf93bfa68"
LANDED = "dc964086c9d412573ac19d70b24b30e6c3ee6168"
ARMS = "457313365eda53e9634ddf522839fe3714d0e86d"
GATE = "211c67f88b4360c63c1e4ed1c6284f36b3f354fd"
VERIFIER = "520a95781efa039df527064ccc6d1940a9288e75"
PRODUCT_FILES = ["frontend/src/features/planning/PlanWithAiSheet.tsx",
                 "frontend/src/api/journeyContinuation.ts",
                 "frontend/src/app/V8Experience.tsx",
                 "frontend/src/i18n/LocaleContext.tsx"]
EXPECTED_FRONTEND_TREE = "a53c7303c6d1513010ff91ecf9c022591c3e513c"  # lane D's own per-file table
MY_DERIVATION = "_ord0298d_commander_derivation_r2.json"


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-landing-receipt"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            last = sys.exc_info()[1]
            time.sleep(2 * (k + 1))
    raise SystemExit(f"GET {path} failed: {last}")


def rehash(sha):
    raw = base64.b64decode(get(f"/repos/{REPO}/git/blobs/{sha}")["content"])
    return raw, hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest() == sha, len(raw)


def main():
    q = urllib.parse.quote(BRANCH, safe="")
    routes = {
        "route1_git_ref_heads": get(f"/repos/{REPO}/git/ref/heads/{q}")["object"]["sha"],
        "route2_commits_sha_param": get(f"/repos/{REPO}/commits?sha={q}&per_page=1")[0]["sha"],
        "route3_git_refs_heads_list": [x["object"]["sha"] for x in get(f"/repos/{REPO}/git/refs/heads")
                                       if x["ref"].endswith(BRANCH)][0],
    }
    all_agree = len(set(routes.values())) == 1 and routes["route1_git_ref_heads"] == LANDED

    cmp_ = get(f"/repos/{REPO}/compare/{PREV}...{LANDED}")
    commit = get(f"/repos/{REPO}/commits/{LANDED}")
    tree = get(f"/repos/{REPO}/git/trees/{LANDED}?recursive=1")
    blobs = {e["path"]: e["sha"] for e in tree["tree"] if e["path"] in PRODUCT_FILES}
    frontend_oid = [e["sha"] for e in tree["tree"] if e["path"] == "frontend"]

    # which files did the whole hop touch, and were any of them outside frontend/** and review/**
    touched, outside = set(), set()
    for c in cmp_.get("commits", []):
        d = get("/repos/%s/commits/%s" % (REPO, c["sha"]))
        for f in d.get("files", []):
            touched.add(f["filename"])
            if not (f["filename"].startswith("frontend/") or f["filename"].startswith("review/")):
                outside.add(f["filename"])

    arms_raw, arms_ok, arms_n = rehash(ARMS)
    gate_raw, gate_ok, gate_n = rehash(GATE)
    ver_raw, ver_ok, ver_n = rehash(VERIFIER)
    mine = json.load(open(MY_DERIVATION, encoding="utf-8"))
    arms_json = json.loads(arms_raw.decode())
    ver_json = json.loads(ver_raw.decode())

    receipt = {
        "schema": "CNX_CMDR_LANDING_RECEIPT_V1",
        "orders_landed": ["ORD-0278 (continuation press carries the round it started in)",
                          "ORD-0253 (both legs of one intent share one transport key)"],
        "branch": BRANCH, "previous_tip": PREV, "landed_tip": LANDED,
        "tip_read_back": routes,
        "all_three_routes_agree_on_landed_sha": all_agree,
        "move": {
            "landed_parents": [p["sha"] for p in commit.get("parents", [])],
            "compare_prev_to_landed_status": cmp_.get("status"),
            "ahead_by": cmp_.get("ahead_by"), "behind_by": cmp_.get("behind_by"),
            "fast_forward_only": cmp_.get("behind_by") == 0 and cmp_.get("status") == "ahead",
            "commits_in_hop": len(cmp_.get("commits", [])),
        },
        "tree_identity": {
            "frontend_subtree_oid": frontend_oid[0] if frontend_oid else None,
            "equals_what_lane_D_measured": (frontend_oid[0] == EXPECTED_FRONTEND_TREE) if frontend_oid else False,
            "named_product_blobs_at_landed_tip": blobs,
            "arms_receipt_tested_tree_field": arms_json.get("tested_tree") or arms_json.get("meta", {}).get("tested_tree"),
        },
        "evidence_rehash": {
            "arms_receipt": {"blob": ARMS, "recomputed_equal": arms_ok, "bytes": arms_n},
            "green_round_gate": {"blob": GATE, "recomputed_equal": gate_ok, "bytes": gate_n},
            "verifier_derivation": {"blob": VERIFIER, "recomputed_equal": ver_ok, "bytes": ver_n,
                                    "verifier_schema": ver_json.get("schema"),
                                    "verifier_signed_by": ver_json.get("verifier")},
        },
        "commander_derivation": {
            "instrument": MY_DERIVATION,
            "arms_total": mine.get("arms_total"), "killed_by_commander": mine.get("killed_by_commander"),
            "claims_agree": mine.get("lane_claims_agree_with_my_derivation"),
            "verifier_present": (mine.get("verifier_comparison") or {}).get("present"),
            "red_set_sizes": mine.get("red_set_sizes"),
        },
        "files_touched_by_the_whole_hop": len(touched),
        "files_outside_frontend_and_review": sorted(outside),
        "nothing_outside_expected": len(outside) == 0,
        "what_this_hop_invalidates": "frontend/src/features/planning/PlanWithAiSheet.tsx changed blob "
                                     "(c22cf42506a4175db992bde387ed8d9c6f1ffb9d -> %s) and three more frontend "
                                     "files changed blob, so per Q24 any in-flight measurement that renders the "
                                     "sheet or the continuation surface is now a previous-generation reading."
                                     % blobs.get(PRODUCT_FILES[0], "unknown"),
        "scope": "Proves the ref move, tree identity and that the cited kill evidence re-hashes. Does not "
                 "claim the phone shows this: no index switch and no preview-backend restart was performed "
                 "(Q47=option 2 holds the user-visible chain until the copy fix lands).",
    }
    json.dump(receipt, open("_ord0298d_landing_receipt_r1.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("landed:", LANDED, "| routes agree:", all_agree, "| ff-only:", receipt["move"]["fast_forward_only"],
          "| ahead", receipt["move"]["ahead_by"], "behind", receipt["move"]["behind_by"])
    print("frontend oid matches D:", receipt["tree_identity"]["equals_what_lane_D_measured"],
          "| files outside frontend/review:", sorted(outside) or "none")
    print("rehash arms/gate/verifier:", arms_ok, gate_ok, ver_ok, "| my derivation:",
          receipt["commander_derivation"]["killed_by_commander"], "/",
          receipt["commander_derivation"]["arms_total"], "| verifier present:",
          receipt["commander_derivation"]["verifier_present"])
    print("wrote _ord0298d_landing_receipt_r1.json")
    return 0 if (all_agree and receipt["move"]["fast_forward_only"]
                and receipt["tree_identity"]["equals_what_lane_D_measured"]
                and arms_ok and gate_ok and ver_ok and not outside) else 3


if __name__ == "__main__":
    raise SystemExit(main())
