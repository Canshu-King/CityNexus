from app.execution.in_transit_reroute import (
    classify_transit_deviation,
    deviation_threshold_m,
    reroute_origin_authority,
    reroute_semantic_key,
)


def test_not_en_route_is_inactive():
    decision = classify_transit_deviation(
        activity_status="IN_PROGRESS",
        location_source="FOREGROUND_WEB",
        location_fresh=True,
        accuracy_m=20,
        route_shape_available=True,
        distance_to_route_m=500,
    )
    assert decision.state == "INACTIVE"


def test_missing_location_is_explicit():
    decision = classify_transit_deviation(
        activity_status="EN_ROUTE",
        location_source=None,
        location_fresh=False,
        accuracy_m=None,
        route_shape_available=True,
        distance_to_route_m=None,
    )
    assert decision.state == "LOCATION_UNAVAILABLE"


def test_missing_route_shape_never_fakes_deviation():
    decision = classify_transit_deviation(
        activity_status="EN_ROUTE",
        location_source="FOREGROUND_WEB",
        location_fresh=True,
        accuracy_m=25,
        route_shape_available=False,
        distance_to_route_m=None,
    )
    assert decision.state == "ROUTE_SHAPE_UNAVAILABLE"
    assert decision.material is False


def test_foreground_location_far_from_route_is_advisory_only():
    decision = classify_transit_deviation(
        activity_status="EN_ROUTE",
        location_source="FOREGROUND_WEB",
        location_fresh=True,
        accuracy_m=30,
        route_shape_available=True,
        distance_to_route_m=500,
    )
    assert decision.state == "ADVISORY_DEVIATION"
    assert decision.authoritative is False
    assert decision.material is False


def test_trusted_single_outlier_does_not_immediately_become_incident():
    decision = classify_transit_deviation(
        activity_status="EN_ROUTE",
        location_source="DEVICE_ATTESTED",
        location_fresh=True,
        accuracy_m=20,
        route_shape_available=True,
        distance_to_route_m=500,
        consecutive_deviation_count=1,
    )
    assert decision.state == "POSSIBLE_VERIFIED_DEVIATION"
    assert decision.material is False


def test_trusted_persistent_deviation_can_be_authoritative():
    decision = classify_transit_deviation(
        activity_status="EN_ROUTE",
        location_source="LOCATION_ATTESTED",
        location_fresh=True,
        accuracy_m=20,
        route_shape_available=True,
        distance_to_route_m=500,
        consecutive_deviation_count=2,
    )
    assert decision.state == "VERIFIED_DEVIATION"
    assert decision.authoritative is True
    assert decision.material is True


def test_near_target_prefers_arrival_flow():
    decision = classify_transit_deviation(
        activity_status="EN_ROUTE",
        location_source="DEVICE_ATTESTED",
        location_fresh=True,
        accuracy_m=20,
        route_shape_available=True,
        distance_to_route_m=500,
        consecutive_deviation_count=2,
        near_target=True,
    )
    assert decision.state == "ARRIVAL_READY"
    assert decision.material is False


def test_dynamic_threshold_respects_accuracy():
    assert deviation_threshold_m(accuracy_m=10) == 150.0
    assert deviation_threshold_m(accuracy_m=80) == 240.0


def test_reroute_origin_authority_keeps_foreground_advisory():
    assert reroute_origin_authority("FOREGROUND_WEB") == "ADVISORY_ROUTE"
    assert reroute_origin_authority("DEVICE_ATTESTED") == "TRUSTED_CURRENT_LOCATION_ROUTE"


def test_reroute_semantic_key_is_stable_for_same_location_generation():
    first = reroute_semantic_key(
        journey_id="j1",
        activity_id="a1",
        location_observation_id="loc1",
        target_place_id="p1",
        mode="walk",
    )
    second = reroute_semantic_key(
        journey_id="j1",
        activity_id="a1",
        location_observation_id="loc1",
        target_place_id="p1",
        mode="WALK",
    )
    assert first == second
