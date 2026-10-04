# Revolution R27 — Collective Journey Mediator

## Checkpoint

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Base SHA: `e135c5cba3c4860f69767f784324a759da395805`
- Final experimental code SHA: `09550ac461ea7e9a566a5ed0b0c9992aece57091`
- Taskbook: `origin/gpt/revolution-r27-collective-journey-mediator-20261004`
- Mission blob SHA: `922a263453c504d801648dcec87ed179345b891d`
- Agent chain: WB2api / Hermes-compatible, `cn:glm-5.3-flash` -> `cn:deepseek-v4.1-flash`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- P7 remains false; no authority/mainline merge was made.

## Implemented product change

The shared Journey surface is now member-aware rather than owner-Twin-aware:

- Journey creation creates an explicit OWNER `JourneyMember`.
- `inspect_journey` and `inspect_twin` return only `MEMBER_IN_FORCE` members.
- Each member carries its own `member_id`, `traveler_id`, role, server-derived `JourneyRoleCapability` values, journey-scoped explicit preferences, and compact learned-soft/conflict context.
- Owner mission preferences are not copied to collaborators.
- Withdrawn or lapsed members disappear from the in-force mediation projection while their membership row remains auditable.
- Candidate evaluation returns per-member explicit and learned contributions, minimum fit, maximum regret, mean fit, and unacceptable member IDs.
- Deterministic classification is `UNANIMOUS_DOMINANCE`, `COMPROMISE_AVAILABLE`, `HUMAN_TRADEOFF_REQUIRED`, `AUTHORITY_CONFLICT`, or `INSUFFICIENT_WORLD_FACTS`.
- The classifier does not average away a severe loser and does not treat UNKNOWN/revalidation-required facts as feasible.
- R26 skip hygiene is preserved: physical routing state is respected, EN_ROUTE fails closed, new adjacency requires a live provider capture, and clarified strategic skips are marked `CLARIFIED_HORIZON_CHOICE` with `preference_learning_eligible=false`.

## Runtime evidence

### Member isolation and configured Agent runtime

Disposable runtime DB: `backend\r27-runtime-20261004.sqlite3`.

Fresh demo shared Journey inspection produced two independent in-force members:

- Owner traveler: `11111111-1111-4111-8111-111111111111`; role `OWNER`; capabilities included `JOURNEY_UPDATE` and `MEMBER_MANAGE`.
- Collaborator traveler: `97750eb1-d523-4a2f-b9d8-44d57967df0f`; role `COLLABORATOR`; capabilities were server-derived and did not include owner-only mutation authority.

The collaborator's journey-scoped `craft` preference appeared only under that collaborator. After withdrawal, the collective projection contained only the owner. A real `cn:glm-5.3-flash` run inspected the shared Journey and Twin through:

`inspect_journey -> inspect_twin -> list_replans -> conclude_recovery`

The run was persisted by the Hermes-compatible runtime. It correctly found no current member conflict in that control Journey and selected a typed `NO_ACTION`. This is an Agent/context proof, not the R27 product closure claim: that control was a draft demo Journey and used no live shared-plan execution.

### Fresh live Nara shared Journey

- Journey: `378ea8dc-7121-4e80-b321-b0ebc426b6a9`
- Owner: `57730d77-68a9-44fe-b4f3-b6c0c2bb2686`
- Second member: `c04d92e4-1356-43dc-8ef5-acddb0aea3ae`, role `ADMIN`
- Discovery: live Overpass; no seeded golden itinerary was added.
- Secondary identity: live Nominatim lookup matched exact Overpass entities.
- Mobility policy: live Valhalla required for any executable candidate; no mock mobility was used.

The bounded acquisition run produced the following machine facts:

| Place | Provider identity | Opening | Cost | Result |
|---|---|---|---|---|
| `real-place-22cf72809897ff4c7f312fcf` / 依水園 | `overpass:way/97082272` | `NORMALIZED_VALID` | `KNOWN`, 1200 JPY | usable fact candidate |
| `real-place-e5c0ef1d8ffb8a8bd6fac3ee` / 吉城園 | `overpass:way/97082273`; Nominatim exact match | `NORMALIZED_VALID` | `UNKNOWN` | not authority-eligible |
| `real-place-343ee994da6a2014af11b3ed` / 東洋民俗博物館 | `overpass:node/1423069493`; Nominatim exact match | `UNKNOWN` | `UNKNOWN` | not authority-eligible |

For the museum acquisition, the receipt was:

- Overpass answered HTTP 200.
- Nominatim secondary source was `ACQUIRED` and `matched_provider_entity=true`.
- Official web source was `NO_SOURCE_URL`.
- Search source was `UNCONFIGURED`.
- `known_opening_count=0`, `known_cost_count=0`.

No UNKNOWN cost was converted to free, and no synthetic opening or mobility evidence was promoted.

## Exact current blocker

`R27_REAL_SHARED_COMPROMISE_NOT_CLOSED`

The current fresh Nara catalog has only one place with both canonical opening and canonical cost. Other real provider entities can be identified and corroborated, but their opening and/or cost facts remain UNKNOWN. Therefore the deterministic gate cannot produce the required pair of materially different, individually `GROUNDED_FEASIBLE` candidates. Without that pair:

- no honest per-member conflict/compromise decision exists;
- no compromise Place can be selected by the Agent;
- no Gateway activation or shared Journey execution is claimed;
- no member clarification is issued merely to hide a world-fact gap.

This is a provider-fact frontier, not a majority-vote or owner-Twin defect.

## Focused verification

Executed with Python 3.13:

```text
63 passed, 1 warning
```

Covered:

- R20 standby trigger authority
- R21 autonomous future synthesis
- R22 opportunity capture
- R23 adaptive TravelerTwin
- R24 adaptive memory
- R25 strategic horizon
- R26 decision-critical clarification
- R27 collective mediation arithmetic
- R27 member surface isolation
- R27 skip hygiene and live post-skip routing boundary

Also passed:

- `compileall -q app`
- `git diff --check`

## Next bounded experiment

Keep the same member-aware mediation branch. Use the Agent's bounded search/source path to acquire a second real Nara candidate with canonical opening and cost, or pivot once to another fresh city if the provider frontier remains unavailable. Only after two individually `GROUNDED_FEASIBLE` candidates exist should the real Agent be allowed to arbitrate compromise and enter the normal Gateway/execution path.
