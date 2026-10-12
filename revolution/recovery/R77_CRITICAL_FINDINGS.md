# R77 critical findings

## 1. Closed httpx.Client bug
R77 fact acquisition opens one httpx.Client for Overpass + Nominatim, exits the context manager, then later reuses that same client for official-web and SearXNG calls. A real client raises RuntimeError after close. Fix client lifetime before enabling real fact-source continuation, and add a regression that actually models close semantics.

## 2. SSRF boundary required
R77 accepts provider-tag website/contact:website/url and server-fetches it. Before mainline use, reject non-http(s), loopback, private/link-local/reserved/multicast/cloud-metadata targets, validate DNS results, and revalidate every redirect. Do not weaken this just to close Mission A.

## 3. UNKNOWN must never become FREE
R77 correctly carried price_known=false and cost_evidence.amount_minor=null, but compatibility storage could still carry cost_minor=0. Decision/UI code must never interpret that zero as free when the status is UNKNOWN.

## 4. Search snippets are leads, not authority
Keep SEARCH_CANDIDATE semantics. SearXNG or another search provider may discover an official source, but snippet text itself must never make a plan selectable.

## 5. Do not overwrite the newer agent runtime
The 2026-09-29 authority tree already has a newer DeepSeek PLAN_ONLY runtime and 11-tool allowlist. Reuse it. Do not restore the older R77 runtime wholesale.

## Working principle
Recover R77 as capability semantics, not as a blind tree replacement.