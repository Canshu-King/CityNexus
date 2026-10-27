# Explicit source research: Hangzhou published, Nanjing remains blocked

Product `6927f06d94bfe8e605e8bbc0881d01db9599a2c4` adds signed `POST /journeys/{journey}/agent/goal-tasks/{task}/research-places`. It reuses the existing Amap research, district, ProviderCall and canonical materialization services. A person can explicitly acquire public places without a working model. The route requires the current signed owner, DRAFT, task online-source consent, JSON `provider_consent: true`, and an idempotency key. WORKING, wrong scope, absent consent and conflicting keys are refused. It preserves model status/usage and creates no AgentRun or AgentRunStep. Public response fields are allowlisted; audit identifies the traveler as actor.

Root focused signed/source/preparation regression: **30 passed, 4 warnings, exit 0**, isolated SQLite. New path is present in both formal YAML and actual runtime OpenAPI. The repository-wide parity utility remains NOT PASS (125 missing / 8 extra); its route walk also misses nested APIRouter paths, including pre-existing preparation/freezing routes. No broad contract rewrite is claimed.

## Same owned database, actual native operations

The owned helper was normally stopped/resumed with the same DB/auth, backend product SHA above, ports 14522/60622. Explicit live-discovery switches were enabled only in that isolated process (`CITYNEXUS_REAL_CITY_ENABLED=true`, `CITYNEXUS_REAL_CITY_MODE=live`). Before this, four Nanjing requests returned REAL_CITY_DISABLED without provider calls; those receipts are retained. There were no new model attempts: AgentRun count stayed **39**. Map ProviderCall count increased **88 → 107** (two district calls, eight place queries, nine walking calls).

| City | Native identities | Acquired POI / valid geometry routes | Publication |
| --- | --- | --- | --- |
| Beijing 110000 | Previous verified native supply | 40 / 3 | Previously published |
| Hangzhou 330100 | Journey `44345072-082c-42a0-be2b-e1f1d6dc3fa0`, task `9def16ac-d6d1-4abb-88de-cedacb3c1c86` | 32 / 3 | Native POST 200; SHA `291cf04d7cfd55d3621f283c3e36132ada30d3e992a589732b42c25320f54885` |
| Nanjing 320100 | Journey `1da284d4-a9c6-4214-8a41-307a1419c475`, task `f37d1870-b419-49f5-a814-5b473ec8c29b` | 32 / 2 | Native POST 409 CITY_SNAPSHOT_INCOMPLETE |

Signed seed 17 and seed 0 reads both report **eligible_city_count=2**, overall **BLOCKED / THREE_ACQUIRED_CITIES_REQUIRED**. The cities have independent provider district receipts, different POI identities and actual coordinates. No Beijing facts were relabeled.

Hangzhou's manual four-stop candidate `7065b549-fd71-4f8d-86db-2573611a9bf0` has 12/05 断桥残雪 + 岳王庙, 12/06 浙江省博物馆孤山馆区 + 西泠印社社址. Native draft PUT200 → prepare201 → city binding200 → freeze200 (3/3) → publish200. Snapshot `94c6236a-68d4-4833-8899-bd70a9fd6186` carries three real walking shapes. The task declined model use and consumed zero model turns. Its PlanVersion remains CANDIDATE and every stop PLANNED; unknown opening/admission facts remain unknown.

## Nanjing: retain the actual refusal

Initial candidate `f2a9feca-e247-4963-9ef2-caa6a74ab521` uses 南京博物院 / 总统府 / 南京夫子庙 / 玄武湖景区. Two real walking replies have segment junction gaps **1.0143m / 1.0140m**, above the existing ≤1m continuity policy; their geometry stays BLOCKED_GEOMETRY_DISCONNECTED. 总统府→南京夫子庙 is valid (119 WGS84 points). Duration freezing does not establish geometry eligibility.

One explicit alternative candidate `ac1c039b-4274-4a37-ab5b-4024206916fe` was prepared from already acquired different venues: 总统府 / 南京夫子庙 / 南京市博物馆 / 南京城墙台城景区. Its old candidate is preserved; neither was active or booked. A new 市博物馆→台城 route is valid, but 夫子庙→市博物馆 has a **1.0144m** junction gap and remains blocked. No continuity threshold was widened and no coordinates were inserted to make publication pass. No further alternative/provider requests were made.

This alternative exposed an existing cache identity mismatch: Activity.source_candidate_id was canonical while stored research_routes used provider IDs. Native freeze therefore remeasured **one previously successful 总统府→夫子庙 pair**. Both ProviderCalls `01bed1e6…` and `231cdd37…` are retained. This is not claimed as exactly-once measurement; normalize the server-owned canonical/provider alias before further freeze work. No old Beijing route or failed model request was repeated.

## Receipts and next step

- `20261026_HANGZHOU_NATIVE_CITY_SUPPLY.json`: actual signed HTTP, independent city source, native plan and published geometry.
- `20261026_NANJING_NATIVE_CITY_SUPPLY.json`: both real candidates, provider receipts and preserved failures.
- `20261026_TWO_CITY_POOL_HTTP.json`: final signed reads for two seeds, with Nanjing's 2/3 gap explicit.
- `20261026_TYPED_CITY_RESEARCH_SUMMARY.json`: source calls, geometry statuses, identities and final counts.

No browser/device acceptance or new completed simulation run is claimed. Next code task is the canonical/provider cache-key mismatch, before any further paid measurement. Then obtain a genuine third reliable Nanjing edge without repeating the recorded pairs or changing the geometry gate. Classroom same-run two-day execution, live Guardian acceptance and physical-device USER_VERIFIED remain separate open gates.
