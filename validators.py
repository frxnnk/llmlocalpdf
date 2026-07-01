"""Focused deterministic validators for Argentine legal extraction fields."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
import re
from typing import Any


_CUIT_WEIGHTS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
_CENT = Decimal("0.01")


def normalize_cuit(raw: str) -> str:
    """Remove common CUIT separators while preserving other invalid chars."""
    return re.sub(r"[\s\-.]", "", str(raw))


def is_valid_cuit(cuit: str) -> bool:
    """Validate an Argentine CUIT/CUIL using the modulo-11 check digit."""
    normalized = normalize_cuit(cuit)
    if len(normalized) != 11 or not normalized.isdigit():
        return False

    total = sum(int(digit) * weight for digit, weight in zip(normalized[:10], _CUIT_WEIGHTS))
    verifier = 11 - (total % 11)
    if verifier == 11:
        verifier = 0
    elif verifier == 10:
        verifier = 9

    return verifier == int(normalized[-1])


def _quantize_amount(amount: Decimal) -> Decimal | None:
    if not amount.is_finite() or amount < 0:
        return None
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def _parse_numeric_amount(value: int | float | Decimal) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None

    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return None

    return _quantize_amount(amount)


def _clean_amount_text(value: str) -> str:
    text = str(value).strip().replace("\u00a0", " ")
    text = re.sub(r"(?i)\bARS\b", "", text)
    text = text.replace("$", "")
    return re.sub(r"\s+", "", text)


def parse_argentine_amount(value: Any) -> Decimal | None:
    """Parse Argentine-style amounts and normalized numeric values.

    Accepted examples: "$339.649,70", "ARS 1.234,5", "1234,56",
    "1.234.567", "339649.70", and numeric Python values.
    """
    if isinstance(value, (int, float, Decimal)):
        return _parse_numeric_amount(value)

    text = _clean_amount_text(str(value))
    if not text or text.startswith("-"):
        return None

    grouped_argentine = re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", text)
    ungrouped_argentine = re.fullmatch(r"\d+(?:,\d{1,2})?", text)
    machine_decimal = re.fullmatch(r"\d+(?:\.\d{1,2})?", text)

    if grouped_argentine:
        normalized = text.replace(".", "").replace(",", ".")
    elif ungrouped_argentine:
        normalized = text.replace(",", ".")
    elif machine_decimal:
        normalized = text
    else:
        return None

    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None

    return _quantize_amount(amount)


def normalize_argentine_amount(value: Any) -> str | None:
    """Return a canonical two-decimal string, or None when invalid."""
    amount = parse_argentine_amount(value)
    if amount is None:
        return None
    return format(amount, "f")
