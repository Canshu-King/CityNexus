"""ORD-0448 step 2: snap every hard-coded border-radius onto the tier table and name it.

Ladder (my prefix, one numeric table + semantic aliases pointing into it):
    0, 4, 8, 12, 16, 20, 24 px, plus circle (50%) and pill (999px).
Snap rule, stated so the diff can be argued with: nearest tier, ties to the LARGER tier, because
tightening a corner can clip content while loosening one cannot.
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
FILES = ["frontend/src/design-tokens.css", "frontend/src/styles.css"]
TIERS = [0, 4, 8, 12, 16, 20, 24]
TIER_TOKEN = {0: "--cn-r-0", 4: "--cn-r-4", 8: "--cn-r-8", 12: "--cn-r-12", 16: "--cn-r-16",
              20: "--cn-r-20", 24: "--cn-r-24"}
PILL, CIRCLE = "--cn-r-pill", "--cn-r-circle"


def snap(v):
    best = min(TIERS, key=lambda t: (abs(t - v), -t))          # ties -> larger tier
    return best


mapping = {}
changed = []
for f in FILES:
    path = WT / f
    text = path.read_text(encoding="utf-8")
    out = []
    pos = 0
    for m in re.finditer(r"(border(?:-\w+)?-radius:\s*)([^;{}]+)(;)", text):
        head, val, tail = m.group(1), m.group(2), m.group(3)
        new_val = val

        def sub_px(mm):
            v = float(mm.group(1))
            iv = int(round(v))
            if iv >= 50:                                        # the pill hack: 99 / 999 px
                return "var(%s)" % PILL
            t = snap(iv)
            return "var(%s)" % TIER_TOKEN[t]

        def sub_pct(mm):
            pct = float(mm.group(1))
            return "var(%s)" % CIRCLE if pct == 50 else "UNMAPPED-%sgp" % pct

        new_val = re.sub(r"\b(\d+(?:\.\d+)?)px\b", sub_px, new_val)
        new_val = re.sub(r"\b\d+(?:\.\d+)?%\b", sub_pct, new_val)
        if new_val != val:
            mapping.setdefault(val.strip(), new_val.strip())
            changed.append((f, text[:m.start()].count("\n") + 1, val.strip(), new_val.strip()))
        out.append(text[pos:m.start()] + head + new_val + tail)
        pos = m.end()
    out.append(text[pos:])
    path.write_text("".join(out), encoding="utf-8", newline="\n")

left = []
for f in FILES:
    for m in re.finditer(r"border(?:-\w+)?-radius:\s*([^;{}]+)", (WT / f).read_text(encoding="utf-8")):
        v = m.group(1)
        if re.search(r"\d+(?:\.\d+)?(px|%)", v):
            left.append((f, v.strip()))
print("rewritten sites:", len(changed))
print("distinct old -> new forms:")
for k, v in sorted(mapping.items(), key=lambda kv: -sum(1 for c in changed if c[2] == kv[0])):
    print("   %-28s -> %s" % (k, v))
print("radius declarations still carrying a literal:", len(left))
for f, v in left[:12]:
    print("   ", f, v)
import collections
per_file = collections.Counter(c[0] for c in changed)
print("per file:", dict(per_file))
