"""Read-only: for the door-GREEN inbox blocks, list each full 40-hex coordinate and where it resolves.

Roots probed (all with `git cat-file -t`, read-only):
  A = D:/moodle/CityNexus                      (the repo the writer hard-codes)
  B = D:/moodle/_qoder_integration_20260919    (the live line, per project memory)
  C = the GitHub authoritative branch tip's repo? no - only local object stores are probed here.
A token that resolves in B but not A is a WRITER-ROOT mismatch, not a fabricated coordinate.
"""
import io
import os
import re
import subprocess
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
ROOTS = [("A_CityNexus", r"D:\moodle\CityNexus"),
         ("B_integration", r"D:\moodle\_qoder_integration_20260919")]
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
RULER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "claim_coordinate_check_r4e.py")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"


def kind(root, tok):
    r = subprocess.run(["git", "-C", root, "cat-file", "-t", tok],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        return None
    return (r.stdout or "").strip()


def main():
    print("roots:", [(n, os.path.isdir(p)) for n, p in ROOTS])
    for n, p in ROOTS:
        r = subprocess.run(["git", "-C", p, "rev-parse", "--git-dir"], capture_output=True, text=True)
        print("  %s git-dir=%s" % (n, (r.stdout or r.stderr).strip()[:80]))
    total = {}
    for f in sorted(os.listdir(INBOX)):
        if not f.endswith(".md"):
            continue
        p = os.path.join(INBOX, f)
        d = subprocess.run([PY, RULER, "--text", p, "--expect-clean"], capture_output=True, timeout=600)
        if d.returncode != 0:
            continue
        body = io.open(p, encoding="utf-8", errors="replace").read()
        toks = sorted(set(HEX40.findall(body)))
        print(chr(10) + "== %s  door=GREEN  hex40=%d" % (f, len(toks)))
        for t in toks:
            ks = [(n, kind(n, t)) for n, rp in ROOTS]
            line = "   %s  %s" % (t[:12], "  ".join("%s=%s" % (n, k or "MISS") for n, k in ks))
            where = [n for n, k in ks if k]
            if not where:
                line += "   <== resolves NOWHERE local"
            elif "A_CityNexus" not in where:
                line += "   <== NOT in the writer's root"
            print(line)
            for w in where:
                total[w] = total.get(w, 0) + 1
        # which line carries the bad ones
        for i, ln in enumerate(body.splitlines(), 1):
            bad = [t for t in HEX40.findall(ln) if not kind(ROOTS[0][1], t)]
            if bad:
                print("   line %d has %d token(s) absent from A_CityNexus: %s" % (i, len(bad), ", ".join(b[:12] for b in bad)))
    print(chr(10) + "resolvable counts by root: %r" % (total,))
    print("at %s" % time.strftime("%H:%M:%S"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
