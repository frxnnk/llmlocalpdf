import copy
import json
import unittest
from pathlib import Path

from golden_eval import compare_result, load_json, summarize_report


FIXTURE_DIR = Path(__file__).parent / "fixtures"
EXPECTED_PATH = FIXTURE_DIR / "expected" / "simple_transfer.json"


class TestGoldenEval(unittest.TestCase):
    def test_fixture_exact_fields_match(self):
        expected = load_json(EXPECTED_PATH)

        report = compare_result(expected, expected)

        self.assertTrue(report["passed"])
        self.assertEqual(report["score"], 1.0)
        self.assertEqual(report["missing_fields"], [])
        self.assertEqual(report["mismatches"], [])

    def test_missing_critical_fields_are_reported(self):
        expected = load_json(EXPECTED_PATH)
        actual = copy.deepcopy(expected)
        del actual["instrucciones"][0]["movimiento"]["destinoFondos"]["identificador"]

        report = compare_result(actual, expected)

        self.assertFalse(report["passed"])
        self.assertIn(
            "instrucciones[0].movimiento.destinoFondos.identificador",
            report["missing_fields"],
        )

    def test_score_summary_is_deterministic(self):
        expected = load_json(EXPECTED_PATH)
        actual = copy.deepcopy(expected)
        actual["instrucciones"][0]["movimiento"]["importe"]["valor"] = 100
        del actual["instrucciones"][0]["movimiento"]["beneficiario"]["cuit"]

        first = summarize_report(compare_result(actual, expected))
        second = summarize_report(compare_result(actual, expected))

        self.assertEqual(first, second)
        self.assertIn("score=", first)
        self.assertIn("missing=instrucciones[0].movimiento.beneficiario.cuit", first)
        self.assertIn("mismatch=instrucciones[0].movimiento.importe.valor", first)

    def test_expected_fixture_is_valid_json(self):
        with open(EXPECTED_PATH, encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["schemaVersion"], "1.0")


if __name__ == "__main__":
    unittest.main()
