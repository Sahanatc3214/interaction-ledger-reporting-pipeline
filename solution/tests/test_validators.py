
import unittest

from solution.validators import (
    normalize_phone,
    normalize_date,
    normalize_decimal,
    normalize_enum
)


class TestValidators(unittest.TestCase):

    def test_phone(self):
        self.assertEqual(
            normalize_phone("9876543210"),
            "+919876543210"
        )

    def test_phone_with_country_code(self):
        self.assertEqual(
            normalize_phone("+91 9876543210"),
            "+919876543210"
        )

    def test_invalid_phone(self):
        with self.assertRaises(ValueError):
            normalize_phone("12345")

    def test_date(self):
        self.assertEqual(
            normalize_date("21/11/2026"),
            "2026-11-21"
        )

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            normalize_date("32/11/2026")

    def test_decimal(self):
        self.assertEqual(
            normalize_decimal("₹27,554"),
            "27554.00"
        )

    def test_enum(self):
        self.assertEqual(
            normalize_enum("MR", ["en", "hi", "mr"]),
            "mr"
        )


if __name__ == "__main__":
    unittest.main()
