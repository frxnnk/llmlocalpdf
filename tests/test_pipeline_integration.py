import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import process_pdfs
from audit_log import append_pdf_processed_event, read_events
from golden_eval import compare_result, load_json, summarize_report


FIXTURE_DIR = Path(__file__).parent / "fixtures"
SIMPLE_TEXT = FIXTURE_DIR / "text" / "simple_transfer.txt"
SIMPLE_EXPECTED = FIXTURE_DIR / "expected" / "simple_transfer.json"
NEW_EXPECTED_FIXTURES = [
    "invalid_cbu.json",
    "multiple_instructions.json",
    "no_financiera.json",
    "needs_ocr.json",
    "ambiguous_amounts.json",
]


class FakeLLMClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def call_with_json_repair(self, **kwargs):
        result = load_json(SIMPLE_EXPECTED)
        result = copy.deepcopy(result)
        result["instrucciones"][0]["instructionId"] = "1"
        result["instrucciones"][0]["descripcionIA"] = "Transferir fondos"
        result["instrucciones"][0]["movimiento"]["tipoMovimiento"] = "transferencia_mep"
        result["instrucciones"][0]["movimiento"]["confianzaTipoMovimiento"] = 0.95
        result["instrucciones"][0]["movimiento"]["beneficiario"]["tipo"] = "persona"
        return result


class TestPipelineIntegration(unittest.TestCase):
    def test_offline_main_writes_json_review_index_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            audit_path = root / "audit.jsonl"
            input_dir.mkdir()
            pdf_path = input_dir / "simple_transfer.pdf"
            pdf_path.write_bytes(b"%PDF-simple")
            source_text = SIMPLE_TEXT.read_text(encoding="utf-8")

            def append_temp_audit(_log_path, source_sha256, output_path):
                return append_pdf_processed_event(
                    audit_path,
                    source_sha256=source_sha256,
                    output_path=output_path,
                    timestamp="2026-06-30T00:00:00+00:00",
                )

            argv = [
                "process_pdfs.py",
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--endpoint",
                "http://offline.test",
                "--workers",
                "1",
            ]
            with (
                patch("sys.argv", argv),
                patch("process_pdfs.setup_logging"),
                patch("process_pdfs.LLMClient", FakeLLMClient),
                patch("process_pdfs.extract_text", return_value=(source_text, False)),
                patch("process_pdfs.uuid.uuid4", return_value="oficio-integration"),
                patch("process_pdfs.append_pdf_processed_event", side_effect=append_temp_audit),
            ):
                process_pdfs.main()

            output_json = output_dir / "simple_transfer.json"
            review_html = output_dir / "simple_transfer.review.html"
            index_jsonl = output_dir / "index.jsonl"
            result = json.loads(output_json.read_text(encoding="utf-8"))
            index_rows = [
                json.loads(line)
                for line in index_jsonl.read_text(encoding="utf-8").splitlines()
            ]
            audit_events = read_events(audit_path)
            report = compare_result(result, load_json(SIMPLE_EXPECTED))
            output_exists = output_json.exists()
            review_text = review_html.read_text(encoding="utf-8")

        self.assertTrue(report["passed"], summarize_report(report))
        self.assertEqual(result["oficioId"], "oficio-integration")
        self.assertTrue(output_exists)
        self.assertIn("simple_transfer.pdf", review_text)
        self.assertEqual(len(index_rows), 1)
        self.assertEqual(index_rows[0]["filename"], "simple_transfer.pdf")
        self.assertEqual(index_rows[0]["oficioId"], "oficio-integration")
        self.assertEqual(len(audit_events), 1)
        self.assertEqual(audit_events[0]["event"], "pdf_processed")

    def test_new_golden_fixtures_are_valid_and_summarizable(self):
        summaries = []

        for filename in NEW_EXPECTED_FIXTURES:
            expected = load_json(FIXTURE_DIR / "expected" / filename)
            report = compare_result(expected, expected)
            summaries.append(summarize_report(report))
            self.assertTrue(report["passed"], filename)

        self.assertEqual(len(summaries), len(NEW_EXPECTED_FIXTURES))
        self.assertTrue(all("passed=true" in summary for summary in summaries))


if __name__ == "__main__":
    unittest.main()
