import unittest
from decimal import Decimal

from validators import normalize_argentine_amount, parse_argentine_amount


class TestParseArgentineAmount(unittest.TestCase):
    def test_parses_argentine_thousands_and_decimal_comma(self):
        self.assertEqual(parse_argentine_amount("$339.649,70"), Decimal("339649.70"))

    def test_parses_ars_prefix_and_spaces(self):
        self.assertEqual(parse_argentine_amount("ARS 1.234,5"), Decimal("1234.50"))

    def test_parses_ungrouped_decimal_comma(self):
        self.assertEqual(parse_argentine_amount("1234,56"), Decimal("1234.56"))

    def test_parses_thousands_without_decimals(self):
        self.assertEqual(parse_argentine_amount("1.234.567"), Decimal("1234567.00"))

    def test_parses_machine_decimal_values(self):
        self.assertEqual(parse_argentine_amount("339649.70"), Decimal("339649.70"))
        self.assertEqual(parse_argentine_amount(1000), Decimal("1000.00"))

    def test_rejects_malformed_grouping(self):
        self.assertIsNone(parse_argentine_amount("12.34,56"))

    def test_rejects_too_many_decimal_digits(self):
        self.assertIsNone(parse_argentine_amount("1.234,567"))

    def test_rejects_negative_amounts(self):
        self.assertIsNone(parse_argentine_amount("-1.234,56"))

    def test_rejects_empty_or_non_amount_text(self):
        self.assertIsNone(parse_argentine_amount(""))
        self.assertIsNone(parse_argentine_amount("sin monto"))


class TestNormalizeArgentineAmount(unittest.TestCase):
    def test_normalizes_to_two_decimal_places(self):
        self.assertEqual(normalize_argentine_amount("$339.649,7"), "339649.70")
        self.assertEqual(normalize_argentine_amount(Decimal("1000")), "1000.00")

    def test_returns_none_for_invalid_value(self):
        self.assertIsNone(normalize_argentine_amount("1,234.56"))


if __name__ == "__main__":
    unittest.main()
