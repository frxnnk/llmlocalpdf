"""Metadata reproducible para auditoria de corridas."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from model_registry import compute_sha256, get_model_filenames, get_model_spec, load_manifest


def get_code_commit(code_dir: Path | None = None) -> str | None:
    repo_dir = code_dir or Path(__file__).parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    commit = result.stdout.strip()
    return commit or None


def build_audit_metadata(
    source_file: Path,
    prompt_text: str,
    extracted_text: str | None = None,
    model_manifest_path: Path | None = None,
    code_dir: Path | None = None,
    processed_at: str | None = None,
) -> dict:
    model_spec = get_model_spec()
    metadata = {
        "source_file": source_file.name,
        "source_sha256": compute_sha256(source_file),
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "model_id": model_spec["id"],
        "model_filename": get_model_filenames(model_spec)[0],
        "processed_at": processed_at or datetime.now(timezone.utc).isoformat(),
    }
    if extracted_text is not None:
        metadata["extracted_text_sha256"] = hashlib.sha256(
            extracted_text.encode("utf-8")
        ).hexdigest()

    if model_manifest_path is not None and model_manifest_path.exists():
        manifest = load_manifest(model_manifest_path)
        model_sha = manifest.get("sha256")
        if model_sha:
            metadata["model_sha256"] = model_sha
        model_files = manifest.get("files")
        if isinstance(model_files, list):
            metadata["model_files"] = [
                {"filename": entry["filename"], "sha256": entry["sha256"]}
                for entry in model_files
                if "filename" in entry and "sha256" in entry
            ]

    code_commit = get_code_commit(code_dir)
    if code_commit:
        metadata["code_commit"] = code_commit

    return metadata
