"""ORD-0459 r2 -- lint what a landing merge onto the live tip would actually produce.

The commander's predicate is that a merged candidate must equal the lane's own bytes. Two questions
have to be answered with numbers, not with confidence:

  1. does the landing merge keep every file this lane changed, byte for byte?
  2. does the merged tree still hold any radius declaration carrying a literal -- i.e. does something
     that landed after my base put off-table corners back on screen?

Both are measured against the tip read live, and the whole reading is written to a text artifact so a
delivery block can cite it by path:line instead of asserting it in prose.
"""
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
LANE = "review/Q-ord0459-radii-tier-step2-r2"
DECL = re.compile(r"(border(?:-\w+)?-radius:\s*)([^;{}]+)(;)")


def git(*a):
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def gitrc(*a):
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").returncode


TIP = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
REF = git("ls-remote", "--refs", "origin", "refs/heads/%s" % LANE).split()[0]
BASE = git("merge-base", TIP, REF)
MINE = git("diff", "--name-only", BASE, REF, "--", "frontend/src").splitlines()
TIPSIDE = git("diff", "--name-only", BASE, TIP, "--", "frontend/src").splitlines()
MT = subprocess.run(["git", "-C", str(WT), "merge-tree", "--write-tree", TIP, REF],
                    capture_output=True, text=True, encoding="utf-8")
MT_RC = MT.returncode
MT_TREE = MT.stdout.splitlines()[0] if MT.stdout else ""


def lint(ref):
    fs = [f for f in git("ls-tree", "-r", "--name-only", ref).splitlines()
          if f.startswith("frontend/src/") and f.endswith(".css")]
    tot, bad = 0, []
    for f in fs:
        text = git("show", "%s:%s" % (ref, f))
        for m in DECL.finditer(text):
            tot += 1
            if re.search(r"\d", re.sub(r"var\([^()]*\)", "", m.group(2))):
                bad.append((f, text[:m.start()].count(chr(10)) + 1, m.group(2).strip()))
    return len(fs), tot, bad


L = []
A = L.append
A("ORD-0459 r2 -- landing-merge lint, both sides measured, tip read live with env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote origin")
A("tip            %s" % TIP)
A("lane ref       refs/heads/%s = %s" % (LANE, REF))
A("merge-tree exit code %s, merged tree %s" % (MT_RC, MT_TREE))
A("merge-base(tip, lane) %s -- the lane forked here; the line has %d frontend file(s) of its own since"
  % (BASE, len(TIPSIDE)))
A("")
A("1. files this lane changes, and whether the landing merge keeps my bytes")
for f in MINE:
    a = git("rev-parse", "%s:%s" % (REF, f))
    b = git("rev-parse", "%s:%s" % (MT_TREE, f))
    A("   %-56s lane %s merged %s %s" % (f, a[:12], b[:12], "EQUAL" if a == b else "DIFFER"))
A("   files whose merged blob differs from the lane's: %d" % sum(
    1 for f in MINE if git("rev-parse", "%s:%s" % (REF, f)) != git("rev-parse", "%s:%s" % (MT_TREE, f))))
A("   frontend files the line moved since the lane forked (the merge takes the tip's side; this lane never touched them): %d"
  % len(TIPSIDE))
for f in TIPSIDE:
    A("       %s" % f)
A("")
A("2. radius declarations carrying a literal, counted in each tree")
for label, ref in (("tip", TIP), ("lane", REF), ("merged", MT_TREE)):
    nfiles, ndecls, bad = lint(ref)
    A("   %-8s css files %d, radius declarations %d, literal-carrying %d" % (label, nfiles, ndecls, len(bad)))
    for b in bad[:6]:
        A("       %s:%s  %s" % (b[0], b[1], b[2]))
A("")
A("3. the earlier ORD-0441 candidate 32807b47a038594b0aba8b9f4a2441b43831b549, tested the same way")
CAND = "32807b47a038594b0aba8b9f4a2441b43831b549"
CAND_BASE = "35326e62fb3de9f0cda459c8426ac22c0c49c715"
CM = subprocess.run(["git", "-C", str(WT), "merge-tree", "--write-tree", TIP, CAND],
                    capture_output=True, text=True, encoding="utf-8")
A("   merge-tree onto the tip exit code %s, merged tree %s" % (CM.returncode, CM.stdout.splitlines()[0] if CM.stdout else ""))
for f in [x for x in git("diff", "--name-only", CAND_BASE, CAND).splitlines() if not x.startswith("review/")]:
    added = [l[1:] for l in git("diff", CAND_BASE, CAND, "--unified=0", "--", f).splitlines()
             if l.startswith("+") and not l.startswith("+++") and l[1:].strip()]
    tip_lines = [x.strip() for x in git("show", "%s:%s" % (TIP, f)).splitlines()]
    missing = [l for l in added if l.strip() not in tip_lines]
    A("   %s: the candidate adds %d lines, of which %d are NOT already on the tip verbatim" % (f, len(added), len(missing)))
    merged_blob = git("rev-parse", "%s:%s" % (CM.stdout.splitlines()[0], f)) if CM.stdout else "NA"
    A("       tip blob %s | candidate blob %s | merged blob %s" % (
        git("rev-parse", "%s:%s" % (TIP, f)), git("rev-parse", "%s:%s" % (CAND, f)), merged_blob))
out = "\n".join(L) + "\n"
dst = WT / "review/ord0459/land_merge_lint_r1.txt"
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(out, encoding="utf-8", newline="\n")
print(out)
