# Technical Source Alignment - 2026-07-01

Este manifiesto actualiza la fuente tecnica despues de mergear los PRs #2 y #3 de `llmlocalpdf`. No reemplaza el cierre historico `2026-06-29-staging-evidence-closure.md`; documenta el estado vigente para que el portal de Cedeira IA no sobreprometa controles.

## Scope

| Repo | Branch | SHA | Rol |
|---|---|---|---|
| `llmlocalpdf` | `main` | `ecc5e6ec9541ab564c6da7339c7fd792d13ff80b` | Fuente tecnica vigente; evidencia local, reportes y validacion strict. |
| `cedeira-ia-compliance` | `docs/knowledge-base` | `362aac8030bcbcaaa74b6b1a9961d54ade530f33` | Portal fuente de verdad en PR draft, pendiente de review/Vercel. |

PRs tecnicos mergeados:

- `llmlocalpdf#2`: `7eec8f14970865052a5a6b98cc115b03c45a6e9a`
- `llmlocalpdf#3`: `ecc5e6ec9541ab564c6da7339c7fd792d13ff80b`

## Verification Run

Comando ejecutado desde `llmlocalpdf`:

```powershell
python -m unittest discover -s tests -v
```

Resultado:

| Check | Resultado |
|---|---|
| Unit/integration tests | `Ran 138 tests ... OK` |

## Claim Discipline

Implementado y defendible hoy:

- Schema contract strict.
- CBU integrada al pipeline con bloqueo por checksum invalido.
- Anchors de cuenta judicial, CBU, importe, beneficiario y CUIT contra texto normalizado.
- Reporte HTML local con hashes, warnings, instrucciones y anchors.
- Audit metadata y audit log local hash-chain.
- Helpers unitarios para CUIT/CUIL e importes argentinos.

No vender como implementado todavia:

- Validacion go/no-go de CUIT/importes integrada al pipeline.
- Citas por pagina/coordenadas del PDF.
- No-egress probado en entorno bancario real.
- Cifrado de volumen, retencion formal o WORM/SIEM externo.

## Portal Sync Rule

`cedeira-ia-compliance` puede citar los helpers CUIT/importes como existentes y testeados, pero no debe decir que el pipeline los usa como validacion operativa hasta que `validators.py` quede integrado en `postprocess.py` o `schema_contract.py` con tests de pipeline.
