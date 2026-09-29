"""ORD-0459 audit -- recompute the radius migration over EVERY stylesheet in the frontend source.

Nothing here is typed in: the baseline text comes from `git show <tip>:<file>` and the branch text
from `git show HEAD:<file>`, and the file list is read from the baseline tree, not from what I
remember editing. Each file's radius declarations are paired in document order, and every changed
pair is checked against the stated snap rule -- so a site migrated to the wrong tier shows up as a
named finding instead of a claim.

Rule under test: nearest tier of 0/4/8/12/16/20/24, ties to the LARGER tier; 50% is the circle tier;
a single value of 99 px or more is the pill tier (the corner-rounding hack this change replaces);
a bare 0 in shorthand names --cn-r-0 rather than staying a literal; a var() fallback is treated like
any other literal because it is the value that paints when the named token is missing.
"""
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
TIP = "8cf94ad794a94df0b6f992dc9e6e1bb0c6e70a4a"
HEAD = "HEAD"
TIERS = [0, 4, 8, 12, 16, 20, 24]
TOKEN_TIER = {"--cn-r-0": 0, "--cn-r-4": 4, "--cn-r-8": 8, "--cn-r-12": 12,
              "--cn-r-16": 16, "--cn-r-20": 20, "--cn-r-24": 24}
SEMANTIC = {"--cn-r-control": 12, "--cn-r-button": 16, "--cn-r-card": 16,
             "--cn-r-hero": 20, "--cn-r-sheet": 24}
NAMED = set(TOKEN_TIER) | set(SEMANTIC) | {"--cn-r-pill", "--cn-r-circle"}
DECL = re.compile(r"(border(?:-\w+)?-radius:\s*)([^;{}]+)(;)")
COMP = re.compile(r"var\((--cn-r-[a-z0-9]+)(?:\s*,\s*([^)]+))?\)|(\d+(?:\.\d+)?)px|(\d+(?:\.\d+)?)%|(\d+(?:\.\d+)?)|([A-Za-z]+)")


def git(*a):
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def show(ref, path):
    return git("show", "%s:%s" % (ref, path))


def expected(val):
    """The token sequence the rule predicts for a baseline declaration value."""
    out = []
    for name, inner, px, pct, bare, word in COMP.findall(val):
        if name:
            if inner:
                out.append(name)
                for sub in COMP.findall(inner):
                    out.append(predict_sub(sub))
            else:
                out.append(name)
        else:
            out.append(predict_sub((name, inner, px, pct, bare, word)))
    return out


def predict_sub(sub):
    _name, _inner, px, pct, bare, word = sub
    if px:
        v = int(round(float(px)))
        return "--cn-r-pill" if v >= 99 else "--cn-r-%d" % min(TIERS, key=lambda t: (abs(t - v), -t))
    if pct:
        return "--cn-r-circle" if float(pct) == 50 else "UNMAPPED-%s%%" % pct
    if bare:
        return "--cn-r-0" if int(bare) == 0 else "UNMAPPED-BARE-%s" % bare
    return "IDENT-%s" % word if word else "UNKNOWN"


def actual(val):
    """The token sequence the branch declares, with any unprefixed literal called out."""
    out = []
    for m in re.finditer(r"var\((--cn-r-[a-z0-9]+)(?:\s*,\s*([^)]+))?\)|(\d+(?:\.\d+)?(?:px|%))|(\b0\b)|([A-Za-z]+)", val):
        tok, inner, lit, zero, word = m.groups()
        if tok:
            out.append(tok if tok in NAMED else "OTHER-%s" % tok)
            if inner:
                nested = re.findall(r"--cn-r-[a-z0-9]+", inner)
                if nested:
                    out.extend(nested)
                else:
                    out.append("LITERAL-FALLBACK:%s" % inner.strip())
        elif lit:
            out.append("LITERAL:%s" % lit)
        elif zero:
            out.append("LITERAL:0")
        elif word:
            out.append("IDENT-%s" % word)
    return out


files = [p for p in git("ls-tree", "-r", "--name-only", TIP).splitlines()
         if p.startswith("frontend/src/") and p.endswith(".css")]
findings, sites, unchanged, unpaired = [], 0, 0, []
rows, per_file = [], {}
for f in files:
    bt, at = show(TIP, f), show(HEAD, f)
    b = [(m.group(1).strip(), m.group(2).strip()) for m in DECL.finditer(bt)]
    a = [(m.group(1).strip(), m.group(2).strip()) for m in DECL.finditer(at)]
    if not b and not a:
        continue
    per_file[f] = (len(b), len(a))
    if len(b) != len(a):
        unpaired.append("%s baseline %d branch %d" % (f, len(b), len(a)))
        continue
    for (pb, vb), (pa, va) in zip(b, a):
        if vb == va:
            unchanged += 1
            continue
        sites += 1
        want = expected(vb)
        got = actual(va)
        # a fallback token counts as satisfied when the fallback names the same tier as the token
        ok = want == got
        if pb != pa:
            findings.append("%s: property name changed %s -> %s" % (f, pb, pa))
            ok = False
        rows.append((f, pb, vb, va, want, got))
        if not ok:
            findings.append("%s %s: %-30s -> %-44s want=%s got=%s" % (f, pb, vb[:30], va[:44], want, got))

print("=== denominator, read from the baseline tree, not from what I edited ===")
print("css files scanned in frontend/src: %d" % len(files))
print("files carrying at least one radius declaration: %d" % len(per_file))
tot_b = sum(v[0] for v in per_file.values())
tot_a = sum(v[1] for v in per_file.values())
print("radius declarations: baseline %d, branch %d" % (tot_b, tot_a))
print("rewritten onto the table by this change: %d" % sites)
print("byte-identical (already on the table): %d" % unchanged)
print("arithmetic rewritten+identical==baseline: %s" % (sites + unchanged + sum(x.split('baseline ')[1].split(' branch')[0] for x in unpaired) == tot_b))
print("files whose declaration count moved (cannot pair line by line): %d %s" % (len(unpaired), unpaired))
print("findings (a migration that does not follow the stated rule): %d" % len(findings))
for x in findings[:25]:
    print("   ", x)

print("=== distinct baseline form -> branch form, with site counts ===")
agg = {}
for f, p, vb, va, w, g in rows:
    agg.setdefault((vb, va), [0, set()])
    agg[(vb, va)][0] += 1
    agg[(vb, va)][1].add(f.split("/")[-1])
for (vb, va), (n, fs) in sorted(agg.items(), key=lambda kv: (-kv[1][0], kv[0][0])):
    print("   %-4s %-32s -> %-48s %s" % (n, vb[:32], va[:48], ",".join(sorted(fs))))

print("=== residual literals: every radius declaration under frontend/src on the branch ===")
bad = []
for p in sorted((WT / "frontend/src").rglob("*.css")):
    t = p.read_text(encoding="utf-8")
    for m in DECL.finditer(t):
        stripped = re.sub(r"var\([^()]*\)", "", m.group(2))
        if re.search(r"\d", stripped):
            bad.append((str(p.relative_to(WT)), t[:m.start()].count("\n") + 1, m.group(2).strip()))
print("   count: %d" % len(bad))
for x in bad[:10]:
    print("   ", x)

print("=== the table itself, as defined on the branch ===")
tb = show(HEAD, "frontend/src/design-tokens.css")
defs = re.findall(r"^\s*(--cn-r-[a-z0-9]+):\s*([^;]+);", tb, re.M)
allowed = set(["var(--cn-r-%s)" % t for t in TIERS] + ["var(--cn-r-pill)", "var(--cn-r-circle)"]
              + ["%dpx" % t for t in TIERS] + ["50%", "999px"])
off = []
for name, val in defs:
    v = val.strip()
    if v not in allowed:
        off.append((name, v))
    print("   %-22s %s" % (name, v))
print("   definitions off the allowed set: %d %s" % (len(off), off))
d = dict(defs)
alias = {k: (int(re.search(r"--cn-r-(\d+)", d.get(k, "")).group(1))
             if re.search(r"--cn-r-(\d+)", d.get(k, "")) else d.get(k, "MISSING"))
         for k in SEMANTIC}
print("=== semantic aliases resolve to %s ; matches rule table: %s" % (alias, alias == SEMANTIC))
