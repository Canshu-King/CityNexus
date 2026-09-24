"""ORD-0271-A / DEBT-3 offline proof (r2): the pre-flight must stop answering a POST_UNION question in a
PRE_UNION run - and must not become laxer anywhere else.

r2 supersedes `test_ord0271a_debt3.py` (r1, never published).  r1 is what caught the two defects r2 now
carries cells for: (a) my first predicate derived "new generation" from the caller's index-ref list, which
left the precached lazy chunks RED in a read-only run (cell D1b), and (b) my first `f_verdict_of` returned
GREEN when a gap token leaked into the strict POST_UNION arm (cell D13).  Both are fixed in the draft and
both stay under a killer here.

Why offline: `deploy_bundle.py` (blob 149e9c6dbe6debcac92041bb192761c1cf1aa2a7) is the instrument that
currently guards the phone preview, so this test never imports the gauge and never deploys anything.  It
pulls the pure pieces out of the draft source by AST and drives them with two immutable, externally
readable field records (repo `Canshu-King/CityNexus`, branch `commander/control`):

  sample A  a real read-only `--preflight-check` (PRE_UNION) of a healthy build export that the shipped
            gauge reported BLOCKED over.
            evidence/ord0271-a-gauge-fixtures/sample_A_preunion_preflight_0923_200628.json
            blob c8e23ddd42259fb05e49376c5074a812839dad0f (26,281 B)
            Its own rows carry both halves of the contradiction: status 200 + content-type text/html from
            HTTP, and disk_present true + a real digest + 1,238,834 bytes from the build export.
  sample B  the SAME names 2m26s later, unioned and judged by the strict POST_UNION arms: overall GREEN.
            evidence/ord0271-a-gauge-fixtures/sample_B_postunion_deploy_d2665e25_0923_200854.json
            blob 0aa298042d78d317828e2d33a6a55eeabefe7bff (66,470 B)

Every expectation is derived from bytes read out of those two blobs.  Where a shape the artifacts do not
contain is needed (an export that lacks a named asset; a live surface answering HTML), the input cell is
labelled `synthetic` in the receipt and the *predicate* it exercises is still the shipped one.
"""
import ast
import base64
import hashlib
import io
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "deploy_bundle_v2_draft.py")
IN_SERVICE_GAUGE = os.path.join(HERE, "deploy_bundle.py")
IN_SERVICE_GAUGE_BLOB = "149e9c6dbe6debcac92041bb192761c1cf1aa2a7"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
BLOB_URL = "https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/%s"
FIXTURES = {
    "A": ("evidence/ord0271-a-gauge-fixtures/sample_A_preunion_preflight_0923_200628.json",
          "c8e23ddd42259fb05e49376c5074a812839dad0f",
          os.path.join(HERE, "receipts", "preflight_0923_200628.json")),
    "B": ("evidence/ord0271-a-gauge-fixtures/sample_B_postunion_deploy_d2665e25_0923_200854.json",
          "0aa298042d78d317828e2d33a6a55eeabefe7bff",
          os.path.join(HERE, "receipts",
                       "deploy_d2665e25855aeb265329266831983de42321697d_0923_200854.json")),
}
OUT = os.path.join(HERE, "receipts", "ord0271a_debt3_selftest_r2.json")
GREEN, RED, GAP = "GREEN", "RED", "NOT_YET_UNIONED_NAMED_GAP"
PARTIAL = "PARTIAL_NAMED_GAPS"


def blob_sha_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def fetch_blob(sha):
    """Read a published fixture back out of GitHub and prove the bytes by blob sha1 - a local path is not a
    coordinate (the red team caught me handing over a local-only sample on 0271-A before)."""
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(BLOB_URL % sha,
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


def draft_tree():
    return ast.parse(draft_source())


def extract(names):
    """Compile selected top-level nodes out of the draft into one shared namespace (no gauge import)."""
    src, tree = draft_source(), draft_tree()
    want = set(names)
    body = [n for n in tree.body
            if (isinstance(n, ast.FunctionDef) and n.name in want)
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in want
                                                  for t in n.targets))]
    found = set()
    for n in body:
        if isinstance(n, ast.FunctionDef):
            found.add(n.name)
        else:
            found |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    if want - found:
        raise SystemExit("DEBT-3 test cannot find in the draft: %s" % sorted(want - found))
    ns = {"pathlib": __import__("pathlib")}
    exec(compile(ast.Module(body=body, type_ignores=[]), DRAFT, "exec"), ns)
    return ns


def fn_source(name):
    return ast.get_source_segment(draft_source(), next(
        n for n in draft_tree().body if isinstance(n, ast.FunctionDef) and n.name == name))


NAMES_CACHE = {}


def probe(fn_name, old, new, call):
    """Evaluate `call` against the shipped draft and against a ONE-variable mutant of it."""
    names = [fn_name, "PRE_UNION", "POST_UNION", "DEBT3_PHASES", "NAMED_GAP"]
    clean_ns = extract(names)
    base = fn_source(fn_name)
    anchored = old in base
    mut_ns = None
    if anchored:
        mut_ns = extract(names)
        exec(compile(ast.parse(base.replace(old, new, 1)), "<mutant:%s>" % fn_name, "exec"), mut_ns)

    def safe(ns):
        if ns is None:
            return "ANCHOR_NOT_FOUND"
        try:
            return str(call(ns))
        except ValueError:
            return "ValueError"
        except Exception as exc:                       # noqa: BLE001 - name whatever the mutant did
            return type(exc).__name__
    return safe(clean_ns), safe(mut_ns), anchored


def rows_from_A(A):
    """Every new-path HTTP row the shipped gauge recorded in the PRE_UNION run.

    `export_present` comes from the row's own `disk_present`: the pre-flight passes the BUILD EXPORT as the
    disk root of these probes, so that field measures the export, not the served dist.
    `published_on_served_disk` is derived from sample B: exactly the names `assets_union.added` lists were
    copied in from the export, so they were NOT on that served root when A ran; anything else A probed was
    already there.  A name in neither set can only read as published, i.e. judged strictly - the fail-closed
    direction.
    """
    pf = A["preflight"]
    index_refs = set(A["src_index_refs"])
    rows = []

    def add(arm, got_row, verdict):
        p = got_row["probes"][0]
        rows.append({"arm": arm, "ref": p["path"], "http_ok": verdict == GREEN,
                     "export_present": bool(p["disk_present"]), "status": p["status"],
                     "ct": p["content_type"], "export_sha256": p.get("disk_sha256"),
                     "export_bytes": p.get("disk_bytes"), "named_by_new_index": p["path"] in index_refs})

    for v in pf["C_pre_new_assets_reach_the_live_server"]:
        add("C_pre", v, v["verdict"])
    for e in pf["G_pre_precache_of_the_new_sw_resolves"]:
        for pr in e["probes"]:
            if pr.get("got"):
                add("G_pre/" + e["sw"], pr["got"], pr["got"]["verdict"])
    for pr in pf["F_pre_user_surfaces"]["probes"]:
        if pr.get("got"):
            add("F_pre/" + str(pr.get("surface")), pr["got"], pr["got"]["verdict"])
    return rows, index_refs


def served_from_B(B):
    """ref -> (http_ok, status, content_type, body sha256) as the strict POST_UNION arms measured them."""
    m = {}
    for v in B.get("pre_switch_asset_probes") or []:
        for p in v["probes"]:
            m[p["path"]] = (v["verdict"] == GREEN, p["status"], p["content_type"], p.get("sha256"))
    return m


def main():
    cells = []

    def check(name, ok, detail):
        cells.append({"cell": name, "verdict": GREEN if ok else RED, "detail": detail})

    A, a_bytes = fetch_blob(FIXTURES["A"][1])
    B, b_bytes = fetch_blob(FIXTURES["B"][1])
    for key, path, size in (("A", FIXTURES["A"][2], a_bytes), ("B", FIXTURES["B"][2], b_bytes)):
        local = io.open(path, "rb").read()
        check("fixture_%s_published_and_byte_identical" % key,
              len(local) == size and blob_sha_of(local) == FIXTURES[key][1],
              {"repo_path": FIXTURES[key][0], "blob": FIXTURES[key][1], "published_len": size,
               "local_len": len(local)})

    ns = extract(["PRE_UNION", "POST_UNION", "DEBT3_PHASES", "NAMED_GAP", "_debt3_phase_decide",
                  "_debt3_row", "f_verdict_of", "preflight_before_switch"])
    decide, fvo = ns["_debt3_phase_decide"], ns["f_verdict_of"]
    PRE, POST = ns["PRE_UNION"], ns["POST_UNION"]
    a_rows, index_refs = rows_from_A(A)
    b_map = served_from_B(B)
    union_added = set((B.get("assets_union") or {}).get("added") or [])
    for r in a_rows:
        r["published_on_served_disk"] = r["ref"].rsplit("/", 1)[-1] not in union_added

    # the signature this test drives must be the signature the gauge carries
    sig = next(n for n in draft_tree().body if isinstance(n, ast.FunctionDef)
               and n.name == "_debt3_phase_decide")
    check("S0_predicate_signature_matches_this_test",
          [a.arg for a in sig.args.args] == ["phase", "present_in_export", "published_on_served_disk",
                                            "http_ok"],
          {"argnames": [a.arg for a in sig.args.args],
           "why": "if the gauge grows a fifth input, driving four of them here would be decoration"})

    # ---- the contradiction DEBT-3 is about, measured out of A
    contradiction = [r for r in a_rows if not r["http_ok"] and r["export_present"]]
    check("A1_sampleA_rows_say_http_absent_export_present", len(contradiction) > 0,
          {"rows": len(a_rows), "contradictions": len(contradiction),
           "example": {k: contradiction[0][k] for k in ("arm", "ref", "status", "ct", "export_bytes")}
           if contradiction else None})
    check("A2_shipped_gauge_called_that_BLOCKED",
          A["preflight"]["switch_readiness"] == "BLOCKED",
          {"switch_readiness": A["preflight"]["switch_readiness"],
           "red_count_printed": len(A["preflight"]["reds"])})
    unnamed = [x for x in A["preflight"]["reds"] if str(x).split(" :: ")[0] == "?"]
    check("A3_shipped_reds_carry_no_ref", len(unnamed) > 0,
          {"unnamed_reds": len(unnamed), "total_reds": len(A["preflight"]["reds"]),
           "first_reds": [str(x)[:58] for x in A["preflight"]["reds"][:3]],
           "why": "_debt3_row stamps every row with its ref, so a refusal names what it refused"})

    # ---- D1/D1b: those rows become NAMED gaps, including the chunks no index names
    d1 = [(r, decide(PRE, r["export_present"], r["published_on_served_disk"], r["http_ok"]))
          for r in contradiction]
    check("D1_preunion_export_present_unserved_name_is_a_named_gap",
          len(d1) > 0 and all(o == GAP for _, o in d1),
          {"n": len(d1), "outcomes": sorted({o for _, o in d1}), "arms": sorted({r["arm"] for r, _ in d1})})
    not_in_index = [r for r, _ in d1 if not r["named_by_new_index"]]
    check("D1b_gap_set_includes_precached_chunks_the_index_never_names", len(not_in_index) > 0,
          {"n": len(not_in_index), "refs": sorted({r["ref"] for r in not_in_index}),
           "rule": "this cell killed my first predicate (index-membership): an index-derived rule judged "
                   "these RED in a read-only run and left DEBT-3 half open"})
    check("D2_named_gap_is_never_reported_as_green", all(o != GREEN for _, o in d1),
          {"outcomes": sorted({o for _, o in d1}), "rule": "not green: nothing was proven over HTTP"})

    # ---- D3: the SAME observations under the strict phase stay RED (phase-bound, not a global downgrade)
    d3 = [decide(POST, r["export_present"], r["published_on_served_disk"], r["http_ok"]) for r, _ in d1]
    check("D3_same_rows_post_union_are_still_red", len(d3) > 0 and all(o == RED for o in d3),
          {"n": len(d3), "outcomes": sorted(set(d3))})

    # ---- D4: what B actually served over HTTP is green in both phases
    b_ok = [ref for ref, t in b_map.items() if t[0]]
    d4 = [(ref, decide(POST, True, True, True), decide(PRE, True, False, True)) for ref in b_ok]
    check("D4_served_real_bytes_green_in_both_phases",
          len(d4) > 0 and all(g == GREEN and pr == GREEN for _, g, pr in d4),
          {"n": len(d4), "refs": sorted(r for r, _, _ in d4)})

    # ---- D5: a name the export itself lacks is RED even pre-union (synthetic input, shipped predicate)
    check("D5_export_missing_name_is_red_even_pre_union", decide(PRE, False, False, False) == RED,
          {"input": {"phase": PRE, "present_in_export": False, "published_on_served_disk": False,
                     "http_ok": False}, "synthetic": True,
           "why": "an index that names an asset the export lacks is the white screen this gauge exists for"})

    # ---- D6: a name already on the served disk is never a gap; A's own "/" rows are the positive control
    root_rows = [r for r in a_rows if r["ref"] == "/"]
    check("D6_root_surface_observed_alive_in_A", len(root_rows) > 0 and all(r["http_ok"] for r in root_rows),
          {"n": len(root_rows),
           "outcomes": sorted({decide(PRE, r["export_present"], True, r["http_ok"]) for r in root_rows})})
    check("D6b_already_served_surface_down_is_red_even_pre_union",
          decide(PRE, True, True, False) == RED,
          {"input": {"phase": PRE, "present_in_export": True, "published_on_served_disk": True,
                     "http_ok": False}, "synthetic": True,
           "why": "the live generation must be answering right now; that is not the union's debt"})

    # ---- D7/D8/D9: the phase cannot be guessed, defaulted, or forgotten at a call site
    try:
        decide("SOMETIMES", True, False, False)
        raised = None
    except ValueError as exc:
        raised = str(exc)[:88]
    check("D7_unknown_phase_raises", raised is not None, {"message": raised})
    pf_sig = next(n for n in draft_tree().body if isinstance(n, ast.FunctionDef)
                  and n.name == "preflight_before_switch")
    check("D8_phase_is_keyword_only_without_default",
          [a.arg for a in pf_sig.args.kwonlyargs] == ["phase"] and list(pf_sig.args.kw_defaults) == [None],
          {"kwonlyargs": [a.arg for a in pf_sig.args.kwonlyargs],
           "kw_defaults": ["<none>" if d is None else "HAS DEFAULT" for d in pf_sig.args.kw_defaults]})
    calls = [n for n in ast.walk(draft_tree()) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "preflight_before_switch"]
    phases = [next((ast.unparse(k.value) for k in c.keywords if k.arg == "phase"), "<MISSING>") for c in calls]
    check("D9_every_call_site_declares_its_phase",
          len(calls) == 2 and sorted(phases) == ["POST_UNION", "PRE_UNION"],
          {"n_calls": len(calls), "phases": phases,
           "keywords": [sorted(k.arg for k in c.keywords) for c in calls]})

    # ---- D10/D11: the live instrument is untouched, and the third state is spelled as a third state
    in_service = io.open(IN_SERVICE_GAUGE, "rb").read()
    check("D10_in_service_gauge_untouched", blob_sha_of(in_service) == IN_SERVICE_GAUGE_BLOB,
          {"path": IN_SERVICE_GAUGE.replace("\\", "/"), "bytes": len(in_service),
           "blob": blob_sha_of(in_service), "expected": IN_SERVICE_GAUGE_BLOB})
    check("D11_the_gap_token_is_neither_green_nor_red",
          ns["NAMED_GAP"] not in (GREEN, RED) and PRE != POST and tuple(ns["DEBT3_PHASES"]) == (PRE, POST),
          {"PRE_UNION": PRE, "POST_UNION": POST, "NAMED_GAP": ns["NAMED_GAP"]})

    # ---- X1: the gap A named IS the artifact B served - digest identity, not an assertion
    link = []
    for r, _ in d1:
        served = b_map.get(r["ref"])
        if served and served[3]:
            link.append({"ref": r["ref"], "A_export_sha256": r["export_sha256"],
                         "B_served_body_sha256": served[3], "equal": r["export_sha256"] == served[3],
                         "in_union_added": r["ref"].rsplit("/", 1)[-1] in union_added})
    check("X1_named_gap_discharged_by_measured_digest_identity",
          len(link) > 0 and all(x["equal"] and x["in_union_added"] for x in link),
          {"links": link[:4], "n": len(link), "union_added": sorted(union_added)})

    # ---- D12..D15: the F aggregate follows the same rule and fails closed in both directions
    def frows(pairs):
        return [{"surface": "s%d" % i, "base": "x", "ref": ref, "got": {"verdict": v}}
                for i, (ref, v) in enumerate(pairs)]
    gapish = [("/assets/x%d.js" % i, GAP) for i in range(2)]
    check("D12_F_preunion_gap_only_is_partial_not_green",
          fvo(frows(gapish + [("/", GREEN)]), False, phase=PRE) == PARTIAL,
          {"verdict": fvo(frows(gapish + [("/", GREEN)]), False, phase=PRE)})
    check("D13_F_postunion_cannot_inherit_the_gap_reading",
          fvo(frows(gapish), False, phase=POST) == RED,
          {"verdict": fvo(frows(gapish), False, phase=POST),
           "why": "a gap token in the strict arm means the lax reading leaked; refuse.  This cell caught a "
                  "fail-open in my own first version, which answered GREEN here."})
    check("D14_F_real_red_dominates_even_pre_union",
          fvo(frows(gapish + [("/", RED)]), False, phase=PRE) == RED,
          {"verdict": fvo(frows(gapish + [("/", RED)]), False, phase=PRE)})
    unconf = [{"surface": "tunnel", "verdict": "NOT_CONFIGURED", "base": None}]
    check("D15_F_pre_existing_rules_unchanged",
          fvo(frows([("/a.js", GREEN), ("/", GREEN)]), False, phase=POST) == GREEN and
          fvo(unconf, True) == "F_UNPROBED_DECLARED" and fvo(unconf, False) == RED and
          fvo(frows([("/a.js", "WEIRD_TOKEN")]), False, phase=PRE) == RED,
          {"all_green": fvo(frows([("/a.js", GREEN), ("/", GREEN)]), False, phase=POST),
           "declared": fvo(unconf, True), "undeclared": fvo(unconf, False),
           "unknown_token": fvo(frows([("/a.js", "WEIRD_TOKEN")]), False, phase=PRE),
           "rule": "regression control: DEBT-3 must not quietly re-point A-3 / F_UNPROBED_DECLARED"})

    # ---- killers: one variable each, and each must flip exactly the cell that owns it
    RET = 'return NAMED_GAP if (present_in_export and not published_on_served_disk) else "RED"'
    killers = [
        {"mutant": "M1_drop_present_in_export_clause", "fn": "_debt3_phase_decide",
         "owner_cell": "D5_export_missing_name_is_red_even_pre_union", "old": RET,
         "new": 'return NAMED_GAP if (not published_on_served_disk) else "RED"',
         "call": lambda n: n["_debt3_phase_decide"](n["PRE_UNION"], False, False, False),
         "expect_clean": RED, "expect_mutant": GAP},
        {"mutant": "M2_drop_published_on_served_disk_clause", "fn": "_debt3_phase_decide",
         "owner_cell": "D6b_already_served_surface_down_is_red_even_pre_union", "old": RET,
         "new": 'return NAMED_GAP if present_in_export else "RED"',
         "call": lambda n: n["_debt3_phase_decide"](n["PRE_UNION"], True, True, False),
         "expect_clean": RED, "expect_mutant": GAP},
        {"mutant": "M3_postunion_inherits_the_gap", "fn": "_debt3_phase_decide",
         "owner_cell": "D3_same_rows_post_union_are_still_red",
         "old": "    if phase == POST_UNION:", "new": "    if False:",
         "call": lambda n: n["_debt3_phase_decide"](n["POST_UNION"], True, False, False),
         "expect_clean": RED, "expect_mutant": GAP},
        {"mutant": "M4_unknown_phase_no_longer_raises", "fn": "_debt3_phase_decide",
         "owner_cell": "D7_unknown_phase_raises",
         "old": "    if phase not in DEBT3_PHASES:", "new": "    if False:",
         "call": lambda n: n["_debt3_phase_decide"]("SOMETIMES", True, False, False),
         "expect_clean": "ValueError", "expect_mutant": GAP},
        {"mutant": "M5_f_verdict_of_ignores_phase", "fn": "f_verdict_of",
         "owner_cell": "D13_F_postunion_cannot_inherit_the_gap_reading",
         "old": 'if phase == PRE_UNION and all(o in ("GREEN", NAMED_GAP) for o in outs):',
         "new": 'if all(o in ("GREEN", NAMED_GAP) for o in outs):',
         "call": lambda n: n["f_verdict_of"](frows(gapish), False, phase=n["POST_UNION"]),
         "expect_clean": RED, "expect_mutant": PARTIAL},
    ]
    kills = []
    for k in killers:
        clean, mut, anchored = probe(k["fn"], k["old"], k["new"], k["call"])
        kills.append({"mutant": k["mutant"], "owner_cell": k["owner_cell"], "anchored": anchored,
                      "clean_returned": clean, "mutant_returned": mut,
                      "verdict": "KILLED" if (anchored and clean == k["expect_clean"] and
                                              mut == k["expect_mutant"]) else "SURVIVED"})
    check("K1_every_mutant_flips_only_its_own_cell",
          len(kills) == len(killers) and all(x["verdict"] == "KILLED" for x in kills),
          {"kills": kills, "n": len(kills),
           "owners_are_distinct": len({x["owner_cell"] for x in kills}) == len(kills)})

    # ---- the aggregate states a reader sees, both phases
    ds = draft_source()
    check("R1_preunion_publishes_both_readiness_keys",
          'out["union_readiness"]' in ds and "NOT_ASSESSED_PRE_UNION" in ds and "READY_TO_UNION" in ds,
          {"keys": ["union_readiness", "switch_readiness"],
           "preunion_switch_state": "NOT_ASSESSED_PRE_UNION"})
    check("R2_readonly_exit_is_judged_on_union_readiness",
          'if pf["union_readiness"] != "READY_TO_UNION":' in ds and "phase=PRE_UNION" in ds and
          "phase=POST_UNION" in ds,
          {"rule": "a read-only run may answer 'may the union run', never 'may the index move'"})

    n_green = sum(1 for c in cells if c["verdict"] == GREEN)
    overall = GREEN if n_green == len(cells) else RED
    draft_bytes = io.open(DRAFT, "rb").read()
    receipt = {"what": "ORD-0271-A / DEBT-3 offline proof r2 (no deploy, no gauge import, published fixtures)",
               "supersedes": "test_ord0271a_debt3.py (r1, local only, never published)",
               "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "draft_under_test": {"path": DRAFT.replace("\\", "/"), "bytes": len(draft_bytes),
                                    "blob": blob_sha_of(draft_bytes)},
               "in_service_gauge": {"path": IN_SERVICE_GAUGE.replace("\\", "/"),
                                    "blob": blob_sha_of(in_service), "expected": IN_SERVICE_GAUGE_BLOB},
               "fixtures": {k: {"repo_path": v[0], "blob": v[1], "local": v[2].replace("\\", "/")}
                            for k, v in FIXTURES.items()},
               "derivation": {
                   "export_present": "the row's own disk_present: the pre-flight probes pass the BUILD "
                                     "EXPORT as the disk root, so that field measures the export",
                   "published_on_served_disk": "false exactly for names listed in sample B's "
                                               "assets_union.added (the union copied them in from the "
                                               "export, so they were absent from that root when A ran)",
                   "decision_table_inputs": ["phase", "present_in_export", "published_on_served_disk",
                                             "http_ok"]},
               "cells": cells, "cells_total": len(cells), "cells_green": n_green, "overall": overall,
               "claimed_result": "offline_selftest_" + overall}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=1, ensure_ascii=False))
    print("overall = %s  (%d/%d cells GREEN)" % (overall, n_green, len(cells)))
    for c in cells:
        print("  %-58s %s" % (c["cell"], c["verdict"]))
    for x in kills:
        print("  kill %-42s %-8s clean=%s mutant=%s" % (x["mutant"], x["verdict"], x["clean_returned"],
                                                        x["mutant_returned"]))
    print("wrote %s" % OUT)
    return 0 if overall == GREEN else 1


if __name__ == "__main__":
    raise SystemExit(main())
