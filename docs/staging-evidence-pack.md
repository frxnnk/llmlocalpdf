# Staging Evidence Pack

Este paquete define la evidencia minima para defender el corte de staging sin depender de Vercel ni de infraestructura bancaria real. No incluye modelos, PDFs, outputs ni logs versionados.

## Baseline mergeado

| Repo | Branch | SHA | Nota |
|---|---|---|---|
| `llmlocalpdf` | `main` | `9ab21d805ce64fdd5846beddfc91ece2bac88475` | PR tecnico inicial mergeado con merge commit. |
| `cedeira-ia-compliance` | `main` | `3a87ea06d61cb35d01c92122ee74b8e60cf90285` | Portal/documentacion alineado; Vercel no fue gate por permisos externos. |

Tags sugeridos para congelar este corte:

- `llmlocalpdf`: `staging-baseline-2026-06-29`
- `cedeira-ia-compliance`: `staging-baseline-2026-06-29`

## Comandos de verificacion local

Ejecutar desde la raiz de `llmlocalpdf`:

```powershell
python -m unittest discover -s tests -v
.\venv\Scripts\python.exe verify_model.py
.\venv\Scripts\python.exe golden_eval.py --actual test_output\simple_transfer.json --expected tests\fixtures\expected\simple_transfer.json
```

Verificar hash-chain del audit log:

```powershell
.\venv\Scripts\python.exe -c "from pathlib import Path; from audit_log import verify_log_chain; print(verify_log_chain(Path('logs/audit.jsonl')))"
```

La salida esperada para audit log valido es:

```text
[]
```

## Artefactos a recolectar despues del E2E sintetico

Estos archivos se generan localmente y no se commitean:

- `models\model-manifest.json`
- `test_input\simple_transfer.pdf`
- `test_output\simple_transfer.json`
- `test_output\simple_transfer.review.html`
- `test_output\index.jsonl`
- `logs\audit.jsonl`
- Salida textual de `python verify_model.py`.
- Salida textual de `golden_eval.py`.
- Salida textual de `python -m unittest discover -s tests -v`.

## Evidencia minima dentro del JSON

`test_output\simple_transfer.json` debe incluir:

- `_pipeline.audit.source_sha256`
- `_pipeline.audit.extracted_text_sha256`
- `_pipeline.audit.prompt_sha256`
- `_pipeline.audit.model_manifest_sha256` o hashes de shards del modelo cuando aplique.
- `_pipeline.audit.code_commit`
- `_pipeline.audit.processed_at`
- `_validation.schema_warnings`
- `_validation.source_anchors`

Anchors criticos esperados cuando el fixture contiene esos datos:

- `instrucciones[0].movimiento.origenFondos.identificador`
- `instrucciones[0].movimiento.destinoFondos.identificador`
- `instrucciones[0].movimiento.importe.valor`
- `instrucciones[0].movimiento.beneficiario.nombre`
- `instrucciones[0].movimiento.beneficiario.cuit`

## Evidencia minima dentro del reporte HTML

`test_output\simple_transfer.review.html` debe mostrar:

- Archivo fuente y `oficioId`.
- Estado OCR y cantidad de instrucciones.
- Hashes auditables.
- Warnings de schema y pipeline.
- Tabla de instrucciones con origen, destino, importe, beneficiario y procesabilidad.
- Tabla de anchors con campo, estado, offsets y snippet.

El reporte no debe incluir el texto completo extraido del PDF.

## Criterio de calidad del golden set

`golden_eval.py` compara el JSON real contra `tests\fixtures\expected\simple_transfer.json`. Si el score no es perfecto, el gap se documenta como dato de calidad de modelo/prompt. No se debe editar el esperado para esconder errores del E2E.

## Limites del corte

Implementado en este corte:

- Hash del PDF fuente.
- Hash del texto normalizado extraido.
- Metadata de prompt, modelo y commit.
- Anchors de cuenta judicial, CBU, importe, beneficiario y CUIT contra texto normalizado.
- Reporte HTML local por oficio.
- Audit log local con hash-chain.

Sigue requiriendo staging bancario real:

- Prueba offline en servidor aislado sin internet.
- Evidencia de firewall/no egress.
- Cifrado de volumen aprobado por el banco.
- Reglas de retencion/borrado.
- Validadores deterministas completos de CUIT e importes.
- Citas por pagina de PDF, no solo offsets del texto normalizado.
