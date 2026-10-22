# CityNexus SE2026 - evidence index

Generated 2026-10-23 02:17 by `live_checks/se_evidence_index_r1.py`. This page exists because round 2 shipped an evidence file from an older generation than the plan it described, and pointed a reader at two files that were not in the package. Both are now checked by machine.

Shipped plan: `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`, sha256 `4cd35d0725c2c5d3ab26cff11925015a4fa78fd52610abcb8ca0ce4918277e41`.

Recovery plan: `Microsoft_Project/CityNexus_Plan_Recovery.mpp`, sha256 `ec3e1a5c7b2b25b8063b17120a3c07f6c3b0c95a2abf70cdf392af79a6d6ada7`.

## Every evidence file, its generator and the digest it claims

| file | bytes | sha256/16 | written by | written at | source-plan digest it claims |
|---|---|---|---|---|---|
| `Evidence/se_deck_result.json` | 16198 | `78e3e56cc8d486c0` | `se_deck_r1.py` | 2026-10-23 02:17 | not a plan-derived file |
| `Evidence/se_evidence_reconcile_result.json` | 9549 | `7e98703a37e6e154` | `se_evidence_reconcile_r1.py` | 2026-10-23 01:43 | planSha256_12: 4cd35d0725c2 (current) |
| `Evidence/se_evidence_revision_result.json` | 733 | `85e363d17b0556c8` | `se_evidence_revision_r1.py` | 2026-10-22 18:53 | not a plan-derived file |
| `Evidence/se_milestone_view_result.json` | 3197 | `47b9935077c1ae37` | `se_milestone_view_r2.py` | 2026-10-23 01:38 | not a plan-derived file |
| `Evidence/se_plan_cpm_r2.json` | 20470 | `8107d4ce6bd60f49` | `se_plan_cpm_r1.py` | 2026-10-23 01:38 | not a plan-derived file |
| `Evidence/se_plan_status_result.json` | 34937 | `a02394b57b3102a1` | `se_plan_status_r1.py` | 2026-10-23 01:38 | not a plan-derived file |
| `Evidence/se_project_brief_result.json` | 4503 | `cac7104936156fe3` | `se_project_brief_r1.py` | 2026-10-23 01:41 | not a plan-derived file |
| `Evidence/se_project_build_r2_result.json` | 128853 | `7e9b4ebd5b223a0f` | `se_project_build_r2.py` | 2026-10-23 01:37 | publication.sha256AfterVerification: 4cd35d0725c2c5d3 (current) |
| `Evidence/se_project_export_r2_result.json` | 788 | `7cee8ac240861887` | `se_project_export_r2.py` | 2026-10-22 18:47 | not a plan-derived file |
| `Evidence/se_project_recovery_result.json` | 2145 | `5e1374a19d451b09` | `se_project_recovery_r1.py` | 2026-10-23 01:38 | sourcePlanSha256: 4cd35d0725c2c5d3 (current) |
| `Evidence/se_project_snapshot_r2_result.json` | 4877 | `4370d818aed3b585` | `se_project_snapshot_r2.py` | 2026-10-23 02:14 | not a plan-derived file |
| `Evidence/se_review_package_r2_result.json` | 1398 | `c8215a47f149ee4c` | `se_review_package_r2.py` | 2026-10-23 02:17 | not a plan-derived file |
| `Evidence/se_visio_build_result.json` | 61641 | `f1c94e98f239a49f` | `se_visio_build_r1.py` | 2026-10-22 18:50 | not a plan-derived file |
| `Evidence/se_visio_plan_brief_result.json` | 8379 | `f00d0f87197b7d95` | `se_visio_plan_brief_r1.py` | 2026-10-22 18:51 | not a plan-derived file |
| `Evidence/se_visio_proof_result.json` | 10248 | `61ebbbba022af9a8` | `se_visio_proof_r2.py` | 2026-10-22 18:50 | not a plan-derived file |

A claimed digest that does not start with the digest of the file on disk is stale evidence, and this generator refuses rather than writing the index.

## Same fact, several files

| fact | values | verdict |
|---|---|---|
| links declared | `se_plan_cpm_r2.json` = 61; `se_project_build_r2_result.json` = 61 | agree |
| links violating date order | `se_plan_cpm_r2.json` = 0; `se_project_build_r2_result.json` = 0 | agree |
| M13 coursework delivery date (engine) | `se_milestone_view_result.json` = 2026-10-23; `se_project_build_r2_result.json` = 2026-10-23 | agree |
| late rows at the status date (engine dates) | `se_plan_status_result.json` = 14; `se_project_build_r2_result.json` = 14 | agree |
| student hours | `se_plan_status_result.json` = 220.9; `se_project_build_r2_result.json` = 220.9 | agree |
| over-allocated person-weeks | `se_plan_status_result.json` = 0; `se_project_build_r2_result.json` = 0 | agree |

`se_plan_cpm_r2.json` is the pure-Python pass: it answers what the declared network implies and it does not model resources, so its finish date is allowed to differ from the engine's. It is also 8 rather than 14 rows late, because a row the engine places on 2026-10-21 the static pass places after the status date. Lateness is therefore judged only on the engine's own dates, and the two files that read them agree. The scheduler difference is explained in `Evidence/PLAN_RECONCILIATION.md`.

## Cited paths

57 relative paths are cited by the markdown in this delivery. Unresolvable: **0**.

Documents excluded from the citation check, by name: `EVIDENCE_INDEX.md`, `INDEPENDENT_R2_REVIEW_20261022.md`, `R3_RESULT.md`. Two kinds: received external reviews and instruction notes, which are quoted as they arrived and are not allowed to be edited into agreement; and this report plus `R3_RESULT.md`, which name the findings they are checking, so scanning them would make the checker cite itself.

Every path a document in this package tells the reader to open resolves to a file that is either in this package or in the product repository the package is cut from.

