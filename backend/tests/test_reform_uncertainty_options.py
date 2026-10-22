"""Local policy-choice tests; no model/provider calls or claims of live delivery."""
import importlib.util
import sys
from pathlib import Path
import unittest

SOURCE = Path(__file__).parents[1] / "app/agent/uncertainty_options.py"
spec = importlib.util.spec_from_file_location("uncertainty_options", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Gap, GapKind, options = module.Gap, module.GapKind, module.continuation_options


class ContinuationTests(unittest.TestCase):
    def decide(self, gaps=(), **kwargs):
        params = {"granted_tools": frozenset(), "attempts": {}}
        params.update(kwargs)
        return options(gaps, **params)

    def test_unknown_hours_do_not_disable_provisional_work(self):
        result = self.decide((Gap("hours", blocks_commit=True),))
        self.assertTrue(result.can_publish_provisional)
        self.assertEqual(result.commit_blockers, ("hours",))
        self.assertEqual(result.next_state, "DELIVER_PARTIAL_WITH_OPEN_QUESTIONS")

    def test_research_can_continue_before_formal_plan_exists(self):
        result = self.decide((Gap("hours"),), granted_tools=frozenset({"research_place_sources"}))
        self.assertEqual(result.tool_options, ("research_place_sources",))

    def test_one_exhausted_tool_does_not_end_other_research(self):
        result = self.decide((Gap("hours"),), granted_tools=frozenset({"research_place_sources", "acquire_place_facts"}), attempts={"research_place_sources": 2})
        self.assertEqual(result.tool_options, ("acquire_place_facts",))

    def test_grants_are_not_invented(self):
        self.assertEqual(self.decide((Gap("price"),)).tool_options, ())

    def test_estimates_require_explicit_lab_scope(self):
        params = {"granted_tools": frozenset({"estimate_place_facts"})}
        self.assertEqual(self.decide((Gap("price"),), **params).tool_options, ())
        self.assertEqual(self.decide((Gap("price"),), allow_lab_estimates=True, **params).tool_options, ("estimate_place_facts",))

    def test_estimates_never_upgrade_evidence_or_remove_blockers(self):
        result = self.decide((Gap("price", blocks_commit=True),), allow_lab_estimates=True, granted_tools=frozenset({"estimate_place_facts"}))
        self.assertEqual(result.evidence_grade, "PROVISIONAL_NOT_VERIFIED")
        self.assertEqual(result.commit_blockers, ("price",))

    def test_only_human_choices_become_questions(self):
        result = self.decide((Gap("open_hours"), Gap("budget_preference", GapKind.USER_CHOICE)))
        self.assertEqual(result.user_questions, ("budget_preference",))

    def test_budget_exhaustion_still_delivers_partial(self):
        result = self.decide((Gap("hours"),), granted_tools=frozenset({"acquire_place_facts"}), remaining_steps=0)
        self.assertTrue(result.can_publish_provisional)
        self.assertFalse(result.tool_options)

    def test_no_gaps_is_not_automatic_commit_permission(self):
        self.assertEqual(self.decide().next_state, "READY_FOR_ACTION_SPECIFIC_VALIDATION")

    def test_duplicate_gaps_and_invalid_counts_are_rejected(self):
        with self.assertRaises(ValueError): self.decide((Gap("x"), Gap("x")))
        with self.assertRaises(ValueError): self.decide(attempts={"x": -1})
        with self.assertRaises(ValueError): self.decide(remaining_steps=-1)

if __name__ == "__main__":
    unittest.main()
