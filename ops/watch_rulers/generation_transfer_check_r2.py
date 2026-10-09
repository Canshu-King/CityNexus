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
                   "generation_transfer_check_selftest.json")
# Why a side could not be read, kept per (ref|path) so a MISSING verdict in the receipt is explainable
# ("HTTP 404" = the file is not in that generation; "IncompleteRead" = the link was flaky).
LAST_ERROR = {}

TRANSFERABLE = "TRANSFERABLE"
NOT_TRANSFERABLE = "NOT_TRANSFERABLE_GENERATION"
MISSING = "CITED_BLOB_MISSING"


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


def judge_cell(cell, gen_a, gen_b, cited_files, reader=None):
    """One cell, one verdict, derived only from the two-sided blob readings it can name.

    `reader` is injectable so the self-test can hand the SAME judge tampered pairs (a near-miss hex, a
    prefix-equal truncation).  Without that, "the judge compares whole 40-hex strings" would be a claim in
    a comment rather than something that can fail - which is the defect class this whole night is about.
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
    missing = [p for p, r in rows.items() if not r[ka] or not r[kb]]
    differ = [p for p, r in rows.items() if r[ka] and r[kb] and r[ka] != r[kb]]
    if missing:
        verdict = MISSING
    elif differ:
        verdict = NOT_TRANSFERABLE
    else:
        verdict = TRANSFERABLE
    return {"cell": cell, "verdict": verdict,
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


def selftest():
    results = {}
    ok_same, rows_same = judge_cell("pos_transferable", GEN_A, GEN_B, [SAME_FILE])
    results["positive_identical_file_is_TRANSFERABLE"] = ok_same["verdict"] == TRANSFERABLE
    ok_changed, rows_changed = judge_cell("neg_changed", GEN_A, GEN_B, [CHANGED_FILE])
    results["negative_changed_file_is_NOT_TRANSFERABLE"] = ok_changed["verdict"] == NOT_TRANSFERABLE
    ok_missing, rows_missing = judge_cell("neg_only_one_generation", GEN_A, GEN_B, [ONLY_IN_B_FILE])
    results["missing_side_is_CITED_BLOB_MISSING_not_pass"] = ok_missing["verdict"] == MISSING
    ok_mixed, rows_mixed = judge_cell("mixed_pair", GEN_A, GEN_B, [SAME_FILE, CHANGED_FILE])
    results["one_changed_file_poisons_the_whole_cell"] = ok_mixed["verdict"] == NOT_TRANSFERABLE
    ok_empty, _ = judge_cell("no_citations", GEN_A, GEN_B, [])
    results["cell_citing_nothing_fails_closed"] = ok_empty["verdict"] == MISSING
    # ---- comparison-laxness killers: the SAME judge, fed tampered pairs through the injected reader.
    real = rows_same[SAME_FILE]["at_" + GEN_A[:9]]
    near = real[:-1] + ("0" if real[-1] != "0" else "1")          # one hex different, same length
    prefix = real[:20]                                            # prefix-equal, half the length
    def reader_near(g, p):
        return real if g == GEN_A else near
    def reader_prefix(g, p):
        return real if g == GEN_A else prefix
    def reader_equal(g, p):
        return real
    v_near, _ = judge_cell("killer_near_miss", GEN_A, GEN_B, [SAME_FILE], reader=reader_near)
    v_prefix, _ = judge_cell("killer_prefix_only", GEN_A, GEN_B, [SAME_FILE], reader=reader_prefix)
    v_equal, _ = judge_cell("control_identical_pair", GEN_A, GEN_B, [SAME_FILE], reader=reader_equal)
    results["K1_one_hex_different_is_NOT_TRANSFERABLE"] = v_near["verdict"] == NOT_TRANSFERABLE
    results["K2_prefix_equal_but_shorter_is_NOT_TRANSFERABLE"] = v_prefix["verdict"] == NOT_TRANSFERABLE
    results["K3_identical_pair_control_stays_TRANSFERABLE"] = v_equal["verdict"] == TRANSFERABLE
    results["K4_missing_side_reader_is_NOT_transferable"] = (
        judge_cell("killer_one_side_none", GEN_A, GEN_B, [SAME_FILE],
                   reader=lambda g, p: real if g == GEN_A else None)[0]["verdict"] == MISSING)

    def reader_throws(g, p):
        raise RuntimeError("simulated IncompleteRead on a truncated response")
    v_throw, _ = judge_cell("killer_transport_throw", GEN_A, GEN_B, [SAME_FILE], reader=reader_throws)
    results["K5_transport_exception_is_CITED_BLOB_MISSING_not_a_crash_not_a_pass"] = v_throw["verdict"] == MISSING
    derived = "SELFTEST_ALL_GREEN" if all(results.values()) else "RED_CELLS:" + ",".join(
        k for k, v in results.items() if not v)
    receipt = {
        "schema": "CNX_GENERATION_TRANSFER_SELFTEST_V1",
        "rule": "GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1",
        "ruling": "arbiter Q24 = (1), 2026-09-25T04:0x+08, in the designated window",
        "gen_a": GEN_A, "gen_b": GEN_B,
        "cells_under_test": {
            "positive_identical_file": ok_same,
            "negative_changed_file": ok_changed,
            "missing_side": ok_missing,
            "mixed_pair": ok_mixed,
            "no_citations": ok_empty,
            "killer_near_miss": v_near,
            "killer_prefix_only": v_prefix,
            "control_identical_pair": v_equal,
            "killer_transport_throw": v_throw,
        },
        "checks": results,
        "derived_result": derived,
        "note": "Verdicts are read back from the GitHub contents API per (path, ref); nothing here is a "
                "literal PASS.  A cell that cannot show both sides is CITED_BLOB_MISSING, never TRANSFERABLE.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    print("gen A =", GEN_A[:9], " gen B =", GEN_B[:9])
    for k, v in results.items():
        print("  %-46s %s" % (k, "ok" if v else "FAIL"))
    print("derived_result =", derived)
    print("wrote", OUT)
    return 0 if all(results.values()) else 4


def check_receipt(path, gen_a, gen_b):
    """Run the rule over a real receipt that carries `cells` with `cited_files`."""
    raw = io.open(path, encoding="utf-8").read()
    doc = json.loads(raw)
    cells = doc.get("cells") or []
    out = []
    for c in cells:
        name = c.get("cell") or c.get("name") or "?"
        cited = c.get("cited_files") or []
        verdict, _ = judge_cell(name, gen_a, gen_b, cited)
        out.append({"cell": name, "verdict": verdict["verdict"], "cited_files": cited,
                    "cited_blob_at_each_generation": verdict.get("cited", {}),
                    "why_missing": verdict.get("errors", {}),
                    "differ": verdict.get("differ", []), "missing": verdict.get("missing", [])})
    tally = {}
    for o in out:
        tally[o["verdict"]] = tally.get(o["verdict"], 0) + 1
    claimed = doc.get("cross_generation_claim")
    bad = [o["cell"] for o in out if o["verdict"] != TRANSFERABLE]
    derived = ("ALL_CELLS_TRANSFERABLE" if not bad else "RED_CELLS:" + ",".join(bad)) if claimed else \
        "NO_CROSS_GENERATION_CLAIM_MADE"
    receipt = {"schema": "CNX_GENERATION_TRANSFER_RECEIPT_V1", "rule": "GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1",
               "receipt_under_check": path, "gen_a": gen_a, "gen_b": gen_b,
               "cells_total": len(out), "tally": tally, "cells": out,
               "claim_made_by_delivery": bool(claimed), "derived_result": derived}
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0 if derived == "ALL_CELLS_TRANSFERABLE" or derived == "NO_CROSS_GENERATION_CLAIM_MADE" else 4


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
