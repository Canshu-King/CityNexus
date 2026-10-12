"""ORD-0577 census branch: ship the instrument and its readings, on this lane's own ref.

Zero product bytes: the only file outside review/ is the new e2e census spec, and it is a ruler, not
a product path. Parent is the tip whose frontend bytes the census ran on (verified equal to this
tree's copy of the shell file before the commit is built).

usage: python ord0577_census_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
TIP = "8996eee4fb9fb4e159588305223ef421728c4e72"
REF = "refs/heads/review/8ac89982-ord0577-off-route-bar-census-r1"
INDEX = LANE / "run/ord0577_census_index"
REPORT = LANE / "run/ord0577_census_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
TIP_SHELL_BLOB = "5d62f7bc78a58369d871a37c820e0b9a1a6076e6"
SPEC = "frontend/e2e/qoder-8ac89982-ord0577-off-route-bar-census-r1.spec.ts"
ENTRIES = [
    (SPEC, TREE / SPEC),
    ("review/ord0577/census_zh.json", LANE / "evidence/ord0512/e2e/ord0577_census_zh.json"),
    ("review/ord0577/census_en.json", LANE / "evidence/ord0512/e2e/ord0577_census_en.json"),
    ("review/ord0577/gate_stdout_r1.txt", LANE / "run/_ord0577_census_r3.out"),
    ("review/ord0577/provenance_r1.txt", LANE / "run/_ord0577_census_provenance.txt"),
    ("review/ord0577/commit_tool_r1.py", LANE / "run/ord0577_census_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    git("cat-file", "-e", "%s^{commit}" % TIP)
    tip_blob = git("rev-parse", "%s:%s" % (TIP, SHELL_REL))
    tree_blob = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % TIP, "REF=%s" % REF, "tip_shell_blob=%s" % tip_blob, "tree_shell_blob=%s" % tree_blob,
           "shell_blobs_equal=%s" % (tip_blob == tree_blob == TIP_SHELL_BLOB)]
    if not (tip_blob == tree_blob == TIP_SHELL_BLOB):
        out.append("REFUSE: the tree is not the bytes the census ran on -- nothing is committed")
        REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
        print("\n".join(out))
        return 6
    for repo_path, source in ENTRIES:
        if not source.exists():
            print("REFUSE: missing %s" % source)
            return 3
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        if INDEX.exists():
            INDEX.unlink()
        git("read-tree", "%s^{tree}" % TIP)
        for repo_path, source in ENTRIES:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        status = git("diff", "--name-status", TIP, tree).splitlines()
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        deleted = [line for line in status if line.startswith("D")]
        out += ["TREE=%s" % tree,
                "against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted))]
        out += ["ADDED %s" % p for p in added]
        out += ["MODIFIED %s" % p for p in modified]
        bad = [p for p in added + modified if not (p.startswith("review/") or p.startswith("frontend/e2e/"))]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a product path outside frontend/e2e/ -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = "\n".join([
            "ORD-0577 census: the bar answers on six screens and is silent on eleven, in both arms",
            "",
            "The order came with a premise measured on two screens (/v8/trash, /v8/stay). This branch",
            "widens it to the denominator the route tables themselves declare -- the union of",
            "desktopRoutes and mobileRoutes, read from source at run time, so a later screen cannot hide",
            "-- and reads the rendered bar on each: which button carries aria-current, which carries the",
            "contrast state, how many buttons are painted, and what the breadcrumb names.",
            "",
            "Found, identically in zh and en: 17 screens measured; 6 answered (hub, live->map, map,",
            "agent, trips, me); 11 silent (studio, stay, discover, import, bookings, footprints,",
            "authoritative, intelligence, twin, trash, access); the bar paints 5 buttons on every one of",
            "them, so the silence is a missing answer rather than a missing bar. The negative control",
            "also measured something the first version of this ruler got wrong: a route that names no",
            "screen is answered as Today with the address left alone, which is why the control now",
            "asserts on the shell's answer instead of on the URL.",
            "",
            "No fix is shipped. Each of the two shapes the order allows needs a ruling this lane does not",
            "own: attributing a screen to the nearest main route needs a screen-to-bar mapping the",
            "product carries nowhere machine-readable, and stating 'not on a main route' needs one new",
            "user-facing string. The measurement is what makes that ruling cheap.",
        ])
        commit = git("commit-tree", tree, "-p", TIP, "-m", message)
        out.append("COMMIT=%s" % commit)
        out.append(git("log", "-1", "--format=%h %ad %s", commit).replace("\n", " | "))
        if "--push" in sys.argv:
            out.append(git("update-ref", REF, commit) or "update-ref ok")
            pushed = subprocess.run(["git", "-C", REPO, "push", "--atomic", "origin", "%s:%s" % (commit, REF)],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            out.append("PUSH rc=%s %s" % (pushed.returncode, (pushed.stderr or "").strip()[:500]))
        else:
            out.append("PUSH=not requested (ref not written)")
    finally:
        if saved is None:
            os.environ.pop("GIT_INDEX_FILE", None)
        else:
            os.environ["GIT_INDEX_FILE"] = saved
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
