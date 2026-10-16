# CityNexus Revolution — Real Public City Discovery Operator Runbook

**Purpose:** guide a traveler through a consented public Overpass search. This document is an operator/user handoff; each external query starts from the traveler's action.

## Configuration preparation (operator only)
1. Confirm that the selected external Overpass server is approved by the operator, supports the intended request load, and that this deployment may transmit public map-center coordinates to it. The built-in R105 allowlist requires a supported public HTTPS host and a base path of `/api`. Do not bypass this by editing host checks or using localhost as a fake 'live' source.
2. In a managed runtime, configure `CITYNEXUS_REAL_CITY_ENABLED=true`, `CITYNEXUS_REAL_CITY_MODE=live`, and an approved `CITYNEXUS_OVERPASS_URL`, such as `https://overpass-api.de/api`. Confirm host approval and availability for the deployment. This bounded Overpass query needs no API key. Keep secrets and proxy credentials out of logs and taskbooks. A city geocoder is optional when travelers use the validated OSM map-link/manual public-center path. Network routing follows `CITYNEXUS_PROVIDER_NETWORK_MODE` and deployment rules.
3. The signed readiness view reports `LIVE_CAPABLE` before a query and `LIVE_VERIFIED` after an observed provider response. Its GET is read-only. DNS preflight runs after the traveler selects a location and consents; it checks for non-global addresses. Transport-level DNS pinning is a separate safeguard for proxy and rebinding scenarios.
4. Enabling the service prepares it for use. The traveler confirms each search in the interface.

## Traveler search steps
1. Sign in and create/open a **DRAFT** Journey with no active PlanVersion for a real chosen city. Only the traveler confirms the city label.
2. Choose **public map area**, not foreground GPS. Paste a validated OpenStreetMap public map link or deliberately tap a public map pin. Review exactly which public WGS84 latitude/longitude will be transmitted.
3. Select a bounded category (e.g. art/history or quiet books). Read the provider recipient disclosure. Check the separate provider consent for exactly these inputs.
4. Press **Search public places** once. The consent checkbox should be consumed. Do not retry simply to collect nicer proof.
5. Review `FOUND_2+`, `PARTIAL_1`, `ZERO`, `UNAVAILABLE`, or `DISABLED`. `LIVE_PROVIDER` appears after an observed public provider response. Opening hours, price, accessibility, ETA, and visit status each use their own source or show `UNKNOWN`.
6. When two usable source identities exist, choose the pair and use R107's forthcoming one-tap private Pocket Walk; otherwise use an honest single-place public-source preview. Sharing with a friend is always a separate public-only voluntary action and their own verification consent.

## Search record
Record the source operation, approved provider host, real/controlled mode, HTTP status, observation time, accepted candidate count, canonical OSM object URLs, and failure reason. Keep member tokens, member IDs, Journey IDs, private origins, exact query centers, and unreviewed pasted text out of general ProviderCall logs.

When operator approval, a chosen public location, traveler consent, or outbound network is unavailable, record `LIVE_BLOCKED_<PRECISE_REASON>`. Arrival, tickets, group presence, bookings, and PlanVersions come from their corresponding records.

**Codex scope:** R106 evidence covers controlled mode. R107 connects public discovery results to a saved private two-stop outing; TEST results retain their source label.
