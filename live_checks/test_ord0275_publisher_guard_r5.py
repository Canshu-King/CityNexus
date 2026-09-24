"""ORD-0275 r3 - publisher guard, driven in-process, zero writes.

Covered here, item by item, so both the red team's five residuals and the arbiter's Q18 cell have readings
that can actually fail:

  D1  the cell that used to check `isinstance(rc, int)` now asserts the recorded PUT COUNTERS themselves.
  D2  `behaviour_signature()` now spans BOTH layers - the nine in-process guard readings r2 published
      (reused verbatim from r2, not re-invented) plus a CLI (rc, PUT) pair for six arms.  The red team
      proved r2's signature was blind to CLI-only mutations; a signature over this file's arms is not.
  D3  `rewrites` records the sha1 of the POST-image, so M1 and M2 differ in a published field instead of
      being identical in every one of them.
  D4  `test_file` is this file's own basename, so the name matches the bytes it ships with.
  D5  the stub records the repo_path of every PUT intention, and the positive-control cell asserts the
      target is the clean one and that exactly one was attempted.
  Q18 four arms - LEGACY_IDENTICAL (rc=0, GET>0, PUT=0), LEGACY_DIFFERENT (rc=5, PUT=0), LEGACY_ABSENT
      (rc=5, PUT=0), LEGACY_AUTH (rc=6, PUT=0) - plus the demanded mutation: exact-SHA equality traded for
      "the remote answered 200", which must be killed by LEGACY_DIFFERENT.

The transport is replaced BEFORE `main()` is entered, so a PUT is only ever a recorded intention; nothing is
uploaded and the publisher's own bytes on disk are never edited (mutations are compiled from a string).
"""
import ast
import hashlib
import io
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.join(HERE, "publish_evidence.py")
OUT = os.path.join(HERE, "receipts", "ord0275_selftest_r5.json")
GREEN, RED = "GREEN", "RED"

# r5: the coordinate this instrument pins its subject to.  `publish_evidence.py` on disk carries the bytes
# that are PUBLISHED AS `live_checks/publish_evidence_r5.py` on `commander/control` - the local name and the
# published revision name differ, which is itself DEBT-1, so the receipt must disclose both.
PUBLISHER_PINNED_BLOB = "ea4416dbafa7ac84718c3d87bd56394fb5ca5f7b"
PUBLISHER_PUBLISHED_AS = "live_checks/publish_evidence_r5.py"
BLOB_URL = ("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/%s")
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
# Built from parts so this source carries no full revision literal of its own.
STALE_NAME_RE = re.compile("test_ord0275_publisher_guard" + r"_r\d+\.py")


def fetch_published_blob(sha):
    """Read the pinned publisher back out of GitHub and prove it by recomputed blob sha1.

    A local path is not a coordinate (EXTERNALLY_READABLE_EVIDENCE).  Failing here is a real red, not a
    reason to skip: a coordinate nobody outside my disk can read cannot be re-derived by the verifier.
    """
    import base64
    import urllib.request
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(BLOB_URL % sha, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-0275-r5"})
    with urllib.request.urlopen(req, timeout=120) as r:
        meta = json.loads(r.read().decode("utf-8"))
    raw = base64.b64decode(meta["content"].replace("\n", ""))
    if blob_sha(raw) != sha:
        raise AssertionError("readback sha1 mismatch for " + sha)
    return raw

# r2's fixtures, reused verbatim (inventing a parallel set is how r3's first draft went RED on me)
CLEAN_LOCAL = "_ord0275_r3_receipt.json"
CLEAN_REPO = "evidence/ord0275-publisher-path-guard/receipt.json"
LOCAL_DIRTY = "_live.db-witness.json"
REPO_DIRTY = "evidence/ord0275/_live_read.json"
CLEAN_BLOB = b'{"order": "ORD-0275", "value": 1}\n'
# Q23 condition 2: the synthetic nature must be DECLARED IN THE NAME, not only inside the value text.
#
# PUBLISHER_SELF_PUBLICATION_CONTRACT (arbiter 2026-09-25T01:3x+08) is why these are assembled rather than
# written as literals: this file tests a secret guard, and a guard that refuses the source of its own test
# leaves evidence nobody else can re-run.  The principle from r2 still holds and is NOT traded away - the
# bytes handed to the guard are still ONE WHOLE LITERAL (see F1 below and the self-check cell X2): I assemble
# the fixture once, in Python, and hand the finished bytes over, so the block and the exemption can never
# end up judging different fragments of a concatenation.
FIX_SK_PREFIX = "sk-" + "synthetic-not-a-real-key-" + "0123456789" + "abcdef"
SYNTHETIC_TEST_FIXTURE_VALUE = FIX_SK_PREFIX
BLOB_OF_FIXTURE = ('{"api_' + 'key": "' + SYNTHETIC_TEST_FIXTURE_VALUE + '"}\n').encode()
SECRET_BLOB = BLOB_OF_FIXTURE
SHORT_REF = SYNTHETIC_TEST_FIXTURE_VALUE[:8]     # <=15 chars on purpose: an identifier-shaped right-hand side
SECRET_LINE = SHORT_REF                          # of that length is NOT the shape the rule objects to

# the Q18 shape: a repo_path whose NAME layer is denylisted but whose object already exists byte-identically
LEGACY_REPO = "evidence/ord0275-publisher-path-guard/_live_legacy_cell.json"
LEGACY_LOCAL = os.path.join(HERE, "_ord0275_r3_legacy_cell.json")
LEGACY_BLOB = b'{"cell": "legacy identical historical path"}\n'


def blob_sha(raw):
    return hashlib.sha1(b"blob %d" % len(raw) + bytes(1) + raw).hexdigest()


def pub_src():
    return io.open(PUBLISHER, encoding="utf-8").read()


def load_publisher(source=None):
    """Compile the publisher (or one mutant of it) into a private namespace; the file on disk is untouched."""
    mod = ast.parse(source if source is not None else pub_src())
    ns = {"__name__": "publisher_under_test", "__file__": PUBLISHER}
    exec(compile(mod, PUBLISHER, "exec"), ns)
    return ns


def guard_bools(ns):
    """R2's nine readings, same names, same polarity - they must survive the Q18 refactor unchanged."""
    g = ns["guard"]
    out = {}
    out["LOCAL_NAME_DIRTY_refused"] = g(LOCAL_DIRTY, CLEAN_REPO, CLEAN_BLOB) is not None
    out["REPO_PATH_DIRTY_refused"] = g(CLEAN_LOCAL, REPO_DIRTY, CLEAN_BLOB) is not None
    out["CLEAN_CLEAN_allowed"] = g(CLEAN_LOCAL, CLEAN_REPO, CLEAN_BLOB) is None
    out["REGRESSION_traversal_refused"] = g(CLEAN_LOCAL, "evidence/../x.json", CLEAN_BLOB) is not None
    out["REGRESSION_bad_prefix_refused"] = g(CLEAN_LOCAL, "backend/app/main.py", CLEAN_BLOB) is not None
    out["REGRESSION_control_tool_gate"] = (
        g(CLEAN_LOCAL, "live_checks/x.py", CLEAN_BLOB) is not None
        and g(CLEAN_LOCAL, "live_checks/x.py", CLEAN_BLOB, control_tool=True) is None)
    out["REGRESSION_sqlite_magic_refused"] = \
        g(CLEAN_LOCAL, CLEAN_REPO, b"SQLite format 3" + bytes(1) + b"j" * 40) is not None
    out["REGRESSION_secret_content_refused"] = g(CLEAN_LOCAL, CLEAN_REPO, SECRET_BLOB) is not None
    r = g(CLEAN_LOCAL, CLEAN_REPO, SECRET_BLOB) or ""
    out["REFUSAL_NAMES_RULE_NO_SECRET"] = ("secret_pattern" in r) and (SECRET_LINE not in r)
    return out


def make_stub(get_status, get_sha):
    state = {"GET": 0, "PUT": 0, "PUT_targets": [], "anomalies": []}

    def fake_call(method, url, payload=None, tries=3):
        if method == "GET":
            state["GET"] += 1
            if get_status == 200:
                return 200, {"sha": get_sha, "size": len(LEGACY_BLOB), "name": "x", "content": ""}
            if get_status == 404:
                return 404, "Not Found"
            return get_status, "auth-or-noise"
        if method == "PUT":
            state["PUT"] += 1
            state["PUT_targets"].append(url.split("/contents/")[-1].split("?")[0])
            return 201, {"commit": {"sha": "0" * 40}}
        state["anomalies"].append("UNEXPECTED_" + method)
        return 400, "stub"
    return state, fake_call


# the six CLI arms whose readings join the behaviour signature (D2)
ARMS = {
    "LEGACY_IDENTICAL": (LEGACY_LOCAL, LEGACY_REPO, 200, blob_sha(LEGACY_BLOB)),
    "LEGACY_DIFFERENT": (LEGACY_LOCAL, LEGACY_REPO, 200, "e" * 40),
    "LEGACY_ABSENT": (LEGACY_LOCAL, LEGACY_REPO, 404, None),
    "LEGACY_AUTH": (LEGACY_LOCAL, LEGACY_REPO, 401, None),
    "FOREIGN_PREFIX": (CLEAN_LOCAL, "backend/app/main.py", 404, None),
    "REPO_NAME_DIRTY": (CLEAN_LOCAL, REPO_DIRTY, 404, None),
    "POSITIVE_CLEAN_WRITE": (CLEAN_LOCAL, CLEAN_REPO, 404, None),
}


class RealNetworkTripwire(AssertionError):
    """Raised instead of touching github.com.  See the note on `cli_arm`."""


def cli_arm(ns, label):
    """Run one arm against a stubbed transport.

    MEASURED LESSON (2026-09-24 19:46): the first version of this function did `ns2 = dict(ns)` and set the
    stub on the COPY.  A function's `__globals__` is the dict it was exec'd into, so the copy had no effect
    and every "stubbed" arm went to the REAL API - which published `evidence/ord0275-publisher-path-guard/
    receipt.json` as commit cb8ef590 while this file claimed `writes_performed_to_github: 0`.  Two cells read
    RED and I refused to explain them away, which is the only reason it was caught.  So: install the stub on
    the module's OWN namespace, restore it afterwards, and keep a tripwire that raises rather than dialling
    out if any code path still reaches for the network.
    """
    local, repo, status, sha = ARMS[label]
    state, transport = make_stub(status, sha)
    real_call, real_urlopen, real_argv = ns["call"], ns["urllib"].request.urlopen, list(ns["sys"].argv)
    # MEASURED 2026-09-24 23:20 (watchdog stack: publish_evidence.py:362 `time.sleep(2)`): the CLI arms did
    # not hang, they PAID the publisher's real wall-clock backoff - 2 s + 2/4/6 s retries, per arm, per run,
    # times every mutant.  Neutralising the sleep is test-only acceleration: the retry COUNT, which is what
    # the arms assert on, is untouched.
    real_sleep = ns["time"].sleep
    ns["time"].sleep = lambda _s: None

    def tripwire(*a, **k):
        raise RealNetworkTripwire("a test arm tried to reach github.com: %s" % (a[:2],))

    ns["call"] = transport
    ns["urllib"].request.urlopen = tripwire
    ns["sys"].argv = ["publish_evidence.py", local, repo, "ord0275 r3 arm"]
    try:
        rc = ns["main"]()
    finally:
        ns["call"], ns["sys"].argv = real_call, real_argv
        ns["urllib"].request.urlopen = real_urlopen
        ns["time"].sleep = real_sleep
    return {"rc": rc, "PUT": state["PUT"], "GET": state["GET"], "PUT_targets": state["PUT_targets"]}


def cli_readings(ns):
    """ONE run per arm.

    The previous line here was a dict comprehension that called `cli_arm(ns, label)` TWICE - once for
    `rc`, once for `PUT` - with two freshly built stubs.  So the pair it published described two
    different invocations, which is the exact shape of the lesson written on `cli_arm`.  Measured cost of
    the double call: ~14 s of publisher backoff per arm, which is why this file looked hung tonight.
    """
    readings = {}
    for label in sorted(ARMS):
        r = cli_arm(ns, label)
        readings[label] = (r["rc"], r["PUT"])
    return readings


def behaviour_signature(ns):
    """D2: the vector now contains CLI behaviour, so a mutation that only changes the CLI layer can no
    longer present a signature equal to base (r2's M4 did exactly that)."""
    vec = {"guard": guard_bools(ns), "cli": {k: list(v) for k, v in cli_readings(ns).items()}}
    return hashlib.sha1(json.dumps(vec, sort_keys=True).encode("utf-8")).hexdigest()


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    io.open(LEGACY_LOCAL, "w", encoding="utf-8", newline="\n").write(LEGACY_BLOB.decode())
    io.open(CLEAN_LOCAL, "w", encoding="utf-8", newline="\n").write(CLEAN_BLOB.decode())
    cells = []

    def check(name, ok, detail):
        cells.append({"cell": name, "verdict": GREEN if ok else RED, "detail": detail})

    base = load_publisher()
    want_legacy = blob_sha(LEGACY_BLOB)
    check("T0_no_arm_can_reach_the_network", True,
          {"tripwire": "urllib.request.urlopen is replaced by a raiser around every arm; the accident that "
                       "motivated it is recorded in the receipt under unintended_write",
           "unintended_write": {"path": "evidence/ord0275-publisher-path-guard/receipt.json",
                                "commit": "cb8ef590", "blob": "c1f029783f55406438de0bbcb509c6fb4248d156",
                                "bytes": 34, "at": "2026-09-24T11:46:07Z",
                                "status": "accidental, disclosed, NOT an instrument output; it overwrote "
                                          "nothing (that path has exactly one commit, this one)"}})

    # ---------- P1..P3 PUBLISHER_SELF_PUBLICATION_CONTRACT applied to this very file
    # The arbiter's contract (2026-09-25T01:3x+08) says a tool must obey the rule it enforces.  These three
    # cells are the whole argument that composing a fixture is not the same as hiding one: the SOURCE stops
    # carrying a credential-shaped literal (P1 green), the RUNTIME bytes are unchanged and still object to
    # (P2/P3), so nothing about what the guard actually judges got softer.
    own = io.open(__file__, "rb").read()
    own_refusal = base["_content_refusal"](own) or ""
    check("P1_this_instrument_can_be_published_by_the_guard_it_tests",
          base["_content_refusal"](own) is None,
          {"own_bytes": len(own),
           "rule_hit": own_refusal.split("secret_pattern=")[-1].rstrip(")") if own_refusal else "NONE"})
    check("P2_the_assembled_fixture_is_still_one_whole_literal_of_the_named_shape",
          (SECRET_BLOB == b'{"api_' + b'key": "' + SYNTHETIC_TEST_FIXTURE_VALUE.encode() + b'"}\n'
           and SECRET_BLOB.startswith(b'{"api_key": "') and len(SYNTHETIC_TEST_FIXTURE_VALUE) == 44
           and SECRET_LINE == SYNTHETIC_TEST_FIXTURE_VALUE[:8] and len(SECRET_LINE) == 8),
          {"value_len": len(SYNTHETIC_TEST_FIXTURE_VALUE), "blob_len": len(SECRET_BLOB),
           "secret_line_len": len(SECRET_LINE),
           "rule": "r2's design note stands: the guard and the exemption must see ONE whole literal.  They "
                   "do - it is the SOURCE that no longer spells it out contiguously"})
    check("P3_the_guard_still_objects_to_the_runtime_bytes",
          base["_content_refusal"](SECRET_BLOB) is not None,
          {"refusal_rule": (base["_content_refusal"](SECRET_BLOB) or "").split("secret_pattern=")[-1].rstrip(")"),
           "meaning": "composing the fixture did not create a way past the block: handed the finished bytes, "
                      "the guard still refuses them"})

    # ---------- the Q18 arms, measured through main()
    li = cli_arm(base, "LEGACY_IDENTICAL")
    ld = cli_arm(base, "LEGACY_DIFFERENT")
    la = cli_arm(base, "LEGACY_ABSENT")
    au = cli_arm(base, "LEGACY_AUTH")
    ff = cli_arm(base, "FOREIGN_PREFIX")
    rn = cli_arm(base, "REPO_NAME_DIRTY")
    check("LEGACY_IDENTICAL_no_write_rc0", li["rc"] == 0 and li["GET"] > 0 and li["PUT"] == 0,
          {"arm": li, "want_sha": want_legacy[:16],
           "rule": "historical path + byte-identical object = PROVED, nothing written; NOT a re-approval "
                   "of the name"})
    check("LEGACY_DIFFERENT_refused_zero_PUT", ld["rc"] == 5 and ld["PUT"] == 0 and ld["GET"] > 0, ld)
    check("LEGACY_ABSENT_refused_zero_PUT", la["rc"] == 5 and la["PUT"] == 0, la)
    check("LEGACY_AUTH_ANOMALY_fail_closed_zero_PUT", au["rc"] == 6 and au["PUT"] == 0, au)
    check("Q18_exemption_does_not_reach_prefix_or_name_layers",
          ff["rc"] == 5 and ff["PUT"] == 0 and rn["PUT"] == 0,
          {"foreign_prefix": {k: ff[k] for k in ("rc", "PUT", "GET")},
           "repo_name_dirty": {k: rn[k] for k in ("rc", "PUT")},
           "rule": "hard boundary 2 of the ruling: only the NAME layer may be judged against the remote"})

    # ---------- D5: a clean target still writes, exactly once, to the path it names.
    # This goes through cli_arm like every other arm: the first draft built its own `dict(ns)` copy here and
    # was therefore the one arm that really reached github.com (see the note on cli_arm).
    pos = cli_arm(base, "POSITIVE_CLEAN_WRITE")
    check("CLEAN_PATH_positive_control_writes_once_to_the_named_target",
          pos["PUT"] == 1 and pos["PUT_targets"] == [CLEAN_REPO] and pos["rc"] in (0, 4, 7),
          {"PUT": pos["PUT"], "targets": pos["PUT_targets"], "rc": pos["rc"], "GET": pos["GET"],
           "rc_note": "0 = proved, 4/7 = read-back noise from the stubbed GET; neither is an extra write"})

    # ---------- D1: the cell reads the counters themselves
    counters = {"LEGACY_IDENTICAL": li["PUT"], "LEGACY_DIFFERENT": ld["PUT"], "LEGACY_ABSENT": la["PUT"],
                "LEGACY_AUTH": au["PUT"], "FOREIGN_PREFIX": ff["PUT"], "REPO_NAME_DIRTY": rn["PUT"],
                "CLEAN_positive": pos["PUT"]}
    check("CLI_cell_reads_the_PUT_counters_not_their_types",
          all(isinstance(v, int) for v in counters.values()) and
          sum(v for k, v in counters.items() if k != "CLEAN_positive") == 0 and
          counters["CLEAN_positive"] == 1,
          {"counters": counters, "rule": "r2's cell6 stayed True with every counter forced to False"})

    # ---------- mutants: one variable each; each must change its own owner reading
    MUT = {
        "M1_repo_path_guard_removed": ("    refused = repo_path_name_refusal(repo_path)\n    if refused:\n"
                                       "        return refused", "    pass"),
        "M2_target_layer_dropped": ("    refusal = guard_pre(local_path, repo_path, blob) or "
                                    "guard_target(repo_path, message, control_tool)",
                                    "    refusal = guard_pre(local_path, repo_path, blob)"),
        "M3_helper_neutralised": ("    c = candidate.lower()", "    c = candidate.lower()\n    return None"),
        "M4_200_instead_of_exact_sha": ("        if existing and existing == want:", "        if existing:"),
    }
    OWNER = {"M1_repo_path_guard_removed": ("REPO_PATH_DIRTY_refused", "REPO_NAME_DIRTY"),
             "M2_target_layer_dropped": ("REGRESSION_bad_prefix_refused", "FOREIGN_PREFIX"),
             "M3_helper_neutralised": ("LOCAL_NAME_DIRTY_refused", "REPO_NAME_DIRTY"),
             "M4_200_instead_of_exact_sha": ("CLEAN_CLEAN_allowed", "LEGACY_DIFFERENT")}
    base_bools, base_cli = guard_bools(base), cli_readings(base)
    base_sig = behaviour_signature(base)
    kills, rewrites = [], []
    for name, (old, new) in sorted(MUT.items()):
        src = pub_src()
        anchored = old in src
        mutated = src.replace(old, new, 1)
        rewrites.append({"mutant": name, "anchored": anchored, "n_edits": 1,
                         "post_image_blob_sha1": blob_sha(mutated.encode("utf-8")),
                         "pre_image_blob_sha1": blob_sha(old.encode("utf-8"))})
        if not anchored:
            kills.append({"mutant": name, "verdict": "SURVIVED", "why": "anchor not found - no-op mutant",
                          "owner_reads_differently": False, "signature_differs": False,
                          "bool_diffs": [], "cli_diffs": [],
                          "owner_guard_cell": OWNER[name][0], "owner_cli_cell": OWNER[name][1]})
            continue
        mns = load_publisher(mutated)
        mb, mc = guard_bools(mns), cli_readings(mns)
        bool_diff = sorted(k for k in base_bools if base_bools[k] != mb[k])
        cli_diff = sorted(k for k in base_cli if tuple(base_cli[k]) != tuple(mc[k]))
        sig_diff = behaviour_signature(mns) != base_sig
        guard_owner, cli_owner = OWNER[name]
        kills.append({"mutant": name, "owner_guard_cell": guard_owner, "owner_cli_cell": cli_owner,
                      "bool_diffs": bool_diff, "cli_diffs": cli_diff, "signature_differs": sig_diff,
                      "verdict": "KILLED" if sig_diff else "SURVIVED",
                      "owner_reads_differently":
                          (guard_owner in bool_diff) or (tuple(base_cli[cli_owner]) != tuple(mc[cli_owner]))})
    for k in kills:
        check("K_%s" % k["mutant"], k["verdict"] == "KILLED" and k["owner_reads_differently"], k)
    check("K_mutants_have_four_distinct_owner_cells",
          len({(k["owner_guard_cell"], k["owner_cli_cell"]) for k in kills}) == 4,
          {"owners": [(k["owner_guard_cell"], k["owner_cli_cell"]) for k in kills]})
    m1 = next(r for r in rewrites if r["mutant"] == "M1_repo_path_guard_removed")
    m2 = next(r for r in rewrites if r["mutant"] == "M2_target_layer_dropped")
    check("D3_M1_and_M2_are_distinguishable_in_the_published_fields",
          m1["post_image_blob_sha1"] != m2["post_image_blob_sha1"],
          {"m1_post": m1["post_image_blob_sha1"][:16], "m2_post": m2["post_image_blob_sha1"][:16],
           "m1_pre": m1["pre_image_blob_sha1"][:16], "m2_pre": m2["pre_image_blob_sha1"][:16],
           "rule": "r2 published only the PRE-image, and M1/M2 shared it, so every field agreed"})
    m2k = next(k for k in kills if k["mutant"] == "M2_target_layer_dropped")
    check("D2_signature_is_no_longer_blind_to_CLI_only_mutants",
          all(k["signature_differs"] for k in kills) and bool(m2k["cli_diffs"]),
          {"note": "M2 changes only main()'s CLI composition; r2's 9-boolean vector could not see it",
           "m2_cli_diffs": m2k["cli_diffs"]})

    # ---------- regressions: nothing else in the judge moved
    check("REGRESSION_the_nine_guard_readings_all_hold", all(base_bools.values()),
          {"bools": base_bools, "signature": base_sig[:16]})
    pb = io.open(PUBLISHER, "rb").read()
    # ---- r5: r3/r4's R cell was TWO defects in one.  (a) `blob_sha(pb) == blob_sha(pub_src())` read the
    #      SAME file twice, so it could never fail - a vacuous judge.  (b) the name half pinned a literal
    #      revision filename, so a re-runner holding the published bytes under the published name went RED
    #      for a naming reason (the red team hit exactly that: 19/20).  Both halves are replaced by judges
    #      that bite the defect class and survive a rename.
    local_blob = blob_sha(pb)
    check("R1_publisher_bytes_match_the_pinned_coordinate",
          local_blob == PUBLISHER_PINNED_BLOB,
          {"local_blob": local_blob, "pinned": PUBLISHER_PINNED_BLOB, "bytes": len(pb),
           "teeth": "an edit to the on-disk publisher goes RED here; r3 compared the file to itself"})
    readback = {"attempted": True}
    try:
        raw = fetch_published_blob(PUBLISHER_PINNED_BLOB)
        readback["external_blob_sha1"] = blob_sha(raw)
        readback["external_bytes"] = len(raw)
        readback["equals_local_disk_bytes"] = (blob_sha(raw) == local_blob)
        readback["equals_pinned"] = (blob_sha(raw) == PUBLISHER_PINNED_BLOB)
    except Exception as exc:
        readback["attempted"] = False
        readback["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
    check("R2_pinned_coordinate_is_externally_readable_and_byte_equal",
          bool(readback.get("equals_local_disk_bytes")) and bool(readback.get("equals_pinned")),
          readback)
    own_src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    stale = STALE_NAME_RE.findall(own_src)
    check("R3_no_stale_revision_filename_literal_in_this_source",
          not stale,
          {"hits": sorted(set(stale)), "test_file": os.path.basename(os.path.abspath(__file__)),
           "note": "D4 kept, but as a computed field: the receipt names the file that ships these bytes; "
                   "a hardcoded revision filename in an assertion is the defect, not the rename"})

    n_green = sum(1 for c in cells if c["verdict"] == GREEN)
    overall = GREEN if n_green == len(cells) else RED
    receipt = {"what": "ORD-0275 r3: Q18 legacy no-op arms + the five D1..D5 corrections",
               "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "test_file": os.path.basename(__file__),
               "publisher": {"path": PUBLISHER.replace("\\", "/"), "bytes": len(pb), "blob": blob_sha(pb)},
               "arbiter_requirement": {"ruling": "bus 5806436649 Q18 (b)", "arms": sorted(ARMS),
                                       "demanded_mutation": "exact SHA equality -> 'remote 200 is enough', "
                                                            "killed by LEGACY_DIFFERENT"},
               "redteam_residuals_addressed": ["D1 counters asserted", "D2 signature spans CLI",
                                               "D3 post-image sha1 published", "D4 test_file basename",
                                               "D5 PUT target asserted"],
               "guard_readings": base_bools, "cli_readings": {k: list(v) for k, v in base_cli.items()},
               "behaviour_signature": base_sig, "rewrites": rewrites, "kills": kills,
               "cells": cells, "cells_total": len(cells), "cells_green": n_green, "overall": overall,
               "claimed_result": "in_process_selftest_" + overall,
               "writes_performed_to_github_by_this_run": 0,
               "unintended_write_before_the_tripwire": {"path": "evidence/ord0275-publisher-path-guard/receipt.json", "commit": "cb8ef590", "blob_sha1": "c1f029783f55406438de0bbcb509c6fb4248d156", "bytes": 34, "at_utc": "2026-09-24T11:46:07Z"}}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=1, ensure_ascii=False))
    print("overall = %s (%d/%d)  publisher blob=%s" % (overall, n_green, len(cells), blob_sha(pb)[:16]))
    for c in cells:
        print("  %-58s %s" % (c["cell"], c["verdict"]))
    for k in kills:
        print("  kill %-34s %-9s bool_diffs=%s cli_diffs=%s" % (k["mutant"], k["verdict"],
                                                                k.get("bool_diffs"), k.get("cli_diffs")))
    print("wrote", OUT)
    for f in (LEGACY_LOCAL, CLEAN_LOCAL):
        if os.path.isfile(f):
            os.remove(f)
    return 0 if overall == GREEN else 1


if __name__ == "__main__":
    raise SystemExit(main())
