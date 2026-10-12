# CityNexus Revolution R89 — From Public POI Preview to a Usable, Evidence-Aware First Stop

## Verified baton
R88 remote HEAD `35fc69dd023acbe2c7263bbbc48b300719926f8e`, implementation `d7d957786`, result `REVOLUTION_R88_REAL_POI_EXPLORATION_WITHOUT_OPENING_PROOF_RESULT.md`. Accept CONTROLLED_PRODUCT_PATH_PROVEN for signed private OSM candidate preview + destination-only per-release consent + no plan mutation. Preserve R87's single genuine Overpass discovery; **do not repeat** it. R88's external opening remains EXTERNAL_NOT_ATTESTED; no real verified opening or field journey.

## Two concrete review points
- `BootstrapDiscoveryPanel.tsx::confirmMapPreview` awaits a server request before `window.open(...)`. Mobile Safari/Chrome popup blockers may reject the window because the call no longer occurs within a user activation. Ensure a usable secure external-map action on mobile (e.g., a preopened blank `noopener` tab within the click followed by validated destination navigation; if rejected, show a plainly clickable URL after server authorization). Never open an unvalidated URL or bypass server checks. Test rejection/fallback, consent cancellation and stale release.
- `source_tags` from OSM are **untrusted third-party claims**, including website/contact and opening_hours. Show appropriate escaping, safe URL scheme/host handling, source identity and captured timestamp; do not treat arbitrary website tags or a source-page click as verified availability. Avoid an XSS/phishing downgrade and avoid `OPEN_NOW` from a raw OSM schedule.

## Revolutionary next user outcome
From a newly created zero-catalog DRAFT Journey, the user can discover an actual source-linked POI, open its exact public map reliably on a normal mobile browser, inspect relevant official evidence, and take the next legitimate action toward starting a Journey. No dead-end `Verify opening first` button with no built-in workflow.

## Deliverables
1. Implement the mobile-safe external map release and accessible fallback. Keep per-release consent, private search context isolation, strict receipt/member/expiry/coordinates checks, destination only and no origin.
2. Inspect existing opening-hours evaluator and existing provider/official-source integrations. If a **legitimate exact-place official verifier already exists**, enable a narrow explicit refresh for the chosen candidate with fresh receipt, source URL, place identity, evidence timestamp and confidence; only grounded verified opening facts may cross the native PlanVersion gate. Do not scrape arbitrary OSM website tags, invent hours, elevate OSM-tag claims, or add a fake verifier.
3. If trusted opening verification cannot be completed, ship a meaningful in-app next action: show public place/source and date, retain a draft candidate watchlist or explicit 'continue exploring without committing' action safely in owner-scoped DRAFT Journey, and allow switching candidate; never imply a route, booking, confirmed stop, or PlanVersion exists. A user-authored note like 'I checked the website' remains self-report and cannot change VERIFIED_PROVIDER status.
4. Narrowly inspect `bootstrap_discovery.py` for independent members encountering the same OSM identity: do not drop all named results for member B solely due to A's private candidate, and never reveal A's private receipt to B. Any fix must preserve deterministic Place idempotency on selection.
5. Validate with **one** fresh product-created signed A/B zero-catalog Journey, controlled provider data (clearly TEST_PROVIDER), one Chromium mobile-oriented browser flow and focused backend checks; no R58-R88 archive suites. If a real official verifier is permitted/available, one bounded attempt only and truthfully report outcome; **no repeated Overpass discovery**. Run typecheck/build/compile/diff.

## Result
Push code and `REVOLUTION_R89_MOBILE_REAL_POI_NEXT_ACTION_RESULT.md` to `gpt/revolution-r33-open-world-journey-adaptation`. Report exact SHAs, opened vs blocked map behavior, privacy and stale checks, official-source evidence grade, Places/PlanVersions/provider/Agent/Guardian counts, and what a traveler can concretely do next. No more verifier-only loops.

Our aim is a travel companion that helps a person take the next real-world step despite incomplete information—not a more elaborate unknown-status screen.
