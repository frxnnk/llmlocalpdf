# Staging Evidence Closure - 2026-06-29

Este manifiesto cierra el paquete local de evidencia para el corte `staging-baseline-2026-06-29`.
No versiona PDFs, outputs, logs ni modelos; registra los hashes que permiten verificar el ZIP operativo local.

## Scope

| Repo | Branch | SHA | Rol |
|---|---|---|---|
| `llmlocalpdf` | `codex/staging-evidence-pack` | `9949653fe86b342c46c4d0facb808233189cd653` | Fuente tecnica, evidencia local, tests y reporte HTML. |
| `cedeira-ia-compliance` | `codex/deck-copy-evidence` | `829a796ad7ae59d2e60bbe21249451649055fb63` | Portal/deck alineado a claims implementados, staging y roadmap. |

Baselines mergeados referenciados por este cierre:

| Repo | `origin/main` SHA |
|---|---|
| `llmlocalpdf` | `9ab21d805ce64fdd5846beddfc91ece2bac88475` |
| `cedeira-ia-compliance` | `3a87ea06d61cb35d01c92122ee74b8e60cf90285` |

## Verification Run

Fecha local de captura: `2026-06-29T21:36:41.4543178-03:00`.

Comandos ejecutados desde `llmlocalpdf`:

```powershell
python -m unittest discover -s tests -v
python verify_model.py
python golden_eval.py --actual test_output\simple_transfer.json --expected tests\fixtures\expected\simple_transfer.json
python -c "from pathlib import Path; from audit_log import verify_log_chain; print(verify_log_chain(Path('logs/audit.jsonl')))"
```

Resultados:

| Check | Resultado |
|---|---|
| Unit tests | `Ran 79 tests ... OK` |
| Model manifest | `[OK] Model verified: models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` |
| Golden eval | `score=1.000000; matched=15/15; passed=true; missing=-; mismatch=-` |
| Audit hash-chain | `[]` |

Comandos ejecutados desde `cedeira-ia-compliance`:

```powershell
rg -n "Qwen3|0\.0\.0\.0:9090|appsettings|AWS S3|logs inmutables" -g "*.html" -g "README.md" .
rg -n "\bRAG\b" -g "*.html" -g "README.md" . | Select-String -NotMatch "base64"
```

Resultado:

| Check | Resultado |
|---|---|
| Claims obsoletos no-RAG | Sin hits. |
| RAG | Hits solo en `informe-compliance.html` como futuro/evolucion/roadmap, no como implementado. |

## Local Artifact Manifest

El ZIP operativo local debe incluir estos artefactos generados y documentales:

| Archivo | SHA-256 | Nota |
|---|---|---|
| `test_output\simple_transfer.json` | `B5CBAC747E7E31191141062A14EF155755DFB2501E46871CC34A11BAA0687194` | JSON sintetico con metadata auditada y anchors. |
| `test_output\simple_transfer.review.html` | `F59784D36EDC3907AEDB9282F61156C05939D17E59F8826AAE9F375B24122F78` | Reporte HTML local de revision. |
| `test_output\index.jsonl` | `BE6EAD9EA27E09FBC50CC3B7CE7B5042FA3C6915F1F65855A66E88E2CFFFB18E` | Indice de salida del E2E sintetico. |
| `logs\audit.jsonl` | `C0035FC4384F3DB17F1EB66BF14370F69A0555E8E566B11ACAC2B97C52F15AB3` | Audit log local hash-chain. |
| `models\model-manifest.json` | `F9A27F3F1FE0D5ADB6F80902083CFC259C469A5CC638F9465F1C09C7C7F85C41` | Manifest SHA-256 del modelo split local. |

## Package Path

Generar y conservar localmente:

```text
test_output\staging-evidence-pack-20260629-213641.zip
```

Contenido esperado:

- `README.md`
- `DEPLOY.md`
- `docs\staging-evidence-pack.md`
- `docs\staging-offline-checklist.md`
- `docs\compliance-claim-matrix.md`
- `docs\evidence-runs\2026-06-29-staging-evidence-closure.md`
- `test_output\simple_transfer.json`
- `test_output\simple_transfer.review.html`
- `test_output\index.jsonl`
- `logs\audit.jsonl`
- `models\model-manifest.json`

## Remaining External Gates

Este cierre no reemplaza la homologacion bancaria. Sigue pendiente:

- Ejecutar el paquete offline dentro de un servidor aislado sin internet.
- Adjuntar evidencia de firewall/no-egress del entorno real.
- Adjuntar evidencia de cifrado de volumen aprobada por el banco.
- Definir retencion/borrado y almacenamiento WORM/SIEM externo si el banco lo exige.
