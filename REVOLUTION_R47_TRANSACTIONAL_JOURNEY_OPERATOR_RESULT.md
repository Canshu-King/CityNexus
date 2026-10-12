# REVOLUTION R47 — Transactional Journey Operator Result

## Outcome

`TRANSACTIONAL_OPERATOR_SANDBOX_RECOVERED`

The Operator now carries an accepted recovery through a frozen, server-owned commerce saga. It creates the replacement sandbox booking first, then cancels the old refundable booking, and returns to `WATCHING` only after both actions are terminal.

## Fresh product experiment

- Environment: captured replay, `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`, AI disabled, explicit `LAB_SANDBOX_PROVIDER`.
- Operator started in `WATCHING`. One `LAB_FIXTURE` disruption produced a traffic-delay recovery proposal.
- Accepted recovery compiled a `WAITING_FOR_APPROVAL` plan with two actions: `CREATE_BOOKING` then `CANCEL_BOOKING`.
- One `USER_CONFIRMATION` approval was consumed. Continuation reported `model_call_count: 0`.
- Final execution state: `COMPLETED`; Operator projection: `WATCHING`.
- Old booking became `CANCELLED` and its Commitment became `CANCELLED`; replacement booking became `CONFIRMED` with a new `ACTIVE` Commitment.
- Every action and booking projection identified `LAB_SANDBOX_PROVIDER`; no live merchant claim was made.

## Implementation

- Durable `RecoveryExecutionPlan` and `RecoveryExecutionAction` rows with semantic idempotency fingerprints and scoped approval.
- Normal commerce booking/cancellation services remain the only mutation path. Active Journey booking is permitted only through the explicit transactional recovery executor.
- Saga states cover waiting, executing, completed, safe failure, partial application, and attention-required outcomes. No fake rollback is performed.
- Operator projection/UI shows action counts, provider provenance, approval state, and completion copy without raw ProviderCall payloads.
- Approval continuation resumes the frozen plan directly and does not invoke another model or reinterpret intent.

## Verification

- Backend focused suites: `21 passed` (transactional operator, projection, and authority action contracts).
- Frontend TypeScript typecheck: passed.
- Focused Playwright: `2 passed` (`r47-transactional-operator.spec.ts`, including the real-seed dependency).
- Fresh experiment: passed with the JSON receipt next to this report.

## Limits

This is a captured replay and sandbox provider experiment. It demonstrates transactional semantics and Booking/Commitment convergence, not live merchant connectivity.
