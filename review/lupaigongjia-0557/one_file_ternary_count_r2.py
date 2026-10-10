# -*- coding: utf-8 -*-
"""Count the one-CJK-arm ternaries in one file at two commits, same instrument both sides.

Fixed after a self-found instrument defect: the first version hard-coded a repo path and ignored
the exit code of `git show`, so a failed lookup produced an empty string and the script reported
"0 hits" for an arm that had never actually been read. That is a blind instrument, not a clean
one. Now: the repo is an argument, a non-zero exit aborts, and an empty blob aborts too.
"""

import re
import subprocess
import sys

PATH = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
LIT = r'"(?:[^"\\]|\\.)*"'
TERN = re.compile(r"\?[ \t]*" + LIT + r"[ \t]*:[ \t]*" + LIT)
CJK = re.compile(u"[　-〿一-鿿豈-﫿]")


def hits(repo, ref):
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "%s^{commit}" % ref],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit("ABORT REF_UNRESOLVED %s in %s :: %s" % (ref, repo, p.stdout.decode("utf-8", "replace")[:120]))
    sha = p.stdout.decode().strip()
    p = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (sha, PATH)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("ABORT GIT_SHOW %s:%s :: %s" % (sha[:10], PATH, p.stderr.decode("utf-8", "replace")[:160]))
    text = p.stdout.decode("utf-8", "replace")
    if "locale" not in text and "function" not in text:
        raise SystemExit("ABORT EMPTY_BLOB %s:%s (%d bytes) - 空内容不当成零命中" % (sha[:10], PATH, len(text)))
    found = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in TERN.finditer(line):
            arms = re.findall(LIT, m.group(0))
            if len(arms) == 2 and bool(CJK.search(arms[0])) != bool(CJK.search(arms[1])):
                found.append((i, line.strip()[:78]))
    return sha, found


if len(sys.argv) < 4:
    raise SystemExit("usage: one_file_ternary_count_r1.py <repo> <before-ref> <after-ref>")
repo, before_ref, after_ref = sys.argv[1], sys.argv[2], sys.argv[3]
b_sha, before = hits(repo, before_ref)
a_sha, after = hits(repo, after_ref)
print("PATH %s repo=%s" % (PATH, repo))
print("BEFORE %s 命中 %d 处: %s" % (b_sha[:10], len(before), before))
print("AFTER  %s 命中 %d 处: %s" % (a_sha[:10], len(after), after))
print("blob_before=%s blob_after=%s" % (
    subprocess.run(["git", "-C", repo, "rev-parse", "%s:%s" % (b_sha, PATH)],
                   stdout=subprocess.PIPE).stdout.decode().strip(),
    subprocess.run(["git", "-C", repo, "rev-parse", "%s:%s" % (a_sha, PATH)],
                   stdout=subprocess.PIPE).stdout.decode().strip()))
