from app.agent.recovery_discovery import recovery_surface_decision


def test_zero_grounded_options_expands():
    d = recovery_surface_decision(
        options=[],
        discovery_attempted=False,
    )
    assert d.should_expand is True
    assert d.state == "NO_GROUNDED_OPTION"


def test_single_grounded_option_expands_for_collective_choice():
    d = recovery_surface_decision(
        options=[
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p1",
                "fit_subject_place_ids": ["museum-a"],
            }
        ],
        discovery_attempted=False,
        collective_choice_needed=True,
    )
    assert d.should_expand is True
    assert d.state == "SINGLE_GROUNDED_OPTION"


def test_single_grounded_option_is_enough_when_no_meaningful_choice_required():
    d = recovery_surface_decision(
        options=[
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p1",
                "fit_subject_place_ids": ["museum-a"],
            }
        ],
        discovery_attempted=False,
        collective_choice_needed=False,
    )
    assert d.should_expand is False


def test_duplicate_semantic_proposals_do_not_fake_two_options():
    d = recovery_surface_decision(
        options=[
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p1",
                "fit_subject_place_ids": ["museum-a"],
                "fit_subject_tags": ["indoor"],
            },
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p2",
                "fit_subject_place_ids": ["museum-a"],
                "fit_subject_tags": ["indoor"],
            },
        ],
        discovery_attempted=False,
        collective_choice_needed=True,
    )
    assert d.grounded_option_count == 1
    assert d.should_expand is True


def test_two_materially_distinct_grounded_options_do_not_expand():
    d = recovery_surface_decision(
        options=[
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p1",
                "fit_subject_place_ids": ["museum-a"],
            },
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p2",
                "fit_subject_place_ids": ["garden-b"],
            },
        ],
        discovery_attempted=False,
        collective_choice_needed=True,
    )
    assert d.state == "SUFFICIENT_GROUNDED_OPTIONS"
    assert d.should_expand is False


def test_one_bounded_attempt_can_end_honestly_exhausted():
    d = recovery_surface_decision(
        options=[
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p1",
                "fit_subject_place_ids": ["museum-a"],
            }
        ],
        discovery_attempted=True,
        collective_choice_needed=True,
    )
    assert d.state == "DISCOVERY_EXHAUSTED"
    assert d.should_expand is False


def test_provider_degradation_does_not_destroy_existing_option():
    d = recovery_surface_decision(
        options=[
            {
                "status": "GROUNDED_FEASIBLE",
                "plan_id": "p1",
                "fit_subject_place_ids": ["museum-a"],
            }
        ],
        discovery_attempted=True,
        discovery_degraded=True,
        collective_choice_needed=True,
    )
    assert d.state == "DISCOVERY_DEGRADED"
    assert d.grounded_option_count == 1
    assert d.should_expand is False
