#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MECHANICAL dead-class strip of a frozen styles.css export (rev 41130d39a9a0addc0a66e14069e5333c898f9720).

Reads  : D:/moodle/_agent_strip_snap_1017/frontend/src/styles.css   (read-only)
Writes : D:/moodle/_cmdr_fe_rev_1016/_agent_strip_after.css
         D:/moodle/_cmdr_fe_rev_1016/_agent_strip_manifest.json

Nothing is written unless every self-check passes (abort otherwise).
Parsing is done with a brace/string/comment aware scanner, never a regex over a line.
"""

import bisect
import difflib
import io
import json
import os
import re
import sys

SRC = r"D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src/styles.css"
DST = r"D:/moodle/_cmdr_fe_rev_1016/_strip_on_tip_after.css"
MAN = r"D:/moodle/_cmdr_fe_rev_1016/_strip_on_tip_manifest.json"

DEAD = ["v8-anchor-row", "v8-trip-metrics", "v8-trip-hero-head", "anchor-line",
        "v8-live-grid", "v8-strength", "v9-live-actions"]
TARGET_LINES = [175, 180, 181, 184, 185, 278]
NEG_PSEUDOS = {"not", "is", "where", "matches", "has"}

FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("  [ok]   %s%s" % (name, ("  " + detail) if detail else ""))
    else:
        FAILS.append(name)
        print("  [FAIL] %s  %s" % (name, detail))
    return bool(ok)


def die(msg):
    print("ABORT: " + msg)
    sys.exit(1)


# --------------------------------------------------------------------------- #
# scanner primitives
# --------------------------------------------------------------------------- #
def skip_comment(t, i):
    j = t.find("*/", i + 2)
    return len(t) if j < 0 else j + 2


def skip_string(t, i):
    q = t[i]
    j = i + 1
    n = len(t)
    while j < n:
        c = t[j]
        if c == "\n":
            return j
        if c == q:
            return j + 1
        j += 1
    return n


def match_brace(t, i):
    """index of the '}' closing the '{' at i, string/comment aware; None if unbalanced."""
    depth = 0
    j = i
    n = len(t)
    while j < n:
        c = t[j]
        if t.startswith("/*", j):
            j = skip_comment(t, j)
            continue
        if c in "\"'":
            j = skip_string(t, j)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return None


def trim_span(t, a, b):
    while a < b and t[a].isspace():
        a += 1
    while b > a and t[b - 1].isspace():
        b -= 1
    return a, b


IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


class Rule(object):
    __slots__ = ("sel", "sel_a", "sel_b", "inner_a", "inner_b", "close",
                 "a", "b", "ancestry", "line")

    def __init__(self, sel, sel_a, sel_b, inner_a, inner_b, close, ancestry, line):
        self.sel = sel
        self.sel_a, self.sel_b = sel_a, sel_b
        self.inner_a, self.inner_b = inner_a, inner_b
        self.close = close
        self.a, self.b = sel_a, close + 1          # full rule span (half-open)
        self.ancestry = ancestry
        self.line = line


def scan_rules(t):
    """Flat list of (selector_text, declaration_text) rule records with file offsets."""
    rules = []
    problems = []
    stack = []                                    # preludes of open @-rule blocks
    i = 0
    n = len(t)
    seg_start = 0
    nlpos = [k for k, ch in enumerate(t) if ch == "\n"]

    def lineno(off):
        return bisect.bisect_left(nlpos, off) + 1

    while i < n:
        c = t[i]
        if c == "\n":
            i += 1
            continue
        if t.startswith("/*", i):
            i = skip_comment(t, i)
            continue
        if c in "\"'":
            i = skip_string(t, i)
            continue
        if c == "{":
            a, b = trim_span(t, seg_start, i)
            prelude = t[a:b]
            close = match_brace(t, i)
            if close is None:
                problems.append("unbalanced '{' at offset %d" % i)
                break
            if prelude.startswith("@"):
                stack.append(prelude)
                i += 1                       # descend: keep scanning inside the block
                seg_start = i
                continue
            rules.append(Rule(prelude, a, b, i + 1, close, close,
                              tuple(stack), lineno(a)))
            i = close + 1
            seg_start = i
            continue
        if c == "}":
            if stack:
                stack.pop()
            else:
                problems.append("stray '}' at offset %d" % i)
            i += 1
            seg_start = i
            continue
        if c == ";":
            i += 1
            seg_start = i
            continue
        i += 1
    if stack:
        problems.append("blocks left open at EOF: %r" % (stack,))
    return rules, problems


# --------------------------------------------------------------------------- #
# selector anatomy
# --------------------------------------------------------------------------- #
def split_members(sel):
    """top-level comma split -> list of trimmed (a, b) offsets into sel + separators."""
    parts = []
    depth = 0
    cur = 0
    i = 0
    n = len(sel)
    while i < n:
        c = sel[i]
        if sel.startswith("/*", i):
            i = skip_comment(sel, i)
            continue
        if c in "\"'":
            i = skip_string(sel, i)
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(trim_span(sel, cur, i))
            cur = i + 1
        i += 1
    parts.append(trim_span(sel, cur, n))
    members = [(a, b) for a, b in parts if b > a]
    seps = []
    for k in range(len(members) - 1):
        seps.append(sel[members[k][1]:members[k + 1][0]])
    return members, seps


def split_compounds(member):
    """split a member selector into compounds at top-level combinators."""
    out = []
    depth = 0
    buf = 0
    i = 0
    n = len(member)
    while i < n:
        c = member[i]
        if member.startswith("/*", i):
            i = skip_comment(member, i)
            continue
        if c in "\"'":
            i = skip_string(member, i)
            continue
        if c in "([":
            depth += 1
            i += 1
            continue
        if c in ")]":
            depth -= 1
            i += 1
            continue
        if depth == 0 and (c.isspace() or c in ">+~"):
            seg = member[buf:i].strip()
            if seg:
                out.append(seg)
            while i < n and (member[i].isspace() or member[i] in ">+~"):
                i += 1
            buf = i
            continue
        i += 1
    seg = member[buf:].strip()
    if seg:
        out.append(seg)
    return out


def compound_classes(compound):
    """-> (positive classes, negative classes [inside :not/:is/:where/:has], attr-value mentions)"""
    pos = []
    neg = []
    attr = []
    i = 0
    n = len(compound)
    while i < n:
        c = compound[i]
        if compound.startswith("/*", i):
            i = skip_comment(compound, i)
            continue
        if c in "\"'":
            j = skip_string(compound, i)
            attr.append(compound[i + 1:j - 1])
            i = j
            continue
        if c == "[":
            j = match_bracket(compound, i)
            inner = compound[i + 1:j]
            for m in re.finditer(r"""(["'])((?:[^"'\\]|\\.)*)\1""", inner):
                attr.append(m.group(2))
            i = j + 1
            continue
        if c == ":" and i + 1 < n:
            m = re.compile(r"::?([A-Za-z-]+)\s*\(").match(compound, i)
            if m:
                name = m.group(1).lower()
                j = match_paren(compound, i + m.end(0) - 1)
                arg = compound[i + m.end(0):j]
                if name in NEG_PSEUDOS:
                    sub_pos, sub_neg, _ = compound_classes(arg)
                    neg.extend(sub_pos)
                    neg.extend(sub_neg)
                i = j + 1
                continue
        if c == ".":
            m = IDENT.match(compound, i + 1)
            if m:
                pos.append(m.group(0))
                i = m.end()
                continue
        i += 1
    return pos, neg, attr


def match_paren(t, i):
    depth = 0
    j = i
    n = len(t)
    while j < n:
        c = t[j]
        if t.startswith("/*", j):
            j = skip_comment(t, j)
            continue
        if c in "\"'":
            j = skip_string(t, j)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n


def match_bracket(t, i):
    depth = 0
    j = i
    n = len(t)
    while j < n:
        c = t[j]
        if t.startswith("/*", j):
            j = skip_comment(t, j)
            continue
        if c in "\"'":
            j = skip_string(t, j)
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n


def line_of(text, off):
    return text.count("\n", 0, off) + 1


# --------------------------------------------------------------------------- #
# plan
# --------------------------------------------------------------------------- #
def main():
    if not os.path.isfile(SRC):
        die("input missing: " + SRC)
    with io.open(SRC, "r", encoding="utf-8", newline="") as f:
        orig = f.read()

    print("source           : %s" % SRC)
    print("source chars     : %d   newlines: %d   crlf: %d" %
          (len(orig), orig.count("\n"), orig.count("\r\n")))
    print("dead classes     : %s" % ", ".join(DEAD))

    rules, problems = scan_rules(orig)
    if problems:
        die("original file does not scan cleanly: %r" % (problems,))
    print("scanned rules    : %d (flat selector/declaration pairs)" % len(rules))

    dead_in_orig = {}
    for d in DEAD:
        pat = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(d) + r"(?![A-Za-z0-9_-])")
        hits = [(i, len(pat.findall(ln))) for i, ln in enumerate(orig.split("\n"), 1)
                if pat.search(ln)]
        dead_in_orig[d] = sum(c for _, c in hits)
    if sum(dead_in_orig.values()) != 29:
        die("dead-class occurrence recount != 29: %r" % (dead_in_orig,))
    print("occurrence recount: %d  %s" % (sum(dead_in_orig.values()), dead_in_orig))

    edits = []        # (start, end, replacement, entry_dict) -- all replacements are "" (pure deletes)
    mod_expected = {}  # (sel_a, sel_b) -> selector text after the member deletion
    manifest = []
    kept_entries = []

    for r in rules:
        if r.ancestry and r.ancestry[-1].startswith("@keyframes"):
            continue                                   # keyframe percentage selectors
        members, seps = split_members(r.sel)
        mtexts = [r.sel[a:b] for a, b in members]
        dead_anchor_idx = []
        anc_live_idx = []
        not_live_idx = []
        deciding = {}
        for k, mtext in enumerate(mtexts):
            comps = split_compounds(mtext)
            if not comps:
                continue
            p0, n0, _a0 = compound_classes(comps[0])
            pd = set(p0) & set(DEAD)
            rest_pos = []
            rest_neg = []
            for cp in comps[1:]:
                p, ng, at = compound_classes(cp)
                rest_pos.extend(p)
                rest_neg.extend(ng)
            pd_rest = set(rest_pos) & set(DEAD)
            pd_neg = (set(rest_neg) | set(n0)) & set(DEAD)
            if pd:
                dead_anchor_idx.append(k)
                deciding[k] = sorted(pd)
            elif pd_rest:
                anc_live_idx.append(k)
                deciding.setdefault(k, sorted(pd_rest))
            elif pd_neg:
                not_live_idx.append(k)
                deciding.setdefault(k, sorted(pd_neg))

        if not dead_anchor_idx and not anc_live_idx and not not_live_idx:
            continue

        # report every dead mention we found, kept or dropped
        for k in anc_live_idx:
            kept_entries.append({
                "class": ",".join(deciding.get(k, DEAD)),
                "line": r.line,
                "action": "kept_because_ancestor_live",
                "selector_before": r.sel,
                "selector_after_or_null": r.sel,
                "decl_bytes": len(orig[r.inner_a:r.inner_b].strip().encode("utf-8")),
                "chars_removed": 0,
            })
        for k in not_live_idx:
            kept_entries.append({
                "class": ",".join(deciding.get(k, DEAD)),
                "line": r.line,
                "action": "kept_because_not_of_live_ancestor",
                "selector_before": r.sel,
                "selector_after_or_null": r.sel,
                "decl_bytes": len(orig[r.inner_a:r.inner_b].strip().encode("utf-8")),
                "chars_removed": 0,
            })

        if not dead_anchor_idx:
            continue

        decl_stripped = orig[r.inner_a:r.inner_b].strip()
        decl_bytes = len(decl_stripped.encode("utf-8"))

        if len(dead_anchor_idx) == len(mtexts):
            span = (r.a, r.b)
            removed = orig[span[0]:span[1]]
            if "\n" in removed:
                die("removal span crosses a newline (line %d): %r" % (r.line, removed[:60]))
            edits.append((span[0], span[1], "", {
                "class": ",".join(sorted({c for k in dead_anchor_idx for c in deciding.get(k, [])})),
                "line": r.line,
                "action": "drop_rule",
                "selector_before": r.sel,
                "selector_after_or_null": None,
                "decl_bytes": decl_bytes,
                "chars_removed": span[1] - span[0],
            }))
        else:
            survivors = [k for k in range(len(mtexts)) if k not in dead_anchor_idx]
            if len(set(seps)) > 1:
                die("mixed inter-member separators on line %d: %r" % (r.line, seps))
            sep = seps[0] if seps else ", "
            new_sel = sep.join(mtexts[k] for k in survivors)
            if len(dead_anchor_idx) != 1:
                die("more than one dead member in one comma list (line %d): %r"
                    % (r.line, r.sel))
            k = dead_anchor_idx[0]
            if k < len(members) - 1:
                span = (r.sel_a + members[k][0], r.sel_a + members[k + 1][0])
            else:
                span = (r.sel_a + members[k - 1][1], r.sel_a + members[k][1])
            dead_text = orig[span[0]:span[1]]
            if "\n" in dead_text:
                die("member removal span crosses a newline (line %d)" % r.line)
            if orig[r.sel_a:span[0]] + orig[span[1]:r.sel_b] != new_sel:
                die("deletion does not reproduce the rebuilt selector on line %d: %r"
                    % (r.line, r.sel))
            mod_expected[(r.sel_a, r.sel_b)] = new_sel
            edits.append((span[0], span[1], "", {
                "class": ",".join(sorted({c for kk in dead_anchor_idx for c in deciding.get(kk, [])})),
                "line": r.line,
                "action": "drop_list_member",
                "selector_before": r.sel,
                "selector_after_or_null": new_sel,
                "decl_bytes": decl_bytes,
                "chars_removed": span[1] - span[0],
            }))

    if not edits:
        die("no rules classified for removal -- plan is empty")

    edits.sort(key=lambda e: (e[0], e[1]))
    for i in range(1, len(edits)):
        if edits[i][0] < edits[i - 1][1]:
            die("overlapping edit spans: %r" % (edits[i - 1][:2], edits[i][:2]))

    # ---- splice ----------------------------------------------------------- #
    out = []
    prev = 0
    for a, b, rep, _e in edits:
        out.append(orig[prev:a])
        out.append(rep)
        prev = b
    out.append(orig[prev:])
    after = "".join(out)
    removed_total = sum((b - a) - len(rep) for a, b, rep, _e in edits)
    if len(orig) - len(after) != removed_total:
        die("char accounting mismatch")

    entries = [e for _a, _b, _r, e in edits] + kept_entries
    entries.sort(key=lambda e: (e["line"], e["action"] == "kept_because_not_of_live_ancestor",
                                e["selector_before"]))
    removed_lines = sorted({e["line"] for e in entries
                            if e["action"] in ("drop_rule", "drop_list_member")})

    # ------------------------------------------------------------------ #
    # SELF-CHECKS
    # ------------------------------------------------------------------ #
    print("")
    print("self-checks")
    orig_pairs = [(r.sel, orig[r.inner_a:r.inner_b]) for r in rules]
    a_rules, a_probs = scan_rules(after)
    after_pairs = [(r.sel, after[r.inner_a:r.inner_b]) for r in a_rules]

    check("transformed file scans cleanly", not a_probs, str(a_probs))

    # expected pair list derived independently from the plan
    expected = []
    drop_spans = {(a, b) for a, b, rep, e in edits if e["action"] == "drop_rule"}
    mod_by_span = dict(mod_expected)
    for r in rules:
        if (r.a, r.b) in drop_spans:
            continue
        rep = mod_by_span.get((r.sel_a, r.sel_b))
        expected.append((rep if rep is not None else r.sel, orig[r.inner_a:r.inner_b]))
    check("transformed rule list == original minus planned edits (order + bytes)",
          after_pairs == expected,
          "orig=%d after=%d expected=%d" % (len(orig_pairs), len(after_pairs), len(expected)))
    if after_pairs != expected:
        for k, (x, y) in enumerate(zip(expected, after_pairs)):
            if x != y:
                print("        first mismatch #%d\n          expected %r\n          got      %r" % (k, x, y))
                break
        die("pair-list mismatch -- nothing written")

    # declaration text of every surviving rule untouched
    check("every surviving declaration block byte-identical",
          [d for _s, d in after_pairs] == [d for _s, d in expected])

    # selector mutation limited to dropping dead members
    ok_sel = True
    why_sel = ""
    for (sa, da), (sb, db) in zip(expected, after_pairs):
        if sa == sb:
            continue
        # only drop_list_member rules may differ; survivors must be preserved in order
        survivors_a = [t.strip() for t in sa.split(",")]
        survivors_b = [t.strip() for t in sb.split(",")]
        if not set(survivors_b) < set(survivors_a):
            ok_sel, why_sel = False, "selector members not a strict subset: %r -> %r" % (sa, sb)
        for d in DEAD:
            if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(d) + r"(?![A-Za-z0-9_-])", sb):
                ok_sel, why_sel = False, "dead class left in mutated selector: %r" % (sb,)
        for m in survivors_b:
            if m not in survivors_a:
                ok_sel, why_sel = False, "member rewritten (not merely dropped): %r" % (m,)
        if len(survivors_b) != len(survivors_a) - 1:
            ok_sel, why_sel = False, "expected exactly one member removed: %r -> %r" % (sa, sb)
    check("selector mutation limited to deleting the dead comma member", ok_sel, why_sel)

    # brace balance / shapes
    check("brace count balanced in transformed",
          after.count("{") == after.count("}"),
          "%d/%d" % (after.count("{"), after.count("}")))
    check("no dangling ',{' in transformed", len(re.findall(r",\s*\{", after)) == 0)
    check("no ',}' in transformed", len(re.findall(r",\s*\}", after)) == 0)
    check("no leading ',' in a selector block",
          len(re.findall(r"[{;]\s*,", after)) == 0)
    check("empty-rule count unchanged",
          len(re.findall(r"\{\s*\}", after)) == len(re.findall(r"\{\s*\}", orig)),
          "%d vs %d" % (len(re.findall(r"\{\s*\}", after)), len(re.findall(r"\{\s*\}", orig))))
    check("no rule with empty selector", all(s.strip() != "" for s, _d in after_pairs))

    # untouched lines byte-identical
    lb = orig.split("\n")
    la = after.split("\n")
    check("line count unchanged", len(lb) == len(la), "%d -> %d" % (len(lb), len(la)))
    changed = [i for i in range(1, min(len(lb), len(la)) + 1)
               if i <= len(lb) and i <= len(la) and lb[i - 1] != la[i - 1]]
    print("        changed lines: %r" % (changed,))
    check("changed lines subset of %r" % (TARGET_LINES,), set(changed) <= set(TARGET_LINES))
    check("changed lines == target lines", changed == TARGET_LINES,
          "targets=%r" % (TARGET_LINES,))

    # pure deletions only on the changed lines (no reflow / reorder / retune)
    pure = True
    for t in changed:
        sm = difflib.SequenceMatcher(None, lb[t - 1], la[t - 1], autojunk=False)
        for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
            if tag == "equal" or tag == "delete":
                continue
            if tag == "replace" and j1 == j2:
                continue
            if tag == "insert" and j2 > j1:
                pure = False
            elif tag != "delete":
                pure = False
    check("changed lines differ from originals by deletions only (no reflow/indent)", pure)

    # dead classes
    pat = {d: re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(d) + r"(?![A-Za-z0-9_-])") for d in DEAD}
    z = {d: len(pat[d].findall(after)) for d in DEAD}
    check("all seven dead classes present in the original (non-vacuous)",
          all(dead_in_orig[d] >= 1 for d in DEAD), str(dead_in_orig))
    check("all seven dead classes appear ZERO times in transformed",
          all(z[d] == 0 for d in DEAD), str(z))
    removed_text = "\n".join(orig[a:b] for a, b, rep, _e in edits)
    acct = {d: len(pat[d].findall(removed_text)) for d in DEAD}
    check("every original occurrence of each dead class is accounted for by an edit",
          all(acct[d] == dead_in_orig[d] for d in DEAD), str(acct))
    # nothing removed that was not dead-anchored: every dropped selector must positively
    # mention a dead class in its leftmost compound
    bad = []
    for a, b, rep, e in edits:
        if rep != "" or e["action"] != "drop_rule":
            continue
        members, _s = split_members(e["selector_before"])
        for ma, mb in members:
            comps = split_compounds(e["selector_before"][ma:mb])
            p0 = set(compound_classes(comps[0])[0]) & set(DEAD) if comps else set()
            if not p0:
                bad.append(e["selector_before"])
    check("every dropped rule is dead-anchored in all of its comma members", not bad, repr(bad[:3]))
    check("dropped/modified lines == summary.changed_lines", removed_lines == TARGET_LINES,
          "%r" % (removed_lines,))

    if FAILS:
        die("self-checks failed: %r -- nothing written" % (FAILS,))

    manifest = entries + [{
        "summary": {
            "rules_dropped": sum(1 for e in entries if e["action"] == "drop_rule"),
            "members_dropped": sum(1 for e in entries if e["action"] == "drop_list_member"),
            "rules_kept_because_ancestor_live":
                sum(1 for e in entries if e["action"] == "kept_because_ancestor_live"),
            "kept_because_not_of_live_ancestor":
                sum(1 for e in entries if e["action"] == "kept_because_not_of_live_ancestor"),
            "chars_removed_total": removed_total,
            "changed_lines": changed,
        }
    }]

    with io.open(DST, "w", encoding="utf-8", newline="") as f:
        f.write(after)
    with io.open(MAN, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2))

    print("")
    print("rules_dropped=%d members_dropped=%d kept_ancestor_live=%d kept_not_of_live_ancestor=%d "
          "chars_removed=%d" % (
              sum(1 for e in entries if e["action"] == "drop_rule"),
              sum(1 for e in entries if e["action"] == "drop_list_member"),
              sum(1 for e in entries if e["action"] == "kept_because_ancestor_live"),
              sum(1 for e in entries if e["action"] == "kept_because_not_of_live_ancestor"),
              removed_total))
    print("wrote %s (%d chars)" % (DST, len(after)))
    print("wrote %s (%d entries)" % (MAN, len(manifest)))
    print("SELF-CHECK RESULT: PASS -- %d checks, 0 failures; changed_lines=%r; "
          "rules_dropped=%d; members_dropped=%d; chars_removed=%d; dead classes in output=0"
          % (CHECKS[0], changed,
             sum(1 for e in entries if e["action"] == "drop_rule"),
             sum(1 for e in entries if e["action"] == "drop_list_member"), removed_total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
