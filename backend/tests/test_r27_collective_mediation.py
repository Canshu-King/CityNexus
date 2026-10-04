from app.collective_mediation import classify_group_decision, fairness_receipt


def _candidate(candidate_id: str, a: float, b: float, *, status: str = "GROUNDED_FEASIBLE"):
    return {
        "candidate_id": candidate_id,
        "status": status,
        "member_fits": {
            "member-a": {"effective_fit": a},
            "member-b": {"effective_fit": b},
        },
    }


def test_r27_fairness_receipt_does_not_hide_a_severe_loser_in_mean():
    candidates = [_candidate("garden", 1.0, 0.0), _candidate("craft", 0.0, 1.0)]
    fairness_receipt(candidates)
    assert candidates[0]["fairness"]["minimum_member_fit"] == 0.0
    assert candidates[0]["fairness"]["unacceptable_member_ids"] == ["member-b"]
    assert classify_group_decision(candidates)["classification"] == "HUMAN_TRADEOFF_REQUIRED"


def test_r27_compromise_is_available_only_when_worst_member_is_protected():
    candidates = [_candidate("garden", 1.0, 0.2), _candidate("craft", 0.2, 1.0), _candidate("shared", 0.7, 0.7)]
    result = classify_group_decision(candidates)
    assert result["classification"] == "COMPROMISE_AVAILABLE"
    assert result["selected_candidate_id"] == "shared"


def test_r27_unknown_world_facts_never_become_a_group_preference_question():
    candidates = [_candidate("unknown", 0.9, 0.9, status="REVALIDATION_REQUIRED")]
    assert classify_group_decision(candidates)["classification"] == "INSUFFICIENT_WORLD_FACTS"
