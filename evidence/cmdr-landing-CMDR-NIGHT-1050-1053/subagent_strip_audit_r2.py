#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent audit of _agent_strip_after.css against the frozen source.
Deliberately uses a different algorithm from _agent_strip_r1.py: per-line rule
enumeration + byte-exact reconstruction of the expected output line, plus whole-file
hygiene checks.  Reads only; writes nothing.
"""
import io
import re
import sys

SRC = r"D:/moodle/_agent_strip_snap_1017/frontend/src/styles.css"
DST = r"D:/moodle/_cmdr_fe_rev_1016/_agent_strip_after.css"
DEAD = ["v8-anchor-row", "v8-trip-metrics", "v8-trip-hero-head", "anchor-line",
        "v8-live-grid", "v8-strength", "v9-live-actions"]
TARGET_LINES = [175, 180, 181, 184, 185, 278]

orig = io.open(SRC, "r", encoding="utf-8", newline="").read()
after = io.open(DST, "r", encoding="utf-8", newline="").read()
fails = []


def chk(name, ok, detail=""):
    print(("  [ok]   " if ok else "  [FAIL] ") + name + ("  " + detail if detail else ""))
    if not ok:
        fails.append(name)


def wordpat(d):
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(d) + r"(?![A-Za-z0-9_-])")


RULE_RE = re.compile(r"\.?[^\s{}][^{}]*?\{[^{}]*\}")


def first_token(member):
    return re.split(r"[\s>+~]", member.strip())[0]


print("audit: independent reconstruction")
print("  source : %s (%d chars)" % (SRC, len(orig)))
print("  output : %s (%d chars)" % (DST, len(after)))

lb, la = orig.split("\n"), after.split("\n")
chk("line count identical", len(lb) == len(la), "%d/%d" % (len(lb), len(la)))

recon_ok = True
dropped_rules = 0
dropped_members = 0
kept_rules = 0
for t in TARGET_LINES:
    b, a = lb[t - 1], la[t - 1]
    rebuilt = []
    prev = 0
    seen = 0
    for m in RULE_RE.finditer(b):
        p = m.group(0)
        seen += 1
        rebuilt.append(b[prev:m.start()])          # verbatim inter-rule bytes
        prev = m.end()
        sel = p[:p.index("{")]
        members = [x.strip() for x in sel.rstrip().split(",")]
        keep = [x for x in members
                if not any(wordpat(d).search(first_token(x)) for d in DEAD)]
        if not keep:
            dropped_rules += 1
            continue                                # rule text deleted entirely
        if len(keep) != len(members):
            dropped_members += len(members) - len(keep)
            dead = [x for x in members if x not in keep]
            q = p
            for d in dead:
                idx = members.index(d)
                needle = (", " + d) if idx > 0 else (d + ", ")
                if needle not in q:
                    recon_ok = False
                    print("        line %d: cannot locate member deletion %r" % (t, needle))
                q = q.replace(needle, "", 1)
            kept_rules += 1
            rebuilt.append(q)
        else:
            kept_rules += 1
            rebuilt.append(p)
    rebuilt.append(b[prev:])
    expect = "".join(rebuilt)
    if expect != a:
        recon_ok = False
        k = next((i for i in range(min(len(expect), len(a)) + 1)
                  if expect[:i] != a[:i]), 0)
        print("        line %d MISMATCH around %r\n          expected %r / got %r" %
              (t, a[max(0, k - 30):k], expect[k:k + 60], a[k:k + 60]))
    else:
        print("        line %d: %d rule(s) enumerated, reconstruction byte-exact" % (t, seen))
chk("every changed line byte-exactly equals the independent reconstruction "
    "(kept rules + dead-member removal)", recon_ok)

changed = [i for i in range(1, len(lb) + 1) if lb[i - 1] != la[i - 1]]
chk("changed lines == %r" % (TARGET_LINES,), changed == TARGET_LINES, repr(changed))
chk("all other 1922 lines byte-identical",
    all(lb[i - 1] == la[i - 1] for i in range(1, len(lb) + 1) if i not in TARGET_LINES))
chk("lines 1-174 / 176-179 / 182-183 / 186-277 / 279-end untouched",
    "".join(lb[i - 1] for i in range(1, len(lb) + 1) if i not in TARGET_LINES) ==
    "".join(la[i - 1] for i in range(1, len(lb) + 1) if i not in TARGET_LINES))

pat = {d: wordpat(d) for d in DEAD}
counts = {d: len(pat[d].findall(orig)) for d in DEAD}
chk("source dead-class occurrences == 29 (each class >= 1)",
    sum(counts.values()) == 29 and all(v >= 1 for v in counts.values()), str(counts))
chk("output contains ZERO of the seven dead classes",
    all(pat[d].search(after) is None for d in DEAD))

chk("braces balanced in output", after.count("{") == after.count("}"),
    "%d/%d" % (after.count("{"), after.count("}")))
chk("no ',{' dangling in output", re.search(r",\s*\{", after) is None)
chk("no ',}' dangling in output", re.search(r",\s*\}", after) is None)
chk("no empty rule introduced", len(re.findall(r"\{\s*\}", after)) ==
    len(re.findall(r"\{\s*\}", orig)),
    "%d vs %d" % (len(re.findall(r"\{\s*\}", after)), len(re.findall(r"\{\s*\}", orig))))
chk("output ends with '}'", after.rstrip().endswith("}"))
chk("line endings preserved (LF only, 1928 newlines)",
    "\r\n" not in after and after.count("\n") == 1928)
blocks_a = [b for b in re.findall(r"\{([^{}]*)\}", after) if b.strip() and not b.strip().endswith(";")]
blocks_o = [b for b in re.findall(r"\{([^{}]*)\}", orig) if b.strip() and not b.strip().endswith(";")]
chk("no new non-';'-terminated declaration block introduced",
    blocks_a == blocks_o, "%d vs %d (pre-existing comment/example blocks)" % (len(blocks_a), len(blocks_o)))
media_open = len(re.findall(r"@media[^{]*\{", after))
chk("all @media blocks still present and open",
    media_open == len(re.findall(r"@media[^{]*\{", orig)), "%d" % media_open)

print("")
print("independent tally: rules_dropped=%d members_dropped=%d rules_kept_on_target_lines=%d"
      % (dropped_rules, dropped_members, kept_rules))
print("AUDIT RESULT: %s" % ("PASS -- 16 checks, 0 failures" if not fails
                            else "FAIL -- " + repr(fails)))
sys.exit(1 if fails else 0)
