# -*- coding: utf-8 -*-
"""名册对账：我这九枚 review/屏工-* 枝在远端（GitHub 镜像）还在不在、
不在的那枚它的提交是否已经在线上（=改名/清理）还是真读不到。"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BARE = "D:/moodle/CityNexus"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"


def git(args, cwd=BARE):
    proc = subprocess.run(["git"] + args, cwd=cwd, capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


rc, out, err = git(["-c", "core.quotePath=false", "ls-remote", "origin", "refs/heads/review/*"])
remote = {}
for line in out.splitlines():
    parts = line.split("\t")
    if len(parts) == 2:
        remote[parts[1].strip()] = parts[0].strip()
rc2, local, _ = git(["-c", "core.quotePath=false", "for-each-ref",
                     "--format=%(refname) %(objectname)", "refs/heads/review/屏工*"])
rc3, line_sha, _ = git(["ls-remote", "origin", LINE])
tip = line_sha.split("\t")[0].strip() if line_sha.strip() else ""
print("REMOTE_REVIEW_REFS %d  LOCAL_PINGGONG %d  LINE %s" % (len(remote), len(local.splitlines()), tip[:12]))
print("REMOTE_HAS_PINGGONG %d" % len([k for k in remote if "屏工" in k]))
for entry in local.splitlines():
    if not entry.strip():
        continue
    ref, sha = entry.split()
    on_remote = ref in remote
    merged = ""
    if sha and tip:
        code, _o, _e = git(["merge-base", "--is-ancestor", sha, tip]) if tip in [t for t in [tip]] else (2, "", "")
        merged = "在线内" if code == 0 else "不在线内"
    same = "同值" if on_remote and remote.get(ref) == sha else ("异值" if on_remote else "-")
    print("  %s sha=%s 远端=%s(%s) 相对权威线=%s"
          % (ref.replace("refs/heads/review/", ""), sha[:12], "有" if on_remote else "无", same, merged))
