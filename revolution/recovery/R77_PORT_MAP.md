# R77 -> current authority port map

Observed product authority tip during preparation: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`. Codex must resolve the current authority tip once before implementation and continue from there.

## Missing from observed authority tree
- `backend/app/fact_acquisition.py`
- `backend/app/agent/autonomous_travel.py`
- `backend/tests/test_r75_provisional_product.py`
- `backend/tests/test_r76_fact_acquisition.py`
- `backend/tests/test_r76_provisional_refresh.py`
- `backend/tests/test_r77_search_source.py`
- `frontend/src/features/agent/AutonomousTravelPanel.tsx`
- R77 `/facts/acquire` endpoint
- R77 `/agent/autonomous-plan` endpoint
- R77 `PROVISIONAL_UNRESOLVED_FACTS` / `UNRESOLVED_ACTIVITY_FACTS` flow

## Existing files are newer and must win structurally
- `backend/app/agent/runtime.py`
- `backend/app/anywhere_capability.py`
- `backend/app/catalog_hydration_operations.py`
- `backend/app/core/config.py`
- `backend/app/integrations/discovery/real_city.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/services.py`
- current frontend API/composer/preparation files

Port R77 behavior surgically into those newer owners. Never replace current `main.py`, `services.py`, `schemas.py` or agent runtime with R77 snapshots.

## Confirmed semantic gaps at the observed authority tip
- strict planner still exposes `CATALOG_INSUFFICIENT` and `PLACE_COST_UNVERIFIED` without the R77 provisional fallback;
- current Overpass mirrors did not include `overpass.openstreetmap.fr`;
- current preparation UI still had READY-sounding wording equivalent to “准备好了，可以去规划”;
- no R77 fact-acquisition subsystem;
- no R77 autonomous panel.

## Required port order
1. provider/discovery resilience + reuse of materialized real catalog;
2. fact acquisition with fixed client lifetime and SSRF safety;
3. provisional persisted PlanVersion fallback only for incomplete-fact strict failures;
4. truthful prepared -> draft UI;
5. fresh-DB real path proving REAL_DRAFT_CLOSED;
6. fact promotion to REAL_SELECTABLE_CLOSED, pivoting to another unseeded destination if Gongshan exact entities have no verifiable facts;
7. real PLAN_ONLY agent run only after the trip itself works.

One capability branch, one result report, one compact evidence directory. No branch-per-bug.