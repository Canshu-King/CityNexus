"""ORD-0578 token route census: ship the ruler AND its readings (zero product bytes).

A first attempt shipped the ruler without the readings; rather than rewrite that pushed ref, this builds a
new one with every file the block cites.

usage: python ord0578_token_commit_r2.py [--push]
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "hubcut"
REF = "refs/heads/review/8ac89982-ord0578-token-route-chrome-r2"
INDEX = LANE / "run/ord0578_token_index"
REPORT = LANE / "run/ord0578_token_commit_r2.txt"
SPEC = "frontend/e2e/qoder-8ac89982-ord0578-token-route-chrome-r1.spec.ts"
ENTRIES = [
    (SPEC, TREE / SPEC),
    ("review/ord0578/token_chrome_zh.json", LANE / "evidence/ord0512/e2e/ord0578_token_chrome_zh.json"),
    ("review/ord0578/token_chrome_en.json", LANE / "evidence/ord0512/e2e/ord0578_token_chrome_en.json"),
    ("review/ord0578/gate_stdout_r1.txt", LANE / "run/_ord0578_token_r3.out"),
    ("review/ord0578/commit_tool_r1.py", LANE / "run/ord0578_token_commit_r2.py"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    tip = os.environ.get("ORD0578_TOKEN_TIP") or git(
        "ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    git("cat-file", "-e", "%s^{commit}" % tip)
    out = ["TIP=%s" % tip, "REF=%s" % REF]
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
        bad = [p for p in added + modified if not (p.startswith("review/") or p.startswith("frontend/e2e/"))]
        if deleted or bad:
            out.append("REFUSE: this tree drops paths or touches a product path -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = "\n".join([
            "ORD-0578: on a token route the chrome is absent, and the screen speaks for itself",
            "",
            "This family asks how the chrome says which screen you are on. /v8/shared/<token> is the",
            "exception: measured on both locales, an unknown token and a malformed tail both paint no bottom",
            "bar, no sidebar, no hamburger, no breadcrumb and no shell container, and each says its own first",
            "line -- 'opened from a link somebody shared', and 'a shared trip poster' for the poster form --",
            "with the refusal carrying the server's own reason name, SHARE_GRANT_UNKNOWN. The control screen",
            "in the same run (/v8/hub) has the bar and the breadcrumb, so the absence is the route's shape and",
            "not a dark run.",
            "",
            "One field reads False and is shipped that way on purpose: the two token cases are compared as raw",
            "strings, and they differ only in whitespace inside the long refusal, so the content agrees while",
            "the bytes do not. The first two versions of that comparison compared whole rows and then whole",
            "rows minus the name -- both could only answer False, which is a comparison never performed; this",
            "one lists the fields it judges and the difference it found is named above.",
            "",
            "No product bytes: the only file outside review/ is the ruler. This ref replaces the earlier one,",
            "which shipped the ruler without the readings; it was not rewritten.",
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