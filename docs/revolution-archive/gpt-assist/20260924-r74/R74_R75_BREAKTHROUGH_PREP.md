# Revolution R7.4 -> R7.5 product breakthrough

R7.4 is a useful checkpoint, not Mission A success.

Machine facts from the external-review package:
- Gongshan resolves to OSM:R:2729765.
- 9 provider-backed rows exist: restaurant 1, park 1, viewpoint 1, hotel 6.
- all 9 have UNKNOWN opening and UNKNOWN cost.
- strict AUTO returns 422 CATALOG_INSUFFICIENT.
- explicit provider-place composition returns 422 PLACE_COST_UNVERIFIED.
- focused backend 57 passed; frontend typecheck/build pass.
- DeepSeek/Hermes were not configured/executed.
- Mission A OPEN; P7=false.

Revolution correction:
Do not spend R7.5 proving the same blocker again. Add a provisional, non-selectable plan lane so real Places with incomplete facts can still produce a useful itinerary while uncertainty remains explicit.

Hard truth remains:
UNKNOWN != VERIFIED.
UNKNOWN cost != FREE.
MOCK != LIVE.
Synthetic mobility cannot close real authority.

Product target:
1. preserve the human destination label (do not title the Journey Osm:r:2729765);
2. emit a real CANDIDATE when >=2 provider-backed visit-role Places with coordinates exist, even if opening/cost are unknown;
3. mark unresolved facts and selectable=false;
4. never fabricate budget_fit/venue availability;
5. display OPENING REQUIRES_CONFIRMATION and COST UNKNOWN in UI;
6. capture real Valhalla/OSRM mobility for actual draft edges when available;
7. keep selection blocked until strict authority genuinely closes.

Suggested strict/draft split:
- existing authoritative _catalogue_templates / strict selection remain fail-closed;
- after strict failure caused only by incomplete opening/cost evidence, invoke a provisional composer;
- provisional PlanVersion can remain status=CANDIDATE with selectable=false and explicit authority_state in explanation/response;
- Activity.cost_status stays UNKNOWN;
- cost summary is PARTIAL with known_subtotal and unknown_item_count;
- utility_score/score_breakdown may be null if dimensions are indeterminate.

Known Gongshan provider objects:
- park: overpass:way/1417996052, 贡山县总体国家安全观主题公园, ~27.734612,98.6709516;
- viewpoint: overpass:node/13030932589, ~27.7370453,98.6731146;
- restaurant: overpass:node/13030932384.

External research leads:
- Yunnan Sports Bureau has an official Bingzhongluo walking route containing 丙中洛观景台, 怒江第一湾, 怒江吊桥, 桃花源, 普化寺 with route ordering/timing.
- Amap/Ctrip expose a named 丙中洛观景台. Treat commercial-provider opening claims as attributed evidence, not official truth.
- 2026 Gongshan notices warn against undeveloped/unopened tourism areas; prefer established visitor routes.

Existing product already has a Valhalla seam via CITYNEXUS_LIVE_VALHALLA_URL. Use that before inventing another mobility architecture. If unavailable, use a legitimate real OSRM route provider, not mock authority.

Mission A stays OPEN until real facts + real mobility + selectable authority close. P7=false.
