# R7.3 provider identity truth contract

Sufficient evidence:
- exact primary provider name;
- exact official/short/alt/localized name supplied by the same provider entity;
- exact follow-up read of the same provider entity that proves such an alias;
- an already-held exact provider entity id explicitly referenced by product context.

Insufficient alone:
- one returned candidate;
- fuzzy score/edit distance/prefix overlap;
- same country/admin type;
- geographic plausibility;
- model/search-engine opinion without same-entity provider evidence.

Required negative control:
云合 -> sole provider result 遂昌县 => NO_MATCH.

Gongshan control:
贡山独龙族怒族自治县 -> OSM:R:2729765 must be re-proven under the same generic rule. If provider-backed alias evidence is absent, fail closed until it is obtained. Do not grandfather the destination.
