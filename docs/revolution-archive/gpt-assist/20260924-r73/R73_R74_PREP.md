# R7.3 -> R7.4 GPT prep

R7.3 final lab candidate: 7adf340bc1f62edd19263268e05ec2e5fc33fb6b.
Frozen R6.3 product base: 74005fa8b191511b48df395abda6033fdb93aec3.

Package review:
- final product diff from base is one path: backend/app/anywhere_capability.py;
- product patch new blob matches packaged source; reverse patch reconstructs the old blob;
- focused suite 89/0;
- broad suite 116/2, and the same two failures reproduce on frozen base;
- live Photon returns R:2729765 with primary label 贡山县 and no provider alias fields;
- product now correctly refuses unique-result identity adoption, so Gongshan becomes NO_MATCH;
- disposable Gongshan DB has zero Places/Journeys/Plans/Activities;
- Mission A OPEN, P7=false.

New highest-value finding:
Photon projection incompleteness is now the blocker. A stable OSM entity id exists, but Photon does not expose enough same-entity name fields to prove the user's long label. Do not revert to uniqueness. Instead add exact same-entity corroboration.

External research lead, not product evidence: a current OSM-derived relation page for 2729765 lists the full name 贡山独龙族怒族自治县, name:zh with the same full value, and short_name=贡山县. Verify this live from an authoritative provider endpoint.

Preferred seam: Nominatim /lookup by exact OSM id with namedetails=1 and extratags=1. Uniqueness may trigger this lookup but never prove identity.

If exact same-entity lookup succeeds and an allowed current-name field exactly matches -> RESOLVED.
If exact same-entity lookup succeeds but no allowed name matches -> NO_MATCH.
If lookup times out/rate-limits/fails -> RUNTIME_FAILURE retryable, not NO_MATCH.
If lookup returns a different entity id -> malformed evidence / fail closed.

Also add a tiny exact-alias parser control for semicolon-separated alt_name values.

R7.3 commits still do not resolve in the connected GitHub repositories. Keep LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE until an isolated experiment branch is published without merge.
