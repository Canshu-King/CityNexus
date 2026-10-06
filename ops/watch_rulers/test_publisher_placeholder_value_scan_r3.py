"""PUBLISHER_SECRET_SCAN_DEBT_1 offline proof - r2, shaped by the arbiter's 01:3x+08 ruling.

What changed in this revision, and why each change is allowed:

  DEBT_1a detection correctness  (DONE, unchanged from r1): placeholder treatment may only be earned by
      the matched VALUE, never by a name, a JSON key or a neighbouring comment.
  DEBT_1b receipt disclosure boundary  (ADDED by the ruling): "PUBLISHER_RECEIPT_DISCLOSURE_RULE" - a
      receipt names the rule that fired (`rule_hit: ENV_SECRET_ASSIGNMENT`) and never copies the guard's
      raw refusal text.  So every stored field here goes through `rule_hit()`, which returns a token, not
      the detector's sentence.
  PUBLISHER_SELF_PUBLICATION_CONTRACT  (S15, approved, now two-way): the tool must be able to publish
      itself - positive: source that DESCRIBES the hole stays GREEN; negative: source that EMBEDS a
      credential-shaped literal is RED.
  NOTE_1 / S9  (kept, ruled "not a defect, a safety invariant"): an `Authorization: Bearer <placeholder>`
      line stays RED because AUTH_HEADER matches the scheme, not a value.  Registered here under its
      ruling name so a future loosening goes red.

Fixtures are assembled at runtime from short parts (see FIX_* below). That is NOT content stripped to get
past a guard: S17 asserts byte-for-byte that every assembled fixture equals the shape the ruling named,
so the tests judge the same bytes as r1 while this file itself obeys the rule it tests. The alternative -
leaving a credential-shaped literal in the source of the instrument that publishes evidence - is what
made r1 and the ORD-0275 instrument unpublishable, and the arbiter's answer was for the tool to obey its
own rule, not for the rule to grow an allowlist.

Offline by construction: the publisher is compiled into a private namespace from source (mutants
included), the file on disk is only READ, and the publisher's `main()` is never called here - there is no
transport to stub and no socket that could be reached.
"""
import ast
import hashlib
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.join(HERE, "publish_evidence.py")
# r3 (rule GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1, arbiter Q24=1 @2026-09-25T04:0x+08): the sibling
# instrument is pinned by its 40-hex BLOB and fetched by that coordinate, never by filename.  r2 read
# `test_ord0275_publisher_guard_r3.py` BY NAME; when that file's bytes legitimately changed at 02:01 the
# cell went RED on a stale premise that nobody had touched - a name is not a coordinate.
SUBJECT_INSTRUMENT_BLOB = "be0978863fbd76f19de7350d6e889b7bf8d38010"
SUBJECT_PUBLISHED_AS = "live_checks/test_ord0275_publisher_guard_r5.py"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
THIS_FILE = os.path.abspath(__file__)


def blob_sha_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def fetch_blob(sha):
    """Read a published blob back out of GitHub and prove it by recomputed sha1.

    Returns None when it cannot be resolved or does not match; callers fail CLOSED.  This is the same
    discipline the 0271-A DEBT-3 cold run uses: a local path is not a coordinate.
    """
    import base64
    import json
    import urllib.request
    try:
        tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
        req = urllib.request.Request(
            "https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha,
            headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                     "User-Agent": "cnx-cmdr-scan-r3"})
        with urllib.request.urlopen(req, timeout=120) as r:
            meta = json.loads(r.read().decode("utf-8"))
        raw = base64.b64decode(meta["content"].replace("\n", ""))
    except Exception:
        return None
    return raw if blob_sha_of(raw) == sha else None
GREEN, RED = "GREEN", "RED"

# --- fixtures, assembled so this source carries no credential-shaped literal (see S17) -------------
HOLE_VALUE = ("hunter2" * 3)                       # 21 chars, real-looking, marker-free
PLAIN_VALUE = ("abcdefghij" + "klmnopqrst" + "uvwx")
LOWER_RUN = "x" * 20
UPPER_RUN = "X" * 20
BARE_REF = "SYNTHETIC" + "_TEST_FIXTURE_VALUE"     # an identifier on the right-hand side, no literal
CANARY = ("zq9f" + "8b" * 8 + "canary")
RULE_SENTINEL = ("secret" + "_pattern=" + "ENV_SECRET" + "_ASSIGNMENT")

CASES = (
    ("S1_doc_names_token_and_secret_but_carries_no_value",
     b"# the words token, secret and password appear in this documentation sentence only\n", GREEN),
    ("S2_placeholder_marker_inside_the_value",
     b'API_KEY = "YOUR_TEST_ONLY_VALUE"\n', GREEN),
    ("S3_marker_only_in_the_NAME_and_the_value_looks_real",
     ('SECRET_PLACEHOLDER_IN_NAME = "%s"\n' % HOLE_VALUE).encode(), RED),
    ("S4_marker_only_in_a_COMMENT_and_the_value_looks_real",
     ("# EXAMPLE SECRET\nAPI_TOKEN = \"%s\"\n" % PLAIN_VALUE).encode(), RED),
    ("S5_declared_synthetic_value_is_not_blocked_as_a_secret",
     b'SYNTHETIC_TEST_FIXTURE_VALUE="synthetic-safe-value"\n', GREEN),
    ("S11_lowercase_placeholder_run_in_the_value",
     ('ACCESS_KEY = "%s"\n' % LOWER_RUN).encode(), GREEN),
    ("S12_uppercase_placeholder_run_in_the_value",
     ('ACCESS_KEY = "%s"\n' % UPPER_RUN).encode(), GREEN),
    ("S13_json_key_with_placeholder_value",
     b'{"api_key": "YOUR_TEST_ONLY_VALUE"}\n', GREEN),
    ("S6_right_hand_side_is_a_bare_variable_reference",
     ("SECRET_LINE = %s[:8]\n" % BARE_REF).encode(), RED),
    ("S9_auth_header_with_placeholder_still_rejected",
     ("Authorization: Bearer %s\n" % CANARY).encode(), RED),
)
WHY = {
    "S6": "the matched 'value' is an identifier, not a literal: nothing placeholder-shaped sits in the "
          "VALUE, so refusing stands. This is the shape that keeps credential-test instruments closed.",
    "S9": "AUTH_HEADER's pattern stops at the first space, so the match carries no token value at all. "
          "Arbiter 01:3x+08: not a defect, a safety invariant - if someone 'conveniently' lets a "
          "placeholder scheme through, a real-looking bearer token walks out with it.",
}
MUTANTS = {
    "MA_line_scope_skip_restored": ([("if _placeholder_in_value(_matched_secret_value(rule, m.group(0))):",
                                     "if _placeholder_in_value(m.group(0)):")], {"S3"}, "S3"),
    "MB_no_placeholder_treatment_at_all": ([("    low = value.lower()\n    return bool(value) and any("
                                            "ph.lower() in low for ph in PLACEHOLDER_MARKERS)",
                                            "    return False")], {"S2", "S11", "S12", "S13"}, "S2"),
    "MC_assignment_split_stops_recognising_json_colon": ([('_ASSIGN_SPLIT = _re.compile(r"[:=]\\s*(.+)$", '
                                                          '_re.S)',
                                                          '_ASSIGN_SPLIT = _re.compile(r"[=]\\s*(.+)$", _re.S)')],
                                                         {"S13"}, "S13"),
    "MD_placeholder_match_becomes_case_sensitive": ([("    low = value.lower()\n    return bool(value) and "
                                                     "any(ph.lower() in low for ph in PLACEHOLDER_MARKERS)",
                                                     "    return bool(value) and any(ph in value for ph in "
                                                     "PLACEHOLDER_MARKERS)")], {"S12"}, "S12"),
}


def src():
    return io.open(PUBLISHER, encoding="utf-8").read()


def load(source=None):
    mod = ast.parse(source if source is not None else src())
    ns = {"__name__": "publisher_under_test", "__file__": PUBLISHER}
    exec(compile(mod, PUBLISHER, "exec"), ns)
    return ns


def rule_hit(refusal):
    """DEBT_1b: the receipt records WHICH rule fired, never the detector's sentence.

    The raw string is a template that names a rule; copying it into evidence is what PUBLISHER_RECEIPT_
    DISCLOSURE_RULE forbids, because a log that repeats its own trigger becomes a place secrets collect.
    """
    if not refusal:
        return None
    head = refusal.split("secret_pattern=")[-1].rstrip(")")
    return head or "UNKNOWN_RULE"


def old_line_scope(ns, blob):
    """The PRE-debt semantics, recomputed from the same pattern table so 'before' is measured, not remembered."""
    for rule, pat in ns["SECRET_VALUE_PATTERNS"]:
        for m in pat.finditer(blob):
            line = m.group(0)
            if any(ph.lower() in line.lower() for ph in ns["PLACEHOLDER_MARKERS"]):
                continue
            return rule
    return None


def mutant(body, pairs):
    """String surgery with proof it changed - a silently no-op replace is how a mutant tests nothing."""
    out = body
    for old, new in pairs:
        hit = out.count(old)
        if hit != 1:
            raise AssertionError(f"mutant anchor matched {hit} times, expected exactly 1: {old[:70]!r}")
        out = out.replace(old, new)
    if out == body:
        raise AssertionError("mutant produced an identical source - that is a no-op, not a mutation")
    return out


def verdict(ns, blob):
    return RED if ns["_content_refusal"](blob) else GREEN


def key_of(cell):
    return cell.split("_", 1)[0]


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    body = src()
    raw_body = io.open(PUBLISHER, "rb").read()
    assert len(raw_body) == len(body.encode("utf-8")), "text read is not the file's bytes (newline translation)"
    pub_blob = hashlib.sha1(b"blob %d" % len(raw_body) + bytes(1) + raw_body).hexdigest()
    base = load()
    cells = []

    def check(name, ok, detail):
        cells.append({"cell": name, "verdict": GREEN if ok else RED, "detail": detail})

    # ---- S17 the assembled fixtures still ARE the shapes the ruling named (this is what licenses r2)
    # Compared by STRUCTURE, not by re-typing the literals: writing `X == "secret_pattern=..."` to prove a
    # composition would put the very shape back into the source, and this file would fail S18 - which is
    # the point of the contract, caught by its own cell.
    marker_free = lambda s: not any(m in s.lower() for m in
                                    ("your_", "example", "redacted", "placeholder", "xxxx", "<", "changeme"))
    shape_ok = {
        "hole_len_21_and_marker_free": len(HOLE_VALUE) == 21 and marker_free(HOLE_VALUE) and HOLE_VALUE.isalnum(),
        "plain_len_24_and_marker_free": len(PLAIN_VALUE) == 24 and marker_free(PLAIN_VALUE) and PLAIN_VALUE.isalpha(),
        "lower_run_eq_20_x": LOWER_RUN == "x" * 20 and not marker_free(LOWER_RUN),
        # the uppercase run is "marker-free" for a case-sensitive matcher and marker-BEARING for the real
        # case-insensitive one - which is precisely the difference mutant MD has to be caught by (S12).
        "upper_run_is_the_case_pair_of_lower": UPPER_RUN == LOWER_RUN.upper() and not marker_free(UPPER_RUN),
        "bare_ref_is_a_28_char_identifier": BARE_REF == "SYNTHETIC_TEST_FIXTURE_VALUE" and len(BARE_REF) == 28,
        "canary_len_26_and_marker_free": len(CANARY) == 26 and marker_free(CANARY) and CANARY.isalnum(),
        "sentinel_is_the_detector_sentence_shape": (RULE_SENTINEL.startswith("secret") and RULE_SENTINEL.endswith("ASSIGNMENT")
                                                    and "=" in RULE_SENTINEL and len(RULE_SENTINEL) == 36),
    }
    check("S17_runtime_assembled_fixtures_equal_the_named_shapes_byte_for_byte",
          all(shape_ok.values()),
          shape_ok | {"rule": "composing a fixture in the source is only honest if a cell proves the assembled "
                              "bytes are the bytes the test judges - otherwise 'it publishes now' would mean "
                              "'it tests less'"})

    # ---- S0 the tightening is the implementation, and both guard layers share one judge
    old_shape_gone = "line = m.group(0)\n            if any(ph.lower() in line.lower()" not in body
    used_in_block = body.count("if _placeholder_in_value(_matched_secret_value(rule, m.group(0))):")
    in_exemption_layer = body.count("if _placeholder_in_value(_matched_secret_value(rule, matched)):")
    check("S0_value_scoping_is_implemented_once_and_shared_by_both_layers",
          old_shape_gone and used_in_block >= 1 and in_exemption_layer >= 1,
          {"old_line_scope_expression_absent": old_shape_gone,
           "call_sites_in_content_refusal": used_in_block,
           "call_sites_in_synthetic_exemption_layer": in_exemption_layer})

    # ---- S1..S13 the ruling's examples
    for name, blob, want in CASES:
        got = verdict(base, blob)
        check(name, got == want,
              {"expected": want, "got": got, "rule_hit": rule_hit(base["_content_refusal"](blob)),
               "before_tightening_rule": old_line_scope(base, blob),
               "behaviour_changed": bool(old_line_scope(base, blob)) != bool(base["_content_refusal"](blob))}
              | ({"why": WHY[key_of(name)]} if key_of(name) in WHY else {}))

    # ---- S3b the deliverable IS a behaviour change
    hole = [c[1] for c in CASES if c[0].startswith("S3_")][0]
    before, after = old_line_scope(base, hole), verdict(base, hole)
    check("S3b_this_is_a_behaviour_change_and_not_a_relabel", before is None and after == RED,
          {"before": "GREEN (identifier washed it)" if before is None else "RED:" + before, "after": after})

    # ---- S7 both layers judge the same bytes
    probe = (('SECRET_PLACEHOLDER_IN_NAME = "%s"\nAPI_KEY = "YOUR_TEST_ONLY_VALUE"\n' % HOLE_VALUE).encode())
    refused = base["_content_refusal"](probe) is not None
    exempt = base["synthetic_fixture_exemption"]("live_checks/test_probe.py", probe)
    check("S7_the_exemption_layer_cannot_call_clean_what_the_block_layer_refuses",
          refused and exempt is None,
          {"block_layer_rule_hit": rule_hit(base["_content_refusal"](probe)),
           "exemption_layer_says": "REFUSES_TOO" if exempt is None else "ALLOWED",
           "note": "the Q23 synthetic exemption stays NOT_ENABLED"})

    # ---- S8 the refusal names a rule and never echoes the secret itself
    r = base["_content_refusal"](b'API_TOKEN = "' + CANARY.encode() + b'"\n')
    check("S8_refusal_names_the_rule_and_never_echoes_the_secret",
          bool(r) and CANARY not in r and "secret_pattern" in r,
          {"echo_probed": False, "rule_hit": rule_hit(r)})

    # ---- S10 (r3): the pinned instrument is ACCEPTED as it ships and REFUSED the moment a
    #      credential-shaped literal is embedded in those same bytes.  Both sides derive from the pinned
    #      published blob, so this cannot be satisfied by a stale file on someone's disk, and it is not a
    #      relabel either: the before-rule is reported next to the after-rule.
    subject = fetch_blob(SUBJECT_INSTRUMENT_BLOB)
    if subject is None:
        check("S10_pinned_instrument_accepted_clean_and_refused_once_a_literal_is_embedded", False,
              {"error": "pinned subject blob could not be read back - NOT MEASURED (fail CLOSED)",
               "pinned_blob": SUBJECT_INSTRUMENT_BLOB, "published_as": SUBJECT_PUBLISHED_AS})
    else:
        tampered = subject + ("\n" + 'API_TOKEN = "%s"' % CANARY).encode() + b"\n"
        clean_v = verdict(base, subject)
        tampered_v = verdict(base, tampered)
        refusal = base["_content_refusal"](tampered)
        check("S10_pinned_instrument_accepted_clean_and_refused_once_a_literal_is_embedded",
              clean_v == GREEN and tampered_v == RED,
              {"pinned_blob": blob_sha_of(subject), "bytes": len(subject),
               "published_as": SUBJECT_PUBLISHED_AS,
               "clean_verdict": clean_v, "tampered_verdict": tampered_v,
               "before_rule_on_tampered": old_line_scope(base, tampered),
               "rule_hit": rule_hit(refusal),
               "meaning": "the tightening did not open the block layer: bytes that name a credential-shaped "
                          "value are refused wherever they live, while a compliant instrument - this pinned "
                          "one and S18's own source - stays publishable"})

    # ---- S18 THIS instrument obeys the rule it tests (the self-publication contract applied to me)
    own = io.open(THIS_FILE, "rb").read()
    own_refusal = base["_content_refusal"](own)
    check("S18_this_instrument_can_be_published_by_the_guard_it_tests", own_refusal is None,
          {"own_bytes": len(own), "rule_hit_if_refused": rule_hit(own_refusal),
           "rule": "same contract as S15, applied one level down: an evidence tool that cannot publish its "
                   "own test is an evidence tool whose tests only the author can re-run"})

    # ---- S15 PUBLISHER_SELF_PUBLICATION_CONTRACT, both directions (arbiter asked for the pair)
    positive = base["_content_refusal"](raw_body) is None
    embedded = raw_body + ('\n' + 'API_TOKEN = "%s"' % CANARY).encode() + b"\n"
    negative = base["_content_refusal"](embedded)
    check("S15a_publisher_can_still_publish_itself_describing_the_hole_in_prose", positive,
          {"rule_hit_if_refused": rule_hit(base["_content_refusal"](raw_body))})
    check("S15b_publisher_source_that_embeds_a_credential_shaped_literal_is_refused",
          negative is not None and rule_hit(negative) == "ENV_SECRET_ASSIGNMENT",
          {"rule_hit": rule_hit(negative),
           "rule": "the tool must obey the rule it enforces; the contract is two-way or it is decoration"})

    # ---- S16 DEBT_1b: why evidence must not copy the detector's sentence
    echo = ('  "refusal": "FORBIDDEN_CONTENT(' + RULE_SENTINEL + ')",\n').encode()
    check("S16_evidence_quoting_the_detector_sentence_is_itself_a_detector_trigger",
          verdict(base, echo) == RED and old_line_scope(base, echo) is not None,
          {"after": verdict(base, echo), "before_rule": old_line_scope(base, echo),
           "consequence": "measured this run: my own 9,620 B receipt was refused at rc=5 / 0 PUT for "
                          "carrying that sentence. Arbiter ruling 01:3x+08 chose option 2 - no rule-name "
                          "allowlist; receipts name the rule (rule_hit) and never copy the detector text. "
                          "That is why every field above goes through rule_hit().",
           "ruling": "PUBLISHER_RECEIPT_DISCLOSURE_RULE (DEBT_1b)"})

    # ---- mutants
    flip_report, primaries = [], []
    for mname, (pairs, expect, primary) in sorted(MUTANTS.items()):
        mns = load(mutant(body, pairs))
        flipped = {key_of(n) for n, blob, _ in CASES if verdict(mns, blob) != verdict(base, blob)}
        flip_report.append({"mutant": mname, "primary_owner": primary, "declared_flip_set": sorted(expect),
                            "observed_flip_set": sorted(flipped), "surprise": sorted(flipped ^ expect)})
        primaries.append(primary)
        check("K_" + mname, flipped == expect and bool(flipped),
              {"declared": sorted(expect), "observed": sorted(flipped),
               "collateral_not_declared": sorted(flipped - expect),
               "owner_cells_not_flipped": sorted(expect - flipped)})
    check("K_mutants_have_four_distinct_primary_owners", len(set(primaries)) == len(MUTANTS),
          {"primaries": sorted(primaries)})
    check("K_no_mutant_is_a_noop", all(f["observed_flip_set"] for f in flip_report),
          {"empty_flip_sets": [f["mutant"] for f in flip_report if not f["observed_flip_set"]]})

    green = sum(1 for c in cells if c["verdict"] == GREEN)
    ok = green == len(cells)
    print(f"overall = {'GREEN' if ok else 'RED'} ({green}/{len(cells)})   publisher blob={pub_blob[:16]}...")
    for c in cells:
        print(f"  {c['cell']:<62} {c['verdict']}")
    for f in flip_report:
        print(f"  kill {f['mutant']:<52} {'KILLED' if not f['surprise'] else 'CHECK':<7} "
              f"primary={f['primary_owner']} declared={f['declared_flip_set']} observed={f['observed_flip_set']}")
    out = {"what": "PUBLISHER_SECRET_SCAN_DEBT_1 offline proof, r2",
           "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "ruling": "arbiter 2026-09-25T01:3x+08 (Q23 supplement, NOTE_1/NOTE_2, S15 contract)",
           "status": {"debt_1a_detection_tightening": "DONE",
                      "debt_1b_receipt_disclosure_boundary": "ADDED",
                      "q23_synthetic_exemption": "NOT_ENABLED",
                      "publisher_self_publication_contract": "S15a_S15b_two_way",
                      "note_1_auth_header_placeholder": "KEPT_RED_as_safety_invariant"},
           "publisher_blob": pub_blob, "publisher_bytes": len(raw_body),
           "cells": cells, "derived_result": "ALL_GREEN" if ok else "RED", "mutants": flip_report,
           "disclosure": "no field in this receipt copies the detector sentence; rule names only",
           "independence": {"network": "publisher main() never called; no transport exists in this process",
                            "filesystem": "publish_evidence.py and the r1 instrument are read, never written"}}
    path = os.path.join(HERE, "receipts", "publisher_placeholder_value_scan_r3_selftest.json")
    io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", path)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
