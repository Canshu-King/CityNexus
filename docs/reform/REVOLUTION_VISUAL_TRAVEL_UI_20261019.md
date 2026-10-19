# Revolution Visual Travel UX | 2026-10-19 | shipping order

## Real user screenshot = product acceptance failure
At 1566x988 on /revolution, the three-column cockpit displayed 3 proposal cards in a ~350px itinerary pane, each card ~100px wide with 10-11px text. Map required an extra click but displayed no spatial preview. Despite already-acquired OSM/AMap POI evidence, the page had **zero photographs**. Bottom Agent input finally existed but looked bolted on. The travel app resembled a desktop admin panel.

There is now real progress to protect: owner-signed Mission persistence, same-task message follow-ups, actual AMap district code 350825 & POI IDs, signed slot patch, four walking route facts, three model-created variants, a Guardian typed READ and real provider receipts. Do not return to fake scene cards or a new front-end shell.

## First committed UI correction in PR
- Real CC BY 3.0 **Guanzhai Mountain** (冠豸山, 连城) photo in the Mission hero. Source: Wikimedia Commons "远望冠豸山 - Guanzhai Mountain - 2010.07 - panoramio.jpg"; photo rheins; visible file/source/license credit; user does not confuse photo with opening-hour proof. Existing goal data controls whether this curated specific image is shown. Other cities get an explicitly labelled scenic *illustration*, not a fake local attraction.
- Three itinerary variants are now **stacked, readable 16px headline / 13px description** instead of 3 x 100px prose columns. A colored accent denotes relaxed/budget/local; actual source count/route count persists. Expand, select, signed PUT, version handling and existing e2e labels remain intact.
- While waiting for external OSM map consent, an owner-data-only **relative-coordinate preview** shows genuine WGS84 locations as keyboard-accessible markers and allows opening linked day activities. It is labelled as *not* a street map or route. Current explicit "加载地图" action and actual MapLibre remain unchanged. No new external tile request.
- These changes are written on the Codex product HEAD feature branch derivative. **Not yet locally built, rendered or deployed**. User is still seeing old code until Codex integrates and runs their real Chrome.

## Next REQUIRED visual capabilities: real photo system, not decorative image theater
The project already has usable map/POI identities. It does not have a photo/media pipeline. Implement it before adding another wizard or test framework.

1. **Typed photo media contract**: {place_id, title, image_url, thumbnail_url?, provenance, author, license, attribution_url, terms_url?, captured_at, confidence, can_show}. Store only rights-permitted fields. Let a photo be explicitly not available. Do not claim that a citywide scenic photo depicts a specific restaurant or place.
2. **Source-specific image acquisition**:
   - Wikidata P18 / Wikimedia Commons: when exact sourced identity exists, request a thumbnail & machine-readable credit/license; imageinfo extmetadata + source URL, show attribution. A generic title search is NOT proof of a specific place and should not silently match.
   - AMap 2.0 API documentation lists optional \`photos\` via \`show_fields=photos\`, including title + URL. Check the exact account entitlement and **AMap terms on displaying/caching third-party imagery**. Don't save/cache provider photo bytes or use that data outside the authorized presentation scope. A key must never reach the browser.
   - Provider has no authorized photo? An explicitly labelled destination illustration remains an honest visual fallback. Never grab random search thumbnails.
3. **Product surfaces**: Destination hero; scrollable gallery for 3-6 verified/relevant locations; individual spot photo cards with 4:3 images, place label, source, open-detail route; daily timeline as large cards with photo + time + walking + price/opening status; photo alt, lazy-load, placeholders and failure fallback. Gallery and map use the **same signed Journey's location IDs**. External photo requests must be intentional and manageable, performance conscious.
4. **Geo-UX**: AMap GCJ02 data must not be painted directly onto WGS84 OSM map. Use separate authorized AMap interactive map/map-link or proven coordinate conversion with provenance and legally permitted use; keep a unified *visual work canvas* without lying about coordinate datum.
5. **Make the Agent speak human**: Lead with "已找到3个景点、生成3套日程"，then a photo/map/next best action; 43/46 model turns and long tooling remain expandable into DSH Control Tower. Chat composer never covers save/choose buttons or mobile bottom nav.
6. **Priorities**: first visual traveler success on 390/430/1366; one photographic POI and one map/itinerary change under same task; then expandable photo carousel across regions. Do not block this user-facing effort on 2000-line audit scripts.

## Browser acceptance
One human opens existing signed 连城 Mission, immediately sees geographic destination imagery (if the photo host loads), reasonably large 3 candidate options (no prose 100px columns), coordinates in the map placeholder before any external map tile, and always-visible Agent composer; selecting a plan still persists. On a 390x844 device no horizontal overflow, no photo covering input/action, usable target sizes ≥44px.

The attached Wikimedia Commons image is CC BY 3.0 with copyright attribution to rheins. The photo is used as *city/region travel inspiration*, not an exact matching POI photo. Source https://commons.wikimedia.org/wiki/File:%E8%BF%9C%E6%9C%9B%E5%86%A0%E8%B1%B8%E5%B1%B1_-_Guanzhai_Mountain_-_2010.07_-_panoramio.jpg

References:
- AMap Web Service POI 2.0 optional photos field: https://developer.amap.com/api/webservice/guide/api/newpoisearch
- AMap API terms/content/cache restrictions: https://developer.amap.com/pages/terms/
- Wikimedia imageinfo + extmetadata: https://www.mediawiki.org/wiki/API:Imageinfo
