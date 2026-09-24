"""ORD-0271-A / DEBT-4 offline proof: re-derive the B-arm decision from the two REAL samples.

Why offline: the gauge under test (deploy_bundle.py, blob 149e9c6dbe6debca...) is the instrument that
currently guards the phone preview, so this test must not run a deployment.  It extracts the pure
decision function `_debt4_decide` from the draft source by AST (no import of the whole gauge, no
side effects) and feeds it inputs taken from two immutable, externally readable releases:

  sample A  worker-only release, asset names byte-identical across generations
            commander/control git blob b9be3a5cb683fb14dce44477e8ed8ae07e1f0658 (66,553 B)
            the shipped gauge answered overall RED here, and the only red source was
            B_NEW_INDEX.old_refs_absent=false - a mathematically unsatisfiable demand.
  sample B  a release where the asset really changed
            commander/control:evidence/ord0271-a-gauge-fixtures/sample_B_real_asset_change_0924_020432.json
            blob dccc1ee1359154dc54de79e5571a30c8d4cc818a (66,509 B), overall GREEN.

Worker digests are computed from the real files each release backed up on disk, not typed in.
"""
import ast
import hashlib
import io
import json
import os
import pathlib
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "deploy_bundle_v2_draft.py")
GAUGE = os.path.join(HERE, "deploy_bundle.py")
SERVE = pathlib.Path(r"D:\moodle\_qoder_preview_20260920\dist")
SAMPLE_A_BLOB = "b9be3a5cb683fb14dce44477e8ed8ae07e1f0658"
SAMPLE_B_PATH = "evidence/ord0271-a-gauge-fixtures/sample_B_real_asset_change_0924_020432.json"
SAMPLE_B_BLOB = "dccc1ee1359154dc54de79e5571a30c8d4cc818a"
IN_SERVICE_GAUGE_BLOB = "149e9c6dbe6debca92041bb192761c1cf1aa2a7"  # the gauge currently guarding the phone chain
OUT = os.path.join(HERE, "receipts", "ord0271a_debt4_selftest.json")


def extract_function(path, name):
    """Pull one top-level function out of a source file and compile it standalone."""
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    mod = ast.Module(body=[fn], type_ignores=[])
    ns = {}
    exec(compile(mod, path, "exec"), ns)
    return ns[name]


def blob_sha(path):
    b = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def fetch_blob(sha):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    req = urllib.request.Request(
        f"https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/{sha}",
        headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                 "User-Agent": "cnx-cmdr"})
    with urllib.request.urlopen(req, timeout=120) as r:
        meta = json.loads(r.read().decode())
    raw = base64_decode(meta["content"])
    if blob_sha_bytes(raw) != sha:
        raise SystemExit("sample blob readback mismatch for " + sha)
    return json.loads(raw.decode())


def base64_decode(s):
    import base64
    return base64.b64decode(s.replace("\n", ""))


def blob_sha_bytes(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def worker_sha_from_backup(backup_dir):
    p = pathlib.Path(backup_dir) / "v10-sw.js"
    if not p.is_file():
        return None
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def worker_sha_now():
    p = SERVE / "v10-sw.js"
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest() if p.is_file() else None


def main() -> int:
    decide = extract_function(DRAFT, "_debt4_decide")
    now_sha = worker_sha_now()
    a = fetch_blob(SAMPLE_A_BLOB)
    b = fetch_blob(SAMPLE_B_BLOB)

    # --- sample A: worker-only release.  The shipped gauge called this RED; the fix must call it GREEN.
    a_old_js = (a.get("generation_OLD") or {}).get("ref")
    a_old_refs = a["old_index_refs"]
    a_new_refs = a["new_index_refs"]
    a_prev = worker_sha_from_backup(a["backup_dir"])
    a_absent, a_ok, a_branch, a_changed, a_only = decide(
        a_old_js, a_old_refs, a_new_refs, True, a_prev, now_sha)

    # --- sample B: assets really changed; original semantics must hold, unchanged.
    b_old_js = (b.get("generation_OLD") or {}).get("ref")
    b_old_refs = b["old_index_refs"]
    b_new_refs = b["new_index_refs"]
    b_prev = worker_sha_from_backup(b["backup_dir"])
    b_absent, b_ok, b_branch, b_changed, b_only = decide(
        b_old_js, b_old_refs, b_new_refs, True, b_prev, now_sha)

    # --- counter-controls: the branch must not be a rubber stamp.
    # (1) worker-only shape but the worker did NOT move -> must be RED (no laundering "nothing deployed")
    same_worker_absent, same_worker_ok, same_worker_branch, *_ = decide(
        a_old_js, a_old_refs, a_new_refs, True, a_prev, a_prev)
    # (2) MIXED generation: the previous refs are a proper subset of what the new index references,
    #     i.e. one index naming both generations.  This is NOT worker-only and must stay RED.
    #     (Revision 1 of the draft judged worker_only as "old_js in new_refs" and washed exactly this case
    #      into GREEN_WORKER_ONLY_DEPLOY; the counter-example caught the defect.)
    mixed_refs = [b_old_js, "/assets/index-NEWONLY.js"] + [r for r in b_new_refs if r != b_old_js]
    mixed_absent, mixed_ok, mixed_branch, mixed_changed, mixed_only = decide(
        b_old_js, b_old_refs, mixed_refs, True, b_prev, now_sha)
    # (3) missing observation on either side of the worker comparison -> fail closed, never green
    missing_obs_absent, missing_obs_ok, missing_obs_branch, *_ = decide(
        a_old_js, a_old_refs, a_new_refs, True, None, now_sha)
    # (4) an empty "previous" observation must not be turned into a worker-only claim either
    empty_old_absent, empty_old_ok, empty_old_branch, *_ = decide(
        a_old_js, [], a_new_refs, True, a_prev, now_sha)

    checks = {
        "sampleA_is_recognised_as_worker_only": a_only is True,
        "sampleA_absent_is_not_applicable_not_true": a_absent is None,
        "sampleA_turns_GREEN_WORKER_ONLY_DEPLOY": a_ok is True and a_branch == "GREEN_WORKER_ONLY_DEPLOY",
        "sampleA_would_have_been_RED_under_the_old_rule": (a_old_js is not None) and (a_old_js in a_new_refs),
        "sampleB_not_worker_only": b_only is False,
        "sampleB_original_semantics_hold": b_absent is True and b_ok is True and b_branch == "NORMAL_ASSET_CHANGE_DEPLOY",
        "countercontrol_worker_not_moved_is_RED": same_worker_ok is False and same_worker_branch == "RED_WORKER_ONLY_DEPLOY_WITHOUT_WORKER_CHANGE",
        "countercontrol_mixed_generation_is_not_worker_only_and_is_RED": (
            mixed_only is False and mixed_absent is False and mixed_ok is False
            and mixed_branch == "NORMAL_ASSET_CHANGE_DEPLOY"),
        "countercontrol_empty_previous_observation_is_not_worker_only": (
            empty_old_ok is False or empty_old_branch == "RED_WORKER_ONLY_DEPLOY_WITHOUT_WORKER_CHANGE"),
        "failclosed_missing_worker_observation_is_RED": missing_obs_ok is False and missing_obs_branch == "RED_WORKER_ONLY_DEPLOY_WITHOUT_WORKER_CHANGE",
    }
    derived = "ALL_GREEN" if all(checks.values()) else "RED_CELLS: " + ",".join(k for k, v in checks.items() if not v)
    receipt = {
        "schema": "CNX_INSTRUMENT_SELFPTEST_V1",
        "order": "ORD-0271-A",
        "cell": "DEBT-4 worker-only deploy must not demand an unsatisfiable old_refs_absent",
        "instrument_under_change": "live_checks/deploy_bundle_v2_draft.py",
        "draft_blob_sha1": blob_sha(DRAFT),
        "in_service_gauge_blob_sha1": blob_sha(GAUGE),
        "in_service_gauge_untouched": blob_sha(GAUGE) == IN_SERVICE_GAUGE_BLOB,
        "draft_differs_from_in_service_gauge": blob_sha(DRAFT) != blob_sha(GAUGE),
        "samples": {
            "A": {"blob": SAMPLE_A_BLOB, "old_ref": a_old_js, "new_refs": a_new_refs,
                  "prev_worker_sha256": a_prev, "installed_worker_sha256": now_sha,
                  "shipped_verdict_overall": a.get("overall"),
                  "shipped_B_fields": (a.get("receipt_ABCDE") or {}).get("B_NEW_INDEX")},
            "B": {"blob": SAMPLE_B_BLOB, "old_ref": b_old_js, "new_refs": b_new_refs,
                  "prev_worker_sha256": b_prev, "installed_worker_sha256": now_sha,
                  "shipped_verdict_overall": b.get("overall"),
                  "shipped_B_fields": (b.get("receipt_ABCDE") or {}).get("B_NEW_INDEX")},
        },
        "derived_decisions": {
            "A": {"old_refs_absent": a_absent, "refs_ok": a_ok, "branch": a_branch, "worker_changed": a_changed, "worker_only": a_only},
            "B": {"old_refs_absent": b_absent, "refs_ok": b_ok, "branch": b_branch, "worker_changed": b_changed, "worker_only": b_only},
            "counter_worker_not_moved": {"refs_ok": same_worker_ok, "branch": same_worker_branch},
            "counter_stale_ref": {"old_refs_absent": mixed_absent, "refs_ok": mixed_ok, "branch": mixed_branch},
            "counter_missing_observation": {"refs_ok": missing_obs_ok, "branch": missing_obs_branch},
        },
        "checks": checks,
        "derived_result": derived,
        "note": "The shipped gauge's own B-field for sample A is quoted above: old_refs_absent=false with "
                "overall=RED. This test never runs a deployment and never writes the shared branch.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    print("derived_result =", derived)
    print("A branch:", a_branch, "| B branch:", b_branch, "| worker now:", now_sha[:16])
    print("shipped A overall =", a.get("overall"), "| shipped A old_refs_absent =",
          (a.get("receipt_ABCDE") or {}).get("B_NEW_INDEX", {}).get("old_refs_absent"))
    print("wrote", OUT)
    for k, v in checks.items():
        print("  %-56s %s" % (k, "ok" if v else "FAIL"))
    return 0 if all(checks.values()) else 4


if __name__ == "__main__":
    raise SystemExit(main())
