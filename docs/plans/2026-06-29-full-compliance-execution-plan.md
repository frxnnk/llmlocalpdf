# Full Compliance Execution Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `llmlocalpdf` into a compliance-ready on-premise judicial-office extraction pipeline and keep `cedeira-ia-compliance` truthful as the client-facing evidence portal.

**Architecture:** `llmlocalpdf` remains the source of truth for actual controls. The static portal can only claim a control as implemented when the code, tests, or deployment artifact proves it. Model use is governed through an allowlisted registry, local manifest, SHA-256 evidence, offline packaging, deterministic validators, and audit metadata.

**Tech Stack:** Python 3.10+, stdlib `unittest`, `pdfplumber`, `requests`, `tqdm`, `huggingface-hub`, Windows batch scripts, `llama.cpp` OpenAI-compatible local endpoint, static HTML documentation.

---

## Decision: Qwen Download Policy

`Qwen/Qwen2.5-7B-Instruct-GGUF` is acceptable as a **candidate implementation model**, not as an unreviewed bank-approved artifact.

Current external evidence checked on 2026-06-29:

- Hugging Face model page: `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF`
- Qwen docs / model card lineage: `https://qwen.readthedocs.io/en/latest/getting_started/concepts.html`
- Qwen project / license context: `https://github.com/QwenLM/Qwen2.5`

Policy:

- Do not present dynamic Hugging Face download as production-ready.
- Keep Qwen as an allowlisted candidate with Apache-2.0 metadata and exact filename.
- For staging, download on a controlled machine, hash the `.gguf`, record license/model card/revision, then deploy offline.
- Startup must verify the model SHA-256 against a local manifest.
- A bank can swap the model only by adding a new allowlisted entry and running the same golden-set comparison.

---

## Phase 1: Model Governance And Supply Chain

### Task 1: Add Tracked Model Registry

**Files:**
- Create: `model_registry.json`
- Create: `model_registry.py`
- Create: `tests/test_model_registry.py`

**Step 1: Write failing tests**

Test cases:

- Registry loads the default Qwen model.
- Default model has provider, source URL, license name, local filename, and risk notes.
- Missing model id raises a clear error.
- SHA-256 helper returns the expected digest for a temp file.

Run:

```powershell
python -m unittest tests.test_model_registry -v
```

Expected: FAIL because files do not exist.

**Step 2: Implement registry**

Create `model_registry.json` with:

```json
{
  "default_model_id": "qwen2.5-7b-instruct-q4_k_m",
  "models": [
    {
      "id": "qwen2.5-7b-instruct-q4_k_m",
      "provider": "Qwen / Alibaba Cloud",
      "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
      "filename": "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
      "files": [
        "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf"
      ],
      "quantization": "Q4_K_M",
      "license": "Apache-2.0",
      "source_url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF",
      "status": "candidate",
      "risk_notes": [
        "Requires bank legal/procurement approval before production.",
        "Production deploy must use an offline artifact and recorded SHA-256.",
        "Dynamic download from Hugging Face is for development only."
      ]
    }
  ]
}
```

Implement `model_registry.py` with simple functions:

- `load_registry(path: Path | None = None) -> dict`
- `get_model_spec(model_id: str | None = None) -> dict`
- `compute_sha256(path: Path) -> str`
- `build_manifest(model_path: Path, model_spec: dict) -> dict`
- `write_manifest(manifest: dict, path: Path) -> None`
- `load_manifest(path: Path) -> dict`
- `validate_manifest(model_path: Path, manifest_path: Path) -> list[str]`

**Step 3: Run tests**

```powershell
python -m unittest tests.test_model_registry -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add model_registry.json model_registry.py tests/test_model_registry.py
git commit -m "feat: add model registry and manifest helpers"
```

### Task 2: Make Model Download Explicit And Manifested

**Files:**
- Modify: `setup_llm.py`
- Modify: `install.bat`
- Create: `verify_model.py`
- Test: `tests/test_model_registry.py`

**Step 1: Write failing tests**

Add tests for:

- `build_manifest` includes `sha256`, `filename`, `repo`, `license`, `created_at`.
- `validate_manifest` returns no errors when file hash matches.
- `validate_manifest` returns a mismatch error when file content changes.

Run:

```powershell
python -m unittest tests.test_model_registry -v
```

Expected: FAIL until implementation is complete.

**Step 2: Update setup**

Change `setup_llm.py` so constants come from `model_registry.get_model_spec()`.

Rules:

- If model exists and manifest exists, verify hash.
- If model exists and manifest is missing, create `models/model-manifest.json` and print a warning that the artifact is not bank-approved until reviewed.
- If model is missing, require explicit `--accept-model-download` or environment variable `LLMLOCALPDF_ACCEPT_MODEL_DOWNLOAD=1`.
- Downloaded model always writes a manifest.

**Step 3: Add `verify_model.py`**

CLI behavior:

```powershell
python verify_model.py
```

Expected:

- Exit 0 if model and manifest match.
- Exit 1 with clear message if model missing, manifest missing, or SHA mismatch.

Optional:

```powershell
python verify_model.py --allow-unmanifested
```

Expected: exit 0 for developer mode, but prints warning.

**Step 4: Update batch scripts**

`install.bat` should pass explicit consent when it downloads in dev:

```bat
python setup_llm.py --accept-model-download
```

`start_server.bat` should run:

```bat
python "%SCRIPT_DIR%verify_model.py"
if errorlevel 1 pause & exit /b 1
```

**Step 5: Run tests and basic verify**

```powershell
python -m unittest tests.test_model_registry -v
python verify_model.py --allow-unmanifested
```

Expected: tests PASS; verify command should not crash even if model is not locally downloaded.

**Step 6: Commit**

```powershell
git add setup_llm.py install.bat start_server.bat verify_model.py tests/test_model_registry.py
git commit -m "feat: require model manifest verification"
```

---

## Phase 2: Deterministic Validation

### Task 3: Add Schema Contract Validator

**Files:**
- Create: `schema_contract.py`
- Create: `tests/test_schema_contract.py`
- Modify: `postprocess.py`

**Step 1: Write failing tests**

Test:

- Missing `schemaVersion` returns warning.
- Missing `resumenGeneral` returns warning.
- `instrucciones` not list returns warning.
- Invalid `movimiento.destinoFondos.tipo` returns warning.
- Valid minimal result returns empty warnings.

Run:

```powershell
python -m unittest tests.test_schema_contract -v
```

Expected: FAIL.

**Step 2: Implement minimal validator**

Function:

```python
def validate_schema(result: dict) -> list[str]:
    ...
```

Keep it stdlib-only and explicit. No JSON Schema dependency yet.

**Step 3: Integrate into postprocess**

`reconcile_instrucciones` should append schema warnings and set:

```python
result.setdefault("_validation", {})
result["_validation"]["schema_warnings"] = warnings
```

**Step 4: Run tests**

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add schema_contract.py postprocess.py tests/test_schema_contract.py
git commit -m "feat: add deterministic schema validation"
```

### Task 4: Integrate CBU Validation Into Pipeline

**Files:**
- Modify: `postprocess.py`
- Modify: `tests/test_cbu.py`

**Step 1: Write failing tests**

Add tests:

- `destinoFondos.tipo == "cbu"` with invalid checksum sets `esProcesable=false`.
- Invalid CBU adds warning with instruction index and field name.
- `cuenta_judicial` is not validated as CBU.
- Valid CBU is normalized and preserved.

Run:

```powershell
python -m unittest tests.test_cbu -v
```

Expected: FAIL for new behavior.

**Step 2: Implement**

Use existing `cbu.is_valid_cbu` and `cbu.normalize_cbu`.

When invalid:

- Append warning.
- Set instruction `esProcesable = False`.
- Append or set `motivoNoProcesable`.

**Step 3: Run tests**

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add postprocess.py tests/test_cbu.py
git commit -m "feat: validate cbu fields in postprocess"
```

### Task 5: Add Source Anchoring Helpers

**Files:**
- Create: `source_anchor.py`
- Create: `tests/test_source_anchor.py`
- Modify: `postprocess.py`

**Step 1: Write failing tests**

Test:

- CBU with spaces/dashes in source anchors to normalized JSON value.
- Amount `$339.649,70` anchors to `339649.70`.
- Missing value returns no anchor.
- Anchor result includes `found`, `start`, `end`, and `snippet`.

Run:

```powershell
python -m unittest tests.test_source_anchor -v
```

Expected: FAIL.

**Step 2: Implement helpers**

Functions:

- `anchor_digits(source_text: str, value: str) -> dict`
- `anchor_amount(source_text: str, value: str | int | float) -> dict`
- `make_snippet(source_text: str, start: int, end: int, window: int = 60) -> str`

**Step 3: Wire into process flow**

Change `process_single_pdf` to call postprocess with `source_text`:

```python
llm_result, warnings = reconcile_instrucciones(llm_result, source_text=text)
```

Store anchors under `_validation.source_anchors`.

**Step 4: Run tests**

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add source_anchor.py postprocess.py process_pdfs.py tests/test_source_anchor.py
git commit -m "feat: anchor extracted values to source text"
```

---

## Phase 3: Audit Metadata And Reproducibility

### Task 6: Add Run Metadata

**Files:**
- Create: `audit_metadata.py`
- Create: `tests/test_audit_metadata.py`
- Modify: `process_pdfs.py`

**Step 1: Write failing tests**

Test metadata includes:

- `source_file`
- `source_sha256`
- `prompt_sha256`
- `model_id`
- `model_filename`
- `model_sha256` if manifest exists
- `code_commit` if git is available
- `processed_at`

**Step 2: Implement**

Use stdlib only: `hashlib`, `subprocess`, `datetime`.

**Step 3: Integrate**

`_pipeline` should include audit metadata for normal and `needs_ocr` outputs.

**Step 4: Test and commit**

```powershell
python -m unittest discover -s tests -v
git add audit_metadata.py process_pdfs.py tests/test_audit_metadata.py
git commit -m "feat: add reproducible audit metadata"
```

### Task 7: Preserve Index Rows For Skipped Files

**Files:**
- Modify: `process_pdfs.py`
- Create: `tests/test_index_writer.py`

**Step 1: Write failing test**

Scenario:

- `output/a.json` already exists.
- `input/b.pdf` is processed.
- `index.jsonl` includes both `a.pdf` and `b.pdf`.

**Step 2: Implement**

Extract index writing into pure function:

```python
def build_index_rows(input_dir: Path, output_dir: Path, new_rows: list[dict]) -> list[dict]:
    ...
```

**Step 3: Test and commit**

```powershell
python -m unittest discover -s tests -v
git add process_pdfs.py tests/test_index_writer.py
git commit -m "fix: preserve skipped files in index"
```

### Task 8: Add Append-Only Audit Log

**Files:**
- Create: `audit_log.py`
- Create: `tests/test_audit_log.py`
- Modify: `process_pdfs.py`

**Step 1: Write failing tests**

Test:

- First event has `prev_hash = null`.
- Second event includes previous event hash.
- Tampering with first event breaks chain verification.

**Step 2: Implement**

JSONL hash-chain with no document text:

```json
{
  "event": "pdf_processed",
  "source_sha256": "...",
  "output_sha256": "...",
  "timestamp": "...",
  "prev_hash": "...",
  "event_hash": "..."
}
```

**Step 3: Test and commit**

```powershell
python -m unittest discover -s tests -v
git add audit_log.py process_pdfs.py tests/test_audit_log.py
git commit -m "feat: add append-only audit log"
```

---

## Phase 4: Offline/Staging Evidence

### Task 9: Offline Bundle Documentation

**Files:**
- Modify: `DEPLOY.md`
- Create: `docs/staging-offline-checklist.md`

**Steps:**

1. Document controlled download machine.
2. Document model hash capture.
3. Document package contents.
4. Document bank server install without internet.
5. Document firewall/egress evidence.
6. Document BitLocker/LUKS evidence.
7. Document rollback/desmantelamiento.

Run:

```powershell
rg -n "HuggingFace|egress|SHA-256|offline|BitLocker|modelo" DEPLOY.md docs/staging-offline-checklist.md
```

Commit:

```powershell
git add DEPLOY.md docs/staging-offline-checklist.md
git commit -m "docs: add offline staging checklist"
```

### Task 10: Compliance Claim Matrix Update

**Files:**
- Modify: `docs/compliance-claim-matrix.md`
- Modify: `C:\Users\franc\OneDrive\Documentos\dev\ferced\cedeira-ia-compliance\*.html`

**Steps:**

1. Promote controls implemented in phases 1-3 from `Staging` to `Implemented`.
2. Keep BitLocker, DMZ, AD/MFA, dashboard, core adapter as staging/roadmap unless code/evidence exists.
3. Re-run stale-claim searches.

Search:

```powershell
rg -n "Qwen3|RAG con citas|AD / MFA.*Implementado|logs inmutables.*Implementado|core bancario.*Implementado|AES-256.*Implementado" C:\Users\franc\OneDrive\Documentos\dev\ferced\cedeira-ia-compliance
```

Expected: no overclaims.

Commit:

```powershell
git add docs/compliance-claim-matrix.md
git -C C:\Users\franc\OneDrive\Documentos\dev\ferced\cedeira-ia-compliance add .
git commit -m "docs: update compliance claims after validation controls"
```

---

## Phase 5: Demo Readiness

### Task 11: Golden Fixtures

**Files:**
- Create: `tests/fixtures/text/simple_transfer.txt`
- Create: `tests/fixtures/expected/simple_transfer.json`
- Create: `golden_eval.py`
- Create: `tests/test_golden_eval.py`

**Goal:** Compare model/prompt changes without relying on vibes.

Tests:

- Fixture exact fields match.
- Missing critical fields are reported.
- Score summary is deterministic.

Commit:

```powershell
git add golden_eval.py tests/fixtures tests/test_golden_eval.py
git commit -m "test: add golden extraction evaluation"
```

### Task 12: Final Verification

Run in `llmlocalpdf`:

```powershell
python -m unittest discover -s tests -v
python verify_model.py --allow-unmanifested
git status --short --branch
```

Run in `cedeira-ia-compliance`:

```powershell
rg -n "Qwen3|0\.0\.0\.0:9090|appsettings|AWS S3|RAG con citas|core bancario.*Implementado|AD / MFA.*Implementado" .
git status --short --branch
```

Expected:

- Tests pass.
- No stale overclaim hits.
- Both repos clean except ahead commits.

---

## Execution Order

1. Phase 1 first, because model governance answers the Qwen concern.
2. Phase 2 second, because deterministic validation is the strongest compliance value.
3. Phase 3 third, because audit evidence makes the demo credible.
4. Phase 4 after code, because docs should follow evidence.
5. Phase 5 last, because golden evaluation needs the validators.

## Stop Conditions

Stop and ask before:

- Downloading a multi-GB model in this workspace.
- Pushing to GitHub.
- Changing live bank/prod infrastructure.
- Adding dependencies.
- Deleting or resetting local files.

