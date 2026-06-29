import hashlib
import re
import tempfile
import unittest
from pathlib import Path

from audit_metadata import build_audit_metadata, get_code_commit
from process_pdfs import build_pipeline_metadata


class TestAuditMetadata(unittest.TestCase):
    def test_metadata_includes_source_prompt_model_and_processed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "oficio.pdf"
            source_file.write_bytes(b"pdf-bytes")

            metadata = build_audit_metadata(
                source_file,
                "prompt text",
                code_dir=Path(tmp),
                processed_at="2026-06-29T00:00:00+00:00",
            )

        self.assertEqual(metadata["source_file"], "oficio.pdf")
        self.assertEqual(
            metadata["source_sha256"],
            hashlib.sha256(b"pdf-bytes").hexdigest(),
        )
        self.assertEqual(
            metadata["prompt_sha256"],
            hashlib.sha256("prompt text".encode("utf-8")).hexdigest(),
        )
        self.assertEqual(metadata["model_id"], "qwen2.5-7b-instruct-q4_k_m")
        self.assertEqual(metadata["model_filename"], "qwen2.5-7b-instruct-q4_k_m.gguf")
        self.assertEqual(metadata["processed_at"], "2026-06-29T00:00:00+00:00")

    def test_metadata_includes_model_sha_when_manifest_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "oficio.pdf"
            source_file.write_bytes(b"pdf-bytes")
            manifest_path = Path(tmp) / "model-manifest.json"
            manifest_path.write_text('{"sha256": "model-sha"}', encoding="utf-8")

            metadata = build_audit_metadata(
                source_file,
                "prompt text",
                model_manifest_path=manifest_path,
                code_dir=Path(tmp),
            )

        self.assertEqual(metadata["model_sha256"], "model-sha")

    def test_get_code_commit_returns_none_outside_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(get_code_commit(Path(tmp)))

    def test_metadata_includes_code_commit_inside_repo(self):
        repo_dir = Path(__file__).parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "oficio.pdf"
            source_file.write_bytes(b"pdf-bytes")

            metadata = build_audit_metadata(source_file, "prompt text", code_dir=repo_dir)

        self.assertRegex(metadata["code_commit"], re.compile(r"^[0-9a-f]{40}$"))

    def test_pipeline_metadata_wraps_audit_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "oficio.pdf"
            source_file.write_bytes(b"pdf-bytes")

            pipeline = build_pipeline_metadata(
                source_file,
                needs_ocr=True,
                warnings=["needs OCR"],
                prompt_text="prompt text",
                script_dir=Path(tmp),
                error="PDF sin texto extraible",
                processed_at="2026-06-29T00:00:00+00:00",
            )

        self.assertEqual(pipeline["source_file"], "oficio.pdf")
        self.assertTrue(pipeline["needs_ocr"])
        self.assertEqual(pipeline["warnings"], ["needs OCR"])
        self.assertEqual(pipeline["error"], "PDF sin texto extraible")
        self.assertEqual(
            pipeline["audit"]["source_sha256"],
            hashlib.sha256(b"pdf-bytes").hexdigest(),
        )
        self.assertEqual(pipeline["audit"]["processed_at"], "2026-06-29T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
