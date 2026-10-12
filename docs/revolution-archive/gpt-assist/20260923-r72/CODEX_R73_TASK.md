# Codex R7.3 task

1. Create a new isolated product experiment from the intended frozen product source. Do not rewrite R7.2 evidence.
2. RED first. Preserve the existing failing control:
   - query 云合
   - sole provider primary label 遂昌县
   - expected NO_MATCH.
3. Add controls:
   - exact primary-name match -> RESOLVED;
   - explicit same-entity alias -> RESOLVED;
   - official/short/alt/localized same-entity name -> RESOLVED;
   - unique unrelated result -> NO_MATCH;
   - fuzzy similarity alone is insufficient;
   - multiple disagreeing entities -> no arbitrary pick;
   - timeout -> runtime failure, not NO_MATCH;
   - Gongshan may stay RESOLVED only if generic provider-backed same-entity evidence proves 贡山独龙族怒族自治县 and OSM:R:2729765 are the same entity. No destination-specific exception.
4. Repair rule: never use len(candidates)==1 as identity proof. Emit the exact comparison rule/reason that proved identity.
5. Run the full provider-identity leg and prior R6-R7 truth controls. Previous 56-case suite must reach zero failures before Mission A acquisition resumes.
6. Improve diagnostic provider capture so successful candidates store complete candidate/evidence payload, not only external_id.
7. Resume Gongshan only after identity is green. Preferred sightseeing frontier remains viewpoint node/13030932589 + park way/1417996052. Restaurant node/13030932384 remains diagnostic/control.
8. Missing opening/cost remains UNKNOWN. No mobility/planner while fewer than two clear sightseeing Places have verified opening and cost.

Mission A OPEN. P7=false.
