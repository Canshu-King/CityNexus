"""ORD-0512 r5：按令把基取到现尖、带上这一代族测读数成枝（产品字节零枚）。

为什么这枚枝里没有产品改动：令要的站名摆放路径已在现尖上逐枚相等（见读数件的 provenance 段），
再切一遍就是一枚空提交；令的同句要"重跑族测后推枝"，所以 r5 带的是那一份 —— 基 = 现尖、父 = 现尖、
新增只有族测读数与两把比较尺。`read-tree` 从尖起，故不可能删别人的路径；出现任何 `M`/`D` 即拒。

usage: python ord0512_commit_r5.py            (build and print)
       python ord0512_commit_r5.py --push     (writes the ref and pushes that one ref)
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TIP = os.environ.get("ORD0512_TIP") or "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"
REF = os.environ.get("ORD0512_REF") or "refs/heads/review/8ac89982-ord0512-stop-names-on-the-glass-r5"
INDEX = LANE / "run/ord0512_index_r5"
REPORT = pathlib.Path(os.environ.get("ORD0512_REPORT") or (LANE / "run/ord0512_commit_r5.txt"))

# The placement paths the order says to keep, re-read off the current tip: byte equality is the
# closure condition, so a re-cut of identical bytes would be an empty commit and is refused here too.
CARRY = {
    "frontend/src/components/v8/MapPanel.tsx": "1d6b1f2256b0cd9798d2cdd729f64075649cec86",
    "frontend/src/lib/mapStopLabels.ts": "27f09d52d1dc08fddbdd9ba2318163fd4aaa9ea6",
    "frontend/e2e/qoder-0512-stop-names-on-the-glass.spec.ts": "a349e7474618a128107c3cc4628040b97e360ae3",
}
EVIDENCE = [
    ("evidence/ord0512/family/ord0512fam_day35_r5.json", "review/ord0512/r5/family_day35_r5.json"),
    ("evidence/ord0512/gate/ord0512fam_day35_r5.log", "review/ord0512/r5/family_day35_r5.log"),
    ("run/_family_day35_r5.out", "review/ord0512/r5/family_stdout_r5.txt"),
    ("evidence/ord0512/family/diff_denom3_vs_day35_r5_fulltitles.txt",
     "review/ord0512/r5/family_diff_previous_vs_day35_r5.txt"),
    ("run/ord0512_family_fulltitle_r1.py", "review/ord0512/r5/family_fulltitle_comparator_r1.py"),
    ("run/ord0512_family_r1.py", "review/ord0512/r5/family_runner_r1.py"),
    ("run/ord0512_commit_r5.py", "review/ord0512/r5/commit_tool_r5.py"),
]

MESSAGE_LINES = [
    "ORD-0512 r5: cut onto the tip the sequencer can read, carrying this generation's family run --",
    "the placement bytes it asks to keep are already on that tip",
    "",
    "The order said: re-cut r5 on the current tip, keep only the stop-name placement path, re-run the",
    "family, push the branch. Ancestry is dead on this line (rebuilt root, no parents), so the landing",
    "test is byte equality; measured against the tip this branch is cut from, all three placement paths",
    "already match byte for byte (MapPanel, the rule module, the glass gate -- their blob ids are the",
    "same strings as the tip's own tree entries, recorded in the family reading's provenance file).",
    "Re-cutting identical bytes is an empty commit, so r5 carries what the order asks for next instead:",
    "the family, re-run on this generation.",
    "",
    "Family on this tip: 14 failed / 102 passed across the eighteen accepted map gates. Paired against",
    "the previous generation's run of the same family by whole-title multiset, the difference is",
    "accounted for in full rather than summarised: five arms appear that were not red before -- four",
    "widths of ORD-0403's reach arm, the family this lane measured as denominator movement (same bytes,",
    "different counts across repeated runs), and one arm of the hub gate that is red with its cause",
    "named and handed up as a finding; four arms disappear, and those are the pre-ruler hub arm names",
    "that moved when the ruler landed, whose three non-320 shapes did turn green. No arm is claimed",
    "fixed or broken here that was not read in both logs.",
    "",
    "Product bytes in this hand: zero. The branch adds readings, the family runner, the whole-title",
    "comparator and this tool under review/ord0512/r5/.",
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    if git("rev-parse", TIP) != TIP:
        print("REFUSE: the tip is not readable in this clone")
        return 2
    moved = []
    for path, expected in CARRY.items():
        on_tip = git("rev-parse", "%s:%s" % (TIP, path))
        if on_tip != expected:
            moved.append("%s tip=%s mine=%s" % (path, on_tip[:12], expected[:12]))
    if moved:
        print("REFUSE: the placement path is NOT on the tip, so this hand owes real bytes: %s" % moved)
        return 6
    missing = [LANE / source for source, _ in EVIDENCE if not (LANE / source).exists()]
    if missing:
        print("REFUSE: missing %s" % [str(path) for path in missing[:4]])
        return 3

    out = ["TIP=%s" % TIP, "REF=%s" % REF, "product_paths=0", "evidence_shipped=%d" % len(EVIDENCE),
           "carry_verified=%d" % len(CARRY)]
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        if INDEX.exists():
            INDEX.unlink()
        git("read-tree", "%s^{tree}" % TIP)
        for source, target in EVIDENCE:
            blob = git("hash-object", "-w", "--no-filters", str(LANE / source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, target))
        tree = git("write-tree")
        out.append("TREE=%s" % tree)
        status = git("diff", "--name-status", TIP, tree).splitlines()
        deleted = [line for line in status if line.startswith("D")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        out.append("against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted)))
        if deleted or modified:
            out += ["MODIFIED %s" % path for path in modified]
            out += ["DELETED %s" % line for line in deleted]
            out.append("REFUSE: r5 must add readings only -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        commit = git("commit-tree", tree, "-p", TIP, "-m", chr(10).join(MESSAGE_LINES))
        out.append("COMMIT=%s" % commit)
        out.append(git("log", "-1", "--format=%h %ad %s", commit).replace("\n", " | "))
        if "--push" in sys.argv:
            out.append(git("update-ref", REF, commit) or "update-ref ok")
            pushed = subprocess.run(["git", "-C", REPO, "push", "--atomic", "origin", "%s:%s" % (commit, REF)],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            out.append("PUSH rc=%s %s" % (pushed.returncode, (pushed.stderr or "").strip()[:600]))
        else:
            out.append("PUSH=not requested (ref not written)")
    finally:
        if saved is None:
            os.environ.pop("GIT_INDEX_FILE", None)
        else:
            os.environ["GIT_INDEX_FILE"] = saved
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out[:12]))
    print("wrote %s (%d lines)" % (REPORT, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
