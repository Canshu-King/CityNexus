# How to rebuild the two counter-example trees (never committed)

CE-1 -- backend mutant mutgen6: hardlink-copy backend/, data/, contracts/ and frontend/src/generated/
out of the delivered candidate wt16, BREAK the hardlink on backend/app/main.py (os.remove then a byte
copy -- writing through the shared inode would edit wt16 itself), then replace the six-line
existing = session.scalars(...).first() inside create_journey_checkin with existing = None.
Run gen7_ce1_r1.py for the pytest pair and gen7_ce1_proof_r1.py for the tree-difference receipt.
The receipt exists because an earlier pair produced a fourth mutant red caused by a file the
throwaway tree did not carry (frontend/src/generated/api.ts, read by the accepted contract arm):
a missing file is an instrument artifact, not a finding.

CE-2 -- front-end mutant wt18 and its face faces/o0500_clientbool7: copy the candidate tree, break the
hardlink on frontend/src/features/trip/TripItinerary.tsx, and in reloadStamps build the mark map from
plan.activities where status === "COMPLETED" instead of from answer.stamps. Build with
gen7_build_r1.py (third entry of FACES) and run gen7_carrier_r1.py, which serves the delivered spec
over a real backend. The arm that bites is ord0500-2 and its message carries both counts.

CE-3 (this round) -- the exposure ruler, three runs of the same instance:
node <cmdr live_checks>/ui_exposure_taint_ast_r7b.cjs --tree <tree>/frontend --out <file>
against the pristine tip worktree, the previous generation's candidate and the fixed one.
