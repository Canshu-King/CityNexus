"""Continuation choices for missing facts, not an authorization or execution layer.

The model chooses among feasible next moves. The gateway still authenticates,
reserves budgets transactionally, and enforces each tool's actual side effects.
This module never turns estimates into observations or a draft into an active plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class GapKind(str, Enum):
    FACT = "FACT"
    USER_CHOICE = "USER_CHOICE"
    CAPABILITY = "CAPABILITY"


@dataclass(frozen=True)
class Gap:
    key: str
    kind: GapKind = GapKind.FACT
    blocks_commit: bool = False


@dataclass(frozen=True)
class Continuation:
    can_publish_provisional: bool
    commit_blockers: tuple[str, ...]
    tool_options: tuple[str, ...]
    user_questions: tuple[str, ...]
    next_state: str
    evidence_grade: str = "PROVISIONAL_NOT_VERIFIED"


_TOOL_CHOICES = ("research_place_sources", "acquire_place_facts", "estimate_place_facts")


def continuation_options(
    gaps: tuple[Gap, ...], *, granted_tools: frozenset[str],
    attempts: Mapping[str, int], attempts_per_tool: int = 2,
    remaining_steps: int = 8, allow_lab_estimates: bool = False,
) -> Continuation:
    """Expose alternatives rather than returning a global BLOCKED result.

    `granted_tools` must come from server policy, never model arguments. Its
    presence is not proof an invocation is currently authorized. The caller
    intersects this output with real runtime availability and final gateway checks.
    An absent prerequisite suspends only dependent actions; existing drafts,
    maps, conversation, and unrelated research can remain useful.
    """
    if attempts_per_tool < 1 or remaining_steps < 0:
        raise ValueError("Invalid continuation budget")
    if any(not gap.key.strip() for gap in gaps):
        raise ValueError("Gap keys must be nonempty")
    if len({gap.key for gap in gaps}) != len(gaps):
        raise ValueError("Gap keys must be unique")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in attempts.values()):
        raise ValueError("Attempt counts must be nonnegative integers")
    blockers = tuple(gap.key for gap in gaps if gap.blocks_commit)
    questions = tuple(gap.key for gap in gaps if gap.kind is GapKind.USER_CHOICE)
    have_facts_to_research = any(gap.kind is GapKind.FACT for gap in gaps)
    options = tuple(
        name for name in _TOOL_CHOICES
        if have_facts_to_research and remaining_steps > 0 and name in granted_tools
        and attempts.get(name, 0) < attempts_per_tool
        and (name != "estimate_place_facts" or allow_lab_estimates)
    )
    if options:
        state = "CONTINUE_RESEARCH_WITH_PROVISIONAL_RESULT"
    elif questions:
        state = "ASK_TARGETED_CHOICE_KEEP_OTHER_WORK"
    elif gaps:
        state = "DELIVER_PARTIAL_WITH_OPEN_QUESTIONS"
    else:
        state = "READY_FOR_ACTION_SPECIFIC_VALIDATION"
    # Publication remains provisional; can_publish is never authorization to commit.
    return Continuation(True, blockers, options, questions, state)
