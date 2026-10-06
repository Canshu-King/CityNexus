"""ORD-0573 copy-table hand: the four trips section labels move out of inline literals into the
per-surface copy table, verbatim. Zero new words on the glass; the module is a new file under src/i18n,
the shell edit is small, and both gates ran green/red on the same bytes.

Parent is the tip read live; hard gates refuse unless the tip carries the base bytes the counter ran on
and the tree is the bytes the gate ran on.

usage: python ord0573_copy_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0573-sections-copy-table-r1"
INDEX = LANE / "run/ord0573_copy_index"
REPORT = LANE / "run/ord0573_copy_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
COPY_REL = "frontend/src/i18n/tripSectionsCopy.ts"
BASE_BLOB = "4fece5054beef7ab90ea6544cfaf1ce7ad720050"
FIXED_BLOB = "4e2fee73e27a7335e7e7f8b1621f9f6f4dc1086d"
SPEC = "frontend/e2e/qoder-8ac89982-ord0573-sections-copy-r1.spec.ts"
BASE_ZH = "frontend/e2e/ord0573_sections_baseline_zh.json"
BASE_EN = "frontend/e2e/ord0573_sections_baseline_en.json"
ENTRIES = [
    (SHELL_REL, TREE / SHELL_REL),
    (COPY_REL, TREE / COPY_REL),
    (SPEC, TREE / SPEC),
    (BASE_ZH, TREE / BASE_ZH),
    (BASE_EN, TREE / BASE_EN),
    ("review/ord0573/copy/gate_stdout_r1.txt", LANE / "run/_ord0573_copy_gate.out"),
    ("review/ord0573/copy/counter_example_r1.txt", LANE / "run/_ord0573_copy_counter.out"),
    ("review/ord0573/copy/typecheck_r1.txt", LANE / "run/_ord0573_copy_tsc.out"),
    ("review/ord0573/copy/readings_zh.json", LANE / "evidence/ord0512/e2e/ord0573_sections_zh.json"),
    ("review/ord0573/copy/readings_en.json", LANE / "evidence/ord0512/e2e/ord0573_sections_en.json"),
    ("review/ord0573/copy/pair_tool_r1.sh", LANE / "run/_ord0573_copy_pair_r1.sh"),
    ("review/ord0573/copy/commit_tool_r1.py", LANE / "run/ord0573_copy_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0573_COPY_TIP") or git(
        "ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    tip_shell = git("rev-parse", "%s:%s" % (tip, SHELL_REL))
    tree_shell = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % tip, "REF=%s" % REF, "tip_shell_blob=%s" % tip_shell, "tree_shell_blob=%s" % tree_shell]
    if tip_shell != BASE_BLOB:
        out.append("REFUSE: the tip no longer carries the bytes the counter ran on -- nothing is committed")
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
            "ORD-0573 (the copy half): the four trips section labels read from the surface's own table",
            "",
            "The labels were inline bilingual literals in the shell, rendered by a `{zh ? item.zh : item.en}`",
            "ternary over a local array. They now come from `i18n/tripSectionsCopy.ts` -- a per-surface copy",
            "table, the same shape `mapPanelCopy.ts` already is. It is verbatim: the words the traveller",
            "reads do not change; only where they are written moved.",
            "",
            "Why this file and not the shared dictionary: the nearest existing keys say different words",
            "(`nav.stay` reads \"Stay Explorer\" / 「住宿选择」 while this tab reads \"Stay\" / 「住宿」), so",
            "reusing them would have changed the glass; and the shared dictionary is being edited by other",
            "lanes, which is the reason every other surface keeps its own table here.",
            "",
            "The gate proves three things: the four words are byte-identical on screen in both arms against",
            "the readings taken before this hand; the roles from the earlier hand (tablist, tab, aria-selected",
            "and the moving selection) still hold; and the inline tab rows are gone from the shell -- that",
            "source arm is what reddens on the tip's own bytes, which is where its teeth are. typecheck:all",
            "exits zero.",
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