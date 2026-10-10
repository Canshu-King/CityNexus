"""Do the blob citations in a receipt actually resolve to the objects they name - and are they canonical 40-hex?

Why this exists: lane E's ORD-0314 a2 finally passed the frozen Q38 ruler (cells 13, hard 0, soft 6), so its
SHAPE is assessable.  But the ruler tests derivability, not addressability, and her field is literally named
`per_arm_reading_blobs_40hex` while its values are 64 characters.  A citation nobody can fetch is not a
coordinate, so this checks each one against the object store and prints a correction table.

Read-only: git rev-parse / cat-file against an already-fetched branch; no writes, no ref moves.
"""
import hashlib
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"
CTRL_REF = "origin/cmdcontrol"
ARTIFACT = "_e0314_a2.json"
ARTIFACT_BLOB = "993a3753b34911e73527b691168b6bfb8062cb17"
ARTIFACT_PATH = "evidence/ord0314-0281-gen3-derivation-d2305848/verifier_derivation_a2_d2305848.json"
FIELD = "per_arm_reading_blobs_40hex"
READINGS_DIR = "evidence/ord0281-keyed-write-deadline-gen3/"


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=180)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def main():
    _, ctrl = git("rev-parse", CTRL_REF)   # git() returns (rc, stdout); the first run unpacked the returncode into `ctrl`, which made every "true blob" lookup fail and is exactly the kind of instrument fault that must not be read as a lane defect
    assert len(ctrl) == 40, "branch ref did not resolve: %r" % ctrl
    d = json.loads(io.open(ARTIFACT, encoding="utf-8").read())
    cited = d.get(FIELD) or {}
    rows = []
    for fname, her in sorted(cited.items()):
        rcv, resolved_to = git("rev-parse", "--verify", "-q", "%s^{blob}" % her)
        rct, true = git("rev-parse", "%s:%s%s" % (ctrl, READINGS_DIR, fname))
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
    out = {
        "schema": "CNX_CMDR_CITATION_ADDRESSABILITY_CHECK_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "do the per-arm blob citations resolve to the objects they name, and are they canonical 40-hex",
        "artifact_under_test": {"path": ARTIFACT_PATH, "blob": ARTIFACT_BLOB, "field": FIELD},
        "rows": rows,
        "summary": {"citations": len(rows), "canonical_40_hex": canon, "resolve_via_git": resolves,
                    "equal_the_true_blob": good},
        "lenient_resolution_warning": "both git and the GitHub blob route happily resolve a longer hex string by "
                                      "its leading 40 characters, so one 64-char citation still lands on the right "
                                      "object. That is luck, not correctness - the one whose first 40 characters are "
                                      "NOT the real sha1 returns nothing at all.",
        "standing_rule": "a field whose name promises a blob must be exactly 40 hex and must resolve to the object "
                         "it names. The frozen Q38 ruler does not test addressability (it tests derivability), so "
                         "this check sits on top of it, not instead of it.",
        "consequence_for_ORD_0314": "the ruler verdict stands - the shape is assessable. My 21:02 ask that each "
                                    "reading be cited by blob is NOT met: %d of %d citations are not the canonical "
                                    "blob of the file they name. ORD-0314 is ACCEPTED-CODE for shape; it is not "
                                    "closed on citations until the a3 fixes them." % (len(rows) - good, len(rows)),
        "discipline": {"refs_pushed": 0, "authoritative_branch_moved": 0, "evidence_paths_overwritten_by_me": 0,
                       "databases_opened": 0, "credential_values_printed": 0, "git_write_operations_run": 0},
        "claim_kind": "git_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("of %d per-arm blob citations: %d canonical 40-hex, %d resolve via git, %d equal the "
                             "true blob of the file they name" % (len(rows), canon, resolves, good))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_citation_check_0314.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for r in rows:
        print("   %-32s len=%d canonical=%-5s resolves=%-5s equals_true=%-5s true=%s" % (
            r["file"], r["cited_length"], r["canonical_40_hex"], r["resolves_via_git"],
            r["citation_is_the_true_blob"], r["true_blob_sha1_of_that_path"][:12]))
    print("file=_cmdr_citation_check_0314.json bytes=%d" % len(txt.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
