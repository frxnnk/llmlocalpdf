# Procesador de Oficios Judiciales con LLM Local

Pipeline automatizado que procesa oficios judiciales argentinos en PDF, extrae texto, lo envía a un LLM local (Qwen2.5 7B via llama.cpp) y genera un JSON estructurado con instrucciones, movimientos de dinero, CBUs, importes, partes y beneficiarios.

**Todo corre 100% local** — sin API keys, sin datos enviados a la nube, sin dependencias externas en runtime.

## Requisitos

- **Python 3.10+** (marcar "Add to PATH" durante la instalación)
- **Windows 10/11 o Windows Server 2019+**
- **~12 GB de disco** (modelo 4.4 GB + llama.cpp + dependencias)
- **~10 GB de RAM libres** (modelo cargado en memoria)

## Instalación (una sola vez)

```
1. Instalar Python 3.10+ desde https://www.python.org/downloads/
2. Clonar o copiar el proyecto:
   git clone https://github.com/frxnnk/llmlocalpdf.git C:\pipeline\llmlocalpdf
3. Doble-click en install.bat
```

`install.bat` hace todo automáticamente:
- Crea entorno virtual Python (`venv/`)
- Instala dependencias (`requirements.txt`)
- Descarga llama.cpp server (~20 MB desde GitHub)
- Descarga modelo Qwen2.5-7B-Instruct Q4_K_M (~4.4 GB desde HuggingFace)
- Crea carpetas de trabajo (`input/`, `output/`)

> La primera instalación tarda ~30 minutos dependiendo de la velocidad de internet (el modelo pesa 4.4 GB).

## Uso diario

### Opción 1: `run.bat` — un solo click (recomendado)

```
1. Copiar PDFs a la carpeta input\
2. Doble-click en run.bat
3. Esperar — se abre la carpeta output\ con los resultados
```

`run.bat` orquesta todo el ciclo automáticamente:
1. Verifica que la instalación esté completa (si no, ejecuta `install.bat`)
2. Verifica que haya PDFs en `input\`
3. Levanta el servidor LLM en segundo plano
4. Espera a que el servidor esté listo (health check con reintentos)
5. Procesa todos los PDFs
6. Detiene el servidor LLM
7. Abre la carpeta `output\` con los resultados

> Si el servidor ya estaba corriendo (levantado manualmente), `run.bat` lo detecta, lo usa, y **no lo mata** al terminar.

### Opción 2: Scripts individuales (uso avanzado)

Para quienes prefieran controlar cada paso:

```bash
# Terminal 1: Levantar el servidor LLM
start_server.bat

# Terminal 2: Procesar PDFs (con el servidor ya corriendo)
process.bat

# Al terminar, detener el servidor
stop_server.bat
```

### Opción 3: Línea de comandos

```bash
# Procesar PDFs con parámetros custom
python process_pdfs.py --input carpeta_pdfs/ --output carpeta_salida/

# Con endpoint custom y más workers
python process_pdfs.py --input pdfs/ --output output/ --endpoint http://127.0.0.1:8080/v1/chat/completions --workers 4
```

#### Parámetros CLI

| Parámetro    | Default                                            | Descripción                     |
|-------------|----------------------------------------------------|---------------------------------|
| `--input`   | (requerido)                                        | Directorio con PDFs             |
| `--output`  | (requerido)                                        | Directorio de salida para JSONs |
| `--endpoint`| `http://127.0.0.1:8080/v1/chat/completions`       | Endpoint del LLM                |
| `--workers` | `2`                                                | Workers concurrentes            |

### Idempotencia

Si el JSON de salida ya existe para un PDF, se skipea automáticamente. Borrar el JSON correspondiente para reprocesar.

## Scripts disponibles

| Script | Descripción |
|---|---|
| `run.bat` | **Ciclo completo**: server + procesar + cleanup (recomendado) |
| `install.bat` | Setup one-time: venv + pip install + descarga modelo |
| `start_server.bat` | Levanta llama-server en localhost:8080 |
| `stop_server.bat` | Mata el proceso llama-server |
| `process.bat` | Procesa PDFs de `input\` a `output\` |

## Deploy en Server (SERVERDELL)

### Hardware de referencia

- **CPU**: Intel Xeon E-2336 (6 cores / 12 threads) @ 2.90 GHz — sin GPU
- **RAM**: 32 GB
- **Modelo**: Qwen2.5-7B Q4_K_M (~4.4 GB en disco, ~7-8 GB en RAM)
- **Rendimiento estimado**: ~2 min/PDF. Para 100 PDFs/día = ~3.3 horas.

### Setup paso a paso

```
SETUP (una vez, IT):
  1. Instalar Python 3.10+ (marcar "Add to PATH")
  2. git clone https://github.com/frxnnk/llmlocalpdf.git C:\pipeline\llmlocalpdf
  3. Doble-click install.bat  (~30 min, descarga modelo 4.4 GB)

USO DIARIO (el equipo):
  1. Copiar PDFs a input\
  2. Doble-click run.bat
  3. Esperar -> se abre la carpeta output\ con los resultados
```

### Rendimiento CPU-only

- `--workers 1` en `process.bat`: con CPU-only un solo worker es más eficiente (no compiten por threads del LLM)
- `-t 6` en `start_server.bat`: usa los 6 cores físicos del Xeon (óptimo para llama.cpp)
- `-c 4096`: contexto suficiente para oficios judiciales típicos

## Schema JSON de salida

Cada PDF genera un `<nombre>.json` con el schema Cedeira v1.0:

```json
{
  "schemaVersion": "1.0",
  "oficioId": "uuid-generado",
  "resumenGeneral": {
    "cantidadInstrucciones": 2,
    "contieneMovimientosDinero": true,
    "contieneInstruccionesNoFinancieras": false
  },
  "instrucciones": [
    {
      "instructionId": "1",
      "tipoInstruccion": "movimiento_dinero",
      "descripcionIA": "El juzgado ordena transferir $500.000 al CBU indicado",
      "movimiento": {
        "tipoMovimiento": "transferencia_mep",
        "confianzaTipoMovimiento": 0.9,
        "origenFondos": {
          "tipo": "cuenta_judicial",
          "identificador": "2850622-3 5009587799576-5"
        },
        "destinoFondos": {
          "tipo": "cbu",
          "identificador": "0110040400000000000017"
        },
        "importe": {
          "valor": 500000.0,
          "moneda": "ARS"
        },
        "beneficiario": {
          "tipo": "persona",
          "nombre": "Juan Perez",
          "cuit": "20-12345678-9"
        }
      },
      "ejecutabilidad": {
        "esProcesable": true,
        "motivoNoProcesable": null
      }
    }
  ],
  "_pipeline": {
    "source_file": "oficio_001.pdf",
    "needs_ocr": false,
    "warnings": [],
    "processed_at": "2025-01-15T10:30:00"
  }
}
```

Además se genera `index.jsonl` con una línea por PDF procesado.

## Estructura del proyecto

```
llmlocalpdf/
├── run.bat                  # Ciclo completo automatizado
├── install.bat              # Setup automático (una vez)
├── start_server.bat         # Levantar llama-server
├── stop_server.bat          # Detener llama-server
├── process.bat              # Procesar PDFs
├── process_pdfs.py          # CLI principal
├── llm_client.py            # Cliente HTTP para LLM
├── pdf_extract.py           # Extracción de texto con pdfplumber
├── cbu.py                   # Validación y extracción de CBUs
├── postprocess.py           # Reconciliación de instrucciones
├── prompt_template.txt      # Prompt para extracción (schema Cedeira)
├── prompt_fix_json.txt      # Prompt para reparar JSON
├── setup_llm.py             # Descarga llama.cpp + modelo
├── requirements.txt         # Dependencias Python pineadas
├── .gitignore
├── input/                   # PDFs a procesar (usuario)
├── output/                  # JSONs generados (resultados)
├── logs/                    # Logs de ejecución
├── models/                  # Modelo GGUF (auto-descargado)
├── llama-server/            # Binario llama.cpp (auto-descargado)
├── venv/                    # Entorno virtual Python
└── tests/
    └── test_cbu.py          # Tests unitarios
```

## Seguridad

- **100% local**: ningún dato sale del servidor. Sin APIs externas, sin telemetría.
- **llama-server bindeado a 127.0.0.1**: solo escucha en localhost, no accesible desde la red.
- **Sin credenciales**: no hay API keys, tokens, ni secrets.
- **Firewall** (recomendado como defensa en profundidad):
  ```
  netsh advfirewall firewall add rule name="Block llama-server inbound" dir=in action=block protocol=TCP localport=8080
  ```
- **Logging**: toda la actividad queda registrada en `logs/`.

## Tests

```bash
python -m pytest tests/ -v
```

## Troubleshooting

| Problema | Solución |
|---|---|
| `No se encontro llama-server.exe` | Ejecutar `install.bat` (o `run.bat` lo hace automáticamente) |
| `No hay archivos PDF en la carpeta input\` | Copiar los PDFs a la carpeta `input\` antes de ejecutar |
| `El servidor no respondio despues de 90 segundos` | Revisar la ventana del servidor por errores de memoria |
| Modelo no descarga | Verificar conexión a internet. Retry: `python setup_llm.py` |
| JSON con `needs_ocr: true` | El PDF es imagen escaneada, no tiene texto extraíble |
| Procesamiento muy lento | Normal con CPU-only (~2 min/PDF). No usar más de 1 worker |
| `Python no esta en el PATH` | Reinstalar Python marcando "Add to PATH" |
| Error de memoria | Cerrar otras aplicaciones. El modelo necesita ~8 GB de RAM |

## Notas para Windows Server 2019

- Asegurar que Python está en el PATH del sistema
- Usar `python` (no `python3`) en Windows
- Los paths de entrada/salida pueden usar `/` o `\`
- El encoding es UTF-8 forzado en toda la I/O
