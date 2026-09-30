# How to rebuild the two counter-example trees (they are deliberately not committed)

Both live in this lane's directory `D:/moodle/_qoder_phone_ord0485_20260930`, next to the delivered
candidate tree `wt9` (tip `822db3d9f07b9c7d535e12afbdeb3074dd94acb2` + this order's changes).

CE-1 -- the backend mutant `mutgen5`: hardlink-copy `backend/ data/ contracts/
frontend/src/generated` out of `wt9`, BREAK the hardlink on `backend/app/main.py` (`os.remove` then
`copyfile`; a plain in-place write would edit `wt9` through the shared inode), and inside
`create_journey_checkin` replace the six-line `existing = session.scalars(...).first()` with
`existing = None`.  Run `gen5_ce1_r1.py` for the pytest pair and `gen5_ce1_proof_r1.py` for the
tree-difference receipt (`gen5_ce1_tree_proof_r1.json`: 424 files compared, only
`backend/app/main.py` differing).  The proof exists because the first pair produced a fourth mutant
red caused by a file the throwaway tree did not carry (`frontend/src/generated/api.ts`, read by the
accepted contract arm) -- a missing file is an instrument artifact, not a finding.

CE-2 -- the front-end mutant `wt10` and its face `faces/o0500_clientbool5`: copy the candidate tree,
break the hardlink on `frontend/src/features/trip/TripItinerary.tsx`, and in `reloadStamps` build the
mark map from `plan.activities` where `status === "COMPLETED"` instead of from `answer.stamps`.  Build
it with `gen5_build_r1.py` (third entry of its FACES list) and run `gen5_carrier_r1.py`, which serves
the delivered spec over a real backend.  The arm that bites is `ord0500-2`, and its own message
carries the row count and the mark count.

Both are throwaway: neither is committed, and `gen5_ce1_r1.py` hashes the delivered `main.py` before
and after the whole pair to show the mutant never touched it.
