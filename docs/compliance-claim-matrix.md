# Matriz de Claims de Compliance - Cedeira IA Oficios

Esta matriz define que se puede afirmar hoy, que queda para staging bancario y que sigue como roadmap. `llmlocalpdf` es la fuente de verdad tecnica; `cedeira-ia-compliance` debe reflejar este estado sin presentar como implementado lo que aun no existe.

## Modelo Canonico Actual

| Item | Estado | Evidencia | Nota |
|---|---|---|---|
| Modelo operativo | Implementado | `setup_llm.py` descarga los shards GGUF `qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` y `qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf`; `README.md` describe Qwen2.5 7B | El portal debe decir Qwen2.5-7B-Instruct-GGUF Q4_K_M salvo que hable de una evaluacion futura de Qwen3. |
| Motor de inferencia | Implementado | `start_server.bat` ejecuta `llama-server.exe`; `llm_client.py` consume endpoint OpenAI-compatible local | El motor es `llama.cpp`, no una API externa. |
| Qwen3-8B | Roadmap / evaluacion | No hay referencia operativa en `llmlocalpdf` | No debe figurar como modelo implementado hasta migrar y medir contra golden set. |

## Implementado Hoy

| Claim | Estado | Evidencia en `llmlocalpdf` | Claim permitido |
|---|---|---|---|
| Ejecucion local por defecto | Implementado | `run.bat`, `start_server.bat`, `llm_client.py` usan `127.0.0.1:8080` | "El pipeline corre localmente en el servidor." |
| Sin API keys | Implementado | No hay secrets/API keys en `requirements.txt`, scripts ni cliente LLM | "No depende de APIs cloud para inferencia." |
| Bind local del LLM | Implementado | `start_server.bat` usa `--host 127.0.0.1` | "El servidor LLM no queda expuesto a la red por defecto." |
| Firewall recomendado | Implementado como documentacion operativa | `README.md` y `DEPLOY.md` incluyen regla `netsh` | "Se documenta bloqueo inbound como defensa en profundidad." |
| Binario `llama.cpp` pineado | Implementado | `setup_llm.py` fija release `b8192` y SHA-256 del zip | "El binario de inferencia descargado se verifica por SHA-256." |
| JSON estructurado | Implementado | `prompt_template.txt`, `process_pdfs.py` escriben JSON por PDF | "El resultado se entrega como JSON con schema Cedeira v1.0." |
| Metadata auditada | Implementado | `audit_metadata.py`; `_pipeline.audit.source_sha256`, `extracted_text_sha256`, `prompt_sha256`, `model_id`, `model_sha256` si hay manifest, `code_commit`, `processed_at` | "Cada salida incluye metadata reproducible de auditoria." |
| Deteccion de PDF sin texto | Implementado | `pdf_extract.py` devuelve `needs_ocr=True` si no hay texto extraible | "Los PDFs sin texto se marcan como pendientes de OCR." |
| Validacion deterministica post-LLM | Implementado | `schema_contract.py`, `postprocess.py`, `tests/test_schema_contract.py` | "La salida se valida contra un contrato deterministico antes de publicarse." |
| CBU integrada al pipeline | Implementado | `postprocess.py` usa `cbu.py`; `tests/test_cbu.py` verifica bloqueo por checksum invalido | "Una CBU invalida marca la instruccion como no procesable." |
| Fuente para campos criticos | Implementado | `source_anchor.py`, `postprocess.py`, `_validation.source_anchors`, `tests/test_source_anchor.py` | "Cuenta judicial, CBU, importe, beneficiario y CUIT se anclan al texto fuente normalizado con snippet y offsets de texto." |
| Manifest del modelo | Implementado | `model_registry.py`, `verify_model.py`, `setup_llm.py`, `start_server.bat` | "El modelo local se verifica contra un manifest SHA-256 antes de iniciar." |
| Audit log append-only local | Implementado | `audit_log.py` genera `logs/audit.jsonl` con cadena de hashes; tests detectan tampering | "Cada PDF procesado deja un evento hash-chain sin texto del documento." |
| Reporte de revision humana local | Implementado | `review_report.py`, `process_pdfs.py`, `tests/test_review_report.py`, `tests/test_output_writer.py` | "Cada JSON procesado genera un HTML local de revision con hashes, warnings, instrucciones y anchors." |
| Instalacion offline documentada | Implementado como documentacion operativa | `DEPLOY.md`, `docs/staging-offline-checklist.md` | "El despliegue bancario usa paquete offline y evidencia de SHA-256/egress." |
| Logs sin contenido del documento | Implementado parcial | `process_pdfs.py` configura file logs a nivel INFO | "Los logs operativos no persisten el texto completo del oficio." |

## Staging Bancario

Estos claims son necesarios para homologacion, pero todavia no deben venderse como implementados.

| Claim | Estado | Trabajo requerido | Gate de evidencia |
|---|---|---|---|
| CUIT e importes validados | Staging | Agregar validadores y normalizadores deterministas | Tests de CUIT/importe y casos negativos. |
| Citas por pagina de PDF | Staging | Mapear anchors del texto normalizado a pagina/coordenadas de PDF | Cada campo critico tiene pagina/snippet/evidencia o dispara revision. |
| Paquete offline probado en servidor aislado | Staging | Ejecutar checklist offline en entorno bancario real | Instalacion sin internet con evidencias firmadas. |
| No egress en runtime | Staging | Bloqueo firewall/DMZ y evidencia operativa | Logs/reglas de firewall demuestran cero salida durante procesamiento. |
| Cifrado en reposo | Staging | BitLocker/volumen cifrado o politica aprobada del banco | Evidencia de volumen cifrado para input/output/logs/modelo. |

## Roadmap / No Implementado

| Claim | Estado | Motivo |
|---|---|---|
| Dashboard administrativo | Roadmap | `llmlocalpdf` es batch por carpetas; no existe UI ni backend web administrativo. |
| AD / MFA | Roadmap | No hay sistema de usuarios en el producto actual. Aplicaria si se crea dashboard/API. |
| TLS 1.3 | Roadmap | El runtime actual es localhost. TLS aplica a una API/dashboard futura o reverse proxy. |
| Cola SQLite | Roadmap | Hoy se procesan archivos `*.pdf` desde `input/` y se escriben JSONs en `output/`. |
| Integracion core bancario | Roadmap | El MVP no debe ejecutar operaciones ni llamar un core real. Primero export validado. |
| RAG / vector database | Roadmap | No hay vector DB ni retrieval. La arquitectura actual es extraccion anclada al PDF de entrada. |
| WORM/SIEM externo | Roadmap/Staging | Hay hash-chain local; falta almacenamiento inmutable externo o politica WORM aprobada. |
| SAST/DAST formal | Roadmap | No hay pipeline de seguridad formal sobre `llama.cpp` o scripts. |
| Auditoria de sesgos | Roadmap | Falta dataset, metodologia y metricas por subgrupo. |
| Alta disponibilidad / fail-safe automatico | Roadmap | El producto actual es batch local; no hay SLA online ni nodo secundario. |
| Desmantelamiento NIST 800-88 | Roadmap | Falta playbook operativo y evidencia de borrado seguro. |
| AWS S3 activo | No aplica hoy | No hay path S3/AWS en `llmlocalpdf`; remover del portal salvo evidencia de otro sistema. |
| `appsettings.json` / admin password | No aplica hoy | No existe app .NET ni archivo `appsettings.json` en `llmlocalpdf`. |
| Dashboard en `0.0.0.0:9090` | No aplica hoy | No existe dashboard; `llama-server` corre en `127.0.0.1:8080`. |

## Claims Permitidos Para Portal

Usar estos textos como base en `cedeira-ia-compliance`:

- "Cedeira IA Oficios procesa PDFs de oficios judiciales en un pipeline local on-premise."
- "La inferencia usa `llama.cpp` con `Qwen2.5-7B-Instruct-GGUF Q4_K_M` en el servidor."
- "El runtime no necesita APIs cloud ni claves externas para procesar documentos."
- "La salida actual es JSON Cedeira v1.0 con metadata auditada de pipeline."
- "El pipeline valida schema, CBU y ancla cuenta judicial, CBU, importe, beneficiario y CUIT al texto fuente con snippets."
- "El modelo local se gobierna con registry, manifest y verificacion SHA-256."
- "El audit log local usa cadena de hashes append-only sin persistir texto del documento."
- "Cada oficio procesado genera un reporte HTML local de revision humana con hashes, warnings, instrucciones y anchors."
- "Los controles de homologacion bancaria se organizan en implementado hoy, staging y roadmap."
- "CUIT/importes deterministas, citas por pagina, egress evidenciado y cifrado de volumen son el siguiente corte de staging."

## Claims Que No Deben Figurar Como Implementados

- Qwen3-8B como modelo operativo.
- RAG.
- Dashboard administrativo.
- AD/MFA.
- TLS 1.3.
- AES-256 implementado por la aplicacion.
- Logs WORM/SIEM externos como implementados.
- Citas pagina por cada campo.
- Integracion core bancario.
- AWS S3 activo.
- `appsettings.json`.
- `0.0.0.0:9090`.

## Regla De Actualizacion

Cada vez que se agregue un control en `llmlocalpdf`, actualizar esta matriz antes de actualizar el portal. La presentacion al banco solo puede decir "implementado" cuando hay:

1. Codigo o configuracion que implementa el control.
2. Test o evidencia operativa que lo verifica.
3. Documentacion que explica como auditarlo.

