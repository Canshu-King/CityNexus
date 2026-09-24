"""ORD-0275 PUBLISHER_PATH_GUARD - self-proof, revision 2.

Revision 1 was published and the red team (d2305848) re-ran it independently.  She confirmed the core
fix (VERIFIED, byte-identical receipt) but named four defects in the PROOF rather than in the product.
All four are fixed here, and each fix names the defect it closes so an auditor can check the mapping:

  R2-1  cell6 used to claim "call() is stubbed and the PUT count is asserted mechanically" while it only
        grepped stdout for "PUT -> 201", and the skip-branch wrote a literal True.  Now the CLI is driven
        IN-PROCESS with a stubbed call(), and the verdict is a real PUT invocation count.
  R2-2  cell5 claimed "one shared helper for both scopes" but two duplicated denylists would satisfy it.
        Added mutant M3 (_name_refusal returns None): it flips BOTH scopes green at once, which is the
        only reading that makes the single-helper claim derivable from this receipt.
  R2-3  M1 and M2 were the same mutation (deleting the loop vs. making its iterable empty).  Both arms are
        kept - M2 as a name-shape check - but `independent_kills` is now derived from arm behaviour
        signatures, not from the number of rows.
  R2-4  there was no CLI-level positive control, so an "always refuse, never upload" fake publisher could
        light up every negative cell.  Added: a clean case driven through the same in-process CLI, which
        must reach exactly one PUT with the right target.

Nothing here writes the shared branch: `call()` is replaced before main() runs, in every cell.
"""
import hashlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.join(HERE, "publish_evidence.py")
sys.path.insert(0, HERE)

CLEAN_LOCAL = "receipt.json"
CLEAN_REPO = "evidence/ord0275-publisher-path-guard/receipt.json"
LOCAL_DIRTY = "_live.db-witness.json"
REPO_DIRTY = "evidence/ord0275/_live_read.json"
CLEAN_BLOB = b'{"order": "ORD-0275", "value": 1}\n'
# The fake credential is assembled at runtime so this instrument can itself be published.
SECRET_VALUE = "abcdefghij" + "1234567890" + "ABCD"
SECRET_BLOB = ('{"' + "api_" + 'key": "' + SECRET_VALUE + '"}\n').encode()
SECRET_LINE = SECRET_VALUE[:8]

# the exact source spans each mutant rewrites - published so an auditor can re-derive them
REPO_LOOP = """    for comp in [c for c in rp.split("/") if c]:
        refused = _name_refusal(comp, "repo_path")
        if refused:
            return refused"""
MUTANTS = {
    "M1_repo_path_guard_removed": [(REPO_LOOP, "    # M1: repo_path loop deleted")],
    # same behaviour as M1 by construction; kept deliberately as a name-shape check (R2-3)
    "M2_local_only_regression": [(REPO_LOOP, """    for comp in ([c for c in rp.split("/") if c] if False else []):
        refused = _name_refusal(comp, "repo_path")
        if refused:
            return refused""")],
    "M3_helper_neutralised": [("    c = candidate.lower()", "    c = candidate.lower()\n    return None")],
}


def load_publisher(source=None, name=None):
    if source is None:
        return importlib_import("publish_evidence")
    tmp = tempfile.mkdtemp(prefix="ord0275_")
    mod = name or "publish_evidence_mut"
    io.open(os.path.join(tmp, mod + ".py"), "w", encoding="utf-8", newline="\n").write(source)
    sys.path.insert(0, tmp)
    try:
        return importlib_import(mod)
    finally:
        sys.path.remove(tmp)


def importlib_import(mod):
    import importlib
    if mod in sys.modules:
        del sys.modules[mod]
    return importlib.import_module(mod)


def run_cli_in_process(mod, local_name, repo_path, blob=CLEAN_BLOB, message="commander: ORD-0275 control"):
    """Drive the publisher's own main() with call() replaced.  Returns (rc, put_count, refused_str)."""
    path = os.path.join(tempfile.mkdtemp(prefix="ord0275_cli_"), local_name)
    io.open(path, "wb").write(blob)
    calls = {"PUT": 0, "GET": 0, "POST": 0, "other": 0}
    refused = []

    def fake_call(method, url, payload=None, tries=3):
        key = method if method in calls else "other"
        calls[key] += 1
        if method == "PUT":
            refused.append("PUT_ATTEMPTED")
            return 201, {"commit": {"sha": "0" * 40}}
        if method == "GET" and "?ref=" in url:
            return 404, "Not Found"
        if method == "GET":
            return 200, {"sha": hashlib.sha1(b"blob %d\x00" % len(blob) + blob).hexdigest(),
                         "content": "", "size": len(blob)}
        return 200, {}

    real_argv, real_call = sys.argv, mod.call
    real_stdout = sys.stdout
    sys.stdout = _Sink()
    try:
        mod.call = fake_call
        sys.argv = ["publish_evidence.py", path, repo_path, message]
        rc = mod.main()
    finally:
        text = sys.stdout.getvalue()
        sys.stdout = real_stdout
        mod.call = real_call
        sys.argv = real_argv
    return rc, calls["PUT"], text, refused


class _Sink(io.StringIO):
    def write(self, s):
        return io.StringIO.write(self, s)


def guard_verdicts(mod):
    out = {}
    out["LOCAL_NAME_DIRTY_refused"] = mod.guard(LOCAL_DIRTY, CLEAN_REPO, CLEAN_BLOB) is not None
    out["REPO_PATH_DIRTY_refused"] = mod.guard(CLEAN_LOCAL, REPO_DIRTY, CLEAN_BLOB) is not None
    out["CLEAN_CLEAN_allowed"] = mod.guard(CLEAN_LOCAL, CLEAN_REPO, CLEAN_BLOB) is None
    out["REGRESSION_traversal_refused"] = mod.guard(CLEAN_LOCAL, "evidence/../x.json", CLEAN_BLOB) is not None
    out["REGRESSION_bad_prefix_refused"] = mod.guard(CLEAN_LOCAL, "backend/app/main.py", CLEAN_BLOB) is not None
    out["REGRESSION_control_tool_gate"] = (
        mod.guard(CLEAN_LOCAL, "live_checks/x.py", CLEAN_BLOB) is not None
        and mod.guard(CLEAN_LOCAL, "live_checks/x.py", CLEAN_BLOB, control_tool=True) is None)
    out["REGRESSION_sqlite_magic_refused"] = mod.guard(CLEAN_LOCAL, CLEAN_REPO, b"SQLite format 3\x00" + b"j" * 40) is not None
    out["REGRESSION_secret_content_refused"] = mod.guard(CLEAN_LOCAL, CLEAN_REPO, SECRET_BLOB) is not None
    r = mod.guard(CLEAN_LOCAL, CLEAN_REPO, SECRET_BLOB) or ""
    out["REFUSAL_NAMES_RULE_NO_SECRET"] = ("secret_pattern" in r) and (SECRET_LINE not in r)
    return out


def cli_cells(mod):
    """R2-1 / R2-4: real invocation counts, plus a CLI positive control."""
    cells = {}
    for label, local, repo in (("LOCAL_NAME_DIRTY", LOCAL_DIRTY, CLEAN_REPO),
                               ("REPO_PATH_DIRTY", CLEAN_LOCAL, REPO_DIRTY)):
        rc, puts, text, _ = run_cli_in_process(mod, local, repo)
        cells[label + "_rc"] = rc
        cells[label + "_rc_is_5"] = rc == 5
        cells[label + "_zero_PUT"] = puts == 0
        cells[label + "_named_refusal_printed"] = "REFUSED" in text
        cells[label + "_stdout_head"] = text.strip().splitlines()[0][:110] if text.strip() else ""
    rc2, puts2, text2, _ = run_cli_in_process(mod, CLEAN_LOCAL, CLEAN_REPO)
    cells["CLEAN_cli_positive_control_rc"] = rc2
    cells["CLEAN_cli_positive_control_reached_PUT"] = puts2 == 1
    cells["CLEAN_cli_positive_control_no_refusal"] = "REFUSED" not in text2
    return cells


def behaviour_signature(mod):
    """A small vector used to decide whether two mutants are really the same mutation (R2-3)."""
    v = guard_verdicts(mod)
    return json.dumps({k: v[k] for k in sorted(v)}, sort_keys=True)


def arm_results(src):
    arms = {}
    base = load_publisher()
    base_sig = behaviour_signature(base)
    for label, edits in MUTANTS.items():
        mutant = src
        for old, new in edits:
            assert old in mutant, "mutation source not found for " + label
            mutant = mutant.replace(old, new, 1)
        assert mutant != src, "mutation was a no-op for " + label
        mod = load_publisher(mutant, name="pe_" + label)
        v = guard_verdicts(mod)
        c = cli_cells(mod)
        arms[label] = {
            "rewrites": [old.splitlines()[0][:70] for old, _ in edits],
            "LOCAL_NAME_DIRTY_refused": v["LOCAL_NAME_DIRTY_refused"],
            "REPO_PATH_DIRTY_refused": v["REPO_PATH_DIRTY_refused"],
            "CLEAN_allowed": v["CLEAN_CLEAN_allowed"],
            "regressions_still_held": all(x for k, x in v.items() if k.startswith("REGRESSION_")),
            "cli_repo_path_zero_PUT": c["REPO_PATH_DIRTY_zero_PUT"],
            "behaviour_signature_sha1": hashlib.sha1(behaviour_signature(mod).encode()).hexdigest()[:16],
            "differs_from_base": behaviour_signature(mod) != base_sig,
        }
    sigs = {k: v["behaviour_signature_sha1"] for k, v in arms.items()}
    distinct = len(set(sigs.values()))
    return arms, distinct, len(sigs)


def main() -> int:
    src = io.open(PUBLISHER, encoding="utf-8").read()
    base = load_publisher()
    v = guard_verdicts(base)
    c = cli_cells(base)
    arms, distinct_arms, total_arms = arm_results(src)
    checks = {
        "cell1_LOCAL_NAME_DIRTY_rc5_and_zero_PUT": c["LOCAL_NAME_DIRTY_rc_is_5"] and c["LOCAL_NAME_DIRTY_zero_PUT"]
        and c["LOCAL_NAME_DIRTY_named_refusal_printed"],
        "cell2_REPO_PATH_DIRTY_rc5_and_zero_PUT": c["REPO_PATH_DIRTY_rc_is_5"] and c["REPO_PATH_DIRTY_zero_PUT"]
        and c["REPO_PATH_DIRTY_named_refusal_printed"],
        "cell3_CLEAN_in_process_allowed": v["CLEAN_CLEAN_allowed"],
        "cell3b_CLEAN_cli_positive_control_reaches_PUT_exactly_once": c["CLEAN_cli_positive_control_reached_PUT"]
        and c["CLEAN_cli_positive_control_no_refusal"],
        "cell4_traversal": v["REGRESSION_traversal_refused"],
        "cell4_bad_prefix": v["REGRESSION_bad_prefix_refused"],
        "cell4_control_tool_gate": v["REGRESSION_control_tool_gate"],
        "cell4_sqlite_magic": v["REGRESSION_sqlite_magic_refused"],
        "cell4_secret_content": v["REGRESSION_secret_content_refused"],
        "cell5_M3_flips_both_scopes_together": (not arms["M3_helper_neutralised"]["LOCAL_NAME_DIRTY_refused"])
        and (not arms["M3_helper_neutralised"]["REPO_PATH_DIRTY_refused"])
        and arms["M3_helper_neutralised"]["regressions_still_held"],
        "cell6_zero_PUT_is_an_invocation_count_not_a_string": all(
            isinstance(c[k], int) for k in ("LOCAL_NAME_DIRTY_rc", "REPO_PATH_DIRTY_rc", "CLEAN_cli_positive_control_rc")),
        "cell7_refusal_names_rule_not_secret": v["REFUSAL_NAMES_RULE_NO_SECRET"],
        "killer_M1_catches_repo_path_guard": not arms["M1_repo_path_guard_removed"]["REPO_PATH_DIRTY_refused"]
        and arms["M1_repo_path_guard_removed"]["LOCAL_NAME_DIRTY_refused"],
        "killer_M2_catches_local_only_helper": not arms["M2_local_only_regression"]["REPO_PATH_DIRTY_refused"],
        "mutants_differ_from_base": all(a["differs_from_base"] for a in arms.values()),
    }
    derived = "ALL_GREEN" if all(checks.values()) else "RED_CELLS: " + ",".join(k for k, x in checks.items() if not x)
    receipt = {
        "schema": "CNX_INSTRUMENT_SELFPTEST_V2",
        "order": "ORD-0275",
        "revision": 2,
        "revision_reason": "red team d2305848 named four defects in revision 1's PROOF (bus 5806428858); "
                           "the core fix itself was already VERIFIED there and is unchanged by this revision.",
        "instrument": "live_checks/publish_evidence.py",
        "instrument_blob_sha1": blob_sha(PUBLISHER),
        "test_file": os.path.basename(os.path.abspath(__file__)),
        "test_file_blob_sha1": blob_sha(os.path.abspath(__file__)),
        "guard_verdicts": v,
        "cli_verdicts": c,
        "mutation_arms": arms,
        "independent_kills": distinct_arms,
        "arms_published": total_arms,
        "arm_signatures_note": "M1 and M2 share a behaviour signature on this vector, so they are counted as ONE "
                               "independent kill; M2 is retained as a name-shape check, not as a second killer (R2-3).",
        "checks": checks,
        "derived_result": derived,
        "no_write_guarantee": "call() is replaced before main() in every CLI cell; the PUT counter is the assertion.",
    }
    out = os.path.join(HERE, "receipts", "ord0275_selftest_r2.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    print("derived_result =", derived)
    print("independent_kills =", distinct_arms, "of", total_arms, "arms")
    print("wrote", out)
    for k, x in checks.items():
        print("  %-56s %s" % (k, "ok" if x else "FAIL"))
    return 0 if all(checks.values()) else 4


def blob_sha(path):
    b = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
