# GPT external check — R25 checkpoint -> live closure strike

Reviewed:
- uploaded `REVOLUTION_R25_STRATEGIC_HORIZON_STEWARD_RESULT.md`;
- remote `codex/revolution-realtrip-recovery` head and current source;
- R25 taskbook carrier branch.

## Verdict

R25 is a substantial implementation checkpoint but is not closure-grade.

The report is appropriately honest: it does NOT claim the defining machine fact
`W1 feasible -> Agent DEFER -> W2 current -> live revalidation -> Gateway -> execution -> COMPLETED`.

Do not create R26 yet. Close R25 in one bounded execution strike.

## P0 source-binding blocker: R25 code is not on GitHub

The report names:
- base: `dc93b91db9878690465349c4c2f76888870b6f49`
- final experimental code: `2a4b53a3daf958de939abec0beeb5bc453d27d3e`
- substantive commits: `26b5139b`, `2a4b53a3`

Direct GitHub inspection shows:
- remote `codex/revolution-realtrip-recovery` still points to `dc93b91db9878690465349c4c2f76888870b6f49`;
- GitHub cannot resolve `2a4b53a3daf958de939abec0beeb5bc453d27d3e`;
- current remote source contains no `remaining_opportunity_horizon`, `horizon_decision`, or `DEFERRED_FOR_HIGHER_VALUE_HORIZON`.

Therefore the implemented R25 capability currently exists only in the local experimental worktree represented by the report.

Before any runtime work:
1. verify local HEAD really contains `2a4b53a3...`;
2. verify it descends from `dc93b91d...`;
3. push the local experimental branch by fast-forward to `origin/codex/revolution-realtrip-recovery`;
4. verify the remote HEAD equals the intended R25 final code SHA.

Do not start a Git archaeology project. This should take minutes.

## Product blocker 1: the sampled Journey cannot prove R25 by construction

The sampled active Nara Journey exposed only one remaining horizon window.

No model, however capable, can prove strategic W1->W2 deferral when W2 is absent.

Stop reusing that Journey.

Create a fresh disposable real-provider Journey whose schedule intentionally contains TWO server-derivable future windows.

This is experiment construction, not a golden answer:
- the windows come from real schedule/commitment structure;
- the Agent still receives no answer Place ID;
- candidates must still be discovered/grounded through product surfaces.

## Product blocker 2: external timeout is not yet a useful machine fact

The GLM call was manually stopped after >90 seconds and no AgentRun was persisted.

Current remote runtime creates RUNNING AgentRun and only flushes before the first model call; it does not commit that row before entering the external call.

For closure:
- persist/commit the AgentRun start before the first external model request;
- use a server-owned bounded model timeout;
- on timeout persist `FAILED_EXTERNAL` with a specific timeout reason and elapsed/provider/model details;
- never translate timeout into NO_ACTION or DEFER.

This is narrow observability/resilience work, not the R25 product mission.

## Model policy for this closure

Primary attempt may use `cn:glm-5.3-flash`.

If it produces a machine-recorded provider timeout:
- do not wait indefinitely;
- do not substitute deterministic fallback prose;
- a second attempt may use the already-configured real Hermes-compatible model `cn:deepseek-v4.1-flash`, with identical mission and server facts.

R25 tests CityNexus strategic autonomy, not dependence on one specific foundation model.

Record the failed primary attempt and the successful fallback attempt separately if this occurs.

## Recommended real Nara resource conflict

Use production code with NO city-specific hardcoding. Experiment setup may choose known real provider-backed Nara rows.

A clean conflict shape is:

- W1 candidate: lower-value non-garden/culture option with known low cost;
- W2 candidate: garden option strongly supported by current TravelerTwin and materially higher cost;
- both individually feasible;
- remaining optional budget >= each individual cost;
- remaining optional budget < W1 cost + W2 cost.

For example, if the current catalog still truthfully supports the same facts:
- a ~300 JPY culture candidate for W1;
- a ~1200 JPY garden candidate for W2;
- optional remaining budget around 1300 JPY.

Do NOT force these exact Places or prices if provider facts changed.
The invariant is the resource conflict, not the names.

The main run must prove `can_take_both=false` because of a real shared resource envelope, while both individual choices remain hard-feasible.

## Two-window fixture shape

Preferred schedule:
- current executable activity;
- future C4 anchor A;
- later C4 anchor B;
- enough truthful slack before each anchor to derive W1 and W2.

After W1 DEFER:
- proceed normally through anchor A / remaining execution;
- once W2 becomes current, recalculate the Twin;
- future planning mobility from W1 is not authority for W2;
- recapture current live route facts before F4 activation.

If the product cannot express two future C4 anchors through its existing API, that is a real R25 product blocker. Fix the smallest boundary required; do not write DB rows directly for the final proof.

## Closure acceptance

Mandatory main proof:

1. remote source binding is correct;
2. fresh ACTIVE provider-backed Journey;
3. `remaining_opportunity_horizon` has exactly/at least two usable bounded windows;
4. W1 and W2 candidates are both canonical and individually hard-feasible;
5. shared time/budget means both cannot be taken;
6. current TravelerTwin makes W2 materially more valuable;
7. neutral mission contains no candidate ID/name and no TAKE/DEFER answer;
8. real Agent inspects horizon;
9. real Agent emits typed `NO_ACTION + DEFER`;
10. server re-validates strategic defer;
11. W1 plan pointer remains unchanged and no future candidate is reserved/accepted;
12. W1 resolves with a strategic defer reason;
13. execution advances until W2 is current;
14. W2 facts/mobility are revalidated under current authority rules;
15. real Agent selects/accepts W2 opportunity through normal Gateway;
16. added activity executes through HTTP state transitions;
17. protected commitments survive;
18. Journey and Twin converge to COMPLETED.

This is the R25 closure.

## Human override

After the main C path succeeds, if the model endpoint is healthy, run one comparable explicit-intent control:
- current mission explicitly prefers W1 or rejects W2;
- hard facts otherwise comparable;
- explicit mission wins over learned soft;
- strategy changes from DEFER to TAKE_NOW (or equivalent explicit-user-consistent action).

Target D, but do not sacrifice a clean C closure to hours of provider retries.

## Anti-loop rule

One closure strike.
No R25.1.
No new planner.
No new memory framework.
No new horizon subsystem.
No report series.

If two-window reality is sound and the real Agent completes the strategic path, close R25 and move on.
