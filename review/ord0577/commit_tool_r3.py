"""ORD-0577 desktop entries census: ship the instrument and its readings (zero product bytes).

usage: python ord0577_desktop_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0577-desktop-entries-census-r1"
INDEX = LANE / "run/ord0577_desktop_index"
REPORT = LANE / "run/ord0577_desktop_commit_r1.txt"
SPEC = "frontend/e2e/qoder-8ac89982-ord0577-desktop-entries-census-r1.spec.ts"
ENTRIES = [
    (SPEC, TREE / SPEC),
    ("review/ord0577/desktop_entries_zh.json", LANE / "evidence/ord0512/e2e/ord0577_desktop_entries_zh.json"),
    ("review/ord0577/desktop_entries_en.json", LANE / "evidence/ord0512/e2e/ord0577_desktop_entries_en.json"),
    ("review/ord0577/gate_stdout_desktop_r1.txt", LANE / "run/_ord0577_desktop_r1.out"),
    ("review/ord0577/desktop_entries_provenance_r1.txt", LANE / "run/_ord0577_desktop_provenance.txt"),
    ("review/ord0577/commit_tool_r3.py", LANE / "run/ord0577_desktop_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0577_DESKTOP_TIP") or git(
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
        out += ["MODIFIED %s" % p for p in modified]
        bad = [p for p in added + modified if not (p.startswith("review/") or p.startswith("frontend/e2e/"))]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a product path -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = "\n".join([
            "ORD-0577 census: at desktop width, two of the seventeen screens have no chrome entry at all",
            "",
            "The two-layer census noted an incomplete list -- the desktop sidebar iterates desktopRoutes",
            "only -- and this branch makes that concrete at 1280x900. Measured on all seventeen screens, in",
            "both locales: the sidebar is shown and has 15 rows (the desktop table's size, read from source",
            "at run time), while the bottom bar and the drawer's door are hidden on every screen, since",
            "styles.css keeps them at display:none above 680px.",
            "",
            "So the two screens that exist only in the mobile table -- trips and me -- have no clickable",
            "entry at desktop width; their breadcrumbs still paint their names, so the screens are real and",
            "reachable by address alone. The phone-width control reads the other way round on every screen",
            "(sidebar hidden, bar and door shown), which is what makes the 'shown' column a measurement.",
            "",
            "No fix ships: giving those two screens a row means changing what the desktop nav is made of --",
            "and the drawer is built from the same table -- so it is a design decision. Two shapes are named",
            "in the lane's block for the commander to choose between.",
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
