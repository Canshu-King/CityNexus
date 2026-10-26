# Three unique acquired cities are READY — 2026-10-26

Native signed HTTP on the preserved root-owned database now returns **READY / eligible_city_count=3 for seed 17 and seed 0**, both before and after a normal restart of the owned service. The three eligible cities are Beijing **110000: 40 POI / 3 geometry edges**, Hangzhou **330100: 32 / 3**, and Suzhou **320500: 31 / 3**. Owned and published views may repeat an adcode; the count is three distinct cities, not seven view rows.

Nanjing **320100: 32 POI / 2 geometry edges** remains blocked with `AT_LEAST_3_CAPTURED_ROUTES_REQUIRED`. Its original plans, failed geometry and duplicate historical calls were preserved. No geometry threshold was relaxed and no Nanjing request was repeated.

## New Suzhou native chain

The owned backend was normally restarted onto tested product `b14a57eef7e3ee7fed4de2b64575efe09e56da9a`, with the same database/auth and existing live-source configuration. Browser pairing was disabled for this run. No Qoder database or service was accessed.

- Journey `e7f868e4-2d03-4d3c-b563-962e47b185f4`; task `ad695293-72e5-4482-9659-0784b98e829f`.
- Signed typed source acquisition queried four explicit new venue names once each. The real district receipt `e31c5a21-5b94-41c7-ba15-01f887557438` bound **苏州市 / 320500**; the task materialized **31** unique canonical places, not 32 (one source object appeared in two searches).
- Signed manual draft: December 5 拙政园 + 苏州博物馆（本馆）; December 6 狮子林 + 平江路. Original source IDs and canonical IDs are retained in the receipt. This is manual source selection, not Agent planning.
- Native draft PUT 200 → prepare-plan 201 → city-identity 200 → freeze-routes 200, verified 3/3 → city publication 200.
- Plan `07a894f2-1e00-41bd-95da-70c6118b89ca` remains **CANDIDATE**, all four activities **PLANNED**. Task remains **NEEDS_DECISION**, model turns **0**. Unknown opening/price and booking facts were not promoted; nothing was activated or completed.
- Native mobility snapshot `06978c12-364f-4e1e-b027-ac988bbb253e`.

| Real WALK edge | ProviderCall | Duration / distance | WGS84 samples | Max provider junction |
| --- | --- | --- | --- | --- |
| 拙政园 → 苏州博物馆本馆 | `c9bc26b3-a68d-444c-9e03-031181c9e93e` | 277s / 346m | 21 | 0.6734m |
| 苏州博物馆本馆 → 狮子林 (cross-day) | `36494e47-13dd-4f48-91cd-c43e586837eb` | 469s / 586m | 39 | 0.7312m |
| 狮子林 → 平江路 | `646790dd-48e3-4172-9b40-2b34eaefd5b8` | 989s / 1236m | 48 | 0.4448m |

Each of these three new pairs was measured once, all `AVAILABLE`; no retry or alternate candidate was used. All gaps remained within the existing 1m rule. Geometry followed the existing provider-to-native-snapshot path; no coordinates or straight lines were inserted.

## Publication and restart receipt

Suzhou public snapshot SHA-256: `4e6d54b8532c6cc46692c46242cb737f2406a1b99039e637d289067116a1d09f`.

Native publication and signed seed 17/0 GETs returned 200. A subsequent normal stop/resume of only the root-owned launcher preserved the same database/auth, all three public snapshot hashes, and both READY seed results. AgentRun count stayed **39**. ProviderCall count increased only during acquisition **107 → 115**: one district, four POI searches, three WALK routes. The restart and readback added **zero** provider/model calls.

Evidence: `20261026_SUZHOU_NATIVE_CITY_SUPPLY.json` includes the native HTTP sequence, source places, provider geometry, canonical plan and published snapshot. `20261026_THREE_CITY_RESTART_HTTP.json` contains pre/post summaries, unchanged counts/hashes and SHA-256 references to the full local signed HTTP receipts. Prewrite consistent database backup and guarded helper/selection files remain in the owned QA `supply-native-20261026` directory.

This closes the three-city source/publication prerequisite on the root-owned stack. It does **not** establish a same-run two-day four-stop completion, a new live-model Guardian acceptance, Qoder classroom integration, map rendering after accept, or physical-device `USER_VERIFIED`. PR56 remains a draft for Qoder integration; frontend dirty changes are excluded. No backend code changed in this receipt increment; product b14a57 has root 26/26 focused regression and two successful CI runs (263 passed, overlapping counts not additive).
