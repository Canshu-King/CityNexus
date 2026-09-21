# CityNexus Accessibility Evidence Mapping Policy

Status: arbiter contract note for Harness/C/F lane implementation of the d6b accessibility finding.

## 1. Decision

Choose **A: add an explicit OSM-tag-to-canonical-accessibility-evidence mapping layer**.

Do not require a second LIVE observation merely because the source fact arrived as an OSM tag.

The current defect is not "no evidence exists". It is "the product does not understand a supported evidence shape".

This does **not** mean `UNKNOWN == ACCESSIBLE`.

It means:

> An explicit provider assertion such as `wheelchair=yes` is evidence for the exact accessibility predicate it encodes, once normalized with provenance. Missing, ambiguous, or conflicting tags remain UNKNOWN/CONFLICT.

## 2. Canonicalization boundary

Raw provider tags must be normalized before `evaluate_feasibility`.

Preferred shape:

```text
raw provider record
-> accessibility evidence adapter
-> canonical accessibility predicates + provenance
-> hard-feasibility policy
```

The planner must not parse OSM tag dictionaries ad hoc.

The frontend and LLM must not interpret raw OSM tags independently.

## 3. Provenance is mandatory

Do not invent a fake LIVE class merely to make the gate pass.

Use the existing CityNexus provenance vocabulary where possible.

For provider-backed OSM/Overpass facts, record at least:

- source_provider: OPENSTREETMAP / OVERPASS (use the repository's existing provider identifier)
- source_entity_id
- source_kind according to acquisition mode:
  - REMOTE_PROVIDER when fetched from the live provider path;
  - OFFLINE_SNAPSHOT or GOLDEN_FIXTURE when the fact came from a frozen/local snapshot;
- source tag key/value used for the mapping;
- observed_at/fetched_at when known;
- fact_quality according to the existing server-owned evidence policy;
- mapping/derivation identifier such as `OSM_ACCESSIBILITY_TAG_MAP_V1`.

Do **not** add a new source_kind called `OSM_TAG_INFERRED` if that would duplicate the existing provenance enum. The mapping is a derivation rule; source_kind should describe where the fact came from.

## 4. Predicate-scoped mapping

A provider tag may satisfy only the predicate it actually supports.

Minimum v1 behavior:

- `wheelchair=yes`
  - canonical predicate: wheelchair access supported;
  - may satisfy a hard wheelchair-access requirement if provenance/freshness is policy-eligible.
- `wheelchair=no`
  - canonical conflict for a hard wheelchair-access requirement.
- `wheelchair=limited`
  - partial/limited evidence;
  - must not silently become full wheelchair access.
- tag absent or unrecognized
  - UNKNOWN, not accessible.
- explicit structural conflict such as `highway=steps`
  - remains conflict under the existing conflict-priority rule.

Do not infer unrelated predicates from one tag.

For example, `wheelchair=yes` must not automatically invent:

- accessible toilet;
- lift availability;
- tactile paving;
- accessible parking;
- assistance staff;
- any other predicate not encoded by the evidence policy.

If CityNexus defines a broader relationship such as "wheelchair=yes implies step-free entrance" in a versioned policy, that relationship must be explicit, tested, and server-owned rather than assumed by callers.

## 5. Conflict precedence

When positive and negative evidence collide, do not hide the contradiction.

Required order:

1. explicit conflict / negative evidence;
2. explicit positive evidence;
3. unknown.

A conflict must remain visible in details/provenance.

The existing `ACCESSIBILITY_CONFLICT` behavior is a positive regression anchor and must stay green.

## 6. LIVE is not the same thing as valid evidence

The evidence policy must distinguish:

- acquisition mode;
- freshness;
- predicate support;
- hard-feasibility eligibility.

An OSM fact can be legitimate provider evidence without being "live right now".

Conversely, a live response does not automatically make every tag hard-eligible.

The server-owned evidence policy decides eligibility.

## 7. d6b acceptance gates

Use the measured 16 places x 6 hard-requirement phrases as the fixed corpus.

Required results:

1. Existing canonical metadata:
   - `metadata_json.accessibility={step_free:true,wheelchair_access:true}`
   - remains accepted where it was already accepted.
2. Existing verified shape:
   - `evidence_status=ACCESSIBILITY_VERIFIED`
   - remains accepted where already accepted.
3. OSM explicit positive:
   - `{"tags":{"wheelchair":"yes"}}`
   - is no longer classified as "missing evidence" for the matching wheelchair predicate.
4. Missing/unrelated tags:
   - remain UNKNOWN / NEEDS_EVIDENCE;
   - must not become accessible by default.
5. Explicit conflict:
   - `{"tags":{"highway":"steps","step_count":"12"}}`
   - remains `ACCESSIBILITY_CONFLICT`.
6. Limited:
   - `wheelchair=limited`
   - never mutates to full positive evidence.
7. Provenance:
   - every accepted OSM-derived predicate carries source identity and derivation information.
8. Mutation:
   - remove/bypass the OSM mapping layer -> the positive OSM corpus must go red;
   - change unknown-tag behavior to "accessible" -> tests must go red;
   - ignore conflict precedence -> tests must go red.

## 8. User-visible semantics

If evidence is explicit and policy-eligible, the UI may say the relevant accessibility feature is supported and cite/provider-label it appropriately.

If evidence is UNKNOWN, the UI should say that accessibility evidence is not verified/available, not that the place is inaccessible.

If evidence conflicts, explain the conflict rather than collapsing it into "missing evidence".

## 9. Relationship to R5 hard-feasibility

Accessibility uses the same umbrella principle as R5-M/R5-T:

> A hard requirement may pass only when the exact fact it relies on has policy-eligible evidence.

But accessibility keeps its own typed reason codes and evidence schema. Do not squeeze wheelchair evidence into mobility-leg or opening-hours fields merely to reuse a generic gate.
