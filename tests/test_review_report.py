import tempfile
import unittest
from pathlib import Path

from review_report import build_review_report_html, write_review_report


def make_result() -> dict:
    return {
        "schemaVersion": "1.0",
        "oficioId": "oficio-1",
        "resumenGeneral": {
            "cantidadInstrucciones": 1,
            "contieneMovimientosDinero": True,
            "contieneInstruccionesNoFinancieras": False,
        },
        "instrucciones": [
            {
                "instructionId": "1",
                "tipoInstruccion": "movimiento_dinero",
                "descripcionIA": "<script>alert(1)</script>",
                "movimiento": {
                    "tipoMovimiento": "transferencia_mep",
                    "confianzaTipoMovimiento": 0.9,
                    "origenFondos": {
                        "tipo": "cuenta_judicial",
                        "identificador": "123-456",
                    },
                    "destinoFondos": {
                        "tipo": "cbu",
                        "identificador": "0110040400000000000017",
                    },
                    "importe": {"valor": 339649.70, "moneda": "ARS"},
                    "beneficiario": {
                        "tipo": "persona",
                        "nombre": "Test",
                        "cuit": "20123456789",
                    },
                },
                "ejecutabilidad": {
                    "esProcesable": False,
                    "motivoNoProcesable": "CBU invalida",
                },
            }
        ],
        "_validation": {
            "schema_warnings": ["schema warning"],
            "source_anchors": {
                "instrucciones[0].movimiento.beneficiario.cuit": {
                    "found": True,
                    "start": 12,
                    "end": 25,
                    "snippet": "CUIT 20-12345678-9",
                }
            },
        },
        "_pipeline": {
            "source_file": "simple_transfer.pdf",
            "needs_ocr": False,
            "warnings": ["pipeline warning"],
            "processed_at": "2026-06-29T00:00:00+00:00",
            "audit": {
                "source_sha256": "source-sha",
                "extracted_text_sha256": "text-sha",
                "prompt_sha256": "prompt-sha",
                "model_manifest_sha256": "manifest-sha",
                "code_commit": "commit-sha",
            },
        },
    }


class TestReviewReport(unittest.TestCase):
    def test_review_report_includes_evidence_and_escapes_model_text(self):
        html = build_review_report_html(make_result(), source_filename="simple_transfer.pdf")

        self.assertIn("simple_transfer.pdf", html)
        self.assertIn("oficio-1", html)
        self.assertIn("source-sha", html)
        self.assertIn("text-sha", html)
        self.assertIn("schema warning", html)
        self.assertIn("pipeline warning", html)
        self.assertIn("instrucciones[0].movimiento.beneficiario.cuit", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_review_report_does_not_include_raw_extracted_text(self):
        result = make_result()
        result["_pipeline"]["audit"]["raw_extracted_text"] = "DOCUMENTO COMPLETO"

        html = build_review_report_html(result, source_filename="simple_transfer.pdf")

        self.assertIn("text-sha", html)
        self.assertNotIn("DOCUMENTO COMPLETO", html)

    def test_write_review_report_creates_html_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "simple_transfer.review.html"

            write_review_report(make_result(), report_path, source_filename="simple_transfer.pdf")

            self.assertTrue(report_path.exists())
            self.assertIn("simple_transfer.pdf", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
