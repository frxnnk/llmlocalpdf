"""Verify the local GGUF model artifact against its manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from model_registry import get_model_filenames, get_model_spec, validate_manifest


BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
MANIFEST_PATH = MODELS_DIR / "model-manifest.json"


def verify_local_model(
    model_path: Path,
    manifest_path: Path,
    *,
    allow_unmanifested: bool = False,
) -> list[str]:
    """Return validation errors for a local model artifact."""
    if allow_unmanifested and not manifest_path.exists():
        return []
    return validate_manifest(model_path, manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify local LLM model file against model-manifest.json"
    )
    parser.add_argument(
        "--allow-unmanifested",
        action="store_true",
        help="Developer mode: allow a present model without manifest, with warning.",
    )
    args = parser.parse_args()

    spec = get_model_spec()
    model_path = MODELS_DIR / get_model_filenames(spec)[0]
    errors = verify_local_model(
        model_path,
        MANIFEST_PATH,
        allow_unmanifested=args.allow_unmanifested,
    )

    if errors:
        print("ERROR: model verification failed")
        for error in errors:
            print(f"  - {error}")
        return 1

    if args.allow_unmanifested and not MANIFEST_PATH.exists():
        if model_path.exists():
            print("WARN: model exists without manifest; acceptable only for developer mode.")
        else:
            print("WARN: model is not downloaded; acceptable only for developer mode.")
        return 0

    print(f"[OK] Model verified: {model_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
