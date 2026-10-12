# Revolution R58 — Split-Group Recovery Negotiator

## Product result

CityNexus can now explain the difference between keeping a shared itinerary intact so one traveller can catch up and explicitly asking the system to prepare a group-wide recovery. A plan-changing action starts one durable, `PLAN_ONLY` Hermes mission; it never silently accepts a plan or treats browser location as verified physical presence.

Implementation commit: `d6926613202ec380c954c1aa3c776c421f9ebd44`

Branch: `gpt/revolution-r33-open-world-journey-adaptation`

`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

## One bounded fresh strike

The run used a fresh disposable SQLite database and recreated the seeded coursework Journey through the product reset/plan/select/start APIs. The seed assigns a stable Journey UUID, so the identifier is reused across isolated databases; this run's rows and lifecycle were fresh.

| Fact | Result |
|---|---|
| Journey | `22222222-2222-4222-8222-222222222222`, `ACTIVE` |
| Owner member | `47f4bcd4-d9cb-52a8-a586-b47f4bcd4d9cb` |
| Companion member / traveler | `fbe30936-724e-4b96-820b-959501ae42ba` / `1a3dbcce-116e-4db0-b1ce-37d3b77875fe` |
| Active PlanVersion before / after | `55523d40-cafe-5bd2-b30a-de057ec7a839` / same |
| Shared protected stop | `Old Town Gate` (`3a58c470-524c-5854-aa39-6c37a350eb80`) |
| Presence authority | `FOREGROUND_WEB` coursework inputs — advisory, not device-attested |
| Route operation | `ba5f4b8f-7c8e-49a0-a472-39757dd957d6`, `COMPLETED` |
| Route evidence | `valhalla-http`, `LIVE_PROVIDER_CAPTURE`, 61 minutes walking |
| Risk projection | `ADVISORY_MEMBER_LATE`, −59 minutes after the protected buffer |
| Pre-existing authoritative member-risk Event / Guardian handoff | none / 0 |
| User escalation Event | one `USER_CHANGE` (`journey-group-recovery-request`) |
| Hermes mission | `901f7828-c3ea-4b24-b1d5-bebfd4480a51`, `FAILED_EXTERNAL` |
| AgentRun / proposal / collective decision | none / none / not reached |
| Active-plan mutation count | 0; plan pointer unchanged |
| Physical execution evidence | none; API state only |

The foreground locations were deliberate coursework inputs around a seeded demo stop, not real travellers' device locations. Valhalla supplied a current route calculation, not live traffic conditions. The route's provenance is therefore reported exactly as captured and is not described as live traffic. The public demo endpoint is documented by the [Valhalla project](https://github.com/valhalla/valhalla#demo-server).

The user-visible “Adjust together” action was invoked once. The current app process had no configured/ready native Hermes runtime, so CityNexus durably recorded `NATIVE_HERMES_UNAVAILABLE_FOR_GROUP_RECOVERY`, stopped before an AgentRun, and left the itinerary untouched. This is the taskbook's honest external-blocked outcome; it is not a claim that WB2api is unusable, and no WB2api/provider configuration was changed.

## Verification

- R57/R58 backend focused tests: **15 passed**.
- Python application compile check: passed; R58 strike script `py_compile`: passed.
- Frontend TypeScript check: passed.
- Vite production build: passed (existing large-chunk advisory only).
- Focused Playwright: **2 passed**, including the R58 “keep plan” versus “adjust together” interaction.
- `git diff --check`: passed.

## Remaining boundary

The new product surface and durable escalation path are implemented and locally verified. Full Agent-mediated recovery remains open until a native Hermes MCP runtime is configured and ready; no proposal was generated or accepted in this strike. The disposable run database is `backend/_r58-product-strike-20261007-81937dac35c847238ecdc91cfc0139b5.sqlite3`.
