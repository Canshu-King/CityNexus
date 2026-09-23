# Revolution Lab R7.2 -> R7.3 external prep

R6.3 frozen checkpoint: 74005fa8b191511b48df395abda6033fdb93aec3.

R7.2 package audit:
- 21 JSON files parse as UTF-8;
- manifest 62 payloads == actual 62, no missing/undeclared entries;
- JUnit 56 cases: 55 pass, 1 fail, 0 error, 0 skipped;
- only failure: test_g6_a_fuzzy_near_match_is_not_an_identity;
- post-hydration DB: 2 provider Places, 0 PlanVersions, 0 Activities;
- park-discovery DB: 0 Places, 1 Journey, 0 PlanVersions, 0 Activities;
- mission and eligibility receipts agree: provider=2, template-eligible=0, clear sightseeing=1, fact-eligible clear sightseeing=0.

Mission A remains OPEN. P7=false.

Highest-priority proven product defect:
Query 云合 with a single provider result 遂昌县 is incorrectly RESOLVED. Provider uniqueness is not identity evidence. The current Gongshan acceptance path also names PROVIDER_UNIQUE_CANONICAL_ENTITY, so R7.3 must repair the generic identity rule without hard-coding Gongshan or replacing uniqueness with fuzzy-score authority.

Identity should accept mismatching labels only when the same provider entity supplies explicit provider-backed alias/canonical evidence such as official_name, short_name, alt_name, localized name:* or an exact follow-up read of the same provider entity proving one of those names.

R7.2 also exposes an evidence-capture weakness: R7.1 once discovered park way/1417996052 but persisted only its external id. R7.2 could not reacquire it. Future successful provider diagnostics should capture the complete candidate/raw metadata at first sight while remaining diagnostic-only.

Do not run mobility/planner while fact_eligible_clear_visit_place_count < 2.
