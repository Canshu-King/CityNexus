"""ORD-0577 building 1: every screen is reachable in both shapes, and the two shapes agree.

This tree carries three unlanded hands, because the authority line still holds none of them:
  - the bar hand (bar answers on every screen; drawer and sidebar get aria-current);
  - the copy hand (the four trips section labels read from the surface's copy table);
  - this one: the desktop sidebar draws the same union the drawer draws, so the two shapes cannot end
    up with different entry sets -- two screens (trips, me) used to exist on the phone bar only and
    were reachable at desktop width by nothing but a typed address.

Parent is the tip read live; hard gates refuse unless the tip carries the base bytes the counter ran on
and the tree is the bytes the gate ran on. Land this one; it supersedes review/…-bar-and-layers-say-where-r2
and review/…-ord0573-sections-copy-table-r1.

usage: python ord0577_building_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0577-desktop-entries-building-r1"
INDEX = LANE / "run/ord0577_building_index"
REPORT = LANE / "run/ord0577_building_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
COPY_REL = "frontend/src/i18n/tripSectionsCopy.ts"
BASE_BLOB = "4fece5054beef7ab90ea6544cfaf1ce7ad720050"
FIXED_BLOB = "d34a34121e2905cd27928d6ff8082142099b3254"
ENTRY_SPEC = "frontend/e2e/qoder-8ac89982-ord0577-entry-sets-match-r1.spec.ts"
ENTRIES = [
    (SHELL_REL, TREE / SHELL_REL),
    (COPY_REL, TREE / COPY_REL),
    (ENTRY_SPEC, TREE / ENTRY_SPEC),
    ("review/ord0577/building/gate_stdout_r1.txt", LANE / "run/_ord0577_entrysets_gate.out"),
    ("review/ord0577/building/counter_names_the_gap_r1.txt", LANE / "run/_ord0577_entrysets_counter.out"),
    ("review/ord0577/building/typecheck_r1.txt", LANE / "run/_ord0577_entrysets_tsc.out"),
    ("review/ord0577/building/entry_sets_zh.json", LANE / "evidence/ord0512/e2e/ord0577_entry_sets_zh.json"),
    ("review/ord0577/building/entry_sets_en.json", LANE / "evidence/ord0512/e2e/ord0577_entry_sets_en.json"),
    ("review/ord0577/building/pair_tool_r1.sh", LANE / "run/_ord0577_entrysets_pair_r1.sh"),
    ("review/ord0577/building/commit_tool_r1.py", LANE / "run/ord0577_building_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0577_BUILDING_TIP") or git(
        "ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    tip_shell = git("rev-parse", "%s:%s" % (tip, SHELL_REL))
    tree_shell = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % tip, "REF=%s" % REF, "tip_shell_blob=%s" % tip_shell, "tree_shell_blob=%s" % tree_shell]
    if tip_shell != BASE_BLOB:
        out.append("REFUSE: the tip no longer carries the base bytes the counter ran on -- nothing is committed")
        REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
        print("\n".join(out))
        return 6
    if tree_shell != FIXED_BLOB:
        out.append("REFUSE: the tree is not the bytes the gate ran on -- nothing is committed")
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
        allowed = ("review/", "frontend/e2e/", SHELL_REL, COPY_REL)
        bad = [p for p in added + modified if not p.startswith(allowed)]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a path outside this hand -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        numstat = git("diff", "--numstat", tip, tree, "--", SHELL_REL).split("\t")
        out.append("shell_file_numstat=%s/%s" % (numstat[0], numstat[1].strip()))
        message = "\n".join([
            "ORD-0577 building: the desktop nav reaches every screen, and both shapes agree",
            "",
            "Two screens (trips, me) existed on the phone bar only. At desktop width the bottom bar and the",
            "drawer's door are hidden by the stylesheet and the sidebar listed only desktopRoutes, so those",
            "two screens had no clickable entry anywhere -- reachable only by a typed address. The desktop",
            "sidebar now draws the same union the drawer draws, so the two shapes cannot drift into different",
            "entry sets; a row without a `group` is titled `nav.groupOther`, exactly as the drawer titles it,",
            "and the words are `nav.<key>`, which both arms already carry.",
            "",
            "Measured by the new gate in both locales at 1280x900 and 390x844, screen by screen, from the",
            "route tables' union read at run time: all 17 screens have a desktop sidebar entry with a painted",
            "box and a phone entry, and clicking each screen's own sidebar row moves the address there (the",
            "interface door, not a deep link). The entry sets match with nothing missing on either side. The",
            "negative control -- an address naming no screen -- is still answered as Today on both shapes, so",
            "the 'it answered' columns are proven to move. On the tip's own bytes the same gate goes red and",
            "NAMES the gap: the desktop sidebar is missing trips and me, painting 15 of 17. typecheck:all is",
            "clean.",
            "",
            "This tree also carries the bar hand and the copy hand, which the line still does not hold. It",
            "supersedes review/8ac89982-ord0577-bar-and-layers-say-where-r2 and",
            "review/8ac89982-ord0573-sections-copy-table-r1. Land this one.",
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