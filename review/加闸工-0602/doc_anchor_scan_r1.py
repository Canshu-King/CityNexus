# -*- coding: utf-8 -*-
"""Walk every `file:line` written in my three evidence docs and prove the referenced file really has
that line, resolving product paths from the committed generation and evidence paths from my folder.
"""
import io
import re
import subprocess
import sys

CAND = "5ed85afea5d86b71be117a6dba80c8f0e24020e9"
REPO = "D:/moodle/_qoder_integration_20260919"
EV = "D:/moodle/_jz_0602"
DOCS = ["readout_r1.txt", "proof_r1.txt", "gates_r2.txt"]
PAT = re.compile(r"([A-Za-z0-9_./\-\u4e00-\u9fff]+\.(?:py|tsx|ts|txt|json|yaml|md)):(\d+)")
GIT_PREFIX = ("backend/", "frontend/", "contracts/", "docs/", "live_checks/")


def main():
    bad = 0
    checked = 0
    gc = {}
    for doc in DOCS:
        text = io.open("%s/%s" % (EV, doc), encoding="utf-8").read()
        for m in PAT.finditer(text):
            path, line = m.group(1), int(m.group(2))
            checked += 1
            if path.startswith(GIT_PREFIX):
                if path not in gc:
                    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (CAND, path)],
                                       capture_output=True, timeout=600)
                    gc[path] = r.stdout.decode("utf-8", "replace").splitlines() if not r.returncode else None
                body = gc[path]
                where = "提交那一代 %s" % path
            else:
                name = path.split("/")[-1]
                if name not in gc:
                    try:
                        gc[name] = io.open("%s/%s" % (EV, name), encoding="utf-8").read().splitlines()
                    except IOError:
                        gc[name] = None
                body = gc[name]
                where = "证据件 %s" % name
            if body is None:
                print("BAD %s 里引 %s —— 文件读不到" % (doc, m.group(0)))
                bad += 1
                continue
            if line > len(body):
                print("BAD %s 里引 %s —— 那文件只有 %d 行" % (doc, m.group(0), len(body)))
                bad += 1
                continue
            if not body[line - 1].strip():
                print("BAD %s 里引 %s —— 那一行是空行" % (doc, m.group(0)))
                bad += 1
                continue
    print("CHECKED %d  BAD %d" % (checked, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
