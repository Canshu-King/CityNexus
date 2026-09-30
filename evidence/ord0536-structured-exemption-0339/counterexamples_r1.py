# -*- coding: utf-8 -*-
"""ORD-0536 r1 - the three counterexamples, each really run.

The order's load-bearing sentence is "不接受「人在块里写一句就算豁免」".  A ruler can honour that in two
different ways, and only one of them is worth anything: it can *describe* the boundary in a comment, or it
can die when something crosses it.  This instrument runs the second kind three times, against copies of r8
in this directory, and writes what each run actually returned.

 M1  a table entry that names a file, a line, a cell id, or one whole sink shape
     -> the ruler must REFUSE the run (exit 3), not load a table that can hand-place an exemption.
 M2  a waiver handed in on the command line
     -> the ruler must REFUSE (exit 2) with the waiver named, and a real run's flag set stays accepted.
 M3  an exemption entry widened by one family (`attribute`, which Q71 closed)
     -> the red count must DROP, proving the count is table-controlled, and `--selftest` must then FAIL
        rather than certify the widened bytes.  The published bytes must FAIL to change at all, which is
        what makes M3 a counterexample rather than a knob.

Nothing here touches the authoritative line, a port, or a database.  The mutants are written next to this
file and are not the delivered bytes.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R8 = os.path.join(HERE, "ui_exposure_taint_ast_r8.cjs")
TREE = os.path.join(HERE, "exp_tip_r8", "frontend", "src")
CONTRACT = os.path.join(HERE, "exp_tip_r8", "contracts", "openapi.yaml")
NODE = "node"
ENV = dict(os.environ)
ENV.pop("HTTP_PROXY", None)
ENV.pop("HTTPS_PROXY", None)

CELL_NAMING_ATTEMPTS = [
    # (arm name, the JS object literal handed to the table, what the ruler is expected to answer)
    ("names_a_file",
     "{ id: 'EX-9-MUTANT', rules: ['*'], sink_shape_families: ['text-in'], origin_kinds: ['*'], "
     "evidence: 'attributed_fold', file: 'features/recovery/RecoveryRequiredPanel.tsx' }",
     "UNKNOWN_KEY"),
    ("names_a_line",
     "{ id: 'EX-9-MUTANT', rules: ['*'], sink_shape_families: ['text-in'], origin_kinds: ['*'], "
     "evidence: 'attributed_fold', line: 299 }",
     "UNKNOWN_KEY"),
    ("names_a_cell_id",
     "{ id: 'EX-9-MUTANT', rules: ['*'], sink_shape_families: ['text-in'], origin_kinds: ['*'], "
     "evidence: 'attributed_fold', cell_id: '9f2c1b0a4d5e6f70' }",
     "UNKNOWN_KEY"),
    ("names_one_whole_sink_shape",
     "{ id: 'EX-9-MUTANT', rules: ['*'], "
     "sink_shape_families: ['text-in:details testid=code:plan-ai-reason'], origin_kinds: ['*'], "
     "evidence: 'attributed_fold' }",
     "FAMILY_NAMES_ONE_SINK"),
    ("invents_an_evidence_name",
     "{ id: 'EX-9-MUTANT', rules: ['*'], sink_shape_families: ['text-in'], origin_kinds: ['*'], "
     "evidence: 'commander_said_so' }",
     "EVIDENCE_NOT_IMPLEMENTED"),
    ("names_a_file_through_the_family_axis",
     "{ id: 'EX-9-MUTANT', rules: ['*'], sink_shape_families: ['features/recovery/RecoveryRequiredPanel.tsx'], "
     "origin_kinds: ['*'], evidence: 'attributed_fold' }",
     "AXIS_NAMES_A_CELL"),
]


def read(path):
    return io.open(path, encoding="utf-8").read()


def wr(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return path


def run_ruler(path, extra, out=None):
    cmd = [NODE, path, "--tree", TREE]
    if out:
        cmd += ["--out", out]
    cmd += extra
    p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=1800)
    doc = None
    txt = (p.stdout or b"").decode("utf-8", "replace")
    i = txt.find("{")
    if i >= 0:
        try:
            doc = json.loads(txt[i:])
        except Exception:
            doc = None
    return p.returncode, doc, txt


def counts(doc):
    if not doc:
        return None
    return {"cells_total": doc.get("cells_total"), "red": doc.get("red_after_exemption_count"),
            "exempted": doc.get("exempted_count"), "verdict": doc.get("verdict")}


def insert_entry(text, entry_js):
    """Put an extra entry at the front of EXEMPTION_TABLE, so the mutant really loads a wider table."""
    marker = "const EXEMPTION_TABLE = Object.freeze([\n"
    if marker not in text:
        raise RuntimeError("table marker not found in the ruler bytes")
    return text.replace(marker, marker + "  " + entry_js + ",\n", 1)


def main():
    base = read(R8)
    out = {"ruler_under_test": R8, "tree": TREE, "contract": CONTRACT, "method": "each row is one subprocess of a real ruler, with its own exit code and JSON", "mutants": {}}

    # control: the published bytes
    rc, doc, _ = run_ruler(R8, ["--contract", CONTRACT], os.path.join(HERE, "ce_control_r8.json"))
    out["control"] = {"exit": rc, "counts": counts(doc),
                      "exemption_ids_seen": sorted({e["exemption_id"] for e in (doc or {}).get("exemption_ledger") or []})}
    sys.stderr.write("control exit %s counts %s\n" % (rc, json.dumps(out["control"]["counts"])))

    # M1: a table that could hand-place an exemption
    for name, entry_js, expected_problem in CELL_NAMING_ATTEMPTS:
        mut_path = wr(os.path.join(HERE, "mutant_%s.cjs" % name), insert_entry(base, entry_js))
        rc, doc, txt = run_ruler(mut_path, ["--contract", CONTRACT])
        refused = bool(doc) and doc.get("verdict") == "REFUSED"
        problems = [p.get("problem") for p in ((doc or {}).get("problems") or [])]
        out["mutants"][name] = {"path": mut_path, "entry_tried": entry_js, "exit": rc,
                                "refused": refused, "reason": (doc or {}).get("reason"),
                                "problems": problems, "expected_problem": expected_problem,
                                "expected_problem_reported": expected_problem in problems,
                                "counts_if_it_ran": counts(doc)}
        sys.stderr.write("M1 %-36s exit %s refused %s problems %s\n" % (name, rc, refused, problems))

    # M2: the waiver handed in as an argument
    for flag, expectation in [("--waive-cell", "HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL"),
                              ("--exempt-cells", "HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL"),
                              ("--baseline-cells", "HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL"),
                              ("--authoritative-count", "UNRECOGNISED_FLAG")]:
        # the same --out the control used: if the run is refused, no file may appear
        sink = os.path.join(HERE, "ce_cli_should_not_exist.json")
        if os.path.exists(sink):
            os.remove(sink)
        rc, doc, txt = run_ruler(R8, [flag, "5", "--out", sink])
        reasons = [r.get("reason") for r in ((doc or {}).get("refusals") or [])]
        out["mutants"]["cli_" + flag.replace("--", "")] = {
            "exit": rc, "verdict": (doc or {}).get("verdict"), "refusal_reasons": reasons,
            "expected_reason_present": expectation in reasons,
            "no_output_file_written": not os.path.exists(sink),
        }
        sys.stderr.write("M2 %-24s exit %s reasons %s wrote_output=%s\n" % (
            flag, rc, reasons, os.path.exists(sink)))

    # M3: two mutants that make an exemption say more than the tree does, each checked against --selftest
    #   a) delete the fold entry: the three fold-attributed cells must fall back to red, and the
    #      no-drift arm (which compares against the partition the PUBLISHED ruler documented) must refuse.
    #   b) let the fold predicate answer "yes" with no measurement: that is what "a person wrote a
    #      sentence and the cell is exempt" looks like inside an instrument.  The count has to move, or
    #      the arm means nothing, and the selftest has to fail, or the count is unguarded.
    removed = base.replace("""  Object.freeze({
    id: 'EX-2-ATTRIBUTED-FOLD',""", """  Object.freeze({
    id: 'EX-2-ATTRIBUTED-FOLD-DELETED-IN-MUTANT',
    __deleted: true,
    unused_rules_for_shape_only: [],""", 1)
    if removed == base:
        raise RuntimeError("the fold entry's id line did not match; mutant a was never built")
    # drop the entry out of the array entirely rather than rename it
    start = removed.index("  Object.freeze({\n    id: 'EX-2-ATTRIBUTED-FOLD-DELETED-IN-MUTANT',")
    end = removed.index("]);", start)
    removed = removed[:start] + removed[end:]
    path_a = wr(os.path.join(HERE, "mutant_fold_entry_removed.cjs"), removed)
    rc_a, doc_a, _ = run_ruler(path_a, ["--contract", CONTRACT])
    rc_a_st, st_a, _ = run_ruler(path_a, ["--selftest"])

    unmeasured = base.replace(
        "    if (name === 'attributed_fold') {",
        "    if (name === 'attributed_fold') {\n"
        "      /* MUTANT: the predicate answers ok without reading the tree - a declared sentence in code. */\n"
        "      return { ok: true, basis: 'declared_in_a_sentence', detail: { mutant: true } };", 1)
    if unmeasured == base:
        raise RuntimeError("the fold predicate head did not match; mutant b was never built")
    path_b = wr(os.path.join(HERE, "mutant_fold_exempts_without_measuring.cjs"), unmeasured)
    rc_b, doc_b, _ = run_ruler(path_b, ["--contract", CONTRACT])
    rc_b_st, st_b, _ = run_ruler(path_b, ["--selftest"])

    rc_st_pub, st_pub, _ = run_ruler(R8, ["--selftest"])
    for label, path, rc, doc, rc_st, st in [
        ("fold_entry_removed", path_a, rc_a, doc_a, rc_a_st, st_a),
        ("fold_exempts_without_measuring", path_b, rc_b, doc_b, rc_b_st, st_b)]:
        out["mutants"][label] = {
            "path": path, "run_exit": rc, "counts": counts(doc),
            "counts_delta_vs_control": ({k: (counts(doc)[k] - out["control"]["counts"][k])
                                         for k in ("cells_total", "red", "exempted")}
                                        if counts(doc) and out["control"]["counts"] else None),
            "selftest_exit": rc_st, "selftest_verdict": (st or {}).get("verdict"),
            "failing_arms": sorted([k for k, v in ((st or {}).get("exemption_arms") or {}).items()
                                    if isinstance(v, dict) and v.get("assertion_met") is False]),
            "failing_old_arms": sorted([k for k, v in ((st or {}).get("slot_arms") or {}).items()
                                        if isinstance(v, dict) and v.get("assertion_met") is False]),
        }
        sys.stderr.write("M3 %-32s counts %s selftest %s arms %s\n" % (
            label, json.dumps(counts(doc)), (st or {}).get("verdict"),
            out["mutants"][label]["failing_arms"]))
    out["mutants"]["published_bytes"] = {
        "selftest_exit": rc_st_pub, "selftest_verdict": (st_pub or {}).get("verdict"),
        "counts": counts(run_ruler(R8, ["--contract", CONTRACT],
                                   os.path.join(HERE, "ce_control_r8.json"))[1]),
    }

    # and the published bytes are unchanged by any of this
    out["published_bytes_unchanged"] = read(R8) == base
    out["mutant_files"] = sorted([f for f in os.listdir(HERE) if f.startswith("mutant_")])
    io.open(os.path.join(HERE, "counterexamples_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
