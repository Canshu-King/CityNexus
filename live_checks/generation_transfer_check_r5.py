"""generation_transfer_check.py - mechanical judge for GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1.

Arbiter ruling Q24 = (1) at 2026-09-25T04:0x+08 said this rule must live in a validator, not in anyone's
memory.  So this file is that validator.  It answers ONE question and answers it from the API, never from
prose:

    a receipt cell observed at generation A is quoted as if it also described generation B - is that legal?

Rule as implemented (one unit = one observation CELL, never the whole order):
    TRANSFERABLE                       every cited file's 40-hex blob is identical at A and B
    NOT_TRANSFERABLE_GENERATION        at least one cited blob differs
    CITED_BLOB_MISSING                 a cited path cannot be resolved at one or both generations
                                       (fail-closed: "we could not look" is never read as "it matched")

`derived_result` is computed from the per-cell verdicts; no cell verdict and no overall string is a literal
in this source.  The self-test proves the judge bites BOTH ways against real repository objects, so a
future edit that makes it permissive is caught here rather than in someone's receipt.

Read-only: GET requests only, no writes, no token is ever printed.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipts",
                   "generation_transfer_check_selftest_r5.json")   # r5: own scratch name, never overwrites r4's
# Why a side could not be read, kept per (ref|path) so a MISSING verdict in the receipt is explainable
# ("HTTP 404" = the file is not in that generation; "IncompleteRead" = the link was flaky).
LAST_ERROR = {}

TRANSFERABLE = "TRANSFERABLE"
NOT_TRANSFERABLE = "NOT_TRANSFERABLE_GENERATION"
MISSING = "CITED_BLOB_MISSING"
UNDECLARED = "CLAIM_KIND_UNDECLARED"
CODE_DETERMINED = "code_determined"
RUNTIME_MEASURED = "runtime_measured"
CLAIM_KINDS = (CODE_DETERMINED, RUNTIME_MEASURED)


def _get(path):
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-generation-transfer-validator", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def blob_at(ref, repo_path, attempts=3):
    """The 40-hex blob sha GitHub reports for one file at one commit.  None means 'not resolvable'.

    A transport hiccup IS 'not resolvable' and must land as CITED_BLOB_MISSING downstream.  r1 crashed the
    whole run on `http.client.IncompleteRead` (a truncated 660 KB response on this link at 04:2x) - a
    validator that dies on a flaky read is worse than one that reports the missing side, because the
    operator retries it until it happens to pass.

    r2 adds BOUNDED RETRIES for exactly that reason: measured at 04:2x, the same file read fine in one
    cell and came back missing in another within one run, so without retries the flakiness of the link
    would be reported as a fact about the repository.  `last_error` is kept for the receipt.
    """
    import http.client
    import time
    last = {"err": None, "code": None}
    for k in range(attempts):
        try:
            meta = _get("/repos/%s/contents/%s?ref=%s" % (REPO, repo_path.lstrip("/"), ref))
            if isinstance(meta, list) or meta.get("type") != "file":
                LAST_ERROR[ref + "|" + repo_path] = "NOT_A_FILE"
                return None
            LAST_ERROR.pop(ref + "|" + repo_path, None)
            return meta.get("sha")
        except urllib.error.HTTPError as exc:
            last["code"] = exc.code
            last["err"] = "HTTPError"
            if exc.code in (404, 400):        # genuinely absent - no point retrying
                LAST_ERROR[ref + "|" + repo_path] = "HTTP_%s" % exc.code
                return None
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as exc:
            last["err"] = "%s" % type(exc).__name__
        if k + 1 < attempts:
            time.sleep(1.5 * (k + 1))
    LAST_ERROR[ref + "|" + repo_path] = last.get("err") or "unknown"
    return None


def judge_cell(cell, gen_a, gen_b, cited_files, reader=None, claim_kind=None):
    """One cell, one verdict, derived only from the two-sided blob readings it can name.

    `reader` is injectable so the self-test can hand the SAME judge tampered pairs (a near-miss hex, a
    prefix-equal truncation).  Without that, "the judge compares whole 40-hex strings" would be a claim in
    a comment rather than something that can fail - which is the defect class this whole night is about.

    r3 adds `claim_kind`, from the ORD-0279 lesson: blob identity licenses a claim whose truth IS determined
    by those bytes.  A duration, a race outcome or a load figure is not, so quoting it across generations
    stays forbidden even when every cited blob matches.  Not declaring a kind is not a pass either.
    """
    reader = reader or blob_at
    ka, kb = "at_" + gen_a[:9], "at_" + gen_b[:9]

    def read(ref, path):
        """A reader that throws is a side we could not look at - never a match, never a crash."""
        try:
            return reader(ref, path)
        except Exception:
            return None

    rows = {}
    for p in cited_files:
        rows[p] = {ka: read(gen_a, p), kb: read(gen_b, p)}
    if not cited_files:
        # a cell that cites nothing cannot be shown to be generation-independent - fail closed
        return {"cell": cell, "verdict": MISSING, "cited": {}, "why": "NO_CITED_FILES"}, rows
    if claim_kind not in CLAIM_KINDS:
        return {"cell": cell, "verdict": UNDECLARED, "claim_kind": claim_kind,
                "cited": {p: {ka: rows[p][ka], kb: rows[p][kb]} for p in cited_files},
                "why": "CLAIM_KIND_NOT_DECLARED - absence of a declaration is not a licence"}, rows
    missing = [p for p, r in rows.items() if not r[ka] or not r[kb]]
    differ = [p for p, r in rows.items() if r[ka] and r[kb] and r[ka] != r[kb]]
    if missing:
        verdict, why = MISSING, "one or both sides unread"
    elif differ:
        verdict, why = NOT_TRANSFERABLE, "cited blob differs"
    elif claim_kind == RUNTIME_MEASURED:
        verdict, why = NOT_TRANSFERABLE, "RUNTIME_MEASURED_NOT_LICENSED_BY_BLOB_IDENTITY"
    else:
        verdict, why = TRANSFERABLE, None
    return {"cell": cell, "verdict": verdict, "claim_kind": claim_kind, "why": why,
            "cited": {p: {ka: rows[p][ka], kb: rows[p][kb]} for p in cited_files},
            "errors": {p: LAST_ERROR.get(gen_a + "|" + p) or LAST_ERROR.get(gen_b + "|" + p)
                       for p in cited_files if p in missing},
            "missing": missing, "differ": differ}, rows


# --- the self-test: three real repository facts, one per verdict, plus the two-way killers -------------
GEN_A = "c79e2b4f4efe414dba22a071a7136ae10b5c84aa"          # the generation ORD-0279 actually ran on
GEN_B = "dcae1bc964125c3a975916f6bf667794cc19622a"          # the landed generation (child of GEN_A)
SAME_FILE = "frontend/src/features/planning/PlanWithAiSheet.tsx"
CHANGED_FILE = "backend/app/main.py"
ONLY_IN_B_FILE = "backend/tests/test_qoder_ord0272_continuation.py"

# r4: every control pair carries its EXPECTED blob at both generations, measured 2026-09-25T04:4x+08 with
# `git rev-parse <ref>:<path>`.  A positive control that is only "whatever this file happens to be today"
# is a premise, not a control - lane F caught that mine could silently stop being identical.
CONTROL_PAIRS = [
    # path, expected at GEN_A (c79e2b4f), expected at GEN_B (dcae1bc96), role
    ("frontend/src/features/planning/PlanWithAiSheet.tsx",
     "58c0580bbb603c939592ae8b911c4a291b4eb60a",
     "58c0580bbb603c939592ae8b911c4a291b4eb60a", "identical"),
    ("backend/app/schemas.py",
     "679ac2eb34b11f4e1a9dc7295292ae1df75c05cb",
     "2e6e26ce17a9e25a40dd8d686f64def5ef1bff0e", "differing"),
    ("contracts/openapi.yaml",
     "4bc58e2e95a09ae46e346d9b243b165a03f58be8",
     "484c64cdaaa41e72d252563b84cef915cb4e80eb", "differing"),
]
EXTERNAL_OK = "EXTERNAL_READBACK_MATCHES_PINNED_EXPECTATIONS"
EXTERNAL_DRIFT = "EXTERNAL_READBACK_CONTROL_PREMISE_DRIFT"
EXTERNAL_UNRESOLVED = "EXTERNAL_READBACK_UNRESOLVED_THIS_RUN"


def pinned_reader(pairs):
    """A reader that answers from the pinned table - so judge correctness is decided offline, deterministically."""
    table = {}
    for path, a, b, _role in pairs:
        table[(GEN_A, path)] = a
        table[(GEN_B, path)] = b

    def read(ref, path):
        return table.get((ref, path))
    return read


def selftest():
    results = {}
    pr = pinned_reader(CONTROL_PAIRS)
    pos = [c for c in CONTROL_PAIRS if c[3] == "identical"]
    neg = [c for c in CONTROL_PAIRS if c[3] == "differing"]
    ok_same, rows_same = judge_cell("pos_transferable", GEN_A, GEN_B, [pos[0][0]], reader=pr,
                                    claim_kind=CODE_DETERMINED)
    results["positive_identical_file_is_TRANSFERABLE"] = ok_same["verdict"] == TRANSFERABLE
    ok_neg1, _ = judge_cell("neg_schemas", GEN_A, GEN_B, [neg[0][0]], reader=pr, claim_kind=CODE_DETERMINED)
    ok_neg2, _ = judge_cell("neg_openapi", GEN_A, GEN_B, [neg[1][0]], reader=pr, claim_kind=CODE_DETERMINED)
    results["negative_changed_file_is_NOT_TRANSFERABLE"] = (
        ok_neg1["verdict"] == NOT_TRANSFERABLE and ok_neg2["verdict"] == NOT_TRANSFERABLE)
    ok_missing, rows_missing = judge_cell("neg_only_one_generation", GEN_A, GEN_B, [ONLY_IN_B_FILE],
                                          reader=lambda g, p: None if p == ONLY_IN_B_FILE else pr(g, p),
                                          claim_kind=CODE_DETERMINED)
    results["missing_side_is_CITED_BLOB_MISSING_not_pass"] = ok_missing["verdict"] == MISSING
    ok_mixed, rows_mixed = judge_cell("mixed_pair", GEN_A, GEN_B, [pos[0][0], neg[0][0]], reader=pr,
                                      claim_kind=CODE_DETERMINED)
    results["one_changed_file_poisons_the_whole_cell"] = ok_mixed["verdict"] == NOT_TRANSFERABLE
    ok_empty, _ = judge_cell("no_citations", GEN_A, GEN_B, [], reader=pr, claim_kind=CODE_DETERMINED)
    results["cell_citing_nothing_fails_closed"] = ok_empty["verdict"] == MISSING
    # ---- comparison-laxness killers: the SAME judge, fed tampered pairs through the injected reader.
    real = pos[0][1]
    near = real[:-1] + ("0" if real[-1] != "0" else "1")          # one hex different, same length
    prefix = real[:20]                                            # prefix-equal, half the length
    def reader_near(g, p):
        return real if g == GEN_A else near
    def reader_prefix(g, p):
        return real if g == GEN_A else prefix
    def reader_equal(g, p):
        return real
    v_near, _ = judge_cell("killer_near_miss", GEN_A, GEN_B, [pos[0][0]], reader=reader_near,
                           claim_kind=CODE_DETERMINED)
    v_prefix, _ = judge_cell("killer_prefix_only", GEN_A, GEN_B, [pos[0][0]], reader=reader_prefix,
                             claim_kind=CODE_DETERMINED)
    v_equal, _ = judge_cell("control_identical_pair", GEN_A, GEN_B, [pos[0][0]], reader=reader_equal,
                            claim_kind=CODE_DETERMINED)
    results["K1_one_hex_different_is_NOT_TRANSFERABLE"] = v_near["verdict"] == NOT_TRANSFERABLE
    results["K2_prefix_equal_but_shorter_is_NOT_TRANSFERABLE"] = v_prefix["verdict"] == NOT_TRANSFERABLE
    results["K3_identical_pair_control_stays_TRANSFERABLE"] = v_equal["verdict"] == TRANSFERABLE
    results["K4_missing_side_reader_is_NOT_transferable"] = (
        judge_cell("killer_one_side_none", GEN_A, GEN_B, [pos[0][0]],
                   reader=lambda g, p: real if g == GEN_A else None,
                   claim_kind=CODE_DETERMINED)[0]["verdict"] == MISSING)

    def reader_throws(g, p):
        raise RuntimeError("simulated IncompleteRead on a truncated response")
    v_throw, _ = judge_cell("killer_transport_throw", GEN_A, GEN_B, [pos[0][0]], reader=reader_throws,
                            claim_kind=CODE_DETERMINED)
    results["K5_transport_exception_is_CITED_BLOB_MISSING_not_a_crash_not_a_pass"] = v_throw["verdict"] == MISSING

    # ---- r3 killers, from the ORD-0279 lesson the red team caught me in: identical blobs do not license
    #      a claim whose truth is not determined by those bytes, and not declaring a kind is not a pass.
    v_runtime, _ = judge_cell("killer_runtime_measured", GEN_A, GEN_B, [pos[0][0]], reader=reader_equal,
                              claim_kind=RUNTIME_MEASURED)
    results["K6_runtime_measured_with_identical_blobs_is_STILL_NOT_TRANSFERABLE"] = (
        v_runtime["verdict"] == NOT_TRANSFERABLE
        and v_runtime.get("why") == "RUNTIME_MEASURED_NOT_LICENSED_BY_BLOB_IDENTITY")
    v_undeclared, _ = judge_cell("killer_undeclared", GEN_A, GEN_B, [pos[0][0]], reader=reader_equal)
    results["K7_undeclared_claim_kind_is_NOT_a_pass"] = v_undeclared["verdict"] == UNDECLARED

    # ---- r5: the whole-receipt judgement (ORD-0283 bit here: A7 empty-set aggregation, A9 key spelling).
    #      Bitten offline - derive_result takes the parsed doc and the per-cell rows, so no network and no
    #      dependency on whether a generation happens to resolve right now.
    d_k9, rc_k9, cl_k9, _, _ = derive_result({"cross_generation_claim": "we moved this"}, [])
    results["K9_claim_with_zero_cells_is_RED_not_vacuously_green"] = (
        d_k9 == CLAIM_WITH_NO_CELLS and rc_k9 == 4 and cl_k9 is True)
    d_k10, rc_k10, cl_k10, key_k10, _ = derive_result({"crossGenerationClaim": "we moved this"}, [])
    results["K10_camelCase_claim_key_cannot_escape_judgement"] = (
        cl_k10 is True and d_k10 == CLAIM_WITH_NO_CELLS and rc_k10 == 4 and key_k10 == "crossGenerationClaim")
    d_k11, rc_k11, cl_k11, key_k11, _ = derive_result({"unrelated_key": 1}, [])
    results["K11_negative_no_claim_key_still_exits_zero"] = (
        cl_k11 is False and d_k11 == "NO_CROSS_GENERATION_CLAIM_MADE" and rc_k11 == 0 and key_k11 is None)
    green_row = [{"cell": "only_cell", "verdict": TRANSFERABLE}]
    d_k12, rc_k12, cl_k12, _, _ = derive_result({"cross_generation_claim": "x"}, green_row)
    results["K12_negative_claimed_with_a_real_green_cell_stays_green"] = (
        d_k12 == "ALL_CELLS_TRANSFERABLE" and rc_k12 == 0)
    d_k13, rc_k13, _, _, tal_k13 = derive_result(
        {"unrelated": 1}, [{"cell": "a", "verdict": MISSING}, {"cell": "b", "verdict": TRANSFERABLE}])
    results["K13_no_claim_but_missing_is_counted_not_hidden"] = (
        rc_k13 == 0 and tal_k13.get(MISSING) == 1)
    # K14/K15 bite the KEY MATCHER itself, both ways: three spellings must be seen as claims, and keys that
    # merely contain "gen" or "cross" must NOT (otherwise every receipt would read as claiming).
    spellings = ("cross_generation_claim", "crossGenerationClaim", "cross-generation-claim")
    results["K14_all_three_claim_spellings_are_detected"] = all(
        find_claim({k: "x"})[0] == "x" for k in spellings)
    decoys = ("generation_gap", "cross_reference", "claim_count", "cells", "schema")
    results["K15_decoy_keys_are_NOT_read_as_claims"] = all(find_claim({d: "x"})[0] is None for d in decoys)
    # Breadth, stated rather than hidden: a key like "cross_generationaclaim" also matches.  Over-inclusion
    # is the safe direction - it means MORE receipts get judged, never fewer.

    # ---- r4: ONE live read-back cell, separate from judge correctness.  It can fail for exactly two named
    #      reasons, and neither of them is allowed to look like "the judge is broken".
    live = []
    unresolved = []
    drift = []
    for path, exp_a, exp_b, role in CONTROL_PAIRS:
        got_a, got_b = blob_at(GEN_A, path), blob_at(GEN_B, path)
        row = {"path": path, "role": role, "expected_a": exp_a, "expected_b": exp_b,
               "observed_a": got_a, "observed_b": got_b}
        if not got_a or not got_b:
            row["state"] = "UNRESOLVED"
            unresolved.append(path)
        elif got_a != exp_a or got_b != exp_b:
            row["state"] = "DRIFT"
            drift.append(path)
        else:
            row["state"] = "MATCH"
        live.append(row)
    external_result = EXTERNAL_OK if not unresolved and not drift else (
        EXTERNAL_UNRESOLVED if unresolved else EXTERNAL_DRIFT)
    results["K8_live_readback_cell_exists_and_is_separate_from_judge_checks"] = bool(live)
    judge_derived = "JUDGE_ALL_GREEN" if all(results.values()) else "RED_CELLS:" + ",".join(
        k for k, v in results.items() if not v)
    receipt = {
        "schema": "CNX_GENERATION_TRANSFER_SELFTEST_V1",
        "rule": "GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1",
        "ruling": "arbiter Q24 = (1), 2026-09-25T04:0x+08, in the designated window",
        "gen_a": GEN_A, "gen_b": GEN_B,
        "cells_under_test": {
            "positive_identical_file": ok_same,
            "negative_schemas_pinned": ok_neg1,
            "negative_openapi_pinned": ok_neg2,
            "missing_side": ok_missing,
            "mixed_pair": ok_mixed,
            "no_citations": ok_empty,
            "killer_near_miss": v_near,
            "killer_prefix_only": v_prefix,
            "control_identical_pair": v_equal,
            "killer_transport_throw": v_throw,
            "killer_runtime_measured": v_runtime,
            "killer_undeclared": v_undeclared,
            "receipt_claim_with_zero_cells": {"verdict": d_k9, "rc": rc_k9, "claimed": cl_k9},
            "receipt_camelCase_key": {"verdict": d_k10, "rc": rc_k10, "key": key_k10},
            "receipt_no_claim_negative": {"verdict": d_k11, "rc": rc_k11, "key": key_k11},
            "receipt_green_cell_negative": {"verdict": d_k12, "rc": rc_k12},
            "receipt_missing_tally_no_claim": {"rc": rc_k13, "tally": tal_k13},
        },
        "checks": results,
        "judge_derived_result": judge_derived,
        "external_readback_result": external_result,
        "external_rows": live,
        "control_pairs_pinned": [list(c) for c in CONTROL_PAIRS],
        "derived_result": ("SELFTEST_ALL_GREEN" if judge_derived == "JUDGE_ALL_GREEN" and external_result == EXTERNAL_OK
                             else "JUDGE:" + judge_derived + " | EXTERNAL:" + external_result),
        "note": "Verdicts are read back from the GitHub contents API per (path, ref); nothing here is a "
                "literal PASS.  A cell that cannot show both sides is CITED_BLOB_MISSING, never TRANSFERABLE.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    print("gen A =", GEN_A[:9], " gen B =", GEN_B[:9])
    for k, v in results.items():
        print("  %-46s %s" % (k, "ok" if v else "FAIL"))
    print("judge_derived_result =", judge_derived)
    print("external_readback_result =", external_result)
    for row in live:
        print("  %-58s %-9s obs_a=%s" % (row["path"][-58:], row["state"], (row["observed_a"] or "-")[:12]))
    print("derived_result =", ("SELFTEST_ALL_GREEN" if judge_derived == "JUDGE_ALL_GREEN" and external_result == EXTERNAL_OK else "SEE_TWO_FIELDS"))
    print("wrote", OUT)
    return 0 if all(results.values()) else 4


CLAIM_WITH_NO_CELLS = "CLAIM_WITH_NO_CELLS"
# ORD-0283/A9: spelling the claim key differently must not opt a receipt out of judgement.
CLAIM_KEY_RE = re.compile(r"cross[\W_]*gen\w*[\W_]*claim", re.IGNORECASE)


def find_claim(doc):
    """(claimed_value, key_used) - ANY shape-matching key holding a truthy value counts as a claim."""
    for k, v in (doc or {}).items():
        if CLAIM_KEY_RE.search(str(k)) and v not in (None, "", False, [], {}, 0):
            return v, str(k)
    return None, None


def derive_result(doc, out):
    """The one whole-receipt judgement, split out of check_receipt so the self-test can bite it.

    ORD-0283/A7 (real bite): in r4 `cells=[]` aggregated into `ALL_CELLS_TRANSFERABLE` with rc=0, because
    `bad` is empty when there is nothing to be bad - zero observations proving a universal claim.  A claim
    with nothing behind it is now its own RED state (rc=4).
    ORD-0283/A8: a receipt that makes no claim still exits 0, but the MISSING tally is handed back so the
    caller can print it - "nothing claimed" must not read as "nothing was wrong".
    """
    claimed, key = find_claim(doc)
    tally = {}
    for o in out:
        tally[o["verdict"]] = tally.get(o["verdict"], 0) + 1
    bad = [o["cell"] for o in out if o["verdict"] != TRANSFERABLE]
    if claimed and not out:
        return CLAIM_WITH_NO_CELLS, 4, True, key, tally
    if claimed:
        return ("ALL_CELLS_TRANSFERABLE" if not bad else "RED_CELLS:" + ",".join(bad)), (0 if not bad else 4), True, key, tally
    return "NO_CROSS_GENERATION_CLAIM_MADE", 0, False, key, tally


def check_receipt(path, gen_a, gen_b):
    """Run the rule over a real receipt that carries `cells` with `cited_files`."""
    raw = io.open(path, encoding="utf-8").read()
    doc = json.loads(raw)
    cells = doc.get("cells") or []
    out = []
    for c in cells:
        name = c.get("cell") or c.get("name") or "?"
        cited = c.get("cited_files") or []
        verdict, _ = judge_cell(name, gen_a, gen_b, cited, claim_kind=c.get("claim_kind"))
        out.append({"cell": name, "verdict": verdict["verdict"], "cited_files": cited,
                    "claim_kind": c.get("claim_kind"), "why": verdict.get("why"),
                    "cited_blob_at_each_generation": verdict.get("cited", {}),
                    "why_missing": verdict.get("errors", {}),
                    "differ": verdict.get("differ", []), "missing": verdict.get("missing", [])})
    derived, rc, claimed_bool, claim_key, tally = derive_result(doc, out)
    receipt = {"schema": "CNX_GENERATION_TRANSFER_RECEIPT_V1", "rule": "GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1",
               "receipt_under_check": path, "gen_a": gen_a, "gen_b": gen_b,
               "cells_total": len(out), "tally": tally, "cells": out,
               "cells_missing": tally.get(MISSING, 0),
               "claim_made_by_delivery": claimed_bool, "claim_key_used": claim_key,
               "derived_result": derived}
    if not claimed_bool and tally.get(MISSING):
        receipt["note_no_claim_but_missing"] = (
            "no cross-generation claim was made so the exit is 0, but %d cell(s) could not be read on "
            "both sides - 'nothing claimed' is NOT 'nothing was wrong'" % tally.get(MISSING))
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return rc


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args or args[0] == "--selftest":
        return selftest()
    if args[0] == "--check" and len(args) >= 4:
        return check_receipt(args[1], args[2], args[3])
    print(__doc__)
    print("usage: generation_transfer_check.py [--selftest | --check <receipt.json> <genA_sha> <genB_sha>]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
