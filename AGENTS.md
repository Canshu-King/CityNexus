# Codex / Qoder: THIS BRANCH IS A REAL HUMAN UNBLOCK TASK

**Only for `fix/revolution-first-human-e2e-20261015`.**

Read `trial/tasks/20261015_CODEX_FIRST_REAL_HUMAN_JOURNEY_RESCUE.md` before editing anything. GitHub Issue: https://github.com/Canshu-King/CityNexus/issues/19.

## Owner and mission

Codex owns **code + actual browser/backend verification**. Qoder should not independently rewrite the trial interface or integrate into the Qoder product line during this fix. Any Qoder handoff must be a minimal named backend blocker approved by the Codex issue.

The real user has repeatedly failed to finish the first Revolution outing, most recently seeing:

> 这一步没有完成。请检查网络后重试，已保存的行程不会因此消失。

This is an unacceptable generic error from `frontend/src/trial/RevolutionQuickExplore.tsx::messageForError`. The root cause of the failed request is **not established**: get the exact method/path/status and a safe reason from actual requests before guessing.

### Work, don't supervise work

1. First reproduce the actual failed screen against the isolated local trial app, diagnose the first failing HTTP request, and **fix the product code**.
2. A new user must be able to open `/revolution`, optionally request real Hermes read-only AI guidance, search `连城`, tap the actual Nominatim result **once** to enter the next screen even with blank map tiles, query public POIs **only on one clear explicit click**, save two genuine sourced stops, enter GO, then reload to see the same member's durable progress.
3. Replace non-actionable red bars with human-readable phase-specific errors and a single recovery action. Degrade without the AI provider, do not silently retry paid providers or make up LIVE_PROVIDER truth.
4. Confirm correctness with **real signed backend + browser** (not only mocked requests), desktop + mobile screenshots, deliberate failure injection, then narrow tests, typecheck/build. Report EXACT evidence grades rather than only counts.
5. Commit and push working code to this branch. File a PR **into** `trial/revolution-first-look-20261014`, and write `trial/results/20261015_FIRST_HUMAN_JOURNEY_RESULT.md` stating clearly at the very top whether the user can actually progress.
6. Never delete/overwrite user `trial/.runtime`, DB, `frontend/package-lock.json`, keys, or local machines. Keep permissions, signed-member isolation, no GPS fake proof, and no paid commerce.

**Stop writing verifier taskbooks in place of fixing the user's problem.** Spend time fixing the visible journey, not reopening the historical ORD/R-series acceptance archive.

**IMPORTANT:** This AGENTS.md and GitHub Issue do not automatically start Codex. Codex must be invoked in a capable local/cloud coding environment; once invoked, the work above is the required plan.
