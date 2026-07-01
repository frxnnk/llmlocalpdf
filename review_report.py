"""Reporte HTML local para revisar resultados y evidencia de auditoria."""

from html import escape
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    return escape(str(value), quote=True)


def _status(value: bool) -> str:
    return "si" if value else "no"


def _list_items(values: list[Any]) -> str:
    if not values:
        return "<li>Sin elementos</li>"
    return "".join(f"<li>{_text(value)}</li>" for value in values)


def _audit_table(audit: dict) -> str:
    keys = [
        "source_sha256",
        "extracted_text_sha256",
        "prompt_sha256",
        "model_manifest_sha256",
        "model_sha256",
        "code_commit",
        "processed_at",
    ]
    rows = []
    for key in keys:
        if key in audit:
            rows.append(f"<tr><th>{_text(key)}</th><td><code>{_text(audit[key])}</code></td></tr>")
    if not rows:
        rows.append("<tr><td colspan=\"2\">Sin metadata de auditoria</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def _anchors_table(anchors: dict) -> str:
    rows = []
    for field, anchor in sorted(anchors.items()):
        if not isinstance(anchor, dict):
            continue
        rows.append(
            "<tr>"
            f"<td><code>{_text(field)}</code></td>"
            f"<td>{_text(_status(bool(anchor.get('found'))))}</td>"
            f"<td>{_text(anchor.get('start'))}</td>"
            f"<td>{_text(anchor.get('end'))}</td>"
            f"<td>{_text(anchor.get('snippet'))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan=\"5\">Sin anchors</td></tr>")
    return (
        "<table><thead><tr><th>Campo</th><th>Encontrado</th><th>Inicio</th>"
        "<th>Fin</th><th>Snippet</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _instruction_rows(instrucciones: list) -> str:
    rows = []
    for instr in instrucciones:
        if not isinstance(instr, dict):
            continue
        mov = instr.get("movimiento") if isinstance(instr.get("movimiento"), dict) else {}
        beneficiario = mov.get("beneficiario") if isinstance(mov.get("beneficiario"), dict) else {}
        origen = mov.get("origenFondos") if isinstance(mov.get("origenFondos"), dict) else {}
        destino = mov.get("destinoFondos") if isinstance(mov.get("destinoFondos"), dict) else {}
        importe = mov.get("importe") if isinstance(mov.get("importe"), dict) else {}
        ejecutabilidad = (
            instr.get("ejecutabilidad") if isinstance(instr.get("ejecutabilidad"), dict) else {}
        )
        rows.append(
            "<tr>"
            f"<td>{_text(instr.get('instructionId'))}</td>"
            f"<td>{_text(instr.get('tipoInstruccion'))}</td>"
            f"<td>{_text(instr.get('descripcionIA'))}</td>"
            f"<td>{_text(origen.get('tipo'))}: <code>{_text(origen.get('identificador'))}</code></td>"
            f"<td>{_text(destino.get('tipo'))}: <code>{_text(destino.get('identificador'))}</code></td>"
            f"<td>{_text(importe.get('moneda'))} {_text(importe.get('valor'))}</td>"
            f"<td>{_text(beneficiario.get('nombre'))}<br><code>{_text(beneficiario.get('cuit'))}</code></td>"
            f"<td>{_text(_status(bool(ejecutabilidad.get('esProcesable'))))}</td>"
            f"<td>{_text(ejecutabilidad.get('motivoNoProcesable'))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan=\"9\">Sin instrucciones</td></tr>")
    return "".join(rows)


def build_review_report_html(result: dict, source_filename: str | None = None) -> str:
    pipeline = result.get("_pipeline", {}) if isinstance(result.get("_pipeline"), dict) else {}
    validation = (
        result.get("_validation", {}) if isinstance(result.get("_validation"), dict) else {}
    )
    resumen = (
        result.get("resumenGeneral", {}) if isinstance(result.get("resumenGeneral"), dict) else {}
    )
    source = source_filename or pipeline.get("source_file") or ""
    audit = pipeline.get("audit", {}) if isinstance(pipeline.get("audit"), dict) else {}
    instrucciones = result.get("instrucciones", [])
    if not isinstance(instrucciones, list):
        instrucciones = []

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Revision oficio {_text(result.get("oficioId"))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; }}
    h1, h2 {{ margin: 0 0 12px; }}
    section {{ margin: 24px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    th, td {{ border: 1px solid #cfd7df; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f6; }}
    code {{ word-break: break-all; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .meta div {{ border: 1px solid #cfd7df; padding: 8px; }}
  </style>
</head>
<body>
  <h1>Revision local de oficio</h1>
  <section class="meta">
    <div><strong>Archivo</strong><br>{_text(source)}</div>
    <div><strong>Oficio ID</strong><br>{_text(result.get("oficioId"))}</div>
    <div><strong>Procesado</strong><br>{_text(pipeline.get("processed_at"))}</div>
    <div><strong>Requiere OCR</strong><br>{_text(_status(bool(pipeline.get("needs_ocr"))))}</div>
    <div><strong>Instrucciones</strong><br>{_text(resumen.get("cantidadInstrucciones"))}</div>
    <div><strong>Movimientos de dinero</strong><br>{_text(_status(bool(resumen.get("contieneMovimientosDinero"))))}</div>
  </section>
  <section>
    <h2>Auditoria</h2>
    {_audit_table(audit)}
  </section>
  <section>
    <h2>Warnings</h2>
    <h3>Schema</h3>
    <ul>{_list_items(validation.get("schema_warnings", []))}</ul>
    <h3>Pipeline</h3>
    <ul>{_list_items(pipeline.get("warnings", []))}</ul>
  </section>
  <section>
    <h2>Instrucciones</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th><th>Tipo</th><th>Descripcion IA</th><th>Origen</th>
          <th>Destino</th><th>Importe</th><th>Beneficiario</th>
          <th>Procesable</th><th>Motivo</th>
        </tr>
      </thead>
      <tbody>{_instruction_rows(instrucciones)}</tbody>
    </table>
  </section>
  <section>
    <h2>Anchors de fuente</h2>
    {_anchors_table(validation.get("source_anchors", {}))}
  </section>
</body>
</html>
"""


def write_review_report(
    result: dict, report_path: Path, source_filename: str | None = None
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        build_review_report_html(result, source_filename=source_filename),
        encoding="utf-8",
    )
