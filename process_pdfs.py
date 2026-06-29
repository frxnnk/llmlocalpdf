"""CLI principal para procesar PDFs de oficios judiciales con LLM local."""

import argparse
import json
import logging
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from llm_client import LLMClient
from pdf_extract import extract_text, normalize_text
from postprocess import reconcile_instrucciones

logger = logging.getLogger(__name__)


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
        result = {
            "schemaVersion": "1.0",
            "oficioId": oficio_id,
            "_pipeline": {
                "source_file": pdf_path.name,
                "needs_ocr": True,
                "error": "PDF sin texto extraíble, requiere OCR",
                "warnings": [],
                "processed_at": datetime.now().isoformat(),
            },
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
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
    llm_result["_pipeline"] = {
        "source_file": pdf_path.name,
        "needs_ocr": False,
        "warnings": warnings,
        "processed_at": datetime.now().isoformat(),
    }

    # Escribir JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(llm_result, f, ensure_ascii=False, indent=2)

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
    with open(index_file, "w", encoding="utf-8") as f:
        for row in sorted(index_rows, key=lambda r: r["filename"]):
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
