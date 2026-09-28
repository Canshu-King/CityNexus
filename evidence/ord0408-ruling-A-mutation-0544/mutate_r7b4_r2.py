"""反控 for ORD-0408 ruling A, second cut.

The first cut (05:4x) ran and came back with two mutants nobody caught and one that did not parse.
All three were MY harness's fault, not the ruler's, and the reasons are worth keeping in the file:

  * K3 was written against a shape of the missing-enum return that the generated ruler does not have,
    so the mutant was syntactically broken and `node --check` refused it - it never ran;
  * K2 as written (`enum` removed from the schema-key list) is not the defect I described: the parse
    takes the block set's owner from the ancestor stack, so that edit changes nothing. The real
    defect is `addSet(out, key, ...)` instead of `addSet(out, ancestor, ...)`;
  * K4 had no arm that could catch it, because every reading in the set was the shipped panel, whose
    chain carries no literal at all. Membership is only testable against a chain that DOES carry one,
    so the invented-code and unrelated-token fixtures are now part of the reading set.

That last point is the useful one: an arm set that cannot fail is not evidence. Six mutants now, each
with the named arm that must flip.
"""
import io
import json
import os
import subprocess
import sys

ROOT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0408"
JIA = os.path.join(WORK, "jia")
FX = os.path.join(JIA, "fx2")
R7B4 = os.path.join(ROOT, "ui_exposure_taint_ast_r7b4.cjs")
PANEL = os.path.join(JIA, "tip", "frontend", "src", "features", "trash", "JourneyTrashPanel.tsx")
REAL = os.path.join(JIA, "tip", "contracts", "openapi.yaml")
INLINE = os.path.join(JIA, "openapi_inline_enum.yaml")
BLOCK = os.path.join(JIA, "openapi_block_enum.yaml")
OTHER = os.path.join(JIA, "openapi_enum_other_field_only.yaml")

READINGS = [
    ("live_contract_names_no_set", PANEL, REAL),
    ("auto_discovered_from_tree", PANEL, None),
    ("inline_enum_names_the_set", PANEL, INLINE),
    ("block_enum_names_the_set", PANEL, BLOCK),
    ("invented_code_outside_the_set", os.path.join(FX, "invented__JourneyTrashPanel.tsx"), INLINE),
    ("unrelated_token_on_the_chain", os.path.join(FX, "unrelated_token__JourneyTrashPanel.tsx"),
     INLINE),
    ("anchor_field_the_contract_omits", os.path.join(FX, "undeclared_field__JourneyTrashPanel.tsx"),
     INLINE),
    ("set_declared_only_for_another_field", PANEL, OTHER),
    ("no_anchor_at_all", os.path.join(FX, "no_anchor__JourneyTrashPanel.tsx"), INLINE),
]

MUT = [
    ("K1_union_fallback",
     "function contractSetFor(field) {\n  const s = CONTRACT.enums[field];\n"
     "  return (s && s.length) ? s : null;",
     "function contractSetFor(field) {\n  const s = CONTRACT.enums[field];\n"
     "  if (s && s.length) return s;\n  const all = [];\n"
     "  for (const k of Object.keys(CONTRACT.enums)) all.push.apply(all, CONTRACT.enums[k]);\n"
     "  return all.length ? all : null;",
     ["anchor_field_the_contract_omits", "set_declared_only_for_another_field",
      "live_contract_names_no_set", "auto_discovered_from_tree"]),
    ("K2_block_set_owned_by_the_enum_keyword",
     "        addSet(out, ancestor, vals, i + 1, 'enum_key_block');",
     "        addSet(out, key, vals, i + 1, 'enum_key_block');",
     ["block_enum_names_the_set"]),
    ("K3_silence_is_permission",
     "  if (!set) {\n    return { ok: false, why: 'CONTRACT_MISSING_ENUM', field: field,",
     "  if (!set) {\n    return { ok: true, basis: 'silent_contract_passes', tokens: [],"
     " set_size: 0, contract: CONTRACT.path, contract_blob: CONTRACT.blob, contract_line: 0 };\n"
     "  } if (false) {\n    return { ok: false, why: 'CONTRACT_MISSING_ENUM', field: field,",
     ["live_contract_names_no_set", "auto_discovered_from_tree",
      "anchor_field_the_contract_omits", "set_declared_only_for_another_field"]),
    ("K4_membership_never_checked",
     "  const bad = seen.filter(function (v) { return set.indexOf(v) < 0; });",
     "  const bad = [];",
     ["invented_code_outside_the_set", "unrelated_token_on_the_chain"]),
    ("K5_ruling_B_restored",
     "        const ev = enumTokenEvidence(h, codeField);",
     "        const ev = { ok: true, basis: 'field_name_is_permission', tokens: [], set_size: 0,"
     " contract: CONTRACT.path, contract_blob: CONTRACT.blob, contract_line: 0 };",
     ["live_contract_names_no_set", "auto_discovered_from_tree",
      "anchor_field_the_contract_omits", "invented_code_outside_the_set"]),
    ("K6_anchor_test_dropped",
     "      const codeField = cnxFieldNamedOnCell(h._node);",
     "      const codeField = 'reason_code';",
     ["no_anchor_at_all", "live_contract_names_no_set"]),
]


def read(ruler, target, contract, label):
    js = os.path.join(JIA, "m2_%s_%s.json" % (label, os.path.splitext(os.path.basename(ruler))[0]))
    cmd = ["node", ruler, "--file", target, "--out", js]
    if contract:
        cmd += ["--contract", contract]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900)
    d = json.load(io.open(js, encoding="utf-8"))
    return {"exit": p.returncode, "cells": len(d.get("hits", [])),
            "exempted": len(d.get("contract_exempted") or []),
            "blocked": [b.get("why") for b in (d.get("contract_blocked") or [])],
            "folded": len(d.get("attributed_in_fold") or [])}


def state(r):
    """The qualitative verdict an arm asserts: who is exempted and on what named red."""
    return (r["exempted"], tuple(r["blocked"]))


def main():
    base_src = io.open(R7B4, encoding="utf-8", errors="replace").read()
    truth = {}
    for label, target, contract in READINGS:
        truth[label] = read(R7B4, target, contract, "base_" + label)
    rows = []
    for name, old, new, must_flip in MUT:
        n = base_src.count(old)
        if n != 1:
            rows.append({"mutant": name, "ran": False, "caught": None,
                         "why_not": "anchor matched %d times, the mutant was not applied" % n})
            continue
        tmp = os.path.join(JIA, ("r7b4_mut_%s.cjs" % name.lower()).replace("-", "_"))
        io.open(tmp, "w", encoding="utf-8", newline="\n").write(base_src.replace(old, new, 1))
        ck = subprocess.run(["node", "--check", tmp], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=180)
        if ck.returncode:
            rows.append({"mutant": name, "ran": False, "caught": None,
                         "why_not": "the mutant does not parse: " + (ck.stderr or "")[:200]})
            os.remove(tmp)
            continue
        got = {label: read(tmp, target, contract, name + "_" + label)
               for label, target, contract in READINGS}
        flipped = sorted(k for k in got if state(got[k]) != state(truth[k]))
        missing = sorted(set(must_flip) - set(flipped))
        rows.append({"mutant": name, "ran": True, "caught": bool(flipped),
                     "flipped_arms": flipped, "arms_that_should_flip": sorted(must_flip),
                     "did_not_flip_those": missing,
                     "detail": {k: {"base": state(truth[k]), "mutant": state(got[k])}
                                for k in flipped},
                     "cells_after": {k: got[k]["cells"] for k in flipped}})
        os.remove(tmp)
    uncaught = [r["mutant"] for r in rows if r.get("caught") is False]
    could_not_run = [r["mutant"] for r in rows if not r.get("ran")]
    partial = [r["mutant"] for r in rows if r.get("caught") and r.get("did_not_flip_those")]
    out = {"schema": "CNX_S4_ORD0408_MUTATION_R2", "ruler": os.path.basename(R7B4),
           "reading_set": [l for l, _t, _c in READINGS],
           "baseline_readings": truth,
           "baseline_says": {
               "a *_code cell is exempted only when the contract names the set":
                   truth["inline_enum_names_the_set"]["exempted"] == 1
                   and truth["block_enum_names_the_set"]["exempted"] == 1,
               "a live contract with no set is a named red, not a pass":
                   truth["live_contract_names_no_set"]["blocked"] == ["CONTRACT_MISSING_ENUM"]
                   and truth["auto_discovered_from_tree"]["blocked"] == ["CONTRACT_MISSING_ENUM"],
               "a code outside the named set is a named red":
                   truth["invented_code_outside_the_set"]["blocked"]
                   == ["value_not_in_the_contract_set"],
               "an anchor naming an undeclared field is a named red (no union)":
                   truth["anchor_field_the_contract_omits"]["blocked"]
                   == ["CONTRACT_MISSING_ENUM"],
               "no anchor means the contract is never consulted":
                   truth["no_anchor_at_all"]["blocked"] == []
                   and truth["no_anchor_at_all"]["exempted"] == 0},
           "mutants": rows, "uncaught": uncaught, "could_not_run": could_not_run,
           "caught_but_not_by_the_named_arm": partial,
           "verdict": ("MUTATION_ALL_CAUGHT" if not uncaught and not could_not_run and not partial
                       else "MUTATION_TEETH_MISSING")}
    io.open(os.path.join(JIA, "mutation_r7b4.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("baseline_says:", json.dumps(out["baseline_says"], ensure_ascii=False, indent=1))
    for r in rows:
        print("%-40s ran=%s caught=%s flipped=%s missed_named_arms=%s" % (
            r["mutant"], r.get("ran"), r.get("caught"), r.get("flipped_arms"),
            r.get("did_not_flip_those") or r.get("why_not", "")))
    print("verdict", out["verdict"])
    return 0 if out["verdict"] == "MUTATION_ALL_CAUGHT" else 1


if __name__ == "__main__":
    sys.exit(main())
