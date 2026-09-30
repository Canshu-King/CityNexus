# How to rebuild the two counter-example trees (they are deliberately not committed)

CE-1 (`mutgen4`): hardlink-copy `backend/ data/ contracts/ frontend/src/generated` out of the
candidate tree, break the hardlink on `backend/app/main.py`, and inside `create_journey_checkin`
replace the six-line `existing = session.scalars(...).first()` with `existing = None`.  The runner is
`gen4_ce1_r1.py`; the tree-difference proof is `gen4_ce1_tree_proof_r1.json` (423 files compared, only
`backend/app/main.py` differing).

CE-2 (`wt8` + `faces/o0500_clientbool`): copy the candidate frontend tree, break the hardlink on
`frontend/src/features/trip/TripItinerary.tsx`, and in `reloadStamps` build the mark map from
`plan.activities` where `status === "COMPLETED"` instead of from `answer.stamps`.  Build with
`gen4_build_r1.py` (the fourth face) and run `gen4_carrier_r1.py`, which serves the delivered spec
over it.  The arm that bites is `ord0500-2`, and it says so with the row count and the mark count in
its own message.

Both are throwaway: neither is committed, and the delivered `main.py` is hashed before and after in
the CE-1 receipt to show the mutant never touched it.
