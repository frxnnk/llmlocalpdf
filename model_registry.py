"""Model registry and local manifest helpers."""

from __future__ import annotations

import hashlib
import json
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


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 for a local artifact."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(model_path: Path, model_spec: dict[str, Any]) -> dict[str, Any]:
    """Build a local manifest for a downloaded model artifact."""
    return {
        "model_id": model_spec["id"],
        "provider": model_spec.get("provider"),
        "repo": model_spec["repo"],
        "filename": model_path.name,
        "expected_filename": model_spec["filename"],
        "quantization": model_spec.get("quantization"),
        "license": model_spec["license"],
        "source_url": model_spec["source_url"],
        "sha256": compute_sha256(model_path),
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
