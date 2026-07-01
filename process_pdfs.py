"""CLI principal para procesar PDFs de oficios judiciales con LLM local."""

import argparse
import json
import logging
import os
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from audit_log import append_pdf_processed_event
from audit_metadata import build_audit_metadata
from llm_client import LLMClient
from pdf_extract import extract_text, normalize_text
from postprocess import reconcile_instrucciones
from review_report import write_review_report

logger = logging.getLogger(__name__)
_AUDIT_LOG_LOCK = threading.Lock()


def setup_logging(log_dir: Path) -> None:
    """Configurar logging dual: consola (INFO) + archivo (DEBUG)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"run_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Consola
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    # Archivo (INFO para no persistir contenido sensible de documentos)
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(file_handler)

    logger.info("Log file: %s", log_file)


def load_prompt(path: str) -> str:
    """Cargar un archivo de prompt como texto UTF-8."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_pipeline_metadata(
    pdf_path: Path,
    needs_ocr: bool,
    warnings: list[str],
    prompt_text: str,
    script_dir: Path,
    extracted_text: str | None = None,
    error: str | None = None,
    processed_at: str | None = None,
) -> dict:
    timestamp = processed_at or datetime.now(timezone.utc).isoformat()
    pipeline = {
        "source_file": pdf_path.name,
        "needs_ocr": needs_ocr,
        "warnings": warnings,
        "processed_at": timestamp,
        "audit": build_audit_metadata(
            pdf_path,
            prompt_text,
            extracted_text=extracted_text,
            model_manifest_path=script_dir / "models" / "model-manifest.json",
            code_dir=script_dir,
            processed_at=timestamp,
        ),
    }
    if error is not None:
        pipeline["error"] = error
    return pipeline


def write_result_outputs(result: dict, output_file: Path, source_filename: str) -> Path:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    report_file = output_file.with_name(f"{output_file.stem}.review.html")
    write_review_report(result, report_file, source_filename=source_filename)
    return report_file


def build_index_rows(input_dir: Path, output_dir: Path, new_rows: list[dict]) -> list[dict]:
    rows_by_filename = {row["filename"]: dict(row) for row in new_rows}

    for pdf_path in sorted(input_dir.glob("*.pdf")):
        if pdf_path.name in rows_by_filename:
            continue

        output_file = output_dir / f"{pdf_path.stem}.json"
        if not output_file.exists():
            continue

        with open(output_file, encoding="utf-8") as f:
            result = json.load(f)

        resumen = result.get("resumenGeneral", {})
        pipeline = result.get("_pipeline", {})
        rows_by_filename[pdf_path.name] = {
            "filename": pdf_path.name,
            "oficioId": result.get("oficioId", ""),
            "cantidadInstrucciones": resumen.get("cantidadInstrucciones", 0),
            "contieneMovimientosDinero": resumen.get("contieneMovimientosDinero", False),
            "needs_ocr": pipeline.get("needs_ocr", False),
            "warnings_count": len(pipeline.get("warnings", [])),
        }

    return sorted(rows_by_filename.values(), key=lambda row: row["filename"])


def process_single_pdf(
    pdf_path: Path,
    output_dir: Path,
    llm: LLMClient,
    system_prompt: str,
    user_prompt_template: str,
    fix_prompt_template: str,
) -> dict:
    """Procesar un solo PDF: extract → LLM → reconcile → write JSON.

    Returns:
        dict con metadata para index.jsonl
    """
    stem = pdf_path.stem
    output_file = output_dir / f"{stem}.json"

    # Generar oficioId único para este PDF
    oficio_id = str(uuid.uuid4())

    # Extracción de texto
    text, needs_ocr = extract_text(str(pdf_path))

    if needs_ocr:
        logger.warning("%s: sin texto extraíble (needs_ocr=True)", stem)
        error_message = "PDF sin texto extraíble, requiere OCR"
        result = {
            "schemaVersion": "1.0",
            "oficioId": oficio_id,
            "_pipeline": build_pipeline_metadata(
                pdf_path,
                needs_ocr=True,
                warnings=[],
                prompt_text=system_prompt,
                script_dir=Path(__file__).parent,
                extracted_text="",
                error=error_message,
            ),
        }
        write_result_outputs(result, output_file, source_filename=pdf_path.name)
        with _AUDIT_LOG_LOCK:
            append_pdf_processed_event(
                Path(__file__).parent / "logs" / "audit.jsonl",
                source_sha256=result["_pipeline"]["audit"]["source_sha256"],
                output_path=output_file,
            )
        return {
            "filename": pdf_path.name,
            "oficioId": oficio_id,
            "cantidadInstrucciones": 0,
            "contieneMovimientosDinero": False,
            "needs_ocr": True,
            "warnings_count": 0,
        }

    # Normalizar
    text = normalize_text(text)

    # Llamada al LLM
    # Separar system y user del template
    parts = system_prompt.split("### USER ###")
    sys_msg = parts[0].replace("### SYSTEM ###", "").strip()
    user_template = parts[1].strip() if len(parts) > 1 else user_prompt_template

    # Inyectar oficioId y texto del documento
    user_msg = user_template.replace("{oficio_id}", oficio_id)
    user_msg = user_msg.replace("{document_text}", text)

    llm_result = llm.call_with_json_repair(
        system=sys_msg,
        user=user_msg,
        fix_prompt_template=fix_prompt_template,
    )

    # Asegurar que oficioId esté presente en el resultado
    llm_result["oficioId"] = oficio_id
    llm_result.setdefault("schemaVersion", "1.0")

    # Limpieza ligera de identificadores en instrucciones
    llm_result, warnings = reconcile_instrucciones(llm_result, source_text=text)

    if warnings:
        for w in warnings:
            logger.warning("%s: %s", stem, w)

    # Agregar metadata del pipeline separada del schema Cedeira
    llm_result["_pipeline"] = build_pipeline_metadata(
        pdf_path,
        needs_ocr=False,
        warnings=warnings,
        prompt_text=system_prompt,
        script_dir=Path(__file__).parent,
        extracted_text=text,
    )

    # Escribir JSON
    write_result_outputs(llm_result, output_file, source_filename=pdf_path.name)
    with _AUDIT_LOG_LOCK:
        append_pdf_processed_event(
            Path(__file__).parent / "logs" / "audit.jsonl",
            source_sha256=llm_result["_pipeline"]["audit"]["source_sha256"],
            output_path=output_file,
        )

    resumen = llm_result.get("resumenGeneral", {})
    cant_instr = resumen.get("cantidadInstrucciones", 0)
    contiene_mov = resumen.get("contieneMovimientosDinero", False)

    logger.info("%s: procesado OK (instrucciones=%d, warnings=%d)",
                stem, cant_instr, len(warnings))

    return {
        "filename": pdf_path.name,
        "oficioId": oficio_id,
        "cantidadInstrucciones": cant_instr,
        "contieneMovimientosDinero": contiene_mov,
        "needs_ocr": False,
        "warnings_count": len(warnings),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Procesar PDFs de oficios judiciales con LLM local"
    )
    parser.add_argument(
        "--input", required=True, help="Directorio con PDFs a procesar"
    )
    parser.add_argument(
        "--output", required=True, help="Directorio de salida para JSONs"
    )
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8080/v1/chat/completions",
        help="Endpoint del LLM (default: http://127.0.0.1:8080/v1/chat/completions)",
    )
    parser.add_argument(
        "--workers", type=int, default=2, help="Workers concurrentes (default: 2)"
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    script_dir = Path(__file__).parent

    # Setup
    setup_logging(script_dir / "logs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cargar prompts
    prompt_file = script_dir / "prompt_template.txt"
    fix_file = script_dir / "prompt_fix_json.txt"

    if not prompt_file.exists():
        logger.error("No se encontró prompt_template.txt en %s", script_dir)
        sys.exit(1)

    system_prompt = load_prompt(str(prompt_file))
    fix_prompt_template = load_prompt(str(fix_file))

    # Encontrar PDFs
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        logger.error("No se encontraron PDFs en %s", input_dir)
        sys.exit(1)

    logger.info("Encontrados %d PDFs en %s", len(pdfs), input_dir)

    # Filtrar ya procesados (idempotencia)
    pending = []
    skipped = 0
    for pdf in pdfs:
        output_file = output_dir / f"{pdf.stem}.json"
        if output_file.exists():
            logger.info("Skip (ya procesado): %s", pdf.name)
            skipped += 1
        else:
            pending.append(pdf)

    if skipped:
        logger.info("Skipped %d PDFs ya procesados", skipped)

    if not pending:
        logger.info("Todos los PDFs ya fueron procesados")
        sys.exit(0)

    logger.info("Procesando %d PDFs con %d workers", len(pending), args.workers)

    # Cliente LLM
    llm = LLMClient(endpoint=args.endpoint)

    # Procesar con ThreadPool
    index_rows = []
    errors = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                process_single_pdf,
                pdf,
                output_dir,
                llm,
                system_prompt,
                "",  # user_prompt_template fallback (no se usa, viene del system_prompt)
                fix_prompt_template,
            ): pdf
            for pdf in pending
        }

        with tqdm(total=len(pending), desc="Procesando PDFs", unit="pdf") as pbar:
            for future in as_completed(futures):
                pdf = futures[future]
                try:
                    row = future.result()
                    index_rows.append(row)
                except Exception:
                    errors += 1
                    logger.exception("Error procesando %s", pdf.name)
                    index_rows.append({
                        "filename": pdf.name,
                        "oficioId": "",
                        "cantidadInstrucciones": 0,
                        "contieneMovimientosDinero": False,
                        "needs_ocr": False,
                        "warnings_count": 0,
                        "error": True,
                    })
                pbar.update(1)

    # Escribir index.jsonl
    index_file = output_dir / "index.jsonl"
    all_index_rows = build_index_rows(input_dir, output_dir, index_rows)
    with open(index_file, "w", encoding="utf-8") as f:
        for row in all_index_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    logger.info(
        "Completado: %d procesados, %d errores, %d skipped. Index: %s",
        len(pending) - errors,
        errors,
        skipped,
        index_file,
    )


if __name__ == "__main__":
    main()
