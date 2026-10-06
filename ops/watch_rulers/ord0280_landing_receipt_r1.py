"""Commander's landing receipt for ORD-0280: every field is READ from a measurement, none is typed.

Why this file exists (standing rule `evidence computed not literal`): a landing claim has two
independent halves - (a) the ref actually moved to the candidate and its parent is the previous tip
(so the move was fast-forward-only), and (b) the two files the candidate carries are BYTE-IDENTICAL to
the blobs that were verified before the move (so the thing landed is the thing measured).  A hand-written
`"PASS"` proves neither.  So:

  1. read the authoritative tip twice, by two different API routes;
  2. read the landed commit's parents and tree;
  3. for each named file, compare the blob at the landed tip against the blob at the VERIFIED CANDIDATE
     by re-fetching both objects and recomputing `git hash-object` locally;
  4. re-run the Q38 cell-derivation ruler as a subprocess against the lane's receipt, re-fetched by blob
     sha, and record the ruler's own exit code + the verdict string IT printed.

No assertion is derived from argv expectations except the two candidate/parent shas, which ARE the
coordinate being claimed; everything else is an observation.
"""
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
BRANCH = "mirror/integration-frontend-apple-pass1"

LANDED = "90d29a172e186aab6e6cb138ab4583ccf93bfa68"
EXPECT_PARENT = "6d041dcce11d05f28a55abadd40717f321b4db38"
CANDIDATE_SHA = "549ac8f1b20bc04e70eadbd238ade737eefbff01"  # the commit I measured BEFORE the move
RECEIPT_BLOB = "02dfbb817e5add8577c4c47a7e898983743b7202"   # ORD-0299 attribution-run receipt
FILES = ["frontend/e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts",
         "frontend/src/features/planning/PlanWithAiSheet.tsx"]


def get(path):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
        "User-Agent": "cmdr-ord0280-landing-receipt"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            return e.code, {"raw": "unparseable"}


def blob_of(commit, path):
    st, t = get(f"/repos/{REPO}/git/trees/{commit}?recursive=1")
    if st != 200:
        return None, f"tree http {st}"
    for e in t.get("tree", []):
        if e.get("path") == path:
            return e["sha"], ("truncated" if t.get("truncated") else "full")
    return None, "path-not-in-tree"


def content_sha(sha):
    """Re-fetch the object and recompute git's blob hash locally - never trust the API's sha alone."""
    import base64
    st, d = get(f"/repos/{REPO}/git/blobs/{sha}")
    if st != 200:
        return None, f"blob http {st}"
    raw = base64.b64decode(d["content"])
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


def main():
    q = urllib.parse.quote(BRANCH, safe="")
    st1, ref = get(f"/repos/{REPO}/git/ref/heads/{q}")
    tip_route1 = (ref.get("object") or {}).get("sha")
    st2, cs = get(f"/repos/{REPO}/commits?sha={q}&per_page=1")
    tip_route2 = cs[0]["sha"] if isinstance(cs, list) and cs else None

    st3, commit = get(f"/repos/{REPO}/commits/{LANDED}")
    parents = [p["sha"] for p in commit.get("parents", [])]
    msg = commit.get("commit", {}).get("message", "")

    # read the receipt from the published blob, so the ruler measures what others can read
    import base64
    st4, rb = get(f"/repos/{REPO}/git/blobs/{RECEIPT_BLOB}")
    raw = base64.b64decode(rb["content"]) if st4 == 200 else b""
    recomputed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest() if raw else None
    receipt_local = "_ord0280_landing_receipt_blob.json"
    if raw:
        open(receipt_local, "wb").write(raw)

    ruler_cmd = [sys.executable, "receipt_cell_derivation_check_r2.py",
                 "--receipt", receipt_local, "--out", "_ord0280_landing_ruler_out.json"]
    p = subprocess.run(ruler_cmd, cwd=".", capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    ruler_stdout = p.stdout or ""
    ruler_verdict = None
    for line in ruler_stdout.splitlines():
        if "overall" in line:
            ruler_verdict = line.strip()
    cells = None
    for line in ruler_stdout.splitlines():
        if line.startswith("cells "):
            try:
                cells = int(line.split()[1])
            except (IndexError, ValueError):
                cells = None

    per_file = []
    for path in FILES:
        landed_blob, note_a = blob_of(LANDED, path)
        cand_blob, note_b = blob_of(CANDIDATE_SHA, path)
        cs_landed, sz_landed = content_sha(landed_blob) if landed_blob else (None, None)
        cs_cand, sz_cand = content_sha(cand_blob) if cand_blob else (None, None)
        per_file.append({
            "path": path,
            "blob_at_landed_tip": landed_blob, "tree_note": note_a,
            "blob_at_verified_candidate": cand_blob, "cand_tree_note": note_b,
            "recomputed_git_hash_at_landed": cs_landed, "bytes_landed": sz_landed,
            "recomputed_git_hash_at_candidate": cs_cand, "bytes_candidate": sz_cand,
            # equality that can only hold if both sides exist AND were re-hashed locally
            "byte_identical": bool(cs_landed) and cs_landed == cs_cand,
        })

    ident = [f for f in per_file if f["byte_identical"]]
    ok_move = bool(tip_route1) and tip_route1 == tip_route2 == LANDED
    ok_parent = parents == [EXPECT_PARENT]
    ok_files = len(ident) == len(FILES)
    ok_ruler = p.returncode == 0 and cells is not None and cells > 0
    overall = ("LANDED_AND_VERIFIED" if (ok_move and ok_parent and ok_files and ok_ruler)
               else "NOT_VERIFIED")

    out = {
        "schema": "CNX_CMDR_LANDING_RECEIPT_V1",
        "order": "ORD-0280",
        "claim": "the attribution-label fix landed on the authoritative line fast-forward-only, "
                 "and the two files at the new tip are byte-identical to the verified candidate",
        "branch": BRANCH,
        "tip_read_back": {
            "route_git_ref_heads_http": st1, "route_git_ref_heads": tip_route1,
            "route_commits_http": st2, "route_commits": tip_route2,
            "routes_agree_on_landed_sha": bool(tip_route1) and tip_route1 == tip_route2,
        },
        "landed_commit": {
            "sha": LANDED, "http": st3, "parents": parents,
            "parent_is_previous_tip": ok_parent,
            "fast_forward_only": ok_parent and ok_move,
            "subject": msg.splitlines()[0] if msg else None,
        },
        "verified_candidate": {"sha": CANDIDATE_SHA},
        "files": per_file,
        "files_expected": len(FILES), "files_byte_identical": len(ident),
        "ruler": {
            "instrument": "receipt_cell_derivation_check_r2.py",
            "subject_published_blob": RECEIPT_BLOB,
            "blob_http": st4, "recomputed_git_hash": recomputed,
            "recomputed_equals_cited": recomputed == RECEIPT_BLOB,
            "bytes": len(raw),
            "exit_code": p.returncode,
            "cells_read": cells,
            "verdict_line_printed_by_ruler": ruler_verdict,
            "stderr_tail": (p.stderr or "")[-200:],
        },
        "decisions": {
            "tip_both_routes_equal_landed": ok_move,
            "parent_equals_previous_tip": ok_parent,
            "all_named_files_byte_identical": ok_files,
            "ruler_green_with_nonzero_cells": ok_ruler,
        },
        "overall": overall,
        "scope": ("Ref move + blob equality + Q38 ruler re-run, all read at 2026-09-25 ~09:40 +08. "
                  "Does NOT claim the phone shows this generation: no dist/index switch and no preview "
                  "backend restart was performed (Q45=option 1), so this is LANDED / NOT-YET-DEPLOYED-to-phone."),
    }
    json.dump(out, open("_ord0280_landing_receipt.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("overall:", overall)
    print("  tip route1/route2:", tip_route1, tip_route2, "agree:", out["tip_read_back"]["routes_agree_on_landed_sha"])
    print("  parents:", parents, "== previous tip:", ok_parent)
    for f in per_file:
        print("  ", f["path"].split("/")[-1], "identical:", f["byte_identical"],
              f["recomputed_git_hash_at_landed"], f["bytes_landed"], "B")
    print("  ruler:", p.returncode, ruler_verdict, "| blob recomputed==cited:",
          out["ruler"]["recomputed_equals_cited"])
    print("wrote _ord0280_landing_receipt.json")
    return 0 if overall == "LANDED_AND_VERIFIED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
