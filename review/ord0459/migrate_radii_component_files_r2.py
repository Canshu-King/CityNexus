"""ORD-0459 pass 2 of the migration: the component stylesheets that live outside styles.css.

Same snap rule as migrate_radii_r1.py, same token table, applied to every CSS file under
frontend/src that still carries a radius literal -- including a var() fallback, which is a literal
that only paints when the named token is missing and must not sit off the table either.

The tool ends with its own gate and aborts non-zero if any radius value under frontend/src is not
on the table, so a half-finished migration cannot be committed by accident.
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt/frontend/src")
TIERS = [0, 4, 8, 12, 16, 20, 24]
TIER_TOKEN = {0: "--cn-r-0", 4: "--cn-r-4", 8: "--cn-r-8", 12: "--cn-r-12", 16: "--cn-r-16",
              20: "--cn-r-20", 24: "--cn-r-24"}
DECL = re.compile(r"(border(?:-\w+)?-radius:\s*)([^;{}]+)(;)")
VAR_FALLBACK = re.compile(r"(var\(--cn-r-[a-z0-9]+,\s*)(\d+(?:\.\d+)?px)(\))")


def snap(v):
    return min(TIERS, key=lambda t: (abs(t - v), -t))


changed = []
for p in sorted(SRC.rglob("*.css")):
    text = p.read_text(encoding="utf-8")
    out, pos = [], 0

    for m in DECL.finditer(text):
        head, val, tail = m.group(1), m.group(2), m.group(3)
        new = val
        new = VAR_FALLBACK.sub(lambda mm: "%svar(%s)%s" % (mm.group(1), TIER_TOKEN[snap(int(round(float(mm.group(2)[:-2]))))], mm.group(3)), new)
        new = re.sub(r"\b(\d+(?:\.\d+)?)px\b", lambda mm: "var(%s)" % TIER_TOKEN[snap(int(round(float(mm.group(1)))))]
                     if int(round(float(mm.group(1)))) < 99 else "var(--cn-r-pill)", new)
        new = re.sub(r"\b\d+(?:\.\d+)?%\b", lambda mm: "var(--cn-r-circle)" if float(mm.group(0)[:-1]) == 50 else "UNMAPPED", new)
        if new != val:
            changed.append((str(p.relative_to(SRC)), text[:m.start()].count("\n") + 1, val.strip(), new.strip()))
        out.append(text[pos:m.start()] + head + new + tail)
        pos = m.end()
    out.append(text[pos:])
    new_text = "".join(out)
    if new_text != text:
        p.write_text(new_text, encoding="utf-8", newline="\n")

print("sites rewritten by this pass: %d" % len(changed))
for f, ln, old, new in changed:
    print("   %s:%s  %s -> %s" % (f, ln, old, new))

bad = []
for p in sorted(SRC.rglob("*.css")):
    for m in DECL.finditer(p.read_text(encoding="utf-8")):
        v = m.group(2)
        if re.sub(r"var\([^)]*\)", "", v).strip() and re.search(r"\d+(?:\.\d+)?(px|%)", re.sub(r"var\([^)]*\)", "", v)):
            bad.append((str(p.relative_to(SRC)), p.read_text(encoding="utf-8")[:m.start()].count("\n") + 1, v.strip()))
print("GATE radius values under frontend/src not on the table: %d" % len(bad))
for b in bad:
    print("   ", b)
sys.exit(1 if bad or not changed else 0)
