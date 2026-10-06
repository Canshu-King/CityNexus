"""ORD-0550 r1 recut verdict: ship the receipts the verdict block cites, on this lane's own ref.

The block says "the tip's own two rulers are green on the tip's own bytes" and names two receipt
paths. A verdict with no retrievable coordinate is not a delivery, so those two receipts (plus the
ruler's own output on the block, and the provenance of the extract) go on a branch whose parent is
the tip that was measured. Nothing outside review/ is added, and no product path is touched.

usage: python ord0550_verdict_commit_r1.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TIP = "cfda610a99592b6c4111dbc5ee7ce0544a8f2fe2"
REF = "refs/heads/review/8ac89982-ord0550-recut-verdict-r1"
INDEX = LANE / "run/ord0550_verdict_index"
REPORT = LANE / "run/ord0550_verdict_commit_r1.txt"
ENTRIES = [
    ("review/ord0550/tip_ruler_0296_r1.txt", LANE / "run/_ord0550_tip_ruler_0296.out"),
    ("review/ord0550/tip_ruler_0479_r1.txt", LANE / "run/_ord0550_tip_ruler_0479.out"),
    ("review/ord0550/recut_verdict_r1.md", LANE / "run/_8ac89982_ord0550_recut_draft.md"),
    ("review/ord0550/provenance_r1.txt", LANE / "run/_ord0550_verdict_provenance.txt"),
    ("review/ord0550/ruler_on_verdict_r1.txt", LANE / "run/_ord0550_ruler_r1.txt"),
    ("review/ord0550/commit_tool_r1.py", LANE / "run/ord0550_verdict_commit_r1.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    git("cat-file", "-e", "%s^{commit}" % TIP)
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
        out = ["TIP=%s" % TIP, "REF=%s" % REF, "TREE=%s" % tree,
               "against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted))]
        out += ["ADDED %s" % p for p in added]
        out += ["MODIFIED %s" % p for p in modified]
        bad = [p for p in added + modified if not p.startswith("review/")]
        if deleted or bad:
            out.append("REFUSE: this tree drops or touches paths outside review/ -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = "\n".join([
            "ORD-0550 r1 recut verdict: my hand's intent is already on the tip, in a stronger form",
            "",
            "The commander's landing gate reported a real three-way conflict on",
            "backend/tests/test_qoder_ord0296_write_deadline.py, so this lane re-read both sides before",
            "cutting anything. The finding is that a rebase would carry no content: the tip already holds",
            "both fixes, and its copies are later and wider than mine -- the 0479 ruler finds its site",
            "through the named table (SITE, REFUSAL_KEY, VALUE) instead of a row number, and the 0296",
            "ruler was rewritten to read its own scale from the product plus a single-source path",
            "whitelist, carrying two rulings that postdate my branch.",
            "",
            "This branch ships no product bytes. It carries the receipts the verdict cites: both tip",
            "rulers run on the tip's own extracted bytes (11 passed; 9 passed / 1 skipped), the",
            "provenance of that extract and of the two failures my first trimmed extract caused, and the",
            "ruler's own output on the verdict text. The verdict itself is review/ord0550/recut_verdict_r1.md.",
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
