# GPT external check — R27 v3 final checkpoint

Reviewed:
- CityNexus-Revolution-R27-Final-20261005-v3.zip;
- delivered runtime DB backend/r27-live-20261005-d.sqlite3;
- remote head 8710b39ced686e398ac8cebff1a127f04722d29f;
- Truth Mesh acquisition;
- plan-delta collective scoring;
- collective mutation gate;
- select_plan / accept_replan / activate_standby call sites;
- real cn:glm-5.3-flash AgentRun.

## Verdict

R27 is very close, but not closed.

What is now machine-proven:
- two MEMBER_IN_FORCE members carry distinct journey-scoped preferences;
- exact world facts are grounded through live provider identity + official source truth;
- Overpass failure no longer necessarily kills exact identity truth when Nominatim proves the exact OSM ref;
- collective scoring uses PLAN_DIFF rather than all shared background activities;
- the server mutation boundary enforces collective mediation;
- a non-dominant alternative was rejected with COLLECTIVE_CANDIDATE_NOT_DOMINANT;
- the allowed plan physically executed to Journey COMPLETED.

This is a real collective-governance proof.

What is NOT machine-proven:
- a real Agent did not mediate while the shared Journey was ACTIVE;
- the only real Agent run happened after Journey COMPLETED and correctly chose NO_ACTION;
- HUMAN_TRADEOFF_REQUIRED has no end-to-end member-resolution path;
- collective_mutation_gate accepts resolved_decision in theory, but no production mutation call site supplies one;
- no durable WAITING_FOR_MEMBERS -> RESOLVED shared decision exists.

Therefore the exact remaining blocker is:

R27_AGENT_COLLECTIVE_LIVE_MEDIATION_NOT_CLOSED

Do not start R28.

## V3 runtime facts verified from SQLite

Journey:
6b3f8094-7123-49a1-8774-88a279f1a8aa

Members:
- OWNER 505ca82f-2009-467b-ab9b-c1ea2334a36a: interest/garden
- ADMIN 14eec2cf-fd5b-4a81-a1c6-d72e234b6610: interest/museum

Selected plan:
293a4de2-ed4e-5a78-8da2-5bd2b5d33f59

Physical execution:
- Isuien Garden COMPLETED
- Nara Craft Museum COMPLETED
- Journey COMPLETED

Real Agent:
1d34510e-ce37-43ab-9813-966e7f8bef1b
cn:glm-5.3-flash

Tool trace:
inspect_journey
-> inspect_twin
-> conclude_recovery(NO_ACTION)

That run saw both member preferences, but it ran after completion. It is a control only.

## V3 compromise is legitimate

The selected v3 plan contains:
- Isuien Garden;
- Nara Craft Museum.

OWNER fit = 1.0.
ADMIN fit = 1.0.

That is not a fake average; when time and budget permit both experiences, "do both" is a legitimate collective solution.

Do not invalidate this receipt.

However it was deterministic setup/selection, not Agent mediation.

## Why the last strike should use a true trade-off

The existing R22 OPPORTUNITY_WINDOW path is ideal.

An F4 opportunity insertion adds one optional Place.

With:
- OWNER preferring garden;
- ADMIN preferring museum;

and two individually grounded candidates:
- one garden;
- one museum;

the server must honestly classify HUMAN_TRADEOFF_REQUIRED.

Do NOT contort preferences to manufacture a unanimous candidate.
Do NOT search for a conveniently dual-tagged Place just to avoid clarification.

R27 should now prove that CityNexus can govern a conflict it cannot optimize away.

## Required final capability

real ACTIVE shared Journey
-> SYSTEM_DERIVED OPPORTUNITY_WINDOW
-> real Agent inspects separate member preferences
-> Agent discovers/acquires at least two feasible choices
-> request_replan creates bounded real proposals
-> server returns HUMAN_TRADEOFF_REQUIRED
-> Agent requests shared decision
-> mission becomes WAITING_FOR_MEMBERS
-> each relevant member answers only their own slot
-> all required responses align on a server-derived option
-> decision becomes RESOLVED
-> child mission resumes
-> real Agent accepts the exact resolved proposal
-> collective mutation gate revalidates the decision
-> normal policy/Gateway authority
-> physical execution
-> Journey completes

That closes R27-C.

## Do not overclaim R27-D

The repository still lacks a proven traveler caller-principal seam for member answer HTTP calls.

A path member_id is not authentication.

For this closure:
- prove member-scoped decision slots and server state integrity;
- explicitly state transport principal authentication remains unproven;
- do not invent X-Traveler-ID security.

R27-C is the mandatory target.
