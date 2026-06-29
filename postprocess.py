"""Post-procesamiento: limpieza ligera de identificadores en instrucciones."""

import logging

from schema_contract import validate_schema

logger = logging.getLogger(__name__)


def reconcile_instrucciones(llm_result: dict) -> tuple[dict, list[str]]:
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
    instrucciones = result.get("instrucciones", [])
    if not isinstance(instrucciones, list):
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
                fondos["identificador"] = str(identificador).strip()

    return result, warnings
