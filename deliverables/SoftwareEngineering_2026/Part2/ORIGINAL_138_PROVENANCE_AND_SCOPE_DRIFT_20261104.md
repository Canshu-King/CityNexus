# CityNexus Original Requirements Provenance and Scope Drift Review
**Date:** 2026-11-04 · **Purpose:** Coursework Part 2 requirement accuracy review.
**Evidence level:** GitHub source history and surviving Moodle project conversation context. This is not a recovered verbatim ChatGPT transcript.

## 1. Original 138-source recovery (verified)

1. `096d857a4fefba272c2f535ac6c67077ef0c596c` (2026-09-04 17:07 UTC): `requirements/requirements.yaml` was an infrastructure-only 0.1.0 stub; all six requirement lists were empty.
2. `072e84f0bde4e02b95835fe3eceb8d06502d3ccb` (2026-09-04 18:02 UTC): commit titled **feat(requirements): establish CityNexus requirements baseline v0.3**. This imported the first repository full 138 formal requirements with the breakdown 8 BG / 61 FR / 24 BR / 16 NFR / 14 SR / 15 IR. The requirements CHANGELOG describes this as imported from a previously prepared 138-item *proposed* baseline; it does not identify the original ChatGPT chat.
3. The `requirements/requirements.yaml` Git blob at the initial 2026-09-04 commit and at the 2026-11-04 Part 2 branch **is identical**, `f564bf23c6bacc38ce2beb37335df49fe4add1dd` (131,654 characters as returned by the GitHub connector). The v0.3 source content has not been silently rewritten.
4. Original `requirements/README.md` explicitly states the teacher/customer has **not** approved the baseline. `requirements/BASELINE.md` says `Baseline Candidate` and warns that future semantic changes require a new version/change log/updated traceability.
5. Original use cases `use-cases/use-cases.yaml`, version 0.1.0, were committed on 2026-09-04 and cover 13 top-level user goals.

Canonical URLs:
- Original 138 exact file: https://github.com/Canshu-King/CityNexus/blob/072e84f0bde4e02b95835fe3eceb8d06502d3ccb/requirements/requirements.yaml
- The import commit: https://github.com/Canshu-King/CityNexus/commit/072e84f0bde4e02b95835fe3eceb8d06502d3ccb
- Original requirements changelog: https://github.com/Canshu-King/CityNexus/blob/072e84f0bde4e02b95835fe3eceb8d06502d3ccb/requirements/CHANGELOG.md
- Original 13 use cases: https://github.com/Canshu-King/CityNexus/blob/e3b787580d181b7335df63933683294c6b884f84/use-cases/use-cases.yaml
- Original domain model: https://github.com/Canshu-King/CityNexus/blob/d5236d9022799ad493a836e1bc1a277969c125cc/domain-model/citynexus-core-domain-model-v0.4.2.yaml

## 2. Original project intent that is demonstrably in 138

The eight original business goals are:
- BG-001 Maintain an Executable Journey
- BG-002 Reduce Journey Tool Fragmentation
- BG-003 Recover from Real-World Disruption
- BG-004 Protect High-Strength Commitments
- BG-005 Deliver Context-Aware Personalisation
- BG-006 Unify Actionable City Services
- BG-007 Explain Intelligent Decisions
- BG-008 Keep External Providers Replaceable

The original v0.3 already contains:
- journey setup, constraint and plan-generation, one active immutable PlanVersion (FR-006..FR-016);
- real-source place search/route availability and recommendations (FR-018..FR-028, IR-001..IR-005);
- booking/order/payment/receipt workflows (FR-032..FR-038), regardless of whether these later shipped;
- context and event-based disruption detection plus progressive local/window/global recovery and human acceptance (FR-039..FR-053);
- natural-language preference extraction, grounded AI explanation, AI-degraded operation and audits (FR-054..FR-059);
- mobile usability, security, privacy and provider resilience (NFR / SR / IR).

**Interpretation:** dynamic replanning and real-context sensing are NOT inherently post-baseline additions. The agent's broad mission was seeded early, but exact extent of autonomous operations must not be retrospectively ascribed to the 138 items.

## 3. After-baseline expansion, not a rewrite of v0.3

Later Revolution documentation includes `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md` (post-R42), which explicitly reframes the North Star as *"Handle this trip for me"*: ongoing agent judgment, tools, observing real-world change, coordinating fellow travellers, approvals and continued execution. These are later product aims:
- **Continuous Autonomous Journey Operator**: extends FR-054..FR-059/UC-11 beyond interpreting preferences/explaining recommendations to a continuously managing agent; must be distinguished from original obligation to preserve human authority.
- **Group/collective trip coordination**: substantial new actors, membership and consensus/authority requirements; no dedicated group member/group journey use case or matching FR namespace in the original 13 use cases. May extend UC-02/UC-08/UC-10, but it is not explicitly specified in v0.3.
- **First-person GO MODE Pocket Walk and change second stop**: R108 documented authenticated, revision-bound, user-self-reported two-stop state, explicitly NOT physically verified; R109 taskbook proposed a member-private pivot. This is more specific than original UC-08 execution and must not be described as GPS-backed fact.
- **Agent tool trace UI, live status and developer-style session transparency**: sensible extension of explanation/audit/usability requirements but absent as a specific original acceptance criterion.
- **Demonstration virtual time/location/instant multi-day replay**: discussed in later user conversations, not expressed as original baseline's normative requirement.

Sources for later evolution:
- https://github.com/Canshu-King/CityNexus/blob/gpt/revolution-r33-open-world-journey-adaptation/REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md
- https://github.com/Canshu-King/CityNexus/blob/gpt/revolution-r33-open-world-journey-adaptation/REVOLUTION_R108_POCKET_WALK_GO_MODE_RESULT.md
- https://github.com/Canshu-King/CityNexus/blob/gpt/revolution-r33-open-world-journey-adaptation/REVOLUTION_R109_GO_MODE_STREET_PIVOT_TASKBOOK.md

These are branch-level evidence, **not** a verified current-production integration, physical arrival proof, or original teacher-approved requirements.

## 4. Gaps and coursework recommendation

- The GitHub record proves the original 138 entered the repository on 2026-09-04 but does not reveal the ChatGPT conversation or offline source where the 138 were first drafted. The earliest surviving shared-project conversation snippets available to this reviewer start later. Do not assert a specific original conversation/title/date without its transcript.
- Preserve the v0.3.0 formal baseline untouched as an appendix/evidence reference. The Part 2 SRS must not call it an approved final delivered-product spec or imply every BG/FR/BR/NFR/SR/IR was fully implemented.
- Classify each original requirement with **retained / implementation-evidence pending / deferred** at course scope; add a small **post-baseline change log** for continuous autonomy, groups, execution, realistic demo modes if included.
- Particularly do not omit original commerce FR-032..FR-038 without explaining deferment, because these are part of v0.3 even if product effort later shifted elsewhere.
- For the final <=20-page PDF, use a brief scope-evolution paragraph rather than trying to squeeze a full new 138-item matrix inside.
- If the user finds the original ChatGPT conversation, use it as a separate source and update this provenance report without silently rewriting the original candidate baseline.

**Review verdict:** The 138 original requirements are preserved byte-for-byte. The main coursework risk is an **implementation/scope divergence and evidence-coverage gap**, not missing or modified original requirements.
