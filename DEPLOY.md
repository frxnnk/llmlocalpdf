# Guia de Deploy — SERVERDELL

Guia paso a paso para instalar y operar el pipeline de oficios judiciales en el servidor de produccion.

## Hardware del servidor

| Componente | Especificacion |
|---|---|
| CPU | Intel Xeon E-2336 (6 cores / 12 threads) @ 2.90 GHz |
| RAM | 32 GB |
| GPU | No tiene (el modelo corre 100% en CPU) |
| OS | Windows Server 2019 |

## Requisitos de recursos

| Recurso | Necesario | Detalle |
|---|---|---|
| Disco | ~12 GB | Modelo GGUF split ~4.4 GB total + llama.cpp ~30 MB + Python + venv |
| RAM libre | ~10 GB | El modelo Qwen2.5-7B Q4_K_M usa ~7-8 GB cargado |
| CPU | 6 threads dedicados | llama-server usa `-t 6` (los 6 cores fisicos del Xeon) |
| Red | Solo para instalacion | Descarga modelo de HuggingFace + llama.cpp de GitHub |

> En runtime NO se necesita internet. Todo corre local.

## Paso 1: Instalar Python

1. Descargar Python 3.10+ desde https://www.python.org/downloads/
2. Ejecutar el instalador
3. **IMPORTANTE**: Marcar "Add Python to PATH" en la primera pantalla del instalador
4. Verificar en cmd:
   ```
   python --version
   ```
   Debe mostrar `Python 3.10.x` o superior.

> Si `python` no se reconoce despues de instalar, reiniciar la sesion de Windows para que el PATH se actualice.

## Paso 2: Clonar el proyecto

Abrir cmd como Administrador y ejecutar:

```
git clone https://github.com/frxnnk/llmlocalpdf.git C:\pipeline\llmlocalpdf
```

Si el servidor no tiene `git`, descargar el ZIP desde GitHub y extraerlo en `C:\pipeline\llmlocalpdf`.

> La ruta `C:\pipeline\llmlocalpdf` es una sugerencia. Puede ser cualquier carpeta donde el equipo tenga permisos de lectura/escritura.

## Paso 3: Instalar dependencias y modelo

```
cd C:\pipeline\llmlocalpdf
install.bat
```

Esto ejecuta automaticamente:
1. Crea un entorno virtual Python (`venv\`)
2. Instala dependencias Python (pdfplumber, requests, tqdm, huggingface-hub)
3. Descarga `llama-server.exe` desde GitHub (~30 MB)
4. Verifica integridad del binario (SHA256)
5. Descarga el modelo Qwen2.5 `Q4_K_M` desde HuggingFace en dos shards GGUF (~4.4 GB total)
6. Crea carpetas `input\` y `output\`

**Tiempo estimado**: 20-40 minutos (depende de la velocidad de internet para bajar los ~4.4 GB del modelo).

> `install.bat` descarga desde HuggingFace solo para desarrollo o laboratorio controlado.
> Para staging bancario o produccion, no descargar el modelo desde el servidor final:
> usar el paquete offline y el checklist en `docs/staging-offline-checklist.md`.

### Verificar instalacion

Despues de `install.bat`, estas carpetas deben existir:

```
C:\pipeline\llmlocalpdf\
  ├── venv\                     (entorno virtual Python)
  ├── llama-server\             (contiene llama-server.exe)
  │   └── llama-server.exe
  └── models\                   (contiene el modelo)
      ├── qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
      ├── qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf
      └── model-manifest.json
```

Verificar el manifest local del modelo antes de levantar el servidor:

```
python verify_model.py
```

El comando debe validar el SHA-256 registrado en `models\model-manifest.json`.
Si falla o falta el manifest, el artefacto no esta listo para staging bancario.

## Staging offline para entorno bancario

Para un banco, el flujo recomendado es:

1. Descargar dependencias y modelo en una maquina controlada con internet.
2. Registrar SHA-256, licencia, URL de origen, revision/model card y aprobacion interna.
3. Armar un paquete offline con codigo, wheels, llama-server, shards `.gguf` y `models\model-manifest.json`.
4. Instalar en el servidor final sin salida a internet.
5. Ejecutar `python verify_model.py` y conservar la salida como evidencia.
6. Documentar firewall/egress, BitLocker o cifrado equivalente, y procedimiento de rollback.

Checklist detallado: `docs/staging-offline-checklist.md`.

## Paso 4: Configurar firewall (recomendado)

El servidor LLM escucha en `127.0.0.1:8080` (solo localhost). Como defensa en profundidad, bloquear el puerto 8080 desde la red:

```
netsh advfirewall firewall add rule name="Block llama-server inbound" dir=in action=block protocol=TCP localport=8080
```

Esto garantiza que aunque alguien cambie el bind address por error, el servidor no sea accesible desde la red.

## Uso diario

### Flujo simple (recomendado)

```
1. Copiar los PDFs a:  C:\pipeline\llmlocalpdf\input\
2. Doble-click en:     C:\pipeline\llmlocalpdf\run.bat
3. Esperar — se abre la carpeta output\ con los resultados
```

`run.bat` hace todo automaticamente:
- Verifica que la instalacion este completa
- Chequea que haya PDFs en `input\`
- Levanta el servidor LLM en segundo plano (ventana minimizada)
- Espera a que el servidor cargue el modelo (~30 seg)
- Procesa todos los PDFs
- Apaga el servidor
- Abre la carpeta de resultados

### Crear acceso directo en el Escritorio

Para que el equipo lo tenga mas accesible:

1. Click derecho en el Escritorio → Nuevo → Acceso directo
2. Ubicacion: `C:\pipeline\llmlocalpdf\run.bat`
3. Nombre: `Procesar Oficios`

## Resultados

Los resultados se guardan en `C:\pipeline\llmlocalpdf\output\`:

```
output\
  ├── oficio_001.json          (un JSON por cada PDF)
  ├── oficio_002.json
  └── index.jsonl              (indice con resumen de todos los procesados)
```

Cada JSON contiene:
- Instrucciones extraidas del oficio (movimientos de dinero, no financieras, administrativas)
- CBUs, cuentas judiciales, importes, monedas
- Datos del beneficiario (nombre, CUIT)
- Tipo de movimiento (transferencia MEP, plazo fijo, retencion, etc.)
- Confianza del modelo en la clasificacion
- Metadata del pipeline (archivo fuente, warnings, timestamp)

### Idempotencia

Si un PDF ya fue procesado (su JSON existe en `output\`), se saltea automaticamente. Para reprocesar un PDF, borrar su JSON de `output\` y volver a correr `run.bat`.

## Rendimiento esperado

| Metrica | Valor |
|---|---|
| Tiempo por PDF | ~2 minutos |
| 10 PDFs | ~20 minutos |
| 50 PDFs | ~1.5 horas |
| 100 PDFs | ~3.3 horas |
| RAM en uso (con modelo cargado) | ~8 GB de 32 GB |
| CPU en uso (procesando) | ~100% en 6 cores |

> El servidor queda libre para otras tareas en los 6 threads restantes (el Xeon tiene 12 threads totales).

### Por que 1 worker

El pipeline usa `--workers 1` porque con CPU-only, usar multiples workers hace que compitan por los mismos cores del LLM, resultando en tiempos peores. Un worker secuencial es mas eficiente.

## Troubleshooting

### `No se encontro llama-server.exe`

`install.bat` no se ejecuto o fallo. Correrlo de nuevo:

```
cd C:\pipeline\llmlocalpdf
install.bat
```

### `No hay archivos PDF en la carpeta input\`

Copiar los PDFs a `C:\pipeline\llmlocalpdf\input\` antes de ejecutar `run.bat`.

### `El servidor no respondio despues de 90 segundos`

El modelo esta tardando en cargar. Posibles causas:
- **RAM insuficiente**: cerrar otras aplicaciones. El modelo necesita ~8 GB libres.
- **Antivirus**: puede estar escaneando `llama-server.exe`. Agregar exclusion para `C:\pipeline\llmlocalpdf\llama-server\`.
- **Primera ejecucion**: Windows puede tardar mas la primera vez que carga el binario.

### `Python no esta en el PATH`

Reinstalar Python marcando "Add Python to PATH". Si ya esta instalado:

```
# En cmd, verificar donde esta Python
where python
```

Si no aparece, agregar manualmente al PATH del sistema:
1. Buscar "Variables de entorno" en el menu inicio
2. En "Path" del sistema, agregar la ruta donde esta `python.exe`

### JSON con `needs_ocr: true`

El PDF es una imagen escaneada, no tiene texto extraible. El pipeline no puede procesarlo sin OCR. Estos PDFs requieren procesamiento manual o agregar un paso de OCR (fuera del alcance actual).

### Procesamiento muy lento (>5 min por PDF)

Normal si el PDF tiene muchas paginas. Si consistentemente es lento:
- Verificar que no hay otros procesos consumiendo CPU intensivamente
- Revisar logs en `C:\pipeline\llmlocalpdf\logs\` para detalles

### Error de memoria

```
El modelo necesita ~8 GB de RAM libre.
RAM total: 32 GB
RAM minima libre recomendada: 10 GB
```

Cerrar aplicaciones que consuman memoria. Si el server corre otros servicios pesados, coordinar horarios de procesamiento.

## Logs

Los logs de cada ejecucion se guardan en `C:\pipeline\llmlocalpdf\logs\`:

```
logs\
  ├── run_20260303_174622.log
  ├── run_20260304_091500.log
  └── ...
```

Cada log incluye:
- PDFs encontrados y procesados
- PDFs salteados (ya procesados)
- Errores con detalle
- Timestamps de inicio y fin

> Los logs NO contienen contenido de los documentos (datos personales) por seguridad.

## Seguridad

| Control | Estado |
|---|---|
| Datos en la nube | No — todo corre local |
| API keys / tokens | No hay ninguno |
| Puerto de red expuesto | No — bind a 127.0.0.1 solamente |
| Binario verificado | Si — SHA256 del release de llama.cpp |
| Dependencias pineadas | Si — todas las versiones fijas |
| PII en logs | No — nivel INFO, sin contenido de documentos |
| Acceso a carpetas | Solo el usuario que ejecuta el script |

## Actualizaciones

Para actualizar el pipeline a una nueva version:

```
cd C:\pipeline\llmlocalpdf
git pull
install.bat
```

`install.bat` es idempotente: si el modelo y llama-server ya existen, no los vuelve a descargar.

## Contacto

Si hay problemas durante el deploy o la operacion, revisar los logs en `C:\pipeline\llmlocalpdf\logs\` y compartirlos para diagnostico.
