import unittest

from postprocess import reconcile_instrucciones
from source_anchor import anchor_amount, anchor_digits


class TestSourceAnchor(unittest.TestCase):
    def test_cbu_with_separators_anchors_to_normalized_value(self):
        source_text = "Transferir a CBU 0110-0404 0000 0000 0000 17 del beneficiario."

        anchor = anchor_digits(source_text, "0110040400000000000017")

        self.assertTrue(anchor["found"])
        self.assertIsInstance(anchor["start"], int)
        self.assertIsInstance(anchor["end"], int)
        self.assertIn("0110-0404", anchor["snippet"])

    def test_amount_with_argentine_format_anchors_to_decimal_value(self):
        source_text = "Librar transferencia por la suma de $339.649,70."

        anchor = anchor_amount(source_text, "339649.70")

        self.assertTrue(anchor["found"])
        self.assertIsInstance(anchor["start"], int)
        self.assertIsInstance(anchor["end"], int)
        self.assertIn("$339.649,70", anchor["snippet"])

    def test_missing_value_returns_empty_anchor(self):
        anchor = anchor_digits("No hay cuenta bancaria en este texto.", "0110040400000000000017")

        self.assertFalse(anchor["found"])
        self.assertIsNone(anchor["start"])
        self.assertIsNone(anchor["end"])
        self.assertEqual(anchor["snippet"], "")

    def test_reconcile_stores_source_anchors(self):
        result = {
            "schemaVersion": "1.0",
            "oficioId": "test-uuid",
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
                        "confianzaTipoMovimiento": 0.9,
                        "origenFondos": {"tipo": "cuenta_judicial", "identificador": "123-456"},
                        "destinoFondos": {"tipo": "cbu", "identificador": "0110040400000000000017"},
                        "importe": {"valor": 339649.70, "moneda": "ARS"},
                        "beneficiario": {"tipo": "persona", "nombre": "Test", "cuit": ""},
                    },
                    "ejecutabilidad": {"esProcesable": True, "motivoNoProcesable": None},
                }
            ],
        }
        source_text = "CBU 0110-0404 0000 0000 0000 17 por $339.649,70"

        corrected, warnings = reconcile_instrucciones(result, source_text=source_text)

        self.assertEqual(warnings, [])
        anchors = corrected["_validation"]["source_anchors"]
        self.assertTrue(
            anchors["instrucciones[0].movimiento.destinoFondos.identificador"]["found"]
        )
        self.assertTrue(anchors["instrucciones[0].movimiento.importe.valor"]["found"])


if __name__ == "__main__":
    unittest.main()
