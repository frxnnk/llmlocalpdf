import json
import os
import unittest
import urllib.request
from pathlib import Path

FIXTURES_TEXT = Path(__file__).parent / "fixtures" / "text"
FIXTURES_EXPECTED = Path(__file__).parent / "fixtures" / "expected"
SCRIPT_DIR = Path(__file__).parent.parent
LLM_ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"


def llm_server_running():
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


@unittest.skipUnless(llm_server_running(), "llama-server not running on :8080")
class TestIntegrationLLM(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from llm_client import LLMClient
        from postprocess import reconcile_instrucciones
        from golden_eval import compare_result

        cls.llm = LLMClient(endpoint=LLM_ENDPOINT)
        cls.reconcile = staticmethod(reconcile_instrucciones)
        cls.compare = staticmethod(compare_result)

        prompt_file = SCRIPT_DIR / "prompt_template.txt"
        cls.system_prompt = prompt_file.read_text(encoding="utf-8")

    def _process_text(self, text):
        if not text.strip():
            return {"_pipeline": {"error": "empty", "needs_ocr": True}}

        marker = "### USER ###"
        if marker in self.system_prompt:
            system_part, user_part = self.system_prompt.split(marker, 1)
        else:
            system_part = self.system_prompt
            user_part = "{document_text}"

        user_prompt = user_part.replace("{document_text}", text).replace("{oficio_id}", "test-integration")
        result = self.llm.call_with_json_repair(
            system_prompt=system_part.strip(),
            user_prompt=user_prompt.strip()
        )
        if not isinstance(result, dict):
            raise ValueError(f"LLM returned non-dict: {type(result)}")

        result.setdefault("schemaVersion", "1.0")
        result.setdefault("oficioId", "test-integration")
        result.setdefault("resumenGeneral", {})
        result.setdefault("instrucciones", [])

        result, _warnings = self.reconcile(result, source_text=text)
        return result

    def test_simple_transfer(self):
        text = (FIXTURES_TEXT / "simple_transfer.txt").read_text(encoding="utf-8")
        result = self._process_text(text)
        expected = json.loads((FIXTURES_EXPECTED / "simple_transfer.json").read_text(encoding="utf-8"))
        comparison = self.compare(result, expected)
        self.assertGreater(comparison["score"], 0.5, f"Score too low: {comparison}")

    def test_no_financiera(self):
        text = (FIXTURES_TEXT / "no_financiera.txt").read_text(encoding="utf-8")
        result = self._process_text(text)
        self.assertIsInstance(result, dict)
        self.assertIn("instrucciones", result)

    def test_invalid_cbu(self):
        text = (FIXTURES_TEXT / "invalid_cbu.txt").read_text(encoding="utf-8")
        result = self._process_text(text)
        expected = json.loads((FIXTURES_EXPECTED / "invalid_cbu.json").read_text(encoding="utf-8"))
        comparison = self.compare(result, expected)
        self.assertGreater(comparison["score"], 0.3, f"Score too low: {comparison}")

    def test_llm_responds(self):
        text = (FIXTURES_TEXT / "simple_transfer.txt").read_text(encoding="utf-8")
        result = self._process_text(text)
        self.assertIsInstance(result, dict)
        self.assertIn("instrucciones", result)
        self.assertIsInstance(result["instrucciones"], list)


if __name__ == "__main__":
    unittest.main()
