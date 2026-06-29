"""Tests for model registry and manifest helpers."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from model_registry import (
    build_manifest,
    compute_sha256,
    get_model_spec,
    load_manifest,
    load_registry,
    validate_manifest,
    write_manifest,
)
from verify_model import verify_local_model


class TestModelRegistry(unittest.TestCase):
    def test_default_qwen_model_is_allowlisted(self):
        spec = get_model_spec()

        self.assertEqual(spec["id"], "qwen2.5-7b-instruct-q4_k_m")
        self.assertEqual(spec["repo"], "Qwen/Qwen2.5-7B-Instruct-GGUF")
        self.assertEqual(spec["filename"], "qwen2.5-7b-instruct-q4_k_m.gguf")
        self.assertEqual(spec["license"], "Apache-2.0")
        self.assertIn("source_url", spec)
        self.assertIn("risk_notes", spec)

    def test_unknown_model_id_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown model id"):
            get_model_spec("missing-model")

    def test_load_registry_from_custom_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "default_model_id": "demo",
                        "models": [
                            {
                                "id": "demo",
                                "provider": "Example",
                                "repo": "example/model",
                                "filename": "demo.gguf",
                                "license": "Apache-2.0",
                                "source_url": "https://example.invalid/model",
                                "risk_notes": [],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = load_registry(registry_path)

        self.assertEqual(registry["default_model_id"], "demo")
        self.assertEqual(registry["models"][0]["filename"], "demo.gguf")

    def test_compute_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "sample.bin"
            file_path.write_bytes(b"abc")

            digest = compute_sha256(file_path)

        self.assertEqual(
            digest,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_manifest_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "qwen2.5-7b-instruct-q4_k_m.gguf"
            model_path.write_bytes(b"model-contents")
            manifest_path = Path(tmp) / "model-manifest.json"

            manifest = build_manifest(model_path, get_model_spec())
            write_manifest(manifest, manifest_path)
            loaded = load_manifest(manifest_path)
            errors = validate_manifest(model_path, manifest_path)

        self.assertEqual(loaded["filename"], "qwen2.5-7b-instruct-q4_k_m.gguf")
        self.assertEqual(loaded["license"], "Apache-2.0")
        self.assertEqual(errors, [])

    def test_manifest_validation_reports_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "qwen2.5-7b-instruct-q4_k_m.gguf"
            model_path.write_bytes(b"model-contents")
            manifest_path = Path(tmp) / "model-manifest.json"

            manifest = build_manifest(model_path, get_model_spec())
            write_manifest(manifest, manifest_path)
            model_path.write_bytes(b"tampered")

            errors = validate_manifest(model_path, manifest_path)

        self.assertTrue(any("SHA-256 mismatch" in error for error in errors))

    def test_verify_local_model_requires_manifest_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "qwen2.5-7b-instruct-q4_k_m.gguf"
            manifest_path = Path(tmp) / "model-manifest.json"
            model_path.write_bytes(b"model-contents")

            errors = verify_local_model(model_path, manifest_path)

        self.assertTrue(any("manifest" in error.lower() for error in errors))

    def test_verify_local_model_allows_unmanifested_dev_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "qwen2.5-7b-instruct-q4_k_m.gguf"
            manifest_path = Path(tmp) / "model-manifest.json"
            model_path.write_bytes(b"model-contents")

            errors = verify_local_model(
                model_path,
                manifest_path,
                allow_unmanifested=True,
            )

        self.assertEqual(errors, [])

    def test_verify_local_model_allows_missing_model_in_dev_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "qwen2.5-7b-instruct-q4_k_m.gguf"
            manifest_path = Path(tmp) / "model-manifest.json"

            errors = verify_local_model(
                model_path,
                manifest_path,
                allow_unmanifested=True,
            )

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
