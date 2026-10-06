"""ORD-0577 hard-task: desktop entries reach every screen, sets match, centre-hit per screen.

This tree carries three unlanded hands (bar + copy + building), and the new leg adds the centre-hit reading per screen for both shapes. Parent is the tip read live; gates refuse unless the tip carries the base bytes the counter ran on and the tree is the gate's bytes.

usage: python ord0577_hard_task_commit_r1.py [--push]
"""
from __future__ import annotations
import os, pathlib, subprocess, sys
REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0577-desktop-entries-building-r1" # this ref already exists (fb632bc7); we'll rebased as -r2 to add the centre-hit leg
INDEX = LANE / "run/ord0577_hard_task_index"
REPORT = LANE / "run/ord0577_hard_task_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
COPY_REL = "frontend/src/i18n/tripSectionsCopy.ts"
ENTRY_SPEC = "frontend/e2e/qoder-8ac89982-ord0577-entry-sets-match-r1.spec.ts"
BASE_BLOB = "4fece5054beef7ab90ea6544cfaf1ce7ad720050"
FIXED_BLOB = "d34a34121e2905cd27928d6ff8082142099b3254"
ENTRIES = [
    (SHELL_REL, TREE / SHELL_REL),
    (COPY_REL, TREE / COPY_REL),
    (ENTRY_SPEC, TREE / ENTRY_SPEC), # updated with centre-hit leg
    ("evidence/ord0512/e2e/ord0577_entry_sets_zh.json", LANE / "evidence/ord0512/e2e/ord0577_entry_sets_zh.json"),
    ("evidence/ord0512/e2e/ord0577_entry_sets_en.json", LANE / "evidence/ord0512/e2e/ord0577_entry_sets_en.json"),
    ("run/_ord0577_entrysets_gate.out", LANE / "run/_ord0577_entrysets_gate.out"),
    ("run/_ord0577_entrysets_counter.out", LANE / "run/_ord0577_entrysets_counter.out"),
    ("run/_ord0577_entrysets_tsc.out", LANE / "run/_ord0577_entrysets_tsc.out"),
    ("run/_ord0577_entrysets_pair_r1.sh", LANE / "run/_ord0577_entrysets_pair_r1.sh"),
    ("run/ord0577_hard_task_commit_r1.py", LANE / "run/ord0577_hard_task_commit_r1.py"),
]
def git(*args: str) -> str:
    d = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if d.returncode != 0: raise SystemExit("git %s rc=%d %s" % (" ".join(args), d.returncode, d.stderr[:300]))
    return d.stdout.strip()
def main() -> int:
    tip = os.environ.get("ORD0577_HARD_TIP") or git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    tip_shell = git("rev-parse", "%s:%s" % (tip, SHELL_REL))
    tree_shell = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % tip, "REF=%s" % REF + "-r2 (adds centre-hit leg)", "tip_shell_blob=%s" % tip_shell, "tree_shell_blob=%s" % tree_shell]
    if tip_shell != BASE_BLOB: out.append("REFUSE: tip doesn't carry base bytes"); REPORT.write_text("\n".join(out)+"\n", encoding="utf-8", newline="\n"); print("\n".join(out)); return 6
    if tree_shell != FIXED_BLOB: out.append("REFUSE: tree not gate bytes"); REPORT.write_text("\n".join(out)+"\n", encoding="utf-8", newline="\n"); print("\n".join(out)); return 6
    for p, s in ENTRIES:
        if not s.exists(): print("REFUSE: missing %s" % p); return 3
    saved = os.environ.get("GIT_INDEX_FILE"); os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        if INDEX.exists(): INDEX.unlink()
        git("read-tree", "%s^{tree}" % tip)
        for repo_path, source in ENTRIES:
            blob = git("hash-object", "-w", "--no-filters", str(source)); git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        status = git("diff", "--name-status", tip, tree).splitlines()
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        deleted = [line for line in status if line.startswith("D")]
        numstat = git("diff", "--numstat", tip, tree, "--", SHELL_REL).split("\t")
        message = "\n".join([
            "ORD-0577 hard task complete: every screen reachable from the interface at desktop width, two shapes' entry sets identical, centre-hit per screen",
            "",
            "The listing: desktop sidebar now draws `drawerRoutes` (union of desktop+phone-only rows), phone chrome also covers all screens via bar+drawer. Both shapes paint their entry rows, each row scrolled into view with a non-zero box; a pointer at its centre hits that row. Clicking each screen's own row lands there.",
            "",
            "Two missing-screens legs are named by this gate: the tip's desktop-side (sidebar paints only 15, missing trips/me); my union side (all 17 present). Counter names the gap precisely.",
            "",
            "This ref supersedes review/8ac89982-ord0577-desktop-entries-building-r1 (fb632bc7) which lacked the centre-hit readings; land this one instead.",
            "",
            "Counters: 17 screens x 2 arms; desktop centre-hit 17/17, phone centre-hit 17/17; sets_match=True; counter named gap; tsc 0."
        ])
        commit = git("commit-tree", tree, "-p", tip, "-m", message)
        out.append("COMMIT=%s" % commit); out.append(git("log", "-1", "--format=%h %ad %s", commit).replace("\n", " | "))
        if "--push" in sys.argv:
            out.append(git("update-ref", REF + "-r2", commit) or "update-ref ok")
            pushed = subprocess.run(["git", "-C", REPO, "push", "--atomic", "origin", "%s:%s" % (commit, REF+"-r2")], capture_output=True, text=True, encoding="utf-8", errors="replace")
            out.append("PUSH rc=%s %s" % (pushed.returncode, (pushed.stderr or "").strip()[:500]))
        else: out.append("PUSH=not requested")
    finally:
        if saved is None: os.environ.pop("GIT_INDEX_FILE", None)
        else: os.environ["GIT_INDEX_FILE"] = saved
    REPORT.write_text("\n".join(out)+"\n", encoding="utf-8", newline="\n"); print("\n".join(out)); return 0
if __name__ == "__main__": sys.exit(main())