import unittest
from unittest.mock import patch

import requests

from llm_client import LLMClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", json_error=None):
        self.status_code = status_code
        self.payload = payload
        self.text = text
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


def llm_payload(content):
    return {"choices": [{"message": {"content": content}}]}


class TestParseJsonResponse(unittest.TestCase):
    def test_parses_plain_json(self):
        result = LLMClient.parse_json_response('{"ok": true}')

        self.assertEqual(result, {"ok": True})

    def test_parses_markdown_json_fence(self):
        raw = "```json\n{\"amount\": 1000}\n```"

        result = LLMClient.parse_json_response(raw)

        self.assertEqual(result, {"amount": 1000})

    def test_returns_none_for_malformed_json(self):
        result = LLMClient.parse_json_response('{"ok": true')

        self.assertIsNone(result)


class TestCall(unittest.TestCase):
    def test_call_posts_openai_payload_and_returns_message_content(self):
        client = LLMClient(endpoint="http://example.test/v1/chat/completions", timeout=12)
        response = FakeResponse(payload=llm_payload('{"ok": true}'))

        with patch("llm_client.requests.post", return_value=response) as post:
            result = client.call("system prompt", "user prompt", temperature=0.3, max_tokens=99)

        self.assertEqual(result, '{"ok": true}')
        post.assert_called_once()
        request = post.call_args.kwargs
        self.assertEqual(request["json"]["temperature"], 0.3)
        self.assertEqual(request["json"]["max_tokens"], 99)
        self.assertEqual(
            request["json"]["messages"],
            [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
        )
        self.assertEqual(request["timeout"], 12)

    def test_4xx_response_is_not_retried(self):
        client = LLMClient(max_retries=3)
        response = FakeResponse(status_code=400, text="bad request")

        with patch("llm_client.requests.post", return_value=response) as post:
            with self.assertRaisesRegex(RuntimeError, "4xx"):
                client.call("system", "user")

        post.assert_called_once()

    def test_5xx_response_is_retried_then_returns_success(self):
        client = LLMClient(max_retries=2, backoff_factor=1.0)
        responses = [
            FakeResponse(status_code=500, text="server error"),
            FakeResponse(payload=llm_payload("fixed")),
        ]

        with patch("llm_client.requests.post", side_effect=responses) as post:
            with patch("llm_client.time.sleep") as sleep:
                result = client.call("system", "user")

        self.assertEqual(result, "fixed")
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_network_errors_are_retried_until_exhausted(self):
        client = LLMClient(max_retries=1, backoff_factor=1.0)

        with patch(
            "llm_client.requests.post",
            side_effect=requests.exceptions.ConnectionError("connection refused"),
        ) as post:
            with patch("llm_client.time.sleep") as sleep:
                with self.assertRaisesRegex(RuntimeError, "after 2 attempts"):
                    client.call("system", "user")

        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_invalid_http_json_body_raises_runtime_error(self):
        client = LLMClient()
        response = FakeResponse(json_error=ValueError("not json"))

        with patch("llm_client.requests.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "Malformed LLM response"):
                client.call("system", "user")

    def test_missing_message_content_raises_runtime_error(self):
        client = LLMClient()
        response = FakeResponse(payload={"choices": [{}]})

        with patch("llm_client.requests.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "Malformed LLM response"):
                client.call("system", "user")


class TestJsonRepair(unittest.TestCase):
    def test_call_with_json_repair_returns_first_valid_json_without_repair(self):
        client = LLMClient()

        with patch.object(client, "call", return_value='{"ok": true}') as call:
            result = client.call_with_json_repair("system", "user", "fix {broken_json}")

        self.assertEqual(result, {"ok": True})
        call.assert_called_once_with("system", "user", 0.2, 1500)

    def test_call_with_json_repair_repairs_malformed_json(self):
        client = LLMClient()

        with patch.object(client, "call", side_effect=['{"ok": true', '{"ok": true}']) as call:
            result = client.call_with_json_repair("system", "user", "fix {broken_json}")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(call.call_count, 2)
        repair_call = call.call_args_list[1].kwargs
        self.assertEqual(repair_call["system"], "Sos un asistente que repara JSON malformado.")
        self.assertIn('{"ok": true', repair_call["user"])
        self.assertEqual(repair_call["temperature"], 0.1)

    def test_call_with_json_repair_raises_when_repair_is_still_malformed(self):
        client = LLMClient()

        with patch.object(client, "call", side_effect=["not json", "still not json"]):
            with self.assertRaisesRegex(RuntimeError, "No se pudo obtener JSON"):
                client.call_with_json_repair("system", "user", "fix {broken_json}")


if __name__ == "__main__":
    unittest.main()
