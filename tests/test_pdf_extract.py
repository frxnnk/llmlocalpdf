import unittest
from unittest.mock import patch

import pdf_extract


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class FakePdf:
    def __init__(self, page_texts):
        self.pages = [FakePage(text) for text in page_texts]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestPdfExtract(unittest.TestCase):
    def test_extract_text_concatenates_pages_and_marks_not_ocr(self):
        with (
            patch("pdf_extract.os.path.getsize", return_value=123),
            patch("pdf_extract.pdfplumber.open", return_value=FakePdf(["Pagina uno", "Pagina dos"])),
        ):
            text, needs_ocr = pdf_extract.extract_text("oficio.pdf")

        self.assertEqual(text, "Pagina uno\nPagina dos")
        self.assertFalse(needs_ocr)

    def test_extract_text_marks_needs_ocr_when_pages_have_no_text(self):
        with (
            patch("pdf_extract.os.path.getsize", return_value=123),
            patch("pdf_extract.pdfplumber.open", return_value=FakePdf(["", None, "   "])),
        ):
            text, needs_ocr = pdf_extract.extract_text("scan.pdf")

        self.assertEqual(text, "")
        self.assertTrue(needs_ocr)

    def test_extract_text_rejects_oversized_pdf_before_opening(self):
        with (
            patch(
                "pdf_extract.os.path.getsize",
                return_value=pdf_extract.MAX_PDF_SIZE_BYTES + 1,
            ),
            patch("pdf_extract.pdfplumber.open") as pdf_open,
        ):
            with self.assertRaisesRegex(ValueError, "PDF demasiado grande"):
                pdf_extract.extract_text("huge.pdf")

        pdf_open.assert_not_called()

    def test_fix_encoding_repairs_common_mojibake(self):
        self.assertEqual(pdf_extract.fix_encoding("LÃ­brese oficio"), "Líbrese oficio")

    def test_normalize_text_removes_nul_and_collapses_horizontal_whitespace(self):
        text = pdf_extract.normalize_text("  uno\t\t dos\x00  \n  tres    cuatro  ")

        self.assertEqual(text, "uno dos\ntres cuatro")


if __name__ == "__main__":
    unittest.main()
