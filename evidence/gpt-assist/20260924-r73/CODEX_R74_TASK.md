# Codex R7.4 exact-entity identity task

RED first:
1. 云合 -> Photon sole 遂昌县; exact lookup same entity names do not include 云合 -> NO_MATCH.
2. 贡山独龙族怒族自治县 -> Photon R:2729765 label 贡山县; exact lookup of R2729765 contains the full query -> RESOLVED OSM:R:2729765.
3. exact lookup returns different OSM id -> fail closed.
4. exact lookup timeout/429/transport -> RUNTIME_FAILURE retryable.
5. exact lookup same id, no exact allowed name -> NO_MATCH.
6. exact Photon primary-name match still resolves without corroboration.
7. multiple Photon entities stay AMBIGUOUS.
8. alt_name=A;B may exactly match A or B; no substring/fuzzy acceptance.

Implementation boundary:
- never use len(candidates)==1 as proof;
- use exact OSM id only as the key for a same-entity follow-up;
- preferred public API: Nominatim /lookup?osm_ids=R...&format=jsonv2&namedetails=1&extratags=1;
- provide a valid CityNexus User-Agent and cache/throttle the mismatch-only lookup;
- do not use Nominatim /details in automation;
- record exact provider, entity id, matched field/value, attempts and timestamps.

After identity is green, rerun Gongshan hydration. Do not run mobility/planner until >=2 clear sightseeing Places have verified opening and cost.

Mission A OPEN. P7=false.
