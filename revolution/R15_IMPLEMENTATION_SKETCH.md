# R15 implementation sketch — shortest path to real truth-seeking

This is not a design requirement. It is a map of the shortest code path discovered during GPT external review.

## 1. Fix the caller-identity bug before autonomous URLs

Current call chain:

```text
AgentToolGateway.acquire_place_facts(request.source_url)
 -> acquire_place_facts(source_bindings=...)
 -> _requested_fact_source_binding()
 -> OPERATOR_CONFIRMED_EXACT_PROVIDER_ENTITY
 -> OPERATOR_VERIFIED
```

An AgentToolCall is not an operator receipt.

Suggested minimal contract change:

- distinguish binding origin at the server boundary;
- human/user-approved route may create `OPERATOR_BOUND_EXACT_ENTITY`;
- Agent gateway may only create `AGENT_SOURCE_CANDIDATE`;
- provider/Nominatim exact website tag creates `PROVIDER_BOUND_EXACT_URL`;
- only deterministically corroborated candidates may become `CORROBORATED_OFFICIAL_SOURCE`.

Do not let a client/model pass an enum that self-selects `OPERATOR_VERIFIED`; the server decides from authenticated/call-path identity.

Minimum regression:

```text
AgentToolCall(source_url="https://arbitrary.example")
 -> no OPERATOR_VERIFIED
 -> no matched_provider_entity=true invented by the request
 -> no canonical opening/cost promotion solely from that binding
```

## 2. Exploit the autonomous path that already exists

`fact_acquisition.py` already has a strong automatic lane:

```text
exact Place external_id
 -> fresh Overpass tags
 -> Nominatim exact lookup
 -> source_url from exact tags/extratags
 -> URL equals exact provider website tag
 -> source_binding approval=PROVIDER_TAG_EXACT_URL
 -> safe official fetch
 -> opening/cost promotion
```

Use this first.

R15 does not need a universal source-discovery engine to close REVOLUTION_A/B. Pick candidate Places whose exact provider rows expose usable official URLs, and let the Agent discover that from the normal catalogue/tool result.

The Revolution behavior is still real because the Agent chooses which Place/fact to investigate; the truth comes from the provider-bound URL.

## 3. Add candidate corroboration only after the exact-tag lane

Existing `_search_fact_candidates` already returns sourceful `SEARCH_CANDIDATE` observations.

If the exact provider tag path is insufficient, add a bounded corroboration operation instead of promoting search output directly.

Conservative first version:

```text
search candidate URL
 -> safe URL validation / SSRF gate
 -> exact provider entity known
 -> fetch page
 -> require deterministic corroboration signal
 -> only then source binding
```

Acceptable corroboration signals for the first general implementation may include:
- exact provider website/contact URL equality after normalization;
- exact official entity identifier echoed by the page/API;
- exact provider-tag URL redirects to the candidate;
- existing specialized exact-ID API bindings such as the Lotsmall path.

Do not use fuzzy same-name alone as authority.

## 4. Turn estimate_place_facts into VOI evidence only

Keep the tool; it is useful.

But in the R15 success run:
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- estimate values may help the Agent choose a Place/source;
- estimates must not satisfy `plan_authority_blocker`;
- canonical Place rows remain the sole normal selection truth.

Consider returning a compact field such as:

```json
{
  "decision_support_only": true,
  "authority_eligible": false,
  "estimated_information_value": ...
}
```

Do not invent a precise numeric VOI unless it is actually computed from candidate sensitivity. A simple ordinal HIGH/MEDIUM/LOW is fine.

## 5. Minimal truth-seeking loop

Do not build a new orchestration framework first. The existing tool loop can express the R15 behavior.

A good model path is:

```text
inspect_journey
inspect_twin
search_city_services
generate_plans / inspect provisional blockers
choose Place with decision-sensitive UNKNOWN
acquire_place_facts
inspect returned canonical counts/provenance
if still UNKNOWN:
    abandon or investigate another provider-bound source
generate_plans
repeat until selectable under normal gate
```

If needed, add one compact tool that summarizes candidate blockers/value-of-information. Prefer that over sending the model megabytes of raw catalogue state.

## 6. c9 runtime hardening: only if live preflight needs it

Current `_merge_sse` drops stream `finish_reason`. Therefore an empty streamed response is retried as budget exhaustion even when the provider may have ended it for another reason.

Small fix shape:
- preserve final streamed finish_reason;
- return it alongside/inside the merged message;
- same-model 2400 retry only for `length` or actual reasoning-only exhaustion;
- provider-empty/content-filter/invalid stream should follow their own fallback/error path.

Also impose a user-facing AgentRun total wall-clock deadline if the live mission can still sit for minutes per failed model turn. Keep it configurable and record a named failure receipt.

Do not make runtime work the R15 milestone.

## 7. R15 acceptance regression set

High-value tests only:

1. Agent-supplied arbitrary source URL cannot manufacture operator approval.
2. Exact provider/Nominatim website URL can become PROVIDER_BOUND_EXACT_URL and promote verified facts.
3. SEARCH_CANDIDATE cannot promote by itself.
4. With lab estimate authority OFF, an estimated-only Place remains non-selectable.
5. After canonical fact acquisition for every used Place, the same normal plan becomes selectable.
6. Live used-edge mobility remains required.
7. Replan replacement Places must pass the same canonical fact boundary.
8. One end-to-end fresh-city run reaches COMPLETED without enabling lab estimate authority.

## 8. Do not regress into evidence work

Once one canonical truth path works, use it on a real Journey immediately.

Do not spend hours generalizing source corroboration before the first R15 authority closure. Close one real loop, then generalize only what the second city proves is necessary.
