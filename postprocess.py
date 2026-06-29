"""Post-procesamiento: limpieza ligera de identificadores en instrucciones."""

import logging

from cbu import is_valid_cbu, normalize_cbu
from schema_contract import validate_schema
from source_anchor import anchor_amount, anchor_digits

logger = logging.getLogger(__name__)


def _mark_not_processable(instr: dict, reason: str) -> None:
    ejecutabilidad = instr.setdefault("ejecutabilidad", {})
    ejecutabilidad["esProcesable"] = False
    current_reason = ejecutabilidad.get("motivoNoProcesable")
    if current_reason:
        if reason not in current_reason:
            ejecutabilidad["motivoNoProcesable"] = f"{current_reason}; {reason}"
    else:
        ejecutabilidad["motivoNoProcesable"] = reason


def reconcile_instrucciones(llm_result: dict, source_text: str | None = None) -> tuple[dict, list[str]]:
    """Limpieza ligera de identificadores en instrucciones del schema Cedeira.

    Para cada instrucción con movimiento no-null:
    - Strip whitespace en origenFondos.identificador
    - Strip whitespace en destinoFondos.identificador
    Sin validación de checksum, sin regex, sin corrección.

    Returns:
        (result_limpio, warnings_list)
    """
    warnings = validate_schema(llm_result)
    result = dict(llm_result)
    result.setdefault("_validation", {})
    result["_validation"]["schema_warnings"] = warnings
    source_anchors = {}
    instrucciones = result.get("instrucciones", [])
    if not isinstance(instrucciones, list):
        if source_text is not None:
            result["_validation"]["source_anchors"] = source_anchors
        return result, warnings

    for i, instr in enumerate(instrucciones):
        mov = instr.get("movimiento")
        if mov is None:
            continue

        for campo_fondos in ("origenFondos", "destinoFondos"):
            fondos = mov.get(campo_fondos)
            if fondos is None:
                continue

            identificador = fondos.get("identificador")
            if identificador is not None:
                cleaned = str(identificador).strip()
                fondos["identificador"] = cleaned

                if fondos.get("tipo") != "cbu":
                    continue

                normalized = normalize_cbu(cleaned)
                if is_valid_cbu(normalized):
                    fondos["identificador"] = normalized
                else:
                    field = f"instrucciones[{i}].movimiento.{campo_fondos}.identificador"
                    warning = f"{field}: CBU invalida"
                    warnings.append(warning)
                    _mark_not_processable(instr, f"CBU invalida en {campo_fondos}.identificador")

                if source_text is not None:
                    field = f"instrucciones[{i}].movimiento.{campo_fondos}.identificador"
                    source_anchors[field] = anchor_digits(source_text, fondos["identificador"])

        importe = mov.get("importe")
        if source_text is not None and isinstance(importe, dict) and "valor" in importe:
            field = f"instrucciones[{i}].movimiento.importe.valor"
            source_anchors[field] = anchor_amount(source_text, importe["valor"])

    if source_text is not None:
        result["_validation"]["source_anchors"] = source_anchors

    return result, warnings
