"""Recompute lane E's a4 top-level derived_result from the cells array and compare with `==`.

Why: B-1 says only a verifier's derived_result closes anything, so when lane E fills that field I must check it
is DERIVED and not asserted. That means I recount her cells myself, from the published bytes, and compare each
number with equality (never `in`, which reads punctuation drift as a match). I also confirm the generation cell
actually scopes the verdicts instead of merely naming a tree.

Read-only: git cat-file against the already-fetched evidence branch.
"""
import hashlib
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"
BLOB = "d8b2a26138fefbaaef2a9c1e20c4f2c3676ac5ce"
PATH = "evidence/ord0314-0281-gen3-derivation-d2305848/verifier_derivation_a4_d2305848.json"
CTRL = "origin/cmdcontrol"
TIP = "2344145ce6342b6ac32ac4d0955c0f524d8c9320"
BOUND = "13af1ff4ba4516aa1a39cda67428ed4a2a34ac69"


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=300)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(a[:3]), p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout


def main():
    raw = git("cat-file", "blob", BLOB)
    recomputed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    at_path = git("rev-parse", "--revs-only", "%s:%s" % (CTRL, PATH)).decode().strip()
    d = json.loads(raw.decode("utf-8"))
    cells = d.get("cells") or []
    # my own counts, from the published bytes
    my_total = len(cells)
    my_met = sum(1 for c in cells if c.get("verdict") == "MET")
    # her own vocabulary: NOT_MEASURED and DECLARED are two different honest states, so I recount them by name
    # instead of dumping everything non-MET into one bucket (that would manufacture a mismatch and read as HER
    # defect - which is exactly the mistake this instrument exists to prevent).
    my_not_measured = sorted(c.get("cell") for c in cells if c.get("verdict") == "NOT_MEASURED")
    my_declared = sorted(c.get("cell") for c in cells if c.get("verdict") == "DECLARED")
    counters = [c for c in cells if str(c.get("cell", "")).startswith("counter_")]
    my_kills = sum(1 for c in counters
                   if any(str(v) == "NOT_MET" for v in (c.get("readings") or {}).values()))
    dr = d.get("derived_result") or {}
    claimed_scope = json.dumps(d.get("generation_binding") or {}, ensure_ascii=False)
    # what SHE claims at the top level, compared with ==
    checks = [
        {"field": "derived_result.cells_total", "mine": my_total,
         "hers": dr.get("cells_total"), "equal": dr.get("cells_total") == my_total},
        {"field": "derived_result.cells_MET", "mine": my_met,
         "hers": dr.get("cells_MET"), "equal": dr.get("cells_MET") == my_met},
        {"field": "derived_result.cells_NOT_MEASURED", "mine": my_not_measured,
         "hers": sorted(dr.get("cells_NOT_MEASURED") or []),
         "equal": sorted(dr.get("cells_NOT_MEASURED") or []) == my_not_measured},
        {"field": "derived_result.cells_DECLARED", "mine": my_declared,
         "hers": sorted(dr.get("cells_DECLARED") or []),
         "equal": sorted(dr.get("cells_DECLARED") or []) == my_declared},
        {"field": "derived_result.independent_kills", "mine": my_kills,
         "hers": dr.get("independent_kills_derived", dr.get("independent_kills")),
         "equal": dr.get("independent_kills_derived", dr.get("independent_kills")) == my_kills},
        {"field": "generation_binding.tested_tree", "mine": BOUND,
         "hers": (d.get("generation_binding") or {}).get("tested_tree"),
         "equal": (d.get("generation_binding") or {}).get("tested_tree") == BOUND},
    ]
    all_equal = all(c["equal"] for c in checks)
    scope = json.dumps(d, ensure_ascii=False)
    out = {
        "schema": "CNX_CMDR_VERIFIER_DERIVED_FIELD_CHECK_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "is lane E's a4 derived_result actually derivable from her own cells array, recomputed by me "
                "from the published bytes and compared with equality",
        "artifact": {"path": PATH, "blob_cited": BLOB, "blob_measured": recomputed,
                     "blob_matches": recomputed == BLOB, "bytes": len(raw),
                     "path_holds_this_blob": at_path == BLOB},
        "comparisons": checks,
        "verdict": "DERIVED_FIELD_REPRODUCES" if all_equal else "DERIVED_FIELD_DOES_NOT_REPRODUCE",
        "generation_scope_language": {
            "names_the_authority_tip": TIP in scope,
            "declares_no_transfer": ("transfers_to_authority_tip" in scope and "false" in scope),
            "marks_tip_readings_not_measured": "NOT_MEASURED" in scope,
        },
        "standing_rule": "a verifier's derived_result is accepted only when someone else can recount it from the "
                         "same bytes and get equality on every number; counts are compared with ==, never with in.",
        "discipline": {"refs_pushed": 0, "authoritative_branch_moved": 0, "product_bytes_changed": 0,
                       "databases_opened": 0, "credential_values_printed": 0},
        "claim_kind": "byte_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("a4 blob %s (%d B) at its claimed path: %s; recomputed from her cells array I get "
                             "total=%d MET=%d not-MET=%s kills=%d, and every one of those equals what she writes at "
                             "top level: %s => %s" % (
                                 BLOB[:10], len(raw), at_path == BLOB, my_total, my_met, my_not_measured, my_kills,
                                 all_equal, out["verdict"]))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_a4_derived_check.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for c in checks:
        print("   %-38s mine=%-14s hers=%-14s equal=%s" % (c["field"], c["mine"], c["hers"], c["equal"]))
    print("file=_cmdr_a4_derived_check.json bytes=%d" % len(txt.encode("utf-8")))
    return 0 if all_equal else 6


if __name__ == "__main__":
    sys.exit(main())
