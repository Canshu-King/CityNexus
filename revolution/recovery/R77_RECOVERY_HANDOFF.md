# Revolution R77 recovery handoff

This branch is a capability-recovery staging point pinned from product tip `4ee14229f80691cf8e5ea913375c0caf83ac02ee`.
It deliberately does **not** modify product code. Codex should resolve the current authority tip once, create one capability branch, and implement from there.

## Why this exists

The isolated Revolution Lab R7.6/R7.7 line already proved a real path on a fresh disposable DB:

`贡山独龙族怒族自治县 -> Photon OSM:R:2729765 -> real Overpass park + viewpoint -> Nominatim exact identity -> LIVE Valhalla 52/53 min -> HTTP 201 CANDIDATE selectable=false -> select HTTP 409 UNRESOLVED_ACTIVITY_FACTS -> active_plan_version_id=null`.

That work never reached the later authority product tree. At the observed authority tip:
- no `backend/app/fact_acquisition.py`;
- no `backend/app/agent/autonomous_travel.py`;
- no R75/R76/R77 regression modules;
- no `/facts/acquire` or `/agent/autonomous-plan` endpoint;
- no R77 `PROVISIONAL_UNRESOLVED_FACTS` / `UNRESOLVED_ACTIVITY_FACTS` flow;
- Overpass mirrors still lack `overpass.openstreetmap.fr`;
- the preparation UI still uses the older READY-sounding wording.

## Mission, not ORD loop

One capability branch. No branch-per-bug and no new micro-ORD numbering.

Close the strongest truthful milestone possible, in order:

1. **REAL_DRAFT_CLOSED**: an unseeded real destination creates a persisted provider-backed candidate with >=2 visit-eligible real Places, exact identity evidence and LIVE used-edge mobility. Missing facts stay explicit and non-selectable.
2. **REAL_SELECTABLE_CLOSED**: a previously unseeded destination has independently verified opening/cost facts for the used Places, becomes selectable, selection succeeds, and the Journey reads back the active plan.
3. **REAL_AGENT_CLOSED**: a configured real agent runtime performs a persisted PLAN_ONLY run on that same real Journey with actual CityNexus tool calls and truthful provenance.

Do not stop after rediscovering a known blocker when a truthful pivot is available.

## Port rules

Do not apply the old R77 tree wholesale. Current files are newer.

- Current `backend/app/agent/runtime.py` wins. It already has the newer DeepSeek PLAN_ONLY runtime and 11-tool allowlist. Port only missing integration hooks.
- Current `main.py`, `schemas.py`, `services.py`, provider code and tests win structurally. Port R77 behavior surgically.
- Add provisional fallback only when strict failure is specifically incomplete opening/cost truth and >=2 real visit-eligible provider Places exist.
- Strict authoritative planning remains fail-closed.
- Search snippets are `SEARCH_CANDIDATE` leads, never authority.
- `CATALOG_PREPARED` means preparation finished, not READY/SELECTABLE.
- Never use parking/hotel rows as fake attractions to reach a count.
- Never let UNKNOWN cost become FREE because compatibility storage contains zero.

## Two R77 defects to fix during recovery

1. R77 `fact_acquisition.py` closes its `httpx.Client` after Overpass/Nominatim, then later reuses that closed client for official-web and SearXNG calls. A real client raises `RuntimeError: Cannot send a request, as the client has been closed.` Fix lifetime management and add a regression whose client actually becomes unusable after `__exit__`.
2. R77 server-fetches provider-tag `website/contact:website/url`. Before mainline use, add SSRF protection: reject private/loopback/link-local/reserved targets, validate DNS results, and revalidate every redirect.

## Execution discipline

- Resolve current authority tip once and branch from it.
- Baseline touched focused suites plus one broad candidate-vs-base comparison.
- Spend the majority of work implementing and executing the real user path, not reviewing historical evidence.
- Rebase at most once after implementation starts. If authority moves again, finish a coherent candidate and report the base SHA.
- One final result report and one compact evidence directory.

## Real selectable closure

Try Gongshan first because R77 proved the draft path. Use safe, operator-approved source discovery and official-page verification.

If the exact Gongshan entities genuinely have no verifiable opening/cost facts, pivot to another previously unseeded destination with >=2 real provider Places and verifiable official facts. The goal is to prove the general capability, not remain emotionally attached to one county.

Acceptance:
- exact source provenance for every used fact;
- no UNKNOWN interpreted as open/free/zero;
- LIVE eligible used-edge mobility;
- plan truthfully selectable;
- select succeeds;
- `Journey.active_plan_version_id` points to the selected plan;
- reload/readback proves persistence.

## Agent

Only after the trip works. Reuse current agent runtime.

If a real runtime is configured, run one PLAN_ONLY mission:
- persisted `AgentRun` + tool steps;
- first action inspects state;
- model prose supplies no authority fact;
- no mutation in PLAN_ONLY.

If Hermes is unavailable, record the exact runtime gap once and continue product work. Do not build another harness bureaucracy just to make a box green.

## Final deliverable

Create `REVOLUTION_REALTRIP_RECOVERY_RESULT.md` with:
- base/final SHA;
- milestones actually closed;
- destination;
- exact used Place IDs and source URLs;
- used mobility provenance;
- select response and active-plan readback;
- agent run/tool sequence if executed;
- focused tests and broad candidate-vs-base delta;
- only remaining genuine external blockers.

The success criterion is simple: the authority product can do something materially new that it could not do before this branch.