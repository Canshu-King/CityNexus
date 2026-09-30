# ORD-0519 readings, computed from the two receipts in this directory

journeys_visible_after_board=3
cities_on_board=3
invariant_three_journeys=true
invariant_no_replay_as_supply=true
invariant_live_calls_credited_to_answered_leg=true
invariant_one_city_no_attempt=true

## per-leg readings, good board
leg city=CN-TIANJIN query=cafe leg=photon http_status=200 bytes=396 elapsed_ms=4703.0 outcome=ANSWERED
leg city=CN-TIANJIN query=cafe leg=nominatim http_status=None bytes=None elapsed_ms=None outcome=SKIPPED
anchor_source city=CN-TIANJIN query=cafe source=photon_city_anchor provenance=LIVE_PROVIDER candidates=8 overpass=CAPTURED nominatim_state=SKIPPED photon_state=CAPTURED
leg city=CN-TIANJIN query=museum leg=none http_status=None bytes=None elapsed_ms=None outcome=NOT_ASKED_THIS_CALL_CACHE_HIT
anchor_source city=CN-TIANJIN query=museum source=None provenance=LIVE_PROVIDER candidates=8 overpass=NOT_ASKED_THIS_CALL nominatim_state=NOT_ASKED_THIS_CALL photon_state=NOT_ASKED_THIS_CALL
leg city=CN-BEIJING query=museum leg=photon http_status=200 bytes=380 elapsed_ms=4797.0 outcome=ANSWERED
leg city=CN-BEIJING query=museum leg=nominatim http_status=None bytes=None elapsed_ms=None outcome=SKIPPED
anchor_source city=CN-BEIJING query=museum source=photon_city_anchor provenance=LIVE_PROVIDER candidates=3 overpass=CAPTURED nominatim_state=SKIPPED photon_state=CAPTURED
leg city=CN-BEIJING query=cafe leg=none http_status=None bytes=None elapsed_ms=None outcome=NOT_ASKED_THIS_CALL_CACHE_HIT
anchor_source city=CN-BEIJING query=cafe source=None provenance=LIVE_PROVIDER candidates=3 overpass=NOT_ASKED_THIS_CALL nominatim_state=NOT_ASKED_THIS_CALL photon_state=NOT_ASKED_THIS_CALL

## cells
cell city=CN-TIANJIN kind=supplied place_rows=11 activities=10 optimizer=ORTOOLS_CP_SAT anchor_sources=['photon_city_anchor']
cell city=CN-BEIJING kind=supplied place_rows=3 activities=10 optimizer=ORTOOLS_CP_SAT anchor_sources=['photon_city_anchor']
cell city=CN-FUZHOU kind=no_supply_attempt_by_design place_rows=None activities=None optimizer=None anchor_sources=None

## mutant M1: the answering leg masked away, fresh store
m1_stop_reason=PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES
m1_seen_provenance=REPLAY
m1_failure_stage=anchor_geocode
m1_fallback_reason=PROVIDER_BAD_RESPONSE
m1_photon_http_status=None
m1_photon_leg_outcome=NOT_ANSWERED_ConnectError
m1_named_cell=NO_REAL_PLACES_ON_THIS_SERVER
m1_rc=4
