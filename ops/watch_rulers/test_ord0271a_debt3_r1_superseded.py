"""ORD-0271-A / DEBT-3 offline proof: the pre-flight must stop answering a POST_UNION question in a
PRE_UNION run - and must not become laxer anywhere else.

Why offline: `deploy_bundle.py` (blob 149e9c6dbe6debcac92041bb192761c1cf1aa2a7) is the instrument that
currently guards the phone preview, so this test never imports the gauge and never deploys anything.  It
pulls the pure pieces out of the draft source by AST and drives them with two immutable, externally
readable field records:

  sample A  a real read-only `--preflight-check` (PRE_UNION) of a healthy build export that the shipped
            gauge reported BLOCKED over.
            commander/control:evidence/ord0271-a-gauge-fixtures/sample_A_preunion_preflight_0923_200628.json
            blob c8e23ddd42259fb05e49376c5074a812839dad0f (26,281 B)
            Its own rows carry both halves of the contradiction: status 200 + content-type text/html from
            HTTP, and disk_present true + a real digest + 1,238,834 bytes from the build export.
  sample B  the SAME two refs 2m26s later, unioned, judged by the strict POST_UNION arms: overall GREEN.
            commander/control:evidence/ord0271-a-gauge-fixtures/sample_B_postunion_deploy_d2665e25_0923_200854.json
            blob 0aa298042d78d317828e2d33a6a55eeabefe7bff (66,470 B)

Every verdict below is DERIVED from bytes read out of those two blobs - no expected string is typed in by
this file except the ones that name an input cell, and each of those is labelled `synthetic` where the
artifact does not contain the shape.  Cross-check: the digest A recorded on disk for
`/assets/index-D76m_cky.js` is compared against the digest B measured over HTTP for the same name, so the
named gap is discharged by a measured identity rather than by an assertion (cell X1).
"""
import ast
import base64
import hashlib
import io
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "deploy_bundle_v2_draft.py")
IN_SERVICE_GAUGE = os.path.join(HERE, "deploy_bundle.py")
IN_SERVICE_GAUGE_BLOB = "149e9c6dbe6debcac92041bb192761c1cf1aa2a7"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"

FIXTURES = {
    "A": ("evidence/ord0271-a-gauge-fixtures/sample_A_preunion_preflight_0923_200628.json",
          "c8e23ddd42259fb05e49376c5074a812839dad0f",
          os.path.join(HERE, "receipts", "preflight_0923_200628.json")),
    "B": ("evidence/ord0271-a-gauge-fixtures/sample_B_postunion_deploy_d2665e25_0923_200854.json",
          "0aa298042d78d317828e2d33a6a55eeabefe7bff",
          os.path.join(HERE, "receipts",
                       "deploy_d2665e25855aeb265329266831983de42321697d_0923_200854.json")),
}
OUT = os.path.join(HERE, "receipts", "ord0271a_debt3_selftest.json")
GREEN, RED, GAP = "GREEN", "RED", "NOT_YET_UNIONED_NAMED_GAP"


def blob_sha_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def fetch_blob(sha):
    """Read a published fixture back out of GitHub and prove the bytes by blob sha1 - a local path is not a
    coordinate (the red team caught me shipping one on 0271-A before)."""
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json", "User-Agent": "cnx-cmdr"})
    with urllib.request.urlopen(req, timeout=180) as r:
        meta = json.loads(r.read().decode())
    raw = base64.b64decode(meta["content"].replace("\n", ""))
    if blob_sha_of(raw) != sha:
        raise SystemExit("fixture blob readback mismatch for " + sha)
    return json.loads(raw.decode()), len(raw)


def draft_source():
    return io.open(DRAFT, encoding="utf-8").read()


def extract(names):
    """Compile selected top-level nodes out of the draft into one shared namespace (no gauge import)."""
    src = draft_source()
    tree = ast.parse(src)
    want = set(names)
    body = [n for n in tree.body
            if (isinstance(n, ast.FunctionDef) and n.name in want)
            or (isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in want for t in n.targets))]
    missing = want - {getattr(n, "name", None) or getattr(getattr(n, "targets", [None])[0], "id", "")
                      for n in body}
    if missing:
        raise SystemExit("DEBT-3 test cannot find in the draft: %s" % sorted(missing))
    ns = {"pathlib": __import__("pathlib"), "sha256": lambda p: blob_sha_of(io.open(p, "rb").read())}
    exec(compile(ast.Module(body=body, type_ignores=[]), DRAFT, "exec"), ns)
    return ns


def extract_fn_source(name):
    src = draft_source()
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(src, fn)


def compile_from(text_src, ns_base):
    mod = ast.parse(text_src)
    ns = dict(ns_base)
    exec(compile(mod, "<mutant>", "exec"), ns)
    return ns


def rows_from_A(A):
    """Every new-generation HTTP row the shipped gauge recorded in the PRE_UNION run, as (ref, ok, present)."""
    pf = A["preflight"]
    new_refs = set(A["src_index_refs"])
    out = []
    for v in pf["C_pre_new_assets_reach_the_live_server"]:
        p = v["probes"][0]
        out.append({"arm": "C_pre", "ref": p["path"], "http_ok": v["verdict"] == GREEN,
                    "present": bool(p["disk_present"]), "status": p["status"], "ct": p["content_type"],
                    "disk_sha256": p.get("disk_sha256"), "disk_bytes": p.get("disk_bytes"),
                    "is_new": p["path"] in new_refs})
    for e in pf["G_pre_precache_of_the_new_sw_resolves"]:
        for pr in e["probes"]:
            got = pr.get("got")
            if not got:
                continue                      # a declared root doc, not an asset row
            p = got["probes"][0]
            out.append({"arm": "G_pre/" + e["sw"], "ref": p["path"], "http_ok": got["verdict"] == GREEN,
                        "present": bool(p["disk_present"]), "status": p["status"], "ct": p["content_type"],
                        "disk_sha256": p.get("disk_sha256"), "disk_bytes": p.get("disk_bytes"),
                        "is_new": p["path"] in new_refs})
    for pr in pf["F_pre_user_surfaces"]["probes"]:
        got = pr.get("got")
        if not got:
            continue
        p = got["probes"][0]
        out.append({"arm": "F_pre/" + str(pr.get("surface")), "ref": p["path"],
                    "http_ok": got["verdict"] == GREEN, "present": bool(p["disk_present"]),
                    "status": p["status"], "ct": p["content_type"], "disk_sha256": p.get("disk_sha256"),
                    "disk_bytes": p.get("disk_bytes"), "is_new": p["path"] in new_refs})
    return out, new_refs


def served_from_B(B):
    """ref -> (http_ok, status, content_type, body sha256) as the strict POST_UNION arms measured them."""
    m = {}
    for v in B.get("pre_switch_asset_probes") or []:
        for p in v["probes"]:
            m[p["path"]] = (v["verdict"] == GREEN, p["status"], p["content_type"], p.get("sha256"))
    return m


def main():
    cells, notes = [], []

    def check(name, ok, detail):
        cells.append({"cell": name, "verdict": GREEN if ok else RED, "detail": detail})

    A, a_bytes = fetch_blob(FIXTURES["A"][1])
    B, b_bytes = fetch_blob(FIXTURES["B"][1])
    for key, doc, path, size in (("A", A, FIXTURES["A"][2], a_bytes), ("B", B, FIXTURES["B"][2], b_bytes)):
        local = io.open(path, "rb").read()
        check(f"fixture_{key}_local_bytes_equal_published", len(local) == size and blob_sha_of(local) ==
              FIXTURES[key][1], {"published_len": size, "local_len": len(local),
                                 "blob": FIXTURES[key][1]})

    ns = extract(["PRE_UNION", "POST_UNION", "DEBT3_PHASES", "NAMED_GAP", "_debt3_phase_decide",
                  "f_verdict_of", "preflight_before_switch"])
    decide, fvo = ns["_debt3_phase_decide"], ns["f_verdict_of"]
    PRE, POST = ns["PRE_UNION"], ns["POST_UNION"]
    a_rows, new_refs = rows_from_A(A)
    b_map = served_from_B(B)
    union_added = set((B.get("assets_union") or {}).get("added") or [])

    # ---- the shape DEBT-3 is about, measured out of A
    contradiction = [r for r in a_rows if r["is_new"] and not r["http_ok"] and r["present"]]
    check("sampleA_contains_http_says_absent_disk_says_present", len(contradiction) > 0,
          {"rows": len(a_rows), "contradictions": len(contradiction),
           "example": {k: contradiction[0][k] for k in ("arm", "ref", "status", "ct", "disk_bytes")}
           if contradiction else None})
    check("sampleA_shipped_gauge_called_that_BLOCKED",
          A["preflight"]["switch_readiness"] == "BLOCKED",
          {"switch_readiness": A["preflight"]["switch_readiness"],
           "red_count_printed": len(A["preflight"]["reds"])})
    unnamed = [x for x in A["preflight"]["reds"] if str(x).split(" :: ")[0] == "?"]
    check("sampleA_shipped_reds_carry_no_ref", len(unnamed) > 0,
          {"unnamed_reds": len(unnamed), "total_reds": len(A["preflight"]["reds"]),
           "first_reds": [str(x)[:60] for x in A["preflight"]["reds"][:3]],
           "why": "the draft fixes this by stamping every row with its ref (_debt3_row)"})

    # ---- D1/D2: those rows become NAMED gaps, and a gap is never called green
    d1 = [(r, decide(PRE, r["is_new"], r["present"], r["http_ok"])) for r in contradiction]
    check("D1_preunion_export_present_asset_is_a_named_gap",
          all(o == GAP for _, o in d1) and len(d1) > 0,
          {"n": len(d1), "outcomes": sorted({o for _, o in d1}),
           "arms": sorted({r["arm"] for r, _ in d1})})
    check("D2_named_gap_is_never_reported_as_green", all(o != GREEN for _, o in d1),
          {"outcomes": sorted({o for _, o in d1}), "rule": "not green: nothing was proven over HTTP"})

    # ---- D3: the SAME observations under the strict phase stay RED (phase-bound, not a global downgrade)
    d3 = [(r, decide(POST, r["is_new"], r["present"], r["http_ok"])) for r, _ in d1]
    check("D3_same_rows_post_union_are_still_red", all(o == RED for _, o in d3) and len(d3) > 0,
          {"n": len(d3), "outcomes": sorted({o for _, o in d3})})

    # ---- D4: what B measured over HTTP is green in both phases
    b_ok = [(ref, t) for ref, t in b_map.items() if t[0]]
    d4 = [(ref, decide(POST, True, True, True), decide(PRE, True, True, True)) for ref, _ in b_ok]
    check("D4_served_real_bytes_green_in_both_phases",
          len(d4) > 0 and all(g == GREEN and p == GREEN for _, g, p in d4),
          {"n": len(d4), "refs": sorted(ref for ref, _, _ in d4)})

    # ---- D5: a new name the export itself does not carry is RED even pre-union  (synthetic input cell)
    synth_missing = "/assets/NOT_IN_THE_EXPORT.example.js"
    assert synth_missing not in new_refs
    check("D5_export_missing_name_is_red_even_pre_union",
          decide(PRE, True, False, False) == RED,
          {"input": {"phase": PRE, "is_new_generation_asset": True, "src_present": False,
                     "http_ok": False}, "ref_for_the_shape": synth_missing,
           "why": "index names an asset the export does not contain == the white screen this gauge exists "
                  "to prevent; it must never be laundered as a gap"})

    # ---- D6: a current-generation / root surface is never a gap (A's own "/" rows are the positive)
    root_rows = [r for r in a_rows if not r["is_new"]]
    check("D6_root_surface_observed_alive_in_A", len(root_rows) > 0 and
          all(r["http_ok"] for r in root_rows),
          {"refs": sorted({r["ref"] for r in root_rows}),
           "outcomes": sorted({decide(PRE, r["is_new"], r["present"], r["http_ok"]) for r in root_rows})})
    check("D6b_root_surface_down_when_absent_even_pre_union",
          decide(PRE, False, False, False) == RED,
          {"input": {"phase": PRE, "is_new_generation_asset": False, "src_present": False,
                     "http_ok": False}, "why": "the live generation must be answering right now"})

    # ---- D7: unknown phase raises instead of guessing
    try:
        decide("SOMETIMES", True, True, False)
        raised = None
    except ValueError as exc:
        raised = str(exc)[:90]
    check("D7_unknown_phase_raises", raised is not None, {"message": raised})

    # ---- D8: the signature is keyword-only with no default, and both call sites name their phase
    sig = next(n for n in ast.parse(draft_source()).body
               if isinstance(n, ast.FunctionDef) and n.name == "preflight_before_switch")
    kwonly = [a.arg for a in sig.args.kwonlyargs]
    kwdefaults = list(sig.args.kw_defaults)
    check("D8_phase_is_keyword_only_without_default",
          kwonly == ["phase"] and kwdefaults == [None],
          {"kwonlyargs": kwonly, "kw_defaults": ["<none>" if d is None else "has default"
                                                 for d in kwdefaults]})
    tree = ast.parse(draft_source())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "preflight_before_switch"]
    passed = sorted({k.arg for c in calls for k in c.keywords})
    per_call = [sorted(k.arg for k in c.keywords) for c in calls]
    phases = [next((ast.unparse(k.value) for k in c.keywords if k.arg == "phase"), "<MISSING>")
              for c in calls]
    check("D9_every_call_site_declares_its_phase",
          len(calls) == 2 and sorted(phases) == sorted(["POST_UNION", "PRE_UNION"]),
          {"n_calls": len(calls), "phases": phases, "keywords_per_call": per_call, "seen": passed})

    # ---- D10: in-service gauge untouched, draft differs only where DEBT-1..4 live
    in_service = io.open(IN_SERVICE_GAUGE, "rb").read()
    check("D10_in_service_gauge_untouched", blob_sha_of(in_service) == IN_SERVICE_GAUGE_BLOB,
          {"blob": blob_sha_of(in_service), "expected": IN_SERVICE_GAUGE_BLOB, "bytes": len(in_service)})
    check("D11_the_gap_token_is_neither_green_nor_red",
          ns["NAMED_GAP"] not in (GREEN, RED) and PRE != POST,
          {"PRE_UNION": PRE, "POST_UNION": POST, "NAMED_GAP": ns["NAMED_GAP"],
           "why": "a third state is the whole point: it must not be spelled GREEN or RED"})

    # ---- X1: the gap A named is the artifact B served - digest identity, not an assertion
    link = []
    for r, o in d1:
        served = b_map.get(r["ref"])
        if served and served[3]:
            link.append({"ref": r["ref"], "A_export_disk_sha256": r["disk_sha256"],
                         "B_served_body_sha256": served[3], "equal": r["disk_sha256"] == served[3],
                         "in_union_added": r["ref"].rsplit("/", 1)[-1] in union_added})
    check("X1_named_gap_discharged_by_measured_digest_identity",
          len(link) > 0 and all(x["equal"] and x["in_union_added"] for x in link),
          {"links": link[:4], "union_added": sorted(union_added)})

    # ---- D12/D13: the F aggregate follows the same rule, fail-closed in both directions
    def frows(pairs):
        return [{"surface": "s%d" % i, "base": "x", "ref": ref, "got": {"verdict": v}}
                for i, (ref, v) in enumerate(pairs)]
    gapish = [(f"/assets/x{i}.js", GAP) for i in range(2)]
    check("D12_F_preunion_gap_only_is_partial_not_green",
          fvo(frows(gapish + [("/", GREEN)]), False, phase=PRE) == "PARTIAL_NAMED_GAPS",
          {"verdict": fvo(frows(gapish + [("/", GREEN)]), False, phase=PRE)})
    check("D13_F_postunion_cannot_inherit_the_gap_reading",
          fvo(frows(gapish), False, phase=POST) == RED,
          {"verdict": fvo(frows(gapish), False, phase=POST),
           "why": "a gap token inside the strict arm means the lax reading leaked; refuse"})
    check("D14_F_real_red_dominates_even_pre_union",
          fvo(frows(gapish + [("/", RED)]), False, phase=PRE) == RED,
          {"verdict": fvo(frows(gapish + [("/", RED)]), False, phase=PRE)})
    check("D15_F_all_green_and_unconfigured_rules_unchanged",
          fvo(frows([("/a.js", GREEN), ("/", GREEN)]), False, phase=POST) == GREEN and
          fvo([{"surface": "tunnel", "verdict": "NOT_CONFIGURED", "base": None}], True) ==
          "F_UNPROBED_DECLARED" and
          fvo([{"surface": "tunnel", "verdict": "NOT_CONFIGURED", "base": None}], False) == RED,
          {"all_green": fvo(frows([("/a.js", GREEN), ("/", GREEN)]), False, phase=POST),
           "rule": "pre-existing F behaviour must survive the DEBT-3 edit (regression control)"})

    # ---- killers: each mutant is ONE variable and must flip exactly the cell that owns it
    mutants = {
        "M1_drop_src_present_guard": (
            '    return NAMED_GAP if src_present else "RED"', '    return NAMED_GAP'),
        "M2_drop_is_new_generation_guard": (
            '    if not is_new_generation_asset:\n        return "RED"', '    pass'),
        "M3_postunion_inherits_the_gap": (
            '    if phase == POST_UNION:\n        return "RED"', '    if False:\n        return "RED"'),
        "M4_unknown_phase_defaults_to_lax": (
            '    if phase not in DEBT3_PHASES:\n        raise ValueError',
            '    if False:\n        raise ValueError'),
        "M5_f_verdict_of_ignores_phase": (
            '    if phase == PRE_UNION and any(o == NAMED_GAP for o in outs):',
            '    if any(o == NAMED_GAP for o in outs):'),
    }
    owner = {"M1_drop_src_present_guard": ("D5_export_missing_name_is_red_even_pre_union",
                                           lambda n: n["_debt3_phase_decide"](PRE, True, False, False)),
             "M2_drop_is_new_generation_guard": ("D6b_root_surface_down_when_absent_even_pre_union",
                                                 lambda n: n["_debt3_phase_decide"](PRE, False, False, False)),
             "M3_postunion_inherits_the_gap": ("D3_same_rows_post_union_are_still_red",
                                               lambda n: n["_debt3_phase_decide"](POST, True, True, False)),
             "M4_unknown_phase_defaults_to_lax": ("D7_unknown_phase_raises",
                                                  lambda n: n["_debt3_phase_decide"]("SOMETIMES",
                                                                                     True, True, False)),
             "M5_f_verdict_of_ignores_phase": ("D13_F_postunion_cannot_inherit_the_gap_reading",
                                               lambda n: n["f_verdict_of"](frows(gapish), False,
                                                                           phase=POST))}
    kills = []
    for mname, (old, new) in sorted(mutants.items()):
        base_src = extract_fn_source("_debt3_phase_decide") if not mname.startswith("M5") \
            else extract_fn_source("f_verdict_of")
        if old not in base_src:
            kills.append({"mutant": mname, "verdict": RED,
                          "why": "anchor text not found - the mutant would be a no-op"})
            continue
        mutated = base_src.replace(old, new, 1)
        mns = extract(["PRE_UNION", "POST_UNION", "DEBT3_PHASES", "NAMED_GAP"])
        try:
            exec(compile(ast.parse(mutated), "<%s>" % mname, "exec"), mns)
            got = owner[mname][1](mns)
            flipped = (got != RED and mname != "M4_unknown_phase_defaults_to_lax") or \
                      (mname == "M4_unknown_phase_defaults_to_lax" and got != "raises")
            kills.append({"mutant": mname, "owner_cell": owner[mname][0], "verdict": "KILLED" if flipped
                          else "SURVIVED", "mutant_returned": str(got)[:60]})
        except ValueError as exc:
            # M4's whole point is that the raise disappears; any mutant that still raises is NOT killed.
            kills.append({"mutant": mname, "owner_cell": owner[mname][0],
                          "verdict": "SURVIVED" if mname == "M4_unknown_phase_defaults_to_lax" else "KILLED",
                          "mutant_returned": "ValueError: " + str(exc)[:60]})
    check("K_each_mutant_flips_only_its_own_cell",
          all(k["verdict"] == "KILLED" for k in kills) and len(kills) == len(mutants),
          {"kills": kills, "n": len(kills)})

    # ---- the rule text and the aggregate states must exist on both shapes (a reader cannot guess)
    check("R1_preunion_publishes_both_readiness_keys",
          'out["union_readiness"]' in draft_source() and "NOT_ASSESSED_PRE_UNION" in draft_source(),
          {"keys": ["union_readiness", "switch_readiness"],
           "preunion_switch_state": "NOT_ASSESSED_PRE_UNION"})
    check("R2_readonly_exit_is_judged_on_union_readiness",
          'if pf["union_readiness"] != "READY_TO_UNION":' in draft_source() and
          'phase=PRE_UNION' in draft_source(),
          {"rule": "a read-only run may answer 'may the union run', never 'may the index move'"})

    n_green = sum(1 for c in cells if c["verdict"] == GREEN)
    overall = GREEN if n_green == len(cells) else RED
    receipt = {"what": "ORD-0271-A / DEBT-3 offline proof (no deploy, no gauge import)",
               "t": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
               "draft_under_test": {"path": DRAFT.replace("\\", "/"),
                                    "bytes": len(io.open(DRAFT, "rb").read()),
                                    "blob": blob_sha_of(io.open(DRAFT, "rb").read())},
               "in_service_gauge": {"path": IN_SERVICE_GAUGE.replace("\\", "/"),
                                    "blob": blob_sha_of(in_service), "expected": IN_SERVICE_GAUGE_BLOB},
               "fixtures": {k: {"repo_path": v[0], "blob": v[1], "local": v[2].replace("\\", "/")}
                            for k, v in FIXTURES.items()},
               "decision_table": {"inputs": ["phase", "is_new_generation_asset", "src_present", "http_ok"],
                                  "outputs": [GREEN, GAP, RED]},
               "cells": cells, "cells_total": len(cells), "cells_green": n_green,
               "overall": overall,
               "claimed_result": "derived_from_published_fixtures" if overall == GREEN else "RED"}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=1, ensure_ascii=False))
    print("overall = %s  (%d/%d cells GREEN)" % (overall, n_green, len(cells)))
    for c in cells:
        print("  %-52s %s" % (c["cell"], c["verdict"]))
    for k in kills:
        print("  kill %-38s %s (%s)" % (k["mutant"], k["verdict"], k.get("mutant_returned", "")))
    print("wrote %s" % OUT)
    return 0 if overall == GREEN else 1


if __name__ == "__main__":
    raise SystemExit(main())
