"""CMDR landing-kind checker r1.

A fast-forward landing can bring product code or only evidence files. Both pass the byte-equality
re-cut and both move the tip, so "the gate was green" says nothing about which one happened.
This prints, per landed commit, how many changed files sit under the product faces
(frontend/src, backend/app, contracts) versus the evidence faces (review/, evidence/, live_checks/).

Read-only: it only runs git diff-tree.
"""
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
PRODUCT = ("frontend/src", "backend/app", "contracts", "frontend/e2e")
EVIDENCE = ("review/", "evidence/", "live_checks/", "backend/tests/")

env = {}
import os
env = dict(os.environ)
env.pop("HTTP_PROXY", None)
env.pop("HTTPS_PROXY", None)


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=300)
    return (p.stdout or "").strip()


def kind(sha):
    files = git("diff-tree", "--no-commit-id", "--root", "-r", "--name-only", sha).splitlines()
    if not files:
        files = git("diff-tree", "--no-commit-id", "-r", "--name-only", sha + "^", sha).splitlines()
    prod = [f for f in files if f.startswith(PRODUCT)]
    ev = [f for f in files if f.startswith(EVIDENCE)]
    other = [f for f in files if f not in prod and f not in ev]
    return {"sha": sha, "files": len(files), "product": len(prod), "evidence": len(ev),
            "other": len(other), "verdict": "PRODUCT" if prod else "EVIDENCE_ONLY",
            "product_files": prod[:6]}


if __name__ == "__main__":
    rows = [kind(s) for s in sys.argv[1:]]
    for r in rows:
        print("%s %-14s files=%d product=%d evidence=%d other=%d %s" % (
            r["sha"][:12], r["verdict"], r["files"], r["product"], r["evidence"], r["other"],
            "; ".join(r["product_files"][:3])))
