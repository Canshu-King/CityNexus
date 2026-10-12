# CityNexus Revolution — Real Public City Discovery Operator Runbook

**Purpose:** make the first genuinely consented public Overpass discovery possible without inventing a human's choice, a result, or physical arrival. This document is an operator/user handoff, **not a command to run an external query unattended**.

## Configuration preparation (operator only)
1. Confirm that the selected external Overpass server is approved by the operator, supports the intended request load, and that this deployment may transmit public map-center coordinates to it. The built-in R105 allowlist requires a supported public HTTPS host and a base path of `/api`. Do not bypass this by editing host checks or using localhost as a fake 'live' source.
2. In a deliberately managed runtime, configure only the needed settings: `CITYNEXUS_REAL_CITY_ENABLED=true`, `CITYNEXUS_REAL_CITY_MODE=live`, and an operator-approved `CITYNEXUS_OVERPASS_URL=https://overpass-api.de/api` **as an example URL only, not a guarantee that this host is available or approved in your deployment**. The actual web experience requires no keys for this bounded Overpass query. Keep secrets/proxy credentials out of logs and taskbooks. Optional city geocoder is **not required** if the traveler uses the existing validated OpenStreetMap map-link/manual public-center path. Network proxy behavior remains subject to `CITYNEXUS_PROVIDER_NETWORK_MODE` and deployment rules.
3. Check the signed product readiness view shows `LIVE_CAPABLE`, NOT `LIVE_VERIFIED`; its GET must not make an external query or DNS call. A DNS preflight occurs after explicit user selection/consent and currently checks for non-global addresses. Note the preflight is **not a connection-level DNS pin**; proxy and DNS rebinding require separate transport safeguards.
4. The operator's act of enabling the service is **not** the traveler's consent. Do not run an automated live call to satisfy a milestone.

## Traveler action, not operator impersonation
1. Sign in and create/open a **DRAFT** Journey with no active PlanVersion for a real chosen city. Only the traveler confirms the city label.
2. Choose **public map area**, not foreground GPS. Paste a validated OpenStreetMap public map link or deliberately tap a public map pin. Review exactly which public WGS84 latitude/longitude will be transmitted.
3. Select a bounded category (e.g. art/history or quiet books). Read the provider recipient disclosure. Check the separate provider consent for exactly these inputs.
4. Press **Search public places** once. The consent checkbox should be consumed. Do not retry simply to collect nicer proof.
5. Review truthful states: `FOUND_2+` (eligible public source identities), `PARTIAL_1` (one; no invented second), `ZERO`, `UNAVAILABLE`, or `DISABLED`. A LIVE_PROVIDER grade applies to an observed **real public provider response** only, never readiness. Site opening, price, accessibility, ETA and actual visit remain unverified unless separately observed.
6. When two usable source identities exist, choose the pair and use R107's forthcoming one-tap private Pocket Walk; otherwise use an honest single-place public-source preview. Sharing with a friend is always a separate public-only voluntary action and their own verification consent.

## Evidence receipt and failure honesty
Keep only: source operation type, approved public provider HOST (no credentials), real vs controlled boundary, HTTP status/answer, observation timestamp, accepted candidate count, canonical OSM object URLs and failure reason. Never write member bearer, member/traveler IDs, Journey ID in external payload, private home/GPS origin, exact public query center in general ProviderCall logs, or unreviewed raw pasted text.

If operator approval, a real city, a public pin, explicit consent or outbound network are missing, record `LIVE_BLOCKED_<PRECISE_REASON>`; do not simulate a venue to satisfy 'First Real City' milestone. No fake arrival, ticket, group co-presence, booking or PlanVersion.

**Codex boundary:** Existing R106 evidence is controlled-only. R107 must improve the ordinary user's native action from REAL (or honestly TEST) discovery results to a saved private two-stop outing, without redefining a fixture as public reality.
