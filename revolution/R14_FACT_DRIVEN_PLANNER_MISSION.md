# Revolution R14 — Fact-Driven Planner

## Why this is the next Revolution

R13 proved a new real city (Nara) can hydrate exact provider-backed Places with official facts, generate AUTO candidates, capture LIVE Valhalla mobility, select a plan, and show it in the real UI. The remaining product limitation is no longer “can we get truth?” but “does the planner actually use that truth intelligently?”

At commit `d075a4cd8796c9e297866fa87374eea4dd856e39`, the strict catalogue planner still:
- filters to visit-eligible Places with opening windows and verified cost;
- sorts eligible Places by earliest opening time, then `place.id`;
- greedily packs the day;
- creates at most three variants by rotating that deterministic ordering;
- assigns candidate score dimensions from a static `metrics_list`, not from the chosen Places, travel, budget, preference, or fact quality.

That means a newly hydrated Place can become eligible without becoming preferred. The system has real-world evidence but still ranks with an early-demo skeleton.

## Mission

Replace the real-city AUTO candidate construction/scoring path with a fact-driven planner while preserving hard authority gates.

The result must make a user preference materially change the chosen candidate in a fresh Nara run, using only provider-backed Places and LIVE used-edge mobility.

## Do not create another ORD loop

- one capability branch;
- inline fixes for blocking defects;
- one final report;
- no branch-per-parser-case;
- no report-only rounds;
- no broad-suite archaeology unless the candidate introduces a regression.

## Phase A — make candidate generation evidence-aware

Keep all hard eligibility rules intact. UNKNOWN must remain UNKNOWN and non-selectable when relevant.

For strict real-city AUTO planning, replace `earliest opening + place.id` as the primary selection logic with a bounded objective that can use real inputs such as:
1. user/traveler preference fit (categories/interests actually present in current product state);
2. LIVE travel minutes for used edges;
3. verified admission cost and budget headroom;
4. opening-window slack / schedule robustness;
5. fact completeness/authority quality;
6. diversity of activity categories;
7. optional value for high-confidence official-source facts.

Do not invent ratings or quality scores that the providers did not supply.

A simple beam search / bounded combinatorial search over the eligible catalogue is acceptable and preferred over a giant new framework. The point is to escape the current greedy rotation, not to build a research optimizer.

## Phase B — replace static candidate scores

The existing `metrics_list` constants must not be the public explanation for real-city candidates.

For provider-backed real-city plans, compute score dimensions from the actual candidate:
- `budget_fit`: from verified total cost vs Journey budget;
- `mobility_fit`: from LIVE used-edge travel burden;
- `time_reliability`: from opening-window slack and schedule fit;
- `preference_fit`: from actual traveler/journey preference evidence when available, otherwise explicitly neutral/unknown rather than fabricated precision;
- `robustness`: from schedule slack / provider degradation / hard constraints;
- `commitment_preservation`: from actual commitment/anchor preservation;
- `opportunity_value`: from bounded real signals only; do not invent venue ratings.

If one dimension has no real basis, represent that honestly in explanation/score provenance. Do not silently substitute a magic constant and call it measured.

Fixture/demo paths may retain legacy deterministic constants if necessary for compatibility. The Revolution target is the real provider-backed catalogue path.

## Phase C — prove the Nara facts influence planning

Use the existing disposable Nara scenario as a diagnostic, not as the only success claim.

The currently verified Places include at least:
- 依水園 — official source, 09:30–16:30, 120000 JPY minor;
- 第一次大極殿院復原事業情報館 — verified free;
- なら工藝館 — verified free;
- きっづ光科学館ふぉとん — verified free;
- 奈良市杉岡華邨書道美術館 — 30000 JPY minor;
- 名勝旧大乗院庭園 — 20000 JPY minor.

Create two materially different user preference profiles / requests, for example:
- garden / heritage / calm walking;
- craft / museum / indoor culture.

The generated top candidate should change for a reason traceable to those preferences and real travel/budget/opening facts.

Do not hardcode Nara names into planner logic.

## Phase D — source binding hardening for autonomous use

R13 operator-bound sources are sufficient for an isolated experiment but not yet a fully autonomous source-discovery claim.

Current `_requested_fact_source_binding` can construct `matched_provider_entity=true` from an operator-supplied URL. That is an approval boundary, not independent identity proof.

Keep operator binding, but make provenance explicit:
- `OPERATOR_BOUND_EXACT_ENTITY` for human-confirmed source URLs;
- `PROVIDER_BOUND_EXACT_URL` when the URL comes from the exact Overpass/Nominatim entity website/contact tag;
- a separate candidate state for discovered/search URLs that are not yet corroborated.

Do not let an arbitrary operator-supplied URL be described as autonomously provider-proven.

If feasible in this round, add one automatic corroboration path based on exact entity + provider website tag or exact municipal page identity. Do not block the planner mission on building a universal web identity engine.

## Phase E — finish the Japanese parser edges inline

`d075a4cd` is a valid minimal fix for the concrete `1,200円 ... 介添え者無料` bug, but add bounded regressions for common Japanese forms before calling the parser stable:
- full-width digits / separators: `１，２００円`;
- prefixed currency: `￥1,200`, `¥1,200`;
- audience ordering where child/student/free text can appear before the general/adult price;
- annual pass / rental / optional-service prices near the admission section must not override the general admission price;
- explicit general/adult price should win over disability/companion/child free exceptions;
- truly free admission must remain known-free, not UNKNOWN.

Prefer a small audience-aware admission parser over accumulating precedence hacks. For default Journey budgeting, select a clearly labeled `一般` / `大人` / general admission price when present. If no default audience price can be identified unambiguously, return UNKNOWN rather than the cheapest incidental amount.

Do not let this parser work consume the majority of the round.

## Acceptance test — Revolution, not review

The round closes only when all of the following are machine facts:
1. fresh provider-backed real-city AUTO generation still works;
2. all selected Places are authority-eligible;
3. all actual used edges retain LIVE provider provenance;
4. changing user preference materially changes the top candidate or its ordering in an explainable way;
5. candidate score/explanation values are derived from actual plan facts, not static `metrics_list` constants;
6. budget changes can change feasibility/ranking without UNKNOWN becoming FREE;
7. source provenance distinguishes operator-bound from automatically provider-bound facts;
8. Japanese mixed paid/free pages no longer select incidental free or secondary-audience price as the default admission price;
9. real UI shows the selected candidate and a concise “why this plan” explanation grounded in actual facts.

## Aggressive stretch goal

After the fact-driven planner works in Nara, run one second unseeded city without adding city-specific planner code. The goal is to demonstrate that the new planner is a general engine, not a Nara optimizer.

## Final deliverable

One file: `REVOLUTION_R14_FACT_DRIVEN_PLANNER_RESULT.md`.

Report only:
- base/final SHA;
- real city/cities used;
- preference inputs;
- eligible Place set;
- generated top candidates and why they differ;
- score provenance per dimension;
- used mobility provenance;
- source-binding provenance classes;
- focused tests + candidate-vs-base broad-suite delta;
- genuine remaining blocker, if any.

Success sentence:

> CityNexus no longer merely schedules whichever verified places happen to sort first; it uses real user intent and real provider facts to choose and explain a materially better real-world itinerary.
