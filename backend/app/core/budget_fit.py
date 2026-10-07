"""Honest budget fit for a Journey whose budget may never have been stated.

`Journey.budget_amount_minor` is NOT NULL with a `>= 0` check, and the create
payload's `Money.amount_minor` only enforces `ge=0`, so zero is a state the
product itself can store: the traveller never gave a budget. Dividing by
`max(1, budget)` there quietly measures the plan against an invented 1 minor
unit, which turns "nobody said" into a confident number.
"""

from __future__ import annotations

#: Carried in place of a score when the journey states no budget. The replanning
#: scorer already uses 0.5 for an unanswered preference/opportunity axis, so the
#: same neutral keeps "not answered" from reading as "answered, and mediocre".
BUDGET_FIT_NEUTRAL = 0.5


def budget_fit_for(budget_amount_minor: int | None, total_cost_minor: int) -> float | None:
    """How well the total cost fits the stated budget.

    Returns ``None`` when the journey states no budget, so callers can carry
    "not answered" instead of a fabricated score. A stated budget of 0 is a real
    answer and is scored as such.
    """
    if budget_amount_minor is None or budget_amount_minor <= 0:
        return None
    return max(0.0, min(1.0, 1.0 - (total_cost_minor / budget_amount_minor)))


def budget_penalty_for(budget_amount_minor: int | None, total_cost_minor: int) -> float:
    """The share of a score that an unaffordable plan should lose on budget.

    Zero when no budget was stated: without a budget there is nothing to measure
    affordability against, so the term contributes nothing rather than a guess.
    """
    fit = budget_fit_for(budget_amount_minor, total_cost_minor)
    if fit is None:
        return 0.0
    return (1.0 - fit) * 0.30