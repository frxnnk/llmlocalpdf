"""Helpers para vincular valores extraidos con spans del texto fuente."""

from decimal import Decimal, InvalidOperation
import re


def _empty_anchor() -> dict:
    return {"found": False, "start": None, "end": None, "snippet": ""}


def make_snippet(source_text: str, start: int, end: int, window: int = 60) -> str:
    snippet_start = max(0, start - window)
    snippet_end = min(len(source_text), end + window)
    return source_text[snippet_start:snippet_end].strip()


def anchor_digits(source_text: str, value: str) -> dict:
    target = re.sub(r"\D", "", str(value))
    if not source_text or not target:
        return _empty_anchor()

    for match in re.finditer(r"\d[\d\s\-.]*\d", source_text):
        if re.sub(r"\D", "", match.group(0)) == target:
            return {
                "found": True,
                "start": match.start(),
                "end": match.end(),
                "snippet": make_snippet(source_text, match.start(), match.end()),
            }

    return _empty_anchor()


def _canonical_amount(value: str | int | float) -> str | None:
    raw = re.sub(r"[^\d,\.\-]", "", str(value).strip())
    if not raw:
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")

    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return None

    return format(amount.quantize(Decimal("0.01")), "f")


def anchor_amount(source_text: str, value: str | int | float) -> dict:
    target = _canonical_amount(value)
    if not source_text or target is None:
        return _empty_anchor()

    pattern = re.compile(
        r"(?:\$|ARS)?\s*-?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?"
        r"|\b-?\d+(?:[\.,]\d{1,2})?\b",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(source_text):
        if _canonical_amount(match.group(0)) == target:
            return {
                "found": True,
                "start": match.start(),
                "end": match.end(),
                "snippet": make_snippet(source_text, match.start(), match.end()),
            }

    return _empty_anchor()
