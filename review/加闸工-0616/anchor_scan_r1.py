# -*- coding: utf-8 -*-
"""Walk every `file:line` in my ORD-0616 docs and prove that line exists and is not blank.

Product paths resolve from the committed generation; evidence paths from my folder; the ledger from
D:/moodle (its line numbers drift as the apply leg grows it, so they are re-read here, not remembered).
"""
import io
import re
import subprocess
import sys

REPO = "D:/moodle/_qoder_integration_20260919"
CAND = "29fdb40779829e2161e6aef0a0e15dbe03443df1"
EV = "D:/moodle/_jz_0616"
DOCS = ["readout_r1.txt", "proof_r1.txt", "_block_r1.md"]
PAT = re.compile(r"([A-Za-z0-9_./\-\u4e00-\u9fff]+\.(?:py|tsx|ts|txt|json|yaml|md)):(\d+)")
GIT_PREFIX = ("backend/", "frontend/", "contracts/", "docs/", "live_checks/")


def main():
    bad = 0
    checked = 0
    cache = {}
    for doc in DOCS:
        text = io.open("%s/%s" % (EV, doc), encoding="utf-8").read()
        for m in PAT.finditer(text):
            path, line = m.group(1), int(m.group(2))
            checked += 1
            name = path.split("/")[-1]
            if path.startswith(GIT_PREFIX):
                key = ("git", path)
                if key not in cache:
                    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (CAND, path)],
                                       capture_output=True, timeout=900)
                    cache[key] = r.stdout.decode("utf-8", "replace").splitlines() if not r.returncode else None
                body, where = cache[key], "提交那一代 %s" % path
            elif name == "CITYNEXUS_AGENT_CONTROL.md":
                key = ("ledger", name)
                if key not in cache:
                    cache[key] = io.open("D:/moodle/" + name, encoding="utf-8").read().splitlines()
                body, where = cache[key], "账本 %s" % name
            else:
                key = ("ev", name)
                if key not in cache:
                    try:
                        cache[key] = io.open("%s/%s" % (EV, name), encoding="utf-8").read().splitlines()
                    except IOError:
                        cache[key] = None
                body, where = cache[key], "证据件 %s" % name
            if body is None:
                print("BAD %s 引 %s —— 文件读不到" % (doc, m.group(0)))
                bad += 1
            elif line > len(body):
                print("BAD %s 引 %s —— 那文件只有 %d 行" % (doc, m.group(0), len(body)))
                bad += 1
            elif not body[line - 1].strip():
                print("BAD %s 引 %s —— 那一行是空行" % (doc, m.group(0)))
                bad += 1
            else:
                print("OK   %s:%d  实读 %r" % (where.split(" ")[-1], line, body[line - 1].strip()[:58]))
    print("CHECKED %d  BAD %d" % (checked, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
