"""Deterministic checks for the Cedeira JSON v1.0 contract."""

from __future__ import annotations

from numbers import Number
from typing import Any


ALLOWED_FONDOS_TIPOS = {
    "cbu",
    "cuenta_judicial",
    "organismo",
    "plazo_fijo",
    "desconocido",
}

ALLOWED_INSTRUCCION_TIPOS = {
    "movimiento_dinero",
    "no_financiera",
    "desconocida",
}


def _warn(warnings: list[str], path: str, message: str) -> None:
    warnings.append(f"{path}: {message}")


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

    for index, instruccion in enumerate(instrucciones):
        path = f"instrucciones[{index}]"
        if not isinstance(instruccion, dict):
            _warn(warnings, path, "expected object")
            continue

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
        if ejecutabilidad is not None and "esProcesable" not in ejecutabilidad:
            _warn(warnings, f"{path}.ejecutabilidad.esProcesable", "missing")

        movimiento = instruccion.get("movimiento")
        if movimiento is None:
            continue
        if not isinstance(movimiento, dict):
            _warn(warnings, f"{path}.movimiento", "expected object or null")
            continue

        confianza = movimiento.get("confianzaTipoMovimiento")
        if not isinstance(confianza, Number) or not 0 <= confianza <= 1:
            _warn(
                warnings,
                f"{path}.movimiento.confianzaTipoMovimiento",
                "expected number between 0 and 1",
            )

        _validate_fondos(movimiento, "origenFondos", f"{path}.movimiento", warnings)
        _validate_fondos(movimiento, "destinoFondos", f"{path}.movimiento", warnings)

        importe = movimiento.get("importe")
        if isinstance(importe, dict):
            if not isinstance(importe.get("valor"), Number):
                _warn(warnings, f"{path}.movimiento.importe.valor", "expected number")
            if not importe.get("moneda"):
                _warn(warnings, f"{path}.movimiento.importe.moneda", "missing")
        else:
            _warn(warnings, f"{path}.movimiento.importe", "expected object")

    return warnings
