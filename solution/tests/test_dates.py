import unittest

from solution.validators import normalize_date


class TestDateNormalization(unittest.TestCase):

    def test_iso_date(self):
        self.assertEqual(
            normalize_date("2026-11-21"),
            "2026-11-21"
        )

    def test_slash_date(self):
        self.assertEqual(
            normalize_date("21/11/2026"),
            "2026-11-21"
        )

    def test_dash_date(self):
        self.assertEqual(
            normalize_date("21-11-2026"),
            "2026-11-21"
        )

    def test_month_name_date(self):
        self.assertEqual(
            normalize_date("21-Nov-2026"),
            "2026-11-21"
        )

    def test_empty_date(self):
        self.assertIsNone(normalize_date(""))

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            normalize_date("31/02/2026")

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            normalize_date("November 21, 2026")


if __name__ == "__main__":
    unittest.main()