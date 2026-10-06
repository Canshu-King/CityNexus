from app.collective_operator import classify_collective_operator_state


def test_single_traveller_is_not_collective():
    assert (
        classify_collective_operator_state(
            member_count=1,
            status=None,
        )
        == "SINGLE_TRAVELLER"
    )


def test_waiting_for_members_is_visible():
    assert (
        classify_collective_operator_state(
            member_count=3,
            status="WAITING_FOR_MEMBERS",
            response_count=1,
        )
        == "WAITING_FOR_MEMBERS"
    )


def test_disagreement_enters_mediation_not_majority_resolution():
    assert (
        classify_collective_operator_state(
            member_count=3,
            status="MEDIATION_REQUIRED",
            response_count=3,
        )
        == "MEDIATING"
    )


def test_resolved_without_receipt_is_not_yet_authorized():
    assert (
        classify_collective_operator_state(
            member_count=2,
            status="RESOLVED",
            response_count=2,
            authority_receipt_present=False,
        )
        == "COLLECTIVE_READY"
    )


def test_authority_receipt_is_distinct_terminal_boundary():
    assert (
        classify_collective_operator_state(
            member_count=2,
            status="RESOLVED",
            response_count=2,
            authority_receipt_present=True,
        )
        == "COLLECTIVE_AUTHORIZED"
    )


def test_stale_collective_decision_never_looks_authorized():
    assert (
        classify_collective_operator_state(
            member_count=2,
            status="STALE",
            response_count=2,
            authority_receipt_present=True,
            stale=True,
        )
        == "COLLECTIVE_STALE"
    )
