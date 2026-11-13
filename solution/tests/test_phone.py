import unittest

from solution.validators import normalize_phone


class TestPhoneNormalization(unittest.TestCase):

    def test_standard_phone(self):
        self.assertEqual(
            normalize_phone("9876543210"),
            "+919876543210"
        )

    def test_phone_with_country_code(self):
        self.assertEqual(
            normalize_phone("+91 9876543210"),
            "+919876543210"
        )

    def test_phone_with_leading_zero(self):
        self.assertEqual(
            normalize_phone("09876543210"),
            "+919876543210"
        )

    def test_phone_with_separators(self):
        self.assertEqual(
            normalize_phone("91-98765-43210"),
            "+919876543210"
        )

    def test_empty_phone(self):
        self.assertIsNone(normalize_phone(""))

    def test_invalid_phone(self):
        with self.assertRaises(ValueError):
            normalize_phone("1234567890")

    def test_phone_with_wrong_length(self):
        with self.assertRaises(ValueError):
            normalize_phone("987654321")


if __name__ == "__main__":
    unittest.main()