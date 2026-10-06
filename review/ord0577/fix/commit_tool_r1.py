"""ORD-0577 fix: the bottom bar answers on every screen -- by a current button on its own routes, by
pointing at the screen's own name everywhere else. Zero new copy, no visible word moved.

Parent is the tip read live at build time; the tree is the tip's tree with this hand's paths overlaid.
A hard gate refuses the commit unless the tip's copy of the shell file is the pre-fix bytes the counter
run used, so a tip that moved under me cannot be silently overlaid.

usage: python ord0577_fix_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0577-bar-says-where-r1"
INDEX = LANE / "run/ord0577_fix_index"
REPORT = LANE / "run/ord0577_fix_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
PREFIX_BLOB = "5d62f7bc78a58369d871a37c820e0b9a1a6076e6"
FIXED_BLOB = "2f0c4a8a92bf70e02309c886afe4e21869f5ca49"
SPEC = "frontend/e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts"
BASE_ZH = "frontend/e2e/ord0577_bar_texts_baseline_zh.json"
BASE_EN = "frontend/e2e/ord0577_bar_texts_baseline_en.json"
ENTRIES = [
    (SHELL_REL, TREE / SHELL_REL),
    (SPEC, TREE / SPEC),
    (BASE_ZH, TREE / BASE_ZH),
    (BASE_EN, TREE / BASE_EN),
    ("review/ord0577/fix/gate_stdout_r1.txt", LANE / "run/_ord0577_fixed_gate.out"),
    ("review/ord0577/fix/counter_example_r1.txt", LANE / "run/_ord0577_fixed_counter.out"),
    ("review/ord0577/fix/typecheck_r1.txt", LANE / "run/_ord0577_fixed_tsc.out"),
    ("review/ord0577/fix/readings_zh.json", LANE / "evidence/ord0512/e2e/ord0577_fixed_zh.json"),
    ("review/ord0577/fix/readings_en.json", LANE / "evidence/ord0512/e2e/ord0577_fixed_en.json"),
    ("review/ord0577/fix/pair_tool_r1.sh", LANE / "run/_ord0577_fix_pair_r1.sh"),
    ("review/ord0577/fix/commit_tool_r1.py", LANE / "run/ord0577_fix_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0577_FIX_TIP") or git(
        "ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    # No fetch here on purpose: other lanes share this repository and a concurrent fetch/push there
    # holds .git/shallow.lock, so the fetch is done by the caller and this only checks presence.
    git("cat-file", "-e", "%s^{commit}" % tip)
    tip_shell = git("rev-parse", "%s:%s" % (tip, SHELL_REL))
    tree_shell = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % tip, "REF=%s" % REF, "tip_shell_blob=%s" % tip_shell,
           "tree_shell_blob=%s" % tree_shell, "prefix_blob=%s" % PREFIX_BLOB, "fixed_blob=%s" % FIXED_BLOB]
    if tip_shell != PREFIX_BLOB:
        out.append("REFUSE: the tip no longer carries the pre-fix shell bytes the counter ran on -- nothing is committed")
        REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
        print("\n".join(out))
        return 6
    if tree_shell != FIXED_BLOB:
        out.append("REFUSE: the tree is not the fixed bytes the gate ran on -- nothing is committed")
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
        allowed = ("review/", "frontend/e2e/", SHELL_REL)
        bad = [p for p in added + modified if not p.startswith(allowed)]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a path outside this hand -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        numstat = git("diff", "--numstat", tip, tree, "--", SHELL_REL).split("\t")
        out.append("shell_file_numstat=%s/%s" % (numstat[0], numstat[1]))
        message = "\n".join([
            "ORD-0577: the bottom bar answers on every screen, and no visible word moved",
            "",
            "The census measured the bar answering on six of the seventeen declared screens and saying",
            "nothing on eleven, and a second census showed the phone drawer already marks the current",
            "screen on all seventeen -- by class only, with no aria-current anywhere in the chrome except",
            "those six bar buttons. So the bar had a truthful answer available and did not use it.",
            "",
            "This hand makes it use it, without inventing anything: on a screen outside the bar's own",
            "routes, the bar carries aria-describedby pointing at the name the breadcrumb already paints",
            "(the same element that names the screen for every declared route), and on its own routes it",
            "keeps the aria-current it already had. The two answers are exclusive -- never both, and now",
            "never neither. The order offered attributing such a screen to a nearest main route instead;",
            "that would need a screen-to-bar mapping the product carries nowhere, and would make the bar",
            "claim a screen the traveller is not on, so the naming answer is the one shipped.",
            "",
            "No new copy: the pointer reuses the screen name already on the glass, so no dictionary key and",
            "no per-screen copy module is needed, and no visible text changes -- the gate compares the",
            "bar's five words on all seventeen screens against the census readings taken before this hand",
            "(shipped here as fixtures), and compares the screen's own name too.",
            "",
            "Counters: with these bytes the gate is green in both locales (six screens answered by a",
            "current button, eleven by the pointer, negative control still answered as Today with no",
            "pointer). With the shell reverted to the tip's own bytes and the gate untouched, it is red at",
            "the first silent screen -- 'the bar answers nothing here'. typecheck:all exits zero.",
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
