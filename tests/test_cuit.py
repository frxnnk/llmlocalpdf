import unittest

from validators import is_valid_cuit, normalize_cuit


class TestNormalizeCuit(unittest.TestCase):
    def test_removes_common_separators(self):
        self.assertEqual(normalize_cuit("20-12345678-6"), "20123456786")
        self.assertEqual(normalize_cuit("20.123.45678.6"), "20123456786")
        self.assertEqual(normalize_cuit(" 20 12345678 6 "), "20123456786")

    def test_preserves_non_numeric_characters_for_validation(self):
        self.assertEqual(normalize_cuit("20-12345678-A"), "2012345678A")


class TestIsValidCuit(unittest.TestCase):
    def test_accepts_valid_cuit_digits(self):
        self.assertTrue(is_valid_cuit("20123456786"))

    def test_accepts_valid_cuit_with_separators(self):
        self.assertTrue(is_valid_cuit("20-12345678-6"))

    def test_rejects_invalid_checksum(self):
        self.assertFalse(is_valid_cuit("20-12345678-9"))

    def test_rejects_wrong_length(self):
        self.assertFalse(is_valid_cuit("2012345678"))
        self.assertFalse(is_valid_cuit("201234567860"))

    def test_rejects_non_numeric(self):
        self.assertFalse(is_valid_cuit("20-12345678-A"))

    def test_rejects_empty_value(self):
        self.assertFalse(is_valid_cuit(""))


if __name__ == "__main__":
    unittest.main()
