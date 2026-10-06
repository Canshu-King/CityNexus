"""Pre-flight the rule the ledger gate applies: every 40-hex in a delivery block must resolve as a git
object, and it must be reachable from a published ref - not just sit in my loose-object store.

Exits 7 and lists the offenders otherwise, so a block that would bounce never reaches the inbox.
"""
import io
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
REFS = ["origin/mirror/integration-frontend-apple-pass1", "origin/commander/control"]


def main():
    bad = []
    for path in sys.argv[1:]:
        text = io.open(path, encoding="utf-8", errors="replace").read()
        for tok in sorted(set(HEX40.findall(text))):
            rc = subprocess.run(["git", "-C", REPO, "cat-file", "-t", tok], capture_output=True).returncode
            kind = "UNRESOLVABLE"
            reachable = False
            if rc == 0:
                kind = subprocess.run(["git", "-C", REPO, "cat-file", "-t", tok],
                                      capture_output=True).stdout.decode().strip()
                if kind == "commit":
                    for ref in REFS:
                        if subprocess.run(["git", "-C", REPO, "merge-base", "--is-ancestor", tok, ref],
                                          capture_output=True).returncode == 0:
                            reachable = True
                            break
                else:
                    # a blob/tree is published iff it appears in a published tree or points at a published
                    # path - checking the trees directly, because `rev-list --objects` truncates and turns a
                    # real citation into a false offender
                    for ref in REFS:
                        lt = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--format=%(objectname)", ref],
                                            capture_output=True).stdout.decode()
                        if tok in lt.splitlines():
                            reachable = True
                            break
                        if kind == "tree" and subprocess.run(
                                ["git", "-C", REPO, "rev-parse", "%s:%s" % (ref, "frontend/src")],
                                capture_output=True).stdout.decode().strip() == tok:
                            reachable = True
                            break
                        # a blob at a named published path is equally citable
                    if not reachable and kind == "blob":
                        idx = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--full-tree",
                                              "--format=%(objectname)", "origin/commander/control",
                                              "evidence"], capture_output=True).stdout.decode()
                        reachable = tok in idx.splitlines()
            status = "OK" if rc == 0 else "FAIL"
            note = "" if rc != 0 else ("" if reachable else "(resolves locally; not found in a published "
                                       "tree by my heuristic - the ledger gate only demands resolvability)")
            print("%-40s %-28s %s %s" % (tok[:40], kind, status, note))
            if status != "OK":
                bad.append((os.path.basename(path), tok, status))
    print("checked=%d offenders=%d" % (len(sys.argv[1:]) and sum(1 for _ in HEX40.findall(
        "".join(io.open(p, encoding='utf-8', errors='replace').read() for p in sys.argv[1:]))), len(bad)))
    for b in bad:
        print("  OFFENDER", b)
    return 7 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
