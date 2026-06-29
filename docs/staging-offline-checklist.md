# Staging Offline Checklist

Este checklist convierte la descarga de Qwen/HuggingFace en un artefacto controlado para una prueba bancaria. No reemplaza aprobacion legal, procurement ni seguridad interna del banco.

## 1. Maquina controlada con internet

- Usar una maquina temporal aprobada para descarga de dependencias.
- Registrar operador, fecha, IP/red y sistema operativo.
- Descargar codigo fuente desde el commit aprobado.
- Descargar wheels de Python, `llama-server.exe` y los shards GGUF del modelo Qwen2.5 `Q4_K_M`.
- No procesar oficios reales en esta maquina.

Evidencia:

- Commit de codigo.
- Lista de archivos descargados.
- URL de origen HuggingFace del modelo.
- URL/release de llama.cpp.

## 2. Captura de SHA-256 y manifest del modelo

- Calcular SHA-256 de cada shard `.gguf` descargado.
- Generar o revisar `models\model-manifest.json`.
- Registrar `model_id`, `repo`, `filename`, `files`, `license`, `source_url`, `sha256` y fecha.
- Ejecutar:

```powershell
python verify_model.py
```

Evidencia:

- `models\model-manifest.json`.
- Salida de `python verify_model.py`.
- Captura de los SHA-256 de los shards del modelo y del paquete offline.

## 3. Contenido minimo del paquete offline

El paquete offline debe contener:

- Codigo fuente del pipeline.
- `requirements.txt` y wheels locales necesarios.
- `llama-server.exe` y evidencia SHA-256.
- `models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf`.
- `models\qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf`.
- `models\model-manifest.json`.
- `DEPLOY.md`.
- Este checklist.

No incluir:

- PDFs reales.
- JSONs de salida con datos personales.
- Logs con contenido de documentos.
- Credenciales o tokens.

## 4. Instalacion en servidor final sin internet

- Copiar el paquete offline al servidor final.
- Instalar Python y dependencias desde wheels locales.
- Confirmar que el servidor no accede a HuggingFace, GitHub ni internet durante la instalacion.
- Ejecutar:

```powershell
python verify_model.py
```

La instalacion no pasa a staging si falta el manifest o si el SHA-256 no coincide.

## 5. Firewall y egress

- Mantener `llama-server` escuchando solo en `127.0.0.1`.
- Bloquear inbound al puerto 8080 desde red.
- Bloquear egress general desde el servidor si la politica del banco lo requiere.
- Documentar excepciones de egress, si existen.

Evidencia:

- Reglas de Windows Firewall o firewall corporativo.
- Prueba de que `127.0.0.1:8080` no responde desde otra maquina.
- Prueba de que no hay salida a HuggingFace/GitHub desde el servidor final.

## 6. Cifrado de disco

- En Windows Server, validar BitLocker o cifrado equivalente aprobado por el banco.
- En Linux, validar LUKS o cifrado equivalente.
- Registrar responsable, fecha y estado.

Evidencia:

- Captura/comando de estado de BitLocker o LUKS.
- Politica de resguardo de claves.

## 7. Prueba funcional controlada

- Usar PDFs sinteticos o anonimizados.
- Ejecutar `run.bat` o `process.bat`.
- Verificar que los JSONs contienen `_pipeline.audit`.
- Verificar que `logs\audit.jsonl` se genera y que la cadena se valida con `verify_log_chain` desde `audit_log.py`.
- Confirmar que no se escribe texto completo de documentos en logs.

Evidencia:

- Salida JSON anonima.
- `index.jsonl`.
- `logs\audit.jsonl`.
- Log de corrida sin PII.

## 8. Rollback y desmantelamiento

- Detener `llama-server`.
- Retirar o archivar el paquete offline aprobado.
- Borrar input/output/logs segun politica de retencion del banco.
- Conservar hashes, manifest y acta de prueba si compliance lo requiere.
- Documentar version anterior a restaurar.

Evidencia:

- Registro de rollback.
- Hash del paquete retirado.
- Confirmacion de borrado o retencion aprobada.
