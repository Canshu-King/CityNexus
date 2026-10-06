# Revolution R32 deterministic core result

## Scope

Implemented the deterministic RecoveryEpoch core on
`gpt/revolution-r32-autonomous-recovery-mesh`. The live R30/R31 strike and all
external model calls were intentionally not run.

## RecoveryEpoch facts

- `recovery_epochs` is server-owned and Journey-scoped with generation,
  reality fingerprint, actionable trigger ids, lifecycle status, and close
  reason.
- SQLite enforces at most one `OPEN` row per Journey with a partial unique
  index. Concurrent creation converges by reloading the database winner.
- The reality projection contains active plan/current activity and canonical
  actionable Event facts; resolved/irrelevant observation churn is excluded.
- AgentRun, ReplanProposal, CollectiveAuthorityReceipt, ActionApproval, and
  AgentPendingAction carry the nullable legacy-compatible epoch binding.
- Final replan mutation re-reads the current open epoch inside the Journey
  write boundary. Stale work returns typed `RECOVERY_EPOCH_SUPERSEDED` facts and
  is not converted into provider failure or generic partial work.
- Executable plans use a normalized semantic identity for candidate
  deduplication while retaining duplicate discovery rows and provenance.

## Validation

The R32 deterministic workflow runs the new RecoveryEpoch tests and the R28,
R29, R30, R31, runtime-state, runtime-gate, and mission-runtime regression
tests. No live strike was executed in this change.
