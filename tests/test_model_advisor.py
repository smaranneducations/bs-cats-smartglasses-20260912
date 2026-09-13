"""Safety boundaries for the offline advisory policy; no paid integrations."""

import importlib.util
import unittest
from pathlib import Path


script = Path(__file__).resolve().parents[1] / "scripts" / "model_advisor.py"
spec = importlib.util.spec_from_file_location("model_advisor", script)
advisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(advisor)


class ModelAdvisorTests(unittest.TestCase):
    def test_deterministic_work_does_not_require_quota_or_model(self):
        result = advisor.advise("deterministic", available_models=[], remaining_usage_percent=0)
        self.assertEqual(result["action"], "use_deterministic_tool")
        self.assertIsNone(result["model"])

    def test_consequential_risk_cannot_inherit_a_cheap_task_route(self):
        result = advisor.advise("documentation", risk="critical")
        self.assertEqual(result["tier"], "complex")

    def test_missing_required_model_does_not_downgrade_or_upgrade(self):
        result = advisor.advise("security", available_models=["gpt-5.6-luna", "gpt-6-astra"])
        self.assertEqual(result["action"], "resolve_model_availability")
        self.assertIsNone(result["model"])

    def test_low_usage_defers_consequential_work(self):
        result = advisor.advise("publishing_controls", remaining_usage_percent=5)
        self.assertEqual(result["action"], "defer_model_work")
        self.assertEqual(result["tier"], "review")
        self.assertIsNone(result["model"])

    def test_exhausted_quota_also_stops_small_model_recommendations(self):
        result = advisor.advise("documentation", remaining_usage_percent=0)
        self.assertEqual(result["action"], "defer_model_work")

    def test_attempts_have_a_terminal_boundary(self):
        last = advisor.advise("feature", failed_attempts=2)
        stopped = advisor.advise("feature", failed_attempts=3)
        self.assertEqual(last["suggested_limits"]["attempts_remaining"], 1)
        self.assertEqual(stopped["action"], "stop_and_replan")
        self.assertIsNone(stopped["model"])

    def test_invalid_inputs_do_not_silently_choose_a_route(self):
        for kwargs in (
            {"task": "unknown"},
            {"task": "feature", "risk": "unknown"},
            {"task": "feature", "failed_attempts": -1},
            {"task": "feature", "remaining_usage_percent": float("nan")},
            {"task": "feature", "available_models": "gpt-5.6-terra"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                advisor.advise(**kwargs)

    def test_output_does_not_claim_to_have_switched_or_priced_a_model(self):
        result = advisor.advise("feature")
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["model_switched"])
        self.assertFalse(result["pricing_verified"])
        self.assertFalse(result["availability_verified"])
        self.assertEqual(result["api_calls_made"], 0)


if __name__ == "__main__":
    unittest.main()
