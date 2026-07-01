import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import process_pdfs


class TestProcessCli(unittest.TestCase):
    def run_main(self, input_dir: Path, output_dir: Path, workers: int = 1):
        argv = [
            "process_pdfs.py",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--workers",
            str(workers),
        ]
        with patch("sys.argv", argv), patch("process_pdfs.setup_logging"):
            return process_pdfs.main()

    def test_main_exits_with_error_when_input_has_no_pdfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()

            with patch("process_pdfs.LLMClient") as llm_client:
                with self.assertRaises(SystemExit) as raised:
                    self.run_main(input_dir, output_dir)

        self.assertEqual(raised.exception.code, 1)
        llm_client.assert_not_called()

    def test_main_idempotent_rerun_writes_index_for_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "already_done.pdf").write_bytes(b"%PDF-existing")
            (output_dir / "already_done.json").write_text(
                json.dumps(
                    {
                        "oficioId": "oficio-existing",
                        "resumenGeneral": {
                            "cantidadInstrucciones": 2,
                            "contieneMovimientosDinero": True,
                        },
                        "_pipeline": {
                            "needs_ocr": False,
                            "warnings": ["warning-a", "warning-b"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("process_pdfs.LLMClient") as llm_client,
                patch("process_pdfs.process_single_pdf") as process_single,
                self.assertRaises(SystemExit) as raised,
            ):
                self.run_main(input_dir, output_dir)

            index_lines = (output_dir / "index.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertEqual(raised.exception.code, 0)
        llm_client.assert_not_called()
        process_single.assert_not_called()
        self.assertEqual(len(index_lines), 1)
        row = json.loads(index_lines[0])
        self.assertEqual(row["filename"], "already_done.pdf")
        self.assertEqual(row["oficioId"], "oficio-existing")
        self.assertEqual(row["cantidadInstrucciones"], 2)
        self.assertEqual(row["warnings_count"], 2)

    def test_main_writes_index_rows_for_processed_pdfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "new.pdf").write_bytes(b"%PDF-new")
            row = {
                "filename": "new.pdf",
                "oficioId": "oficio-new",
                "cantidadInstrucciones": 1,
                "contieneMovimientosDinero": True,
                "needs_ocr": False,
                "warnings_count": 0,
            }

            with (
                patch("process_pdfs.load_prompt", return_value="prompt"),
                patch("process_pdfs.LLMClient", return_value=Mock()),
                patch("process_pdfs.process_single_pdf", return_value=row) as process_single,
            ):
                self.run_main(input_dir, output_dir)

            index_lines = (output_dir / "index.jsonl").read_text(encoding="utf-8").splitlines()

        process_single.assert_called_once()
        self.assertEqual([json.loads(line) for line in index_lines], [row])

    def test_main_writes_error_row_when_worker_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "broken.pdf").write_bytes(b"%PDF-broken")

            with (
                patch("process_pdfs.load_prompt", return_value="prompt"),
                patch("process_pdfs.LLMClient", return_value=Mock()),
                patch(
                    "process_pdfs.process_single_pdf",
                    side_effect=RuntimeError("boom"),
                ),
            ):
                self.run_main(input_dir, output_dir)

            rows = [
                json.loads(line)
                for line in (output_dir / "index.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["filename"], "broken.pdf")
        self.assertTrue(rows[0]["error"])
        self.assertEqual(rows[0]["oficioId"], "")
        self.assertEqual(rows[0]["cantidadInstrucciones"], 0)


if __name__ == "__main__":
    unittest.main()
