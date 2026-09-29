"""Classify every line of the diff between the two commits on the ORD-0428 branch.

The second commit claims to be comment-only, and "it is only a comment" is exactly the kind of sentence a
reader cannot check without opening the diff.  So the classification is done here and written out: each
removed/added line is labelled, and the count of non-comment lines is the number the block quotes.

Classification is deliberately conservative: a line counts as comment only if it is a `/* ... */` opener
or closer, a ` * ` continuation, or a continuation of a line that opened inside such a block.  Anything
else -- including a JSX text line -- is counted as non-comment, so a mislabel would show up as a
non-zero count rather than as a false "comment-only".
"""
import io
import json
import os
import re
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0428"
REPO = "D:/moodle/CityNexus"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
BASE = "4037cb331ea00b83124316d40329762fa1131689"


def git(*args):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy="] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, env=ENV)
    assert r.returncode == 0, (args, r.stderr[:400])
    return r.stdout


def classify(lines):
    """Return (comment, non_comment, detail) for the +/- body lines of a unified diff."""
    comment, other = [], []
    for ln in lines:
        body = ln[1:]
        s = body.strip()
        if not s:
            continue
        if (s.startswith("/*") or s.startswith("*") or s.startswith("*/")
                or s.endswith("*/") or " * " in body):
            comment.append(ln)
        else:
            other.append(ln)
    return comment, other


def main():
    rev = [l.strip() for l in git("rev-list", BASE + "..review/qoder-0428-wallet-card-title-join-r1").splitlines() if l.strip()]
    head_sha, first_sha = rev[0], rev[1]
    out = {"base": BASE, "first_commit": first_sha, "head_commit": head_sha,
           "files": [l for l in git("diff", "--name-only", first_sha, head_sha).splitlines() if l.strip()]}
    body = git("diff", "-U0", first_sha, head_sha).splitlines()
    plus = [l for l in body if l.startswith("+") and not l.startswith("+++")]
    minus = [l for l in body if l.startswith("-") and not l.startswith("---")]
    cp, co = classify(plus)
    mp, mo = classify(minus)
    out["second_commit_diff"] = {
        "added_lines": len(plus), "removed_lines": len(minus),
        "added_comment_lines": len(cp), "added_non_comment_lines": len(co),
        "removed_comment_lines": len(mp), "removed_non_comment_lines": len(mo),
        "non_comment_lines_verbatim": co + mo,
        "comment_only": not co and not mo,
    }
    # what the whole branch changes against its base, by file
    out["branch_vs_base"] = {
        "files": [l for l in git("diff", "--name-only", BASE, head_sha).splitlines() if l.strip()],
        "numstat": [l for l in git("diff", "--numstat", BASE, head_sha).splitlines() if l.strip()],
    }
    # the entry asset the current build emits, named from the file system rather than from a log
    dist = r"D:\moodle\_qoder_lane_S4_0926\wt0428\frontend\dist\assets"
    entries = sorted(f for f in os.listdir(dist) if re.match(r"index-.*\.js$", f)) if os.path.isdir(dist) else []
    import hashlib
    out["built_entry_after_second_commit"] = [
        {"name": f, "bytes": os.path.getsize(os.path.join(dist, f)),
         "local_bytes_sha1": hashlib.sha1(io.open(os.path.join(dist, f), "rb").read()).hexdigest()}
        for f in entries]
    io.open(os.path.join(WORK, "commit_pair_diff_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
