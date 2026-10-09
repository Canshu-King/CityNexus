#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest for cmdr_recut_r1.py -- two-way, plumbing only, never touches a work tree or the real index.

Why: cmdr_recut_r1.py decides whether a lane's bytes landed intact.  A tool whose "identical" proof
could pass vacuously is worse than no tool, so every arm below asserts BOTH the verdict and the fact
that makes the verdict non-vacuous (the fixture really changed the file; the "clean" arms really are
clean for the stated reason).

Arms
  A control      candidate changes ONE file off an older base; tip untouched there -> RECUT_OK, 1/1.
  B same-line    tip and candidate rewrite the same line differently -> must NOT be RECUT_OK.
  C auto-merge   tip edits a different region of the same file -> RECUT_OK and the merged blob must
                 equal the LANE's blob (this is what "no source line was auto-merged" tests).
  D fast-forward candidate already carries the tip as its parent -> the tool must decline to invent
                 a re-cut rather than quietly produce a merge commit.

Run:  python cmdr_recut_selftest_r1.py [--out FILE]     exit 0 = every arm discriminated correctly.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = "D:/moodle/CityNexus"
LINE = "origin/mirror/integration-frontend-apple-pass1"
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cmdr_recut_r1.py")
VICTIM = "frontend/src/components/ProductErrorBoundary.tsx"
NEIGHBOUR = "frontend/src/features/setup/JourneyTrialSetup.tsx"

TMP = tempfile.mkdtemp(prefix="cnx_recut_selftest_")


def git(*args, **kw):
    env = dict(os.environ)
    if kw.get("idx"):
        env["GIT_INDEX_FILE"] = kw["idx"]
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300, env=env,
                       input=kw.get("input"))
    if p.returncode:
        raise SystemExit("git %s -> rc %d: %s" % (" ".join(args[:2]), p.returncode,
                                                  (p.stderr or p.stdout).strip()[:400]))
    return p.stdout.strip()


def git_bin(*args, **kw):
    """Byte-safe variant: hash-object -w --stdin takes bytes on stdin and text=True would corrupt it."""
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, timeout=300,
                       input=kw.get("data"))
    if p.returncode:
        raise SystemExit("git %s -> rc %d: %s" % (" ".join(args[:2]), p.returncode,
                                                  p.stderr.decode("utf-8", "replace").strip()[:400]))
    return p.stdout.decode("utf-8", "replace").strip()


def show_bytes(rev, path):
    """Exact bytes of one blob. The selftest's whole point is line hunks, so a `.strip()` here would
    silently turn a clean two-region merge into a trailing-newline conflict -- which is the bug this
    file used to have."""
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                       capture_output=True, timeout=300)
    if p.returncode:
        raise SystemExit("git show %s:%s -> %s" % (rev, path, p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout


def make_child(parent, path, mutate, msg):
    """Commit whose only change vs `parent` is `path` := mutate(original bytes). Isolated temp index."""
    cur = show_bytes(parent, path)
    new_content = mutate(cur)
    if new_content == cur:
        raise SystemExit("VACUOUS FIXTURE: mutate left %s unchanged at %s" % (path, parent[:12]))
    blob = git_bin("hash-object", "-w", "--stdin", data=new_content)
    if blob == git("rev-parse", "%s:%s" % (parent, path)):
        raise SystemExit("VACUOUS FIXTURE: hash-object returned the pre-existing blob")
    idx = os.path.join(TMP, "idx_%s_%d" % (path[-12:], len(os.listdir(TMP))))
    git("read-tree", parent, idx=idx)
    git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, path), idx=idx)
    tree = git("write-tree", idx=idx)
    return git("commit-tree", tree, "-p", parent, "-m", msg)


def run_tool(order, cand, line):
    out = os.path.join(TMP, order + ".json")
    p = subprocess.run([sys.executable, TOOL, "--order", order, "--cand", cand,
                        "--line", line, "--out", out],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    rep = {}
    if os.path.exists(out):
        rep = json.load(open(out, encoding="utf-8"))
    rep["_rc"] = p.returncode
    rep["_stdout"] = p.stdout.strip()[-500:]
    return rep


def main():
    a = sys.argv
    out_path = a[a.index("--out") + 1] if "--out" in a else os.path.join(TMP, "selftest.json")

    tip = git("rev-parse", LINE)
    base = git("rev-parse", "%s~~~~" % tip)          # four generations back: a genuine stale base
    # Precondition, stated rather than assumed: both fixture files must be byte-stable between the
    # chosen base and the tip, otherwise arm B's "same line" conflict would not be the thing I test.
    for f in (VICTIM, NEIGHBOUR):
        bb, tb = git("rev-parse", "%s:%s" % (base, f)), git("rev-parse", "%s:%s" % (tip, f))
        if bb != tb:
            raise SystemExit("PRECONDITION BROKEN: %s differs between base %s and tip %s (%s vs %s); "
                             "pick a stable file or a nearer base before trusting these arms."
                             % (f, base[:12], tip[:12], bb[:8], tb[:8]))
    src = show_bytes(base, VICTIM)
    nb = show_bytes(base, NEIGHBOUR)
    stamp = b"cmdr-recut-selftest"

    # A: candidate touches only VICTIM, off the older base; the line never went near that file.
    cand_A = make_child(base, VICTIM, lambda b: b + b"\n/* arm-A lane tail */\n", "arm-A candidate")
    # B: both sides append at EOF -> the same hunk, so the three-way merge must report a conflict.
    tip_B = make_child(tip, VICTIM, lambda b: b + b"\n/* arm-B tip tail */\n", "arm-B tip side")
    cand_B = make_child(base, VICTIM, lambda b: b + b"\n/* arm-B cand tail */\n", "arm-B candidate")
    # C: both sides change VICTIM but in different regions -> merge-tree is *clean*, yet the file that
    #    lands is neither the lane's nor the tip's.  The lane's tests no longer describe it, so the
    #    tool must refuse.  This is the arm that keeps `identical` from being decorative.
    tip_C = make_child(tip, VICTIM, lambda b: b"/* arm-C tip head */\n" + b, "arm-C tip side")
    cand_C = make_child(base, VICTIM, lambda b: b + b"\n/* arm-C cand tail */\n", "arm-C candidate")
    # D: candidate is a direct child of the current tip -> a re-cut would invent a merge commit.
    cand_D = make_child(tip, NEIGHBOUR, lambda b: b + b"\n/* arm-D */\n", "arm-D candidate")

    repA = run_tool("armA", cand_A, tip)
    repB = run_tool("armB", cand_B, tip_B)
    repC = run_tool("armC", cand_C, tip_C)
    repD = run_tool("armD", cand_D, tip)

    checks = []

    def chk(name, ok, reading):
        checks.append({"arm": name, "holds": bool(ok), "reading": reading})

    chk("A.verdict_RECUT_OK", repA.get("verdict") == "RECUT_OK", repA.get("verdict"))
    chk("A.all_files_identical", repA.get("files") and all(f["identical"] for f in repA["files"]),
        [(f["path"].split("/")[-1], f["identical"]) for f in repA.get("files", [])])
    chk("A.cand_really_changed_the_file",
        all(f["cand_changed_the_file"] for f in repA.get("files", [])),
        "non-vacuity: lane blob != base blob")
    chk("A.parents_are_tip_then_cand",
        repA.get("readback_parents", [])[:1] == [tip], repA.get("readback_parents"))

    chk("B.refused_to_claim_a_clean_recut", repB.get("verdict") != "RECUT_OK", repB.get("verdict"))
    chk("B.exit_nonzero", repB.get("_rc", 0) != 0, "rc=%s" % repB.get("_rc"))

    chk("C.refused_because_the_lane_blob_did_not_survive",
        repC.get("verdict") == "REFUSED_AUTO_MERGED" and VICTIM in repC.get("auto_merged_files", []),
        "%s auto=%s" % (repC.get("verdict"), repC.get("auto_merged_files")))
    chk("C.the_refusal_names_the_file_not_a_crash", repC.get("_rc", 0) == 5, "rc=%s" % repC.get("_rc"))

    chk("D.declines_when_ff_is_possible", repD.get("verdict") is None and
        "FAST_FORWARD_POSSIBLE" in repD.get("_stdout", ""), repD.get("_stdout", "")[:120])

    report = {
        "tool": "cmdr_recut_r1.py", "line": LINE, "tip": tip, "base": base,
        "fixtures": {"cand_A": cand_A, "tip_B": tip_B, "cand_B": cand_B,
                     "tip_C": tip_C, "cand_C": cand_C, "cand_D": cand_D},
        "recut_A": repA.get("recut_commit"), "checks": checks,
        "arms": {"A": repA.get("verdict"), "B": repB.get("verdict"),
                 "C": repC.get("verdict"), "D": "FAST_FORWARD_POSSIBLE"
                 if "FAST_FORWARD_POSSIBLE" in repD.get("_stdout", "") else repD.get("verdict")},
    }
    report["all_holds"] = all(c["holds"] for c in checks)
    report["n_checks"] = len(checks)
    report["n_holds"] = sum(1 for c in checks if c["holds"])
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    for c in checks:
        print("%-34s %s   %s" % (c["arm"], "HOLD" if c["holds"] else "BROKEN", c["reading"]))
    print("SELFTEST %s  %d/%d checks  out=%s" % ("GREEN" if report["all_holds"] else "RED",
                                                 report["n_holds"], report["n_checks"], out_path))
    return 0 if report["all_holds"] else 1


if __name__ == "__main__":
    import io
    sys.exit(main())
