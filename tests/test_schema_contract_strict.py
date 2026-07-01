import copy
import unittest

from schema_contract import validate_schema


def make_strict_result(instruction_count=1):
    instrucciones = []
    for index in range(instruction_count):
        instrucciones.append(
            {
                "instructionId": str(index + 1),
                "tipoInstruccion": "movimiento_dinero",
                "descripcionIA": 'Transferir fondos segun "orden judicial".',
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
                    "beneficiario": {
                        "tipo": "persona",
                        "nombre": "Test",
                        "cuit": "20123456786",
                    },
                },
                "ejecutabilidad": {
                    "esProcesable": True,
                    "motivoNoProcesable": None,
                },
            }
        )

    return {
        "schemaVersion": "1.0",
        "oficioId": "test-uuid",
        "resumenGeneral": {
            "cantidadInstrucciones": instruction_count,
            "contieneMovimientosDinero": True,
            "contieneInstruccionesNoFinancieras": False,
        },
        "instrucciones": instrucciones,
    }


class TestStrictSchemaContract(unittest.TestCase):
    def test_valid_strict_result_has_no_warnings(self):
        warnings = validate_schema(make_strict_result())

        self.assertEqual(warnings, [])

    def test_cantidad_instrucciones_must_match_instruction_count(self):
        result = make_strict_result(instruction_count=2)
        result["resumenGeneral"]["cantidadInstrucciones"] = 1

        warnings = validate_schema(result)

        self.assertTrue(any("cantidadInstrucciones" in warning and "expected 2" in warning for warning in warnings))

    def test_instruction_id_is_required(self):
        result = make_strict_result()
        del result["instrucciones"][0]["instructionId"]

        warnings = validate_schema(result)

        self.assertTrue(any("instrucciones[0].instructionId" in warning for warning in warnings))

    def test_instruction_id_must_be_sequential_string(self):
        result = make_strict_result(instruction_count=2)
        result["instrucciones"][1]["instructionId"] = "99"

        warnings = validate_schema(result)

        self.assertTrue(any("instrucciones[1].instructionId" in warning and "'2'" in warning for warning in warnings))

    def test_descripcion_ia_is_required(self):
        result = make_strict_result()
        result["instrucciones"][0]["descripcionIA"] = "   "

        warnings = validate_schema(result)

        self.assertTrue(any("instrucciones[0].descripcionIA" in warning for warning in warnings))

    def test_tipo_movimiento_must_be_allowed_value(self):
        result = make_strict_result()
        result["instrucciones"][0]["movimiento"]["tipoMovimiento"] = "wire_transfer"

        warnings = validate_schema(result)

        self.assertTrue(any("movimiento.tipoMovimiento" in warning for warning in warnings))

    def test_prompt_tipo_movimiento_values_are_allowed(self):
        allowed_values = [
            "transferencia_mep",
            "movimiento_core",
            "plazo_fijo_alta",
            "plazo_fijo_baja",
            "inversion_titulos",
            "rescate_titulos",
            "retencion_legal",
            "desconocido",
        ]
        base = make_strict_result()

        for value in allowed_values:
            with self.subTest(value=value):
                result = copy.deepcopy(base)
                result["instrucciones"][0]["movimiento"]["tipoMovimiento"] = value

                self.assertEqual(validate_schema(result), [])

    def test_moneda_must_be_allowed_value(self):
        result = make_strict_result()
        result["instrucciones"][0]["movimiento"]["importe"]["moneda"] = "USD"

        warnings = validate_schema(result)

        self.assertTrue(any("movimiento.importe.moneda" in warning for warning in warnings))

    def test_procesability_fields_are_required(self):
        result = make_strict_result()
        del result["instrucciones"][0]["ejecutabilidad"]["motivoNoProcesable"]

        warnings = validate_schema(result)

        self.assertTrue(any("ejecutabilidad.motivoNoProcesable" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
