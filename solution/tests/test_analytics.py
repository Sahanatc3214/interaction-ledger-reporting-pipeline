
import unittest

from solution.analytics import add_effective_dispositions


class TestAnalytics(unittest.TestCase):

    def test_latest_override_is_effective(self):

        calls = [{
            "workflow_id": "motor_renewal",
            "dispositions": [
                {
                    "event_type": "disposition.set",
                    "occurred_at": "2026-11-13T10:00:00+05:30",
                    "code": "renewed"
                },
                {
                    "event_type": "disposition.override",
                    "occurred_at": "2026-11-13T11:00:00+05:30",
                    "code": "not_interested"
                }
            ]
        }]

        result = add_effective_dispositions(calls)

        self.assertEqual(
            result[0]["effective_disposition"],
            "not_interested"
        )

        self.assertTrue(result[0]["is_terminal"])
        self.assertFalse(result[0]["is_success"])

    def test_latest_set_when_no_override(self):

        calls = [{
            "workflow_id": "motor_renewal",
            "dispositions": [
                {
                    "event_type": "disposition.set",
                    "occurred_at": "2026-11-13T10:00:00+05:30",
                    "code": "callback_requested"
                },
                {
                    "event_type": "disposition.set",
                    "occurred_at": "2026-11-13T11:00:00+05:30",
                    "code": "renewed"
                }
            ]
        }]

        result = add_effective_dispositions(calls)

        self.assertEqual(
            result[0]["effective_disposition"],
            "renewed"
        )

        self.assertTrue(result[0]["is_success"])

    def test_no_disposition(self):

        calls = [{
            "workflow_id": "motor_renewal",
            "dispositions": []
        }]

        result = add_effective_dispositions(calls)

        self.assertIsNone(
            result[0]["effective_disposition"]
        )

        self.assertFalse(result[0]["is_success"])


if __name__ == "__main__":
    unittest.main()
