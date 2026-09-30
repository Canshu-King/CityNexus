# ORD-0519 readings, computed from the four receipts in this directory

journeys_visible_after_board=3
cities_on_board=3
invariant_three_journeys=true
invariant_no_replay_as_supply=true
invariant_live_calls_credited_to_answered_leg=true
invariant_one_city_no_attempt=true

## good board (default order photon,nominatim)
leg city=CN-TIANJIN query=cafe leg=photon http_status=200 bytes=396 elapsed_ms=4703.0 outcome=ANSWERED
leg city=CN-TIANJIN query=cafe leg=nominatim http_status=None bytes=None elapsed_ms=None outcome=SKIPPED
credit city=CN-TIANJIN query=cafe source=photon_city_anchor provenance=LIVE_PROVIDER candidates=8 overpass=CAPTURED nominatim_state=SKIPPED photon_state=CAPTURED
leg city=CN-TIANJIN query=museum leg=none http_status=None bytes=None elapsed_ms=None outcome=NOT_ASKED_THIS_CALL_CACHE_HIT
credit city=CN-TIANJIN query=museum source=None provenance=LIVE_PROVIDER candidates=8 overpass=NOT_ASKED_THIS_CALL nominatim_state=NOT_ASKED_THIS_CALL photon_state=NOT_ASKED_THIS_CALL
leg city=CN-BEIJING query=museum leg=photon http_status=200 bytes=380 elapsed_ms=4797.0 outcome=ANSWERED
leg city=CN-BEIJING query=museum leg=nominatim http_status=None bytes=None elapsed_ms=None outcome=SKIPPED
credit city=CN-BEIJING query=museum source=photon_city_anchor provenance=LIVE_PROVIDER candidates=3 overpass=CAPTURED nominatim_state=SKIPPED photon_state=CAPTURED
leg city=CN-BEIJING query=cafe leg=none http_status=None bytes=None elapsed_ms=None outcome=NOT_ASKED_THIS_CALL_CACHE_HIT
credit city=CN-BEIJING query=cafe source=None provenance=LIVE_PROVIDER candidates=3 overpass=NOT_ASKED_THIS_CALL nominatim_state=NOT_ASKED_THIS_CALL photon_state=NOT_ASKED_THIS_CALL

## cells of the good board
cell city=CN-TIANJIN kind=supplied place_rows=11 activities=10 optimizer=ORTOOLS_CP_SAT
cell city=CN-BEIJING kind=supplied place_rows=3 activities=10 optimizer=ORTOOLS_CP_SAT
cell city=CN-FUZHOU kind=no_supply_attempt_by_design place_rows=None activities=None optimizer=None

## credit pair F: only nominatim allowed to anchor, category mirror then failed
f_leg nominatim http_status=200 outcome=ANSWERED elapsed_ms=844.0
f_credit source=nominatim_city_anchor provenance=REPLAY photon_state=None
f_named_cell=NO_REAL_PLACES_ON_THIS_SERVER
f_exit_code=4

## mutant G: the only allowed leg is masked to a dead port
g_leg_photon outcome=NOT_ANSWERED_ConnectError http_status=None
g_credit source=None provenance=REPLAY
g_stop_reason=PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES
g_exit_code=4

## mutant M1 (first run of this shape, kept for the record)
m1_stop_reason=PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES
m1_photon_leg_outcome=NOT_ANSWERED_ConnectError
m1_failure_stage=anchor_geocode
m1_exit_code=4
