#!/usr/bin/env python3
"""ORD-0371 r5f counter-control: every rule r5f adds OR keeps must be load-bearing.

Each variant reverts exactly one predicate in the r5f source, runs that mutant's own --selftest, and
records which arms go red.  Three carried-over anchors had to be re-pointed because r5f rewrote the
lines they grabbed (`receipt_near` -> `line_attributed`, the conditional exempt predicate, the conditional
tuple in `scan`); one revert (`line_lock_removed`) initially escaped, which is how I found that naming
the conditional classes had quietly taken over the job the line lock used to do - the arm
`exempt_r5f_line_lock_reaches_a_bare_number_past_the_window` exists because of that miss.
"""
import contextlib
import io
import json
import re
import sys

SRC_PATH = (sys.argv[1] if len(sys.argv) > 1 else
            r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\claim_coordinate_check_r5f.py")

VARIANTS = (
    # ---- r5f's own three rules ----
    ("line_attribution_removed",                       # rule 1 reversed: the line no longer attributes
     '        vouch = DURABLE.search(text[lstart:lend])', "        vouch = None"),
    ("line_attribution_spills_to_the_whole_block",     # rule 1 taken too far: one blob launders all
     '        vouch = DURABLE.search(text[lstart:lend])',
     '        vouch = DURABLE.search(text)'),
    ("conditional_classes_made_unconditional",         # rule 2 taken too far: units hide every number
     '    if cls in ("DIMENSION", "DISCIPLINE_ZERO", "COUNT"):\n        return bool(line_attributed)',
     '    if cls in ("DIMENSION", "DISCIPLINE_ZERO", "COUNT"):\n        return True'),
    ("COUNT_class_reverted_to_no_class",               # rule 2 removed: back to "no class matched"
     '    COUNT_TAIL_RE = re.compile(r"^(?:\\d[\\d_,.]*\\s*)?(%s)" % "|".join(COUNT_TAILS))',
     '    COUNT_TAIL_RE = re.compile(r"(?!x)x")'),
    ("COUNT_adjacency_widened_past_punctuation",       # the regression my first pass shipped
     '    tail = COUNT_TAIL_RE.match(tok) or COUNT_TAIL_RE.match(after.lstrip(" \\t"))',
     '    tail = COUNT_TAIL_RE.match(tok) or COUNT_TAIL_RE.match(after.lstrip(" ，、（(：:="))'),
    ("bare_artifact_path_accepted_as_a_coordinate",    # the widening I am NOT allowed to decide
     "                     + PATH_LINE_ALT,",
     '                     + PATH_LINE_ALT\n                     + r"|[A-Za-z0-9_./\\\\-]*\\.[A-Za-z]'
     r'{1,6}\b",'),
    ("remedy_left_blank",                              # rule 3 removed
     '"remedy": remedy_for(row),', '"remedy": "",'),
    ("remedy_is_one_fixed_string",                     # rule 3 reduced to boilerplate
     'def remedy_for(row):', 'def remedy_for(row):\n    return "attach a coordinate"'),
    # ---- r5e's channels, still load-bearing ----
    ("line_lock_removed_from_the_window_lookup",
     "    m = DURABLE.search(line)", "    m = None"),
    ("window_fallback_removed",                        # r5f keeps this; removing it reddened 15 blocks
     "    m = DURABLE.search(window)", "    m = None"),
    ("uniform_verdicts_removed", "return text, unify_literal_verdicts(rows)", "return text, rows"),
    ("repeat_dedupe_removed", "            if key in seen:", "            if False and key in seen:"),
    ("uniformity_extended_to_conditional_classes",
     '        if row["class"] in UNIFORM_CLASSES and row["token"] not in decided:',
     '        if row["class"] in UNIFORM_CLASSES + CONDITIONAL_CLASSES '
     'and row["token"] not in decided:'),
    # ---- the classifier rules inherited from r5b/r5c/r5d ----
    ("closed_status_set_dropped",
     '    if re.fullmatch(r"\\d{3}", tok) and int(tok) in STATUS_CODES:', "    if False:"),
    ("status_set_widened_to_any_three_digits",
     '    if re.fullmatch(r"\\d{3}", tok) and int(tok) in STATUS_CODES:',
     '    if re.fullmatch(r"\\d{3}", tok):'),
    ("leading_zero_ticket_rule_removed", '    if re.fullmatch(r"0\\d{3}", tok):', "    if False:"),
    ("segment_rule_removed", '    if re.fullmatch(r"\\d[\\d,]{0,15}", tok) and (', "    if False and ("),
    ("segment_rule_drops_the_adjacency",
     '            before.endswith("/") or text[end:end + 1] in ("/", "]")', "            True"),
    ("identifier_boundary_rule_removed",
     '    if re.search(r"[A-Za-z0-9_]$", before[-1:]) and re.match(r"[A-Za-z0-9_]", text[end:end + 1]):',
     "    if False:"),
    ("dimension_unit_rule_removed", "    unit = unit_of(text, start, end)", "    unit = None"),
    ("address_octet_rule_removed",
     '    if re.search(r"\\d{1,3}\\.\\d{1,3}$", before) or re.match(r"^\\.\\d{1,3}", after):',
     "    if False:"),
    ("occurrence_dedupe_removed", "        if start < covered_to:", "        if False and start < covered_to:"),
)

NO_EFFECT_PROVEN_ELSEWHERE = {
    # stated, not excused: this mutant changes which bucket an exempt reading is counted in, not any
    # verdict, because a conditional class is already shape-determined and exemption still comes from the
    # occurrence's own line.  Measured over the whole inbox (23 blocks) - see the delivered proof file.
    "uniformity_extended_to_conditional_classes":
        "measured over the live inbox in mutation_no_effect_proof_r1.json: identical verdict, claim "
        "count, refusal set AND exempt buckets on every block it ran",
}


def run_selftest(src):
    ns = {"__name__": "mutant"}
    exec(compile(src, SRC_PATH, "exec"), ns)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ns["selftest"]()
    return code, json.loads(buf.getvalue())


def main():
    src = open(SRC_PATH, encoding="utf-8").read()
    control_code, control = run_selftest(src)
    rows = [{"variant": "CONTROL (unmutated)", "caught_by": [], "selftest_exit": control_code,
             "arms": len(control["selftest_checks"])}]
    checks = {"control_passes": control_code == 0}
    uncaught = []
    for name, old, new in VARIANTS:
        if src.count(old) != 1:
            rows.append({"variant": name, "error": "ANCHOR_NOT_UNIQUE",
                         "count": src.count(old), "anchor": old[:80]})
            checks["anchor_" + name] = False
            uncaught.append(name + "(anchor)")
            continue
        mutant = src.replace(old, new, 1)
        try:
            compile(mutant, SRC_PATH, "exec")
        except SyntaxError as e:
            rows.append({"variant": name, "error": "MUTANT_DOES_NOT_COMPILE", "detail": str(e)[:90]})
            checks["compiles_" + name] = False
            uncaught.append(name + "(compile)")
            continue
        try:
            code, out = run_selftest(mutant)
        except Exception as e:  # noqa: BLE001
            # A mutant whose self-test cannot even run is a mutant that lost a rule; it is CAUGHT,
            # recorded with the failure, and never reported as "no arm needed".
            rows.append({"variant": name, "caught_by": ["SELFTEST_RAISED"], "selftest_exit": None,
                         "detail": "%s: %s" % (type(e).__name__, str(e)[:120])})
            checks["caught_" + name] = True
            continue
        caught = sorted(k for k, v in out["selftest_checks"].items() if not v)
        ok = code == 6 and bool(caught)
        if not ok and name in NO_EFFECT_PROVEN_ELSEWHERE:
            rows.append({"variant": name, "caught_by": caught, "selftest_exit": code,
                         "no_effect_proven": NO_EFFECT_PROVEN_ELSEWHERE[name]})
            checks["documented_no_effect_" + name] = True
            continue
        rows.append({"variant": name, "caught_by": caught, "selftest_exit": code,
                     "arms_total": len(out["selftest_checks"])})
        checks["caught_" + name] = ok
        if not ok:
            uncaught.append(name)
    out = {"ruler": re.search(r'VERSION = "(.*)"', src).group(1), "control": rows[0],
           "variants": rows[1:], "checks": checks, "uncaught_mutations": uncaught,
           "overall_pass": all(checks.values())}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["overall_pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
