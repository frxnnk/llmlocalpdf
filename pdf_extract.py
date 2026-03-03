"""Extracción de texto de PDFs con pdfplumber."""

import logging
import re

import pdfplumber

logger = logging.getLogger(__name__)


def fix_encoding(text: str) -> str:
    """Reparar mojibake común en PDFs (Latin-1/CP1252 leído como UTF-8).

    Estrategia:
    1. Detectar replacement chars (\ufffd) o patrones mojibake (ej: Ã¡ = á)
    2. Intentar latin-1 → utf-8
    3. Fallback cp1252 → utf-8
    4. Último recurso: eliminar \ufffd
    5. Si no hay mojibake: devolver sin cambios
    """
    if not text:
        return text

    # Detectar mojibake: replacement char o patrones típicos de UTF-8 leído como Latin-1
    has_replacement = "\ufffd" in text
    # Patrones comunes: Ã¡=á, Ã©=é, Ã­=í, Ã³=ó, Ãº=ú, Ã±=ñ, Ã=Á, etc.
    has_mojibake = bool(re.search(r"Ã[\xa0-\xbf]|Ã[¡©­³ºñ]", text))

    if not has_replacement and not has_mojibake:
        return text

    logger.debug("Mojibake detectado (replacement=%s, patterns=%s)", has_replacement, has_mojibake)

    # Intentar reparar: latin-1 encode → utf-8 decode
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        logger.debug("Encoding reparado con latin-1 → utf-8")
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    # Fallback: cp1252 encode → utf-8 decode
    try:
        fixed = text.encode("cp1252").decode("utf-8")
        logger.debug("Encoding reparado con cp1252 → utf-8")
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    # Último recurso: eliminar replacement chars
    if has_replacement:
        fixed = text.replace("\ufffd", "")
        logger.warning("No se pudo reparar encoding, se eliminaron %d replacement chars",
                        text.count("\ufffd"))
        return fixed

    return text


def extract_text(pdf_path: str) -> tuple[str, bool]:
    """Extraer texto de un PDF usando pdfplumber.

    Returns:
        (texto, needs_ocr): texto concatenado de todas las páginas,
        y True si el PDF no tiene texto extraíble (necesitaría OCR).
    """
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            text = fix_encoding(text)
            pages_text.append(text)

    full_text = "\n".join(pages_text)

    if not full_text.strip():
        return ("", True)

    return (full_text, False)


def normalize_text(text: str) -> str:
    """Normalizar texto extraído de PDF.

    - Eliminar caracteres NUL
    - Colapsar runs de whitespace (excepto newlines) a un solo espacio
    - Strip de cada línea
    """
    # Quitar NUL chars
    text = text.replace("\x00", "")

    # Colapsar whitespace horizontal (no newlines) a un espacio
    text = re.sub(r"[^\S\n]+", " ", text)

    # Strip de cada línea
    lines = [line.strip() for line in text.splitlines()]

    return "\n".join(lines)
