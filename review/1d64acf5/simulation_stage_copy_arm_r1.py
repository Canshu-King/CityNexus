#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Counterexample arm for the SimulationPanel stage-copy migration.

Denominator is declared, not discovered: the 25 static inline bilingual pairs measured in
frontend/src/features/simulation/SimulationPanel.tsx at the parent tip.  Nothing here relaxes.

Usage:
  python simulation_stage_copy_arm_r1.py <repo-dir> <parent-tip> <candidate-ref>
Exit 0 = every claim held;  exit 9 = a claim broke (printed with its cause).
"""
import io, json, re, subprocess, sys

PAIR_SHAPE = re.compile(r'^(\s*)(zh|en)\s*:\s*"(.*)",\s*$')


def git(repo, *a):
    p = subprocess.run(["git", "-C", repo] + list(a), capture_output=True)
    if p.returncode != 0:
        raise SystemExit("git failed %s :: %s" % (a[:2], (p.stderr or b"")[-200:]))
    return (p.stdout or b"").decode("utf-8", "replace")


def pairs(src, keep_static_only=True):
    """Adjacent same-indent zh:/en: literals, returned with the source line of the first arm."""
    lines = src.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = PAIR_SHAPE.match(lines[i])
        m2 = PAIR_SHAPE.match(lines[i + 1]) if i + 1 < len(lines) else None
        if m and m2 and m.group(2) != m2.group(2) and m.group(1) == m2.group(1):
            zh, en = (m.group(3), m2.group(3)) if m.group(2) == "zh" else (m2.group(3), m.group(3))
            if "${" not in zh and "${" not in en:
                out.append({"line": i + 1, "indent": len(m.group(1)), "zh": zh, "en": en})
            i += 2
            continue
        i += 1
    return out


def module_arms(src):
    """key -> (zh, en) from the dictionary's COPY table, verbatim source literals."""
    out = {}
    for m in re.finditer(r'^  ([A-Za-z0-9_]+): \{ zh: "(.*)", en: "(.*)"\s*\},\s*$', src, re.M):
        out[m.group(1)] = (m.group(2), m.group(3))
    return out


def main():
    repo, parent, cand = sys.argv[1], sys.argv[2], sys.argv[3]
    comp = "frontend/src/features/simulation/SimulationPanel.tsx"
    mod = "frontend/src/i18n/simulationStageCopy.ts"
    before = git(repo, "show", "%s:%s" % (parent, comp))
    after = git(repo, "show", "%s:%s" % (cand, comp))
    modsrc = git(repo, "show", "%s:%s" % (cand, mod))

    fails = []

    def claim(name, ok, detail=""):
        print("%-46s %s %s" % (name, "HELD" if ok else "BROKE", detail))
        if not ok:
            fails.append(name)

    old_pairs = pairs(before)
    claim("denominator: parent really had 25 pairs", len(old_pairs) == 25, "count=%d" % len(old_pairs))

    arms = module_arms(modsrc)
    claim("dictionary carries 25 keys", len(arms) == 25, "count=%d" % len(arms))

    # every arm moved out must be byte-identical, in the order the pairs appeared
    moved = re.findall(r'\.\.\.simulationStagePair\("([A-Za-z0-9_]+)"\)', after)
    claim("component names 25 dictionary keys", len(moved) == 25, "count=%d" % len(moved))
    claim("component names each key once", len(set(moved)) == len(moved),
          "distinct=%d" % len(set(moved)))

    mismatched = []
    for idx, key in enumerate(moved):
        if idx >= len(old_pairs):
            mismatched.append((key, "no source pair at index %d" % idx))
            continue
        if key not in arms:
            mismatched.append((key, "not in dictionary"))
            continue
        if (arms[key][0], arms[key][1]) != (old_pairs[idx]["zh"], old_pairs[idx]["en"]):
            mismatched.append((key, "arms differ from %s" % old_pairs[idx]["line"]))
    claim("every word byte-equal to the line it came from", not mismatched,
          json.dumps(mismatched, ensure_ascii=False)[:220])

    # selection behaviour the component keeps: zh-prefixed locale takes the Chinese arm
    zh_arm = 'return locale.startsWith("zh") ? arms.zh : arms.en;'
    claim("locale rule still selects the Chinese arm", zh_arm in modsrc)
    claim("anything-not-zh takes the English arm", "arms.en" in modsrc)

    # no inline copy left in the component for the migrated shape
    claim("no static inline bilingual pair left in component", len(pairs(after)) == 0,
          "left=%d" % len(pairs(after)))
    claim("component imports the dictionary module",
          'import { simulationStagePair } from "../../i18n/simulationStageCopy";' in after)

    # the module must be the only carrier of the migrated PAIR SHAPE; a short caption may still
    # appear quoted inside an unmigrated interpolated sentence -- that is reported, not hidden.
    shape_left = [k for k, (z, e) in arms.items() if ('zh: "%s",' % z) in after]
    claim("no migrated pair left in its inline shape", not shape_left, str(shape_left)[:180])
    embedded = sorted(k for k, (z, e) in arms.items() if z in after)
    print("%-46s INFO  %s" % ("captions still quoted inside longer copy", json.dumps(embedded, ensure_ascii=False)))

    print("")
    print("FAIL %d" % len(fails))
    return 0 if not fails else 9


if __name__ == "__main__":
    sys.exit(main())
