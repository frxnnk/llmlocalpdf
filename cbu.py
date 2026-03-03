"""Validación y extracción de CBUs (Clave Bancaria Uniforme) argentinas.

Algoritmo de checksum:
- Bloque 1 (8 dígitos): pos 0-6 datos, pos 7 check. Pesos: [7,1,3,7,1,3,7]
- Bloque 2 (14 dígitos): pos 8-20 datos, pos 21 check. Pesos: [3,9,7,1,3,9,7,1,3,9,7,1,3]
- check_digit = (10 - (sum(d_i * w_i) % 10)) % 10
"""

import re


def normalize_cbu(raw: str) -> str:
    """Quitar espacios, guiones y puntos de una cadena CBU."""
    return re.sub(r"[\s\-\.]", "", raw)


def compute_check_digit(digits: str, weights: list[int]) -> int:
    """Calcular dígito verificador: (10 - (sum(d*w) % 10)) % 10."""
    total = sum(int(d) * w for d, w in zip(digits, weights))
    return (10 - (total % 10)) % 10


def is_valid_cbu(cbu: str) -> bool:
    """Validar CBU de 22 dígitos con checksum de ambos bloques."""
    cbu = normalize_cbu(cbu)
    if len(cbu) != 22 or not cbu.isdigit():
        return False

    # Bloque 1: dígitos 0-6 datos, dígito 7 check
    weights_1 = [7, 1, 3, 7, 1, 3, 7]
    check_1 = compute_check_digit(cbu[0:7], weights_1)
    if check_1 != int(cbu[7]):
        return False

    # Bloque 2: dígitos 8-20 datos, dígito 21 check
    weights_2 = [3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3]
    check_2 = compute_check_digit(cbu[8:21], weights_2)
    if check_2 != int(cbu[21]):
        return False

    return True


def extract_cbues(text: str) -> list[str]:
    """Extraer CBUs válidas de texto libre usando regex + checksum.

    Busca secuencias de dígitos (con posibles espacios, guiones o puntos)
    que puedan formar una CBU de 22 dígitos, las normaliza y valida.
    """
    # Patrón: dígito, luego 20-26 chars (dígitos/espacios/guiones/puntos), dígito final
    pattern = r"\d[\d\s\-\.]{20,26}\d"
    candidates = re.findall(pattern, text)

    valid = []
    seen = set()
    for candidate in candidates:
        normalized = normalize_cbu(candidate)
        if len(normalized) == 22 and normalized.isdigit() and normalized not in seen:
            if is_valid_cbu(normalized):
                valid.append(normalized)
                seen.add(normalized)

    return valid
