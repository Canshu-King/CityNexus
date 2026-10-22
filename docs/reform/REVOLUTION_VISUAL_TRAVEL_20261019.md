# CityNexus Visual Travel Experience — real photos, readable trips, living spatial results
2026-10-19 | UI P0 / Revolution Mission | Integrate into Codex PR #23

## Why
User's actual desktop screenshot: left pane is a scroll-heavy Agent audit log; center is copy and a gated tile map; right shows three itinerary cards squashed into ~100px-wide, 10–11px type. There is no destination photography. Real map and Agent source facts exist, yet the product still looks like an old administrative dashboard.

## The branch implements actual application changes
- DestinationMedia: visual Liancheng hero with confirmed Wikimedia Commons Guanzhai Mountain photo, author, CC BY 3.0 attribution and a safe illustration fallback.
- PlacePhotoGallery: license-linked photographic previews for exact Liancheng POI names that have matching district and LIVE_PROVIDER identity; original-source and author links, with fallback when CDN unavailable. Historical photos are **not** proof of opening, amenities or current conditions.
- GoalDraftVariants: a legible vertical three-option comparison replacing three narrow text columns, preserving dates, actual source references and original plan/approval semantics.
- WorkspaceMap: before OSM tile consent, a relative-point preview computed from the existing signed WGS84 source coordinates. It is labelled **not a street map or route**. Existing MapLibre, tile-consent, navigation and coordinate boundaries stay in force. Native GCJ02 points remain in their distinct high-confidence provider surface.
- MissionCockpit: concise traveller-facing Agent state first, full detailed conversation/tools behind native disclosure. Persistent bottom chat stays mounted.
- Visual Playwright fixture at 390/1366 checks cards, source-linked photos, map preview, no premature tile request and visible chat.

Status: these are actual GitHub product bytes, **NOT** locally executed typecheck/build/Chrome or user-verified screenshots yet. The tests are TEST_FIXTURE.

## Next: real signed PlaceMedia lookup, not static city photo substitutions

### Qoder — media evidence interface
Expose typed discover_place_media(place_id, confirmed_public_region) to the same Mission research tools.
- Only lookup a known/canonical provider place identified by place_id and administrative scope, not a model-invented arbitrary name or generic web image.
- Support reuse-eligible media such as Wikimedia Commons official API imageinfo and linked Wikidata P18. Do not assume that Amap's POI endpoint grants unrestricted rehosting/hotlink rights.
- Return structured place_id, provider_place_id, image_url, source_page, author, license, license_url, captured_at, verified_identity, width, height, mime, plus NOT_FOUND/NO_PERMISSION/UNAVAILABLE.
- Cache and honor content rights; whitelist public safe HTTPS image origins, block SSRF/tracking, SVG/script payloads and credential leakage. Not every POI has a photo: no unrelated images masquerading as that POI.
- Agent can research photos inside existing read-only bounded authorization; missing photos cannot halt travel planning.

### Codex — consumer UX
- Wire signed PlaceMedia records to the existing Mission POI cards. Make photo, short localized fact and one contextual action visually dominant, not long diagnostic text.
- Photos + maps + date cards share stable place_id; when route fact exists show real mode, distance, minutes, provenance and capture time, otherwise unknown. No fake polylines or estimates.
- Desktop: dominant map + image-rich exploration with compact Agent; vertical timeline/variants. Mobile: visual map/photo screen and swipable itinerary, persistent unobstructed composer.
- Real 390/430/1366 Chromium and phone screenshot checks; heading at least 22px, card titles at least 15px, body at least 13px, 44px targets.
- Same signed Journey: user types “第二天下午换成轻松一点的地方”, model runs, affected draft slots change, gallery/map/itinerary update and reload persists.

Acceptance fields: PRODUCT_SHA, PHOTO_SOURCE_LINK, IDENTITY_CHECK, MAP_COORDS, THREE_VARIANTS_LEGIBLE, CHAT_UNOBSTRUCTED, LIVE_AGENT_STEP, LIVE_PROVIDER, ITINERARY_DIFF, USER_VERIFIED.

Do not rewrite user Windows working tree or force push while Codex operates. Integrate this PR by normal merge/cherry-pick after real tests.

## Wikimedia Commons starter source pages
- Guanzhai Mountain (rheins, CC BY 3.0): https://commons.wikimedia.org/wiki/File:%E8%BF%9C%E6%9C%9B%E5%86%A0%E8%B1%B8%E5%B1%B1_-_Guanzhai_Mountain_-_2010.07_-_panoramio.jpg
- Peitian Village (张元柏, CC BY-SA 3.0): https://commons.wikimedia.org/wiki/File:2012_%E7%A6%8F%E5%BB%BA_%E9%BE%99%E5%B2%A9_%E8%BF%9E%E5%9F%8E%E5%8E%BF_%E5%9F%B9%E7%94%B0%E5%8F%A4%E6%9D%91_-_panoramio_(3).jpg
- Shimen Lake (rheins, CC BY 3.0): https://commons.wikimedia.org/wiki/File:%E7%9F%B3%E9%97%A8%E6%B9%96_-_Shimeng_Lake_-_2010.07_-_panoramio_-_rheins.jpg . Author and license verified on the Commons file page during Windows integration.

## Windows integration increment

PR #41 was fast-forwarded from `e1b672bd79` at source `f94f6917d0`. The gallery now binds the three exact existing source IDs plus the Commons location metadata, without rewriting UNKNOWN facts. Photo actions focus the same place in the itinerary/map; nearby coordinate pins expand as a group. Current local validation and actual Chrome screenshots are recorded in `trial/results/20261019_VISUAL_INTEGRATION.md`; the unexecuted status above describes the original cloud contribution.
