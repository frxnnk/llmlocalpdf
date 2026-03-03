"""Post-procesamiento: limpieza ligera de identificadores en instrucciones."""

import logging

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
    warnings = []
    result = dict(llm_result)
    instrucciones = result.get("instrucciones", [])

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
