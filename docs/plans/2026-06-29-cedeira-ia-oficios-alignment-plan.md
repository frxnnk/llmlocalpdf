# Cedeira IA Oficios Alignment Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert `llmlocalpdf` + `cedeira-ia-compliance` into one aligned product track: an on-premise judicial-offices pipeline that produces auditable JSON from PDFs, with truthful compliance documentation and a bank-demo path.

**Architecture:** `llmlocalpdf` is the technical source of truth. `cedeira-ia-compliance` is the client-facing/compliance portal and must only claim controls that are implemented, explicitly in staging, or explicitly roadmap. The first product milestone is not automatic banking execution; it is a verifiable, reviewable, source-grounded extraction workflow.

**Tech Stack:** Python 3.10+, stdlib-first validators, `pdfplumber`, `requests`, `tqdm`, `huggingface-hub`, Windows batch scripts, `llama.cpp` OpenAI-compatible local endpoint, static HTML portal.

---

## Current Evidence

- `llmlocalpdf` is clean on `main` at `ff98bdd`.
- `cedeira-ia-compliance` is on `main` at `2fa0aac` with local uncommitted Basic Auth hardening changes in `.gitignore`, `README.md`, `middleware.js`, and `.env.example`.
- Existing `llmlocalpdf` tests passed: `python -m unittest discover -s tests -v` -> 34 tests OK.
- Runtime model in code is `Qwen2.5-7B-Instruct-GGUF Q4_K_M`.
- Portal/docs currently claim `Qwen3-8B-GGUF` and several controls that are not implemented yet.

## Product Definition

**Product name:** Cedeira IA Oficios.

**One-line promise:** A bank can run a local pipeline that turns judicial-office PDFs into structured JSON, flags risk, anchors critical fields to the original source, and produces evidence a compliance/security team can inspect.

**MVP boundary:**
- Process PDFs from a local input folder.
- Generate schema-valid JSON.
- Validate critical fields deterministically after the LLM response.
- Mark untrusted outputs as `review_required` / `esProcesable=false`.
- Generate a local review report for a human.
- Preserve audit metadata needed to reproduce the run.
- Do not execute banking operations automatically.
- Do not integrate with a real core banking system yet.

**Staging boundary:**
- Runs on isolated Windows Server.
- Model and llama binary are available offline.
- Model hash is verified before inference.
- Runtime egress is blocked and evidenced.
- Outputs/logs live on encrypted storage or an approved encrypted volume.
- Append-only audit trail exists.
- Demo package includes sanitized examples, metrics, and compliance evidence.

**Out of scope until a bank contract defines it:**
- Generic core-banking adapter.
- Full web dashboard with AD/MFA.
- Production decision automation.
- Multi-tenant SaaS.
- RAG/vector database. Current architecture is source-grounded extraction from the input PDF, not RAG.

## Canonical Decision

Use `Qwen2.5-7B-Instruct-GGUF Q4_K_M` as the canonical implementation model now because that is what `llmlocalpdf` downloads and runs. Treat Qwen3 as a future evaluation branch only after a golden-set comparison proves it is better.

Gate:

```powershell
rg -n "Qwen3|Qwen3-8B" C:\Users\franc\OneDrive\Documentos\dev\ferced\cedeira-ia-compliance
```

Expected after alignment: only appears in explicit future-evaluation notes, or not at all.

---

## Phase 0: Truth Alignment

**Objective:** Stop the documentation from claiming controls the code does not implement.

**Deliverables:**
- Claim matrix: implemented / staging / roadmap.
- Portal copy aligned to current runtime reality.
- Basic Auth secret fallback removed from portal middleware.

**Gate:** A reviewer can map every public compliance claim to either code evidence, documented staging evidence, or roadmap.

### Task 0.1: Create Claim Matrix

**Files:**
- Create: `docs/compliance-claim-matrix.md`
- Reference: `README.md`
- Reference: `DEPLOY.md`
- Reference: `../cedeira-ia-compliance/README.md`
- Reference: `../cedeira-ia-compliance/presentacion-banco.html`
- Reference: `../cedeira-ia-compliance/gap-analysis.html`
- Reference: `../cedeira-ia-compliance/roadmap-implementacion.html`
- Reference: `../cedeira-ia-compliance/circuito-completo.html`

**Step 1: List implemented controls**

Document these as implemented:
- Local default execution.
- No API keys.
- `llama-server` bound to `127.0.0.1`.
- Firewall recommendation.
- SHA-256 verification of pinned `llama.cpp` release.
- JSON structured output.
- Basic metadata: `source_file`, `needs_ocr`, `warnings`, `processed_at`.
- CBU validation helper exists but is not integrated.

**Step 2: List staging controls**

Document these as staging targets:
- Deterministic schema validation.
- CBU/CUIT/amount validation.
- Source anchoring per critical field.
- Model `.gguf` hash verification at startup.
- Human review report.
- Append-only audit trail.
- Offline install package.
- Evidence of no runtime egress.

**Step 3: List roadmap controls**

Document these as roadmap:
- AD/MFA dashboard.
- TLS reverse proxy.
- Core banking integration.
- Queue/dashboard workflow.
- RAG/vector retrieval.
- Formal SAST/DAST.
- Bias audit program.
- NIST 800-88 decommissioning playbook.

**Step 4: Verify**

Run:

```powershell
rg -n "Qwen3|0\.0\.0\.0:9090|appsettings|AWS S3|RAG|logs inmutables|AD \+ MFA" ..\cedeira-ia-compliance
```

Expected: each remaining hit is either removed, corrected, or clearly labeled as roadmap/staging.

**Step 5: Commit**

```powershell
git add docs/compliance-claim-matrix.md
git commit -m "docs: add compliance claim matrix"
```

### Task 0.2: Align Portal Claims

**Files:**
- Modify: `../cedeira-ia-compliance/README.md`
- Modify: `../cedeira-ia-compliance/index.html`
- Modify: `../cedeira-ia-compliance/presentacion-banco.html`
- Modify: `../cedeira-ia-compliance/gap-analysis.html`
- Modify: `../cedeira-ia-compliance/roadmap-implementacion.html`
- Modify: `../cedeira-ia-compliance/circuito-completo.html`
- Modify: `../cedeira-ia-compliance/informe-compliance.html`

**Step 1: Replace model identity**

Replace implemented-model references:

```text
Qwen3-8B-GGUF -> Qwen2.5-7B-Instruct-GGUF Q4_K_M
Qwen3-8B local -> Qwen2.5-7B local
```

Keep Qwen3 only if explicitly phrased as "future evaluation".

**Step 2: Remove non-existent dashboard claims**

Replace claims about:
- dashboard on `0.0.0.0:9090`
- `appsettings.json`
- admin password in config

With:

```text
Hoy no existe dashboard administrativo en llmlocalpdf. La interfaz operativa actual es batch local por carpetas input/output. Un dashboard con AD/MFA queda como roadmap si el banco lo requiere.
```

**Step 3: Downgrade aspirational checks**

For deck/public content, split controls into:
- Implementado hoy
- Requerido para staging bancario
- Roadmap

Do not show AES-256, AD/MFA, RAG, logs inmutables, source-per-field, or core integration as implemented.

**Step 4: Verify links/assets**

Run:

```powershell
$missing = @()
Get-ChildItem -Filter *.html | ForEach-Object {
  $file=$_.Name
  $text=Get-Content $_.FullName -Raw -Encoding UTF8
  [regex]::Matches($text, '(?:href|src)="([^"]+)"') | ForEach-Object {
    $ref=$_.Groups[1].Value
    if ($ref -match '^(https?:|mailto:|#|data:)') { return }
    $path=($ref -split '[?#]')[0]
    if ([string]::IsNullOrWhiteSpace($path)) { return }
    $full=Join-Path (Get-Location) $path
    if (-not (Test-Path $full)) { $missing += [PSCustomObject]@{File=$file; Ref=$ref} }
  }
}
if ($missing.Count) { $missing | Format-Table -AutoSize } else { 'No missing local href/src targets found.' }
```

Expected: no missing local targets.

**Step 5: Commit**

```powershell
cd ..\cedeira-ia-compliance
git add README.md index.html presentacion-banco.html gap-analysis.html roadmap-implementacion.html circuito-completo.html informe-compliance.html
git commit -m "docs: align compliance portal with llmlocalpdf reality"
```

---

## Phase 1: Evaluation Harness

**Objective:** Measure the pipeline before improving it.

**Deliverables:**
- Sanitized golden examples.
- Expected JSON fixtures.
- Fake LLM tests for pipeline behavior.
- Metrics report script.

**Gate:** The team can say whether a model/prompt/code change improved or worsened extraction on the same dataset.

### Task 1.1: Add Schema Contract

**Files:**
- Create: `schema_contract.py`
- Create: `tests/test_schema_contract.py`

**Step 1: Write failing tests**

Cover:
- Missing `schemaVersion`.
- Invalid `tipoInstruccion`.
- `movimiento` must be `None` for non-financial instructions.
- `confianzaTipoMovimiento` must be 0.0 to 1.0.
- `cantidadInstrucciones` must match `len(instrucciones)`.

**Step 2: Implement simple functions**

Use functions, not classes:

```python
def validate_schema(result: dict) -> list[str]:
    ...
```

Return a list of warning/error strings; do not raise for ordinary validation failures.

**Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_schema_contract -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add schema_contract.py tests/test_schema_contract.py
git commit -m "test: add JSON schema contract validation"
```

### Task 1.2: Add Golden Fixtures

**Files:**
- Create: `tests/fixtures/text/simple_transfer.txt`
- Create: `tests/fixtures/text/multiple_instructions.txt`
- Create: `tests/fixtures/text/no_financial_instruction.txt`
- Create: `tests/fixtures/expected/simple_transfer.json`
- Create: `tests/fixtures/expected/multiple_instructions.json`
- Create: `tests/fixtures/expected/no_financial_instruction.json`
- Create: `tests/test_golden_contract.py`

**Step 1: Use sanitized examples only**

No real personal data. Use fake names, fake expediente numbers, and CBUs that pass checksum but are visibly synthetic.

**Step 2: Test expected JSON shape**

Validate:
- Schema contract.
- CBU checksum.
- Number of instructions.
- Movement type.
- Amount parsing.
- Beneficiary fields.

**Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_golden_contract -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add tests/fixtures tests/test_golden_contract.py
git commit -m "test: add sanitized golden extraction fixtures"
```

---

## Phase 2: Deterministic Post-LLM Controls

**Objective:** Do not trust the LLM for critical banking fields unless deterministic checks pass.

**Deliverables:**
- Integrated CBU validation.
- CUIT validation.
- Amount/source anchoring.
- Processability rules.
- Expanded warnings.

**Gate:** If a critical field is not valid and source-grounded, the output is not marked processable.

### Task 2.1: Integrate CBU Validation

**Files:**
- Modify: `postprocess.py`
- Modify: `tests/test_cbu.py`

**Step 1: Write failing tests**

Add cases where:
- `destinoFondos.tipo == "cbu"` and identifier has invalid checksum.
- CBU field is valid but not present in source text.
- Valid CBU with separators is normalized.

Expected behavior:
- Invalid or missing-source CBU adds warning.
- Instruction becomes `esProcesable=false`.
- `motivoNoProcesable` explains the deterministic failure.

**Step 2: Change function signature conservatively**

Prefer:

```python
def reconcile_instrucciones(llm_result: dict, source_text: str = "") -> tuple[dict, list[str]]:
    ...
```

Keep default `source_text=""` to avoid breaking existing callers immediately.

**Step 3: Wire source text**

Modify `process_pdfs.py` to call:

```python
llm_result, warnings = reconcile_instrucciones(llm_result, text)
```

**Step 4: Verify**

Run:

```powershell
python -m unittest tests.test_cbu -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 5: Commit**

```powershell
git add postprocess.py process_pdfs.py tests/test_cbu.py
git commit -m "feat: validate CBU fields against source text"
```

### Task 2.2: Add Critical Field Anchoring

**Files:**
- Create: `source_anchor.py`
- Create: `tests/test_source_anchor.py`
- Modify: `postprocess.py`

**Step 1: Write failing tests**

Cover:
- Exact CBU present.
- CBU with separators present.
- Amount present as `$ 500.000`, `500000`, and `500.000,00`.
- Missing amount.
- Beneficiary name partial match.

**Step 2: Implement simple match helpers**

Use functions:

```python
def find_cbu_anchor(source_text: str, cbu: str) -> dict | None:
    ...

def find_amount_anchor(source_text: str, amount: float) -> dict | None:
    ...
```

Anchor shape:

```json
{
  "field": "destinoFondos.identificador",
  "value": "0110040400000000000017",
  "snippet": "...",
  "matchType": "normalized_exact"
}
```

No fuzzy matching in the first implementation.

**Step 3: Attach anchors**

Add:

```json
"_evidence": {
  "anchors": [...]
}
```

inside each instruction.

**Step 4: Verify**

Run:

```powershell
python -m unittest tests.test_source_anchor -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 5: Commit**

```powershell
git add source_anchor.py postprocess.py tests/test_source_anchor.py
git commit -m "feat: anchor critical fields to source text"
```

---

## Phase 3: Audit Metadata and Reproducibility

**Objective:** Every output should explain what code/model/prompt/input produced it.

**Deliverables:**
- PDF SHA-256.
- Extracted text SHA-256.
- Prompt SHA-256.
- Code commit.
- Model path and optional model SHA-256.
- Start/end timestamps.

**Gate:** Given an output JSON, a reviewer can identify the exact input, prompt, code revision, and model artifact used.

### Task 3.1: Add Audit Helpers

**Files:**
- Create: `audit_metadata.py`
- Create: `tests/test_audit_metadata.py`
- Modify: `process_pdfs.py`

**Step 1: Write failing tests**

Cover:
- SHA-256 for file.
- SHA-256 for text.
- Git commit returns a string or `"unknown"` if git unavailable.
- Prompt hash changes when prompt changes.

**Step 2: Implement helpers**

Use stdlib only:

```python
def sha256_file(path: Path) -> str:
    ...

def sha256_text(text: str) -> str:
    ...

def current_git_commit(base_dir: Path) -> str:
    ...
```

**Step 3: Write `_audit` block**

Add to each output:

```json
"_audit": {
  "input_sha256": "...",
  "extracted_text_sha256": "...",
  "prompt_sha256": "...",
  "code_commit": "...",
  "model_file": "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
  "started_at": "...",
  "finished_at": "..."
}
```

**Step 4: Verify**

Run:

```powershell
python -m unittest tests.test_audit_metadata -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 5: Commit**

```powershell
git add audit_metadata.py process_pdfs.py tests/test_audit_metadata.py
git commit -m "feat: add audit metadata to generated JSON"
```

### Task 3.2: Fix Index Reproducibility

**Files:**
- Modify: `process_pdfs.py`
- Create: `tests/test_index_writer.py`

**Step 1: Write failing test**

Reproduce current issue:
- One PDF already has output JSON.
- One PDF is newly processed.
- `index.jsonl` should include both rows, not only newly processed rows.

**Step 2: Extract index writer function**

Simple function:

```python
def build_index_rows(output_dir: Path, processed_rows: list[dict]) -> list[dict]:
    ...
```

Read existing JSON outputs and include skipped files.

**Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_index_writer -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add process_pdfs.py tests/test_index_writer.py
git commit -m "fix: include skipped outputs in index"
```

---

## Phase 4: Human Review Demo

**Objective:** Give the bank a safe review workflow without building a full dashboard.

**Deliverables:**
- Local HTML review report per PDF.
- Three demo cases.
- Export folder for approved JSON.

**Gate:** Demo can show processable, review-required, and OCR/non-processable examples end to end.

### Task 4.1: Generate Review HTML

**Files:**
- Create: `review_report.py`
- Create: `tests/test_review_report.py`
- Modify: `process_pdfs.py`

**Step 1: Write failing tests**

Validate generated HTML contains:
- source filename
- processability status
- warnings
- critical field anchors
- JSON block

**Step 2: Implement report generator**

Use stdlib `html.escape`.

Output:

```text
output/<pdf_stem>.review.html
```

**Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_review_report -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add review_report.py process_pdfs.py tests/test_review_report.py
git commit -m "feat: generate local review reports"
```

### Task 4.2: Add Demo Pack

**Files:**
- Create: `demo/README.md`
- Create: `demo/input/`
- Create: `demo/expected/`
- Create: `demo/run_demo.bat`

**Step 1: Add sanitized examples**

Include:
- `01-procesable`
- `02-requiere-revision`
- `03-needs-ocr`

If PDFs are not available, start with text fixtures and document that PDF samples are pending.

**Step 2: Add run instructions**

Demo should explain:
- install prerequisites
- run command
- expected outputs
- what to show in the portal/deck

**Step 3: Verify**

Run available tests:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add demo
git commit -m "docs: add sanitized demo pack"
```

---

## Phase 5: Staging Hardening

**Objective:** Prepare evidence for bank security/compliance review.

**Deliverables:**
- Model hash verification.
- Append-only hash-chain audit log.
- Offline install notes.
- Evidence checklist.

**Gate:** A staging operator can prove model integrity, no runtime egress, and run reproducibility.

### Task 5.1: Verify Model Hash at Startup

**Files:**
- Modify: `setup_llm.py`
- Modify: `start_server.bat`
- Create: `model_manifest.py`
- Create: `tests/test_model_manifest.py`

**Step 1: Write failing tests**

Cover:
- Manifest missing -> warning/failure depending mode.
- Hash mismatch -> fail closed.
- Hash match -> pass.

**Step 2: Implement manifest**

Manifest path:

```text
models/model-manifest.json
```

Fields:

```json
{
  "filename": "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
  "files": [
    "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
    "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf"
  ],
  "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
  "revision": "",
  "sha256": ""
}
```

If exact model hash is unknown, create the manifest after download by hashing the local file and require future startup to match it.

**Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_model_manifest -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add setup_llm.py start_server.bat model_manifest.py tests/test_model_manifest.py
git commit -m "feat: verify model hash before inference"
```

### Task 5.2: Add Append-Only Audit Log

**Files:**
- Create: `audit_log.py`
- Create: `tests/test_audit_log.py`
- Modify: `process_pdfs.py`

**Step 1: Write failing tests**

Cover:
- First event has previous hash empty.
- Second event includes previous event hash.
- Tampering with first event changes chain verification result.

**Step 2: Implement JSONL hash chain**

Write to:

```text
logs/audit.jsonl
```

Do not include document text or PII. Include filenames, hashes, status, warning counts, and timestamps.

**Step 3: Verify**

Run:

```powershell
python -m unittest tests.test_audit_log -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 4: Commit**

```powershell
git add audit_log.py process_pdfs.py tests/test_audit_log.py
git commit -m "feat: add hash-chained audit log"
```

---

## Phase 6: Compliance Portal as Evidence Layer

**Objective:** Use the portal to show what the product actually does, with proof and limitations.

**Deliverables:**
- Updated portal copy.
- Demo page with screenshots/results from demo pack.
- Compliance matrix tied to current controls.
- Clear roadmap labels.

**Gate:** The portal can be shown to a bank without overstating implementation status.

### Task 6.1: Add Product Status Page

**Files:**
- Create: `../cedeira-ia-compliance/product-status.html`
- Modify: `../cedeira-ia-compliance/index.html`

**Step 1: Create status sections**

Sections:
- Implementado hoy
- En staging
- Roadmap
- Limitaciones actuales
- Evidencia disponible

**Step 2: Link from portal**

Add link in `index.html` under internal/technical documents.

**Step 3: Verify**

Run local link check from Phase 0.

Expected: no missing local targets.

**Step 4: Commit**

```powershell
cd ..\cedeira-ia-compliance
git add product-status.html index.html
git commit -m "docs: add product implementation status page"
```

### Task 6.2: Update Bank Deck

**Files:**
- Modify: `../cedeira-ia-compliance/presentacion-banco.html`

**Step 1: Keep the sales narrative**

Do not make the deck defensive. Keep the promise, but label controls precisely:
- "Disponible hoy"
- "Preparado para staging"
- "Roadmap de homologacion"

**Step 2: Replace RAG claim**

Use:

```text
Extraccion anclada al documento fuente
```

instead of RAG unless a retrieval system exists.

**Step 3: Verify**

Run:

```powershell
rg -n "RAG|Qwen3|AD \+ MFA|logs inmutables|core bancario" presentacion-banco.html
```

Expected: hits are either removed or explicitly staged/roadmap.

**Step 4: Commit**

```powershell
git add presentacion-banco.html
git commit -m "docs: align bank deck with product status"
```

---

## Agent Execution Model

Use subagents only for independent scopes with disjoint write sets.

**Agent A: Pipeline validation**
- Owns: `schema_contract.py`, `source_anchor.py`, `postprocess.py`, related tests.
- Goal: deterministic validation and source anchoring.

**Agent B: Audit and operations**
- Owns: `audit_metadata.py`, `audit_log.py`, `model_manifest.py`, related tests, minimal edits to `process_pdfs.py`, `setup_llm.py`, `start_server.bat`.
- Goal: reproducibility and staging evidence.

**Agent C: Portal alignment**
- Owns: `../cedeira-ia-compliance/*.html`, `../cedeira-ia-compliance/README.md`.
- Goal: truthful claims and product-status page.

**Main agent responsibilities:**
- Keep the plan coherent.
- Review agent changes.
- Run full tests.
- Resolve any conflicts in shared files.
- Ensure documentation follows the code, not the other way around.

## Verification Gates

Before claiming the project is aligned:

```powershell
cd C:\Users\franc\OneDrive\Documentos\dev\ferced\llmlocalpdf
python -m unittest discover -s tests -v
git status --short --branch
```

Expected:
- all tests pass
- no unintended local changes

Then:

```powershell
cd C:\Users\franc\OneDrive\Documentos\dev\ferced\cedeira-ia-compliance
rg -n "Qwen3|0\.0\.0\.0:9090|appsettings|AWS S3|RAG|logs inmutables" *.html README.md
git status --short --branch
```

Expected:
- no unsupported claims remain, or every hit is explicitly labeled as staging/roadmap
- no unintended local changes

## Final Definition of Done

The alignment goal is complete only when:

- `llmlocalpdf` has deterministic validation tests and they pass.
- Critical fields are source-grounded or marked not processable.
- Outputs include audit metadata.
- Existing skipped outputs are represented correctly in `index.jsonl`.
- Demo pack exists with at least three sanitized cases.
- Portal and deck match implementation status.
- Basic Auth in portal has no hardcoded fallback secret.
- Both repos have clean git status except intentional committed work.
- The bank-facing narrative no longer claims Qwen3, RAG, dashboard, AD/MFA, AES-256, logs inmutables, core integration, or source-per-field as implemented unless code/evidence proves it.

