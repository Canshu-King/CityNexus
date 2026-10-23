# CityNexus SE2026 - evidence index

Generated 2026-10-23 18:25 by `live_checks/se_evidence_index_r1.py`. This page exists because round 2 shipped an evidence file from an older generation than the plan it described, and pointed a reader at two files that were not in the package. Both are now checked by machine.

Shipped plan: `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`, sha256 `6398e58f9b4cd3b3f1a24255d50c9bb2b10569abdd747271f15d3e50eab84aee`.

Recovery plan: `Microsoft_Project/CityNexus_Plan_Recovery.mpp`, sha256 `7e4f561a46d32b229bf593c18b37adfdc1cfc63080388c595b684f9142fcc0fb`.

## Every evidence file, its generator and the digest it claims

| file | bytes | sha256/16 | written by | written at | source-plan digest it claims |
|---|---|---|---|---|---|
| `Evidence/se_deck_result.json` | 16198 | `c47facb986dbf0d8` | `se_deck_r1.py` | 2026-10-23 04:38 | not a plan-derived file |
| `Evidence/se_evidence_reconcile_result.json` | 9549 | `5483ddea04f22ad6` | `se_evidence_reconcile_r1.py` | 2026-10-23 04:37 | planSha256_12: 6398e58f9b4c (current) |
| `Evidence/se_evidence_revision_result.json` | 733 | `85e363d17b0556c8` | `se_evidence_revision_r1.py` | 2026-10-22 18:53 | not a plan-derived file |
| `Evidence/se_milestone_view_result.json` | 3243 | `fc68ee0f31b2b7e1` | `se_milestone_view_r2.py` | 2026-10-23 04:37 | not a plan-derived file |
| `Evidence/se_plan_cpm_r2.json` | 20470 | `8107d4ce6bd60f49` | `se_plan_cpm_r1.py` | 2026-10-23 04:36 | not a plan-derived file |
| `Evidence/se_plan_status_result.json` | 34958 | `e01ad57e037d96ba` | `se_plan_status_r1.py` | 2026-10-23 04:37 | not a plan-derived file |
| `Evidence/se_project_brief_result.json` | 4526 | `59cb883632b12c3b` | `se_project_brief_r1.py` | 2026-10-23 04:37 | not a plan-derived file |
| `Evidence/se_project_build_r2_result.json` | 129195 | `760f54dbfabc605d` | `se_project_build_r2.py` | 2026-10-23 04:35 | publication.sha256AfterVerification: 6398e58f9b4cd3b3 (current) |
| `Evidence/se_project_export_r2_result.json` | 788 | `7cee8ac240861887` | `se_project_export_r2.py` | 2026-10-22 18:47 | not a plan-derived file |
| `Evidence/se_project_recovery_result.json` | 2523 | `cc5f815b4a8ad191` | `se_project_recovery_r1.py` | 2026-10-23 04:37 | sourcePlanSha256: 6398e58f9b4cd3b3 (current) |
| `Evidence/se_project_snapshot_r2_result.json` | 6461 | `999d9007902aaf29` | `se_project_snapshot_r2.py` | 2026-10-23 04:38 | not a plan-derived file |
| `Evidence/se_review_package_r2_result.json` | 1528 | `bff98d7724eba566` | `se_review_package_r2.py` | 2026-10-23 13:24 | not a plan-derived file |
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

76 relative paths are cited by the markdown in this delivery. Unresolvable: **0**.

Documents excluded from the citation check, by name: `CLASSROOM_20261023_NOON_PRIORITY.md`, `CLASSROOM_QODER_CONTINUOUS_UNTIL_NOON_20261023.md`, `CLASSROOM_R3_LAST_MILE_20261023.md`, `EVIDENCE_INDEX.md`, `INDEPENDENT_R2_REVIEW_20261022.md`, `R3_RESULT.md`, `TEACHER_READABILITY_CORRECTION_20261023.md`. Two kinds: received external reviews and instruction notes, which are quoted as they arrived and are not allowed to be edited into agreement; and this report plus `R3_RESULT.md`, which name the findings they are checking, so scanning them would make the checker cite itself.

Every path a document in this package tells the reader to open resolves to a file that is either in this package or in the product repository the package is cut from.

