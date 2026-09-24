"""ORD-0275 PUBLISHER_PATH_GUARD - self-proof for the repo_path name guard.

Written by the commander (writer of this order per arbiter 5805656486). Verifier: red team.

Design rules this file must obey, taken from the acceptance contract:
  * cell 6: a counter-example must NEVER really write the shared branch - `call()` is stubbed and the
    PUT invocation count is asserted mechanically;
  * cell 3: a CLEAN/CLEAN positive control must still pass, otherwise the "safest" publisher is one
    that uploads nothing;
  * the two mutation arms (M1/M2) prove the new cell is not decoration: removing the repo_path check,
    or making the helper local-only, MUST turn REPO-PATH-DIRTY green (i.e. stop refusing).

Every verdict below is computed from a call result; nothing is written as a literal PASS.
"""
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.join(HERE, "publish_evidence.py")
sys.path.insert(0, HERE)

CLEAN_LOCAL = "receipt.json"
CLEAN_REPO = "evidence/ord0275-publisher-path-guard/receipt.json"
LOCAL_DIRTY_REPO_CLEAN = "_live.db-witness.json"          # forbidden fragment on the LOCAL side only
REPO_DIRTY_LOCAL_CLEAN = "evidence/ord0275/_live_read.json"  # forbidden fragment on the REMOTE side only
CLEAN_BLOB = b'{"order": "ORD-0275", "value": 1}\n'
# The fake credential is assembled at runtime on purpose: this instrument must itself be publishable,
# and a literal `api_key": "<20 chars>"` in this file would trip the very content scan it exercises.
SECRET_VALUE = "abcdefghij" + "1234567890" + "ABCD"
SECRET_BLOB = ('{"' + "api_" + 'key": "' + SECRET_VALUE + '"}\n').encode()
SECRET_LINE = SECRET_VALUE[:8]  # what must NEVER appear in a refusal message


def load_publisher(source=None):
    """Import publish_evidence, optionally from a mutated source string, without touching the real file."""
    if source is None:
        return importlib.import_module("publish_evidence")
    tmp = tempfile.mkdtemp(prefix="ord0275_")
    path = os.path.join(tmp, "publish_evidence_mut.py")
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    sys.path.insert(0, tmp)
    try:
        return importlib.import_module("publish_evidence_mut")
    finally:
        sys.path.remove(tmp)


def verdicts(mod):
    """Run the seven guard-shaped cells against one publisher module and derive every verdict."""
    out = {}
    out["LOCAL_NAME_DIRTY_refused"] = mod.guard(LOCAL_DIRTY_REPO_CLEAN, CLEAN_REPO, CLEAN_BLOB) is not None
    out["REPO_PATH_DIRTY_refused"] = mod.guard(CLEAN_LOCAL, REPO_DIRTY_LOCAL_CLEAN, CLEAN_BLOB) is not None
    out["CLEAN_CLEAN_allowed"] = mod.guard(CLEAN_LOCAL, CLEAN_REPO, CLEAN_BLOB) is None
    # cell 4: the pre-existing boundaries must not regress
    out["REGRESSION_traversal_refused"] = mod.guard(CLEAN_LOCAL, "evidence/../x.json", CLEAN_BLOB) is not None
    out["REGRESSION_bad_prefix_refused"] = mod.guard(CLEAN_LOCAL, "backend/app/main.py", CLEAN_BLOB) is not None
    out["REGRESSION_control_tool_gate"] = (
        mod.guard(CLEAN_LOCAL, "live_checks/x.py", CLEAN_BLOB) is not None
        and mod.guard(CLEAN_LOCAL, "live_checks/x.py", CLEAN_BLOB, control_tool=True) is None)
    out["REGRESSION_sqlite_magic_refused"] = mod.guard(CLEAN_LOCAL, CLEAN_REPO, b"SQLite format 3\x00" + b"j" * 40) is not None
    out["REGRESSION_secret_content_refused"] = mod.guard(CLEAN_LOCAL, CLEAN_REPO, SECRET_BLOB) is not None
    # the refusal must name a rule and must not echo a secret value
    r = mod.guard(CLEAN_LOCAL, CLEAN_REPO, SECRET_BLOB) or ""
    out["REFUSAL_NAMES_RULE_NO_SECRET"] = ("secret_pattern" in r) and (SECRET_LINE not in r)
    return out


def cli_refusal_cells():
    """Cell 1/2 at the CLI level: exit code 5, a named refusal, and zero PUT invocations.

    Preflight first: if the in-process guard does NOT refuse a case, we must not hand that path to the
    real CLI, because a leaking guard would then really PUT probe junk onto the shared branch - the exact
    accident HARNESS reported.  A preflight failure is recorded and the CLI is skipped for that case.
    """
    res = {}
    pre = load_publisher()
    for name, local, repo in (("LOCAL_NAME_DIRTY", LOCAL_DIRTY_REPO_CLEAN, CLEAN_REPO),
                              ("REPO_PATH_DIRTY", CLEAN_LOCAL, REPO_DIRTY_LOCAL_CLEAN)):
        would_refuse = pre.guard(local, repo, CLEAN_BLOB)
        if would_refuse is None:
            res[name + "_preflight"] = "GUARD_DID_NOT_REFUSE - CLI skipped to avoid writing the shared branch"
            res[name + "_rc"] = None
            res[name + "_rc_is_5"] = False
            res[name + "_printed_refusal"] = False
            res[name + "_no_upload_claim"] = True
            res[name + "_stdout_head"] = ""
            continue
        res[name + "_preflight"] = "refused in-process: " + str(would_refuse)[:80]
        path = os.path.join(tempfile.mkdtemp(prefix="ord0275_cli_"), local)
        io.open(path, "w", encoding="utf-8", newline="\n").write(CLEAN_BLOB.decode())
        p = subprocess.run([sys.executable, PUBLISHER, path, repo, "commander: ORD-0275 negative control"],
                           capture_output=True, text=True)
        out = p.stdout + p.stderr
        res[name + "_rc"] = p.returncode
        res[name + "_rc_is_5"] = p.returncode == 5
        res[name + "_printed_refusal"] = "REFUSED" in out
        res[name + "_no_upload_claim"] = "BYTE-LEVEL MATCH" not in out and "PUT -> 201" not in out
        res[name + "_stdout_head"] = out.strip().splitlines()[0][:120] if out.strip() else ""
    return res


def arm_results():
    """M1 / M2 mutants: each must make REPO_PATH_DIRTY stop refusing, and nothing else."""
    src = io.open(PUBLISHER, encoding="utf-8").read()
    m1 = src.replace("""    for comp in [c for c in rp.split("/") if c]:
        refused = _name_refusal(comp, "repo_path")
        if refused:
            return refused""", "    # M1_repo_path_guard_removed")
    m2 = src.replace("""    for comp in [c for c in rp.split("/") if c]:
        refused = _name_refusal(comp, "repo_path")""", """    for comp in ([c for c in rp.split("/") if c] if False else []):
        refused = _name_refusal(comp, "repo_path")""")
    arms = {}
    for label, mutant in (("M1_repo_path_guard_removed", m1), ("M2_local_only_regression", m2)):
        assert mutant != src, "mutation was a no-op for " + label
        v = verdicts(load_publisher(mutant))
        arms[label] = {
            "repo_path_dirty_now_allowed": not v["REPO_PATH_DIRTY_refused"],
            "local_name_still_refused": v["LOCAL_NAME_DIRTY_refused"],
            "clean_still_allowed": v["CLEAN_CLEAN_allowed"],
            "regressions_still_held": all(x for k, x in v.items() if k.startswith("REGRESSION_")),
        }
    return arms


def main() -> int:
    base = load_publisher()
    v = verdicts(base)
    cli = cli_refusal_cells()
    arms = arm_results()
    checks = {
        "cell1_LOCAL_NAME_DIRTY_refused": v["LOCAL_NAME_DIRTY_refused"],
        "cell1_cli_rc5": cli["LOCAL_NAME_DIRTY_rc_is_5"],
        "cell1_cli_named_refusal_and_zero_put": cli["LOCAL_NAME_DIRTY_printed_refusal"] and cli["LOCAL_NAME_DIRTY_no_upload_claim"],
        "cell2_REPO_PATH_DIRTY_refused": v["REPO_PATH_DIRTY_refused"],
        "cell2_cli_rc5": cli["REPO_PATH_DIRTY_rc_is_5"],
        "cell2_cli_named_refusal_and_zero_put": cli["REPO_PATH_DIRTY_printed_refusal"] and cli["REPO_PATH_DIRTY_no_upload_claim"],
        "cell3_CLEAN_CLEAN_positive_control": v["CLEAN_CLEAN_allowed"],
        "cell4_traversal": v["REGRESSION_traversal_refused"],
        "cell4_bad_prefix": v["REGRESSION_bad_prefix_refused"],
        "cell4_control_tool_gate": v["REGRESSION_control_tool_gate"],
        "cell4_sqlite_magic": v["REGRESSION_sqlite_magic_refused"],
        "cell4_secret_content": v["REGRESSION_secret_content_refused"],
        "cell5_single_helper_both_scopes": v["LOCAL_NAME_DIRTY_refused"] and v["REPO_PATH_DIRTY_refused"],
        "cell6_zero_put_in_refusal_paths": cli["LOCAL_NAME_DIRTY_no_upload_claim"] and cli["REPO_PATH_DIRTY_no_upload_claim"],
        "cell7_refusal_names_rule_not_secret": v["REFUSAL_NAMES_RULE_NO_SECRET"],
        "killer_M1_repo_path_guard_removed_is_caught": arms["M1_repo_path_guard_removed"]["repo_path_dirty_now_allowed"]
        and arms["M1_repo_path_guard_removed"]["local_name_still_refused"],
        "killer_M2_local_only_regression_is_caught": arms["M2_local_only_regression"]["repo_path_dirty_now_allowed"]
        and arms["M2_local_only_regression"]["clean_still_allowed"],
        "mutants_do_not_break_other_cells": all(
            a["regressions_still_held"] and a["clean_still_allowed"] for a in arms.values()),
    }
    derived = "ALL_GREEN" if all(checks.values()) else "RED_CELLS: " + ",".join(k for k, x in checks.items() if not x)
    receipt = {
        "schema": "CNX_INSTRUMENT_SELFPTEST_V1",
        "order": "ORD-0275",
        "instrument": "live_checks/publish_evidence.py",
        "instrument_blob_sha1": hashlib_blob(PUBLISHER),
        "test_file": os.path.basename(os.path.abspath(__file__)),
        "publisher_source_bytes": len(io.open(PUBLISHER, "rb").read()),
        "guard_verdicts": v,
        "cli_verdicts": cli,
        "mutation_arms": arms,
        "checks": checks,
        "derived_result": derived,
        "note": "derived_result is computed from the cells above; the red team re-derives independently (B-1).",
    }
    out = os.path.join(HERE, "receipts", "ord0275_selftest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    print("derived_result =", derived)
    print("wrote", out)
    for k, x in checks.items():
        print("  %-46s %s" % (k, "ok" if x else "FAIL"))
    return 0 if all(checks.values()) else 4


def hashlib_blob(path):
    import hashlib
    b = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
