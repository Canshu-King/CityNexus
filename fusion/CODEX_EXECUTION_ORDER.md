# CODEX — Unified Fusion Journey/Agent/Phone Order (2026-10-14)

Read `fusion/UNIFIED_FUSION_CHARTER.md` first. Revolution has shown serious product work; the failure was delivery to normal users. **Your assignment is to make the one fused application expose and execute it**, not to start R110 or a new verifier campaign.

Work on `fusion/codex-journey-20261014`; do not touch `commander/control`, Qoder's mirror, old Revolution branches, or the canonical integration branch directly. Qoder owns the parallel import branch; rebase/cherry-pick reviewed Qoder PR(s) safely when integrating, never overwrite their newer product fixes.

## First actions
1. Verify exact source SHAs from charter and establish isolated worktree with fresh DB and no reused backend; inventory Revolution normal-UI entrypoints, routes, backend operations, signed auth, migrations and provider configuration. Confirm R108 and GPT reviewer corrections in `a5a2f109...`. R109 is a taskbook, not shipped.
2. Run smallest necessary baseline tests: R107/R108 affected backend slices and one 390x844 signed browser action. Check `npm run typecheck:all`, Vite build, app compile. Do not run R58-R106 archival history to prove again.
3. Build the **one mobile user experience** that resolves the classroom failure: after sign-in and opening/creating an ordinary Journey, a visible 'Explore city / Start a Pocket Walk' action leads to the real-city source-aware discovery and R107 direct-save, then R108 GO. Add a real user-facing landing/route; no debug/developer-only path.
4. Ensure the unified navigation preserves Qoder's Today/Map/Trips/Copilot/Wallet/Me when Qoder import lands. Normal app must clearly expose both full Journey Operator and simple Pocket Walk without pretending they are identical workflows. Pocket Walk remains DRAFT/no PlanVersion; ACTIVE Journey operator is separate.
5. Integrate external Agent/Guardian truth to ordinary UI, respecting the current authority and status. When the configured Hermes/DeepSeek model is unavailable, show not available and usable alternative, not simulated autonomous completion. Have at least one bounded controlled disruption acceptance after integration, and optionally a real Agent if actually configured with operator approval. Do NOT leak credentials.
6. Keep discovery explicit opt-in: city/public map center and separate provider consent; no GPS sent silently; TEST_PROVIDER never relabelled LIVE. Two navigation/map permissions separate; no physical arrival proof; signed A/B cannot leak Pocket Walk or private detour.
7. Prove with one fresh backend + Playwright and a user-operated mobile HTTPS staging build. Direct actual phone acceptance requires the user/runner with physical device; report it as pending until observed, not something the browser test automatically certifies.
8. Deliver `fusion/CODEX_RESULT.md`, implementation SHAs, user-flow walkthrough, actual consent/provenance, test results, blocking errors, PR. Review Qoder transplant for any overwrites of R108 fixes and shared auth/PlanVersion/AgentGateway.

## Required integrated journey path
Normal app -> authenticated Journey (or safe DRAFT creation) -> public city chosen by user -> exact external provider disclosure and opt-in -> source-labelled places -> TWO public stops -> persisted private Pocket Walk -> GO progression -> separate map app launch consent -> reopen/reload restores self-report -> other signed member cannot read. No provider call for a cancelled consent. If LIVE provider unavailable, show the genuinely controlled demo with big 'Sample/test locations' label rather than perform unapproved live calls.

Secondary path: ACTIVE Journey -> one 'Take care of this trip' Operator entry -> controlled clearly LAB-labelled incident -> investigates -> requires proper authority -> executes exact approved change -> continues watching, OR truthfully shows external model blocked. Never invent a proposal to make the demo green.

## Stops
Do not package this as feature-complete if Qoder core pages are gone, even if Revolution tests pass. No direct prod deploy, no force push, no uncontrolled user DB mutation. Each merged unit must increase unified user-accessible capability.
