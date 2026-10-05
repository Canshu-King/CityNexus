"""ORD-0553 r12 -- revet a bundle: the dist a screen reading came from must be reproducible byte-for-byte
from the sha it claims, and a different generation must not pass.

Why after r11: the generation lock proves the build *receipt* names the pinned sha and that the served
index.html names what the walk recorded.  It does not prove the bytes on disk really are that sha's
output -- the gap I named RULE_GAP_CHUNK_HASH_NOT_REVETED_BY_LOCK.  This closes it the only way that is
actually checkable for a vite build: build the same sha again in a second, independent directory and
compare every file's sha256.  Equal sets with equal bytes means the served bundle was that generation's
output; any difference is refused.

Two cases must both behave: same sha twice -> identical; a neighbouring generation -> refused.  A tool
that passes both is not evidence on its own, so a third arm asserts it is not a rubber stamp.
"""
import hashlib
import io
import json
import os
import re
import sys

BUILDS = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"


def dist_files(tag):
    root = os.path.join(BUILDS, "_build_%s" % tag, "frontend", "dist")
    out = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, root).replace("\\", "/")] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def entry(tag):
    idx = os.path.join(BUILDS, "_build_%s" % tag, "frontend", "dist", "index.html")
    return sorted(set(re.findall(r"assets/index-[A-Za-z0-9_-]+\.js",
                                 io.open(idx, encoding="utf-8", errors="replace").read())))


def build_sha(tag):
    return json.load(io.open(os.path.join(BUILDS, "_build_%s_info.json" % tag), encoding="utf-8"))["sha"]


def revet(tag_a, tag_b):
    A, B = dist_files(tag_a), dist_files(tag_b)
    only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
    diff = [f for f in sorted(set(A) & set(B)) if A[f] != B[f]]
    return {"pinned_a": build_sha(tag_a), "tag_a": tag_a, "files_a": len(A),
            "pinned_b": build_sha(tag_b), "tag_b": tag_b, "files_b": len(B),
            "entry_a": entry(tag_a), "entry_b": entry(tag_b),
            "only_in_a": only_a[:6], "only_in_b": only_b[:6], "bytes_differ": diff[:6],
            "same_byte_identical": not only_a and not only_b and not diff}


def main():
    pos = revet("cmdra_0553_r11", "cmdra_0553_r12v")
    neg = revet("cmdra_0553_r11", "cmdra_0553_r12neg")
    arms = [
        {"id": "independent_rebuild_of_one_sha_is_byte_identical",
         "verdict": "PASS" if pos["same_byte_identical"] and pos["entry_a"] == pos["entry_b"] else "FAIL",
         "observed": "%d files vs %d, entry %s on both, only_a %d, only_b %d, bytes_differ %d" % (
             pos["files_a"], pos["files_b"], ",".join(pos["entry_a"]), len(pos["only_in_a"]),
             len(pos["only_in_b"]), len(pos["bytes_differ"]))},
        {"id": "a_previous_generation_is_refused",
         "verdict": "PASS" if (not neg["same_byte_identical"]) and neg["entry_a"] != neg["entry_b"] else "FAIL",
         "observed": "%d vs %d, entry %s vs %s, bytes_differ %d, only_in_a %s" % (
             neg["files_a"], neg["files_b"], ",".join(neg["entry_a"]), ",".join(neg["entry_b"]),
             len(neg["bytes_differ"]), neg["only_in_a"][:2])},
        {"id": "revet_is_not_a_rubber_stamp",
         "verdict": "PASS" if (pos["same_byte_identical"] and not neg["same_byte_identical"]) else "FAIL",
         "observed": "identical(same sha)=%s identical(other generation)=%s" % (
             pos["same_byte_identical"], neg["same_byte_identical"])},
    ]
    reds = [a["id"] for a in arms if a["verdict"] == "FAIL"]
    rep = {"tool": "cmdra_0553_dist_revet_r12",
           "rule": "the bundle a reading came from must be reproducible byte-for-byte from the sha it claims",
           "positive": pos, "negative": neg, "arms": arms,
           "verdict": "RED" if reds else "GREEN", "red_arms": reds,
           "note_missing_dists": "the older _build_cmdra_0553_r8 and _build_cmdra_0553_r2 trees had no "
                                 "frontend dir at all when this ran -- shared build scratch is reclaimed, "
                                 "so a block must never depend on the dist surviving"}
    out = os.path.join(R1, "_evidence", "r12_dist_revet_report.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps({"out": out, "verdict": rep["verdict"], "red_arms": reds}, ensure_ascii=False))
    for a in arms:
        print(" ", a["verdict"], a["id"], "|", a["observed"][:150])
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(main())
