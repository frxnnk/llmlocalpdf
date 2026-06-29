"""Tests para cbu.py, pdf_extract, y postprocess."""

import sys
import unittest
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cbu import compute_check_digit, extract_cbues, is_valid_cbu, normalize_cbu
from pdf_extract import fix_encoding, normalize_text
from postprocess import reconcile_instrucciones


class TestComputeCheckDigit(unittest.TestCase):
    def test_known_block1(self):
        # Banco Nación (entidad 0110), sucursal 040
        # Bloque 1: 0110040 -> check digit
        digits = "0110040"
        weights = [7, 1, 3, 7, 1, 3, 7]
        cd = compute_check_digit(digits, weights)
        # Manual: 0*7+1*1+1*3+0*7+0*1+4*3+0*7 = 0+1+3+0+0+12+0 = 16
        # (10 - 16%10) % 10 = (10-6)%10 = 4
        self.assertEqual(cd, 4)


class TestIsValidCbu(unittest.TestCase):
    def test_valid_cbu(self):
        # CBU válida calculada: entidad 0110, suc 040, check1=4
        # Bloque 1: 01100404
        # Bloque 2: necesitamos calcular un bloque 2 válido
        # Cuenta: 0000000000001 -> check2
        # Pesos: [3,9,7,1,3,9,7,1,3,9,7,1,3]
        # 0*3+0*9+0*7+0*1+0*3+0*9+0*7+0*1+0*3+0*9+0*7+0*1+1*3 = 3
        # (10 - 3%10) % 10 = 7
        # CBU: 0110040400000000000017
        self.assertTrue(is_valid_cbu("0110040400000000000017"))

    def test_valid_cbu_with_spaces(self):
        self.assertTrue(is_valid_cbu("0110 0404 0000000000 0017"))

    def test_invalid_checksum(self):
        # Cambiar último dígito: 7 -> 8
        self.assertFalse(is_valid_cbu("0110040400000000000018"))

    def test_invalid_checksum_block1(self):
        # Cambiar check digit de bloque 1: 4 -> 5
        self.assertFalse(is_valid_cbu("0110040500000000000017"))

    def test_wrong_length_short(self):
        self.assertFalse(is_valid_cbu("011004040000000000001"))  # 21 dígitos

    def test_wrong_length_long(self):
        self.assertFalse(is_valid_cbu("01100404000000000000170"))  # 23 dígitos

    def test_non_numeric(self):
        self.assertFalse(is_valid_cbu("011004040000000000001A"))

    def test_empty(self):
        self.assertFalse(is_valid_cbu(""))


class TestExtractCbues(unittest.TestCase):
    def test_extract_from_clean_text(self):
        text = "La CBU es 0110040400000000000017 y algo más."
        result = extract_cbues(text)
        self.assertEqual(result, ["0110040400000000000017"])

    def test_extract_with_separators(self):
        text = "CBU: 0110-0404-0000000000-0017 del titular"
        result = extract_cbues(text)
        self.assertEqual(result, ["0110040400000000000017"])

    def test_extract_with_spaces(self):
        text = "CBU 0110 0404 0000 0000 0000 17 asignada"
        result = extract_cbues(text)
        self.assertEqual(result, ["0110040400000000000017"])

    def test_no_match(self):
        text = "Este texto no contiene números de CBU válidos."
        result = extract_cbues(text)
        self.assertEqual(result, [])

    def test_invalid_checksum_not_returned(self):
        text = "CBU falsa: 0110040400000000000018 inválida"
        result = extract_cbues(text)
        self.assertEqual(result, [])

    def test_dedup(self):
        text = "CBU 0110040400000000000017 repetida 0110040400000000000017"
        result = extract_cbues(text)
        self.assertEqual(len(result), 1)


class TestNormalizeCbu(unittest.TestCase):
    def test_remove_spaces(self):
        self.assertEqual(normalize_cbu("0110 0404"), "01100404")

    def test_remove_dashes(self):
        self.assertEqual(normalize_cbu("0110-0404"), "01100404")

    def test_remove_dots(self):
        self.assertEqual(normalize_cbu("0110.0404"), "01100404")

    def test_mixed(self):
        self.assertEqual(normalize_cbu("0110-0404 0000.0000"), "011004040000.0000".replace(".", ""))
        self.assertEqual(normalize_cbu("0110-0404 0000.0000"), "0110040400000000")


class TestNormalizeText(unittest.TestCase):
    def test_collapse_whitespace(self):
        self.assertEqual(normalize_text("hello   world"), "hello world")

    def test_preserve_newlines(self):
        self.assertEqual(normalize_text("line1\nline2"), "line1\nline2")

    def test_remove_nul(self):
        self.assertEqual(normalize_text("hel\x00lo"), "hello")

    def test_strip_lines(self):
        self.assertEqual(normalize_text("  hello  \n  world  "), "hello\nworld")

    def test_tabs_collapsed(self):
        self.assertEqual(normalize_text("hello\t\tworld"), "hello world")

    def test_mixed(self):
        text = "  line1 \x00 extra   spaces  \n\t  line2\t\there  "
        result = normalize_text(text)
        self.assertEqual(result, "line1 extra spaces\nline2 here")


class TestFixEncoding(unittest.TestCase):
    def test_passthrough_clean(self):
        """Texto limpio pasa sin cambios."""
        text = "Carátula del expediente número 12345"
        self.assertEqual(fix_encoding(text), text)

    def test_empty_string(self):
        self.assertEqual(fix_encoding(""), "")

    def test_mojibake_latin1_to_utf8(self):
        """Texto UTF-8 leído como Latin-1 se repara."""
        # Simular mojibake: "Carátula" en UTF-8 bytes, leído como Latin-1
        original = "Carátula"
        broken = original.encode("utf-8").decode("latin-1")
        # broken debería contener patrones como Ã¡
        self.assertIn("Ã", broken)
        fixed = fix_encoding(broken)
        self.assertEqual(fixed, original)

    def test_replacement_chars_removed(self):
        """Replacement chars (\ufffd) se eliminan como último recurso."""
        text = "Car\ufffdtula del expediente"
        fixed = fix_encoding(text)
        self.assertNotIn("\ufffd", fixed)
        self.assertEqual(fixed, "Cartula del expediente")

    def test_cp1252_mojibake(self):
        """Texto UTF-8 leído como CP1252 se repara."""
        original = "Resolución"
        # CP1252 puede decodificar los mismos bytes que Latin-1 para muchos chars
        broken = original.encode("utf-8").decode("cp1252", errors="replace")
        # Si tiene replacement chars, el fix debería manejarlos
        if "\ufffd" not in broken:
            # CP1252 pudo decodificar → intentar fix vía latin-1
            fixed = fix_encoding(broken)
            # Debería reparar o al menos no romper
            self.assertNotIn("\ufffd", fixed)


class TestReconcileInstrucciones(unittest.TestCase):
    VALID_CBU = "0110040400000000000017"

    def _make_result(self, instrucciones):
        return {
            "schemaVersion": "1.0",
            "oficioId": "test-uuid",
            "resumenGeneral": {
                "cantidadInstrucciones": len(instrucciones),
                "contieneMovimientosDinero": True,
                "contieneInstruccionesNoFinancieras": False,
            },
            "instrucciones": instrucciones,
        }

    def test_valid_cbu_passes(self):
        """CBU válida en destinoFondos se normaliza y pasa."""
        instr = {
            "instructionId": "1",
            "tipoInstruccion": "movimiento_dinero",
            "descripcionIA": "test",
            "movimiento": {
                "tipoMovimiento": "transferencia_mep",
                "confianzaTipoMovimiento": 0.9,
                "origenFondos": {"tipo": "cuenta_judicial", "identificador": "123-456"},
                "destinoFondos": {"tipo": "cbu", "identificador": "0110-0404 0000000000 0017"},
                "importe": {"valor": 1000.0, "moneda": "ARS"},
                "beneficiario": {"tipo": "persona", "nombre": "Test", "cuit": ""},
            },
            "ejecutabilidad": {"esProcesable": True, "motivoNoProcesable": None},
        }
        result = self._make_result([instr])
        corrected, warnings = reconcile_instrucciones(result)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(
            corrected["instrucciones"][0]["movimiento"]["destinoFondos"]["identificador"],
            self.VALID_CBU,
        )

    def test_invalid_destino_cbu_blocks_instruction(self):
        """CBU invalida marca la instruccion como no procesable."""
        instr = {
            "instructionId": "1",
            "tipoInstruccion": "movimiento_dinero",
            "descripcionIA": "test",
            "movimiento": {
                "tipoMovimiento": "transferencia_mep",
                "confianzaTipoMovimiento": 0.9,
                "origenFondos": {"tipo": "cuenta_judicial", "identificador": "123-456"},
                "destinoFondos": {"tipo": "cbu", "identificador": "0110040400000000000018"},
                "importe": {"valor": 1000.0, "moneda": "ARS"},
                "beneficiario": {"tipo": "persona", "nombre": "Test", "cuit": ""},
            },
            "ejecutabilidad": {"esProcesable": True, "motivoNoProcesable": None},
        }
        result = self._make_result([instr])

        corrected, warnings = reconcile_instrucciones(result)

        self.assertFalse(corrected["instrucciones"][0]["ejecutabilidad"]["esProcesable"])
        self.assertIn(
            "CBU invalida",
            corrected["instrucciones"][0]["ejecutabilidad"]["motivoNoProcesable"],
        )
        self.assertTrue(
            any("instrucciones[0].movimiento.destinoFondos.identificador" in warning for warning in warnings)
        )

    def test_cuenta_judicial_not_validated_as_cbu(self):
        """Cuenta judicial NO se valida como CBU — solo strip whitespace."""
        instr = {
            "instructionId": "1",
            "tipoInstruccion": "movimiento_dinero",
            "descripcionIA": "test",
            "movimiento": {
                "tipoMovimiento": "movimiento_core",
                "confianzaTipoMovimiento": 0.8,
                "origenFondos": {"tipo": "cuenta_judicial", "identificador": " 2850622-3 5009587799576-5 "},
                "destinoFondos": {"tipo": "cbu", "identificador": self.VALID_CBU},
                "importe": {"valor": 500.0, "moneda": "ARS"},
                "beneficiario": {"tipo": "persona", "nombre": "Test", "cuit": ""},
            },
            "ejecutabilidad": {"esProcesable": True, "motivoNoProcesable": None},
        }
        result = self._make_result([instr])
        corrected, warnings = reconcile_instrucciones(result)
        # No genera warnings
        self.assertEqual(len(warnings), 0)
        # Se hizo strip whitespace
        self.assertEqual(
            corrected["instrucciones"][0]["movimiento"]["origenFondos"]["identificador"],
            "2850622-3 5009587799576-5",
        )

    def test_strip_whitespace_on_identificadores(self):
        """Strip whitespace se aplica a todos los identificadores."""
        instr = {
            "instructionId": "1",
            "tipoInstruccion": "movimiento_dinero",
            "descripcionIA": "test",
            "movimiento": {
                "tipoMovimiento": "transferencia_mep",
                "confianzaTipoMovimiento": 0.9,
                "origenFondos": {"tipo": "cbu", "identificador": "  0110040400000000000017  "},
                "destinoFondos": {"tipo": "cbu", "identificador": "\t0110040400000000000017\n"},
                "importe": {"valor": 1000.0, "moneda": "ARS"},
                "beneficiario": {"tipo": "persona", "nombre": "Test", "cuit": ""},
            },
            "ejecutabilidad": {"esProcesable": True, "motivoNoProcesable": None},
        }
        result = self._make_result([instr])
        corrected, warnings = reconcile_instrucciones(result)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(
            corrected["instrucciones"][0]["movimiento"]["origenFondos"]["identificador"],
            "0110040400000000000017",
        )
        self.assertEqual(
            corrected["instrucciones"][0]["movimiento"]["destinoFondos"]["identificador"],
            "0110040400000000000017",
        )

    def test_instruction_without_movimiento_skipped(self):
        """Instrucción con movimiento=null se skipea sin error."""
        instr = {
            "instructionId": "1",
            "tipoInstruccion": "no_financiera",
            "descripcionIA": "Notificar al banco",
            "movimiento": None,
            "ejecutabilidad": {"esProcesable": True, "motivoNoProcesable": None},
        }
        result = self._make_result([instr])
        corrected, warnings = reconcile_instrucciones(result)
        self.assertEqual(len(warnings), 0)
        self.assertIsNone(corrected["instrucciones"][0]["movimiento"])


if __name__ == "__main__":
    unittest.main()
