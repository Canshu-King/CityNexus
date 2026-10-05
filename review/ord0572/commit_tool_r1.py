"""ORD-0572 · 底栏选中态：组装候选提交（默认只打印，不写 ref）。

形制：父 = 现读尖；树从尖的树起（read-tree），只盖这一手动过的路径，所以不可能删别人的东西；
`diff --name-status` 里出现任何 `D`、或 `M` 里出现这两枚之外的路径，整枚拒。

这手产品侧应当只有一枚文件（`V8Experience.tsx`）加一枚新闸（`frontend/e2e/` 下新文件）。

usage: python ord0572_commit_r1.py            (build and print)
       python ord0572_commit_r1.py --push     (writes the new ref and pushes that one ref)
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
TIP = os.environ.get("ORD0572_TIP") or "b2fccfdf2728bbb025c3c09db36ce5ed9401ee4c"
REF = os.environ.get("ORD0572_REF") or "refs/heads/review/8ac89982-ord0572-bottom-bar-says-where-you-are-r1"
INDEX = LANE / "run/ord0572_index"
REPORT = pathlib.Path(os.environ.get("ORD0572_REPORT") or (LANE / "run/ord0572_commit_r1.txt"))

MODIFIED = ["frontend/src/app/V8Experience.tsx"]
ADDED_PRODUCT = ["frontend/e2e/qoder-8ac89982-ord0572-nav-current.spec.ts"]
LOGS = [
    ("run/_ord0572_gate.out", "review/ord0572/gate_stdout_r1.txt"),
    ("run/_ord0572_typecheck.out", "review/ord0572/typecheck_r1.txt"),
    ("evidence/ord0512/gate/ord0572_r1.log", "review/ord0572/gate_full_log_r1.log"),
    ("run/_ord0572_counter.out", "review/ord0572/counter_example_r1.txt"),
    ("run/ord0572_commit_r1.py", "review/ord0572/commit_tool_r1.py"),
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
    if git("rev-parse", TIP) != TIP:
        print("REFUSE: the tip is not readable in this clone")
        return 2
    tip_files = {}
    for line in git("ls-tree", "-r", "--format=%(objectname) %(path)", TIP).splitlines():
        oid, _, path = line.partition(" ")
        tip_files[path] = oid

    entries = []
    for relative in MODIFIED:
        node = TREE / relative
        data = node.read_bytes()
        if blob_id(data) == tip_files.get(relative):
            print("REFUSE: %s is byte-identical to the tip" % relative)
            return 5
        entries.append((relative, node))
    for relative in ADDED_PRODUCT:
        node = TREE / relative
        if not node.is_file():
            print("REFUSE: this hand lacks %s" % relative)
            return 2
        if tip_files.get(relative) is not None:
            print("REFUSE: %s already exists on the tip" % relative)
            return 5
        entries.append((relative, node))

    readings = sorted(glob.glob(str(TREE.parent / "evidence/ord0512/e2e/ord0572_*.json")))
    if len(readings) != 10:
        print("REFUSE: expected ten gate readings, found %d" % len(readings))
        return 3
    for path in readings:
        name = "review/ord0572/readings/" + pathlib.Path(path).name
        entries.append((name, pathlib.Path(path)))
    for source, target in LOGS:
        path = LANE / source
        if not path.exists():
            print("REFUSE: missing evidence %s" % path)
            return 4
        entries.append((target, path))

    out = ["TIP=%s" % TIP, "REF=%s" % REF, "modified=%d" % len(MODIFIED),
           "new_gate=%d" % len(ADDED_PRODUCT), "readings=%d" % len(readings),
           "logs=%d" % len(LOGS)]
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        if INDEX.exists():
            INDEX.unlink()
        git("read-tree", "%s^{tree}" % TIP)
        for repo_path, source in entries:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        out.append("TREE=%s" % tree)
        status = git("diff", "--name-status", TIP, tree).splitlines()
        deleted = [line for line in status if line.startswith("D")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        out.append("against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted)))
        out += ["MODIFIED %s" % path for path in modified]
        out += ["ADDED %s" % path for path in added if not path.startswith("review/")]
        if deleted or sorted(modified) != sorted(MODIFIED):
            out.append("REFUSE: this hand must modify only the one shell file -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = (
            "ORD-0572: the bottom bar now says which screen you are on, and the four words on it do not move\n"
            "\n"
            "The lane's own C2 check found no nameless control on these two screens, and named what was\n"
            "actually missing instead: the active item was drawn only by a class and a contrast role, so\n"
            "a traveller using a screen reader heard four buttons and could not tell which screen the\n"
            "device was already on. This hand adds `aria-current=\"page\"` to the one button the route\n"
            "matches and to no other, reusing the panel's existing notion of a match -- including the\n"
            "one the shell already had, that `live` is the map button's screen. `data-contrast-role` and\n"
            "`.active` stay exactly where they were; the diff against this tip is nine added lines and\n"
            "nothing removed, and that is the whole product change.\n"
            "\n"
            "The new gate (`frontend/e2e/qoder-8ac89982-ord0572-nav-current.spec.ts`) judges five screens\n"
            "under both dictionary arms: exactly one button claims current and it is the screen you are\n"
            "on; the other three are required to still have no `aria-current` at all (an attribute spread\n"
            "to every button would be worse than none); and the contrast role plus the active class must\n"
            "stay on the claiming button, because the dark gate and the styling read those. Eleven arms\n"
            "green on a stack this lane owns -- own ports, fresh run-id database -- and `typecheck:all`\n"
            "exit code zero.\n"
            "\n"
            "\"The words did not change\" is measured, not asserted: every reading of this run is compared\n"
            "against the same lane's pre-change C2 reading of the same shapes and screens (that pass ran\n"
            "on the tip's own bytes), 24 comparable pairs, zero mismatches. The comparison is asymmetric\n"
            "on purpose and said so: that earlier pass recorded only the buttons its rule flagged, so the\n"
            "English arm contributes two keys per screen and the Chinese arm four.\n"
            "\n"
            "One premise from the order is corrected by measurement rather than followed: it referred to\n"
            "a `trips.` prefix already on this screen. Scanning `frontend/src` for `\"trips.` returns zero\n"
            "hits on this tip -- the bottom bar's own words come from `mobile.*` and the drawer from\n"
            "`nav.`. The sibling order's tab labels therefore need a decision, not a guess: they can go\n"
            "into `frontend/src/i18n/LocaleContext.tsx` (a shared file over two thousand lines, which the\n"
            "standing rule queues by) or into a per-feature copy module in the newer shape the repo has\n"
            "settled on. That half is held for one word of ruling; the roles it also asked for are not\n"
            "blocked by that choice.\n"
        )
        commit = git("commit-tree", tree, "-p", TIP, "-m", message)
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
