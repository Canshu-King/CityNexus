"""`git cat-file -e` answers with an exit code, not with stdout.

My first landing check read the empty stdout of a *successful* existence probe and recorded every
file as ABSENT_AT_TIP -- an instrument artifact that would have gone into the ledger as a fact about
the tree.  This probe returns the blob id when the path exists at a revision and a named value when
it does not, so the difference is decided by the return code where the difference actually lives.
"""
import os
import subprocess

REPO = r"D:/moodle/CityNexus"


def blob_at(rev, path):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(k, None)
    env["NO_PROXY"] = "api.github.com"
    r = subprocess.run(["git", "-C", REPO, "cat-file", "-e", "%s:%s" % (rev, path)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, env=env)
    if r.returncode != 0:
        return "PATH_ABSENT_AT_REV"
    out = subprocess.run(["git", "-C", REPO, "rev-parse", "%s:%s" % (rev, path)],
                         stdout=subprocess.PIPE, timeout=120,
                         env=env).stdout.decode("utf-8").strip()
    return out
