# CityNexus Revolution Lab R7.1 - GPT external audit

## Verdict

R7.1 supports the narrow conclusion FACT_EVIDENCE_INSUFFICIENT: Gongshan has seven provider-backed Places, but zero are currently eligible for AUTO templates under the existing role/opening/cost gates. Mission A remains OPEN and P7=false.

## Machine-supported facts

- frozen product checkpoint remains 74005fa8b191511b48df395abda6033fdb93aec3;
- resumed hydration ran on clean ec1ade2cff0733192111a434a76d17cb3cb3efc9 and stayed clean;
- Gongshan canonical destination remains OSM:R:2729765;
- resumed hydration completed CATALOG_PREPARED / PARTIAL;
- catalogue now holds six hotels plus one viewpoint;
- mobility remains MISSING, explicit_pairs=0, hard_eligible=false;
- provider_place_count=7, template_eligible_place_count=0;
- UNKNOWN cost remains distinct from known-free;
- focused tests report 9 passed.

## Exact acquisition frontier

Already-held visit object:
- overpass:node/13030932589 - viewpoint

New provider objects discovered by the isolated R7.1 probe but not held:
- overpass:way/1417996052 - park
- overpass:node/13030932384 - restaurant

Prefer viewpoint + park for Mission A. Keep restaurant as diagnostic/control unless meal-role semantics are explicitly made first-class; do not close Mission A by exploiting the current generic visit whitelist.

## Provider timing

R7.1 weakens the prior hypothesis that shared question-order starvation is the sole cause. Fresh-deadline isolated queries succeeded for park and restaurant at positions 3 and 4, while attraction/hotel timed out; resumed preparation also got six hotels as its last question in about 2.7s. Do not rewrite orchestration around order starvation without repeated/rotated evidence.

## Evidence defects to close without product changes

1. R71_SOURCE_BINDING.json gives parent 705c41b for ec1ade2, but r71_gongshan_resumed_prep.json gives parent 3690cf9 and commit_list.txt also places 3690cf9 immediately before ec1ade2. Regenerate from Git.
2. change_summary/post_frozen_change_list mention R7_ROUND_RECEIPT.md, but the file is absent from the archive.
3. R71_ROUND_RECEIPT.md names evidence/diagnostic_tools.diff, but the archive contains diagnostic_and_receipt_diff.txt.
4. stdout JSON copies are GB18030, while canonical JSON evidence is UTF-8. Semantic content matches, but future JSON receipts should be UTF-8.

These do not overturn the zero-eligibility result.

## Next truth objective

Do not change Planner gates. First capture exact-object facts for the held viewpoint and isolated park, materialize the park through the real product seam, obtain verified opening and explicit cost semantics for two clear sightseeing stops, recompute eligibility, and only then attempt hard-eligible mobility and AUTO.
