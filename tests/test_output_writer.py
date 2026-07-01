import json
import tempfile
import unittest
from pathlib import Path

from process_pdfs import write_result_outputs


class TestOutputWriter(unittest.TestCase):
    def test_write_result_outputs_creates_json_and_review_html(self):
        result = {
            "oficioId": "oficio-1",
            "resumenGeneral": {"cantidadInstrucciones": 0},
            "instrucciones": [],
            "_pipeline": {
                "source_file": "simple_transfer.pdf",
                "needs_ocr": False,
                "warnings": [],
                "audit": {"source_sha256": "source-sha"},
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "simple_transfer.json"

            report_file = write_result_outputs(
                result, output_file, source_filename="simple_transfer.pdf"
            )

            self.assertEqual(report_file, Path(tmp) / "simple_transfer.review.html")
            self.assertEqual(json.loads(output_file.read_text(encoding="utf-8")), result)
            self.assertIn("simple_transfer.pdf", report_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
