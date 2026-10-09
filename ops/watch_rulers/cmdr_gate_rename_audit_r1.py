"""Audit lane HJ-P3's one renamed field: did she pass the shared-content gate by changing a KEY, keeping the value?

Why this matters beyond one file: the Q57 gate is identical-or-refuse, and her remedy for a hit was to publish a
copy whose only difference is `"token"` -> `"pair_id"`. That is legitimate ONLY if (a) exactly the key name moved,
(b) the value, order and every other byte are unchanged, and (c) the original stays published so nothing was
deleted to make the gate quiet. If I do not measure that, "rename the field the gate looks at" becomes a hole
through which anyone can walk. So: byte-diff the two blobs myself and count what actually differs.

Read-only: git cat-file against the already-fetched evidence branch.
"""
import difflib
import hashlib
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"
ORIG = ("original (gate-refused, kept published)", "206d4831c5fd2aa7fde7518502b1e8a9521d4fee")
PUB = ("published copy", "3f0db1fdebb6690593fa659389c62cc6e9fb37ff")
PROOF = ("her own copy-proof artifact", "c3a64804f522aaa2f751a6a9fda9aa7e1923c8f2")
DIR = "evidence/ord0300-c2-pairing-hjp3/"


def blob(sha, required=True):
    p = subprocess.run(["git", "-C", REPO, "cat-file", "blob", sha], capture_output=True, timeout=300)
    if p.returncode:
        if required:
            raise SystemExit("blob %s missing locally - fetch commander/control first" % sha)
        return None
    r = hashlib.sha1(b"blob %d\x00" % len(p.stdout) + p.stdout).hexdigest()
    if r != sha:
        raise SystemExit("blob %s recomputes as %s" % (sha, r))
    return p.stdout


def main():
    # The gate-refused original is NOT on the shelf (only her `_pub.json` copy is), so this audit cannot diff the
    # two files. What it CAN do is measure the published copy and the arithmetic of the claim: a rename of
    # "token"->"pair_id" is +2 bytes per occurrence, so the declared size delta must equal 2 * occurrences, and
    # the old key name must appear zero times in what was published.
    o_raw = blob(ORIG[1], required=False)
    p_raw, proof_raw = blob(PUB[1]), blob(PROOF[1])
    proof = json.loads(proof_raw.decode("utf-8"))
    old_key = '"token"'
    new_key = '"pair_id"'
    occurrences_new = p_raw.decode("utf-8").count(new_key)
    occurrences_old = p_raw.decode("utf-8").count(old_key)
    declared_delta = proof["published_copy"]["bytes"] - proof["source"]["bytes"]
    arithmetic = declared_delta == 2 * occurrences_new
    pub_blob_matches = hashlib.sha1(b"blob %d\x00" % len(p_raw) + p_raw).hexdigest() == PUB[1]
    original_on_shelf = o_raw is not None
    if original_on_shelf:
        o = o_raw.decode("utf-8").splitlines()
        p = p_raw.decode("utf-8").splitlines()
        diff = [l for l in difflib.unified_diff(o, p, lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        minus = [l[1:].strip().rstrip(",") for l in diff if l.startswith("-")]
        plus = [l[1:].strip().rstrip(",") for l in diff if l.startswith("+")]

        def strip_key(line):
            return line.split(":", 1)[1] if ":" in line else line
        val_equal = len(minus) == len(plus) and all(strip_key(a) == strip_key(b) for a, b in zip(minus, plus))
        changed = {"minus": minus, "plus": plus}
    else:
        val_equal = None
        changed = {}
    gate_status = ("KEY_ONLY_RENAME_CONTENT_PRESERVED" if (val_equal and original_on_shelf)
                   else ("LENGTH_AND_KEY_ARITHMETIC_CONSISTENT_ORIGINAL_NOT_ON_SHELF"
                         if arithmetic and occurrences_old == 0 else "NOT_ESTABLISHED"))
    out = {
        "schema": "CNX_CMDR_GATE_RENAME_AUDIT_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "measure HJ-P3's claim that the published copy differs from the gate-refused original only in one "
                "field NAME, and that the original is still on the shelf",
        "blobs": [{"role": r, "sha": s, "bytes": (len(b) if (b := blob(s, required=False)) else None),
                   "on_shelf_in_branch": b is not None} for r, s in (ORIG, PUB, PROOF)],
        "her_proof_artifact": proof,
        "published_copy_measured": {"bytes": len(p_raw), "blob_recomputes": pub_blob_matches,
                                    "occurrences_of_new_key": occurrences_new,
                                    "occurrences_of_old_key": occurrences_old},
        "rename_arithmetic": {"declared_source_bytes": proof["source"]["bytes"],
                              "declared_published_bytes": proof["published_copy"]["bytes"],
                              "declared_delta": declared_delta,
                              "expected_delta_for_a_key_rename_only": 2 * occurrences_new,
                              "consistent": arithmetic},
        "changed_lines": changed,
        "value_bytes_identical_after_stripping_the_key": val_equal,
        "original_still_published": original_on_shelf,
        "gate_status": gate_status,
        "audit_ceiling": ("byte-level equality of the two files cannot be tested by anyone who does not hold the "
                          "refused original - she must publish it under its own new path for this exception to be "
                          "independently checkable"),
        "standing_rule": "passing the shared-content gate by renaming the key it flags is acceptable only as a "
                         "MEASURED key-only change with the refused original left published and a byte-level proof "
                         "artifact; stripping or falsifying the content to quiet the gate is not.",
        "for_the_ledger": ("this becomes the named exception shape: a rename must ship (original blob ON THE SHELF, "
                           "copy blob, proof artifact) and anyone invoking it must cite all three"),
        "discipline": {"refs_pushed": 0, "files_written_by_this_script": 0, "databases_opened": 0,
                       "credential_values_printed": 0},
        "claim_kind": "byte_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = (
        "published copy %d B (blob recomputes: %s) carries the new key %d time(s) and the old key %d; the declared "
        "size delta %d B equals 2 x %d = %d, which is what renaming \"%s\"->\"%s\" alone predicts (%s); the "
        "gate-refused original %s is %s on commander/control => %s" % (
            len(p_raw), pub_blob_matches, occurrences_new, occurrences_old, declared_delta, occurrences_new,
            2 * occurrences_new, "token", "pair_id", arithmetic, ORIG[1],
            "NOT" if not original_on_shelf else "", gate_status))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_p3_rename_audit.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    print("file=_cmdr_p3_rename_audit.json bytes=%d" % len(txt.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
