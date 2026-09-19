# Legacy E2E migration map — the eight `/` Journey Mode specs

Arbiter's ruling (pass-8, §4): do **not** swap `journey-status` for some V8
testid and call the migration done — "that is just resurrecting a selector
corpse". Archive each legacy spec only after its *capability invariant* has been
shown to exist in the current suite, and record the mapping either way.

## Why all eight fail identically

`src/main.tsx`'s `App()` renders `V8Experience` for every route and only falls
back to `LegacyApp` when the path starts with `/legacy`. The old Journey Mode
surface still exists — it was deliberately moved behind that path ("a first-time
user never lands on the legacy surface, see PHASE 2"). Each of the eight starts
with `page.goto("/")` and asserts `data-testid="journey-status"`, which only the
legacy tree renders.

Probe (temporary, reverted): pointing `golden.spec.ts` at `/legacy` made
`journey-status` resolve immediately, with `data-source="backend"` already
satisfied; the next assertion then failed on `ACTIVE` vs the real
`PLANNED · backend truth`. So the entry path is one line, and the remaining gap
is a truth-value question, not a dead surface.

## The map

| legacy spec | capability invariant it actually guards | current equivalent | status | decision |
|---|---|---|---|---|
| `golden.spec.ts` | journey state comes from backend truth, and a closure event triggers recovery that survives reload | `backend/tests/test_guardian_v4.py`, `test_impact_resolver.py`; frontend `qoder-ack-resolution.spec.ts` (ack vs resolution, self-seeded) | covered at API + rendered level | **Archive** once `/legacy` entry is recorded; keep the reload-persistence case by porting it onto the V8 Live surface |
| `live-autopilot-v5.spec.ts` | zero-touch autopilot: provider pulse → CP-SAT V2 → recovery → reload | `test_solver_v2_integration.py`, `test_solver_runtime_gate.py`, `test_agent_mission_runtime.py`; `qoder-live-structure.spec.ts` L1→L2→L3 state matrix | recovery chain covered server-side; the *zero-touch* UI trigger is not | **Port first**: needs a V8-level test that the autopilot fires without a user prompt |
| `predictive-real-city-v6.spec.ts` | predictive real-city twin prevents a weakness before it bites | `test_v13_3_real_city_intelligence.py`, `v13-5-fully-grounded.spec.ts` (fully grounded discovery, passing) | partially covered — detection yes, autonomous prevention no | **Port first** |
| `product-hardening.spec.ts:10` | TravelerTwin Control Tower renders persisted evidence and an explicit authority boundary | `test_gpt_agent_authority_v3.py`, `test_gpt_v5_mission_authority.py` | authority boundary covered server-side; the Control Tower UI is legacy-only | **Archive** the UI expectations, keep the authority assertions |
| `product-hardening.spec.ts:21` | Control Tower compiles and reloads a persisted natural-language mission | `test_agent_mission_runtime.py`, `test_gpt_v5_mission_authority.py` | covered at runtime level, not through a UI | **Archive** with a note that no current UI owns this surface |
| `product-hardening.spec.ts:46` | assisted acceptance is policy-driven; route/feed evidence survives reload | `qoder-ack-rendered.spec.ts`, `qoder-ack-resolution.spec.ts`, `test_qoder_live_replans_endpoint.py` | covered, and covered *in the current product surface* | **Archive** |
| `product-hardening.spec.ts:172` | autonomous mode executes an envelope-safe recovery through the Agent Gateway | `test_gpt_agent_authority_v3.py`, `test_agent_runtime_gate.py` | gateway + envelope safety covered server-side | **Port first** if the V8 shell is meant to expose autonomous mode; otherwise archive |
| `product-hardening.spec.ts:251` | Proactive Guardian launches the flagship recovery without a new chat prompt | `test_guardian_v4.py`, `test_guardian_model_evidence.py`, `test_v10_flagship_e2e.py` | covered | **Archive** |

## Rules applied

- An invariant is "covered" only when something in the **current** suite asserts
  it against the **current** surface or API — not when a similarly-named old test
  exists.
- Where the capability is real but only the legacy UI asserted it visually, the
  decision is *port first, then archive*, so retiring the file never deletes a
  behaviour check.
- The four current-product specs (`product-v8` ×2, `real-world-trip-operations-v9`,
  `v10-live-execution`) are **not** in this file's archive list. Per the same
  ruling they stay in the default suite and get rewritten against today's V8
  behaviour; work so far: locale pinned (they assert English copy while the app
  follows `navigator.language`), the retired `hub.title` heading replaced by
  `today-heading`, `AI` → `Copilot`, `read-only ready` → the current
  `exec.readOnlyReady` value `available offline`, the hard-coded four offer cards
  turned into a logged branch, and the AgentComposer testid replaced by the
  Copilot dock.
- Correction (pass-11 disproved the original note in this file, which claimed
  those v10 specs "pass alone but fail in the serial full run because the suite
  shares one SQLite file"). That hypothesis is **false** and the database has
  been cleared of it: re-running the failing specs individually on the same HEAD
  and the same seed reproduced the identical failures. The real causes are
  contract drift and unfinished fixture ownership —
  `v10-live-execution` was simply the last spec of the family not yet owning its
  journey (fixed in pass-12 A), `product-v8` drives a Copilot submit control that
  has since changed shape, and `real-world-trip-operations-v9` drives the raw
  JSON workbench that is now deliberately hidden behind an Advanced/developer
  disclosure while `JourneyInboxWorkbench` is the consumer path. No reordering,
  no retries, and no database-harness change is warranted; the arbiter closed
  `TEST_INFRA_SHARED_DB_BLOCKER` and marked `PER_WORKER_TEMP_DB` as
  NOT_AUTHORIZED.
