
import unittest

from solution.event_processor import normalize_event_timestamp


class TestEventTimestamps(unittest.TestCase):

    def test_utc_timestamp(self):
        self.assertEqual(
            normalize_event_timestamp("2026-11-13T10:00:00Z"),
            "2026-11-13T15:30:00+05:30"
        )

    def test_ist_timestamp(self):
        self.assertEqual(
            normalize_event_timestamp("2026-11-13T10:00:00+05:30"),
            "2026-11-13T10:00:00+05:30"
        )

    def test_naive_timestamp_is_treated_as_ist(self):
        self.assertEqual(
            normalize_event_timestamp("2026-11-13 10:00:00"),
            "2026-11-13T10:00:00+05:30"
        )

    def test_missing_timestamp(self):
        self.assertIsNone(normalize_event_timestamp(None))

    def test_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            normalize_event_timestamp("not-a-timestamp")


if __name__ == "__main__":
    unittest.main()
