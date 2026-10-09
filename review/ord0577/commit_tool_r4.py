"""ORD-0577 gap width: how wide is the missing-entry gap. Zero product bytes.

usage: python ord0577_gapwidth_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0577-entry-gap-width-r1"
INDEX = LANE / "run/ord0577_gapwidth_index"
REPORT = LANE / "run/ord0577_gapwidth_commit_r1.txt"
SPEC = "frontend/e2e/qoder-8ac89982-ord0577-entry-gap-width-r1.spec.ts"
ENTRIES = [
    (SPEC, TREE / SPEC),
    ("review/ord0577/gap_width_zh.json", LANE / "evidence/ord0512/e2e/ord0577_gap_width_zh.json"),
    ("review/ord0577/gap_width_en.json", LANE / "evidence/ord0512/e2e/ord0577_gap_width_en.json"),
    ("review/ord0577/gate_stdout_gapwidth_r1.txt", LANE / "run/_ord0577_gapwidth_r1.out"),
    ("review/ord0577/commit_tool_r4.py", LANE / "run/ord0577_gapwidth_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0577_GAPWIDTH_TIP") or git(
        "ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    out = ["TIP=%s" % tip, "REF=%s" % REF]
    for repo_path, source in ENTRIES:
        if not source.exists():
            print("REFUSE: missing %s" % source)
            return 3
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        if INDEX.exists():
            INDEX.unlink()
        git("read-tree", "%s^{tree}" % tip)
        for repo_path, source in ENTRIES:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        status = git("diff", "--name-status", tip, tree).splitlines()
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        deleted = [line for line in status if line.startswith("D")]
        out += ["TREE=%s" % tree,
                "against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted))]
        out += ["ADDED %s" % p for p in added]
        bad = [p for p in added + modified if not (p.startswith("review/") or p.startswith("frontend/e2e/"))]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a product path -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = "\n".join([
            "ORD-0577: the missing-entry gap starts exactly at the breakpoint and holds above it",
            "",
            "At desktop width the sidebar lists the fifteen desktop routes while the bottom bar and the",
            "drawer's door are hidden by the stylesheet, so the two screens that exist only in the mobile",
            "table -- trips and me -- have no clickable entry at all. This branch measures how wide that gap",
            "is rather than only noting that it exists at one width.",
            "",
            "Five widths were read in both locales (390, 680, 681, 900, 1280), and the breakpoint is read",
            "out of styles.css at run time -- the query that actually turns .v8-mobile-menu on -- rather",
            "than written down here. Result, identical in zh and en: at 390 and 680 the sidebar is hidden and",
            "the bar and the door are shown, so both screens are reachable; from 681 upward the sidebar is",
            "shown with fifteen rows and the bar and the door are hidden, so those two screens have no entry",
            "at every width probed.",
            "",
            "The phone-width and desktop-width ends are asserted inside the ruler, so the 'shown' columns",
            "are proven to move rather than to sit at a constant. No product bytes: the only file outside",
            "review/ is the ruler itself.",
        ])
        commit = git("commit-tree", tree, "-p", tip, "-m", message)
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