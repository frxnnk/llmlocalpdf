"""Tests for setup-time LLM artifact downloads."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import setup_llm


class TestSetupLlmDownload(unittest.TestCase):
    def test_download_model_uses_huggingface_hub_python_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            models_dir = Path(tmp) / "models"
            manifest_path = models_dir / "model-manifest.json"
            model_spec = {
                "id": "demo",
                "provider": "Example",
                "repo": "example/model",
                "filename": "demo.gguf",
                "license": "Apache-2.0",
                "source_url": "https://example.invalid/model",
                "risk_notes": [],
            }

            def fake_hf_download(**kwargs):
                model_path = Path(kwargs["local_dir"]) / kwargs["filename"]
                model_path.parent.mkdir(parents=True, exist_ok=True)
                model_path.write_bytes(b"downloaded-model")
                return str(model_path)

            def fake_subprocess_run(*args, **kwargs):
                model_path = models_dir / model_spec["filename"]
                model_path.parent.mkdir(parents=True, exist_ok=True)
                model_path.write_bytes(b"downloaded-model")
                return subprocess.CompletedProcess(args, 0)

            with (
                patch("setup_llm.MODELS_DIR", models_dir),
                patch("setup_llm.MANIFEST_PATH", manifest_path),
                patch("setup_llm.get_model_spec", return_value=model_spec),
                patch(
                    "setup_llm.hf_hub_download",
                    side_effect=fake_hf_download,
                    create=True,
                ) as hf_download,
                patch(
                    "setup_llm.subprocess.run",
                    side_effect=fake_subprocess_run,
                ) as subprocess_run,
            ):
                setup_llm.download_model(accept_download=True)

            self.assertEqual(hf_download.call_count, 1)
            _, kwargs = hf_download.call_args
            self.assertEqual(kwargs["repo_id"], "example/model")
            self.assertEqual(kwargs["filename"], "demo.gguf")
            self.assertEqual(Path(kwargs["local_dir"]), models_dir)
            subprocess_run.assert_not_called()
            self.assertTrue(manifest_path.exists())

    def test_download_model_downloads_all_allowlisted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            models_dir = Path(tmp) / "models"
            manifest_path = models_dir / "model-manifest.json"
            model_spec = {
                "id": "demo-split",
                "provider": "Example",
                "repo": "example/model",
                "filename": "demo-00001-of-00002.gguf",
                "files": [
                    "demo-00001-of-00002.gguf",
                    "demo-00002-of-00002.gguf",
                ],
                "license": "Apache-2.0",
                "source_url": "https://example.invalid/model",
                "risk_notes": [],
            }
            downloaded: list[str] = []

            def fake_hf_download(**kwargs):
                downloaded.append(kwargs["filename"])
                model_path = Path(kwargs["local_dir"]) / kwargs["filename"]
                model_path.parent.mkdir(parents=True, exist_ok=True)
                model_path.write_bytes(kwargs["filename"].encode("utf-8"))
                return str(model_path)

            with (
                patch("setup_llm.MODELS_DIR", models_dir),
                patch("setup_llm.MANIFEST_PATH", manifest_path),
                patch("setup_llm.get_model_spec", return_value=model_spec),
                patch(
                    "setup_llm.hf_hub_download",
                    side_effect=fake_hf_download,
                ),
            ):
                setup_llm.download_model(accept_download=True)

            self.assertEqual(downloaded, model_spec["files"])
            self.assertTrue((models_dir / model_spec["files"][0]).exists())
            self.assertTrue((models_dir / model_spec["files"][1]).exists())
            self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
