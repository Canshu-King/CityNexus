"""ORD-0408 ruling A, acceptance arms - second pass.

Why a second pass: the first fixtures were hand-written look-alikes and the published ruler reported
NO_EXPOSURE_SHAPE_FOUND on every one of them (0 cells).  A cell that is not live cannot be exempted,
so those arms proved nothing.  These fixtures are the SHIPPED panel with exactly one knob turned, so
r7b1 fires on each of them the same two cells it fires on the original, and the only difference
between an arm and its control is the thing the arm is testing.

Readings are written to jia/arms_r2.json and every number in the ledger block comes back from that
file; nothing here is typed in.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0408"
ROOT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
JIA = os.path.join(WORK, "jia")
TIP = os.path.join(JIA, "tip")
FX = os.path.join(JIA, "fx2")
R7B1 = os.path.join(ROOT, "ui_exposure_taint_ast_r7b1.cjs")
R7B4 = os.path.join(ROOT, "ui_exposure_taint_ast_r7b4.cjs")
REAL = os.path.join(TIP, "contracts", "openapi.yaml")
PANEL = os.path.join(TIP, "frontend", "src", "features", "trash", "JourneyTrashPanel.tsx")

SET = ["JOURNEY_NOT_FOUND", "JOURNEY_ALREADY_DELETED", "JOURNEY_NOT_DELETED", "PROVIDER_REFUSED"]

KNOBS = {
    "control": [],
    # the client supplies a fallback that the contract DOES name
    "in_set": [("const code = refusalReasonCode(cause);",
                'const code = refusalReasonCode(cause) || "JOURNEY_NOT_DELETED";')],
    # the client supplies a fallback the contract does NOT name - the invented-code shape
    "invented": [("const code = refusalReasonCode(cause);",
                  'const code = refusalReasonCode(cause) || "NOT_A_REAL_CODE";')],
    # an unrelated uppercase token on the same chain: the ruling errs RED and names it
    "unrelated_token": [("const code = refusalReasonCode(cause);",
                         'const code = refusalReasonCode(cause) || "INTERNAL_ERROR";')],
    # the anchor is gone: nothing about the shape or the className may name a field
    "no_anchor": [(' data-cnx-field="reason_code"', "")],
    # the anchor names a field the contract says nothing about
    "undeclared_field": [('data-cnx-field="reason_code"', 'data-cnx-field="error_code"')],
}


def wr(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return path


def fixtures():
    if not os.path.isdir(FX):
        os.makedirs(FX)
    base_text = io.open(PANEL, encoding="utf-8").read()
    out = {}
    for name, subs in KNOBS.items():
        t = base_text
        for old, new in subs:
            assert t.count(old) == 1, (name, old, t.count(old))
            t = t.replace(old, new, 1)
        f = wr(os.path.join(FX, "%s__JourneyTrashPanel.tsx" % name), t)
        assert (os.path.getsize(f) != os.path.getsize(PANEL)) or not subs, name
        out[name] = f
    out["verbatim_copy"] = wr(os.path.join(FX, "verbatim__JourneyTrashPanel.tsx"), base_text)
    assert os.path.getsize(out["verbatim_copy"]) == os.path.getsize(PANEL)
    return out


def contracts():
    s = io.open(REAL, encoding="utf-8").read()
    assert s.count("reason_code: {type: string}") == 1
    inline = wr(os.path.join(JIA, "openapi_inline_enum.yaml"), s.replace(
        "reason_code: {type: string}",
        "reason_code: {type: string, enum: [%s]}" % ", ".join(SET), 1))
    # The block form has to sit DEEPER than the field name it belongs to.  Written flat, the `enum:`
    # is a sibling of `reason_code` and the arm tests a contract that does not declare the set at
    # all - which is what the first B5 run did, and the parse was right to call it missing.
    block = wr(os.path.join(JIA, "openapi_block_enum.yaml"), s.replace(
        "reason_code: {type: string}",
        "reason_code:\n              type: string\n              enum:\n"
        + "".join("                - %s\n" % v for v in SET), 1))
    other = wr(os.path.join(JIA, "openapi_enum_other_field_only.yaml"), s.replace(
        "reason_code: {type: string}",
        "reason_code: {type: string}\n            error_class: {type: string, enum: [%s]}"
        % ", ".join(SET), 1))
    return {"real": REAL, "inline": inline, "block": block, "other_field": other}


def run(ruler, target, contract, out_name):
    js = os.path.join(JIA, "out_%s.json" % out_name)
    cmd = ["node", ruler, "--file", target, "--out", js]
    if contract:
        cmd += ["--contract", contract]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    d = json.load(io.open(js, encoding="utf-8"))
    cells = [{"id": h.get("cell_id"), "rule": h["rule"], "line": h["line"]} for h in d.get("hits", [])]
    ex = d.get("contract_exempted", [])
    bl = d.get("contract_blocked", [])
    return {"exit": r.returncode, "cells": sorted(c["rule"] + "@" + str(c["line"]) for c in cells),
            "cell_ids": sorted(c["id"] for c in cells),
            "folded": sorted(e.get("file_line") for e in d.get("attributed_in_fold", [])),
            "exempted": [{"line": e["file_line"], "rule": e["rule"], "field": e.get("field"),
                          "basis": e.get("basis"), "tokens": e.get("tokens_seen"),
                          "enum_size": e.get("enum_size"),
                          "contract": os.path.basename(e.get("contract") or ""),
                          "contract_line": e.get("contract_enum_line"),
                          "contract_blob": e.get("contract_blob")} for e in ex],
            "blocked": [{"line": b["file_line"], "rule": b["rule"], "field": b.get("field"),
                         "why": b.get("why"), "examples": b.get("examples"),
                         "contract": os.path.basename(b.get("contract") or ""),
                         "fields_with_enum": b.get("fields_with_enum"),
                         "enum_size": b.get("enum_size")} for b in bl],
            "contract": (d.get("contract") and {
                "path": d["contract"]["path"], "readable": d["contract"]["readable"],
                "bytes": d["contract"]["bytes"], "blob": d["contract"]["blob"],
                "fields_with_enum": d["contract"]["fields_with_enum"],
                "reason_code_members": (d["contract"].get("enums") or {}).get("reason_code"),
                "reason_code_form": (d["contract"].get("enum_forms") or {}).get("reason_code"),
                "forms_counted": d["contract"].get("forms"),
                "reason_code_line": (d["contract"]["enum_lines"] or {}).get("reason_code"),
                "auto": d["contract"].get("auto_discovered"), "note": d["contract"]["note"]}) or None,
            "stderr_head": (r.stderr or "")[:160]}


def main():
    F = fixtures()
    C = contracts()
    res = {"fixtures": {k: {"path": v, "bytes": os.path.getsize(v)} for k, v in F.items()},
           "contracts": {k: {"path": v, "bytes": os.path.getsize(v),
                             "local_sha1_over_bytes":
                                 hashlib.sha1(open(v, "rb").read()).hexdigest()}
                         for k, v in C.items()}}

    # STEP 0 - is each fixture a LIVE cell under the published ruler?  Without this the rest is noise.
    live = {}
    for k in sorted(F):
        live[k] = run(R7B1, F[k], None, "live_r7b1_%s" % k)
    res["step0_live_under_r7b1"] = {k: v["cells"] for k, v in live.items()}
    res["step0_all_live"] = bool(live["control"]["cells"]) and all(
        v["cells"] == live["control"]["cells"] for k, v in live.items()
        if k in ("in_set", "invented", "unrelated_token", "undeclared_field"))

    arms = {}
    arms["B1_in_set_code_contract_names_it"] = run(R7B4, F["in_set"], C["inline"], "B1")
    arms["B2_invented_code_outside_the_set"] = run(R7B4, F["invented"], C["inline"], "B2")
    arms["B3_real_contract_declares_nothing"] = run(R7B4, F["control"], C["real"], "B3")
    arms["B4_inline_enum_form"] = run(R7B4, F["control"], C["inline"], "B4")
    arms["B5_block_enum_form"] = run(R7B4, F["control"], C["block"], "B5")
    arms["B6_no_anchor_at_all"] = run(R7B4, F["no_anchor"], C["inline"], "B6")
    arms["B7_anchor_names_a_field_the_contract_omits"] = run(R7B4, F["undeclared_field"],
                                                            C["inline"], "B7")
    arms["B8_unrelated_uppercase_token"] = run(R7B4, F["unrelated_token"], C["inline"], "B8")
    arms["B9_set_declared_only_for_another_field"] = run(R7B4, F["control"], C["other_field"], "B9")
    res["arms"] = arms
    res["step0_detail"] = live

    # B10 - tree mode without --contract: the contract must come from the scanned tree
    js = os.path.join(JIA, "out_B10_tree.json")
    r = subprocess.run(["node", R7B4, "--tree", os.path.join(TIP, "frontend", "src"), "--out", js],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=1800, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    d = json.load(io.open(js, encoding="utf-8"))
    res["B10_tree_contract_travels_with_the_tree"] = {
        "exit": r.returncode, "hits_total": d.get("cells_total"),
        "contract": d.get("contract"),
        "contract_exempted": d.get("contract_exempted"),
        "contract_blocked": d.get("contract_blocked"),
        "attributed_in_fold_count": d.get("attributed_in_fold_count")}

    # B11 - before / after over the same batch: the published ruler vs r7b4, tree mode, no contract
    # flag on either side, so the difference is the code and nothing else.
    before = os.path.join(JIA, "out_B11_before.json")
    after = os.path.join(JIA, "out_B11_after.json")
    for ruler, o in ((R7B1, before), (R7B4, after)):
        subprocess.run(["node", ruler, "--tree", os.path.join(TIP, "frontend", "src"), "--out", o],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=1800, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    b = json.load(io.open(before, encoding="utf-8"))
    a = json.load(io.open(after, encoding="utf-8"))
    ids_b = sorted(h.get("cell_id") for h in b.get("hits", []))
    ids_a = sorted(h.get("cell_id") for h in a.get("hits", []))
    res["B11_before_after_tree"] = {
        "r7b1_cells": len(ids_b), "r7b4_cells_no_contract": len(ids_a),
        "only_before": sorted(set(ids_b) - set(ids_a)), "only_after": sorted(set(ids_a) - set(ids_b)),
        "r7b1_folded": b.get("attributed_in_fold_count"), "r7b4_folded": a.get("attributed_in_fold_count"),
        "r7b4_contract_blocked": len(a.get("contract_blocked") or []),
        "r7b4_contract": a.get("contract"),
        "r7b1_per_rule": b.get("per_rule"), "r7b4_per_rule": a.get("per_rule")}

    # B12 - selftest: the published arm set must still pass, unchanged, on r7b4
    st = {}
    for tag, ruler in (("r7b1", R7B1), ("r7b4", R7B4)):
        o = os.path.join(JIA, "out_selftest_%s.json" % tag)
        p = subprocess.run(["node", ruler, "--selftest", "--out", o], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=1800, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        dd = json.load(io.open(o, encoding="utf-8"))
        st[tag] = {"exit": p.returncode, "verdict": dd.get("verdict"),
                   "passed": dd.get("passed"), "total": dd.get("total"),
                   "expectations_moved": [m.get("fixture") for m in (dd.get("expectations_moved") or [])],
                   "keys": sorted(k for k in dd if k not in ("fixtures", "arms"))}
    res["B12_selftest"] = st

    # THE HARNESS DECIDES, NOT THE READER: every arm carries the verdict the ruling requires, and a
    # drift exits non-zero.  Writing the numbers down without a predicate is how a regression passes.
    EXPECT = {
        "B1_in_set_code_contract_names_it": {"cells": 1, "exempt": 1, "blocked": 0,
                                            "basis": "literal_on_the_chain_checked_against_the_named_set"},
        "B2_invented_code_outside_the_set": {"cells": 2, "exempt": 0, "blocked": 1,
                                            "why": "value_not_in_the_contract_set"},
        "B3_real_contract_declares_nothing": {"cells": 2, "exempt": 0, "blocked": 1,
                                             "why": "CONTRACT_MISSING_ENUM"},
        "B4_inline_enum_form": {"cells": 1, "exempt": 1, "blocked": 0,
                               "form": "inline_on_field_line"},
        "B5_block_enum_form": {"cells": 1, "exempt": 1, "blocked": 0, "form": "enum_key_block"},
        "B6_no_anchor_at_all": {"cells": 2, "exempt": 0, "blocked": 0},
        "B7_anchor_names_a_field_the_contract_omits": {"cells": 2, "exempt": 0, "blocked": 1,
                                                      "why": "CONTRACT_MISSING_ENUM"},
        "B8_unrelated_uppercase_token": {"cells": 2, "exempt": 0, "blocked": 1,
                                         "why": "value_not_in_the_contract_set"},
        "B9_set_declared_only_for_another_field": {"cells": 2, "exempt": 0, "blocked": 1,
                                                  "why": "CONTRACT_MISSING_ENUM"},
    }
    checks = []
    for name, want in sorted(EXPECT.items()):
        got = arms[name]
        ok = (len(got["cells"]) == want["cells"] and len(got["exempted"]) == want["exempt"]
              and len(got["blocked"]) == want["blocked"])
        detail = {"arm": name, "want": want,
                  "now": {"cells": got["cells"], "exempt": got["exempted"], "blocked": got["blocked"]}}
        if ok and want.get("why"):
            ok = bool(got["blocked"]) and got["blocked"][0]["why"] == want["why"]
        if ok and want.get("basis"):
            ok = bool(got["exempted"]) and got["exempted"][0]["basis"] == want["basis"]
        if ok and want.get("form"):
            ok = bool(got["exempted"]) and got["exempted"][0].get("contract_line")
            ok = ok and (got["contract"] or {}).get("reason_code_form") == want["form"]
        detail["pass"] = bool(ok)
        checks.append(detail)

    t10 = res["B10_tree_contract_travels_with_the_tree"]
    checks.append({"arm": "B10_tree_contract_from_the_same_tree", "pass": bool(
        t10["contract"] and t10["contract"]["readable"] and t10["contract"]["auto_discovered"]
        and t10["contract"]["path"].replace("\\", "/").endswith("jia/tip/contracts/openapi.yaml")),
        "now": t10["contract"]})
    b11 = res["B11_before_after_tree"]
    checks.append({"arm": "B11_no_cell_lost_or_gained_between_rulers", "pass": bool(
        b11["r7b1_cells"] == b11["r7b4_cells_no_contract"] and not b11["only_before"]
        and not b11["only_after"] and b11["r7b1_folded"] == b11["r7b4_folded"]), "now": b11})
    checks.append({"arm": "B12_selftest_still_green_and_moves_nothing_new", "pass": bool(
        st["r7b4"]["verdict"] == "SELFTEST_PASS" and st["r7b4"]["exit"] == 0
        and st["r7b4"]["expectations_moved"] == st["r7b1"]["expectations_moved"]),
        "now": {"r7b1": st["r7b1"]["expectations_moved"], "r7b4": st["r7b4"]["expectations_moved"],
                "r7b4_verdict": st["r7b4"]["verdict"]}})
    res["checks"] = checks
    res["all_checks_pass"] = all(c["pass"] for c in checks)
    wr(os.path.join(JIA, "arms_r2.json"), json.dumps(res, ensure_ascii=False, indent=1))
    print("CHECKS: " + " / ".join("%s=%s" % (c["arm"].split("_")[0], "PASS" if c["pass"] else "FAIL")
                                  for c in checks))
    print("all_checks_pass:", res["all_checks_pass"])
    for c in checks:
        if not c["pass"]:
            print("FAILED", c["arm"], json.dumps(c, ensure_ascii=False)[:700])
    if not res["all_checks_pass"]:
        return 1
    wr(os.path.join(JIA, "arms_r2.json"), json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in ("step0_live_under_r7b1", "step0_all_live")},
                     ensure_ascii=False, indent=1))
    for k, v in arms.items():
        print("== %-46s cells %d exempt %d blocked %d" % (k, len(v["cells"]), len(v["exempted"]),
                                                          len(v["blocked"])))
        if v["exempted"]:
            print("   ", json.dumps(v["exempted"], ensure_ascii=False)[:400])
        if v["blocked"]:
            print("   ", json.dumps(v["blocked"], ensure_ascii=False)[:400])
    print("B10", json.dumps(res["B10_tree_contract_travels_with_the_tree"]["contract"],
                            ensure_ascii=False)[:400])
    print("B11", json.dumps({k: v for k, v in res["B11_before_after_tree"].items()
                             if k != "r7b4_contract"}, ensure_ascii=False)[:600])
    print("B12", json.dumps(res["B12_selftest"], ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
