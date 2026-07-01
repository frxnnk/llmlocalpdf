"""Deterministic checks for the Cedeira JSON v1.0 contract."""

from __future__ import annotations

from numbers import Number
from typing import Any


ALLOWED_FONDOS_TIPOS = {
    "cbu",
    "cuenta_judicial",
    "fondo",
    "organismo",
    "plazo_fijo",
    "titulo",
    "desconocido",
}

ALLOWED_INSTRUCCION_TIPOS = {
    "administrativa",
    "movimiento_dinero",
    "no_financiera",
    "desconocida",
}

ALLOWED_MOVIMIENTO_TIPOS = {
    "transferencia_mep",
    "movimiento_core",
    "plazo_fijo_alta",
    "plazo_fijo_baja",
    "inversion_titulos",
    "rescate_titulos",
    "retencion_legal",
    "desconocido",
}

ALLOWED_MONEDAS = {"ARS"}


def _warn(warnings: list[str], path: str, message: str) -> None:
    warnings.append(f"{path}: {message}")


def _is_number(value: Any) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _validate_required_object(
    parent: dict[str, Any],
    key: str,
    path: str,
    warnings: list[str],
) -> dict[str, Any] | None:
    value = parent.get(key)
    if not isinstance(value, dict):
        _warn(warnings, f"{path}.{key}", "expected object")
        return None
    return value


def _validate_fondos(
    movimiento: dict[str, Any],
    key: str,
    path: str,
    warnings: list[str],
) -> None:
    fondos = movimiento.get(key)
    if not isinstance(fondos, dict):
        _warn(warnings, f"{path}.{key}", "expected object")
        return

    tipo = fondos.get("tipo")
    if tipo not in ALLOWED_FONDOS_TIPOS:
        _warn(
            warnings,
            f"{path}.{key}.tipo",
            f"invalid value {tipo!r}",
        )

    if "identificador" not in fondos:
        _warn(warnings, f"{path}.{key}.identificador", "missing")


def validate_schema(result: dict[str, Any]) -> list[str]:
    """Return deterministic schema warnings for a Cedeira v1.0 result."""
    warnings: list[str] = []

    if not isinstance(result, dict):
        return ["result: expected object"]

    if result.get("schemaVersion") != "1.0":
        _warn(warnings, "schemaVersion", "missing or not '1.0'")

    if not result.get("oficioId"):
        _warn(warnings, "oficioId", "missing")

    resumen = result.get("resumenGeneral")
    if not isinstance(resumen, dict):
        _warn(warnings, "resumenGeneral", "expected object")
    else:
        for key in (
            "cantidadInstrucciones",
            "contieneMovimientosDinero",
            "contieneInstruccionesNoFinancieras",
        ):
            if key not in resumen:
                _warn(warnings, f"resumenGeneral.{key}", "missing")

    instrucciones = result.get("instrucciones")
    if not isinstance(instrucciones, list):
        _warn(warnings, "instrucciones", "expected list")
        return warnings

    if isinstance(resumen, dict) and "cantidadInstrucciones" in resumen:
        cantidad = resumen.get("cantidadInstrucciones")
        if not isinstance(cantidad, int) or isinstance(cantidad, bool):
            _warn(warnings, "resumenGeneral.cantidadInstrucciones", "expected integer")
        elif cantidad != len(instrucciones):
            _warn(
                warnings,
                "resumenGeneral.cantidadInstrucciones",
                f"expected {len(instrucciones)}, got {cantidad}",
            )

    for index, instruccion in enumerate(instrucciones):
        path = f"instrucciones[{index}]"
        if not isinstance(instruccion, dict):
            _warn(warnings, path, "expected object")
            continue

        expected_instruction_id = str(index + 1)
        instruction_id = instruccion.get("instructionId")
        if not isinstance(instruction_id, str) or not instruction_id.strip():
            _warn(warnings, f"{path}.instructionId", "missing")
        elif instruction_id != expected_instruction_id:
            _warn(
                warnings,
                f"{path}.instructionId",
                f"expected {expected_instruction_id!r}, got {instruction_id!r}",
            )

        descripcion = instruccion.get("descripcionIA")
        if not isinstance(descripcion, str) or not descripcion.strip():
            _warn(warnings, f"{path}.descripcionIA", "missing")

        tipo_instruccion = instruccion.get("tipoInstruccion")
        if tipo_instruccion not in ALLOWED_INSTRUCCION_TIPOS:
            _warn(
                warnings,
                f"{path}.tipoInstruccion",
                f"invalid value {tipo_instruccion!r}",
            )

        ejecutabilidad = _validate_required_object(
            instruccion,
            "ejecutabilidad",
            path,
            warnings,
        )
        if ejecutabilidad is not None:
            if "esProcesable" not in ejecutabilidad:
                _warn(warnings, f"{path}.ejecutabilidad.esProcesable", "missing")
            elif not isinstance(ejecutabilidad.get("esProcesable"), bool):
                _warn(warnings, f"{path}.ejecutabilidad.esProcesable", "expected boolean")

            if "motivoNoProcesable" not in ejecutabilidad:
                _warn(warnings, f"{path}.ejecutabilidad.motivoNoProcesable", "missing")

        movimiento = instruccion.get("movimiento")
        if movimiento is None:
            if tipo_instruccion == "movimiento_dinero":
                _warn(warnings, f"{path}.movimiento", "expected object")
            continue
        if not isinstance(movimiento, dict):
            _warn(warnings, f"{path}.movimiento", "expected object or null")
            continue

        tipo_movimiento = movimiento.get("tipoMovimiento")
        if tipo_movimiento not in ALLOWED_MOVIMIENTO_TIPOS:
            _warn(
                warnings,
                f"{path}.movimiento.tipoMovimiento",
                f"invalid value {tipo_movimiento!r}",
            )

        confianza = movimiento.get("confianzaTipoMovimiento")
        if not _is_number(confianza) or not 0 <= confianza <= 1:
            _warn(
                warnings,
                f"{path}.movimiento.confianzaTipoMovimiento",
                "expected number between 0 and 1",
            )

        _validate_fondos(movimiento, "origenFondos", f"{path}.movimiento", warnings)
        _validate_fondos(movimiento, "destinoFondos", f"{path}.movimiento", warnings)

        importe = movimiento.get("importe")
        if isinstance(importe, dict):
            if not _is_number(importe.get("valor")):
                _warn(warnings, f"{path}.movimiento.importe.valor", "expected number")
            moneda = importe.get("moneda")
            if not moneda:
                _warn(warnings, f"{path}.movimiento.importe.moneda", "missing")
            elif moneda not in ALLOWED_MONEDAS:
                _warn(
                    warnings,
                    f"{path}.movimiento.importe.moneda",
                    f"invalid value {moneda!r}",
                )
        else:
            _warn(warnings, f"{path}.movimiento.importe", "expected object")

    return warnings
