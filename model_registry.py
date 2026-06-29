"""Model registry and local manifest helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).parent
DEFAULT_REGISTRY_PATH = BASE_DIR / "model_registry.json"


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load the tracked allowlist of candidate models."""
    registry_path = path or DEFAULT_REGISTRY_PATH
    with open(registry_path, encoding="utf-8") as f:
        registry = json.load(f)

    if "default_model_id" not in registry:
        raise ValueError("Model registry missing default_model_id")
    if not isinstance(registry.get("models"), list):
        raise ValueError("Model registry missing models list")

    return registry


def get_model_spec(model_id: str | None = None, path: Path | None = None) -> dict[str, Any]:
    """Return an allowlisted model spec by id, or the registry default."""
    registry = load_registry(path)
    selected_id = model_id or registry["default_model_id"]

    for spec in registry["models"]:
        if spec.get("id") == selected_id:
            return dict(spec)

    raise ValueError(f"Unknown model id: {selected_id}")


def get_model_filenames(model_spec: dict[str, Any]) -> list[str]:
    """Return all local filenames required for a model artifact."""
    files = model_spec.get("files")
    if files:
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            raise ValueError("Model spec files must be a list of filenames")
        return list(files)
    return [model_spec["filename"]]


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 for a local artifact."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_model_paths(model_paths: Path | Sequence[Path]) -> list[Path]:
    if isinstance(model_paths, Path):
        return [model_paths]
    return list(model_paths)


def build_manifest(
    model_path: Path | Sequence[Path],
    model_spec: dict[str, Any],
) -> dict[str, Any]:
    """Build a local manifest for a downloaded model artifact."""
    model_paths = _normalize_model_paths(model_path)
    if not model_paths:
        raise ValueError("At least one model file is required")

    primary_path = model_paths[0]
    file_entries = [
        {
            "filename": path.name,
            "sha256": compute_sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in model_paths
    ]

    return {
        "model_id": model_spec["id"],
        "provider": model_spec.get("provider"),
        "repo": model_spec["repo"],
        "filename": primary_path.name,
        "expected_filename": model_spec["filename"],
        "expected_files": get_model_filenames(model_spec),
        "files": file_entries,
        "quantization": model_spec.get("quantization"),
        "license": model_spec["license"],
        "source_url": model_spec["source_url"],
        "sha256": file_entries[0]["sha256"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_status": "candidate_unreviewed",
        "approval_notes": model_spec.get("risk_notes", []),
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write a model manifest as stable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a local model manifest."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_manifest(model_path: Path, manifest_path: Path) -> list[str]:
    """Validate that a local model file matches its recorded manifest."""
    errors: list[str] = []

    if not model_path.exists():
        return [f"Model file not found: {model_path}"]
    if not manifest_path.exists():
        return [f"Model manifest not found: {manifest_path}"]

    manifest = load_manifest(manifest_path)
    expected_filename = manifest.get("expected_filename") or manifest.get("filename")
    if expected_filename and model_path.name != expected_filename:
        errors.append(
            f"Model filename mismatch: expected {expected_filename}, got {model_path.name}"
        )

    manifest_files = manifest.get("files")
    if isinstance(manifest_files, list) and manifest_files:
        for entry in manifest_files:
            filename = entry.get("filename")
            expected_sha = entry.get("sha256")
            if not filename:
                errors.append("Model manifest file entry missing filename")
                continue

            artifact_path = model_path.parent / filename
            if not artifact_path.exists():
                errors.append(f"Model file not found: {artifact_path}")
                continue
            if not expected_sha:
                errors.append(f"Model manifest missing sha256 for {filename}")
                continue

            actual_sha = compute_sha256(artifact_path)
            if actual_sha != expected_sha:
                errors.append(
                    f"SHA-256 mismatch for {filename}: expected {expected_sha}, got {actual_sha}"
                )
        return errors

    expected_sha = manifest.get("sha256")
    if not expected_sha:
        errors.append("Model manifest missing sha256")
    else:
        actual_sha = compute_sha256(model_path)
        if actual_sha != expected_sha:
            errors.append(
                f"SHA-256 mismatch: expected {expected_sha}, got {actual_sha}"
            )

    return errors
