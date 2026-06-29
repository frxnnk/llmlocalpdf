import json
import tempfile
import unittest
from pathlib import Path

from process_pdfs import build_index_rows


class TestIndexWriter(unittest.TestCase):
    def test_preserves_rows_for_skipped_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "a.pdf").write_bytes(b"a")
            (input_dir / "b.pdf").write_bytes(b"b")
            (output_dir / "a.json").write_text(
                json.dumps(
                    {
                        "oficioId": "oficio-a",
                        "resumenGeneral": {
                            "cantidadInstrucciones": 2,
                            "contieneMovimientosDinero": True,
                        },
                        "_pipeline": {"needs_ocr": False, "warnings": ["warn"]},
                    }
                ),
                encoding="utf-8",
            )
            new_rows = [
                {
                    "filename": "b.pdf",
                    "oficioId": "oficio-b",
                    "cantidadInstrucciones": 1,
                    "contieneMovimientosDinero": False,
                    "needs_ocr": False,
                    "warnings_count": 0,
                }
            ]

            rows = build_index_rows(input_dir, output_dir, new_rows)

        self.assertEqual([row["filename"] for row in rows], ["a.pdf", "b.pdf"])
        self.assertEqual(rows[0]["oficioId"], "oficio-a")
        self.assertEqual(rows[0]["cantidadInstrucciones"], 2)
        self.assertTrue(rows[0]["contieneMovimientosDinero"])
        self.assertEqual(rows[0]["warnings_count"], 1)


if __name__ == "__main__":
    unittest.main()
