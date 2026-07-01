import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from process_pdfs import process_single_pdf


def make_llm_result() -> dict:
    return {
        "schemaVersion": "1.0",
        "oficioId": "llm-will-be-overwritten",
        "resumenGeneral": {
            "cantidadInstrucciones": 1,
            "contieneMovimientosDinero": True,
            "contieneInstruccionesNoFinancieras": False,
        },
        "instrucciones": [
            {
                "instructionId": "1",
                "tipoInstruccion": "movimiento_dinero",
                "descripcionIA": "Transferir fondos",
                "movimiento": {
                    "tipoMovimiento": "transferencia_mep",
                    "confianzaTipoMovimiento": 0.92,
                    "origenFondos": {
                        "tipo": "cuenta_judicial",
                        "identificador": "123-456",
                    },
                    "destinoFondos": {
                        "tipo": "cbu",
                        "identificador": "0110-0404 0000 0000 0000 17",
                    },
                    "importe": {"valor": 339649.70, "moneda": "ARS"},
                    "beneficiario": {
                        "tipo": "persona",
                        "nombre": "DIAZ GUERRERO MAURICIO",
                        "cuit": "20358095403",
                    },
                },
                "ejecutabilidad": {
                    "esProcesable": True,
                    "motivoNoProcesable": None,
                },
            }
        ],
    }


class FakeLLM:
    def __init__(self, result: dict | None = None, error: Exception | None = None):
        self.result = result if result is not None else make_llm_result()
        self.error = error
        self.calls = []

    def call_with_json_repair(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return copy.deepcopy(self.result)


class TestProcessSinglePdf(unittest.TestCase):
    def run_process(self, tmp: str, llm: FakeLLM, extracted_text: str):
        root = Path(tmp)
        pdf_path = root / "simple_transfer.pdf"
        output_dir = root / "output"
        pdf_path.write_bytes(b"%PDF-test")
        output_dir.mkdir()

        system_prompt = (
            "### SYSTEM ###\nSystem rules\n"
            "### USER ###\nID {oficio_id}\nTEXT {document_text}"
        )
        with (
            patch("process_pdfs.extract_text", return_value=(extracted_text, False)),
            patch("process_pdfs.uuid.uuid4", return_value="oficio-123"),
            patch("process_pdfs.append_pdf_processed_event") as append_audit,
        ):
            row = process_single_pdf(
                pdf_path,
                output_dir,
                llm,
                system_prompt,
                "",
                "fix {bad_json}",
            )

        return row, output_dir / "simple_transfer.json", append_audit

    def test_success_writes_json_review_and_returns_index_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            llm = FakeLLM()

            row, output_file, append_audit = self.run_process(
                tmp,
                llm,
                "Librese transferencia a CBU 0110-0404 0000 0000 0000 17",
            )

            result = json.loads(output_file.read_text(encoding="utf-8"))
            review_file = output_file.with_name("simple_transfer.review.html")
            review_exists = review_file.exists()

        self.assertEqual(row["filename"], "simple_transfer.pdf")
        self.assertEqual(row["oficioId"], "oficio-123")
        self.assertEqual(row["cantidadInstrucciones"], 1)
        self.assertTrue(row["contieneMovimientosDinero"])
        self.assertFalse(row["needs_ocr"])
        self.assertEqual(row["warnings_count"], 0)
        self.assertEqual(result["oficioId"], "oficio-123")
        self.assertEqual(
            result["instrucciones"][0]["movimiento"]["destinoFondos"]["identificador"],
            "0110040400000000000017",
        )
        self.assertFalse(result["_pipeline"]["needs_ocr"])
        self.assertEqual(result["_pipeline"]["warnings"], [])
        self.assertIn("source_sha256", result["_pipeline"]["audit"])
        self.assertIn("TEXT Librese transferencia", llm.calls[0]["user"])
        self.assertTrue(review_exists)
        append_audit.assert_called_once()

    def test_needs_ocr_writes_pipeline_error_without_calling_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "scan.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF-scan")
            output_dir.mkdir()
            llm = FakeLLM(error=AssertionError("LLM should not be called"))

            with (
                patch("process_pdfs.extract_text", return_value=("", True)),
                patch("process_pdfs.uuid.uuid4", return_value="oficio-ocr"),
                patch("process_pdfs.append_pdf_processed_event") as append_audit,
            ):
                row = process_single_pdf(
                    pdf_path,
                    output_dir,
                    llm,
                    "### SYSTEM ###\nSystem",
                    "",
                    "fix",
                )

            result = json.loads((output_dir / "scan.json").read_text(encoding="utf-8"))

        self.assertEqual(row["filename"], "scan.pdf")
        self.assertEqual(row["oficioId"], "oficio-ocr")
        self.assertTrue(row["needs_ocr"])
        self.assertEqual(row["cantidadInstrucciones"], 0)
        self.assertTrue(result["_pipeline"]["needs_ocr"])
        self.assertEqual(result["_pipeline"]["error"], "PDF sin texto extraíble, requiere OCR")
        self.assertEqual(llm.calls, [])
        append_audit.assert_called_once()

    def test_warnings_from_postprocess_are_recorded_and_counted(self):
        invalid_result = make_llm_result()
        invalid_result["instrucciones"][0]["movimiento"]["destinoFondos"][
            "identificador"
        ] = "1234567890123456789012"
        llm = FakeLLM(result=invalid_result)

        with tempfile.TemporaryDirectory() as tmp:
            row, output_file, _ = self.run_process(
                tmp,
                llm,
                "Transferir a la CBU 1234567890123456789012",
            )
            result = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertEqual(row["warnings_count"], 1)
        self.assertIn("CBU invalida", result["_pipeline"]["warnings"][0])
        instruction = result["instrucciones"][0]
        self.assertFalse(instruction["ejecutabilidad"]["esProcesable"])
        self.assertIn(
            "CBU invalida",
            instruction["ejecutabilidad"]["motivoNoProcesable"],
        )

    def test_llm_exception_propagates_without_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "bad_llm.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF-bad")
            output_dir.mkdir()
            llm = FakeLLM(error=RuntimeError("llm unavailable"))

            with (
                patch("process_pdfs.extract_text", return_value=("texto", False)),
                patch("process_pdfs.uuid.uuid4", return_value="oficio-error"),
                patch("process_pdfs.append_pdf_processed_event") as append_audit,
            ):
                with self.assertRaisesRegex(RuntimeError, "llm unavailable"):
                    process_single_pdf(
                        pdf_path,
                        output_dir,
                        llm,
                        "### SYSTEM ###\nSystem",
                        "",
                        "fix",
                    )

            self.assertFalse((output_dir / "bad_llm.json").exists())
            append_audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
