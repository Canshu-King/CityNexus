"""Commander's P7 acceptance checker — mechanical, deliberately hostile to easy PASSes.

Implements `P7_RESOLVER_BEHAVIOR_RECEIPT.md` (aea25cc8). A receipt passes only if every condition is
backed by behavioral evidence collected through the normal application entrypoint. Symbol presence,
grep hits, import statements, and unit-test counts are explicitly rejected as evidence kinds, because
that is exactly what fooled me twice tonight.

Usage: python p7_check.py <receipt.json> [--sha <delivery_sha>]
Exit 0 only when P7_RESOLVER_INTEGRATED may be declared true.
"""
import json, sys

BEHAVIORAL = {"HTTP_RESPONSE", "DB_STATE", "UI_STATE", "RUNTIME_REPLAY", "LIVE_REQUEST"}
BAD_EVIDENCE = {"GREP", "IMPORT", "SYMBOL", "TEST_COUNT", "SELF_REPORT"}
OUTCOMES = ("MATCH", "AMBIGUOUS", "NO_MATCH", "RUNTIME_FAILURE")

CONDITIONS = [
    ("1_unseeded_raw_via_normal_path", "prestate_no_seed + entrypoint is the product route, not a direct service call"),
    ("2_consumer_reads_typed_result", "provider_module=PhotonIdentityProvider AND product_consumer non-empty"),
    ("3_raw_vs_normalized_columns", "exact_raw and normalized_query recorded as distinct fields"),
    ("4_match_creates_server_identity", "MATCH: server-owned canonical from source_provider+source_entity_id, WGS84 legal"),
    ("5_unresolved_null", "AMBIGUOUS/NO_MATCH/RUNTIME_FAILURE all keep canonical_destination_id null"),
    ("6_durable_idempotent_replay", "operation persisted; replay adds no second identity and no mutation"),
    ("7_pending_never_identity", "no pending:/raw value used as canonical id anywhere in the receipt"),
]


def evidence_ok(block):
    kind = (block or {}).get("evidence_kind", "SELF_REPORT")
    return kind in BEHAVIORAL, kind


def check(r, sha=None):
    fails = []
    ident = r.get("identity", {})
    if sha and ident.get("delivery_sha") != sha:
        fails.append(f"identity.delivery_sha {ident.get('delivery_sha')} != requested {sha}")
    for field in ("worktree_path", "exact_test_or_replay_commands", "normal_application_entrypoint", "product_consumer"):
        if not ident.get(field):
            fails.append(f"identity.{field} missing")
    if ident.get("worktree_dirty") is True:
        fails.append("worktree dirty: commander upgrades nothing from an uncommitted tree")

    per = r.get("outcomes", {})
    for name in OUTCOMES:
        b = per.get(name)
        if not b:
            fails.append(f"behavioral receipt missing: {name}")
            continue
        ok, kind = evidence_ok(b)
        if not ok:
            fails.append(f"{name}: evidence_kind={kind} is not behavioral "
                         f"({'rejected symbol/aggregate class' if kind in BAD_EVIDENCE else 'unknown'})")

    m = (per.get("MATCH") or {})
    if m and not (m.get("source_provider") and m.get("source_entity_id") and m.get("wgs84_ok")):
        fails.append("MATCH must carry source_provider + source_entity_id + legal WGS84, else it must be a named malformed outcome")
    if m.get("canonical_created_by") not in (None, "server"):
        fails.append(f"MATCH canonical must be server-owned, got {m.get('canonical_created_by')!r}")
    if r.get("match_hashed_identity_instead") is True:
        fails.append("MATCH hashed an identity to proceed: hard fail (never fabricate canonical)")

    nm = (per.get("NO_MATCH") or {})
    for k in ("transport_contract_ok", "semantic_response_parseable", "result_count"):
        if k not in nm:
            fails.append(f"NO_MATCH missing {k}: must prove answered-empty, not HTTP/timeout")
    if nm and nm.get("result_count") not in (0, None):
        fails.append("NO_MATCH with result_count != 0 is not a no-match")

    rf = (per.get("RUNTIME_FAILURE") or {})
    if rf and rf.get("collapsed_to") == "NO_MATCH":
        fails.append("RUNTIME_FAILURE collapsed into NO_MATCH: forbidden (R14/R10)")

    att = r.get("attempts_history", {})
    if att.get("kept") != "all" or att.get("final_outcome_equals_audit_history") is True:
        fails.append("ProviderAttempt must keep every mirror attempt; final outcome != audit history")

    matrix = r.get("p7_matrix", {})
    for key, what in CONDITIONS:
        val = matrix.get(key)
        if not isinstance(val, dict) or val.get("result") != "PASS":
            fails.append(f"P7 {key} not PASS ({what})")
        elif not evidence_ok(val)[0]:
            fails.append(f"P7 {key} PASS without behavioral evidence_kind")

    stale = r.get("canary", {}).get("observation_of_stale_build") is True
    return fails, stale


if __name__ == "__main__":
    path = sys.argv[1]
    want = sys.argv[sys.argv.index("--sha") + 1] if "--sha" in sys.argv else None
    r = json.load(open(path, encoding="utf-8"))
    fails, stale = check(r, want)
    print(f"checks failed: {len(fails)}")
    for f in fails:
        print("   -", f)
    if stale:
        print("   ! canary observation came from a pre-P7 build: record STALE_CANARY_OBSERVATION")
    print("VERDICT:", "P7_RESOLVER_INTEGRATED = true" if not fails and not stale else "P7 stays FALSE")
    sys.exit(0 if not fails and not stale else 1)
