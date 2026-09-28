ORD-0383 格三 - the 找回 door's write is now decided by the database, and what that claim rests on
===============================================================================================

Ruled by the commander at 02:47 on 2026-09-29 ("格三优优先…两下同时点「找回」仍无锁"), against the base
tip this lane read for itself at 02:48: `dccd13ad66ea35e9a6d7ca7a3d91a1ae9a579808`.

What changed, in one line each
------------------------------

* before: `journey.deleted_at = None` then `session.commit()` - a read-then-write of an ORM object,
  with the door's own docstring admitting it ("Two taps at once are still unguarded, as in slice 1").
* after: one `UPDATE ... WHERE id = ? AND deleted_at = <the moment this tap read>`, judged by
  `.rowcount`, retried against a fresh read up to `_UNDELETE_WRITE_ATTEMPTS` times, and a refusal by
  name when it cannot win.  The shape is the one this file already prescribes in
  `_accept_replan_executing` ("Conditional writes, not object assignment") and already uses in
  `_take_over_lapsed_claims`, `select_plan` and `_trip_studio_accept_impl`.  No new mechanism, no new
  `error.code`, and no new `reason_code`: the two refusals are the `JOURNEY_NOT_DELETED` /
  `JOURNEY_ALREADY_DELETED` pair the product already answers with.

Which arm proves what (numbers in `READINGS_r1.json`, produced by `readout_r1.py`)
---------------------------------------------------------------------------------

| arm | base tip, unfixed | this lane, fixed |
|---|---|---|
| `test_two_taps_fired_together_keep_the_invariant_and_one_audit_row_per_success` | 1 failed | 1 passed |
| `test_the_two_taps_window_really_overlaps_instead_of_being_asserted` | 1 passed | 1 passed |
| `test_a_tap_that_cannot_win_names_its_refusal_and_never_reaches_a_framework_five_hundred` | 1 passed | 1 passed |
| `test_the_single_tap_path_is_unchanged_by_the_predicate` | 1 passed | 1 passed |

Only the first row is a discriminator, and this file says so instead of implying four.  The reason
it can be trusted is the second row: it measures the window rather than asserting it.  In both trees
12 of 12 rounds had the two taps actually inside the door at the same time
(`overlapping_rounds=12`), and in that same shape the unfixed door let **both** taps answer 200 in
12 of 12 rounds (`double_success=12`), while the fixed one let both win in 0 of 12
(`double_success=0`, `unnamed_refusal=0`, `audit_row_mismatch=0`).  The slowest first tap in a round
was 0.0856 s unfixed and 0.0940 s fixed, so the fix did not buy its result by being slow.  A green on arm 1 without arm 2
would have been a coincidence, and arm 2 fails loudly if the transport ever serialises the taps.

The hammer arm answered `codes=[200, 204, 409]` in both trees - `undelete_taps=50 delete_taps=50
successes=47 audit_rows=47` unfixed, `undelete_taps=53 delete_taps=59 successes=47 audit_rows=47`
fixed - so `audit_rows == successes` holds under churn either way.  That makes it a "never a 500,
never a silent success" guard, not evidence about the race; the race is arm 1's job.

Whole backend suite, one command, two trees
-------------------------------------------

    PYTHONPATH=<tree>:<tree>/backend python -X utf8 -m pytest backend/tests -q

* base tip `dccd13ad...`: 1436 collected, `10 failed, 1410 passed, 15 skipped, 1 xfailed`.
* this candidate:         1440 collected (+4, the four arms above), `9 failed, 1415 passed`.
* disappeared: 1, new: 0.

The disappeared one is **not** claimed as a fix.  It is
`backend/tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation`,
which spawns five processes and shares one operation; run by itself it passed twice in the base tree
and twice in this tree (`1 passed` x4), so it is order/isolation-sensitive inside a whole-suite run and
independent of this change.  Its sibling `test_qoder_g3_xproc_http.py::...share_one_operation` is red
in both runs, unchanged.

The one assertion of mine that the order forced me to re-take
------------------------------------------------------------

`backend/tests/test_qoder_ord0399_journey_undelete.py::test_this_door_did_not_borrow_the_recovery_or_restore_words`
pinned the literal `deleted_at = None` inside the door as its "this door really clears the column"
sentinel.  Replacing the assignment with the predicate removed that literal, so the arm went red while
saying nothing about vocabulary.  It now accepts either spelling of the clear (`.values(deleted_at=None)`
or the assignment).  That is a widened anchor, so it is paired with two mutants that both still bite:

* `mut_no_clear` (predicate writes `deleted_at=seen`, i.e. never clears): the re-taken arm red, **and**
  arm 1 red with the store proving it (`('2026-09-28T19:11:36.432906+00:00', [200, 200])` - the trip
  stayed in the bin and both taps claimed success).
* `mut_borrowed_word` (audit action renamed to `journey.restored`): the arm red with "the audit action
  this door writes changed name", and the behavioural audit arm red too.

格一 (the false sentence inside the byte-frozen door): measured, not executed
-----------------------------------------------------------------------------

The ruling was 乙 - move the sentence out, leave the protected bytes alone, do not re-cut
`review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json`.  Those three cannot all hold, and this is the
measurement rather than an argument:

* the claim "the query below is the only place on this tree that filters the column, and no other
  module under `backend/app` reads it" sits at `backend/app/main.py:2961`-`:2962`, which is inside the
  972-byte span the arm compares (the arm's span runs from the `@app.get("/api/v1/journeys"...)`
  decorator to the `@app.delete(...)` decorator, so the docstring is part of what is frozen);
* in a private copy of the base tip, the arm on the untouched file: `1 passed`;
* in the same copy, after deleting those two lines from the door and placing the true list of readers
  above the decorator (which is exactly 乙): `AssertionError: list_journeys moved - the order forbids
  changing this door`.

So 乙 is not executable as written.  The two that are:

* 甲 - edit the docstring and re-cut the baseline record with
  `review/ord0402-readouts/make_list_door_baseline_artifact_r1.py <tip>` (it refuses to write unless
  the new and old segments agree, which is why it cannot quietly bless a moved door); or
* 丙 - narrow the arm's protected span to the door's signature and query, leaving the docstring
  outside the frozen bytes.  This one I will not choose myself: it changes what constraint ① covers,
  and "not one word" was your sentence, not mine.

Nothing in `list_journeys` was touched by this delivery.  The false sentence is still there, and it is
still false - named here and in the block, and left alone pending one word of ruling.

格二 (the bin's `TEXT` ordering vs the contract's "newest first") was recorded by the ruling and not
ticketed, so it is untouched here: no sort change, no contract change, no baseline re-cut.

Store and discipline
--------------------

Every arm above answers against the temporary database the pytest process declares for itself in
`backend/tests/conftest.py` (`sqlite:///<temp>/suite.db`, printed by its report header), built through
the product's own `POST /api/v1/journeys`.  `demo/reset` 0 calls; `_preview.db` and `_live.db` 0 opens;
no read-only backup of a shared store was needed for this cell, so none was taken; other lanes'
worktrees, branches and processes 0 touched; the authoritative line 0 bytes; credentials 0 printed;
ports 0 opened - the concurrency is inside one process, and no arm needs a listening socket.
Free-space note: this lane added three trees today - `_qoder_ord0383_lock_ctl` 272 MB (five copied
trees for the controls), `_qoder_lane_ord0383_lock_base` 132 MB (the pristine baseline worktree) and
`_qoder_lane_ord0383_lock` 132 MB (the delivery) - measured by `du -sm` at 03:15, so about 536 MB of
D: is this cell's.  All of it is scratch this lane owns and can be removed once the cell is landed;
`df -h D:` read 15 GiB free before the work and at the same level after it.
