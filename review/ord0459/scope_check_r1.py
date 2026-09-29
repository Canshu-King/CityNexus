"""ORD-0459 scope check -- prove that nothing but a corner radius moved.

Parse both stylesheets into rules (selector -> declarations) straight from the git objects, pair them
by selector, and print every property that differs. The claim being tested is the one the order rests
on: this change must not touch the ORD-0430 pill yield-at-rest semantics, no colour, no size, no
spacing. Anything that shows up here as a non-radius property difference is a regression to argue
about, so the tool prints the whole rule text for those selectors rather than a summary.
"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = "D:/moodle/_qoder_q_ord0427_20260929/wt"
TIP = "57ff5d1c2f8540d498d945ed591c36689fc0f39e"
FILES = ["frontend/src/styles.css", "frontend/src/design-tokens.css", "frontend/src/v10.css",
         "frontend/src/map-controls.css", "frontend/src/features/access/access.css",
         "frontend/src/features/discovery/discovery-batch.css",
         "frontend/src/features/planning/planRanking.css",
         "frontend/src/features/simulation/SimulationPanel.css"]


def show(ref, path):
    return subprocess.run(["git", "-C", WT, "show", "%s:%s" % (ref, path)],
                          capture_output=True, text=True, encoding="utf-8").stdout


def rules(text):
    """selector -> list of (property, value), by document order; @media bodies are flattened with a marker."""
    out, ctx, i, buf = {}, [], 0, ""
    depth = 0
    sel_start = 0
    result = []
    # crude but adequate brace scanner: capture (selector, body) pairs at any nesting depth
    while i < len(text):
        c = text[i]
        if c == "{":
            sel = text[sel_start:i].strip().splitlines()[-1].strip()
            j = i + 1
            d = 1
            while j < len(text) and d:
                if text[j] == "{":
                    d += 1
                elif text[j] == "}":
                    d -= 1
                j += 1
            body = text[i + 1:j - 1]
            result.append((sel, body, text[sel_start:i]))
            i = j
            sel_start = j
            continue
        if c == "}":
            sel_start = i + 1
        i += 1
    return result


def decls(body):
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return [(m.group(1).strip(), m.group(2).strip())
            for m in re.finditer(r"([-\w]+)\s*:\s*([^;]+);", body)]


total_rules = diff_rules = 0
nonscope = []
per_file = {}
for f in FILES:
    a = rules(show(TIP, f))
    b = rules(show("HEAD", f))
    same, changed, only_a, only_b = 0, 0, [], []
    mapA = {}
    for sel, body, _ in a:
        mapA.setdefault(sel, []).append(body)
    mapB = {}
    for sel, body, _ in b:
        mapB.setdefault(sel, []).append(body)
    for sel in mapA:
        if sel not in mapB:
            only_a.append(sel)
            continue
        for body_a, body_b in zip(mapA[sel], mapB[sel]):
            total_rules += 1
            da, db = decls(body_a), decls(body_b)
            if da == db:
                same += 1
                continue
            changed += 1
            props_a = [p for p, _ in da]
            props_b = [p for p, _ in db]
            added = [p for p in props_b if p not in props_a]
            removed = [p for p in props_a if p not in props_b]
            if added or removed:
                # adding a tier token to the table is in scope; anything else is not
                if all(re.fullmatch(r"--cn-r-[a-z0-9]+", p) for p in added) and not removed:
                    continue
                nonscope.append((f, sel, "property set changed: added=%s removed=%s" % (added, removed),
                                 props_a, props_b, body_a, body_b))
                continue
            bad = [(pa, va, vb) for (pa, va), (pb, vb) in zip(da, db) if va != vb and "radius" not in pa]
            if bad:
                nonscope.append((f, sel, "non-radius value changed", bad, None, body_a, body_b))
    only_b = [s for s in mapB if s not in mapA]
    per_file[f] = {"rules_paired": same + changed, "identical": same, "radius-only-changed": changed,
                   "selectors_only_on_tip": len(only_a), "selectors_only_on_branch": len(only_b)}
    for s in only_a:
        per_file[f].setdefault("note_only_on_tip", []).append(s)
    for s in only_b:
        per_file[f].setdefault("note_only_on_branch", []).append(s)

print("=== per file ===")
for f in FILES:
    print("   %-56s %s" % (f, per_file[f]))
print("rules paired across the two trees: %d" % total_rules)
print("=== out-of-scope findings (anything that is not a radius) : %d ===" % len(nonscope))
for n in nonscope:
    print("   %s  selector=%s  %s" % (n[0], n[1], n[2]))
    print("      detail: %s" % str(n[3])[:220])
    print("      rule on tip:    %s" % " ".join(n[5].split())[:220])
    print("      rule on branch: %s" % " ".join(n[6].split())[:220])

print("=== the ORD-0430 semantics, named and compared verbatim ===")


def named(f, ref, needle):
    """Every rule whose selector contains needle, as selector -> declaration list."""
    return {sel: ["%s: %s" % d for d in decls(body)]
            for sel, body, _ in rules(show(ref, f)) if needle in sel}


for needle in ("yield-at-rest", "cn-copilot-edge", "cn-copilot-dock"):
    for f in ("frontend/src/styles.css", "frontend/src/design-tokens.css"):
        a, b = named(f, TIP, needle), named(f, "HEAD", needle)
        if not a and not b:
            continue
        print("   %-14s %-32s rules tip=%d branch=%d  verbatim equal=%s" % (
            needle, f, len(a), len(b), a == b))
        if a != b:
            for sel in sorted(set(a) | set(b)):
                if a.get(sel) != b.get(sel):
                    print("      %s" % sel)
                    print("         tip:    %s" % " | ".join(a.get(sel, ["ABSENT"])))
                    print("         branch: %s" % " | ".join(b.get(sel, ["ABSENT"])))
print("exit: %d out-of-scope findings" % len(nonscope))
sys.exit(1 if nonscope else 0)
