"""ORD-0577 recut onto the current tip: one branch carrying both hands (bar + drawer/sidebar).

Why one branch: the parent must be the tip read live, and the tip still carries neither hand, so a tree
that holds both is the only way to offer the whole cell on this generation. It supersedes
review/8ac89982-ord0577-bar-says-where-r1 and review/8ac89982-ord0577-layers-say-where-r1; land one.

Hard gates: the tip must still carry the base bytes the counters ran on, and the tree must be the bytes
the gates ran on.

usage: python ord0577_recut_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0577-bar-and-layers-say-where-r2"
INDEX = LANE / "run/ord0577_recut_index"
REPORT = LANE / "run/ord0577_recut_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
BASE_BLOB = "4fece5054beef7ab90ea6544cfaf1ce7ad720050"
FIXED_BLOB = "1f449899e0899dfed2ae46ab0cb2b3c114898b44"
BAR_SPEC = "frontend/e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts"
LAYERS_SPEC = "frontend/e2e/qoder-8ac89982-ord0577-layers-say-where-r1.spec.ts"
CAPTURE = "frontend/e2e/qoder-8ac89982-ord0577-layers-baseline-r1.spec.ts"
BAR_BASE_ZH = "frontend/e2e/ord0577_bar_texts_baseline_zh.json"
BAR_BASE_EN = "frontend/e2e/ord0577_bar_texts_baseline_en.json"
LAYERS_BASE_ZH = "frontend/e2e/ord0577_layers_baseline_zh.json"
LAYERS_BASE_EN = "frontend/e2e/ord0577_layers_baseline_en.json"
ENTRIES = [
    (SHELL_REL, TREE / SHELL_REL),
    (BAR_SPEC, TREE / BAR_SPEC),
    (LAYERS_SPEC, TREE / LAYERS_SPEC),
    (CAPTURE, TREE / CAPTURE),
    (BAR_BASE_ZH, TREE / BAR_BASE_ZH),
    (BAR_BASE_EN, TREE / BAR_BASE_EN),
    (LAYERS_BASE_ZH, TREE / LAYERS_BASE_ZH),
    (LAYERS_BASE_EN, TREE / LAYERS_BASE_EN),
    ("review/ord0577/r2/bar_gate_r1.txt", LANE / "run/_ord0577_recut_bar_gate.out"),
    ("review/ord0577/r2/bar_counter_r1.txt", LANE / "run/_ord0577_recut_bar_counter.out"),
    ("review/ord0577/r2/layers_gate_r1.txt", LANE / "run/_ord0577_recut_layers_gate.out"),
    ("review/ord0577/r2/layers_counter_r1.txt", LANE / "run/_ord0577_recut_layers_counter.out"),
    ("review/ord0577/r2/typecheck_r1.txt", LANE / "run/_ord0577_recut_tsc.out"),
    ("review/ord0577/r2/bar_readings_zh.json", LANE / "evidence/ord0512/e2e/ord0577_fixed_zh.json"),
    ("review/ord0577/r2/bar_readings_en.json", LANE / "evidence/ord0512/e2e/ord0577_fixed_en.json"),
    ("review/ord0577/r2/layers_readings_zh.json", LANE / "evidence/ord0512/e2e/ord0577_layers_fixed_zh.json"),
    ("review/ord0577/r2/layers_readings_en.json", LANE / "evidence/ord0512/e2e/ord0577_layers_fixed_en.json"),
    ("review/ord0577/r2/pair_tool_r1.sh", LANE / "run/_ord0577_recut_r1.sh"),
    ("review/ord0577/r2/commit_tool_r1.py", LANE / "run/ord0577_recut_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0577_RECUT_TIP") or git(
        "ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    tip_shell = git("rev-parse", "%s:%s" % (tip, SHELL_REL))
    tree_shell = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % tip, "REF=%s" % REF, "tip_shell_blob=%s" % tip_shell, "tree_shell_blob=%s" % tree_shell]
    if tip_shell != BASE_BLOB:
        out.append("REFUSE: the tip no longer carries the bytes the counters ran on -- nothing is committed")
        REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
        print("\n".join(out))
        return 6
    if tree_shell != FIXED_BLOB:
        out.append("REFUSE: the tree is not the bytes the gates ran on -- nothing is committed")
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
        out.append("shell_file_numstat=%s/%s" % (numstat[0], numstat[1].strip()))
        message = "\n".join([
            "ORD-0577 recut on the current tip: the bar, the drawer and the sidebar all say where you are",
            "",
            "The same two hands as before, re-cut because another lane rewrote the shell file's comments and",
            "the earlier branches no longer sit on the tip. Both gates and both counters were re-run on this",
            "generation: green with these bytes, red with the tip's own bytes and the gate untouched.",
            "",
            "Hand one -- the bottom bar answers on every screen. On its own routes a button keeps its",
            "aria-current; on the other eleven screens the bar carries aria-describedby pointing at the name",
            "the breadcrumb already paints. The two answers are exclusive: never both, never neither. The",
            "order offered attributing such a screen to a nearest main route; that needs a mapping the",
            "product carries nowhere and would make the bar claim a screen the traveller is not on.",
            "",
            "Hand two -- the phone drawer and the desktop sidebar give the row that already carries .active",
            "an aria-current=\"page\": the drawer on all seventeen screens, the sidebar on the fifteen it has",
            "a row for. The spoken mark must be the same row that is painted, asserted screen by screen, so",
            "the two cannot drift apart later.",
            "",
            "No new copy anywhere: both hands reuse names already on the glass, so no dictionary key and no",
            "per-screen copy module is needed, and nothing visible moves -- the words of the bar, the drawer",
            "and the sidebar are compared screen by screen against baselines captured on unmodified bytes,",
            "which ship here as fixtures. typecheck:all exits zero.",
            "",
            "Supersedes review/8ac89982-ord0577-bar-says-where-r1 and",
            "review/8ac89982-ord0577-layers-say-where-r1. Land this one, not those.",
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
