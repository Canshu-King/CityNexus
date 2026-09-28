"""Second stage of the ORD-0424 cut: let tier C reach the claim, the report and the CLI.

Pipeline, so the generation is reproducible from the published bytes:
    cnx_copy_tiers_r1.py (tip, blob 8f1b40022fcba770ac6ec6ce501aab2ecb93882b)
      -> bolt_shapes_r2.py   adds the three shapes and their per-shape exclusion rules
      -> this script         folds tier C into HARDCODED_FALLBACK's gated claim, into RENDER_TIERS,
                             into --list-fallbacks, and adds --data for the seed directory

Every replacement asserts it matched exactly once: a silent no-op here would publish a tool whose
report still ignores the tier it just started computing, which is the kind of green that means nothing.
"""
import ast
import io
import os

TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
TARGET = os.path.join(TOOLS, "cnx_copy_tiers_r2.py")

OLD_CLAIM = '''def component_fallback(src_dir):
    """The gated claim plus its denominator, both computed from the tree."""
    from collections import Counter
    hits, pairs, files = scan_tree(src_dir)
    tier_a = [h for h in hits if h[0] == "A"]
    tier_b = [h for h in hits if h[0] == "B"]
    skipped = [h for h in hits if h[0].endswith("-skipped")]
    bad = tier_a + tier_b'''

NEW_CLAIM = '''def component_fallback(src_dir, data_dir=None):
    """The gated claim plus its denominator, both computed from the tree.

    Tier C is ORD-0424's addition: a hardcoded English string sitting in element text, in a ternary
    branch, or in a `useState` default. It is a hit and it gates, because a Chinese screen is handed
    English either way; the letter only keeps it separate so the published `??` reading stays
    comparable line for line.
    """
    from collections import Counter
    hits, pairs, files = scan_tree(src_dir, data_dir)
    tier_a = [h for h in hits if h[0] == "A"]
    tier_b = [h for h in hits if h[0] == "B"]
    tier_c = [h for h in hits if h[0] == "C"]
    c_skipped = [h for h in hits if h[0] == "C-skipped"]
    skipped = [h for h in hits if h[0].endswith("-skipped")]
    bad = tier_a + tier_b + tier_c'''

OLD_MEASURE = '''    measure = ("%d files scanned: tier A (language branch in the slot) %d, tier B (bare literal) %d, "
               "excluded as machine tokens %d; inline bilingual pairs anywhere = %d "
               "(denominator only -- most are legitimate inline pairs, NOT a defect count)"
               % (files, len(tier_a), len(tier_b), len(skipped), pairs))'''

NEW_MEASURE = '''    c_by_shape = Counter(h[4].split(":")[0] for h in tier_c)
    measure = ("%d files scanned: tier A (language branch in the slot) %d, tier B (bare literal) %d, "
               "excluded as machine tokens %d; inline bilingual pairs anywhere = %d "
               "(denominator only -- most are legitimate inline pairs, NOT a defect count); "
               "ORD-0424 tier C (a shape the ?? anchor cannot see) %d [%s], "
               "excluded by a named shape rule %d"
               % (files, len(tier_a), len(tier_b), len(skipped), pairs, len(tier_c),
                  ", ".join("%s=%d" % (k, v) for k, v in sorted(c_by_shape.items())),
                  len(c_skipped)))'''

OLD_RT = '''def render_tiers_finding(src_dir):'''
NEW_RT = '''def render_tiers_finding(src_dir, data_dir=None):'''

OLD_RT_BODY = '''    hits, _pairs, files = scan_tree(src_dir)
    live = [h for h in hits if h[0] in ("A", "B")]'''
NEW_RT_BODY = '''    hits, _pairs, files = scan_tree(src_dir, data_dir)
    live = [h for h in hits if h[0] in ("A", "B", "C")]'''

OLD_CALLS = '''        findings.append(component_fallback(src_dir))
        findings.append(render_tiers_finding(src_dir))'''
NEW_CALLS = '''        findings.append(component_fallback(src_dir, data_dir or default_data_dir(src_dir)))
        findings.append(render_tiers_finding(src_dir, data_dir or default_data_dir(src_dir)))'''

OLD_LIST = '''        hits, _pairs, _files = scan_tree(a.src)'''
NEW_LIST = '''        hits, _pairs, _files = scan_tree(a.src, a.data or default_data_dir(a.src))'''

# audit() has no argument namespace of its own: data_dir arrives as a parameter, defaulted, so the
# published call shape still works
OLD_AUDIT = 'def audit(after_path, base_path, e2e_dir, src_dir=None):'
NEW_AUDIT = 'def audit(after_path, base_path, e2e_dir, src_dir=None, data_dir=None):'
OLD_AUDIT_CALL = 'audit(a.i18n, a.baseline, a.e2e, a.src)'
NEW_AUDIT_CALL = 'audit(a.i18n, a.baseline, a.e2e, a.src, a.data)'

# the shapes module reads a seed directory, so the two modules it uses must be imported; the
# published tool reached for neither
OLD_IMPORTS = '''import argparse
import re
import sys
import tempfile
from pathlib import Path'''
NEW_IMPORTS = '''import argparse
import io
import os
import re
import sys
import tempfile
from pathlib import Path'''

OLD_ARG = '''    ap.add_argument("--list-fallbacks", action="store_true",'''
NEW_ARG = '''    ap.add_argument("--data", help="seed directory (default: <root>/data/mock of the scanned "
                                   "tree); the names it holds are excluded by rule, printed with "
                                   "the file and offset they matched in")
''' + OLD_ARG

HELPER = '''def default_data_dir(src_dir):
    """The scanned tree's own seed directory, if it is there: <root>/data/mock.

    Walks up from `--src` (frontend/src) so a lane export and a worktree each find the data of the
    generation they are scanning, rather than a copy from a different checkout.
    """
    here = os.path.abspath(src_dir)
    for _i in range(6):
        cand = os.path.join(here, "data", "mock")
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return None


'''

PAIRS = [(OLD_IMPORTS, NEW_IMPORTS), (OLD_AUDIT, NEW_AUDIT), (OLD_AUDIT_CALL, NEW_AUDIT_CALL), (OLD_CLAIM, NEW_CLAIM), (OLD_MEASURE, NEW_MEASURE), (OLD_RT, NEW_RT),
         (OLD_RT_BODY, NEW_RT_BODY), (OLD_CALLS, NEW_CALLS), (OLD_LIST, NEW_LIST),
         (OLD_ARG, NEW_ARG)]


def main():
    s = io.open(TARGET, encoding="utf-8").read()
    for old, new in PAIRS:
        n = s.count(old)
        assert n == 1, "expected 1 match, got %d for %r" % (n, old[:60])
        s = s.replace(old, new, 1)
    assert s.count("def audit(") == 1
    s = s.replace("def audit(", HELPER + "def audit(", 1)
    io.open(TARGET, "w", encoding="utf-8", newline="\n").write(s)
    ast.parse(s)
    print("report wired into", os.path.basename(TARGET), len(s.encode("utf-8")), "B  ast.parse ok")


if __name__ == "__main__":
    main()
