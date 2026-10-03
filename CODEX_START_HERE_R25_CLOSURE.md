# CODEX START HERE — R25 Live Closure Strike

Read:

1. `GPT_R25_CHECKPOINT_EXTERNAL_CHECK.md`
2. `revolution/R25_LIVE_CLOSURE_STRIKE.md`

Before implementation/runtime work, output:

- `TASKBOOK_READ`
- local HEAD
- remote `origin/codex/revolution-realtrip-recovery` HEAD
- whether local `2a4b53a3daf958de939abec0beeb5bc453d27d3e` exists
- whether `dc93b91d...` is its ancestor
- configured Agent provider/model
- estimate authority value
- one sentence explaining why the old one-window Journey can never prove R25
- one sentence explaining why a provider timeout must be persisted as failure rather than treated as NO_ACTION
- one sentence confirming that a real alternate configured model is allowed after a recorded timeout, but deterministic fallback prose is not

Then:

1. push/bind the R25 source;
2. make timeout machine-visible if needed;
3. create the fresh two-window Journey;
4. assert both windows and resource conflict BEFORE model call;
5. run the real Agent;
6. drive W2 through live revalidation and execution;
7. update the existing R25 result only.

Do not start R26.
