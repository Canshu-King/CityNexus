"""ORD-0577 second layer census: ship the drawer/sidebar instruments and their readings.

Zero product bytes: the two files outside review/ are rulers. Parent is the tip whose shell bytes the
census ran on (verified equal to this tree's copy of that file before anything is committed).

usage: python ord0577_layers_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
TIP = "d602db8ed6280a56697eda8500cc4effe3484479"
REF = "refs/heads/review/8ac89982-ord0577-nav-layers-census-r1"
INDEX = LANE / "run/ord0577_layers_index"
REPORT = LANE / "run/ord0577_layers_commit_r1.txt"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
SHELL_BLOB = "5d62f7bc78a58369d871a37c820e0b9a1a6076e6"
LAYERS_SPEC = "frontend/e2e/qoder-8ac89982-ord0577-nav-layers-census-r1.spec.ts"
PROBE_SPEC = "frontend/e2e/qoder-8ac89982-ord0577-hamburger-probe-r1.spec.ts"
ENTRIES = [
    (LAYERS_SPEC, TREE / LAYERS_SPEC),
    (PROBE_SPEC, TREE / PROBE_SPEC),
    ("review/ord0577/layers_zh.json", LANE / "evidence/ord0512/e2e/ord0577_layers_zh.json"),
    ("review/ord0577/layers_en.json", LANE / "evidence/ord0512/e2e/ord0577_layers_en.json"),
    ("review/ord0577/hamburger_probe.json", LANE / "evidence/ord0512/e2e/ord0577_hamburger_probe.json"),
    ("review/ord0577/gate_stdout_layers_r1.txt", LANE / "run/_ord0577_layers_r3.out"),
    ("review/ord0577/gate_stdout_probe_r1.txt", LANE / "run/_ord0577_probe_r1.out"),
    ("review/ord0577/provenance_r2.txt", LANE / "run/_ord0577_layers_provenance.txt"),
    ("review/ord0577/commit_tool_r2.py", LANE / "run/ord0577_layers_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    git("cat-file", "-e", "%s^{commit}" % TIP)
    tip_blob = git("rev-parse", "%s:%s" % (TIP, SHELL_REL))
    tree_blob = git("hash-object", "--no-filters", str(TREE / SHELL_REL))
    out = ["TIP=%s" % TIP, "REF=%s" % REF, "tip_shell_blob=%s" % tip_blob, "tree_shell_blob=%s" % tree_blob,
           "shell_blob_equals_the_measured_one=%s" % (tip_blob == tree_blob == SHELL_BLOB)]
    if not (tip_blob == tree_blob == SHELL_BLOB):
        out.append("REFUSE: this tip's shell bytes are not the ones the census ran on -- nothing is committed")
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
        git("read-tree", "%s^{tree}" % TIP)
        for repo_path, source in ENTRIES:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        status = git("diff", "--name-status", TIP, tree).splitlines()
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        deleted = [line for line in status if line.startswith("D")]
        out += ["TREE=%s" % tree,
                "against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted))]
        out += ["ADDED %s" % p for p in added]
        out += ["MODIFIED %s" % p for p in modified]
        bad = [p for p in added + modified if not (p.startswith("review/") or p.startswith("frontend/e2e/"))]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a product path outside frontend/e2e/ -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = "\n".join([
            "ORD-0577 second layer census: the drawer already knows all 17 screens, and says it by class",
            "",
            "The bar census showed the bottom bar answers on six of the seventeen declared screens and is",
            "silent on eleven. This branch asks the same question of the other two chrome layers, because",
            "the cost of the two fix shapes the order allows depends on the answer.",
            "",
            "Measured, identically in zh and en: the phone drawer (390x844, seventeen rows) marks the",
            "current screen's own row on every one of the seventeen screens, and the negative control",
            "lands on the Today row -- but zero drawer rows carry aria-current. The desktop sidebar",
            "(1280x900, fifteen rows) marks the current row on fifteen screens, each mark also carrying",
            "data-contrast-role=state, and zero of its rows carry aria-current either; the two mobile-only",
            "keys, trips and me, have no sidebar row at all. So the drawer already holds the answer for",
            "every screen and states it only visually, and no layer except the six bar buttons speaks in",
            "the accessibility tree.",
            "",
            "Two failed runs ship with this branch rather than being hidden: the first never set the phone",
            "viewport, so it clicked a control that styles.css hides above 680px, and the second exceeded",
            "the default 60 s test budget. The hamburger probe was written to tell those two facts apart",
            "and measures the door visible with a 46x27 box on all seventeen screens.",
            "",
            "No product bytes: the two files outside review/ are rulers. Nothing is fixed here -- what this",
            "measurement makes cheap is the ruling: whether the drawer's existing per-screen answer should",
            "also be stated to a screen reader, or whether an off-main-route screen should instead be",
            "attributed to a nearest main route, which would need a mapping the product does not carry.",
        ])
        commit = git("commit-tree", tree, "-p", TIP, "-m", message)
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
