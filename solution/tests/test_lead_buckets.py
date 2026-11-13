
import unittest

from solution.analytics import (
    get_call_statistics,
    add_effective_dispositions,
    calculate_lead_statistics
)


class TestLeadBuckets(unittest.TestCase):

    def test_bucket_results(self):

        calls = get_call_statistics()
        calls = add_effective_dispositions(calls)

        leads = calculate_lead_statistics(calls)

        buckets = {lead["bucket"] for lead in leads}

        expected_buckets = {
            "yet_to_reach_out",
            "completed",
            "in_progress_dialed",
            "in_progress_telephony_failed"
        }

        self.assertEqual(buckets, expected_buckets)


if __name__ == "__main__":
    unittest.main()
