#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Counterexample arm for the SimulationPanel stage-copy migration.

Denominators are declared, not discovered:
  - 25  static inline bilingual pairs measured in SimulationPanel.tsx at the parent tip;
  - 23  moved into the lane dictionary by this cell;
  - 2   left inline verbatim because codes_on_screen_gate_r4 refuses a newly written rendered line
        carrying a raw server enum (NO_SCENARIO, ACTIVE).  They must still be byte-identical.

Usage: python simulation_stage_copy_arm_r1.py <repo-dir> <parent-tip> <candidate-ref>
Exit 0 = every claim held;  exit 9 = a claim broke (printed with its cause).
"""
import io, json, re, subprocess, sys

PAIR_SHAPE = re.compile(r'^(\s*)(zh|en)\s*:\s*"(.*)",\s*$')

MOVED = 23
# The two pairs this cell leaves inline, named by their line at the parent tip so the arm never
# retypes product copy: :206 carries NO_SCENARIO, :235 carries ACTIVE.
BLOCKED_LINES = [206, 235]


def git(repo, *a):
    p = subprocess.run(["git", "-C", repo] + list(a), capture_output=True)
    if p.returncode != 0:
        raise SystemExit("git failed %s :: %s" % (a[:2], (p.stderr or b"")[-200:]))
    return (p.stdout or b"").decode("utf-8", "replace")


def pairs(src):
    """Adjacent same-indent zh:/en: string literals -- the inline bilingual shape."""
    lines = src.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = PAIR_SHAPE.match(lines[i])
        m2 = PAIR_SHAPE.match(lines[i + 1]) if i + 1 < len(lines) else None
        if m and m2 and m.group(2) != m2.group(2) and m.group(1) == m2.group(1):
            zh, en = (m.group(3), m2.group(3)) if m.group(2) == "zh" else (m2.group(3), m.group(3))
            if "${" not in zh and "${" not in en:
                out.append({"line": i + 1, "zh": zh, "en": en})
            i += 2
            continue
        i += 1
    return out


def module_arms(src):
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
        print("%-52s %s %s" % (name, "HELD" if ok else "BROKE", detail))
        if not ok:
            fails.append(name)

    old_pairs = pairs(before)
    claim("measured denominator: parent carried 25 inline pairs", len(old_pairs) == 25,
          "count=%d" % len(old_pairs))

    arms = module_arms(modsrc)
    claim("dictionary carries %d keys" % MOVED, len(arms) == MOVED, "count=%d" % len(arms))

    moved = re.findall(r'\.\.\.simulationStagePair\("([A-Za-z0-9_]+)"\)', after)
    claim("component names %d dictionary keys" % MOVED, len(moved) == MOVED, "count=%d" % len(moved))
    claim("component names each key once", len(set(moved)) == len(moved), "distinct=%d" % len(set(moved)))
    claim("every key it names exists in the dictionary",
          all(k in arms for k in moved), str([k for k in moved if k not in arms])[:160])

    # match by text, not by line: the 2 blocked pairs stay where they were
    blocked = [(p["zh"], p["en"]) for p in old_pairs if p["line"] in BLOCKED_LINES]
    if len(blocked) != len(BLOCKED_LINES):
        raise SystemExit("ABORT: could not find the declared blocked lines in the parent read: %s"
                         % BLOCKED_LINES)
    blocked_set = set(blocked)
    old_moved = [p for p in old_pairs if (p["zh"], p["en"]) not in blocked_set]
    claim("parent minus the two blocked pairs leaves %d" % MOVED, len(old_moved) == MOVED,
          "count=%d" % len(old_moved))
    mismatched = []
    for idx, key in enumerate(moved):
        if idx >= len(old_moved):
            mismatched.append((key, "no source pair at index %d" % idx))
            continue
        if key not in arms:
            mismatched.append((key, "not in dictionary"))
            continue
        if arms[key] != (old_moved[idx]["zh"], old_moved[idx]["en"]):
            mismatched.append((key, "arms differ from parent line %s" % old_moved[idx]["line"]))
    claim("every word byte-equal to the line it came from", not mismatched,
          json.dumps(mismatched, ensure_ascii=False)[:220])

    # the two refused pairs must NOT have been quietly edited or deleted
    kept = [(p["zh"], p["en"]) for p in pairs(after)]
    claim("the two refused pairs are still inline, byte-identical",
          all(pair in kept for pair in blocked), "inline_now=%d" % len(kept))
    claim("exactly the two refused pairs remain inline", len(kept) == len(BLOCKED_LINES),
          "count=%d" % len(kept))

    zh_arm = 'return locale.startsWith("zh") ? arms.zh : arms.en;'
    claim("locale rule still selects the Chinese arm", zh_arm in modsrc)
    claim("anything-not-zh takes the English arm", "arms.en" in modsrc)
    claim("component imports the dictionary module",
          'import { simulationStagePair } from "../../i18n/simulationStageCopy";' in after)

    embedded = sorted(k for k, (z, e) in arms.items() if z in after)
    print("%-52s INFO  %s" % ("captions still quoted inside longer copy",
                              json.dumps(embedded, ensure_ascii=False)))

    print("")
    print("FAIL %d" % len(fails))
    return 0 if not fails else 9


if __name__ == "__main__":
    sys.exit(main())
