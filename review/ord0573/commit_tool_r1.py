"""ORD-0573（角色那半）：组装候选提交（默认只打印，不写 ref）。

形制：父 = 现读尖；树从尖的树起，只盖这一手动过的路径；`diff --name-status` 出现 `D`、或 `M` 里
出现这枚之外的路径，整枚拒。

一处自检写成硬话：这手只该带 tab 角色那几行。若提交时现尖还没收下 ORD-0572，那枚外壳文件里就会
同时带着上一手的九行 —— 那是叠枝，不是偷偷做的事，脚本会把这件事原样写进提交语与回执里，
让我没法把两手混成一手的读数报出去。

usage: python ord0573_commit_r1.py            (build and print)
       python ord0573_commit_r1.py --push     (writes the new ref and pushes that one ref)
"""
from __future__ import annotations

import glob
import hashlib
import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
TIP = os.environ.get("ORD0573_TIP") or ""
REF = os.environ.get("ORD0573_REF") or "refs/heads/review/8ac89982-ord0573-trip-sections-say-which-one-r1"
INDEX = LANE / "run/ord0573_index"
REPORT = pathlib.Path(os.environ.get("ORD0573_REPORT") or (LANE / "run/ord0573_commit_r1.txt"))

REL = "frontend/src/app/V8Experience.tsx"
SPEC = "frontend/e2e/qoder-8ac89982-ord0573-trips-tab-roles.spec.ts"
COST_SPEC = "frontend/e2e/qoder-8ac89982-ord0573-upstream-locator-forms-r1.spec.ts"
BLOB_WITH_0572_ONLY = "62aa8b83c35a5d408170bc2ad4470ae70e78a136"
LOGS = [
    ("run/_ord0573_gate.out", "review/ord0573/gate_stdout_r1.txt"),
    ("run/_ord0573_counter.out", "review/ord0573/counter_example_r1.txt"),
    ("run/_ord0572_recheck.out", "review/ord0573/previous_cell_recheck_r1.txt"),
    ("run/_ord0573_typecheck.out", "review/ord0573/typecheck_r1.txt"),
    ("run/_ord0573cost_in.out", "review/ord0573/cost_stdout_roles_in_r1.txt"),
    ("run/_ord0573cost_out.out", "review/ord0573/cost_stdout_roles_out_r1.txt"),
    ("run/_ord0573_v9rolesout_r1.out", "review/ord0573/upstream_v9_on_tip_bytes_r1.txt"),
    ("run/_ord0573cost_pair_r2.sh", "review/ord0573/cost_pair_tool_r1.sh"),
    ("evidence/ord0512/gate/ord0573_r1.log", "review/ord0573/gate_full_log_r1.log"),
    ("run/ord0573_commit_r1.py", "review/ord0573/commit_tool_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def blob_id(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def main() -> int:
    tip = TIP or git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    tip_rel = git("rev-parse", "%s:%s" % (tip, REL))
    stacked = tip_rel != BLOB_WITH_0572_ONLY
    entries = [(REL, TREE / REL), (SPEC, TREE / SPEC), (COST_SPEC, TREE / COST_SPEC)]
    readings = sorted(glob.glob(str(LANE / "evidence/ord0512/e2e/ord0573_*.json")))
    cost_readings = sorted(glob.glob(str(LANE / "evidence/ord0512/e2e/ord0573cost_roles_*.json")))
    if len(readings) != 2:
        print("REFUSE: expected two gate readings, found %d" % len(readings))
        return 3
    if len(cost_readings) != 4:
        print("REFUSE: expected four cost-ruler readings (two generations x two locales), found %d" % len(cost_readings))
        return 3
    for path in readings:
        entries.append(("review/ord0573/readings/" + pathlib.Path(path).name, pathlib.Path(path)))
    for path in cost_readings:
        entries.append(("review/ord0573/cost/" + pathlib.Path(path).name, pathlib.Path(path)))
    for source, target in LOGS:
        entries.append((target, LANE / source))

    out = ["TIP=%s" % tip, "REF=%s" % REF, "tip_shell_blob=%s" % tip_rel,
           "stacked_on_previous_hand=%s" % stacked, "readings=%d" % len(readings),
           "cost_readings=%d" % len(cost_readings)]
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        if INDEX.exists():
            INDEX.unlink()
        git("read-tree", "%s^{tree}" % tip)
        for repo_path, source in entries:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        out.append("TREE=%s" % tree)
        status = git("diff", "--name-status", tip, tree).splitlines()
        deleted = [line for line in status if line.startswith("D")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        out.append("against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted)))
        out += ["MODIFIED %s" % path for path in modified]
        out += ["ADDED %s" % path for path in added if not path.startswith("review/")]
        if deleted:
            out.append("REFUSE: this tree drops paths the tip carries -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        if blob_id((TREE / REL).read_bytes()) == tip_rel:
            out.append("REFUSE: the shell file is byte-identical to the tip -- this hand changed nothing")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 5
        lines = git("diff", "--numstat", tip, tree, "--", REL).split("\t")
        out.append("shell_file_numstat=%s/%s" % (lines[0].strip(), lines[1].strip()))
        message = [
            "ORD-0573 (the roles half): the four trip sections now say which one is open, and no word moved",
            "",
            "The order paired two things; this hand ships only the one that needs no decision from anyone:",
            "`role=\"tablist\"` on the section bar, and `role=\"tab\"` with `aria-selected` and a stable id on",
            "each of the four. A traveller using a screen reader heard four buttons and a class-driven look;",
            "now one of them says out loud that it is the section on screen, and tapping another moves that",
            "fact with it -- which is what the new gate drives, rather than reading a static first render.",
            "",
            "Deliberately not done here, and named rather than quietly dropped: `aria-controls` and the",
            "panel-side `role=\"tabpanel\"` need a wrapper element, which changes the DOM tree on a screen",
            "the map family's geometry arms judge. Adding a dangling `aria-controls` to a non-existent id",
            "would be an accessibility claim that points at nothing, so the attribute waits for the wrapper",
            "and for a family re-run that measures the wrapper's cost.",
            "",
            "The words on the four tabs are untouched: this tip's labels still come from the inline",
            "bilingual array, which is the half of the order blocked on a premise -- the `trips.` prefix it",
            "told me to reuse does not exist in `frontend/src` (zero hits), so where those keys live is a",
            "ruling, not a guess. `data-testid` values and the `.active` class stay where the other gates",
            "read them, and the gate records each tab's painted box so a layout shift cannot hide in a",
            "pure-attribute change.",
            "",
            "Counters: with the roles in, the new arms are green and the previous hand's gate re-ran green",
            "on the same tree; with the roles reverted (only the roles, one file, the tip's own bytes) the",
            "same arms go red. `typecheck:all` exit code zero. Exact numbers live in the lane's receipt",
            "files under review/ord0573/.",
            "",
            "The cost of this, measured rather than argued (`review/ord0573/cost/`, four files: two",
            "generations x two locales). A tab's role replaces the button role, it does not add to it, so",
            "a locator written as `getByRole(\"button\", {name})` stops answering. Two shipped upstream",
            "gates click these very tabs that way -- `frontend/e2e/product-v8.spec.ts:101` and",
            "`frontend/e2e/real-world-trip-operations-v9.spec.ts:46`, both of which force locale `en` in",
            "their own `addInitScript`. The new ruler replays both locator forms on the live screen: on",
            "the tip's bytes all four words answer through the button form and zero through the tab form,",
            "on this hand's bytes the same four answer through the tab form and zero through the button",
            "form -- a clean swap, no word left unreachable, and the negative control (a word no control",
            "carries) reads zero in both forms on both generations, which is what keeps the counters from",
            "being trusted blindly. Those two assertion lines belong to their own authors, so this hand",
            "did not touch them; the remedy is one word each (`button` -> `tab`) and the call on who makes",
            "it is the commander's. What is NOT claimed: that either upstream spec runs green or red end",
            "to end here -- `real-world-trip-operations-v9.spec.ts` was run on the tip's own bytes and",
            "already fails before it reaches that line (its `POST /api/v1/demo/reset` answers 403 on this",
            "lane's stack, recorded in `review/ord0573/upstream_v9_on_tip_bytes_r1.txt`), so the only",
            "honest statement about those two gates is about the locator form, not the verdict.",
        ]
        if stacked:
            message += [
                "",
                "Stacking, said plainly: this tip's copy of the shell file is not the previous hand's blob",
                BLOB_WITH_0572_ONLY + ", so the diff against this tip carries that hand's nine added",
                "lines as well. Land the earlier branch first and this one reduces to the roles alone; the",
                "numstat above is measured on the tip actually named as this commit's parent, not on a",
                "hoped-for base.",
            ]
        else:
            message += [
                "",
                "Base, read at build time rather than remembered: this tip's copy of the shell file is",
                BLOB_WITH_0572_ONLY + ", which is the previous hand's landed bytes, so the numstat above",
                "is this hand alone -- the roles, four added lines, nothing else.",
            ]
        commit = git("commit-tree", tree, "-p", tip, "-m", chr(10).join(message))
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
    print("\n".join(out[:14]))
    print("wrote %s (%d lines)" % (REPORT, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
