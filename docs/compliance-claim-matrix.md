# Matriz de Claims de Compliance - Cedeira IA Oficios

Esta matriz define que se puede afirmar hoy, que queda para staging bancario y que sigue como roadmap. `llmlocalpdf` es la fuente de verdad tecnica; `cedeira-ia-compliance` debe reflejar este estado sin presentar como implementado lo que aun no existe.

## Modelo Canonico Actual

| Item | Estado | Evidencia | Nota |
|---|---|---|---|
| Modelo operativo | Implementado | `setup_llm.py` descarga `qwen2.5-7b-instruct-q4_k_m.gguf`; `README.md` describe Qwen2.5 7B | El portal debe decir Qwen2.5-7B-Instruct-GGUF Q4_K_M salvo que hable de una evaluacion futura de Qwen3. |
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
| Metadata basica | Implementado | `_pipeline.source_file`, `needs_ocr`, `warnings`, `processed_at` en `process_pdfs.py` | "Cada salida incluye metadata basica del pipeline." |
| Deteccion de PDF sin texto | Implementado | `pdf_extract.py` devuelve `needs_ocr=True` si no hay texto extraible | "Los PDFs sin texto se marcan como pendientes de OCR." |
| Validacion CBU helper | Parcial | `cbu.py` valida checksum y extrae CBUs; no esta integrado al flujo principal | "Existe helper de validacion CBU; integracion al pipeline en staging." |
| Logs sin contenido del documento | Implementado parcial | `process_pdfs.py` configura file logs a nivel INFO | "Los logs operativos no persisten el texto completo del oficio." |

## Staging Bancario

Estos claims son necesarios para homologacion, pero todavia no deben venderse como implementados.

| Claim | Estado | Trabajo requerido | Gate de evidencia |
|---|---|---|---|
| Validacion deterministica post-LLM | Staging | Validar schema, enums, rangos, conteos y coherencia `movimiento` / `tipoInstruccion` | Tests de contrato pasan y warnings se reflejan en JSON. |
| CBU integrada al pipeline | Staging | Usar `cbu.py` en `postprocess.py` y bloquear CBU invalida | CBU invalida produce `esProcesable=false`. |
| CUIT e importes validados | Staging | Agregar validadores y normalizadores deterministas | Tests de CUIT/importe y casos negativos. |
| Fuente por campo critico | Staging | Anclar CBU, importe y beneficiario al texto extraido | Cada campo critico tiene snippet/evidencia o dispara revision. |
| Hash del PDF | Staging | Calcular SHA-256 del input | `_audit.input_sha256` presente. |
| Hash del texto extraido | Staging | Calcular SHA-256 del texto normalizado | `_audit.extracted_text_sha256` presente. |
| Hash/version del prompt | Staging | Calcular SHA-256 de `prompt_template.txt` | `_audit.prompt_sha256` presente. |
| Commit del codigo | Staging | Guardar `git rev-parse HEAD` en metadata | `_audit.code_commit` presente. |
| Hash del `.gguf` | Staging | Manifest local del modelo y verificacion al arranque | Startup falla si el modelo no coincide. |
| Audit log append-only | Staging | JSONL con cadena de hash, sin PII | Test de tampering detecta alteracion. |
| Reporte de revision humana | Staging | HTML local por oficio con JSON, warnings y anchors | Demo con casos procesable/revision/no procesable. |
| Instalacion offline | Staging | Paquete de modelo/binario predescargado y verificado | Instalacion sin internet en servidor aislado. |
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
| Logs inmutables | Roadmap/Staging | Hay logs normales; falta hash chain o almacenamiento append-only. |
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
- "La salida actual es JSON Cedeira v1.0 con metadata basica de pipeline."
- "Los controles de homologacion bancaria se organizan en implementado hoy, staging y roadmap."
- "Fuente por campo, validacion deterministica completa, hash del modelo, auditoria append-only y revision humana son el siguiente corte de staging."

## Claims Que No Deben Figurar Como Implementados

- Qwen3-8B como modelo operativo.
- RAG.
- Dashboard administrativo.
- AD/MFA.
- TLS 1.3.
- AES-256 implementado por la aplicacion.
- Logs inmutables.
- Citas pagina/offset por cada campo.
- Integracion core bancario.
- AWS S3 activo.
- `appsettings.json`.
- `0.0.0.0:9090`.

## Regla De Actualizacion

Cada vez que se agregue un control en `llmlocalpdf`, actualizar esta matriz antes de actualizar el portal. La presentacion al banco solo puede decir "implementado" cuando hay:

1. Codigo o configuracion que implementa el control.
2. Test o evidencia operativa que lo verifica.
3. Documentacion que explica como auditarlo.

