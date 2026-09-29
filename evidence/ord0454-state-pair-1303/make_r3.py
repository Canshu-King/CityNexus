"""Cut `tools/cnx_copy_tiers_r3.py` from the published r2 bytes, adding the ORD-0454 STATE_PAIR face.

The order says to bolt the rule onto an existing ruler rather than start a new one, so nothing here rewrites a
published file: r2's bytes are the base, the new face is appended as its own section, and every splice point is
an asserted-unique anchor -- a drifted r2 fails the cut instead of producing a quietly different tool. r2 itself
is never opened for writing.
"""
import ast
import io
import os

TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
SRC = os.path.join(TOOLS, "cnx_copy_tiers_r2.py")
DST = os.path.join(TOOLS, "cnx_copy_tiers_r3.py")

BLOCK = r'''
# ---- ORD-0454: paired-state face (STATE_PAIR) ---------------------------------------------
# Borrowed shape: F5 and F10 of `D:/moodle/_apk_analysis_pi_travel/MAP/map_findings.md`. The competitor ships
# every selectable thing as a PAIR of names (`map_marker_recommend_poi_selected` beside `..._unselected`;
# 打卡 beside 取消打卡), because a control that can only ever look "on" tells the traveller nothing about what
# pressing it would do. Our tree keeps the same promise with four different spellings, so the twin test accepts
# all four and prints WHICH ONE answered: a rule for the bare base class, a `base:not(.state)` rule, an explicit
# `.unselected` spelling, or a `[data-k="false"]` rule beside `[data-k="true"]`.
# The vocabulary is measured from this tree rather than assumed: `selected / picked / checked / pressed` are
# traveller toggles, while `active` and `current` mark which step or row is the current one -- nobody toggles
# those -- so they are counted out loud into `out_of_scope_states` instead of being silently enforced or
# silently dropped. A class NAME that merely contains a state word (`.v8-selected-stay`,
# `.v8-map-selected-stop`) is not a state modifier; arm K9g is the control that keeps that from rotting into a
# false positive.

TOGGLE_STATES = ("selected", "picked", "checked", "pressed")
NON_TOGGLE_STATES = ("active", "current")
# An attribute is only a traveller toggle when its OWN NAME says so. `aria-disabled="true"` and
# `data-current="true"` are honest shapes whose off state is "no rule at all" -- an enabled button needs no
# styling, and the row that is not current is just a row. Enforcing a false-side rule on those is a ruler
# firing on a shape it was never about, so they are counted into `attributes_out_of_scope` and reported.
TOGGLE_ATTR = re.compile("^(?:data-|aria-)[\\\\w-]*(?:%s)$" % "|".join(TOGGLE_STATES))
_COMBINATOR = re.compile(r"[\s>+~,]+")
_CLASS_TOKEN = re.compile(r"\.(-?[_A-Za-z][\w-]*)")
_ATTR_EQ = re.compile(r"\[\s*([*^$|~]?[\w-]+)\s*=\s*[\"']([^\"']*)[\"']\s*\]")
_NOT_CLASS = re.compile(r":not\(\s*\.([\w-]+)\s*\)")
_BARE_BASE = re.compile(r"^\.(-?[_A-Za-z][\w-]*)$")


def _css_strip_comments(text):
    """Blank comments out but keep every newline, so a reported line number is the real one."""
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)


def _css_rules(text):
    clean = _css_strip_comments(text)
    out = []
    for m in re.finditer(r"([^{}]+)\{", clean):
        sel = m.group(1).strip()
        if sel and not sel.startswith("@"):
            out.append((sel, clean[:m.start()].count("\n") + 1))
    return out


def _css_compounds(selector):
    return [c.strip() for c in _COMBINATOR.split(selector) if c.strip()]


def state_pair_cells(src_dir):
    """Every on-state in the shipped CSS layer plus which twin answers for it.

    A green row names its twin, so the reader can tell "the base class is styled" from "nothing was asked".
    """
    sheets = {}
    for dirpath, _dirs, fnames in os.walk(src_dir):
        for fn in sorted(fnames):
            if fn.endswith(".css"):
                p = os.path.join(dirpath, fn)
                sheets[os.path.relpath(p, src_dir).replace("\\", "/")] = io.open(
                    p, encoding="utf-8", errors="replace").read()
    base_rules, not_twins, named_off = set(), set(), set()
    attr_out_of_scope = set()
    on_cells, attr_cells = [], []
    for f, text in sheets.items():
        for sel, line in _css_rules(text):
            for comp in _css_compounds(sel):
                classes = _CLASS_TOKEN.findall(comp)
                attrs = _ATTR_EQ.findall(comp)
                states = [c for c in classes if c in TOGGLE_STATES]
                others = [c for c in classes if c not in TOGGLE_STATES]
                if states:
                    on_cells.append({"file": f, "line": line, "compound": comp, "selector": sel[:90],
                                     "state": states[0], "base": others[-1] if others else None})
                for n, v in attrs:
                    if v not in ("true", "false"):
                        continue
                    if TOGGLE_ATTR.match(n):
                        attr_cells.append({"file": f, "line": line, "compound": comp, "selector": sel[:90],
                                           "attr": n, "value": v,
                                           "base": others[-1] if others else None})
                    elif n.startswith("data-") or n.startswith("aria-"):
                        attr_out_of_scope.add(n)
                un_named = any(c.startswith("un") and c[2:] in TOGGLE_STATES for c in others)
                if un_named:
                    named_off.update(c[2:] for c in others if c.startswith("un"))
                bare = _BARE_BASE.match(comp)
                if bare:
                    base_rules.add(bare.group(1))
                for n in _NOT_CLASS.findall(comp):
                    if n in TOGGLE_STATES:
                        not_twins.update(others)
    for c in on_cells:
        twins = []
        if c["base"] and c["base"] in base_rules:
            twins.append("base_rule(.%s)" % c["base"])
        if c["base"] and c["base"] in not_twins:
            twins.append("not_pseudo_twin")
        if c["base"] and c["state"] in named_off:
            twins.append("named_unselected_twin")
        if c["base"] and any(a["base"] == c["base"] and a["value"] == "false" for a in attr_cells):
            twins.append("attribute_false_twin")
        c["twins"] = sorted(set(twins))
        c["paired"] = bool(c["twins"])
    seen = {}
    for a in attr_cells:
        seen.setdefault((a["base"], a["attr"]), set()).add(a["value"])
    for a in attr_cells:
        a["paired"] = True if a["value"] == "false" else (
            "false" in seen.get((a["base"], a["attr"]), set()))
        a["twins"] = (["attribute_%s_has_true_and_false" % a["attr"]] if a["paired"] else [])
    out_of_scope = sorted({c for text in sheets.values() for sel, _line in _css_rules(text)
                           for comp in _css_compounds(sel) for c in _CLASS_TOKEN.findall(comp)
                           if c in NON_TOGGLE_STATES})
    return {"cells": on_cells, "attr_cells": attr_cells,
            "population": {"css_files": len(sheets), "on_state_cells": len(on_cells),
                           "paired": sum(1 for c in on_cells if c["paired"]),
                           "unpaired": sum(1 for c in on_cells if not c["paired"]),
                           "attribute_on_cells": sum(1 for a in attr_cells if a["value"] == "true"),
                           "attribute_unpaired": sum(1 for a in attr_cells
                                                     if a["value"] == "true" and not a["paired"]),
                           "base_rules": len(base_rules),
                           "out_of_scope_states": out_of_scope,
                           "out_of_scope_attributes": sorted(attr_out_of_scope)}}


def state_pair_gaps(d):
    p = d["population"]
    rows = ["%s:%s %s (state .%s, no twin of any accepted spelling)"
            % (c["file"], c["line"], c["compound"], c["state"]) for c in d["cells"] if not c["paired"]]
    rows += ['%s:%s %s (%s="true" with no rule for the off state)'
             % (a["file"], a["line"], a["compound"], a["attr"])
             for a in d["attr_cells"] if a["value"] == "true" and not a["paired"]]
    return rows, p["unpaired"] + p["attribute_unpaired"]


def state_pair_findings(src_dir, base_dir=None):
    d = state_pair_cells(src_dir)
    p = d["population"]
    gaps, n_gap = state_pair_gaps(d)
    measure = ("%d stylesheet(s) read, %d on-state cell(s): %d paired, %d unpaired; %d attribute-on cell(s), "
               "%d without an off-side rule; %d bare base rule(s) known; left out of scope on purpose -- "
               "states: %s | attributes: %s"
               % (p["css_files"], p["on_state_cells"], p["paired"], p["unpaired"], p["attribute_on_cells"],
                  p["attribute_unpaired"], p["base_rules"], ", ".join(p["out_of_scope_states"]) or "none",
                  ", ".join(p["out_of_scope_attributes"]) or "none"))
    ok = not n_gap
    if base_dir:
        b = state_pair_cells(base_dir)
        _bg, b_n = state_pair_gaps(b)
        before = {"%s|%s" % (c["compound"], c["state"]) for c in b["cells"] if not c["paired"]}
        before |= {'%s|%s' % (a["compound"], a["attr"]) for a in b["attr_cells"]
                   if a["value"] == "true" and not a["paired"]}
        after = {"%s|%s" % (c["compound"], c["state"]) for c in d["cells"] if not c["paired"]}
        after |= {'%s|%s' % (a["compound"], a["attr"]) for a in d["attr_cells"]
                  if a["value"] == "true" and not a["paired"]}
        new_gaps = sorted(after - before)
        measure += ("; growth mode against %s: that tree already carries %d unpaired cell(s), this one adds "
                    "%d new" % (base_dir, len(before), len(new_gaps)))
        gaps, ok = new_gaps, not new_gaps
    return ("STATE_PAIR", measure, ok,
            " || ".join(gaps[:4]) or ("every on-state has a named twin; which spelling answered is printed "
                                      "per cell by --list-state-pairs"))


def state_pair_mutants():
    """Each arm builds its own stylesheet layer: an injected gap must be caught, and the four legitimate twin
    spellings plus the two decoy shapes (a name containing a state word; a state nobody toggles) stay quiet.
    K9i/K9j settle the growth semantics: a gap that already exists on the base tree is not blamed on the
    candidate, and one the candidate introduces is."""
    import shutil
    import tempfile
    cases = [
        ("K9a_on_state_without_a_twin_is_caught",
         ".v9-new-thing.selected { color: red; }\n", False),
        ("K9b_base_rule_answers",
         ".v9-new-thing { color: blue; }\n.v9-new-thing.selected { color: red; }\n", True),
        ("K9c_not_pseudo_twin_answers",
         ".v9-new-thing:not(.selected) { color: blue; }\n.v9-new-thing.selected { color: red; }\n", True),
        ("K9d_named_unselected_twin_answers",
         ".v9-new-thing.unselected { color: blue; }\n.v9-new-thing.selected { color: red; }\n", True),
        ("K9e_attribute_true_and_false_answer",
         '.v9-card[data-picked="false"] { color: blue; }\n.v9-card[data-picked="true"] { color: red; }\n', True),
        ("K9f_attribute_true_with_no_off_side_is_caught",
         '.v9-card[data-picked="true"] { color: red; }\n', False),
        ("K9g_a_name_holding_the_word_selected_stays_quiet",
         ".v8-selected-stay { color: blue; }\n.v8-map-selected-stop { color: blue; }\n", True),
        ("K9h_current_row_state_is_out_of_scope_not_enforced",
         ".v8-mode-option.active { color: red; }\n", True),
        ("K9i_the_state_alone_without_a_base_is_caught",
         ".selected { color: red; }\n", False),
        # A disabled button and the current row are honest shapes whose off state is "no rule at all"; treating
        # them as unpaired toggles is the false positive that would make this face unusable as a gate.
        ("K9l_disabled_and_current_attributes_stay_quiet",
         '.cn-sim-button[aria-disabled="true"] { opacity: .4; }\nli[data-current="true"] { font-weight: 700; }\n',
         True),
        ("K9m_decision_active_attribute_stays_quiet",
         '.live-shell[data-decision-active="true"] { gap: 2px; }\n', True),
        ("K9n_a_toggle_attribute_named_by_content_is_still_caught",
         '.v9-card[data-selected="true"] { color: red; }\n', False),
        # The first version counted `.family-chip:disabled` as that chip's unselected twin. It is not: a
        # disabled chip is a different question, and a variant class styles one variant, not the untouched
        # default. Only a rule whose compound IS the bare base class answers for the off state.
        ("K9o_a_disabled_or_variant_rule_is_not_an_unselected_twin",
         ".v9-chip:disabled { opacity: .4; }\n.v9-chip.neutral { color: grey; }\n"
         ".v9-chip.selected { color: red; }\n", False),
        ("K9p_bare_base_rule_is_the_twin",
         ".v9-chip { color: black; }\n.v9-chip.selected { color: red; }\n", True),
    ]
    out = []
    for label, css, expect_quiet in cases:
        root = tempfile.mkdtemp(prefix="cnx-statepair-")
        try:
            io.open(os.path.join(root, "sheet.css"), "w", encoding="utf-8", newline="\n").write(css)
            p = state_pair_cells(root)["population"]
            gap = p["unpaired"] + p["attribute_unpaired"]
            verdict_ok = (gap == 0) if expect_quiet else (gap > 0)
            out.append((label, "on=%d paired=%d unpaired=%d attr_unpaired=%d, expected %s"
                        % (p["on_state_cells"], p["paired"], p["unpaired"], p["attribute_unpaired"],
                           "quiet" if expect_quiet else "RED"), verdict_ok))
        finally:
            shutil.rmtree(root, ignore_errors=True)
    base = tempfile.mkdtemp(prefix="cnx-sp-base-")
    cand = tempfile.mkdtemp(prefix="cnx-sp-cand-")
    try:
        io.open(os.path.join(base, "sheet.css"), "w", encoding="utf-8", newline="\n").write(
            ".v9-old.selected { color: red; }\n")
        io.open(os.path.join(cand, "sheet.css"), "w", encoding="utf-8", newline="\n").write(
            ".v9-old.selected { color: red; }\n.v9-new.selected { color: blue; }\n")
        f = state_pair_findings(cand, base)
        out.append(("K9j_growth_mode_blames_only_what_the_candidate_added",
                    "ok=%s measure=%s" % (f[2], f[1][f[1].find("growth mode"):][:110]),
                    f[2] is False and "adds 1 new" in f[1] and "carries 1" in f[1]))
        same = state_pair_findings(cand, cand)
        out.append(("K9k_growth_mode_is_zero_when_nothing_was_added",
                    "ok=%s adds 0 new: %s" % (same[2], "adds 0 new" in same[1]),
                    same[2] is True and "adds 0 new" in same[1]))
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(cand, ignore_errors=True)
    return out

'''


def splice(text):
    def rep(anchor, replacement):
        n = text.count(anchor)
        assert n == 1, "anchor seen %d time(s): %r" % (n, anchor[:70])
        return text.replace(anchor, replacement)

    text = rep("\ndef main():", BLOCK + "\ndef main():")
    text = rep("        findings.append(rendered_finding(after_path, base_path, src_dir))",
               "        findings.append(rendered_finding(after_path, base_path, src_dir))\n"
               "        findings.append(state_pair_findings(src_dir, state_base))")
    text = rep('        findings.append(("RENDERED_NOT_RUN",',
               '        findings.append(("STATE_PAIR_NOT_RUN",\n'
               '                         "no stylesheet layer was read (pass --src frontend/src to enable '
               'this face)",\n'
               '                         True, "NOT_RUN is not a pass: paired states were never measured, '
               'so nothing here proves a toggle answers both ways"))\n'
               '        findings.append(("RENDERED_NOT_RUN",')
    text = rep("def audit(after_path, base_path, e2e_dir, src_dir=None, data_dir=None):",
               "def audit(after_path, base_path, e2e_dir, src_dir=None, data_dir=None, state_base=None):")
    text = rep('    ap.add_argument("--list-fallbacks", action="store_true",',
               '    ap.add_argument("--state-base", help="the tip tree STATE_PAIR compares against; '
               'without it the face is absolute over the scanned tree")\n'
               '    ap.add_argument("--list-state-pairs", action="store_true",\n'
               '                    help="print every on-state cell and the twin that answers for it")\n'
               '    ap.add_argument("--list-fallbacks", action="store_true",')
    text = rep("    for name, measure, ok, detail in audit(a.i18n, a.baseline, a.e2e, a.src, a.data):",
               "    for name, measure, ok, detail in audit(a.i18n, a.baseline, a.e2e, a.src, a.data,\n"
               "                                            a.state_base):")
    text = rep("    if a.ladder:",
               "    if a.src and a.list_state_pairs:\n"
               "        d = state_pair_cells(a.src)\n"
               "        for c in sorted(d[\"cells\"], key=lambda r: (r[\"file\"], r[\"line\"])):\n"
               "            print(\"     [%s] %s:%s %s  state .%s on base .%s  twin: %s\"\n"
               "                  % (\"PAIRED  \" if c[\"paired\"] else \"UNPAIRED\", c[\"file\"], c[\"line\"],\n"
               "                     c[\"compound\"], c[\"state\"], c[\"base\"], \", \".join(c[\"twins\"]) or \"NONE\"))\n"
               "        for x in sorted(d[\"attr_cells\"], key=lambda r: (r[\"file\"], r[\"line\"])):\n"
               "            print(\"     [%s] %s:%s %s  %s=\\\"%s\\\"  twin: %s\"\n"
               "                  % (\"PAIRED  \" if x[\"paired\"] else \"UNPAIRED\", x[\"file\"], x[\"line\"],\n"
               "                     x[\"compound\"], x[\"attr\"], x[\"value\"], \", \".join(x[\"twins\"]) or \"NONE\"))\n"
               "        print(\"     left out of scope on purpose -- states: %s | attributes: %s\"\n"
               "              % (\", \".join(d[\"population\"][\"out_of_scope_states\"]) or \"none\",\n"
               "                 \", \".join(d[\"population\"][\"out_of_scope_attributes\"]) or \"none\"))\n"
               "    if a.ladder:")
    text = rep('        print("  -- render-tier self-test: each tier claim needs its own arm --")',
               '        print("  -- ORD-0454 paired-state self-test: an injected gap must be caught and the '
               'four legitimate twin spellings must stay quiet --")\n'
               "        for label, detail, ok in state_pair_mutants():\n"
               "            print(f\"  [{'MET' if ok else 'VIOLATION'}] {label:48s} {detail}\")\n"
               "            rc |= 0 if ok else 1\n"
               '        print("  -- render-tier self-test: each tier claim needs its own arm --")')
    return text


def main():
    base = io.open(SRC, encoding="utf-8").read()
    assert not os.path.exists(DST), "refusing to overwrite a published tool: " + DST
    out = splice(base)
    ast.parse(out)
    io.open(DST, "w", encoding="utf-8", newline="\n").write(out)
    print("cut %s: %d bytes from %s (%d bytes); r2 left untouched"
          % (DST, len(out.encode("utf-8")), os.path.basename(SRC), len(base.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    main()
