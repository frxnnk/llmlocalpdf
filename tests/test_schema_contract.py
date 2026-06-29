"""Tests for deterministic schema contract validation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from postprocess import reconcile_instrucciones
from schema_contract import validate_schema


def make_valid_result() -> dict:
    return {
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
                    "origenFondos": {
                        "tipo": "cuenta_judicial",
                        "identificador": "123-456",
                    },
                    "destinoFondos": {
                        "tipo": "cbu",
                        "identificador": "0110040400000000000017",
                    },
                    "importe": {"valor": 1000.0, "moneda": "ARS"},
                    "beneficiario": {"tipo": "persona", "nombre": "Test", "cuit": ""},
                },
                "ejecutabilidad": {
                    "esProcesable": True,
                    "motivoNoProcesable": None,
                },
            }
        ],
    }


class TestSchemaContract(unittest.TestCase):
    def test_valid_minimal_result_has_no_warnings(self):
        warnings = validate_schema(make_valid_result())

        self.assertEqual(warnings, [])

    def test_missing_schema_version_returns_warning(self):
        result = make_valid_result()
        del result["schemaVersion"]

        warnings = validate_schema(result)

        self.assertTrue(any("schemaVersion" in warning for warning in warnings))

    def test_missing_resumen_general_returns_warning(self):
        result = make_valid_result()
        del result["resumenGeneral"]

        warnings = validate_schema(result)

        self.assertTrue(any("resumenGeneral" in warning for warning in warnings))

    def test_instrucciones_must_be_list(self):
        result = make_valid_result()
        result["instrucciones"] = {}

        warnings = validate_schema(result)

        self.assertTrue(any("instrucciones" in warning for warning in warnings))

    def test_invalid_fondos_tipo_returns_warning(self):
        result = make_valid_result()
        result["instrucciones"][0]["movimiento"]["destinoFondos"]["tipo"] = "wallet"

        warnings = validate_schema(result)

        self.assertTrue(any("destinoFondos.tipo" in warning for warning in warnings))

    def test_reconcile_stores_schema_warnings(self):
        result = make_valid_result()
        del result["schemaVersion"]

        corrected, warnings = reconcile_instrucciones(result)

        self.assertTrue(any("schemaVersion" in warning for warning in warnings))
        self.assertEqual(
            corrected["_validation"]["schema_warnings"],
            warnings,
        )


if __name__ == "__main__":
    unittest.main()
