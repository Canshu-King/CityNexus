"""The journey's budget is a divisor, so an unstated one must not be measured against 1.

`backend/app` scored `budget_fit` against `max(1, journey.budget_amount_minor)` in four
places, and `replanning/verified_scoring.py` handed out a full 1.0 when the budget was
zero. Both turn "the traveller never said" into a confident number that downstream
consumers cannot distinguish from a real score. These arms assert the honest reading.
"""

from __future__ import annotations

import pytest

from app.core.budget_fit import BUDGET_FIT_NEUTRAL, budget_fit_for, budget_penalty_for
from app.replanning.verified_scoring import score_replan_candidate


def _score(**overrides):
    envelope = {
        "journey_end_slack_min": 30,
        "robust": True,
        "budget_remaining_minor": 95_000,
    }
    envelope.update(overrides.pop("envelope", {}))
    return score_replan_candidate(
        base_activity_count=0,
        moved_count=1,
        removed_count=0,
        added_count=0,
        travel_delta_min=0,
        after_envelope=envelope,
        commitments_preserved=True,
        **overrides,
    )


def test_unstated_budget_is_not_a_score():
    assert budget_fit_for(0, 5_000) is None
    assert budget_fit_for(None, 5_000) is None


def test_stated_budget_still_scores():
    assert budget_fit_for(100_000, 5_000) == pytest.approx(0.95)
    assert budget_fit_for(5_000, 5_000) == pytest.approx(0.0)
    assert budget_fit_for(5_000, 20_000) == pytest.approx(0.0)


def test_unstated_budget_carries_no_penalty():
    assert budget_penalty_for(0, 5_000) == pytest.approx(0.0)
    assert budget_penalty_for(100_000, 5_000) == pytest.approx(0.015)


def test_replan_score_leaves_budget_unanswered_when_unstated():
    result = _score(budget_amount_minor=0, envelope={"budget_remaining_minor": -5_000})

    assert result.breakdown["budget_fit"] == pytest.approx(BUDGET_FIT_NEUTRAL)
    assert result.breakdown["budget_fit_declared"] is False


def test_replan_score_keeps_the_real_score_when_stated():
    result = _score(budget_amount_minor=100_000)

    assert result.breakdown["budget_fit"] == pytest.approx(0.95)
    assert "budget_fit_declared" not in result.breakdown


def test_replan_score_treats_a_missing_remaining_as_unanswered():
    result = _score(
        budget_amount_minor=100_000,
        envelope={"budget_remaining_minor": None},
    )

    assert result.breakdown["budget_fit_declared"] is False
