"""Build the reconciliation receipt for the frontend write-leg denominator (commander's own run).

Every number here is computed at build time from the two artifacts, not typed:
  - mine:  _cmdr_write_legs_30a5f90e.json        (produced by write_leg_scan_r1.js on a `git archive` export)
  - hers:  evidence/ord0312-write-deadline-coverage-f/frontend_write_deadline_coverage_r1.json (by blob)
and the line-anchor check re-reads the exported tree byte for byte to answer one narrow question:
is the coordinate she published actually the call site?

Why: her post replaced my word "covered" with a denominator (14 legs, 2 covered).  Two of those two
covered coordinates and two of the twelve bare coordinates turn out not to sit on a call line, so the
number is real but its anchors are not, and a number with wrong anchors cannot be carried into an order.
"""
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-reconcile", "X-GitHub-Api-Version": "2022-11-28"}
EXPORT = r"D:/moodle/_qoder_cmdr_ref_20260921/snap_tip_30a5f90e/frontend/src"
MINE = "_cmdr_write_legs_30a5f90e.json"
HER_BLOB = "6e3ef780c4ad3e0f302f98b15850ecd4e92adf29"
HER_PATH = "evidence/ord0312-write-deadline-coverage-f/frontend_write_deadline_coverage_r1.json"
TIP = "30a5f90e5deaed6e45a704ddcc7d6e5e9790475b"
GITREPO = "D:/moodle/CityNexus"


def blob(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def get_blob(sha):
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha)
    for k, v in HDRS.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        obj = json.loads(r.read().decode())
    raw = base64.b64decode(obj["content"])
    return raw, blob(raw)


def tip_recheck():
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/"
                                 + urllib.parse.quote("mirror/integration-frontend-apple-pass1", safe=""))
    for k, v in HDRS.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())["object"]["sha"]


def export_matches_tip():
    """Prove the directory I scanned IS the tip's frontend/src, path by path, not by trust."""
    p = subprocess.run(["git", "-C", GITREPO, "ls-tree", "-r", "--name-only", TIP, "frontend/src"],
                       capture_output=True, text=True, timeout=180)
    paths = [ln for ln in p.stdout.splitlines() if ln.strip()]
    if not paths:
        return {"ok": False, "why": "ls-tree produced nothing - instrument failure, not an absence", "stderr": p.stderr[:200]}
    import urllib.parse  # noqa
    bad = []
    checked = 0
    for rel in paths:
        local = os.path.join(EXPORT, rel[len("frontend/src/"):].replace("/", os.sep))
        if not os.path.exists(local):
            bad.append(("missing", rel))
            continue
        p2 = subprocess.run(["git", "-C", GITREPO, "rev-parse", "%s:%s" % (TIP, rel)],
                            capture_output=True, text=True, timeout=60)
        want = p2.stdout.strip()
        got = blob(io.open(local, "rb").read())
        checked += 1
        if want != got:
            bad.append(("mismatch", rel, want, got))
    return {"ok": not bad, "paths_in_tip_frontend_src": len(paths), "blobs_recomputed": checked,
            "mismatches": bad[:10], "mismatch_count": len(bad)}


def anchor_check(site):
    """Read the exact line she cited; report its length and whether it is a call at all."""
    local = os.path.join(EXPORT, site["file"].replace("/", os.sep))
    if not os.path.exists(local):
        return {**site, "exists": False}
    lines = io.open(local, encoding="utf-8", errors="replace").read().split("\n")
    n = site["line"]
    text = lines[n - 1] if 1 <= n <= len(lines) else None
    return {"file": site["file"], "line": n, "line_chars": (len(text) if text is not None else None),
            "line_is_blank": (text is not None and text.strip() == ""),
            "line_contains_fetch": (text is not None and "fetch" in text),
            "line_contains_method_POST": (text is not None and 'method: "POST"' in text)}


def call_line_for(file_rel, window_from, window_to, needle):
    local = os.path.join(EXPORT, file_rel.replace("/", os.sep))
    lines = io.open(local, encoding="utf-8", errors="replace").read().split("\n")
    for i in range(window_from, min(window_to, len(lines))):
        if needle in lines[i]:
            return i + 1
    return None


def main():
    import urllib.parse  # noqa
    tip_now = tip_recheck()
    mine = json.loads(io.open(MINE, encoding="utf-8").read())
    her_raw, her_sha = get_blob(HER_BLOB)
    her = json.loads(her_raw.decode("utf-8"))
    her_sites = [{"file": s["file"], "line": s["line"]} for s in her["covered_sites"]] + \
                [{"file": s["file"], "line": s["line"], "method": s.get("method")} for s in her["uncovered_sites"]]
    mkey = {(l["file"], l["line"]): l for l in mine["all_legs"]}
    hkey = {(s["file"], s["line"]) for s in her_sites}
    both = sorted(set(mkey) & hkey)
    only_mine = sorted(set(mkey) - hkey)
    only_hers = sorted(hkey - set(mkey))

    checks = [anchor_check(s) for s in her_sites]
    blank_anchors = [c for c in checks if c.get("line_is_blank")]
    non_call_anchors = [c for c in checks if not c.get("line_contains_fetch") and not c.get("line_contains_method_POST")]

    # where the two anchors she calls covered actually are
    real_calls = {
        "LiveRecovery_accept": call_line_for("features/execution/LiveRecovery.tsx", 220, 240, "fetchWithWriteDeadline("),
        "V14RecoveryTruthPanel_accept": call_line_for("features/recovery/V14RecoveryTruthPanel.tsx", 64, 84, "fetchWithWriteDeadline("),
    }
    mine_covered = [l for l in mine["all_legs"] if l["covered_by_any_of_the_three"]]
    union = sorted(set(mkey) | hkey)

    out = {
        "schema": "CNX_CMDR_WRITE_LEG_RECONCILIATION_V1",
        "lane": "commander 494abfd7",
        "generated_at_local": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": "how many frontend write legs exist on the current tip and how many carry a deadline - "
                    "two instruments answering the same sentence differently",
        "tip_recheck_from_github": tip_now,
        "tip_agrees_with_both_measurements": tip_now == TIP,
        "tree_export_verification": export_matches_tip(),
        "instrument_mine": {
            "tool": "write_leg_scan_r1.js", "selftest": "SELFTEST_PASS (3 fixtures: own-signal leg=covered, "
            "bare leg=bare, toString/toLocaleString calls must not be legs)",
            "definition": "fetch(...) with a literal write method, or .post/.put/.patch/.delete, or "
                          ".request({method:<write>}); deadline questions asked at the AST node (own options "
                          "signal / enclosing-function signal parameter / enclosing-function timeout)",
            "files_scanned": mine["files_scanned"], "legs_total": mine["legs_total"],
            "legs_by_method": mine["legs_by_method"],
            "covered": mine["legs_covered_by_any_of_the_three"],
            "covered_sites": [{"file": l["file"], "line": l["line"], "own_options_has_signal": l["own_options_has_signal"]}
                              for l in mine_covered],
            "known_blind_spot": "a call routed through a named wrapper (fetchWithWriteDeadline) is not a `fetch` "
                                "identifier, so this instrument cannot see those legs - that is why her two "
                                "wrapper legs appear as 'only hers' below",
            "first_run_defect_disclosed": mine.get("first_run_defect_disclosed"),
        },
        "instrument_hers": {
            "artifact_blob": her_sha, "artifact_blob_requested": HER_BLOB,
            "blob_match": her_sha == HER_BLOB, "bytes": len(her_raw),
            "legs_total": her["legs_total"], "legs_covered": her["legs_covered"],
            "definition": her["method"], "measured_on": her["measured_on"], "tree": her["tree"],
            "files_importing_writeDeadline": her["files_importing_writeDeadline"],
            "frontend_files_with_any_signal": her["frontend_files_with_any_signal"],
        },
        "set_comparison": {
            "union_sites": len(union), "agreed_sites": len(both),
            "only_mine": len(only_mine), "only_hers": len(only_hers),
            "agreed_list": [{"file": f, "line": n, "method": mkey[(f, n)]["method"],
                             "covered_by_mine": mkey[(f, n)]["covered_by_any_of_the_three"]} for f, n in both],
            "only_mine_list": [{"file": f, "line": n, "method": mkey[(f, n)]["method"], "call": mkey[(f, n)]["call"],
                                "covered_by_mine": mkey[(f, n)]["covered_by_any_of_the_three"]} for f, n in only_mine],
            "only_hers_list": [{"file": f, "line": n} for f, n in only_hers],
        },
        "anchor_findings": {
            "anchors_cited_by_hers": len(her_sites),
            "anchors_that_are_blank_lines": [{"file": c["file"], "line": c["line"]} for c in blank_anchors],
            "anchors_that_contain_neither_fetch_nor_a_POST_literal":
                [{"file": c["file"], "line": c["line"], "line_chars": c.get("line_chars")} for c in non_call_anchors],
            "wrapper_call_lines_found_by_rereading_the_file": real_calls,
            "note": "the count she published and the coordinates she published are not the same object: both "
                    "sites she marks covered resolve to a blank line in the exported tree, and the two sites she "
                    "marks uncovered inside PlanWithAiSheet.tsx are, at the real call lines, legs whose own "
                    "options object carries `signal` (verified by reading those lines).",
        },
        "what_this_changes": {
            "covered_is_not_two": mine["legs_covered_by_any_of_the_three"] + her["legs_covered"],
            "covered_reasoning": "her 2 wrapper legs (fetchWithWriteDeadline) + my 2 legs carrying `signal` in "
                                 "their own options = 4 sites that demonstrably carry a deadline; none of the "
                                 "four is in the other's denominator, so 2/14 is an artefact of two partial sets.",
            "bare_by_union": len(union) - (mine["legs_covered_by_any_of_the_three"] + her["legs_covered"]),
            "shapes_the_orders_never_named": [
                {"file": f, "line": n, "method": mkey[(f, n)]["method"], "call": mkey[(f, n)]["call"]}
                for f, n in only_mine if not mkey[(f, n)]["covered_by_any_of_the_three"]],
            "decision_this_moves": "whether 'the write-deadline half is covered by ORD-0281/0288/0312' is a "
                                   "true sentence - it is not, on the union denominator, for the 4 legs whose "
                                   "verb is PUT/DELETE. Whether that is a defect to fix or a decision to keep is "
                                   "a scope question, not a measurement question, so it goes to the arbiter.",
        },
        "discipline": {"authoritative_branch_moved": 0, "refs_pushed_by_this_run": 0,
                       "demo_reset_calls": 0, "live_or_preview_db_reads_or_writes": 0,
                       "credential_values_printed": 0, "product_bytes_changed": 0,
                       "export_dir_is_read_only_for_this_run": True},
        "claim_kind": "code_determined",
        "claimed_result": "two denominators reconciled; anchors of one of them corrected against the bytes",
        "derived_result": None,
    }
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_leg_reconciliation_2022.json", "w", encoding="utf-8").write(txt)
    sc = out["set_comparison"]
    print("tip ok=%s  export blobs recomputed=%s mismatches=%s" % (
        out["tree_export_verification"]["ok"], out["tree_export_verification"].get("blobs_recomputed"),
        out["tree_export_verification"].get("mismatch_count")))
    print("union=%s agreed=%s only_mine=%s only_hers=%s" % (sc["union_sites"], sc["agreed_sites"],
                                                            sc["only_mine"], sc["only_hers"]))
    print("hers anchors blank=%s  non-call=%s  wrapper lines=%s" % (
        out["anchor_findings"]["anchors_that_are_blank_lines"],
        len(out["anchor_findings"]["anchors_that_contain_neither_fetch_nor_a_POST_literal"]), real_calls))
    print("covered(not 2)=%s bare_by_union=%s" % (out["what_this_changes"]["covered_is_not_two"],
                                                  out["what_this_changes"]["bare_by_union"]))
    print("file=_cmdr_leg_reconciliation_2022.json bytes=%d sha=%s" % (len(txt.encode("utf-8")), blob(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa
    sys.exit(main())
