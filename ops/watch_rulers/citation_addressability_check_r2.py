"""Parameterised re-cut of the addressability ruler: same check, any receipt, any field.

Why r2 exists: r1 is hardcoded to lane E's a2.  She delivered a3 (`verifier_derivation_a3_d2305848.json`)
that claims all five citations are now canonical 40-hex and equal the true blob of the file they name, and
claims it was copied from my own addressability table.  A claim of "I followed your instrument" must be
measured BY that instrument, not by reading her prose - so the instrument is lifted to take arguments
without touching r1's file (published tool paths are never rewritten).

Read-only: git rev-parse / cat-file against an already-fetched branch; no writes, no ref moves.
"""
import argparse
import hashlib
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"
CTRL_REF = "origin/cmdcontrol"


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=180)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-blob", required=True, help="40-hex blob of the receipt under test")
    ap.add_argument("--artifact-path", required=True)
    ap.add_argument("--field", default="per_arm_reading_blobs_40hex")
    ap.add_argument("--readings-dir", default="evidence/ord0281-keyed-write-deadline-gen3/")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rc, blob = git("cat-file", "-t", args.artifact_blob)
    assert rc == 0 and blob == "blob", "artifact blob %s does not resolve locally (%s) - fetch first" % (
        args.artifact_blob, blob)
    _, ctrl = git("rev-parse", CTRL_REF)
    assert len(ctrl) == 40, "branch ref did not resolve: %r" % ctrl
    # the artifact must be reachable at the path it claims, byte for byte
    rcp, at_path = git("rev-parse", "--revs-only", "%s:%s" % (ctrl, args.artifact_path))
    assert at_path == args.artifact_blob, "path %s holds %s, not the cited %s" % (
        args.artifact_path, at_path, args.artifact_blob)

    raw = subprocess.run(["git", "-C", REPO, "cat-file", "blob", args.artifact_blob],
                         capture_output=True).stdout
    d = json.loads(raw.decode("utf-8"))
    cited = d.get(args.field) or {}
    assert cited, "field %s absent or empty - the ruler would pass vacuously" % args.field
    rows = []
    for fname, her in sorted(cited.items()):
        rcv, resolved_to = git("rev-parse", "--verify", "-q", "%s^{blob}" % her)
        rct, true = git("rev-parse", "%s:%s%s" % (ctrl, args.readings_dir, fname))
        assert rct == 0 and len(true) == 40, "path %s did not resolve in %s (rc=%d)" % (fname, ctrl[:12], rct)
        b = subprocess.run(["git", "-C", REPO, "cat-file", "blob", true], capture_output=True).stdout
        rows.append({
            "file": fname,
            "cited_value": her, "cited_length": len(her),
            "canonical_40_hex": len(her) == 40,
            "resolves_via_git": rcv == 0, "resolved_to": resolved_to if rcv == 0 else None,
            "true_blob_sha1_of_that_path": true,
            "true_sha1_recomputes_from_bytes": hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest() == true,
            "true_bytes": len(b),
            "citation_is_the_true_blob": (rcv == 0 and resolved_to == true and len(her) == 40),
            "leading_40_chars_equal_the_true_blob": her[:40] == true,
        })
    good = sum(1 for r in rows if r["citation_is_the_true_blob"])
    resolves = sum(1 for r in rows if r["resolves_via_git"])
    canon = sum(1 for r in rows if r["canonical_40_hex"])
    all_good = good == len(rows) and len(rows) > 0
    out = {
        "schema": "CNX_CMDR_CITATION_ADDRESSABILITY_CHECK_V2",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "do the per-arm blob citations in an arbitrary receipt resolve to the objects they name, "
                "and are they canonical 40-hex",
        "instrument_diff_from_r1": "r1 hardcoded E's a2; r2 takes the receipt as arguments and additionally "
                                   "asserts the artifact itself is reachable at its claimed path under the same "
                                   "blob, and refuses to run on an empty field (a vacuous pass is a pass I did not earn)",
        "artifact_under_test": {"path": args.artifact_path, "blob": args.artifact_blob, "field": args.field,
                                "artifact_bytes": len(raw)},
        "rows": rows,
        "summary": {"citations": len(rows), "canonical_40_hex": canon, "resolve_via_git": resolves,
                    "equal_the_true_blob": good, "all_citations_addressable": all_good},
        "verdict": "CITATIONS_ADDRESSABLE" if all_good else "CITATIONS_NOT_ADDRESSABLE",
        "standing_rule": "a field whose name promises a blob must be exactly 40 hex and must resolve to the object "
                         "it names. The frozen Q38 ruler tests derivability, not addressability, so this sits on "
                         "top of it, not instead of it.",
        "discipline": {"refs_pushed": 0, "authoritative_branch_moved": 0, "evidence_paths_overwritten_by_me": 0,
                       "databases_opened": 0, "credential_values_printed": 0, "git_write_operations_run": 0},
        "claim_kind": "git_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("of %d per-arm blob citations: %d canonical 40-hex, %d resolve via git, %d equal the "
                             "true blob of the file they name" % (len(rows), canon, resolves, good))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open(args.out, "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for r in rows:
        print("   %-32s len=%d canonical=%-5s resolves=%-5s equals_true=%-5s true=%s" % (
            r["file"], r["cited_length"], r["canonical_40_hex"], r["resolves_via_git"],
            r["citation_is_the_true_blob"], r["true_blob_sha1_of_that_path"][:12]))
    print("verdict=%s  out=%s bytes=%d" % (out["verdict"], args.out, len(txt.encode("utf-8"))))
    return 0 if all_good else 5


if __name__ == "__main__":
    sys.exit(main())
